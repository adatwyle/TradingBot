# -*- coding: utf-8 -*-
"""
s13 — R1 (causalité, couche indicateur incluse) + R5 (conformité) sur les
données d'EXPLORATION uniquement (hold-out scellé jamais chargé ici).

Le CLI générique exige >= 2000 barres via load_bars par défaut (5 ans D1 =
~1580) : on appelle donc directement les check() des modules de validation sur
les 20 ans épinglés, ce qui est STRICTEMENT le même test, en couvrant en plus
les trois familles × deux sens au lieu des seuls défauts du manifest.

Usage : python strategies/s13_macd_fx/backtests/run_validation.py
Sorties : backtests/causality.txt, backtests/conformance.txt
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.validation import causality, conformance                     # noqa: E402
from core.data.source import load_bars                                  # noqa: E402
from strategies.S013_macd_fx.strategy import Strategy                    # noqa: E402

HERE = os.path.dirname(__file__)
SEAL = pd.Timestamp("2025-02-16")     # hold-out scellé — jamais chargé ici
CUT = pd.Timestamp("2026-08-16")

PARAM_SETS = [
    dict(family="mr", direction="long", n_down=5, exit="sym10"),
    dict(family="mr", direction="short", n_down=3, range_filter=True, exit="atr_1.5_1.5"),
    dict(family="cross", direction="long", trigger="sig", exit="atr_2_3"),
    dict(family="cross", direction="short", trigger="zero", exit="hold20_sl3"),
    dict(family="ext", direction="long", lookback=252, q=0.05, exit="sym3"),
    dict(family="ext", direction="short", lookback=126, q=0.10, exit="atr_1.5_1.5"),
]
SYMBOLS = ["EURUSD", "USDJPY", "AUDCAD"]


def explo_bars(symbol: str) -> pd.DataFrame:
    df = load_bars(symbol, "D1", days=7300, max_age_hours=10**9)
    return df[(df.index < SEAL)]


def main() -> int:
    fail = 0
    cz, cf = [], []
    for sym in SYMBOLS:
        bars = explo_bars(sym)
        for ps in PARAM_SETS:
            strat = Strategy(ps)
            strat._symbol = sym
            rep = causality.check(strat, bars, sym)
            cz.append(f"### params {ps}\n" + rep.render() + "\n")
            if not rep.ok:
                fail += 1
                print(f"[R1 FAIL] {sym} {ps}")
            else:
                print(f"[R1 ok] {sym} {ps}")
            repc = conformance.check(strat, bars, sym, n_bars=400)
            cf.append(f"### params {ps}\n" + repc.render() + "\n")
            okc = repc.ok if hasattr(repc, "ok") else not repc.divergences
            if not okc:
                fail += 1
                print(f"[R5 FAIL] {sym} {ps}")
            else:
                print(f"[R5 ok] {sym} {ps}")

    with open(os.path.join(HERE, "causality.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(cz))
    with open(os.path.join(HERE, "conformance.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(cf))
    print(f"\n{'PASS' if not fail else 'FAIL'} — {fail} échec(s). "
          f"Sorties archivées dans backtests/.")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
