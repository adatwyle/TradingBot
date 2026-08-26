"""
MESURE DE L'AMBIGUÏTÉ INTRA-BARRE
==================================

LA QUESTION
-----------
Notre backtest ne connaît que 4 nombres par barre H1 : open, high, low, close.
Il ignore le CHEMIN suivi par le prix à l'intérieur de l'heure.

Quand le stop ET la cible tombent tous deux dans l'amplitude d'une même barre,
l'issue dépend entièrement de l'ordre de visite — information que nous n'avons
pas. Le moteur suppose alors **le stop en premier** (hypothèse pessimiste).

Cette supposition est-elle coûteuse ? On n'en savait rien. Ce module le mesure,
en utilisant les 12 barres M5 contenues dans chaque barre H1 comme arbitre.

MÉTHODE
-------
Pour chaque barre H1, on simule une entrée à l'ouverture avec un stop et une
cible à des distances réalistes (multiples d'ATR). Trois cas :

    RÉSOLU      un seul des deux niveaux est touché -> aucune ambiguïté
    AMBIGU      les deux sont dans l'amplitude H1   -> le M5 tranche
    NEUTRE      aucun des deux n'est touché

Sur les cas AMBIGUS, on compare la vérité M5 à notre hypothèse « stop d'abord ».

LECTURE DU RÉSULTAT
-------------------
    part d'ambigus faible (< 5 %)  -> le modèle H1 est solide
    part élevée + hypothèse souvent fausse -> nos backtests sous-estiment
                                              systématiquement les résultats

Un biais pessimiste est moins dangereux qu'un biais optimiste : il fait rejeter
de bonnes stratégies plutôt qu'accepter de mauvaises. Mais le connaître permet
de le corriger.

    python -m core.validation.intrabar --symbols EURUSD SP500
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data.harvester import load_dataset  # noqa: E402
from core.data.source import load_bars  # noqa: E402


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyse(h1: pd.DataFrame, m5: pd.DataFrame, sl_mult: float, tp_mult: float,
            side: str = "LONG") -> dict:
    """Simule une entrée par barre H1 et arbitre les cas ambigus avec le M5."""
    h1 = h1.copy()
    h1["atr"] = atr(h1)
    h1 = h1.dropna()

    # Regroupe les barres M5 par heure de rattachement.
    m5_by_hour = {ts: g for ts, g in m5.groupby(m5.index.floor("h"))}

    n_total = n_resolved = n_ambiguous = n_neutral = 0
    n_pess_right = n_pess_wrong = 0

    for ts, row in h1.iterrows():
        a = float(row["atr"])
        if not np.isfinite(a) or a <= 0:
            continue
        entry = float(row["open"])
        hi, lo = float(row["high"]), float(row["low"])

        if side == "LONG":
            stop, target = entry - sl_mult * a, entry + tp_mult * a
        else:
            stop, target = entry + sl_mult * a, entry - tp_mult * a

        hit_sl = lo <= stop <= hi
        hit_tp = lo <= target <= hi
        n_total += 1

        if not hit_sl and not hit_tp:
            n_neutral += 1
            continue
        if hit_sl != hit_tp:
            n_resolved += 1
            continue

        # Ambigu : le M5 tranche.
        n_ambiguous += 1
        sub = m5_by_hour.get(ts)
        if sub is None or sub.empty:
            continue

        truth = None
        for _, b in sub.iterrows():
            bh, bl = float(b["high"]), float(b["low"])
            s_in = bl <= stop <= bh
            t_in = bl <= target <= bh
            if s_in and t_in:
                continue      # toujours ambigu à 5 min — on n'arbitre pas
            if s_in:
                truth = "SL"; break
            if t_in:
                truth = "TP"; break

        if truth == "SL":
            n_pess_right += 1     # notre hypothèse était juste
        elif truth == "TP":
            n_pess_wrong += 1     # on a compté une perte là où c'était un gain

    decided = n_pess_right + n_pess_wrong
    return {
        "barres": n_total,
        "neutres": n_neutral,
        "resolus": n_resolved,
        "ambigus": n_ambiguous,
        "pct_ambigu_sur_touches": (100.0 * n_ambiguous / (n_resolved + n_ambiguous)
                                   if (n_resolved + n_ambiguous) else 0.0),
        "arbitres_m5": decided,
        "hypothese_juste": n_pess_right,
        "hypothese_fausse": n_pess_wrong,
        "pct_hypothese_fausse": (100.0 * n_pess_wrong / decided) if decided else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", default=["EURUSD", "SP500"])
    ap.add_argument("--geometries", nargs="+", default=["1.5:3.0", "2.0:2.0", "2.0:4.0"],
                    help="couples SL:TP en multiples d'ATR")
    a = ap.parse_args()

    print("=" * 84)
    print("AMBIGUÏTÉ INTRA-BARRE — le modèle H1 est-il fiable ?")
    print("=" * 84)
    print("Le backtest suppose « stop touché avant la cible » quand les deux")
    print("tombent dans la même barre H1. Le M5 sert ici d'arbitre.\n")

    any_data = False
    for sym in a.symbols:
        m5 = load_dataset(sym, "M5")
        if m5 is None or m5.empty:
            print(f"[{sym}] aucun dataset M5 local — lancer le moissonneur")
            continue

        h1 = load_bars(sym, "H1")
        if h1 is None:
            print(f"[{sym}] H1 indisponible")
            continue

        # On restreint le H1 à la période effectivement couverte par le M5.
        h1 = h1[(h1.index >= m5.index[0]) & (h1.index <= m5.index[-1])]
        if h1.empty:
            print(f"[{sym}] aucun recouvrement H1/M5")
            continue

        any_data = True
        print(f"--- {sym} ---")
        print(f"  recouvrement : {h1.index[0].date()} -> {h1.index[-1].date()}"
              f"   ({len(h1)} barres H1, {len(m5)} barres M5)")
        print(f"  {'SL:TP':>9} {'ambigus':>9} {'% des touches':>14}"
              f" {'arbitrés':>9} {'hypothèse fausse':>18}")
        print("  " + "-" * 74)

        for g in a.geometries:
            sl_s, tp_s = g.split(":")
            r = analyse(h1, m5, float(sl_s), float(tp_s))
            pct_wrong = ("—" if r["pct_hypothese_fausse"] is None
                         else f"{r['pct_hypothese_fausse']:.1f} %")
            print(f"  {g:>9} {r['ambigus']:>9} {r['pct_ambigu_sur_touches']:>13.1f} %"
                  f" {r['arbitres_m5']:>9} {pct_wrong:>18}")
        print()

    if not any_data:
        print("Aucune donnée exploitable.")
        return 1

    print("=" * 84)
    print("LECTURE")
    print("  « % des touches » = part des trades où stop ET cible tombent dans la")
    print("    même barre H1. C'est la zone d'incertitude de notre modèle.")
    print("  « hypothèse fausse » = cas où le M5 montre que la CIBLE a été touchée")
    print("    en premier, alors que le backtest comptait une perte.")
    print()
    print("  Un taux d'erreur élevé signifie que nos backtests SOUS-ESTIMENT les")
    print("  résultats. Biais pessimiste : il fait rejeter de bonnes stratégies")
    print("  plutôt qu'accepter de mauvaises — préférable, mais à connaître.")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
