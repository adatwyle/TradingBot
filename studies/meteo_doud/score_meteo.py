"""
Scoring des prévisions « météo de Doudi » contre les barres réelles XAUUSD.

    python studies/meteo_doud/score_meteo.py [--csv forecasts.csv]

CE QUE CE SCRIPT MESURE, ET CE QU'IL NE MESURE PAS
---------------------------------------------------
Elle publie chaque dimanche une prévision directionnelle chiffrée pour la semaine
(« mon scénario est d'aller chercher les 3150 »). Ce script demande, pour chaque
prévision datée : **le prix a-t-il atteint la cible avant la fin de la semaine,
et qu'a-t-il fallu endurer avant ?**

Trois mesures par prévision :
  atteint          la cible est-elle touchée dans la fenêtre ?
  bars_to_target   en combien de barres H1 (proxy de la vitesse)
  mae_pips         pire excursion adverse avant l'atteinte (ce qu'un suiveur
                   aurait dû encaisser)

Et une lecture d'ensemble : le taux d'atteinte face à un **témoin trivial** —
« le prix touche-t-il un niveau situé à la même distance, mais DANS L'AUTRE
SENS ? ». C'est le seul comparatif honnête : sur un actif volatil, atteindre un
niveau à ±X n'a rien de remarquable en soi. Une prévision ne vaut que si elle
bat sa propre symétrie.

CE QUE ÇA NE PROUVERA JAMAIS SEUL
-----------------------------------
Le corpus actuel provient de clips TikTok où elle *annonce ses réussites*. Le
biais de publication est total : les météos ratées ne sont pas postées. Un taux
d'atteinte élevé sur cet échantillon ne mesure donc **rien d'autre que sa
sélection**. Le chiffre ne devient interprétable qu'avec l'historique complet du
canal Discord, où les prévisions sont publiées avant de connaître l'issue.

Le script est écrit maintenant pour que ce jour-là, la mesure prenne une minute
au lieu d'une soirée — et pour que le protocole soit figé AVANT de voir les
données complètes.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:                                    # console Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.data.source import load_bars  # noqa: E402

PIP = 0.01
DEFAULT_HORIZON_DAYS = 7          # une météo couvre la semaine
HERE = os.path.dirname(os.path.abspath(__file__))


def load_forecasts(path: str) -> list[dict]:
    """Colonnes attendues : date (AAAA-MM-JJ), direction (up|down), target (prix),
    source (référence vérifiable). `origin` optionnel : prix au moment de l'annonce."""
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("date")]
    for r in rows:
        r["target"] = float(r["target"])
        r["direction"] = r["direction"].strip().lower()
    return rows


def score_one(bars: pd.DataFrame, fc: dict, horizon_days: int) -> dict:
    start = pd.Timestamp(fc["date"])
    end = start + timedelta(days=horizon_days)
    win = bars.loc[(bars.index >= start) & (bars.index <= end)]
    if win.empty:
        return {**fc, "statut": "hors données"}

    origin = float(fc.get("origin") or win["open"].iloc[0])
    target = fc["target"]
    up = fc["direction"] == "up"
    # Témoin : le niveau symétrique, même distance, sens opposé.
    mirror = origin - (target - origin)

    def first_touch(level: float, above: bool):
        hit = win["high"] >= level if above else win["low"] <= level
        idx = np.flatnonzero(hit.to_numpy())
        return int(idx[0]) if len(idx) else None

    i_t = first_touch(target, above=up)
    i_m = first_touch(mirror, above=not up)

    if i_t is None:
        mae = (origin - win["low"].min()) if up else (win["high"].max() - origin)
    else:
        pre = win.iloc[: i_t + 1]
        mae = (origin - pre["low"].min()) if up else (pre["high"].max() - origin)

    return {
        **fc,
        "origin": round(origin, 2),
        "mirror": round(mirror, 2),
        "atteint": i_t is not None,
        "temoin_atteint": i_m is not None,
        "atteint_avant_temoin": (i_t is not None and (i_m is None or i_t < i_m)),
        "bars_to_target": i_t,
        "mae_pips": round(max(0.0, float(mae)) / PIP, 0),
        "distance_pips": round(abs(target - origin) / PIP, 0),
        "statut": "ok",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scoring météo Doud")
    ap.add_argument("--csv", default=os.path.join(HERE, "forecasts.csv"))
    ap.add_argument("--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS)
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"aucun fichier de prévisions à {args.csv}")
        return 2
    fcs = load_forecasts(args.csv)
    bars = load_bars("XAUUSD", "H1")
    if bars is None:
        print("barres XAUUSD indisponibles")
        return 2

    print(f"{len(fcs)} prévisions · barres {bars.index[0]} → {bars.index[-1]} "
          f"· horizon {args.horizon_days} j\n")
    print(f"{'date':12s} {'sens':5s} {'cible':>9s} {'dist':>7s} {'atteint':>8s} "
          f"{'témoin':>7s} {'avant':>6s} {'barres':>7s} {'MAE':>7s}  source")
    rows = []
    for fc in fcs:
        r = score_one(bars, fc, args.horizon_days)
        rows.append(r)
        if r["statut"] != "ok":
            print(f"{fc['date']:12s} {fc['direction']:5s} {fc['target']:9.2f}"
                  f"   {r['statut']}")
            continue
        print(f"{r['date']:12s} {r['direction']:5s} {r['target']:9.2f} "
              f"{r['distance_pips']:7.0f} {str(r['atteint']):>8s} "
              f"{str(r['temoin_atteint']):>7s} {str(r['atteint_avant_temoin']):>6s} "
              f"{str(r['bars_to_target']):>7s} {r['mae_pips']:7.0f}  {r.get('source','')}")

    ok = [r for r in rows if r["statut"] == "ok"]
    if not ok:
        return 0
    n = len(ok)
    hit = sum(1 for r in ok if r["atteint"])
    first = sum(1 for r in ok if r["atteint_avant_temoin"])
    print(f"\nAtteintes : {hit}/{n}   ·   atteintes AVANT le témoin symétrique : "
          f"{first}/{n}")
    print("La seconde colonne est la seule qui distingue une prévision d'une "
          "amplitude.")
    if n < 30:
        print(f"\n[EFFECTIF INSUFFISANT] {n} prévisions. Rien ne se conclut ici : "
              "ce corpus vient de clips où elle annonce ses réussites, donc le "
              "biais de publication est total. Mesure interprétable seulement sur "
              "l'historique complet du canal Discord.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
