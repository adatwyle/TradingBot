"""
CONTRÔLE DE FENÊTRE — la composante horaire de H91 fait-elle quelque chose ?

    python strategies/s91_claude_scratch/backtests/window_control.py \
        > backtests/window_control.txt

POURQUOI CE TEST
----------------
H91 affirme deux choses distinctes :
  (a) une extension de prix se rétracte  -> mean-reversion générique
  (b) cet effet est PROPRE à la fenêtre de faible liquidité 22-06h serveur

Le walk-forward et l'ablation testent (a)+(b) ensemble. Si la même règle marche
aussi bien à toutes les heures, alors (b) est faux : la fenêtre n'apporte rien,
et l'appeler « H91 » serait une usurpation.

STATUT MÉTHODOLOGIQUE — À LIRE
-------------------------------
C'est un contrôle **post-hoc**, exécuté APRÈS avoir vu le walk-forward. Il ne
peut donc PAS sauver l'hypothèse ni produire un résultat promouvable, et aucune
des fenêtres ajoutées ici n'entre dans `param_grid` du manifest. Elles sont
injectées uniquement dans ce script. Il sert à une seule chose : savoir de quoi
la réfutation est la réfutation.

La mesure est faite à SPREAD NUL, pour comparer le signal brut et non les
péages, qui diffèrent d'une fenêtre à l'autre.
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

from core.backtest.engine import run as run_engine     # noqa: E402
from core.data.instruments import get_spec             # noqa: E402
from core.data.source import load_bars                 # noqa: E402
from strategies.s91_claude_scratch import strategy as S  # noqa: E402
from strategies.s91_claude_scratch.strategy import (   # noqa: E402
    CONTROL_JPY, ELIGIBLE, Strategy,
)

# Fenêtres de CONTRÔLE — injectées ici, jamais dans le manifest.
S.WINDOWS["ctrl_pic"] = (13, 14, 15, 16, 17)                    # Londres/NY
S.WINDOWS["ctrl_londres"] = (8, 9, 10, 11, 12)                  # matin européen
S.WINDOWS["ctrl_toutes"] = tuple(range(24))                     # aucune porte

ORDER = ["large", "etroite", "ctrl_londres", "ctrl_pic", "ctrl_toutes"]
LABEL = {
    "large": "H91 22-06h",
    "etroite": "H91 23-04h",
    "ctrl_londres": "ctrl 08-12h",
    "ctrl_pic": "ctrl 13-17h",
    "ctrl_toutes": "ctrl 24h/24",
}
ALL_SYMBOLS = ELIGIBLE + CONTROL_JPY
# Géométrie figée à la cellule par défaut : on isole l'effet FENÊTRE.
GEOM = [{"z_min": 2.0, "sl_atr": 2.5, "rr": 1.0},
        {"z_min": 1.5, "sl_atr": 2.5, "rr": 1.0},
        {"z_min": 2.5, "sl_atr": 3.0, "rr": 1.0}]


def rule(c="=", n=100):
    print(c * n)


def main():
    print("s91_claude_scratch — CONTRÔLE DE FENÊTRE (post-hoc, non promouvable)")
    print("Mesure à SPREAD NUL : on compare le SIGNAL, pas les péages.")
    print("Géométries : z_min/sl_atr/rr = (2.0/2.5/1.0), (1.5/2.5/1.0), (2.5/3.0/1.0)")
    print()
    rule()
    print("R/trade BRUT (spread nul), moyenne sur les 3 géométries")
    rule()
    print(f"  {'instrument':<11}{'groupe':<14}" +
          "".join(f"{LABEL[w]:>14}" for w in ORDER))
    print("  " + "-" * 95)

    table = {}
    for sym in ALL_SYMBOLS:
        df = load_bars(sym, "H1")
        s = Strategy()
        s._symbol = sym
        data = s.precompute(df, s.params)
        spec0 = dataclasses.replace(get_spec(sym), spread_pips=0.0)
        row, rown = [], []
        for w in ORDER:
            vals, ns = [], []
            for g in GEOM:
                p = dict(s.params)
                p.update(g)
                p["window"] = w
                res = run_engine(s.generate_signals(data, p, len(df)), df, spec0)
                if res.trades:
                    vals.append(res.total_r / res.n_trades)
                    ns.append(res.n_trades)
            row.append(np.mean(vals) if vals else np.nan)
            rown.append(int(np.mean(ns)) if ns else 0)
        table[sym] = (row, rown)
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        print(f"  {sym:<11}{grp:<14}" + "".join(f"{v:>+14.4f}" for v in row))

    print("  " + "-" * 95)
    el = np.array([table[s][0] for s in ELIGIBLE], dtype=float)
    ct = np.array([table[s][0] for s in CONTROL_JPY], dtype=float)
    print(f"  {'MOY ÉLIGIBLES':<25}" + "".join(f"{v:>+14.4f}" for v in el.mean(axis=0)))
    print(f"  {'MOY CONTRÔLE JPY':<25}" + "".join(f"{v:>+14.4f}" for v in ct.mean(axis=0)))
    print()
    print(f"  {'nb trades moyen':<25}" +
          "".join(f"{int(np.mean([table[s][1][i] for s in ALL_SYMBOLS])):>14}"
                  for i in range(len(ORDER))))

    print()
    rule()
    print("LECTURE")
    rule()
    m = dict(zip(ORDER, el.mean(axis=0)))
    best = max(m, key=lambda k: m[k])
    print(f"  Meilleure fenêtre sur les éligibles : {LABEL[best]} ({m[best]:+.4f} R/trade)")
    print(f"  Fenêtre H91 22-06h                  : {m['large']:+.4f} R/trade")
    print(f"  Fenêtre témoin 24h/24               : {m['ctrl_toutes']:+.4f} R/trade")
    delta = m["large"] - m["ctrl_toutes"]
    print(f"  Apport de la porte horaire H91      : {delta:+.4f} R/trade")
    print()
    if delta <= 0:
        print("  -> La porte horaire n'apporte RIEN. La composante (b) de H91 est")
        print("     fausse : ce qui est mesuré est du mean-reversion générique, pas")
        print("     un effet de liquidité de session.")
    else:
        print("  -> La porte horaire apporte un gain brut. La composante (b) reçoit")
        print("     un appui, à lire avec le confondant de tendance (§3 ablation).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
