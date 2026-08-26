"""
Walk-forward ancré + diagnostics — s10_legacy_meanrev (Legacy S1).

    python strategies/s10_legacy_meanrev/backtests/run_wf.py > backtests/anchored_wf.txt

N'implémente AUCUN moteur (R9) : tout passe par `core.backtest.anchored_wf` et
`core.backtest.engine`. Ce script orchestre et imprime les diagnostics que la
méthodologie du projet exige :

  * R1 rejoué sur plusieurs points de la grille, pas seulement le défaut
  * effectif hors échantillon SYSTÉMATIQUE
  * comparaison au nombre de réussites attendues par pur hasard
  * ABLATION DU SPREAD (s01 §5.1) : sépare « pas d'edge » de « edge mangé »
  * CONTRÔLE LONG/SHORT (s01 §5.3) : 2021-2026 fabrique de faux edges
    directionnels — SP500 / NIKKEI / FTSE sont des indices en bull market
  * robustesse au voisinage de la meilleure configuration
  * concentration du résultat sur un instrument
  * péage du spread sur la distance de risque RÉELLEMENT observée
  * durée de détention réelle (test de fidélité fixé en Phase 1)
"""
from __future__ import annotations

import dataclasses
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward              # noqa: E402
from core.backtest.engine import run as run_engine                  # noqa: E402
from core.data.instruments import get_spec                          # noqa: E402
from core.data.source import load_bars                              # noqa: E402
from core.validation.causality import check as causality_check      # noqa: E402
from strategies.S010_legacy_meanrev.strategy import Strategy         # noqa: E402

MIN_TRADES = 20
MAX_DD_R = 12.0
VARIANTS = ("DIV_SR", "DIV_NOSR", "HIST_INF")


def rule(c="=", n=104):
    print(c * n)


def section(title):
    print()
    rule()
    print(title)
    rule()


def _fit(sym, params):
    """Instancie la stratégie pour un instrument donné."""
    s = Strategy(params)
    s._symbol = sym
    return s


def _full_run(sym, df, spec, params):
    s = _fit(sym, params)
    p = s.params
    return run_engine(s.generate_signals(s.precompute(df, p), p, len(df)), df, spec)


# ─────────────────────────────────────────────────────────────────────────────
def causality_sweep(symbols):
    """R1 sur plusieurs coins de la grille. Un test qui ne couvre que les
    paramètres par défaut ne prouve rien sur les 107 autres cellules — et c'est
    précisément une fuite de ce type qui a contaminé S1 pendant des mois."""
    section("R1 — INVARIANT DE CAUSALITÉ SUR PLUSIEURS POINTS DE GRILLE")
    sym = symbols[0]
    df = load_bars(sym, "H1")
    combos = [{"variant": v, "rsi_band": rb, "adx_max": ax, "sl_atr": sl, "rr": rr}
              for v in VARIANTS for rb in (30, 40) for ax in (25, 50)
              for sl in (1.5, 2.5) for rr in (1.0, 2.0)]
    bad = 0
    for c in combos:
        rep = causality_check(_fit(sym, c), df, sym)
        if not rep.ok:
            bad += 1
            print(f"  {c}  -> *** FUITE ***")
            for cut in rep.cuts:
                if not cut.ok:
                    print(f"      {cut.fraction:.0%} : {cut.first_divergence}")
    print(f"  {len(combos)} combinaisons testées sur {sym} ({len(df)} barres) — "
          f"{len(combos)-bad} OK, {bad} en fuite.")
    print("  VERDICT R1 :", "PASSÉ" if bad == 0 else "ÉCHOUÉ")
    return bad == 0


# ─────────────────────────────────────────────────────────────────────────────
def full_sample(symbols):
    """Plein échantillon par variante. PAS un critère de validation (aucun hors
    échantillon) : c'est un diagnostic. Il porte aussi le test de fidélité
    (durée de détention) fixé en Phase 1."""
    section("DIAGNOSTIC PLEIN ÉCHANTILLON (pas un critère — voir walk-forward)")
    print(f"  {'sym':<9}{'variante':<10}{'n':>6}{'R':>9}{'R/trade':>10}{'WR%':>7}"
          f"{'PF':>7}{'risqPips':>10}{'drag%':>8}{'TPn':>6}{'TPméd h':>9}{'TPp75 h':>9}")
    print("  " + "-" * 100)
    agg = defaultdict(list)
    holds = defaultdict(list)
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        for v in VARIANTS:
            res = _full_run(sym, df, spec, {"variant": v})
            if not res.trades:
                continue
            risk = np.median([t.risk_distance for t in res.trades]) / spec.pip
            drag = 100 * spec.spread_pips / risk
            tp = [t.bars_held for t in res.trades if t.exit_reason == "TP"]
            pf = res.profit_factor
            print(f"  {sym:<9}{v:<10}{res.n_trades:>6}{res.total_r:>+9.1f}"
                  f"{res.total_r/res.n_trades:>+10.4f}{res.win_rate:>7.1f}"
                  f"{(pf if pf else 0):>7.2f}{risk:>10.1f}{drag:>8.2f}{len(tp):>6}"
                  f"{(np.median(tp) if tp else 0):>9.0f}"
                  f"{(np.percentile(tp, 75) if tp else 0):>9.0f}")
            agg[v].append(res.total_r / res.n_trades)
            holds[v].extend(tp)
        print()

    print("  Espérance moyenne par trade (R), moyenne sur les instruments :")
    print(f"    {'variante':<12}{'R/trade moyen':>16}{'instr. positifs':>18}")
    for v in VARIANTS:
        val = agg.get(v, [])
        if not val:
            continue
        print(f"    {v:<12}{np.mean(val):>+16.4f}"
              f"{sum(1 for x in val if x > 0):>13}/{len(val)}")
    print()
    print("  Seuil de rentabilité brut = 0.0000 R/trade. Le péage du spread est")
    print("  DÉJÀ inclus (le moteur le facture à l'entrée ET à la sortie).")

    print()
    print("  TEST DE FIDÉLITÉ (critère fixé en Phase 1, AVANT les résultats) :")
    print("  S1 est une stratégie H1 avec SL/TP à 1,5-4 ATR. La détention médiane")
    print("  des GAGNANTS doit tomber entre quelques heures et quelques jours.")
    print("  Sinon l'implémentation ne teste pas S1 -> verdict NON REPRODUCTIBLE.")
    for v in VARIANTS:
        hh = holds.get(v, [])
        if not hh:
            continue
        print(f"    {v:<12} médiane {np.median(hh):>5.0f} h  "
              f"({np.median(hh)/24:>4.1f} j)   p90 {np.percentile(hh,90):>5.0f} h  "
              f"({np.percentile(hh,90)/24:>4.1f} j)   n={len(hh)}")


# ─────────────────────────────────────────────────────────────────────────────
def walk_forward(symbols):
    section("WALK-FORWARD ANCRÉ — 4 fenêtres, hors échantillon")
    reports = {}
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s = _fit(sym, None)
        print(f"\n>>> {sym} — {len(df)} barres H1", flush=True)
        rep = run_walk_forward(s, df, spec, min_trades=MIN_TRADES,
                               max_dd_r=MAX_DD_R, verbose=True)
        print(rep.render(top=8))
        reports[sym] = rep
    return reports


def synthesis(reports):
    section("SYNTHÈSE — TABLEAU PAR INSTRUMENT")
    n_cfg = next(iter(reports.values())).n_configs
    chance = n_cfg * 0.05
    print(f"  Grille : {n_cfg} configurations par instrument.")
    print(f"  Un edge NUL produirait ~{chance:.1f} « STRICT pass » par pur hasard.")
    print()
    print(f"  {'instrument':<12}{'STRICT':>8}{'attendu':>9}{'TIER1':>8}"
          f"{'trades OOS':>12}{'moy OOS R':>11}{'meilleur moy':>14}")
    print("  " + "-" * 76)
    tot = 0
    for sym, rep in reports.items():
        s, t = rep.strict(), rep.tier1()
        oos = [r.total_test_trades for r in rep.results]
        best = max(rep.results, key=lambda r: r.avg_oos)
        allavg = np.mean([r.avg_oos for r in rep.results])
        tot += len(s)
        print(f"  {sym:<12}{len(s):>8}{chance:>9.1f}{len(t):>8}"
              f"{int(np.median(oos)):>12}{allavg:>+11.2f}{best.avg_oos:>+14.2f}")
    print("  " + "-" * 76)
    print(f"  {'TOTAL':<12}{tot:>8}{chance*len(reports):>9.1f}")
    print()
    print("  « trades OOS » = médiane, sur la grille, des trades hors échantillon")
    print(f"  cumulés sur les 4 fenêtres. Seuil de crédibilité : {MIN_TRADES}.")
    return tot, chance * len(reports)


def robustness(reports):
    section("ROBUSTESSE — LA MEILLEURE CELLULE EST-ELLE ISOLÉE ?")
    print("  Un edge réel survit au déplacement d'un paramètre. Si seule la")
    print("  cellule optimale est positive, c'est du sur-ajustement.")
    print()
    for sym, rep in reports.items():
        best = max(rep.results, key=lambda r: r.avg_oos)
        neigh = [r for r in rep.results
                 if sum(1 for k in best.params if r.params.get(k) != best.params[k]) == 1]
        pos = sum(1 for r in neigh if r.avg_oos > 0)
        print(f"  {sym:<9} meilleure = {best.label}")
        print(f"            moy OOS {best.avg_oos:+.2f} R sur "
              f"{best.total_test_trades} trades ; voisins positifs : {pos}/{len(neigh)}")
    print()
    print("  Référence : si le signe était aléatoire, on attendrait ~50 %.")


def concentration(reports):
    section("CONCENTRATION — LE RÉSULTAT TIENT-IL À UN SEUL INSTRUMENT ?")
    contrib = {s: max(r.avg_oos for r in rep.results) for s, rep in reports.items()}
    tot = sum(v for v in contrib.values() if v > 0)
    print(f"  {'instrument':<12}{'meilleure moy OOS':>20}{'part du positif':>20}")
    print("  " + "-" * 54)
    for k, v in sorted(contrib.items(), key=lambda x: -x[1]):
        share = f"{100*v/tot:.0f} %" if v > 0 and tot > 0 else "-"
        print(f"  {k:<12}{v:>+20.2f}{share:>20}")


# ─────────────────────────────────────────────────────────────────────────────
def spread_ablation(symbols):
    """Le diagnostic le plus informatif de s01 (§5.1).

    Mêmes signaux, même moteur, `spread_pips` mis à zéro. Sépare deux
    diagnostics qui appellent des décisions OPPOSÉES :
      * espérance ≈ 0 à spread nul  -> le signal n'a pas d'edge, rien à sauver
      * espérance > 0 à spread nul  -> l'edge existe mais les coûts le mangent
                                       (changer de TF / d'instrument peut aider)
    """
    section("ABLATION DU SPREAD — « pas d'edge » ou « edge mangé par les coûts » ?")
    print(f"  {'sym':<9}{'variante':<10}{'n':>6}{'R/tr réel':>12}{'R/tr spread=0':>15}"
          f"{'coût':>10}{'WR réel':>9}{'WR sp=0':>9}")
    print("  " + "-" * 84)
    real, zero = [], []
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        spec0 = dataclasses.replace(spec, spread_pips=0.0)
        for v in VARIANTS:
            a = _full_run(sym, df, spec, {"variant": v})
            b = _full_run(sym, df, spec0, {"variant": v})
            if not a.trades or not b.trades:
                continue
            ra, rb = a.total_r / a.n_trades, b.total_r / b.n_trades
            real.append(ra)
            zero.append(rb)
            print(f"  {sym:<9}{v:<10}{a.n_trades:>6}{ra:>+12.4f}{rb:>+15.4f}"
                  f"{ra-rb:>+10.4f}{a.win_rate:>9.1f}{b.win_rate:>9.1f}")
        print()
    print("  " + "-" * 84)
    print(f"  {'MOYENNE':<19}{len(real):>6}{np.mean(real):>+12.4f}"
          f"{np.mean(zero):>+15.4f}{np.mean(real)-np.mean(zero):>+10.4f}")
    print(f"  cellules positives : {sum(1 for x in real if x > 0)}/{len(real)} "
          f"au spread réel, {sum(1 for x in zero if x > 0)}/{len(zero)} à spread nul.")
    print()
    print("  Lecture : à spread nul, une pièce non biaisée donnerait ~50 % de")
    print("  cellules positives et une espérance de 0,0000 R/trade.")


def long_short_control(symbols):
    """Contrôle directionnel — obligatoire sur 2021-2026.

    s01 a attrapé USDJPY exactement comme ça : +69,7 R du côté long, −10,0 R du
    côté short, soit un pari sur la hausse du dollar-yen déguisé en système.
    Ici le risque est maximal : SP500, NIKKEI et FTSE sont des indices actions
    sur une période de bull market séculaire.
    """
    section("CONTRÔLE LONG/SHORT — l'edge est-il un pari directionnel déguisé ?")
    print("  Une stratégie de RETOUR À LA MOYENNE ne doit pas avoir de côté")
    print("  préféré. Si tout le résultat vient d'un seul sens sur 2021-2026,")
    print("  c'est du beta sur le régime, pas un edge.")
    print()
    print(f"  {'sym':<9}{'variante':<10}{'nL':>5}{'R long':>10}{'R/tr L':>10}"
          f"{'nS':>6}{'R short':>10}{'R/tr S':>10}{'diagnostic':>22}")
    print("  " + "-" * 94)
    from core.contracts.strategy import Side
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        for v in VARIANTS:
            res = _full_run(sym, df, spec, {"variant": v})
            L = [t for t in res.trades if t.side == Side.LONG]
            S = [t for t in res.trades if t.side == Side.SHORT]
            if not L or not S:
                continue
            rl, rs = sum(t.pnl_r for t in L), sum(t.pnl_r for t in S)
            el, es = rl / len(L), rs / len(S)
            if el > 0 and es > 0:
                diag = "symétrique"
            elif el > 0 or es > 0:
                diag = "UN SEUL CÔTÉ"
            else:
                diag = "négatif des 2 côtés"
            print(f"  {sym:<9}{v:<10}{len(L):>5}{rl:>+10.1f}{el:>+10.4f}"
                  f"{len(S):>6}{rs:>+10.1f}{es:>+10.4f}{diag:>22}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
def main():
    symbols = Strategy().manifest().symbols
    print("s10_legacy_meanrev (Legacy S1) — WALK-FORWARD ANCRÉ ET DIAGNOSTICS")
    print(f"instruments : {', '.join(symbols)}")
    print("TF : H1   |   variantes : DIV_SR, DIV_NOSR, HIST_INF")
    print(f"critères : Tier1 = PnL train > 0, >= {MIN_TRADES} trades, DD <= {MAX_DD_R} R")
    print()
    print("AVERTISSEMENT : tous les chiffres S1 antérieurs au 15.08.2026 sont")
    print("contaminés par un lookahead (clôture résiduelle à closes[-1]). Ils ne")
    print("servent ici QUE de point de comparaison. Voir research/ANALYSIS.md §0.")

    if not causality_sweep(symbols):
        print("\nR1 ÉCHOUÉ — arrêt. Aucun résultat n'est publiable.")
        return 1

    full_sample(symbols)
    reports = walk_forward(symbols)
    synthesis(reports)
    robustness(reports)
    concentration(reports)
    spread_ablation(symbols)
    long_short_control(symbols)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
