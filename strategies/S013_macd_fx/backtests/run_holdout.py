# -*- coding: utf-8 -*-
"""
s13 — F7 : OUVERTURE UNIQUE DU HOLD-OUT SCELLÉ (2025-02-16 → 2026-08-15).

À N'EXÉCUTER QU'UNE FOIS, sur la liste close de candidates écrite au VERDICT
AVANT l'exécution. Tout run supplémentaire après lecture des chiffres serait
une falsification du protocole (FALSIFICATION.md §HOLD-OUT).

Pour chaque candidate :
  * warmup rejoué : les barres chargées commencent 300 barres avant le sceau,
    seuls les trades ENTRÉS >= 2025-02-16 comptent (même méthode que s12 F4) ;
  * R/trade net (spread catalogue + slippage 0,5) — seuil > 0 ;
  * témoin hold-out : `control_arm` (200 tirages, graine 20260816) sur la
    tranche scellée, dispositif de risque copié des trades hold-out — seuil
    percentile >= 90 ;
  * lecture coût nul (information, pas critère).

Usage : python strategies/s13_macd_fx/backtests/run_holdout.py
Sortie : backtests/holdout.txt
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import control_arm                        # noqa: E402
from core.backtest.engine import BacktestResult, run as run_engine       # noqa: E402
from core.data.instruments import get_spec                               # noqa: E402
from core.data.source import load_bars                                   # noqa: E402
from strategies.S013_macd_fx.strategy import Strategy                     # noqa: E402

HERE = os.path.dirname(__file__)
SEAL = pd.Timestamp("2025-02-16")
CUT = pd.Timestamp("2026-08-16")
SLIPPAGE = 0.5
LEAD = 300     # barres de warmup rejouées avant le sceau

# LISTE CLOSE — figée et commitée AVANT toute exécution de ce script.
# Sélection par la règle du FALSIFICATION (percentile puis R/t OOS, survivantes
# F1-F6 — détail backtests/candidates.txt). Aucun ajout après ouverture.
EK = dict(cooldown_bars=0, cb_losses=999)
CANDIDATES: list[tuple] = [
    ("EURJPY", dict(family="ext", direction="long", lookback=252, q=0.10,
                    exit="atr_1.5_1.5"), EK),   # pct 100, F2-F4 pass, F8 +0.021
    ("AUDCAD", dict(family="ext", direction="long", lookback=252, q=0.10,
                    exit="atr_1.5_1.5"), EK),   # pct 100, F2-F4 pass, F8 +0.020
    ("EURCHF", dict(family="mr", direction="short", n_down=3,
                    range_filter=True, exit="sym3"), EK),  # pct 100, F8 -0.027
]


def rpt(res):
    if not res.n_trades:
        return "0 trade"
    return (f"{res.n_trades:>4} tr, {res.total_r:>+8.2f} R, "
            f"{res.total_r/res.n_trades:>+8.4f} R/t, WR {res.win_rate:.1f} %")


def run_candidate(pair, params, ek, L):
    bars_all = load_bars(pair, "D1", days=7300, max_age_hours=10**9)
    bars_all = bars_all[bars_all.index < CUT]
    i_seal = int(np.searchsorted(bars_all.index, SEAL))
    bars = bars_all.iloc[max(0, i_seal - LEAD):]

    st = Strategy()
    st._symbol = pair
    full = dict(st.params)
    full.update(params)
    data = st.precompute(bars, full)
    sigs = st.generate_signals(data, full, len(bars))

    def run_with(spec):
        res_all = run_engine(sigs, bars, spec, end_idx=len(bars), **ek)
        keep = [t for t in res_all.trades if pd.Timestamp(t.entry_time) >= SEAL]
        return BacktestResult(trades=keep)

    spec = replace(get_spec(pair), slippage_pips=SLIPPAGE)
    spec0 = replace(get_spec(pair), spread_pips=0.0, slippage_pips=0.0)
    res = run_with(spec)
    res0 = run_with(spec0)

    L.append("=" * 90)
    L.append(f"HOLD-OUT {pair} / {params}")
    L.append(f"  net    : {rpt(res)}")
    L.append(f"  coût 0 : {rpt(res0)} (information)")

    rpt_net = res.total_r / res.n_trades if res.n_trades else float("nan")
    ok_net = res.n_trades > 0 and rpt_net > 0

    # Témoin sur la tranche scellée seule (les barres >= SEAL).
    sl = bars_all.iloc[i_seal:]
    arm = control_arm(sl, spec, res.trades, res.total_r,
                      engine_kwargs=ek) if res.n_trades else None
    if arm is not None:
        L.append(f"  {arm.line()}")
        ok_arm = arm.percentile >= 90
    else:
        L.append("  témoin : impossible (effectif insuffisant)")
        ok_arm = False

    verdict = "F7 PASSE" if (ok_net and ok_arm) else "F7 DÉCLENCHÉE"
    L.append(f"  -> {verdict} (net>0 : {ok_net}, percentile>=90 : {ok_arm})")
    L.append("")


def main():
    if not CANDIDATES:
        raise SystemExit("Liste de candidates vide — à figer au VERDICT avant exécution.")
    L = []
    for pair, params, ek in CANDIDATES:
        run_candidate(pair, params, ek, L)
    txt = "\n".join(L)
    with open(os.path.join(HERE, "holdout.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write((txt + "\n-> holdout.txt\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
