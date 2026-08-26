"""
s12 — R1 (causalité) + R5 (conformité) sur l'historique D1 COMPLET.

Pourquoi pas les CLI `python -m core.validation.*` : leur `load_bars` par
défaut (1855 jours) ne donne que ~1300 barres D1, sous le seuil de 2000 du
balayage causalité. On appelle donc les MÊMES fonctions `check()` de core avec
l'historique MT5 profond (30 ans demandés -> 2016+ livré par Swissquote).
Aucune logique de validation n'est réécrite ici (R9).

Usage : python strategies/s12_prt_macd_meanrev/backtests/run_validation.py
Sortie : backtests/causality.txt, backtests/conformance.txt
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.data.source import load_bars                       # noqa: E402
from core.validation import causality, conformance           # noqa: E402
from strategies.S012_prt_macd_meanrev.strategy import Strategy  # noqa: E402

HERE = os.path.dirname(__file__)
DAYS = 365 * 30          # Swissquote sert 2016+ (~2770 barres D1)


def main() -> int:
    failures = 0
    for symbol in ["SP500", "NASDAQ", "DAX"]:
        df = load_bars(symbol, "D1", days=DAYS)
        if df is None or len(df) < 2000:
            print(f"[SKIP] {symbol} — données insuffisantes")
            failures += 1
            continue

        # R1 — invariant de troncature, params par défaut (le harnais WF refait
        # precompute par cellule ; l'invariant porte sur le même code).
        strat = Strategy()
        rep1 = causality.check(strat, df, symbol)
        # R5 — rejoue la queue barre par barre.
        rep5 = conformance.check(Strategy(), df, symbol)

        suffix = "" if symbol == "SP500" else f"_{symbol}"
        with open(os.path.join(HERE, f"causality{suffix}.txt"), "w", encoding="utf-8") as f:
            f.write(rep1.render())
        with open(os.path.join(HERE, f"conformance{suffix}.txt"), "w", encoding="utf-8") as f:
            f.write(rep5.render())

        print(f"=== {symbol} ({len(df)} barres) : R1 "
              f"{'OK' if rep1.ok else 'FUITE'} / R5 {'OK' if rep5.ok else 'DIVERGENT'}")
        if not rep1.ok or not rep5.ok:
            failures += 1
            print(rep1.render())
            print(rep5.render())
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
