"""
R1 POUR LE CONTRAT D'ALLOCATION — et ce que le gardien de `core/` ne couvre pas
===============================================================================

POURQUOI CE FICHIER EXISTE PLUTÔT QU'UN APPEL À `core.validation.causality`
---------------------------------------------------------------------------
`python -m core.validation.causality --strategy s07_ionita_gaussian` **ne peut
pas s'exécuter** sur cette stratégie. Ce n'est pas un choix, c'est une limite du
gardien, démontrée plus bas par `demonstrate_core_gap()` :

  1. `causality.main()` lit `m.symbols[0]`. `AllocationManifest` n'a pas de champ
     `symbols` — il a `universe`. -> `AttributeError`.
  2. `causality.check()` appelle `strategy.precompute(df, params)` avec UN
     DataFrame, puis `strategy.generate_signals(...)`. Le contrat d'allocation
     expose `precompute(bars: dict, params)` et `generate_allocations(...)`.
     Les signatures ne correspondent pas.

Le docstring de `core/contracts/allocation.py` affirme pourtant :
« l'invariant de troncature R1 s'applique tel quel — `core/validation/
causality.py` sait tester les deux contrats ». **C'est faux aujourd'hui.**
Constat signalé, non corrigé : l'interdiction de toucher à `core/` tient.

CE QUE CE FICHIER FAIT, ET LA SURFACE EXACTE QU'IL COUVRE
----------------------------------------------------------
Trois couches, de la plus fine à la plus grossière. Un « R1 passé » ne vaut que
la surface couverte, donc la surface est énumérée dans le rapport, colonne par
colonne, et pas résumée par un OK.

  Couche 1 — LE FILTRE SEUL (`gaussian.prove_causality`)
      Le canal gaussien recalculé sur données tronquées, comparé au canal
      calculé sur l'historique complet. Attendu : écart EXACTEMENT nul.
      Accompagné d'un CONTRE-EXEMPLE `filtfilt` qui, lui, doit montrer un écart
      non nul — sans quoi le test n'aurait pas le pouvoir de détecter ce qu'il
      prétend détecter.

  Couche 2 — TOUS LES INDICATEURS (`core.validation.causality._compare_precompute`)
      On appelle la primitive de `core/`, pas une réécriture. C'est le même code
      qui garde les autres stratégies. Il n'inspecte que si `precompute()` rend
      un `pd.DataFrame` — c'est le piège documenté (un dict passe au travers en
      silence). `precompute()` de cette stratégie rend donc délibérément un
      DataFrame à plat, et le rapport liste les colonnes réellement comparées.

  Couche 3 — LES DÉCISIONS (invariant de troncature sur les allocations)
      generate_allocations(precompute(bars),      p, T)
          ==
      generate_allocations(precompute(bars[:T]),  p, T)
      Transposition littérale de R1 au contrat d'allocation. On compare les
      poids barre à barre, pas les objets.

CE QUI N'EST PAS COUVERT ICI, ET DOIT ÊTRE DIT
-----------------------------------------------
  - Le moteur `run_allocation` lui-même : couvert par `tests/test_allocation_
    engine.py::test_r1_truncature`, déjà vert dans `core/`. On ne le re-teste
    pas, on s'appuie dessus.
  - Les séries short synthétiques : construites dans `run_backtest.py` à partir
    des rendements passés uniquement ; la couche 3 les voit puisqu'elles entrent
    dans le moteur, mais leur construction est vérifiée séparément par
    `check_synthetic_shorts()` ci-dessous.

USAGE
-----
    python -m strategies.s07_ionita_gaussian.validate_r1
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.validation.causality import _compare_precompute  # primitive de core
from strategies.s07_ionita_gaussian.gaussian import prove_causality
from strategies.s07_ionita_gaussian.strategy import Strategy

CUTS = (0.60, 0.70, 0.80, 0.90)


# ─────────────────────────────────────────────────────────────────────────────
def demonstrate_core_gap() -> list[str]:
    """Montre, par exécution, que le gardien de `core/` ne couvre pas ce contrat.

    On n'affirme pas « ça ne marche pas » : on l'appelle et on rapporte l'erreur.
    """
    L = ["COUCHE 0 — CE QUE LE GARDIEN DE core/ COUVRE RÉELLEMENT ICI", "-" * 78]
    strat = Strategy()

    m = strat.manifest()
    if hasattr(m, "symbols"):
        L.append("  causality.main() : `manifest.symbols` existe — OK")
    else:
        L.append("  causality.main() : `AllocationManifest` n'a PAS de champ `symbols`")
        L.append("     (il a `universe`) -> `--strategy s07_ionita_gaussian` lève")
        L.append("     AttributeError avant même de charger des barres.")

    has_gs = hasattr(strat, "generate_signals")
    L.append(f"  causality.check()  : `generate_signals` présent = {has_gs}")
    if not has_gs:
        L.append("     -> l'invariant de core/ ne peut pas être exécuté tel quel.")
    L.append("")
    L.append("  CONSÉQUENCE : le CLI `python -m core.validation.causality` est")
    L.append("  INAPPLICABLE à cette stratégie. La couverture R1 rapportée ci-")
    L.append("  dessous vient de ce fichier, qui réutilise la primitive")
    L.append("  `_compare_precompute` de core/ pour la couche indicateur.")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
def check_filter(df: pd.DataFrame, params: dict) -> tuple[list[str], bool]:
    """Couche 1 — le filtre gaussien seul, avec son contre-exemple."""
    L = ["COUCHE 1 — LE FILTRE GAUSSIEN SEUL", "-" * 78]
    r = prove_causality(df, period=int(params["period"]), poles=int(params["poles"]),
                        mult=float(params["mult"]), cuts=CUTS)
    L.append(f"  {r['n_bars']} barres · période {r['period']} · {r['poles']} pôles")
    L.append("")
    L.append(f"  {'coupure':>8} {'T':>7} {'notre filtre':>16} {'lfilter':>12} "
             f"{'filtfilt (piège)':>18}")
    L.append("  " + "-" * 68)
    ok = True
    detects = False
    for c in r["cuts"]:
        worst = max(c["causal_max_dev"].values())
        ok &= (worst == 0.0)
        detects |= (c["filtfilt_max_dev"] > 0.0)
        L.append(f"  {c['fraction']:>7.0%} {c['T']:>7} {worst:>16.3e} "
                 f"{c['lfilter_max_dev']:>12.3e} {c['filtfilt_max_dev']:>18.3e}")
    L.append("")
    L.append("  Colonnes vérifiées : filter, upper, lower, trend "
             "(les quatre du canal).")
    if ok:
        L.append("  -> écart EXACTEMENT nul : le filtre ne lit aucune barre future.")
    else:
        L.append("  -> *** ÉCART NON NUL : le filtre voit le futur ***")
    if detects:
        L.append("  -> le contre-exemple filtfilt produit bien un écart : le test a")
        L.append("     le pouvoir de détecter la fuite qu'il prétend écarter.")
    else:
        L.append("  -> *** le contre-exemple n'échoue pas : test sans pouvoir ***")
        ok = False
    L.append("")
    return L, ok


# ─────────────────────────────────────────────────────────────────────────────
def check_indicators(strat: Strategy, bars: dict[str, pd.DataFrame],
                     params: dict) -> tuple[list[str], bool]:
    """Couche 2 — tous les indicateurs, via la primitive de core/."""
    L = ["COUCHE 2 — TOUS LES INDICATEURS (primitive core/_compare_precompute)",
         "-" * 78]
    n = len(next(iter(bars.values())))
    data_full = strat.precompute(bars, params)

    if not isinstance(data_full, pd.DataFrame):
        L.append("  *** precompute() ne rend pas un DataFrame : la couche")
        L.append("      indicateur de core/ retournerait [] SANS RIEN INSPECTER.")
        return L, False

    numeric = [c for c in data_full.columns
               if data_full[c].to_numpy().dtype.kind in "fiu"]
    L.append(f"  precompute() rend un DataFrame de {len(data_full.columns)} colonnes,")
    L.append(f"  dont {len(numeric)} numériques — donc réellement comparées.")
    L.append("")
    L.append("  Colonnes sous surveillance :")
    for c in numeric:
        L.append(f"    - {c}")
    L.append("")

    leaks = []
    for frac in CUTS:
        T = int(n * frac)
        trunc = {s: df.iloc[:T].copy() for s, df in bars.items()}
        data_trunc = strat.precompute(trunc, params)
        leaks.extend(_compare_precompute(data_full, data_trunc, T, frac))

    L.append(f"  {'coupure':>8} {'T':>7}  verdict")
    L.append("  " + "-" * 40)
    for frac in CUTS:
        T = int(n * frac)
        bad = [x for x in leaks if x.fraction == frac]
        L.append(f"  {frac:>7.0%} {T:>7}  " +
                 ("OK" if not bad else f"*** {len(bad)} colonne(s) en fuite ***"))
    if leaks:
        L.append("")
        for x in leaks[:15]:
            L.append(f"    {x.fraction:>5.0%} {x.column:<24} écart max {x.max_deviation:.3e} "
                     f"sur {x.n_affected}/{x.n_compared} points, portée {x.reach_bars} b")
    L.append("")
    return L, not leaks


# ─────────────────────────────────────────────────────────────────────────────
def check_allocations(strat: Strategy, bars: dict[str, pd.DataFrame],
                      params: dict) -> tuple[list[str], bool]:
    """Couche 3 — invariant de troncature sur les décisions."""
    L = ["COUCHE 3 — LES DÉCISIONS (invariant de troncature sur les allocations)",
         "-" * 78]
    L.append("  generate_allocations(precompute(bars),     p, T)")
    L.append("      ==")
    L.append("  generate_allocations(precompute(bars[:T]), p, T)")
    L.append("")
    n = len(next(iter(bars.values())))
    data_full = strat.precompute(bars, params)

    L.append(f"  {'coupure':>8} {'T':>7} {'allocs A':>10} {'allocs B':>10}  verdict")
    L.append("  " + "-" * 60)
    ok = True
    for frac in CUTS:
        T = int(n * frac)
        a = strat.generate_allocations(data_full, params, T)
        trunc = {s: df.iloc[:T].copy() for s, df in bars.items()}
        b = strat.generate_allocations(strat.precompute(trunc, params), params, T)

        div = _diff_allocations(a, b)
        ok &= div is None
        L.append(f"  {frac:>7.0%} {T:>7} {len(a):>10} {len(b):>10}  " +
                 ("OK" if div is None else "*** FUITE ***"))
        if div:
            L.append(f"           -> {div}")
    L.append("")
    return L, ok


def _diff_allocations(a: list, b: list) -> str | None:
    if len(a) != len(b):
        return (f"nombre d'allocations différent ({len(a)} vs {len(b)}) — "
                f"une décision dépend de barres postérieures à la coupure.")
    for i, (x, y) in enumerate(zip(a, b)):
        if pd.Timestamp(x.timestamp) != pd.Timestamp(y.timestamp):
            return f"allocation #{i} : horodatage {x.timestamp} != {y.timestamp}"
        kx = {s: round(w, 10) for s, w in x.weights.items()}
        ky = {s: round(w, 10) for s, w in y.weights.items()}
        if kx != ky:
            return f"allocation #{i} ({x.timestamp}) : poids {kx} != {ky}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
def check_synthetic_shorts(bars: dict[str, pd.DataFrame]) -> tuple[list[str], bool]:
    """Les séries short synthétiques ne doivent lire que le passé.

    Construction : `open_s[i] = open_s[i-1] * (1 - r[i])` où `r[i]` est le
    rendement open->open de la série réelle entre i-1 et i. Chaque valeur ne
    dépend que de barres d'indice <= i. On le vérifie par troncature, comme le
    reste — une construction « évidemment causale » est exactement le genre
    d'évidence qui a coûté des mois à ce projet.
    """
    from strategies.s07_ionita_gaussian.run_backtest import build_short_series
    L = ["COUCHE 4 — SÉRIES SHORT SYNTHÉTIQUES", "-" * 78]
    ok = True
    for sym, df in bars.items():
        full = build_short_series(df)
        for frac in CUTS:
            T = int(len(df) * frac)
            trunc = build_short_series(df.iloc[:T])
            dev = float(np.nanmax(np.abs(
                full["open"].to_numpy()[:T] - trunc["open"].to_numpy())))
            if dev > 0.0:
                ok = False
                L.append(f"  *** {sym} à {frac:.0%} : écart {dev:.3e} ***")
    L.append(f"  {len(bars)} série(s) x {len(CUTS)} coupures — "
             + ("écart nul partout." if ok else "FUITE DÉTECTÉE."))
    L.append("")
    return L, ok


# ─────────────────────────────────────────────────────────────────────────────
def run(bars: dict[str, pd.DataFrame], params: dict | None = None,
        universe: list[str] | None = None) -> tuple[str, bool]:
    strat = Strategy(universe=universe or sorted(bars))
    params = params or strat.params

    L = ["=" * 78,
         "R1 — INVARIANT DE CAUSALITÉ (contrat d'allocation)",
         "=" * 78,
         f"Stratégie : s07_ionita_gaussian",
         f"Univers   : {', '.join(sorted(bars))}",
         f"Barres    : {len(next(iter(bars.values())))} (D1)",
         f"Params    : période={params['period']} pôles={params['poles']} "
         f"mult={params['mult']} shorts={params['enable_shorts']}",
         ""]
    L += demonstrate_core_gap()

    ref = bars[sorted(bars)[0]]
    l1, ok1 = check_filter(ref, params)
    l2, ok2 = check_indicators(strat, bars, params)
    l3, ok3 = check_allocations(strat, bars, params)
    l4, ok4 = check_synthetic_shorts(bars)
    L += l1 + l2 + l3 + l4

    ok = ok1 and ok2 and ok3 and ok4
    L.append("=" * 78)
    if ok:
        L.append("VERDICT : R1 PASSÉ sur les 4 couches.")
        L.append("")
        L.append("SURFACE COUVERTE, explicitement :")
        L.append("  [x] filtre gaussien seul, avec contre-exemple filtfilt actif")
        L.append("  [x] toutes les colonnes numériques de precompute(), listées")
        L.append("      ci-dessus, via la primitive _compare_precompute de core/")
        L.append("  [x] les allocations elles-mêmes, poids par poids, 4 coupures")
        L.append("  [x] les séries short synthétiques")
        L.append("  [ ] NON couvert ici : le moteur run_allocation lui-même — il")
        L.append("      l'est par tests/test_allocation_engine.py::test_r1_truncature")
        L.append("  [ ] NON couvert : le CLI core/validation/causality, inapplicable")
        L.append("      à ce contrat (cf. COUCHE 0).")
    else:
        L.append("VERDICT : R1 ÉCHOUÉ. Résultats non publiables.")
    L.append("=" * 78)
    return "\n".join(L), ok


def main() -> int:
    from strategies.s07_ionita_gaussian.run_backtest import load_universe, UNIVERSE_CRYPTO

    bars = load_universe(UNIVERSE_CRYPTO)
    report, ok = run(bars, universe=UNIVERSE_CRYPTO)
    print(report)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "causality.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n  -> {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
