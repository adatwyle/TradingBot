# -*- coding: utf-8 -*-
"""
s13 — EXPLORATION (fenêtre 2006-08 → 2025-02-15 UNIQUEMENT, hold-out scellé
jamais chargé). WF ancré 4 fenêtres + témoin apparié sur les cellules
éligibles les mieux classées, par (paire × famille × sens).

Protocole : research/FALSIFICATION.md (gel 6405c80). Coûts réels = spread
catalogue + slippage 0,5 pip par bout. engine_kwargs = cooldown 0, cb off ;
la sous-grille hold20 tourne avec max_hold_bars=20 (stratégie ET témoin).

Usage : python strategies/s13_macd_fx/backtests/run_explore.py [PAIR...]
Sorties : backtests/explore_<PAIR>.txt + backtests/explore_summary.csv (append)
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward, attach_control_arm  # noqa: E402
from core.data.instruments import get_spec                                  # noqa: E402
from core.data.source import load_bars                                      # noqa: E402
from strategies.S013_macd_fx.strategy import Strategy                        # noqa: E402

HERE = os.path.dirname(__file__)
SEAL = pd.Timestamp("2025-02-16")
SLIPPAGE = 0.5
MIN_OOS = 60          # F5
MIN_FULL = 100        # F5
TOP_ARMS = 3          # témoins par (famille-run × sens)

RUNS = [
    ("A_mr", dict(family=["mr"], direction=["long", "short"],
                  n_down=[3, 4, 5], range_filter=[False, True],
                  exit=["sym3", "sym10", "atr_1.5_1.5", "atr_2_3"]),
     dict(cooldown_bars=0, cb_losses=999)),
    ("B_cross", dict(family=["cross"], direction=["long", "short"],
                     trigger=["sig", "zero"],
                     exit=["atr_1.5_1.5", "atr_2_3"]),
     dict(cooldown_bars=0, cb_losses=999)),
    ("B_hold", dict(family=["cross"], direction=["long", "short"],
                    trigger=["sig", "zero"], exit=["hold20_sl3"]),
     dict(cooldown_bars=0, cb_losses=999, max_hold_bars=20)),
    ("C_ext", dict(family=["ext"], direction=["long", "short"],
                   lookback=[126, 252], q=[0.05, 0.10],
                   exit=["sym3", "atr_1.5_1.5", "atr_2_3"]),
     dict(cooldown_bars=0, cb_losses=999)),
]

CSV_PATH = os.path.join(HERE, "explore_summary.csv")
CSV_FIELDS = ["pair", "run", "family", "direction", "label", "params",
              "n_full", "full_r", "full_rpt", "oos_w1", "oos_w2", "oos_w3",
              "oos_w4", "honest_r", "oos_trades", "oos_rpt", "strict",
              "ctrl_pctile", "ctrl_null_med", "ctrl_null_p95", "ctrl_eff_ok",
              "ctrl_beta"]


def eligible(r) -> bool:
    return (r.total_test_trades >= MIN_OOS
            and r.full_sample is not None
            and r.full_sample.n_trades >= MIN_FULL)


def row_for(pair, run_name, r):
    fs = r.full_sample
    oos = r.oos_series + [np.nan] * (4 - len(r.oos_series))
    d = dict(
        pair=pair, run=run_name, family=r.params.get("family"),
        direction=r.params.get("direction"), label=r.label,
        params=repr({k: v for k, v in sorted(r.params.items())}),
        n_full=fs.n_trades if fs else 0,
        full_r=round(fs.total_r, 3) if fs else "",
        full_rpt=round(fs.total_r / fs.n_trades, 5) if fs and fs.n_trades else "",
        oos_w1=round(oos[0], 3), oos_w2=round(oos[1], 3),
        oos_w3=round(oos[2], 3), oos_w4=round(oos[3], 3),
        honest_r=round(r.honest_r, 3), oos_trades=r.total_test_trades,
        oos_rpt=(round(r.honest_r / r.total_test_trades, 5)
                 if r.total_test_trades else ""),
        strict=int(r.strict_pass),
        ctrl_pctile="", ctrl_null_med="", ctrl_null_p95="",
        ctrl_eff_ok="", ctrl_beta="",
    )
    if r.control is not None:
        c = r.control
        d.update(ctrl_pctile=round(c.percentile, 1),
                 ctrl_null_med=round(c.null_median, 3),
                 ctrl_null_p95=round(c.null_p95, 3),
                 ctrl_eff_ok=int(c.effectif_ok),
                 ctrl_beta=(round(c.beta_directionnel, 4)
                            if np.isfinite(c.beta_directionnel) else ""))
    return d


def run_pair(pair: str, writer) -> str:
    bars = load_bars(pair, "D1", days=7300, max_age_hours=10**9)
    bars = bars[bars.index < SEAL]
    spec = replace(get_spec(pair), slippage_pips=SLIPPAGE)
    out = [f"### {pair} — exploration {bars.index[0].date()} -> "
           f"{bars.index[-1].date()} ({len(bars)} barres), spread "
           f"{spec.spread_pips} pips + slippage {SLIPPAGE}"]

    for run_name, grid, ek in RUNS:
        strat = Strategy()
        strat._symbol = pair
        report = run_walk_forward(strat, bars, spec, param_grid=grid,
                                  min_trades=MIN_OOS, verbose=False,
                                  engine_kwargs=ek)
        # Témoins : top-3 éligibles par sens (classés avg_oos).
        chosen = []
        for d in ("long", "short"):
            pool = [r for r in report.results
                    if r.params.get("direction") == d and eligible(r)]
            pool.sort(key=lambda r: -r.avg_oos)
            chosen += pool[:TOP_ARMS]
        if chosen:
            attach_control_arm(report, bars, spec, configs=chosen,
                               engine_kwargs=ek, verbose=False)
        out.append(f"\n===== {run_name} =====")
        out.append(report.render(top=8))
        for r in report.results:
            writer.writerow(row_for(pair, run_name, r))
        print(f"  {pair} {run_name} : {report.n_configs} cellules, "
              f"{len(chosen)} témoins", flush=True)

    txt = "\n".join(out)
    path = os.path.join(HERE, f"explore_{pair}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return path


def main():
    pairs = sys.argv[1:] or ["EURUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
                             "EURJPY", "CHFJPY", "EURCHF", "AUDCAD"]
    new = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new:
            w.writeheader()
        for p in pairs:
            print(f"[{p}]", flush=True)
            path = run_pair(p, w)
            f.flush()
            print(f"  -> {path}", flush=True)


if __name__ == "__main__":
    main()
