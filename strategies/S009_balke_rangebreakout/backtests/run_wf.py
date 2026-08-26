"""
s09 — Walk-forward ancré + bras témoin, par instrument.

Grille FIGÉE dans research/FALSIFICATION.md (avant tout backtest).
`engine_kwargs` (sortie 18h/19h via max_hold_bars, cooldown 0, pas de circuit
breaker — fidélité source) est transmis à run_walk_forward ET à
attach_control_arm : le témoin rejoue le même dispositif de risque.

Usage : python strategies/s09_balke_rangebreakout/backtests/run_wf.py [SYMBOL]
Sortie : backtests/anchored_wf_<sym>.txt
"""
from __future__ import annotations

import os
import pickle
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward, attach_control_arm  # noqa: E402
from core.backtest.engine import InstrumentSpec                              # noqa: E402
from core.data.instruments import get_spec                                   # noqa: E402
from core.data.source import CACHE_DIR                                       # noqa: E402
from strategies.s09_balke_rangebreakout.strategy import Strategy             # noqa: E402

HERE = os.path.dirname(__file__)

# ── configuration par instrument (réglages tradés de la source, pas un balayage)
GRIDS = {
    "USDJPY": dict(
        param_grid={
            "range_start_hour": [3],
            "range_end_hour": [5, 6],
            "sl_mode": ["range", "pct_entry", "pct_range"],
            "breakouts": [1, 2],
            "range_filter_pct": [None, (0.2, 0.4)],
        },
        engine_kwargs=dict(max_hold_bars=11, cooldown_bars=0, cb_losses=999),
    ),
    "XAUUSD": dict(
        param_grid={
            "range_start_hour": [3],
            "range_end_hour": [6],
            "sl_mode": ["range", "pct_entry", "pct_range"],
            "breakouts": [1],
            "range_filter_pct": [None, (0.15, 0.85)],
        },
        engine_kwargs=dict(max_hold_bars=12, cooldown_bars=0, cb_losses=999),
    ),
    "GBPUSD": dict(   # F5 : réplication de SA config, pas une optimisation
        param_grid={
            "range_start_hour": [4],
            "range_end_hour": [11, 12],
            "sl_mode": ["range"],
            "breakouts": [1],
            "range_filter_pct": [None],
        },
        engine_kwargs=dict(max_hold_bars=5, cooldown_bars=0, cb_losses=999),
    ),
    "EURJPY": dict(   # témoin d'échec documenté (−2,5 k€ live)
        param_grid={
            "range_start_hour": [3],
            "range_end_hour": [6],
            "sl_mode": ["range"],
            "breakouts": [1],
            "range_filter_pct": [None],
        },
        engine_kwargs=dict(max_hold_bars=11, cooldown_bars=0, cb_losses=999),
    ),
}

DEFAULT_LABEL = ("breakouts1_range_end_hour6_range_filter_pctNone_"
                 "range_start_hour3_sl_moderange")


def load_bars(symbol: str) -> pd.DataFrame:
    with open(os.path.join(CACHE_DIR, f"{symbol}_H1_1855d.pkl"), "rb") as f:
        df = pickle.load(f)
    zero = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    return df[~zero]


def spec_for(symbol: str, df: pd.DataFrame) -> InstrumentSpec:
    if symbol == "GBPUSD":
        sp = float(df["spread"].median()) / 10.0   # points MT5 (5 déc.) -> pips
        return InstrumentSpec(symbol="GBPUSD", pip=0.0001, spread_pips=round(sp, 1),
                              max_spread_pips=round(3 * sp, 1), pip_value_per_lot=10.0)
    return get_spec(symbol)


def exit_stats(report) -> str:
    """Distribution des heures et raisons de sortie de la config par défaut —
    validation de l'approximation max_hold_bars (dégradation déclarée n°2)."""
    for r in report.results:
        if r.label == DEFAULT_LABEL or len(report.results) == 1:
            trades = [t for w in r.windows for t in w.test.trades]
            if r.full_sample:
                trades = r.full_sample.trades or trades
            if not trades:
                return "  (aucun trade)"
            hrs = pd.Series([t.exit_time.hour for t in trades if t.exit_time])
            reasons = pd.Series([t.exit_reason for t in trades])
            eh = hrs.value_counts().sort_index()
            er = reasons.value_counts()
            return (f"  sorties (config défaut, plein échantillon, {len(trades)} trades)\n"
                    f"    par raison : {dict(er)}\n"
                    f"    heure de sortie : méd {hrs.median():.0f}h, p10 "
                    f"{hrs.quantile(.1):.0f}h, p90 {hrs.quantile(.9):.0f}h\n"
                    f"    part des sorties 17-19h : "
                    f"{100 * hrs.between(17, 19).mean():.0f} %")
    return ""


def run_symbol(symbol: str) -> None:
    cfg = GRIDS[symbol]
    bars = load_bars(symbol)
    spec = spec_for(symbol, bars)
    strat = Strategy()
    print(f"=== {symbol} : {len(bars)} barres, spread {spec.spread_pips} pips ===")

    report = run_walk_forward(strat, bars, spec,
                              param_grid=cfg["param_grid"],
                              engine_kwargs=cfg["engine_kwargs"])

    # témoin : config par défaut (F1) + top-3 OOS + top STRICT/TIER1
    chosen, seen = [], set()
    pool = ([r for r in report.results if r.label == DEFAULT_LABEL]
            + report.strict()[:3] + report.tier1()[:3]
            + sorted(report.results, key=lambda r: -r.avg_oos)[:3])
    for r in pool:
        if id(r) not in seen:
            seen.add(id(r))
            chosen.append(r)
    attach_control_arm(report, bars, spec, configs=chosen,
                       engine_kwargs=cfg["engine_kwargs"])

    txt = report.render(top=8)
    txt += "\n\n--- SORTIE TEMPORELLE : validation de l'approximation ---\n"
    txt += exit_stats(report) + "\n"
    txt += "\n--- TÉMOIN PAR CONFIG (toutes les configs armées) ---\n"
    for r in chosen:
        if r.control is not None:
            txt += (f"  {r.label:<60} honest_r {r.honest_r:>+8.2f} "
                    f"({r.total_test_trades} trades OOS)\n      {r.control.line()}\n")

    out = os.path.join(HERE, f"anchored_wf_{symbol}.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write((txt + f"\n-> {out}\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    syms = sys.argv[1:] or list(GRIDS)
    for s in syms:
        run_symbol(s)
