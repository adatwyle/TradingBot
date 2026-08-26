"""
R5 — CONFORMITÉ BACKTEST / LIVE, s08_markov_regime
===================================================

R5 exige que `generate_allocations()` (backtest) et `on_bar()` (live) produisent
les MÊMES décisions sur le même état de marché. C'est la première cause de « ça
marchait en backtest ».

POURQUOI CE FICHIER PLUTÔT QUE `core/validation/conformance.py`
----------------------------------------------------------------
Même lacune que pour R1 : le gardien de `core/` est câblé sur le contrat
ÉPISODIQUE (`generate_signals` / `on_bar -> Signal`). Le contrat d'allocation
expose `generate_allocations` / `on_bar -> Allocation`. Constat signalé, non
corrigé (interdiction de toucher à `core/`).

CE QUI EST REJOUÉ
-----------------
Pour chaque barre i d'une fenêtre de fin d'historique, on construit un
`AllocationContext` ne contenant QUE `bars[:i+1]` — c'est littéralement ce que
voit le processus en direct — et on compare le poids rendu par `on_bar()` au
poids en vigueur dans le chemin backtest à la même date.

La fenêtre est restreinte aux dernières barres parce que `on_bar()` recalcule
tout l'historique à chaque appel (choix délibéré : réutiliser le même code plutôt
que le réécrire, cf. docstring de `strategy.py`). Le coût est quadratique ; la
surface testée est donc déclarée, pas maquillée en « conformité totale ».

USAGE
-----
    python -m strategies.s08_markov_regime.validate_r5
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.contracts.allocation import AllocationContext
from strategies.s08_markov_regime.run_backtest import load_universe
from strategies.s08_markov_regime.strategy import Strategy

N_BARS = 250          # barres rejouées, en fin d'historique
SYMBOLS = ["SP500", "BTCUSD"]


def replay(sym: str, params: dict) -> tuple[list[str], bool]:
    bars = load_universe([sym])
    strat = Strategy(params=params, universe=[sym])
    data = strat.precompute(bars, strat.params)
    n = len(data)

    # Chemin backtest : allocation en vigueur à chaque date.
    allocs = strat.generate_allocations(data, strat.params, n)
    held: dict[pd.Timestamp, dict] = {}
    cur: dict = {}
    by_ts = {pd.Timestamp(a.timestamp): a.weights for a in allocs}
    for ts in data.index:
        if ts in by_ts:
            cur = by_ts[ts]
        held[ts] = dict(cur)

    L = [f"  {sym} — {N_BARS} dernières barres rejouées en mode live"]
    mismatches = []
    for i in range(n - N_BARS, n):
        ts = data.index[i]
        ctx = AllocationContext(
            universe=[sym], timeframe="D1",
            bars={sym: bars[sym].iloc[:i + 1].copy()},
            now=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.now(),
            spreads={sym: 0.0}, current_weights={},
        )
        live = strat.on_bar(ctx)
        wl = {k: round(v, 10) for k, v in (live.weights if live else {}).items()
              if v > 1e-12}
        wb = {k: round(v, 10) for k, v in held[ts].items() if v > 1e-12}
        if wl != wb:
            mismatches.append(f"    {ts.date()} : live {wl} != backtest {wb}")

    ok = not mismatches
    L.append(f"    désaccords : {len(mismatches)} / {N_BARS}   "
             f"{'OK' if ok else '*** R5 ÉCHOUÉ ***'}")
    L += mismatches[:10]
    if len(mismatches) > 10:
        L.append(f"    ... et {len(mismatches)-10} autres")
    L.append("")
    return L, ok


def main() -> int:
    L = ["=" * 88, "R5 — CONFORMITÉ BACKTEST / LIVE (contrat allocation)", "=" * 88, ""]
    L.append("Le CLI `core/validation/conformance.py` est câblé sur le contrat")
    L.append("ÉPISODIQUE et ne sait pas rejouer `on_bar -> Allocation`. Lacune de")
    L.append("core/ signalée, non corrigée (interdiction d'y toucher).")
    L.append("")
    all_ok = True
    for sym in SYMBOLS:
        for tag, p in (("défaut", dict(enable_shorts=True)),
                       ("binaire + shorts", dict(size_mode="binary",
                                                 enable_shorts=True))):
            L.append(f"  ### {tag}")
            l, ok = replay(sym, p)
            L += l
            all_ok = all_ok and ok
    L.append("=" * 88)
    L.append("VERDICT R5 : " + ("PASSÉ — les deux chemins décident à l'identique "
                                "sur la fenêtre rejouée."
                                if all_ok else "ÉCHOUÉ."))
    L.append("=" * 88)
    txt = "\n".join(L)
    print(txt)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "conformance.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"\n-> {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
