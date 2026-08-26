"""S017 study 01 — H3: do compression breakouts WITH volume follow through better?

Measurable NOW (no GEX history needed): ~60 days of SPY 5min bars.
Definitions from spec-strategie.md §3.4-3.6 (defaults frozen in manifest.yaml),
WITHOUT the GEX-proximity condition — this isolates the volume filter's effect.

Also reports EMA alignment frequency (trade-opportunity feasibility, spec §3.4).

Output: research/results_study01_<date>.md
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

DB = Path("C:/db/tradingBot/S017")
OUT = Path(__file__).parent / f"results_study01_{datetime.now():%Y-%m-%d}.md"

# frozen defaults (manifest.yaml)
COMPRESS_BARS = 6
COMPRESS_RANGE_ATR = 1.5
VOL_MULT = 1.5
VOL_SMA = 20
STOP_BUFFER_ATR = 0.25
EMA_SPREAD_MIN_5M = 0.15
EMA_SPREAD_MIN_D = 0.30


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = pd.concat(
        [df["high"] - df["low"],
         (df["high"] - df["close"].shift()).abs(),
         (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def load_5min() -> pd.DataFrame:
    df = pd.read_csv(DB / "ohlcv" / "SPY_5min.csv", index_col=0, parse_dates=True)
    df = df.tz_convert("America/New_York")
    df = df.between_time("09:30", "15:55")  # RTH bars only
    return df


def load_daily() -> pd.DataFrame:
    df = pd.read_csv(DB / "ohlcv" / "SPY_daily.csv", index_col=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
    return df


def daily_stack(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    d["ema9"], d["ema21"], d["ema50"] = ema(d.close, 9), ema(d.close, 21), ema(d.close, 50)
    d["atr14"] = atr(d)
    spread = pd.concat([d.ema9 - d.ema21, d.ema21 - d.ema50], axis=1)
    d["bull"] = (d.ema9 > d.ema21) & (d.ema21 > d.ema50) & (spread.min(axis=1) / d.atr14 >= EMA_SPREAD_MIN_D)
    spread_b = pd.concat([d.ema21 - d.ema9, d.ema50 - d.ema21], axis=1)
    d["bear"] = (d.ema50 > d.ema21) & (d.ema21 > d.ema9) & (spread_b.min(axis=1) / d.atr14 >= EMA_SPREAD_MIN_D)
    # shifted: state known at next day's open (previous CLOSED daily bar — R1)
    d["bull_known"] = d["bull"].shift(1).fillna(False).astype(bool)
    d["bear_known"] = d["bear"].shift(1).fillna(False).astype(bool)
    return d


def find_breakouts(day: pd.DataFrame) -> list[dict]:
    """All compression breakouts in one RTH day, long and short."""
    out = []
    n = len(day)
    h, l, c, v = day.high.values, day.low.values, day.close.values, day.volume.values
    a = day.atr14.values
    vs = day.vol_sma.values
    e9, e21, e50 = day.ema9.values, day.ema21.values, day.ema50.values
    i = COMPRESS_BARS
    while i < n - 1:
        w_h = h[i - COMPRESS_BARS:i].max()
        w_l = l[i - COMPRESS_BARS:i].min()
        if not np.isfinite(a[i - 1]) or a[i - 1] <= 0 or (w_h - w_l) > COMPRESS_RANGE_ATR * a[i - 1]:
            i += 1
            continue
        # bar i is the potential breakout bar
        side = "long" if c[i] > w_h else ("short" if c[i] < w_l else None)
        if side is None:
            i += 1
            continue
        vol_ratio = v[i] / vs[i] if vs[i] > 0 else np.nan
        entry = c[i]
        stop = (min(w_l, e50[i]) - STOP_BUFFER_ATR * a[i]) if side == "long" \
            else (max(w_h, e50[i]) + STOP_BUFFER_ATR * a[i])
        risk = abs(entry - stop)
        if risk <= 0 or not np.isfinite(vol_ratio):
            i += 1
            continue
        # 5min EMA alignment at breakout (spread in ATR)
        if side == "long":
            aligned = e9[i] > e21[i] > e50[i] and min(e9[i] - e21[i], e21[i] - e50[i]) / a[i] >= EMA_SPREAD_MIN_5M
        else:
            aligned = e50[i] > e21[i] > e9[i] and min(e21[i] - e9[i], e50[i] - e21[i]) / a[i] >= EMA_SPREAD_MIN_5M
        # walk forward to EOD: +1R before stop?
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
        out.append(dict(ts=day.index[i], side=side, vol_ratio=vol_ratio,
                        aligned=aligned, outcome=outcome, mfe=round(mfe, 2)))
        i += COMPRESS_BARS  # skip overlapping windows
    return out


def main() -> None:
    df5 = load_5min()
    daily = daily_stack(load_daily())

    df5["ema9"], df5["ema21"], df5["ema50"] = ema(df5.close, 9), ema(df5.close, 21), ema(df5.close, 50)
    df5["atr14"] = atr(df5)
    df5["vol_sma"] = df5.volume.rolling(VOL_SMA).mean()

    events = []
    for d, day in df5.groupby(df5.index.date):
        if len(day) < COMPRESS_BARS + VOL_SMA:
            continue
        events += find_breakouts(day)
    ev = pd.DataFrame(events)

    lines = [f"# Study 01 — volume breakout follow-through (H3) — {datetime.now():%Y-%m-%d}",
             "",
             f"Data: SPY 5min RTH {df5.index[0].date()} .. {df5.index[-1].date()} "
             f"({df5.index.normalize().nunique()} days, {len(df5)} bars)",
             f"Defaults: compress={COMPRESS_BARS} bars <= {COMPRESS_RANGE_ATR}xATR14, "
             f"vol_mult={VOL_MULT}, stop=min(window_low,EMA50)-{STOP_BUFFER_ATR}xATR",
             "", f"Total compression breakouts: {len(ev)}", ""]

    def bucket_stats(sub: pd.DataFrame, label: str) -> str:
        if not len(sub):
            return f"| {label} | 0 | - | - | - |"
        n = len(sub)
        wins = (sub.outcome == "target1r").sum()
        stops = (sub.outcome == "stop").sum()
        return (f"| {label} | {n} | {wins/n*100:.0f}% | {stops/n*100:.0f}% | "
                f"{sub.mfe.median():.2f} |")

    for title, pop in [("All breakouts", ev),
                       ("5min-EMA-aligned only", ev[ev.aligned])]:
        lines += [f"## {title}", "",
                  "| population | n | +1R before stop | stopped | median MFE (R) |",
                  "|---|---|---|---|---|",
                  bucket_stats(pop[pop.vol_ratio >= VOL_MULT], f"volume >= {VOL_MULT}x"),
                  bucket_stats(pop[pop.vol_ratio < VOL_MULT], f"volume < {VOL_MULT}x"), ""]
        # finer buckets
        lines += ["| vol_ratio bucket | n | +1R before stop | stopped | median MFE (R) |",
                  "|---|---|---|---|---|"]
        for lo, hi in [(0, 1.0), (1.0, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 99)]:
            lines.append(bucket_stats(pop[(pop.vol_ratio >= lo) & (pop.vol_ratio < hi)],
                                      f"{lo}-{hi if hi < 99 else 'inf'}"))
        lines.append("")

    # EMA alignment feasibility
    dk = daily.loc[daily.index >= df5.index[0].normalize()]
    lines += ["## EMA alignment frequency (feasibility)", "",
              f"- Daily stack (known at open, spread >= {EMA_SPREAD_MIN_D} ATR): "
              f"bull {dk.bull_known.mean()*100:.0f}% / bear {dk.bear_known.mean()*100:.0f}% "
              f"/ chop {(~(dk.bull_known | dk.bear_known)).mean()*100:.0f}% of {len(dk)} days"]
    al5 = []
    for side in ("long", "short"):
        if side == "long":
            ok = (df5.ema9 > df5.ema21) & (df5.ema21 > df5.ema50) & \
                 (pd.concat([df5.ema9 - df5.ema21, df5.ema21 - df5.ema50], axis=1).min(axis=1) / df5.atr14 >= EMA_SPREAD_MIN_5M)
        else:
            ok = (df5.ema50 > df5.ema21) & (df5.ema21 > df5.ema9) & \
                 (pd.concat([df5.ema21 - df5.ema9, df5.ema50 - df5.ema21], axis=1).min(axis=1) / df5.atr14 >= EMA_SPREAD_MIN_5M)
        al5.append(f"{side} {ok.mean()*100:.0f}%")
    lines.append(f"- 5min stack aligned+spread: {' / '.join(al5)} of bars")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    ev.to_csv(OUT.with_suffix(".csv"), index=False)
    print("\n".join(lines))
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
