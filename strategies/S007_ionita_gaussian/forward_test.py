"""
REPRODUCTION DU FORWARD-TEST PUBLIÉ PAR L'AUTEUR
=================================================

C'est la comparaison la plus informative disponible, et de loin.

CE QU'ON REPRODUIT, ET POURQUOI CELUI-LÀ
-----------------------------------------
Dans `sources/03_gaussian_10months_forward.txt`, l'auteur revient dix mois après
avoir publié la stratégie et mesure ce qu'elle a réellement fait depuis :

    « 51.74% profit »            (rendement total)
    « the maxdown was 8.57 »     (drawdown maximal)
    « profitable trades was 44.44% »
    sur BTC, en daily, à partir du 15 octobre 2024

C'est une donnée HORS ÉCHANTILLON publiée par l'auteur, contre lui-même s'il le
fallait. Elle vaut infiniment mieux que les 7 492 % de la vidéo publicitaire,
qui sont une courbe d'équité optimisée sur l'historique complet.

Le chiffre le plus important de cette vidéo n'est pourtant pas le sien. C'est
celui-ci, prononcé deux minutes plus tard :

    « let's measure the buy and hold return. It was here about 68%. »

Son propre forward-test rend donc 51,74 % là où ne rien faire rendait 68 %.

ÉCARTS ASSUMÉS DE CETTE REPRODUCTION
-------------------------------------
1. Il mesure la stratégie TradingView « Gaussian Channel V3.1 », LONG SEUL. Le
   prompt que nous reproduisons (`TR-GC-Crypto-LS-2`) est la version portefeuille
   long+short. La mécanique LONGUE est la même — entrée sur croisement au-dessus
   de la bande haute, sortie sous la bande haute — et c'est elle qu'on isole ici.
2. Son BTC est un spot d'exchange ; le nôtre est un CFD Swissquote. Les prix
   diffèrent à la marge, les coûts nettement (cf. le portage).
3. Ses paramètres exacts ne sont pas publiés ; on prend les valeurs par défaut du
   Pine Script d'origine (144 / 4 pôles / 1,414). C'est l'interprétation la plus
   favorable : elle ne suppose aucun réglage caché à notre avantage.

USAGE
-----
    python -m strategies.S007_ionita_gaussian.forward_test
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
from strategies.S007_ionita_gaussian.run_backtest import (
    load_universe, make_specs, carry_drag_pct, SWAP_ANNUAL_PCT,
)
from strategies.S007_ionita_gaussian.strategy import Strategy

# Fenêtre du forward-test de l'auteur. Début : le 15 octobre 2024, date de
# publication de sa vidéo d'automatisation (il la justifie à l'écran). Fin : la
# publication de la vidéo de bilan, le 9 septembre 2025.
FWD_START = pd.Timestamp("2024-10-15")
FWD_END = pd.Timestamp("2025-09-09")

CLAIMED = {"total_pct": 51.74, "max_dd_pct": -8.57, "win_rate_pct": 44.44,
           "buy_hold_pct": 68.0}


def _count_round_trips(weights: pd.Series) -> tuple[int, list[tuple[int, int]]]:
    """Segments contigus d'exposition — l'équivalent d'un « trade » ici.

    La source raisonne en trades (elle en énumère neuf à l'écran). Une
    allocation n'a pas de trades ; l'objet comparable est l'épisode de détention
    continue. On les compte pour pouvoir reporter un effectif, sans quoi le
    taux de réussite ne veut rien dire (`docs/METHODOLOGY.md` §6).
    """
    inv = (weights > 1e-9).to_numpy()
    segs, start = [], None
    for i, x in enumerate(inv):
        if x and start is None:
            start = i
        elif not x and start is not None:
            segs.append((start, i)); start = None
    if start is not None:
        segs.append((start, len(inv)))
    return len(segs), segs


def run() -> str:
    L = []
    L.append("=" * 78)
    L.append("REPRODUCTION DU FORWARD-TEST PUBLIÉ PAR L'AUTEUR")
    L.append("=" * 78)
    L.append(f"Fenêtre    : {FWD_START.date()} -> {FWD_END.date()}")
    L.append(f"Instrument : BTCUSD (CFD Swissquote) — l'auteur mesure un spot")
    L.append(f"Réglages   : 144 / 4 pôles / 1,414 (défauts du Pine Script)")
    L.append("")
    L.append("Ce que l'auteur annonce :")
    L.append(f"    rendement total      {CLAIMED['total_pct']:>8.2f} %")
    L.append(f"    drawdown max         {CLAIMED['max_dd_pct']:>8.2f} %")
    L.append(f"    trades gagnants      {CLAIMED['win_rate_pct']:>8.2f} %  (sur ~9 trades)")
    L.append(f"    buy & hold, par lui  {CLAIMED['buy_hold_pct']:>8.2f} %  <- son propre chiffre")
    L.append("")

    bars_all = load_universe(["BTCUSD"])
    full = bars_all["BTCUSD"]
    idx = full.index

    # Le warmup doit être PRIS AVANT la fenêtre, pas dedans : le filtre a besoin
    # de son historique. On simule donc depuis le début des données et on ne
    # MESURE que la fenêtre. C'est aussi ce que fait TradingView.
    a = int(idx.searchsorted(FWD_START))
    b = int(idx.searchsorted(FWD_END, side="right"))
    L.append(f"Barres disponibles : {len(idx)} au total, "
             f"{b - a} dans la fenêtre mesurée "
             f"({idx[a].date()} -> {idx[b - 1].date()})")
    L.append("")

    strat = Strategy(universe=["BTCUSD"])
    params = dict(strat.params)
    params["enable_shorts"] = False
    params["weight_mode"] = "normalized"   # 100 % BTC quand investi, comme TV

    data = strat.precompute(bars_all, params)
    allocs = strat.generate_allocations(data, params, b)
    specs = make_specs(["BTCUSD"])
    res = run_allocation(allocs, bars_all, specs, end_idx=b, periods_per_year=365.0)

    eq = res.equity.iloc[a:b]
    eq = eq / eq.iloc[0]
    total = 100.0 * float(eq.iloc[-1] - 1.0)
    dd = 100.0 * float(((eq / eq.cummax()) - 1.0).min())

    w = res.weights_history["BTCUSD"].iloc[a:b]
    n_trades, segs = _count_round_trips(w)
    invested = 100.0 * float((w > 1e-9).mean())

    # Rendement de chaque épisode de détention, pour un taux de réussite
    # comparable au sien.
    #
    # ATTENTION AU DÉCALAGE D'UN CRAN, il fausse tout si on l'oublie : dans le
    # moteur, `equity[i]` inclut DÉJÀ le rendement de la barre i, produit par le
    # poids décidé à la barre i-1. Le gain d'un épisode qui court de `s` à `e-1`
    # est donc `equity[e-1] / equity[s-1]`, pas `equity[e] / equity[s]`.
    # Une première version prenait la seconde forme et gonflait le cumul.
    # Cas `s == 0` : la position était DÉJÀ ouverte à l'entrée de la fenêtre. Ce
    # n'est pas un artefact — l'auteur décrit exactement la même chose, son
    # premier trade étant déclenché par la bougie du 14 octobre, la veille du
    # début de sa mesure. On prend alors la base normalisée `eq[0]`.
    eq_np = eq.to_numpy()
    seg_rets, kept = [], []
    for s, e in segs:
        if e <= s + 1:
            continue
        base = eq_np[s - 1] if s > 0 else eq_np[0]
        r = 100.0 * (eq_np[min(e, len(eq_np)) - 1] / base - 1.0)
        seg_rets.append(r); kept.append((s, e))
    wins = sum(1 for r in seg_rets if r > 0)
    wr = 100.0 * wins / len(seg_rets) if seg_rets else 0.0

    # Contrôle de cohérence : hors épisode le portefeuille est en cash, donc le
    # produit des épisodes doit reproduire le total. S'il ne le reproduit pas,
    # le découpage est faux et le détail affiché serait trompeur.
    compounded = 100.0 * (float(np.prod([1 + r / 100.0 for r in seg_rets])) - 1.0)

    opens = full["open"].iloc[a:b]
    bh = 100.0 * float(opens.iloc[-1] / opens.iloc[0] - 1.0)

    drag = carry_drag_pct(invested, ["BTCUSD"])
    years = (b - a) / 365.0
    total_after_carry = total - drag * years

    L.append("Ce que NOUS mesurons :")
    L.append(f"    rendement total      {total:>8.2f} %   "
             f"(effectif : {len(seg_rets)} épisodes de détention)")
    L.append(f"    drawdown max         {dd:>8.2f} %")
    L.append(f"    épisodes gagnants    {wr:>8.2f} %   ({wins}/{len(seg_rets)})")
    L.append(f"    buy & hold BTC       {bh:>8.2f} %   <- mesuré sur nos barres")
    L.append(f"    investi              {invested:>8.1f} % du temps")
    L.append("")
    L.append(f"    portage non modélisé : -{drag:.1f} %/an x {years:.2f} an "
             f"= -{drag * years:.1f} pt")
    L.append(f"    rendement après portage {total_after_carry:>8.2f} %")
    L.append("")

    L.append("Détail des épisodes (l'auteur en énumère neuf à l'écran) :")
    for k, ((s, e), r) in enumerate(zip(kept, seg_rets), 1):
        L.append(f"    {k:>2}. {idx[a + s].date()} -> "
                 f"{idx[a + min(e, len(eq_np)) - 1].date()}  {r:>+8.2f} %")
    L.append(f"    composé : {compounded:+.2f} %   (total mesuré {total:+.2f} % — "
             f"écart {abs(compounded - total):.2f} pt)")
    if abs(compounded - total) > 1.0:
        L.append("    *** découpage incohérent avec la courbe : détail non fiable ***")
    L.append("")

    L.append("-" * 78)
    L.append("CONFRONTATION")
    L.append("-" * 78)
    L.append(f"  {'':<26} {'auteur':>12} {'nous':>12} {'écart':>12}")
    L.append(f"  {'rendement total':<26} {CLAIMED['total_pct']:>11.2f}% "
             f"{total:>11.2f}% {total - CLAIMED['total_pct']:>+11.2f}")
    L.append(f"  {'drawdown max':<26} {CLAIMED['max_dd_pct']:>11.2f}% "
             f"{dd:>11.2f}% {dd - CLAIMED['max_dd_pct']:>+11.2f}")
    L.append(f"  {'trades/épisodes gagnants':<26} {CLAIMED['win_rate_pct']:>11.2f}% "
             f"{wr:>11.2f}% {wr - CLAIMED['win_rate_pct']:>+11.2f}")
    L.append(f"  {'buy & hold':<26} {CLAIMED['buy_hold_pct']:>11.2f}% "
             f"{bh:>11.2f}% {bh - CLAIMED['buy_hold_pct']:>+11.2f}")
    L.append("")
    L.append(f"  Stratégie moins buy & hold, chez l'auteur : "
             f"{CLAIMED['total_pct'] - CLAIMED['buy_hold_pct']:+.2f} points")
    L.append(f"  Stratégie moins buy & hold, chez nous     : "
             f"{total - bh:+.2f} points")
    L.append("")
    L.append("  Lecture : le signe de cet écart est le résultat qui compte. Il est")
    L.append("  négatif dans les DEUX mesures — celle de l'auteur comme la nôtre.")
    L.append("")
    L.append(f"  EFFECTIF : {len(seg_rets)} épisodes. Sur un tel nombre, l'intervalle")
    L.append("  de confiance du taux de réussite couvre pratiquement tout. Aucun")
    L.append("  taux de réussite calculé sur cette fenêtre — le sien comme le")
    L.append("  nôtre — n'est statistiquement interprétable.")
    L.append("=" * 78)
    return "\n".join(L)


def main() -> int:
    report = run()
    print(report)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "forward_test.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
