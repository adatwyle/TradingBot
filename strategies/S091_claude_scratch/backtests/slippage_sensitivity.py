"""
SENSIBILITÉ AU SLIPPAGE — s91_claude_scratch

    python strategies/s91_claude_scratch/backtests/slippage_sensitivity.py \
        > backtests/slippage_sensitivity.txt

POURQUOI CE TEST EXISTE MAINTENANT
-----------------------------------
Le VERDICT initial listait « slippage non modélisé » comme limite, en se
contentant de dire qu'il ne peut qu'aggraver. `core/backtest/engine.py` expose
désormais `InstrumentSpec.slippage_pips` (coût de bord payé aux DEUX extrémités,
toujours défavorable). La limite devient donc **chiffrable**, et une limite
chiffrée vaut mieux qu'une limite invoquée.

CE QUE ÇA MESURE
----------------
Le résultat central du dossier est : « l'edge brut existe, mais il vaut environ
1/1,5 du péage ». Le slippage déplace le péage. La question précise est donc :

    de combien le slippage éloigne-t-il encore le point d'équilibre ?

et, symétriquement, la question qui compte pour la suite du projet :

    à quel coût total le système passerait-il à l'équilibre ?

Le balayage va de 0 (l'hypothèse optimiste des mesures précédentes) à 0,5 pip
(borne haute annoncée par le moteur pour le FX liquide hors news).
"""
from __future__ import annotations

import dataclasses
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import _grid                # noqa: E402
from core.backtest.engine import run as run_engine         # noqa: E402
from core.data.instruments import get_spec                 # noqa: E402
from core.data.source import load_bars                     # noqa: E402
from strategies.s91_claude_scratch.strategy import (       # noqa: E402
    CONTROL_JPY, ELIGIBLE, Strategy,
)

ALL_SYMBOLS = ELIGIBLE + CONTROL_JPY
SLIPPAGES = [0.0, 0.1, 0.2, 0.3, 0.5]
TRAIN_FRAC = 0.60


def rule(c="=", n=100):
    print(c * n)


def main():
    print("s91_claude_scratch — SENSIBILITÉ AU SLIPPAGE")
    print("Coût de bord = demi-spread + slippage, payé à l'entrée ET à la sortie.")
    print(f"Balayage : {SLIPPAGES} pips  (0,2-0,5 = ordre de grandeur FX liquide)")
    print("Grille complète : 54 configurations par instrument.")
    print()

    cells = _grid(Strategy().manifest().param_grid)
    cache = {}
    for sym in ALL_SYMBOLS:
        df = load_bars(sym, "H1")
        s = Strategy()
        s._symbol = sym
        data = s.precompute(df, s.params)
        sigs = []
        for c in cells:
            p = dict(s.params)
            p.update(c)
            sigs.append(s.generate_signals(data, p, len(df)))
        cache[sym] = (df, sigs, int(len(df) * TRAIN_FRAC))

    rule()
    print("R/trade moyen sur la grille — PLEIN ÉCHANTILLON")
    rule()
    print(f"  {'instrument':<11}{'groupe':<14}" +
          "".join(f"{'slip ' + str(v):>12}" for v in SLIPPAGES))
    print("  " + "-" * 88)
    res_full = {}
    for sym in ALL_SYMBOLS:
        df, sigs, _ = cache[sym]
        base = get_spec(sym)
        row = []
        for sl in SLIPPAGES:
            spec = dataclasses.replace(base, slippage_pips=sl)
            v = [r.total_r / r.n_trades
                 for r in (run_engine(g, df, spec) for g in sigs) if r.n_trades]
            row.append(float(np.mean(v)) if v else np.nan)
        res_full[sym] = row
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        print(f"  {sym:<11}{grp:<14}" + "".join(f"{v:>+12.4f}" for v in row))
    print("  " + "-" * 88)
    el = np.array([res_full[s] for s in ELIGIBLE])
    print(f"  {'MOY ÉLIGIBLES':<25}" + "".join(f"{v:>+12.4f}" for v in el.mean(axis=0)))

    print()
    rule()
    print("R/trade moyen sur la grille — TRANCHE DE TEST SEULE (60-100 %)")
    rule()
    print("  C'est le chiffre qui compte : l'hypothèse a été formée sur le train.")
    print()
    print(f"  {'instrument':<11}{'groupe':<14}" +
          "".join(f"{'slip ' + str(v):>12}" for v in SLIPPAGES))
    print("  " + "-" * 88)
    res_oos = {}
    for sym in ALL_SYMBOLS:
        df, sigs, cut = cache[sym]
        base = get_spec(sym)
        cutt = df.index[cut - 1]
        row = []
        for sl in SLIPPAGES:
            spec = dataclasses.replace(base, slippage_pips=sl)
            vals = []
            for g in sigs:
                tr = [t.pnl_r for t in run_engine(g, df, spec).trades
                      if t.entry_time > cutt]
                if tr:
                    vals.append(float(np.mean(tr)))
            row.append(float(np.mean(vals)) if vals else np.nan)
        res_oos[sym] = row
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        print(f"  {sym:<11}{grp:<14}" + "".join(f"{v:>+12.4f}" for v in row))
    print("  " + "-" * 88)
    elo = np.array([res_oos[s] for s in ELIGIBLE])
    print(f"  {'MOY ÉLIGIBLES':<25}" + "".join(f"{v:>+12.4f}" for v in elo.mean(axis=0)))

    print()
    rule()
    print("LECTURE")
    rule()
    m0, m5 = el.mean(axis=0)[0], el.mean(axis=0)[-1]
    o0, o5 = elo.mean(axis=0)[0], elo.mean(axis=0)[-1]
    print(f"  Plein échantillon, éligibles : {m0:+.4f} (slip 0) -> {m5:+.4f} (slip 0,5)")
    print(f"  Hors échantillon, éligibles  : {o0:+.4f} (slip 0) -> {o5:+.4f} (slip 0,5)")
    print(f"  Coût marginal de 0,5 pip de slippage : {m5-m0:+.4f} R/trade")
    print()
    print("  Le verdict PAS D'EDGE est établi à slippage NUL, c'est-à-dire dans")
    print("  l'hypothèse la PLUS FAVORABLE. Le slippage ne fait que l'aggraver :")
    print("  aucune valeur du balayage ne ramène les éligibles à l'équilibre hors")
    print("  échantillon. La limite « slippage non modélisé » est donc chiffrée,")
    print("  et elle va dans le sens du verdict.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
