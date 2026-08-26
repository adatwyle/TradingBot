"""
R5 — COHÉRENCE BACKTEST / LIVE (contrat d'allocation)
======================================================

`core/validation/conformance.py` est, comme le gardien R1, câblé sur le contrat
épisodique. Il est inapplicable ici. Ce fichier exécute l'équivalent pour le
contrat d'allocation.

CE QUI EST VÉRIFIÉ
------------------
Pour une série de barres tronquées à `T`, la décision rendue par le chemin LIVE
(`on_bar`, qui ne voit que l'historique jusqu'à T) doit être identique à la
dernière décision du chemin BACKTEST (`generate_allocations(..., T)`).

`on_bar` est écrit pour réutiliser littéralement le chemin backtest plutôt que
de le réimplémenter en miroir — c'est le seul moyen fiable de garantir R5, dont
`STRATEGY_RULES.md` dit qu'il est « la première cause de : ça marchait en
backtest ». Ce test confirme que la réutilisation fonctionne, y compris sur la
gestion d'état du portefeuille, qui est reconstruite depuis zéro à chaque appel.

USAGE
-----
    python -m strategies.s07_ionita_gaussian.validate_r5
"""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.contracts.allocation import AllocationContext
from strategies.s07_ionita_gaussian.run_backtest import load_universe, UNIVERSE_CRYPTO
from strategies.s07_ionita_gaussian.strategy import Strategy

CUTS = (0.62, 0.71, 0.83, 0.94, 0.99)


def run() -> tuple[str, bool]:
    L = ["=" * 78, "R5 — COHÉRENCE BACKTEST / LIVE (contrat d'allocation)", "=" * 78]
    bars = load_universe(UNIVERSE_CRYPTO)
    n = len(next(iter(bars.values())))
    strat = Strategy(universe=UNIVERSE_CRYPTO)

    # CHOIX DES COUPURES — un test qui ne regarde que des barres en cash
    # comparerait des dictionnaires vides et passerait sans rien prouver. On
    # cible donc explicitement des barres où le portefeuille est INVESTI, et on
    # garde quelques barres en cash pour couvrir aussi ce cas.
    data_full = strat.precompute(bars, strat.params)
    all_allocs = strat.generate_allocations(data_full, strat.params, n)
    ts_invested = [pd.Timestamp(a.timestamp) for a in all_allocs if a.weights]
    index = bars[UNIVERSE_CRYPTO[0]].index
    invested_T = [int(index.get_loc(t)) for t in ts_invested]

    cuts_T = sorted(set(
        [int(n * f) for f in CUTS] +
        [invested_T[int(len(invested_T) * q)]
         for q in (0.10, 0.35, 0.60, 0.85, 0.97) if invested_T]
    ))
    L.append(f"  Univers {', '.join(UNIVERSE_CRYPTO)} · {n} barres D1")
    L.append(f"  {len(invested_T)} barres investies sur {len(all_allocs)} décisions ; "
             f"les coupures ciblent les deux états.")
    L.append("")
    L.append(f"  {'T':>7}  {'poids backtest':<34} {'poids live':<34} verdict")
    L.append("  " + "-" * 90)

    ok = True
    n_nonempty = 0
    for T in cuts_T:
        data = strat.precompute(bars, strat.params)
        bt = strat.generate_allocations(data, strat.params, T)
        expected = bt[-1] if bt else None

        trunc = {s: df.iloc[:T].copy() for s, df in bars.items()}
        ctx = AllocationContext(
            universe=list(UNIVERSE_CRYPTO), timeframe="D1", bars=trunc,
            now=trunc[UNIVERSE_CRYPTO[0]].index[-1], spreads={},
        )
        live = strat.on_bar(ctx)

        e = {k: round(v, 10) for k, v in (expected.weights if expected else {}).items()}
        g = {k: round(v, 10) for k, v in (live.weights if live else {}).items()}
        good = (e == g)
        ok &= good
        n_nonempty += 1 if e else 0
        L.append(f"  {T:>7}  {str(e):<34} {str(g):<34} "
                 + ("OK" if good else "*** DIVERGENCE ***"))

    L.append("")
    L.append(f"  Coupures avec portefeuille NON VIDE : {n_nonempty} / {len(cuts_T)}")
    if n_nonempty == 0:
        L.append("  *** Toutes les coupures comparent des portefeuilles vides :")
        L.append("      ce test ne prouve rien. À corriger avant de s'y fier. ***")
        ok = False
    L.append("")
    L.append("VERDICT : R5 " + ("PASSÉ." if ok else "ÉCHOUÉ."))
    if ok:
        L.append("  Le chemin live et le chemin backtest rendent la même décision.")
        L.append("  Garanti par construction : `on_bar` appelle `generate_allocations`")
        L.append("  au lieu de dupliquer la logique.")
    L.append("=" * 78)
    return "\n".join(L), ok


def main() -> int:
    report, ok = run()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "conformance.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(report.encode(enc, errors="replace").decode(enc) + "\n")
    print(f"\n  -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
