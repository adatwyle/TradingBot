"""
Examen du seul résidu non écarté — NIKKEI — et comparaison au run contaminé.

    python strategies/s10_legacy_meanrev/backtests/residue_nikkei.py \
        > backtests/residue_nikkei.txt

NIKKEI est le seul des 8 instruments à dépasser le nombre de réussites attendues
par pur hasard dans le walk-forward ancré (9 contre 5,4), et le seul à être
long/short symétrique sur les TROIS variantes. C'est exactement la situation de
XAUUSD dans s01 : ni écarté, ni retenu tant qu'on ne l'a pas disséqué.

Les tests appliqués sont ceux qui ont disqualifié XAUUSD dans s01 §3.3 :
stabilité annuelle, contrôle directionnel sur la meilleure cellule, voisinage,
et TIER 1. Aucun n'a été choisi après avoir vu ce résultat.

Le second bloc chiffre ce que la question centrale du mandat demande :
de combien la fuite `closes[-1]` gonflait-elle les conclusions publiées ?
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.engine import run as run_engine          # noqa: E402
from core.contracts.strategy import Side                    # noqa: E402
from core.data.instruments import get_spec                  # noqa: E402
from core.data.source import load_bars                      # noqa: E402
from strategies.S010_legacy_meanrev.strategy import Strategy  # noqa: E402


def rule(c="=", n=104):
    print(c * n)


def section(t):
    print()
    rule()
    print(t)
    rule()


def run_cfg(sym, params):
    df = load_bars(sym, "H1")
    spec = get_spec(sym)
    s = Strategy(params)
    s._symbol = sym
    p = s.params
    return run_engine(s.generate_signals(s.precompute(df, p), p, len(df)), df, spec)


# La meilleure cellule NIKKEI du walk-forward ancré (moy OOS +13,26 R).
# Reprise telle quelle depuis backtests/anchored_wf.txt, pas re-cherchée.
BEST_NIKKEI = {"variant": "HIST_INF", "rsi_band": 40, "adx_max": 35,
               "sl_atr": 1.5, "rr": 2.0}


def yearly(sym, params, label):
    res = run_cfg(sym, params)
    by = defaultdict(list)
    for t in res.trades:
        by[t.entry_time.year].append(t.pnl_r)
    print(f"\n  {label} — {sym} — {res.n_trades} trades, "
          f"{res.total_r:+.1f} R, {res.total_r/max(1,res.n_trades):+.4f} R/trade, "
          f"WR {res.win_rate:.1f} %, DD max {res.max_drawdown_r:.1f} R")
    print(f"    {'année':<8}{'n':>6}{'R':>10}{'R/trade':>10}")
    tot = 0.0
    best_year, best_r = None, -1e9
    for y in sorted(by):
        v = by[y]
        tot += sum(v)
        if sum(v) > best_r:
            best_r, best_year = sum(v), y
        print(f"    {y:<8}{len(v):>6}{sum(v):>+10.1f}{np.mean(v):>+10.4f}")
    rest = [x for y, v in by.items() if y != best_year for x in v]
    print(f"    -> meilleure année {best_year} : {best_r:+.1f} R "
          f"= {100*best_r/tot:.0f} % du total")
    if rest:
        print(f"    -> hors {best_year} : {sum(rest):+.1f} R sur {len(rest)} trades "
              f"({np.mean(rest):+.4f} R/trade)")
    return res


def direction(res, label):
    L = [t for t in res.trades if t.side == Side.LONG]
    S = [t for t in res.trades if t.side == Side.SHORT]
    print(f"    {label} directionnel : "
          f"LONG {len(L)} tr {sum(t.pnl_r for t in L):+.1f} R "
          f"({np.mean([t.pnl_r for t in L]):+.4f} R/tr)  |  "
          f"SHORT {len(S)} tr {sum(t.pnl_r for t in S):+.1f} R "
          f"({np.mean([t.pnl_r for t in S]):+.4f} R/tr)")


def main():
    print("s10_legacy_meanrev — EXAMEN DU RÉSIDU NIKKEI + COMPARAISON AU RUN CONTAMINÉ")

    section("1. NIKKEI — STABILITÉ ANNUELLE DE LA MEILLEURE CELLULE")
    print("  Test repris de s01 §3.3, où il a disqualifié XAUUSD (72 % du résultat")
    print("  venait de la seule année 2022). Critère fixé avant de regarder :")
    print("  si > 60 % du résultat vient d'une seule année, ce n'est pas un système.")
    res = yearly("NIKKEI", BEST_NIKKEI, "meilleure cellule WF (HIST_INF rsi40 adx35 sl1.5 rr2)")
    direction(res, "meilleure cellule")

    print()
    print("  Les 3 variantes au paramétrage par défaut, pour voir si le résultat")
    print("  tient à la cellule ou à l'instrument :")
    for v in ("DIV_SR", "DIV_NOSR", "HIST_INF"):
        r = yearly("NIKKEI", {"variant": v}, f"défaut / {v}")
        direction(r, v)

    section("2. CONTRÔLE — LE MÊME TEST SUR LES DEUX EX-VEDETTES CONTAMINÉES")
    print("  SP500 et FTSE portaient le « PORTFOLIO ROBUSTE » de SPEC.md §7.1")
    print("  (+244 et +108 CHF/fenêtre). Sur moteur propre ils font 0/108 STRICT.")
    for sym in ("SP500", "FTSE"):
        r = yearly(sym, {"variant": "DIV_SR"}, f"défaut / DIV_SR")
        direction(r, sym)

    section("3. DE COMBIEN LA FUITE GONFLAIT-ELLE LES CONCLUSIONS ?")
    print("""
  Le run contaminé de référence est `anchored_wf_results.txt` (2026-04-10) :
  même protocole (walk-forward ancré, 4 fenêtres, critère STRICT), 210 configs,
  17 instruments. Comparaison à protocole identique, normalisée par la taille
  de grille.

    instrument | contaminé /210 |  taux  | propre /108 |  taux  | attendu hasard
    -----------+----------------+--------+-------------+--------+---------------
    SP500      |       7        |  3.3 % |      0      |  0.0 % |     5.0 %
    FTSE       |       7        |  3.3 % |      0      |  0.0 % |     5.0 %
    AUDCHF     |       3        |  1.4 % |      4      |  3.7 % |     5.0 %
    NIKKEI     |       2        |  1.0 % |      9      |  8.3 % |     5.0 %
    USDJPY     |       0        |  0.0 % |      0      |  0.0 % |     5.0 %
    EURUSD     |     absent     |    -   |      0      |  0.0 % |     5.0 %
    EURCHF     |     absent     |    -   |      4      |  3.7 % |     5.0 %
    AUDUSD     |     absent     |    -   |      2      |  1.9 % |     5.0 %

  LE POINT CENTRAL, ET IL NE PORTE PAS SUR LA FUITE :

  Le run contaminé a produit 19 réussites STRICT sur 17 x 210 = 3 570 cellules.
  Un edge STRICTEMENT NUL en aurait produit ~178 (3 570 x 5 %).
  Il faisait donc DIX FOIS MOINS BIEN QUE LE HASARD — et il a quand même été
  publié comme « PORTFOLIO ROBUSTE » dans SPEC.md §7.1, puis chiffré à
  +612 CHF/an.

  Le run propre produit 19 réussites sur 8 x 108 = 864 cellules, contre ~43
  attendues du hasard : deux fois moins bien que le hasard.

  Autrement dit : la correction du lookahead n'a PAS transformé un résultat
  positif en résultat négatif. Le résultat était déjà négatif AVANT la
  correction — personne n'avait calculé le taux de faux positifs. La fuite a
  déplacé QUELS instruments semblaient marcher (SP500 et FTSE s'effondrent de
  3,3 % a 0 %, NIKKEI monte de 1,0 % a 8,3 %) sans jamais changer le fait que
  l'ensemble était sous le seuil du hasard.

  C'est un résultat plus dérangeant que « la fuite gonflait de X % » :
  le chiffre publie n'etait pas seulement gonfle, il n'etait pas lu.

  RÉSERVE HONNÊTE SUR CETTE COMPARAISON — trois écarts de protocole
  interdisent d'attribuer TOUT l'écart à la fuite :
    (a) les cellules gagnantes de SP500 et FTSE dans le run contaminé étaient
        des COMBINAISONS multi-variantes (HI_cons+NO_SR, HI_aggr+NO_SR) que le
        contrat de la plateforme ne permet pas d'exprimer (ANALYSIS §4.4) ;
        leur 0/108 n'est donc pas strictement le même test ;
    (b) ma détection de divergence est une fractale confirmée, pas la fenêtre
        tronquée de l'historique (ANALYSIS §4.1) ;
    (c) le moteur commun est plus pessimiste (stop prioritaire, pas de marge de
        bruit sur le stop) et compte en R, pas en CHF (ANALYSIS §4.5).
  La conclusion « sous le seuil du hasard » ne dépend d'aucun de ces trois
  points : elle se calcule sur les comptes de réussites du run contaminé
  lui-même, avec ses propres chiffres.
""")

    section("4. SUR-DISPERSION — POURQUOI « 19 CONTRE 43 » EST À LIRE AVEC PRUDENCE")
    print("""
  Le repère « 5 % de la grille par pur hasard » suppose des configurations
  INDÉPENDANTES. Elles ne le sont pas : deux cellules voisines partagent la
  quasi-totalité de leurs trades. Le nombre de réussites est donc SUR-DISPERSÉ
  — il arrive par paquets (0, 0, 9, 4...) plutôt que dispersé autour de 5,4.

  Conséquence dans les deux sens :
   * un instrument à 9/108 n'est pas « 1,7x le hasard » de façon significative ;
   * mais un TOTAL de 19 contre 43 attendues sur 8 instruments reste informatif,
     parce que la sur-dispersion joue surtout DANS un instrument, pas entre eux.
  On ne conclut donc pas sur un instrument isolé, on conclut sur le portefeuille
  — et on traite NIKKEI comme un résidu à part, pas comme une preuve.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
