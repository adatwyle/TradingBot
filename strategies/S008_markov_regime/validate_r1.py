"""
R1 POUR LE CONTRAT D'ALLOCATION — s08_markov_regime
====================================================

POURQUOI CE FICHIER PLUTÔT QU'UN APPEL AU GARDIEN DE `core/`
--------------------------------------------------------------
`python -m core.validation.causality --strategy s08_markov_regime` **ne peut pas
s'exécuter**. Ce n'est pas un contournement, c'est une limite du gardien,
démontrée par exécution dans `demonstrate_core_gap()` :

  1. `causality.main()` lit `m.symbols[0]` ; `AllocationManifest` n'a pas de
     champ `symbols` (il a `universe`).
  2. `causality.check()` appelle `precompute(df, params)` avec UN DataFrame puis
     `generate_signals(...)` ; le contrat d'allocation expose
     `precompute(bars: dict, params)` et `generate_allocations(...)`.

Le docstring de `core/contracts/allocation.py` affirme pourtant que
« `core/validation/causality.py` sait tester les deux contrats ». C'est faux à ce
jour. Constat signalé, non corrigé : l'interdiction de toucher à `core/` tient.
Même lacune que celle relevée par s07 — elle n'a donc pas été traitée depuis.

LES QUATRE COUCHES, ET LA SURFACE EXACTE QU'ELLES COUVRENT
------------------------------------------------------------
Un « R1 passé » ne vaut que la surface couverte. Elle est donc énumérée.

  Couche 0  Ce que `core/` couvre réellement ici (rien, et on le montre)
  Couche 1  INDICATEURS — `core.validation.causality._compare_precompute`,
            la primitive de `core/`, pas une réécriture. Elle n'inspecte que si
            `precompute()` rend un `pd.DataFrame` : c'est le piège documenté
            (un dict passe au travers en silence). Notre `precompute()` rend
            donc un DataFrame plat, et le rapport liste les colonnes comparées.
  Couche 2  DÉCISIONS — invariant de troncature transposé aux allocations.
  Couche 3  SÉRIES SHORT SYNTHÉTIQUES — leur construction doit elle aussi être
            causale, sinon la fuite entre par les données et non par le code.

  Couche 4  CONTRE-ÉPREUVE — une fuite est injectée volontairement. Si le test
            ne la voit pas, il ne prouve rien sur le reste. Un test de causalité
            qu'on n'a jamais vu échouer n'est pas un test.

CE QUI N'EST PAS COUVERT ICI
-----------------------------
Le moteur `run_allocation` lui-même : couvert par
`tests/test_allocation_engine.py`, dans `core/`. On s'appuie dessus, on ne le
re-teste pas.

USAGE
-----
    python -m strategies.s08_markov_regime.validate_r1
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.validation.causality import _compare_precompute
from strategies.s08_markov_regime import markov as mk
from strategies.s08_markov_regime.run_backtest import (
    build_short_series, load_universe, with_shorts,
)
from strategies.s08_markov_regime.strategy import Strategy, is_short_symbol

CUTS = (0.60, 0.70, 0.80, 0.90)
SYMBOLS = ["SP500", "BTCUSD"]


# ─────────────────────────────────────────────────────────────────────────────
def demonstrate_core_gap() -> list[str]:
    L = ["COUCHE 0 — CE QUE LE GARDIEN DE core/ COUVRE RÉELLEMENT ICI", "-" * 88]
    s = Strategy()
    m = s.manifest()
    L.append(f"  `manifest.symbols` existe : {hasattr(m, 'symbols')}"
             f"   (le CLI de core/ le lit -> AttributeError)")
    L.append(f"  `generate_signals` présent : {hasattr(s, 'generate_signals')}"
             f"   (l'invariant de core/ l'appelle)")
    L.append("  CONSÉQUENCE : le CLI `python -m core.validation.causality` est")
    L.append("  INAPPLICABLE. La couverture ci-dessous vient de ce fichier, qui")
    L.append("  réutilise la primitive `_compare_precompute` de core/ en couche 1.")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
def layer1_indicators(bars: dict[str, pd.DataFrame], params: dict) -> tuple[list[str], bool]:
    L = ["COUCHE 1 — INDICATEURS (primitive de core/)", "-" * 88]
    s = Strategy(params=params, universe=sorted(bars))
    full = s.precompute(bars, s.params)
    L.append(f"  precompute() rend : {type(full).__name__}"
             f"  ({'inspecté par core/' if isinstance(full, pd.DataFrame) else 'OPAQUE — NON inspecté'})")
    L.append(f"  colonnes réellement comparées ({len(full.columns)}) : "
             f"{', '.join(full.columns)}")
    L.append("")
    n = len(full)
    ok = True
    L.append(f"  {'coupure':>8} {'T':>7}  verdict")
    L.append("  " + "-" * 60)
    for f in CUTS:
        T = int(n * f)
        trunc = s.precompute({k: v.iloc[:T].copy() for k, v in bars.items()}, s.params)
        leaks = _compare_precompute(full, trunc, T, f)
        if leaks:
            ok = False
            L.append(f"  {f:>7.0%} {T:>7}  *** FUITE ***")
            for lk in leaks[:6]:
                dev = f"{lk.max_deviation:.3e}" if np.isfinite(lk.max_deviation) else "NaN"
                L.append(f"           {lk.column:<18} écart {dev} sur "
                         f"{lk.n_affected}/{lk.n_compared} points "
                         f"(dont NaN : {lk.n_nan_mismatch}), portée {lk.reach_bars} b")
        else:
            L.append(f"  {f:>7.0%} {T:>7}  OK")
    L.append("")
    return L, ok


# ─────────────────────────────────────────────────────────────────────────────
def layer2_decisions(bars: dict[str, pd.DataFrame], params: dict) -> tuple[list[str], bool]:
    L = ["COUCHE 2 — DÉCISIONS (invariant de troncature sur les allocations)", "-" * 88]
    L.append("    generate_allocations(precompute(bars),     p, T)")
    L.append("        ==")
    L.append("    generate_allocations(precompute(bars[:T]), p, T)")
    L.append("")
    base = {k: v for k, v in bars.items() if not is_short_symbol(k)}
    s = Strategy(params=params, universe=sorted(base))
    full = s.precompute(base, s.params)
    n = len(full)
    ok = True
    L.append(f"  {'coupure':>8} {'T':>7} {'allocs A':>9} {'allocs B':>9}  verdict")
    L.append("  " + "-" * 70)
    for f in CUTS:
        T = int(n * f)
        if T <= s.manifest().warmup_bars + 10:
            continue
        a = s.generate_allocations(full, s.params, T)
        trunc = s.precompute({k: v.iloc[:T].copy() for k, v in base.items()}, s.params)
        b = s.generate_allocations(trunc, s.params, T)
        diff = _first_divergence(a, b)
        if diff:
            ok = False
            L.append(f"  {f:>7.0%} {T:>7} {len(a):>9} {len(b):>9}  *** FUITE ***")
            L.append(f"           -> {diff}")
        else:
            L.append(f"  {f:>7.0%} {T:>7} {len(a):>9} {len(b):>9}  OK")
    L.append("")
    return L, ok


def _first_divergence(a, b) -> str | None:
    if len(a) != len(b):
        return f"nombre d'allocations différent ({len(a)} vs {len(b)})"
    for i, (x, y) in enumerate(zip(a, b)):
        if pd.Timestamp(x.timestamp) != pd.Timestamp(y.timestamp):
            return f"allocation #{i} : horodatage {x.timestamp} != {y.timestamp}"
        kx = {k: round(v, 10) for k, v in x.weights.items() if v > 1e-12}
        ky = {k: round(v, 10) for k, v in y.weights.items() if v > 1e-12}
        if kx != ky:
            return f"allocation #{i} ({x.timestamp}) : poids {kx} != {ky}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
def layer3_shorts(bars: dict[str, pd.DataFrame]) -> tuple[list[str], bool]:
    L = ["COUCHE 3 — SÉRIES SHORT SYNTHÉTIQUES", "-" * 88]
    L.append("  `open_s[i]` ne doit dépendre que de barres d'indice <= i, sinon la")
    L.append("  fuite entre par les DONNÉES et pas par le code de la stratégie.")
    L.append("")
    ok = True
    for sym, df in sorted(bars.items()):
        full = build_short_series(df)["open"].to_numpy()
        worst = 0.0
        for f in CUTS:
            T = int(len(df) * f)
            tr = build_short_series(df.iloc[:T])["open"].to_numpy()
            worst = max(worst, float(np.max(np.abs(full[:T] - tr))))
        status = "OK" if worst < 1e-9 else "*** FUITE ***"
        ok = ok and worst < 1e-9
        L.append(f"  {sym:<10} écart max sur les 4 coupures : {worst:.3e}   {status}")
    L.append("")
    return L, ok


# ─────────────────────────────────────────────────────────────────────────────
def layer4_counterproof(bars: dict[str, pd.DataFrame], params: dict) -> list[str]:
    """Le test doit SAVOIR échouer. On lui donne une fuite et on vérifie qu'il la voit.

    Deux fuites injectées, de natures différentes :
      (a) une moyenne mobile CENTRÉE — écart numérique près de la coupure
      (b) une grille d'échantillonnage ancrée sur la DERNIÈRE barre au lieu de la
          première — c'est le piège n°1 documenté dans `markov.py`, et il ne
          produit aucun NaN : seule la valeur change. Une implémentation naïve
          l'écrirait sans y penser.
    """
    L = ["COUCHE 4 — CONTRE-ÉPREUVE : le test voit-il une fuite injectée ?", "-" * 88]
    sym = sorted(bars)[0]
    close = bars[sym]["close"].to_numpy(dtype=float)
    idx = bars[sym].index
    n = len(close)

    def leak_centered(c):
        return pd.Series(c).rolling(21, center=True).mean().to_numpy()

    def leak_anchor_end(c):
        """Grille non recouvrante ancrée sur la FIN de la série."""
        ret = mk.rolling_return(c, 20)
        st = mk.classify(ret, 0.05, -0.05)
        # ancrage inversé : on part de la dernière barre et on remonte de 20 en 20
        rev = st[::-1]
        res = mk.markov_signal(rev, 20, causal=True)["signal"][::-1]
        return res

    for tag, fn in (("moyenne mobile centrée", leak_centered),
                    ("grille ancrée sur la FIN", leak_anchor_end)):
        full = pd.DataFrame({"x": fn(close)}, index=idx)
        seen = 0
        for f in CUTS:
            T = int(n * f)
            trunc = pd.DataFrame({"x": fn(close[:T])}, index=idx[:T])
            if _compare_precompute(full, trunc, T, f):
                seen += 1
        verdict = "DÉTECTÉE" if seen else "*** NON DÉTECTÉE — le test est aveugle ***"
        L.append(f"  {tag:<28} vue à {seen}/{len(CUTS)} coupures   {verdict}")
    L.append("")
    L.append("  Une couche 1 verte n'a de valeur que parce que ces deux fuites-ci,")
    L.append("  elles, la font rougir.")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    L = ["=" * 88, "R1 — CAUSALITÉ, s08_markov_regime (contrat allocation)", "=" * 88, ""]
    L += demonstrate_core_gap()

    all_ok = True
    for sym in SYMBOLS:
        bars = load_universe([sym])
        L.append("#" * 88)
        L.append(f"# {sym} — {len(bars[sym])} barres D1")
        L.append("#" * 88)
        L.append("")
        # Paramètres testés : le défaut, plus la variante recouvrante et la
        # variante à horizon > 1, qui empruntent des chemins de code différents.
        for tag, p in (("défaut (step=20, causal)", dict()),
                       ("step=1 (recouvrant)", dict(step=1)),
                       ("horizon=5 (P^n)", dict(horizon=5))):
            L.append(f"  ### paramètres : {tag}")
            l1, ok1 = layer1_indicators(bars, p)
            l2, ok2 = layer2_decisions(bars, dict(p, enable_shorts=True))
            L += l1 + l2
            all_ok = all_ok and ok1 and ok2

        l3, ok3 = layer3_shorts(bars)
        L += l3
        all_ok = all_ok and ok3

    L += layer4_counterproof(load_universe(["SP500"]), dict())

    L.append("=" * 88)
    L.append("VERDICT R1 : " + ("PASSÉ — aucune information future détectée sur la "
                                "surface couverte." if all_ok else
                                "ÉCHOUÉ — résultats non publiables."))
    L.append("=" * 88)
    txt = "\n".join(L)
    print(txt)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "causality.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"\n-> {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
