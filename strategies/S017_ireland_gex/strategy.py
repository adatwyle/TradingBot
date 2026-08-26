"""S017 ireland_gex — StrategyModule skeleton (contract-conform, TCK-003 pending).

Encodes the full 5-condition checklist (spec-strategie.md §3.2-3.7) against the
socle contract `app/core/contracts/strategy.py` (READ-ONLY import — cc-S017
never modifies app/). The strategy becomes pluggable the moment TCK-003 lands;
nothing here depends on unshipped socle code beyond the existing contract.

EXOGENOUS DATA INTERFACE (proposal for TCK-003, kept minimal)
-------------------------------------------------------------
The platform loader joins two per-day premarket GEX columns onto the 5min bars
(constant within a trading day, from the day's premarket snapshot — R1-causal
because the snapshot exists BEFORE the open):

    gex_majors : str   e.g. "760;765"  (day's major levels, ';'-separated)
    gex_regime : str   "positive" | "negative"

Until the loader exists, `python strategy.py --selftest` exercises the module
end-to-end on the research store (C:/db/tradingBot/S017/) including a
truncation-invariant check (R1).

Rules honored: R1 causality, R2 no sizing (negative-gamma size modulation is
emitted as Signal.meta for core/risk), R3 stop mandatory, R6 stateless on_bar,
R7 manifest mirrors manifest.yaml (source of truth), R9 no private backtester.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

# READ-ONLY import of the socle contract (cloisonnement: no writes into app/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "app"))
from core.contracts.strategy import (  # noqa: E402
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Defaults mirror manifest.yaml (source of truth, R7). Ranges live there too.
DEFAULT_PARAMS: dict[str, Any] = {
    "level_major_frac": 0.50,      # used upstream by the GEX map builder
    "level_top_k": 5,
    "level_universe_pct": 2.0,
    "near_level_pct": 0.10,        # % of price = "at the level"
    "regime_mode": "net",
    "neg_gamma_size_factor": 0.5,  # metadata for core/risk (R2)
    "neg_gamma_partial_frac": 0.5,
    "ema_spread_min_5m": 0.15,
    "ema_spread_min_daily": 0.30,
    "compress_bars": 6,
    "compress_range_atr": 1.5,
    "vol_mult": 1.5,
    "vol_cap": None,               # H3b variant (spec §3.5) — None = video-faithful
    "vol_sma_bars": 20,
    "entry_cutoff_min": 0,
    "stop_buffer_atr": 0.25,
    "rr_min": 2.0,
    "eod_close": True,
}

WARMUP_BARS = 60  # EMA50 + ATR14 + volume SMA20 on 5min


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = pd.concat(
        [df["high"] - df["low"],
         (df["high"] - df["close"].shift()).abs(),
         (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


class IrelandGex(StrategyModule):
    """Day-trading SPY driven by dealer gamma-exposure levels (spec §1)."""

    STRATEGY_ID = "S017_ireland_gex"
    MAGIC_NUMBER = 130017

    # ── declaration ─────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Ireland GEX levels (SPY)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s017_ireland_gex",
            source="https://www.youtube.com/watch?v=bXVHsViQuyE",
            symbols=["SPY"],
            timeframe="M5",
            warmup_bars=WARMUP_BARS,
            param_grid={  # exploration ranges — full grid in manifest.yaml
                "vol_mult": [1.2, 1.5, 2.0, 2.5],
                "vol_cap": [None, 2.0, 2.5, 3.0],
                "compress_bars": [4, 6, 8, 12],
                "compress_range_atr": [1.0, 1.5, 2.0, 2.5],
                "near_level_pct": [0.05, 0.10, 0.20, 0.30],
            },
            default_params=dict(DEFAULT_PARAMS),
            status="RESEARCH",
            notes="Pending TCK-003 (SPY 5min loader + per-day GEX exogenous columns).",
        )

    # ── backtest path ───────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Indicators + causal daily stack + parsed GEX columns, computed once.

        `df` = 5min RTH bars (ET tz index) with columns
        open/high/low/close/volume + gex_majors + gex_regime (see header).
        Causality: every value at index i derives from data at indices <= i;
        the daily stack uses only previous CLOSED daily bars (shift 1).
        """
        d = df.copy()
        d["ema9"], d["ema21"], d["ema50"] = _ema(d.close, 9), _ema(d.close, 21), _ema(d.close, 50)
        d["atr14"] = _atr(d)
        d["vol_sma"] = d.volume.rolling(int(params["vol_sma_bars"])).mean()

        # causal daily EMA stack from the 5min series itself (previous closed day)
        daily = d[["open", "high", "low", "close"]].resample("1D").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        de9, de21, de50 = _ema(daily.close, 9), _ema(daily.close, 21), _ema(daily.close, 50)
        datr = _atr(daily)
        smin = float(params["ema_spread_min_daily"])
        bull = (de9 > de21) & (de21 > de50) & \
               (pd.concat([de9 - de21, de21 - de50], axis=1).min(axis=1) / datr >= smin)
        bear = (de50 > de21) & (de21 > de9) & \
               (pd.concat([de21 - de9, de50 - de21], axis=1).min(axis=1) / datr >= smin)
        bull_known = bull.shift(1).astype("boolean").fillna(False)
        bear_known = bear.shift(1).astype("boolean").fillna(False)
        dates = pd.Index(d.index.normalize().date if d.index.tz is None
                         else d.index.tz_localize(None).normalize().date)
        kb = pd.Series(bull_known.values, index=daily.index.date)
        ks = pd.Series(bear_known.values, index=daily.index.date)
        d["daily_bull"] = [bool(kb.get(x, False)) for x in dates]
        d["daily_bear"] = [bool(ks.get(x, False)) for x in dates]

        # parse per-day GEX columns once
        majors: list[list[float]] = []
        for v in d.get("gex_majors", pd.Series("", index=d.index)).fillna(""):
            majors.append([float(x) for x in str(v).split(";") if x not in ("", "nan")])
        d["_majors"] = majors
        if "gex_regime" not in d:
            d["gex_regime"] = ""
        return d

    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """All signals over [0, end_idx). Nothing at index >= end_idx is read (R1)."""
        out: list[Signal] = []
        d: pd.DataFrame = data.iloc[:end_idx]          # hard truncation — R1
        for i in range(WARMUP_BARS, len(d)):
            sig = self._decide(d, i, params)
            if sig is not None:
                out.append(sig)
        return out

    # ── live path ───────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """Pure function of (ctx, params) — R6. Same decision code as backtest (R5)."""
        d = self.precompute(ctx.bars, self.params)
        if len(d) <= WARMUP_BARS:
            return None
        return self._decide(d, len(d) - 1, self.params)

    # ── shared decision (single implementation → R5 conformance by design) ──
    def _decide(self, d: pd.DataFrame, i: int, params: dict) -> Optional[Signal]:
        """Evaluate the 5-condition checklist on bar i (the freshly closed bar).

        Uses ONLY rows <= i. Returns a Signal or None.
        """
        row = d.iloc[i]
        majors: list[float] = row["_majors"]
        if not majors:
            return None                                    # no map -> no trade
        atr14 = row["atr14"]
        if not np.isfinite(atr14) or atr14 <= 0 or not np.isfinite(row["vol_sma"]):
            return None

        # same-day guard: compression window must not span the prior session
        cb = int(params["compress_bars"])
        if i - cb < 0:
            return None
        win = d.iloc[i - cb:i]
        if win.index.normalize().nunique() != 1 or \
                win.index[0].date() != row.name.date():
            return None
        # entry cutoff (minutes after open)
        cutoff = int(params["entry_cutoff_min"])
        if cutoff:
            day_first = d[d.index.date == row.name.date()].index[0]
            if (row.name - day_first).total_seconds() / 60.0 < cutoff:
                return None

        # condition 4a — compression
        w_h, w_l = float(win.high.max()), float(win.low.min())
        prev_atr = d["atr14"].iloc[i - 1]
        if not np.isfinite(prev_atr) or prev_atr <= 0 or \
                (w_h - w_l) > float(params["compress_range_atr"]) * prev_atr:
            return None

        # condition 1 — compression sits AT a major GEX level
        tol = float(params["near_level_pct"]) / 100.0 * float(row.close)
        at_level = [k for k in majors if w_l - tol <= k <= w_h + tol]
        if not at_level:
            return None                                    # no man's land

        # condition 4b — breakout bar with volume in the declared window
        close = float(row.close)
        side: Optional[Side] = None
        if close > w_h:
            side = Side.LONG
        elif close < w_l:
            side = Side.SHORT
        if side is None:
            return None
        vol_ratio = float(row.volume) / float(row.vol_sma) if row.vol_sma > 0 else 0.0
        if vol_ratio < float(params["vol_mult"]):
            return None
        cap = params.get("vol_cap")
        if cap is not None and vol_ratio >= float(cap):
            return None                                    # H3b exhaustion skip

        # condition 3 — EMA stacks aligned daily + 5min, matching the side
        s5 = float(params["ema_spread_min_5m"])
        e9, e21, e50 = float(row.ema9), float(row.ema21), float(row.ema50)
        if side == Side.LONG:
            ok5 = e9 > e21 > e50 and min(e9 - e21, e21 - e50) / atr14 >= s5
            okd = bool(row["daily_bull"])
        else:
            ok5 = e50 > e21 > e9 and min(e21 - e9, e50 - e21) / atr14 >= s5
            okd = bool(row["daily_bear"])
        if not (ok5 and okd):
            return None

        # condition 5 — structural stop, target = next major else 2R, RR gate
        buf = float(params["stop_buffer_atr"]) * atr14
        if side == Side.LONG:
            stop = min(w_l, e50) - buf
            risk = close - stop
            nxt = [k for k in majors if k > close + tol]
            target = min(nxt) if nxt else close + 2 * risk
        else:
            stop = max(w_h, e50) + buf
            risk = stop - close
            nxt = [k for k in majors if k < close - tol]
            target = max(nxt) if nxt else close - 2 * risk
        if risk <= 0:
            return None
        if abs(target - close) / risk < float(params["rr_min"]):
            target = close + 2 * risk if side == Side.LONG else close - 2 * risk

        # condition 2 — regime modulates management only (metadata for core/risk, R2)
        regime = str(row.get("gex_regime", "")) or "unknown"
        meta = {
            "gex_level": at_level[0],
            "gex_regime": regime,
            "vol_ratio": round(vol_ratio, 2),
            "eod_close": bool(params["eod_close"]),
        }
        if regime == "negative":
            meta["size_factor"] = float(params["neg_gamma_size_factor"])
            meta["partial_frac_at_1r"] = float(params["neg_gamma_partial_frac"])

        return Signal(
            timestamp=row.name.to_pydatetime(),
            symbol="SPY",
            side=side,
            entry=close,
            stop=float(stop),
            target=float(target),
            reason=(f"A+ setup: {side.value} breakout of {cb}-bar compression at GEX "
                    f"{at_level[0]:.0f} ({regime}), vol {vol_ratio:.1f}x, "
                    f"EMA stacks aligned"),
            meta=meta,
        )


# ── standalone selftest on the research store (no socle loader needed) ──────
def _selftest() -> int:
    """Exercise the module on C:/db/tradingBot/S017/ data + R1 truncation check."""
    import re
    db = Path("C:/db/tradingBot/S017")
    df = pd.read_csv(db / "ohlcv" / "SPY_5min.csv", index_col=0, parse_dates=True)
    df = df.tz_convert("America/New_York").between_time("09:30", "15:55")

    # join per-day GEX columns from canonical snapshots (same as TCK-003 will do)
    majors_by_day: dict = {}
    regime_by_day: dict = {}
    for p in sorted((db / "gex").glob("SPY_gex_????-??-??.csv")):
        m = re.match(r"SPY_gex_(\d{4}-\d{2}-\d{2})\.csv$", p.name)
        if not m:
            continue
        g = pd.read_csv(p)
        day = pd.Timestamp(m.group(1)).date()
        majors_by_day[day] = ";".join(f"{k:g}" for k in g[g.is_major].strike)
        regime_by_day[day] = "positive" if g.gex.sum() > 0 else "negative"
    dates = pd.Index(df.index.tz_localize(None).normalize().date)
    df["gex_majors"] = [majors_by_day.get(x, "") for x in dates]
    df["gex_regime"] = [regime_by_day.get(x, "") for x in dates]

    strat = IrelandGex()
    data = strat.precompute(df, strat.params)
    sigs = strat.generate_signals(data, strat.params, len(data))
    print(f"[selftest] bars={len(data)}, gex days={len(majors_by_day)}, "
          f"signals={len(sigs)}")
    for s in sigs:
        print(f"  {s.timestamp} {s.side.value} entry={s.entry:.2f} stop={s.stop:.2f} "
              f"target={s.target:.2f} rr={s.rr:.2f} | {s.reason}")

    # R1 truncation invariant (spot check at 3 cut points)
    for t in (len(data) // 2, max(WARMUP_BARS + 1, len(data) - 100), len(data)):
        full = strat.generate_signals(data, strat.params, t)
        trunc = strat.generate_signals(strat.precompute(df.iloc[:t], strat.params),
                                       strat.params, t)
        a = [(s.timestamp, s.side, round(s.entry, 4)) for s in full]
        b = [(s.timestamp, s.side, round(s.entry, 4)) for s in trunc]
        assert a == b, f"R1 truncation invariant BROKEN at T={t}: {a} != {b}"
    print("[selftest] R1 truncation invariant: OK (3 cut points)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__)
