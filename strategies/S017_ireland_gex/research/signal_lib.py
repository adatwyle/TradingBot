"""S017 ireland_gex — shared research building blocks.

Single source for indicator math, data loading, breakout detection and
GEX-snapshot inventory, reused by phase_a.py and etude_03_volume_cap.py
(study_01/study_02 predate this module and are kept frozen with their
dated results).

All definitions implement spec-strategie.md §3 with the defaults frozen in
manifest.yaml. No backtest engine here (R9) — pure signal measurement.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DB = Path("C:/db/tradingBot/S017")

# ── frozen defaults (manifest.yaml) ─────────────────────────────────────────
COMPRESS_BARS = 6
COMPRESS_RANGE_ATR = 1.5
VOL_MULT = 1.5
VOL_SMA = 20
STOP_BUFFER_ATR = 0.25
EMA_SPREAD_MIN_5M = 0.15
EMA_SPREAD_MIN_D = 0.30
NEAR_LEVEL_PCT = 0.10          # % of price = "at the level"
LEVEL_UNIVERSE_PCT = 2.0
RR_MIN = 2.0

RTH_BARS_FULL = 78             # 09:30..15:55 ET in 5min bars


# ── indicator math ──────────────────────────────────────────────────────────
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = pd.concat(
        [df["high"] - df["low"],
         (df["high"] - df["close"].shift()).abs(),
         (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion (honest at small n)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


# ── data loading ────────────────────────────────────────────────────────────
def load_5min() -> pd.DataFrame:
    """SPY 5min RTH bars (ET tz), with indicators used everywhere.

    Convention (same as study_01): indicators are computed on the
    RTH-concatenated series — EMAs bleed across day boundaries, which is
    consistent between studies and with a live warmup that spans days.
    """
    df = pd.read_csv(DB / "ohlcv" / "SPY_5min.csv", index_col=0, parse_dates=True)
    df = df.tz_convert("America/New_York").between_time("09:30", "15:55")
    df["ema9"], df["ema21"], df["ema50"] = ema(df.close, 9), ema(df.close, 21), ema(df.close, 50)
    df["atr14"] = atr(df)
    df["vol_sma"] = df.volume.rolling(VOL_SMA).mean()
    return df


def load_daily() -> pd.DataFrame:
    df = pd.read_csv(DB / "ohlcv" / "SPY_daily.csv", index_col=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
    return df


def daily_stack(daily: pd.DataFrame) -> pd.DataFrame:
    """Daily EMA stack; *_known = state at next open (previous CLOSED bar, R1)."""
    d = daily.copy()
    d["ema9"], d["ema21"], d["ema50"] = ema(d.close, 9), ema(d.close, 21), ema(d.close, 50)
    d["atr14"] = atr(d)
    spread = pd.concat([d.ema9 - d.ema21, d.ema21 - d.ema50], axis=1)
    d["bull"] = (d.ema9 > d.ema21) & (d.ema21 > d.ema50) & \
                (spread.min(axis=1) / d.atr14 >= EMA_SPREAD_MIN_D)
    spread_b = pd.concat([d.ema21 - d.ema9, d.ema50 - d.ema21], axis=1)
    d["bear"] = (d.ema50 > d.ema21) & (d.ema21 > d.ema9) & \
                (spread_b.min(axis=1) / d.atr14 >= EMA_SPREAD_MIN_D)
    d["bull_known"] = d["bull"].shift(1).astype("boolean").fillna(False).astype(bool)
    d["bear_known"] = d["bear"].shift(1).astype("boolean").fillna(False).astype(bool)
    return d


# ── GEX snapshot inventory ──────────────────────────────────────────────────
@dataclass
class GexDay:
    date: str                       # YYYY-MM-DD
    path: Path
    spot: float                     # spot at capture
    asof: str
    net_gex: float                  # $ per 1% move
    regime: str                     # positive | negative
    majors: list[float] = field(default_factory=list)
    major_signs: dict[float, str] = field(default_factory=dict)
    n_premarket_rows: int = 1       # >1 = canonical file was overwritten same day
    quality: str = "ok"             # ok | multi-capture


def list_gex_days() -> list[GexDay]:
    """All canonical (non-suffixed) premarket GEX snapshots, with quality flags."""
    days: list[GexDay] = []
    sum_path = DB / "gex" / "SPY_gex_summary.csv"
    summary = pd.read_csv(sum_path) if sum_path.exists() else pd.DataFrame()
    for p in sorted((DB / "gex").glob("SPY_gex_????-??-??.csv")):
        m = re.match(r"SPY_gex_(\d{4}-\d{2}-\d{2})\.csv$", p.name)
        if not m:
            continue
        date = m.group(1)
        g = pd.read_csv(p)
        majors_df = g[g.is_major]
        majors = [float(k) for k in majors_df.strike]
        signs = {float(r.strike): ("positive" if r.gex > 0 else "negative")
                 for r in majors_df.itertuples()}
        n_rows = 1
        if len(summary):
            n_rows = int(((summary.date == date) & (summary.snapshot == "premarket")).sum()) or 1
        days.append(GexDay(
            date=date, path=p, spot=float(g.spot.iloc[0]), asof=str(g["asof"].iloc[0]),
            net_gex=float(g.gex.sum()),
            regime="positive" if g.gex.sum() > 0 else "negative",
            majors=majors, major_signs=signs,
            n_premarket_rows=n_rows,
            quality="multi-capture" if n_rows > 1 else "ok",
        ))
    return days


def placebo_levels(gd: GexDay, universe: pd.DataFrame) -> dict[str, list[float]]:
    """Placebo level groups for H1 (spec §4), deterministic per day.

    - offset : majors shifted by ±2.50 $ (half-strike, same neighbourhoods)
    - round  : $5-round strikes in universe, non-major, > 2.5 $ from any major
    - random : uniform in the universe band, > 1.0 $ from any major,
               seeded by the date (reproducible run to run)
    """
    majors = gd.majors
    offset = [k + 2.5 for k in majors] + [k - 2.5 for k in majors]
    rnd_strikes = [float(k) for k in universe.strike
                   if k % 5 == 0 and (not majors or min(abs(k - m) for m in majors) > 2.5)]
    seed = int(hashlib.sha256(gd.date.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    lo = gd.spot * (1 - LEVEL_UNIVERSE_PCT / 100)
    hi = gd.spot * (1 + LEVEL_UNIVERSE_PCT / 100)
    random_lv: list[float] = []
    tries = 0
    while len(random_lv) < max(4, 2 * len(majors)) and tries < 200:
        lv = float(rng.uniform(lo, hi))
        tries += 1
        if majors and min(abs(lv - m) for m in majors) <= 1.0:
            continue
        random_lv.append(round(lv, 2))
    return {"major": majors, "placebo_offset": offset,
            "placebo_round": rnd_strikes, "placebo_random": random_lv}


# ── event measurement ───────────────────────────────────────────────────────
def first_touch_multi_horizon(day: pd.DataFrame, level: float,
                              horizons: tuple[int, ...] = (3, 6, 12)) -> dict | None:
    """First 5min bar touching `level`; reaction at each horizon (bars).

    Returns rejection/penetration (in ATR14 units of the touch bar) and
    `held_h{n}` = close after n bars still on the approach side of the level.
    Contacts with < 2 forward bars are dropped (nothing to measure).
    """
    touch = day[(day.low <= level) & (day.high >= level)]
    if not len(touch):
        return None
    i = day.index.get_loc(touch.index[0])
    bar = day.iloc[i]
    if not np.isfinite(bar.atr14) or bar.atr14 <= 0:
        return None
    fwd_all = day.iloc[i + 1:]
    if len(fwd_all) < 2:
        return None
    from_above = bar.open > level
    out: dict = {"level": level, "touch_time": str(touch.index[0]),
                 "from_above": bool(from_above), "atr": float(bar.atr14)}
    for h in horizons:
        fwd = fwd_all.iloc[:h]
        if from_above:
            rej = (fwd.high.max() - level) / bar.atr14
            pen = (level - fwd.low.min()) / bar.atr14
            held = bool(fwd.close.iloc[-1] > level)
        else:
            rej = (level - fwd.low.min()) / bar.atr14
            pen = (fwd.high.max() - level) / bar.atr14
            held = bool(fwd.close.iloc[-1] < level)
        out[f"rej_h{h}"] = round(float(rej), 2)
        out[f"pen_h{h}"] = round(float(pen), 2)
        out[f"held_h{h}"] = held
        out[f"nfwd_h{h}"] = len(fwd)
    return out


def find_breakouts(day: pd.DataFrame,
                   compress_bars: int = COMPRESS_BARS,
                   compress_range_atr: float = COMPRESS_RANGE_ATR,
                   stop_buffer_atr: float = STOP_BUFFER_ATR,
                   ema_spread_min_5m: float = EMA_SPREAD_MIN_5M) -> list[dict]:
    """All compression breakouts in one RTH day (long + short), parameterised.

    Same walk-forward as study_01: outcome = +1R before stop / stopped / eod;
    also records window bounds for level-proximity checks and full-day MFE.
    """
    out = []
    n = len(day)
    h, l, c, v = day.high.values, day.low.values, day.close.values, day.volume.values
    a, vs = day.atr14.values, day.vol_sma.values
    e9, e21, e50 = day.ema9.values, day.ema21.values, day.ema50.values
    i = compress_bars
    while i < n - 1:
        w_h = h[i - compress_bars:i].max()
        w_l = l[i - compress_bars:i].min()
        if not np.isfinite(a[i - 1]) or a[i - 1] <= 0 or (w_h - w_l) > compress_range_atr * a[i - 1]:
            i += 1
            continue
        side = "long" if c[i] > w_h else ("short" if c[i] < w_l else None)
        if side is None:
            i += 1
            continue
        vol_ratio = v[i] / vs[i] if vs[i] > 0 else np.nan
        entry = c[i]
        stop = (min(w_l, e50[i]) - stop_buffer_atr * a[i]) if side == "long" \
            else (max(w_h, e50[i]) + stop_buffer_atr * a[i])
        risk = abs(entry - stop)
        if risk <= 0 or not np.isfinite(vol_ratio):
            i += 1
            continue
        if side == "long":
            aligned = e9[i] > e21[i] > e50[i] and \
                min(e9[i] - e21[i], e21[i] - e50[i]) / a[i] >= ema_spread_min_5m
        else:
            aligned = e50[i] > e21[i] > e9[i] and \
                min(e21[i] - e9[i], e50[i] - e21[i]) / a[i] >= ema_spread_min_5m
        outcome, mfe = "eod", 0.0
        for j in range(i + 1, n):
            if side == "long":
                mfe = max(mfe, (h[j] - entry) / risk)
                if l[j] <= stop:
                    outcome = "stop"
                    break
                if h[j] >= entry + risk:
                    outcome = "target1r"
                    break
            else:
                mfe = max(mfe, (entry - l[j]) / risk)
                if h[j] >= stop:
                    outcome = "stop"
                    break
                if l[j] <= entry - risk:
                    outcome = "target1r"
                    break
        out.append(dict(ts=day.index[i], bar_idx=i, side=side,
                        vol_ratio=float(vol_ratio), aligned=bool(aligned),
                        entry=float(entry), stop=float(stop),
                        w_low=float(w_l), w_high=float(w_h),
                        outcome=outcome, mfe=round(float(mfe), 2)))
        i += compress_bars  # skip overlapping windows
    return out


def walk_r_outcome(day: pd.DataFrame, bar_idx: int, side: str,
                   entry: float, stop: float, target: float) -> tuple[str, float]:
    """Walk bar_idx+1..EOD with a fixed stop/target. Returns (outcome, realized R).

    stop hit -> -1R ; target hit -> +target R ; neither -> mark-to-close R at EOD.
    Bar hitting both stop and target counts as stop (conservative, no intra-bar
    sequencing available at 5min).
    """
    risk = abs(entry - stop)
    tgt_r = abs(target - entry) / risk
    h, l, c = day.high.values, day.low.values, day.close.values
    for j in range(bar_idx + 1, len(day)):
        if side == "long":
            if l[j] <= stop:
                return "stop", -1.0
            if h[j] >= target:
                return "target", round(tgt_r, 2)
        else:
            if h[j] >= stop:
                return "stop", -1.0
            if l[j] <= target:
                return "target", round(tgt_r, 2)
    last = c[-1]
    r = (last - entry) / risk if side == "long" else (entry - last) / risk
    return "eod", round(float(r), 2)
