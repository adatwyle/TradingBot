# -*- coding: utf-8 -*-
"""
s13 — instruction des cellules pré-candidates (EXPLORATION uniquement).

Pour chaque cellule listée dans CANDIDATES (sélectionnées par la règle écrite
du FALSIFICATION §Règle, sur explore_summary.csv) :
  F2 — espérance à spread nul (plein échantillon exploration)
  F3 — voisinage : cellules à un cran (ordinal : valeur adjacente ;
       catégoriel : toute autre valeur), même famille/sens — % OOS>0 et médiane
  F4 — multi-graines : témoin rejoué 5 graines (20260816+k)
  F8 — transfert à froid sur les 8 autres paires (R/trade plein échantillon,
       poolé, coûts réels)

Usage : python strategies/s13_macd_fx/backtests/run_candidates.py
Sortie : backtests/candidates.txt
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import (                                  # noqa: E402
    run_walk_forward, attach_control_arm)
from core.backtest.engine import run as run_engine                       # noqa: E402
from core.data.instruments import get_spec                               # noqa: E402
from core.data.source import load_bars                                   # noqa: E402
from strategies.S013_macd_fx.strategy import Strategy                     # noqa: E402

HERE = os.path.dirname(__file__)
SEAL = pd.Timestamp("2025-02-16")
SLIPPAGE = 0.5
PAIRS = ["EURUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
         "EURJPY", "CHFJPY", "EURCHF", "AUDCAD"]

# Rempli APRÈS lecture de explore_summary.csv, par la règle écrite d'avance :
# cellules éligibles à percentile >= 95, classées percentile DESC puis R/t OOS
# DESC ; on instruit les 6 premières (F2/F3/F4/F8), les 3 premières
# SURVIVANTES deviennent la liste close du hold-out.
# Chaque entrée : (pair, run_name, params_dict, engine_kwargs)
EK = dict(cooldown_bars=0, cb_losses=999)
CANDIDATES: list[tuple] = [
    ("EURJPY", "C_ext", dict(family="ext", direction="long", lookback=252,
                             q=0.10, exit="atr_1.5_1.5"), EK),          # pct 100.0, +0.2069
    ("AUDCAD", "C_ext", dict(family="ext", direction="long", lookback=252,
                             q=0.10, exit="atr_1.5_1.5"), EK),          # pct 100.0, +0.1984
    ("EURCHF", "A_mr", dict(family="mr", direction="short", n_down=3,
                            range_filter=True, exit="sym3"), EK),       # pct 100.0, +0.0865
    ("EURCHF", "C_ext", dict(family="ext", direction="long", lookback=252,
                             q=0.10, exit="sym3"), EK),                 # pct 100.0, +0.0599
    ("EURJPY", "C_ext", dict(family="ext", direction="short", lookback=126,
                             q=0.10, exit="atr_1.5_1.5"), EK),          # pct 99.5, +0.2011
    ("EURJPY", "C_ext", dict(family="ext", direction="long", lookback=126,
                             q=0.10, exit="atr_1.5_1.5"), EK),          # pct 99.5, +0.1889
]

ORDINAL = {"n_down": [3, 4, 5], "lookback": [126, 252], "q": [0.05, 0.10]}
GRIDS = {
    "A_mr": dict(n_down=[3, 4, 5], range_filter=[False, True],
                 exit=["sym3", "sym10", "atr_1.5_1.5", "atr_2_3"]),
    "B_cross": dict(trigger=["sig", "zero"], exit=["atr_1.5_1.5", "atr_2_3"]),
    "B_hold": dict(trigger=["sig", "zero"], exit=["hold20_sl3"]),
    "C_ext": dict(lookback=[126, 252], q=[0.05, 0.10],
                  exit=["sym3", "atr_1.5_1.5", "atr_2_3"]),
}


def explo(pair):
    df = load_bars(pair, "D1", days=7300, max_age_hours=10**9)
    return df[df.index < SEAL]


def full_run(pair, params, ek, zero_cost=False):
    bars = explo(pair)
    spec = get_spec(pair)
    spec = replace(spec, slippage_pips=0.0 if zero_cost else SLIPPAGE,
                   spread_pips=0.0 if zero_cost else spec.spread_pips)
    st = Strategy()
    st._symbol = pair
    full = dict(st.params)
    full.update(params)
    data = st.precompute(bars, full)
    sigs = st.generate_signals(data, full, len(bars))
    return run_engine(sigs, bars, spec, end_idx=len(bars), **ek)


def rpt(res):
    if not res.n_trades:
        return "0 trade"
    return (f"{res.n_trades:>4} tr, {res.total_r:>+8.2f} R, "
            f"{res.total_r/res.n_trades:>+8.4f} R/t, WR {res.win_rate:.1f} %")


def neighbors_of(run_name, params):
    """Cellules à un cran : un seul paramètre bouge (ordinal = adjacent)."""
    out = []
    grid = GRIDS[run_name]
    for k, values in grid.items():
        cur = params[k]
        if k in ORDINAL:
            vs = ORDINAL[k]
            i = vs.index(cur)
            alts = [vs[j] for j in (i - 1, i + 1) if 0 <= j < len(vs)]
        else:
            alts = [v for v in values if v != cur]
        for v in alts:
            q = dict(params)
            q[k] = v
            out.append(q)
    return out


def main():
    csv = pd.read_csv(os.path.join(HERE, "explore_summary.csv"))
    L = []

    def echo(s=""):
        print(s, flush=True)
        L.append(s)

    for pair, run_name, params, ek in CANDIDATES:
        echo("=" * 90)
        echo(f"CANDIDATE {pair} / {run_name} / {params}")
        echo("=" * 90)

        # ── F2 : coût nul, plein échantillon exploration ────────────────────
        r_real = full_run(pair, params, ek, zero_cost=False)
        r_zero = full_run(pair, params, ek, zero_cost=True)
        echo(f"F2 réel   : {rpt(r_real)}")
        echo(f"F2 coût 0 : {rpt(r_zero)}")
        f2 = (r_zero.total_r / max(r_zero.n_trades, 1)) > 0
        echo(f"F2 {'PASSE' if f2 else 'DÉCLENCHÉE (R/t <= 0 à coût nul)'}")

        # ── F3 : voisinage depuis le CSV d'exploration ──────────────────────
        sub = csv[(csv.pair == pair) & (csv.run == run_name)
                  & (csv.direction == params["direction"])]
        by_params = {}
        for _, row in sub.iterrows():
            p = ast.literal_eval(row["params"])
            key = tuple(sorted((k, p[k]) for k in GRIDS[run_name]))
            by_params[key] = row
        neigh = []
        for q in neighbors_of(run_name, params):
            key = tuple(sorted((k, q[k]) for k in GRIDS[run_name]))
            if key in by_params:
                neigh.append(by_params[key])
        pos = [n for n in neigh if float(n["honest_r"]) > 0]
        med = float(np.median([float(n["oos_rpt"]) for n in neigh])) if neigh else np.nan
        echo(f"F3 voisinage : {len(pos)}/{len(neigh)} voisins OOS>0, "
             f"médiane R/t OOS voisins {med:+.4f}")
        for n in neigh:
            echo(f"    {n['label']:<62} honest {float(n['honest_r']):+7.2f} "
                 f"({int(n['oos_trades'])} tr, {float(n['oos_rpt']):+.4f} R/t)")
        f3 = neigh and len(pos) >= 0.5 * len(neigh) and med >= 0
        echo(f"F3 {'PASSE' if f3 else 'DÉCLENCHÉE'}")

        # ── F4 : multi-graines sur le témoin OOS ────────────────────────────
        bars = explo(pair)
        spec = replace(get_spec(pair), slippage_pips=SLIPPAGE)
        st = Strategy()
        st._symbol = pair
        grid1 = {k: [v] for k, v in params.items()}
        grid1["family"] = [params["family"]]
        report = run_walk_forward(st, bars, spec, param_grid=grid1,
                                  min_trades=60, verbose=False, engine_kwargs=ek)
        cell = report.results[0]
        pcts = []
        for k in range(5):
            attach_control_arm(report, bars, spec, configs=[cell],
                               seed=20260816 + k, engine_kwargs=ek, verbose=False)
            pcts.append(cell.control.percentile if cell.control else np.nan)
        n95 = sum(1 for p in pcts if p >= 95)
        echo(f"F4 graines : percentiles {[round(p,1) for p in pcts]} -> {n95}/5 >= 95")
        echo(f"F4 {'PASSE' if n95 >= 4 else 'DÉCLENCHÉE'}")

        # ── F8 : transfert à froid, 8 autres paires ─────────────────────────
        tot_r = tot_n = 0.0
        for other in PAIRS:
            if other == pair:
                continue
            res = full_run(other, params, ek, zero_cost=False)
            tot_r += res.total_r
            tot_n += res.n_trades
            echo(f"F8 {other} : {rpt(res)}")
        pooled = tot_r / tot_n if tot_n else float("nan")
        echo(f"F8 poolé hors {pair} : {tot_n:.0f} tr, {pooled:+.4f} R/t "
             f"-> {'OK' if pooled > -0.05 else 'SUSPICION sélection de paire'}")
        echo()

    with open(os.path.join(HERE, "candidates.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("-> candidates.txt")


if __name__ == "__main__":
    main()
