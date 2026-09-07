"""
Criblage des candidats d'entrée — PÉRIODE D'ÉTUDE 2021-2024 UNIQUEMENT.

    PYTHONIOENCODING=utf-8 python studies/derive_screener/run_screen.py
    SCREEN_TF=H1 PYTHONIOENCODING=utf-8 python studies/derive_screener/run_screen.py

2025 et 2026 sont un HOLDOUT. Ils ne sont pas chargés, volontairement : le seul moyen
fiable de ne pas regarder un holdout est de ne pas pouvoir le lire. Ils ne seront
ouverts qu'en T6, sur le candidat retenu, et une seule fois.

La liste des candidats est arrêtée dans `screener.py` et ne bouge plus (PLAN § T5).
Aucun réglage fin de leurs paramètres : on cherche une dérive franche, pas une dérive
optimisée. Une entrée qui exige un réglage précis pour montrer sa dérive est déjà
surajustée.

VALIDATION DE L'OUTIL (faite le 2026-09-07, avant ce criblage)
---------------------------------------------------------------
  - couverture : sur entrées aléatoires, 40 intervalles sur 40 contiennent zéro,
    biais moyen −0,001 R ;
  - récupération : une dérive injectée est retrouvée (55 % d'entrées bien orientées
    → E[R] = +0,111, intervalle excluant zéro) ;
  - plancher de détection : ±0,181 R à n = 300, ±0,099 à n = 1 000, ±0,057 à n = 3 000.

Conséquence à ne pas oublier en lisant le tableau : **la v1 elle-même est sous le
plancher** à son effectif (336 entrées sur la période, avantage réel ≈ +0,09 R). Le
témoin positif ne peut donc pas être « vu » ici, et son absence de signal n'invalide
rien — c'est une limite de puissance, mesurée, pas un défaut d'outil. En revanche un
candidat à 3 000 entrées dont l'intervalle exclut +0,05 exclut bel et bien un avantage
de la taille de celui de la v1.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.data.source import load_bars                              # noqa: E402
from studies.derive_screener.screener import (                      # noqa: E402
    CANDIDATS, cribler, temoin,
)

SYMBOL = "XAUUSD"
TIMEFRAME = os.environ.get("SCREEN_TF", "M15")
ETUDE_FIN = "2024-12-31"
GEOMETRIES = ((1.5, 4.0), (1.0, 2.0))   # celle de la v1, puis une cible plus proche
SEED = 20260907
OUT = os.path.dirname(os.path.abspath(__file__))
SPREAD_ETUDE = 52.0                     # médiane mesurée 2021-2024 (AUDIT § 1.1)


def rule(c="=", n=108):
    print(c * n)


def main() -> int:
    brut = load_bars(SYMBOL, TIMEFRAME, days=365 * 6)
    if brut is None or len(brut) < 10000:
        print("barres indisponibles")
        return 2
    bars = brut.loc[brut.index <= ETUDE_FIN].copy()

    rule()
    print(f"CRIBLAGE DE DÉRIVE · {SYMBOL} {TIMEFRAME}")
    rule()
    print(f"étude   : {bars.index[0].date()} → {bars.index[-1].date()}  ({len(bars)} barres)")
    print(f"holdout : non chargé, {len(brut) - len(bars)} barres mises de côté")
    print(f"spread médian de la période : {SPREAD_ETUDE:.0f} pips")
    print()
    print("E[R] = P(cible) × (tp/sl) − P(stop). Sous absence de dérive, E[R] = 0 pour")
    print("TOUTE géométrie (théorème d'arrêt optionnel). « seuil » est la demi-largeur")
    print("de l'intervalle : en dessous, le candidat n'est pas mesurable à cet effectif.")

    rapport: dict = {"symbol": SYMBOL, "timeframe": TIMEFRAME,
                     "etude": [str(bars.index[0]), str(bars.index[-1])],
                     "n_bars": len(bars), "spread_pips": SPREAD_ETUDE,
                     "resultats": {}}

    for sl, tp in GEOMETRIES:
        print()
        rule("-")
        print(f"GÉOMÉTRIE stop {sl:.1f} ATR · cible {tp:.1f} ATR   "
              f"(réussite d'équilibre {100 * sl / (sl + tp):.1f} %)")
        rule("-")
        print(f"{'candidat':24s} {'n':>6s} {'E[R]':>8s} {'IC 95%':>18s} {'seuil':>7s} "
              f"{'réuss.':>7s} {'gain':>7s} {'témoin':>15s} {'verdict':>10s}")

        for nom, gen in sorted(CANDIDATS.items()):
            try:
                entrees = gen(bars)
            except Exception as exc:                # un générateur cassé se voit
                print(f"{nom:24s}   ERREUR : {exc}")
                continue
            v = cribler(bars, entrees, nom, sl_atr=sl, tp_atr=tp)
            if not np.isfinite(v.e):
                print(f"{nom:24s} {v.n:6d}   effectif insuffisant (< 30)")
                continue
            seuil = (v.ic_haut - v.ic_bas) / 2.0
            tm, ts = temoin(bars, entrees, nom, seed=SEED, tirages=10,
                            sl_atr=sl, tp_atr=tp)
            suspect = np.isfinite(tm) and abs(tm) > 0.05
            if v.significatif:
                verdict = "DÉRIVE +" if v.e > 0 else "DÉRIVE −"
            elif seuil < 0.06:
                verdict = "nul (net)"          # exclut un avantage de taille v1
            else:
                verdict = "indécis"
            if suspect:
                verdict += "(?)"
            print(f"{nom:24s} {v.n:6d} {v.e:+8.3f} [{v.ic_bas:+6.3f},{v.ic_haut:+6.3f}] "
                  f"{seuil:7.3f} {100 * v.p_favorable:6.1f}% {v.derive_pips:+7.0f} "
                  f"{tm:+6.3f}±{ts:5.3f} {verdict:>10s}")
            rapport["resultats"].setdefault(f"sl{sl}_tp{tp}", {})[nom] = {
                "n": v.n, "e_r": round(v.e, 4),
                "ic": [round(v.ic_bas, 4), round(v.ic_haut, 4)],
                "seuil_detection": round(seuil, 4),
                "taux_reussite": round(100 * v.p_favorable, 2),
                "taux_equilibre": round(100 * v.p_equilibre, 2),
                "gain_pips": round(v.derive_pips, 1),
                "risque_median_pips": round(v.risque_median_pips, 1),
                "horizon_median_barres": v.horizon_median,
                "non_resolus": v.non_resolus, "ambigus": v.ambigus,
                "temoin_moyen": None if not np.isfinite(tm) else round(tm, 4),
                "significatif": bool(v.significatif),
            }

    print()
    rule()
    print("LECTURE")
    rule()
    print("1. « nul (net) » = l'intervalle est assez serré pour exclure un avantage de")
    print("   la taille de celui de la v1 (≈ +0,09 R/trade). C'est un résultat, pas une")
    print("   absence de résultat.")
    print("2. « indécis » = l'effectif ne permet pas de conclure. Ne rien en tirer.")
    print("3. Le témoin est l'espérance d'entrées tirées au hasard, mêmes effectifs et")
    print("   mêmes proportions de sens. Il doit rester proche de zéro.")
    print(f"4. {len(CANDIDATS)} candidats × {len(GEOMETRIES)} géométries = "
          f"{len(CANDIDATS) * len(GEOMETRIES)} tests. À 5 %, on attend "
          f"≈ {0.05 * len(CANDIDATS) * len(GEOMETRIES):.1f} faux positifs. Une dérive")
    print("   qui n'apparaît qu'à une seule géométrie ne compte pas.")
    print("5. « gain » est E[R] converti en pips, à comparer au spread "
          f"({SPREAD_ETUDE:.0f} pips).")

    p = os.path.join(OUT, f"screen_{TIMEFRAME}.json")
    json.dump(rapport, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nrésultats : {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
