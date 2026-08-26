"""
BUG SIGNALÉ DANS `core/backtest/allocation_engine.py` — DÉMONSTRATION
=====================================================================

**Ce fichier ne corrige rien.** L'interdiction de modifier `core/` s'applique.
Il documente et démontre, pour que la correction soit faite par qui de droit.

RÉSUMÉ
------
Le moteur attribue à une décision prise à la clôture de la barre `i` le
rendement `open[i] -> open[i+1]`. Or ce rendement commence à l'OUVERTURE du
jour `i`, donc AVANT la décision. Le moteur crédite la stratégie d'un mouvement
qu'elle ne pouvait pas capter.

Son propre docstring annonce pourtant la convention correcte :

    « Décision à la clôture de la barre i, rebalancement à l'ouverture de i+1.
      C'est la convention de la source et elle évite le lookahead d'exécution. »

Si le rebalancement a lieu à l'ouverture de `i+1`, le premier rendement
captable est `open[i+1] -> open[i+2]`, soit `rets[i+2]`. Le code applique le
poids à `rets[i+1]` :

    target.iloc[pos + 1] = ...        # ligne ~198
    port_ret = (held * rets).sum(...) # ligne ~215,  rets[i] = open[i]/open[i-1]

Il manque exactement une barre de décalage.

POURQUOI R1 NE L'ATTRAPE PAS
-----------------------------
`tests/test_allocation_engine.py::test_r1_truncature` passe, et il a raison de
passer : le résultat sur [0, T) ne dépend d'aucune barre postérieure à T. Le
défaut n'est pas une fuite depuis le futur lointain, c'est un décalage d'indice
systématique. L'invariant de troncature est aveugle à cette classe d'erreurs.

C'est la même leçon que le bug `closes[-1]` de `fast_bt_multi`, sous une autre
forme : un test vert ne couvre que ce qu'il regarde.

AMPLEUR MESURÉE SUR CETTE STRATÉGIE
------------------------------------
La stratégie entre quand le close franchit la bande haute — donc précisément
les jours de forte hausse. Le décalage lui offre gratuitement la hausse du jour
d'entrée. Sur BTCUSD + ETHUSD, 2018-2026 :

    avec le décalage (moteur tel quel)    107 278 % de rendement total
    après correction du décalage              voir backtests/anchored_wf.txt

CONTOURNEMENT APPLIQUÉ EN ATTENDANT
------------------------------------
`strategy.generate_allocations()` horodate ses allocations à `index[i+1]` au
lieu de `index[i]`. Le moteur pose alors le poids sur `held[i+2]`, ce qui donne
le rendement `open[i+1] -> open[i+2]` — la convention annoncée. Le décalage est
fait dans la stratégie, pas dans `core/`.

Ce contournement devra être RETIRÉ le jour où le moteur sera corrigé, sans quoi
le décalage s'appliquerait deux fois. `strategy.py` porte la même consigne.

USAGE
-----
    python -m strategies.s07_ionita_gaussian.bug_allocation_engine
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.allocation_engine import run_allocation
from core.backtest.engine import InstrumentSpec
from core.contracts.allocation import Allocation


def demo() -> str:
    L = []
    L.append("=" * 78)
    L.append("BUG — allocation_engine : décalage d'exécution d'une barre")
    L.append("=" * 78)
    L.append("")
    L.append("MONTAGE")
    L.append("  Prix d'OUVERTURE : 100 les jours 0-2, puis 200 à partir du jour 3.")
    L.append("  Le saut se produit donc entre la clôture du jour 2 et l'ouverture")
    L.append("  du jour 3. Aucun coût, aucun slippage.")
    L.append("")
    L.append("  Une stratégie qui décide à la CLÔTURE du jour 2 est exécutée, selon")
    L.append("  le docstring du moteur, à l'OUVERTURE du jour 3 — où le prix vaut")
    L.append("  déjà 200. Elle achète à 200, le prix reste à 200 : son gain doit")
    L.append("  être de 0 %. Tout gain positif est un mouvement qu'elle n'a pas pu")
    L.append("  capter.")
    L.append("")

    N = 10
    idx = pd.date_range("2020-01-01", periods=N, freq="D")
    opens = np.array([100.0] * 3 + [200.0] * (N - 3))
    df = pd.DataFrame({"open": opens, "high": opens, "low": opens, "close": opens},
                      index=idx)
    bars = {"AAA": df}
    specs = {"AAA": InstrumentSpec("AAA", 1.0, 0.0, 1e9, 1.0, 0.0)}

    L.append(f"  opens = {opens.astype(int).tolist()}")
    L.append("")
    L.append(f"  {'décision au close du jour':<28} {'poids appliqués':<26} "
             f"{'gain':>8}   attendu")
    L.append("  " + "-" * 76)

    rows = []
    for d in (1, 2, 3, 4):
        allocs = [Allocation(timestamp=idx[d], weights={"AAA": 1.0})]
        res = run_allocation(allocs, bars, specs, periods_per_year=365.0)
        gain = 100.0 * (float(res.equity.iloc[-1]) - 1.0)
        held = res.weights_history["AAA"].to_numpy().astype(int).tolist()
        # Exécution à l'ouverture de d+1 : on achète à opens[d+1].
        expected = 100.0 * (opens[-1] / opens[min(d + 1, N - 1)] - 1.0)
        rows.append((d, gain, expected))
        L.append(f"  {d:<28} {str(held):<26} {gain:>7.1f}% {expected:>9.1f}%")

    L.append("")
    bad = [(d, g, e) for d, g, e in rows if abs(g - e) > 1e-9]
    if bad:
        L.append("  DIVERGENCES :")
        for d, g, e in bad:
            L.append(f"    décision au close du jour {d} : le moteur crédite "
                     f"{g:.1f} % alors que l'exécution à l'ouverture du jour {d+1} "
                     f"(prix {opens[d+1]:.0f}) ne permet que {e:.1f} %.")
        L.append("")
        L.append("  DIAGNOSTIC : `target.iloc[pos + 1]` devrait être")
        L.append("  `target.iloc[pos + 2]` pour que le premier rendement subi soit")
        L.append("  open[i+1] -> open[i+2], conformément au docstring du module.")
        L.append("")
        L.append("  R1 NE VOIT RIEN : test_r1_truncature passe, et légitimement —")
        L.append("  aucune barre postérieure à T n'influence [0, T). Le défaut est")
        L.append("  un décalage systématique, invisible à l'invariant de troncature.")
        ok = False
    else:
        L.append("  Aucune divergence : le moteur applique la convention annoncée.")
        L.append("  (Si ce message apparaît, le bug a été corrigé dans core/ — il")
        L.append("   faut alors RETIRER le décalage compensatoire de strategy.py.)")
        ok = True

    L.append("=" * 78)
    return "\n".join(L), ok


def main() -> int:
    report, ok = demo()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "bug_allocation_engine.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(report.encode(enc, errors="replace").decode(enc) + "\n")
    print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
