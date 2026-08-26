"""
Walk-forward ancré + diagnostics — s01_fxalexg_swing.

    python strategies/s01_fxalexg_swing/backtests/run_wf.py > backtests/anchored_wf.txt

N'implémente AUCUN moteur (R9) : tout passe par `core.backtest.anchored_wf` et
`core.backtest.engine`. Ce script se contente d'orchestrer et d'imprimer les
diagnostics que la méthodologie du projet exige :

  * effectif hors échantillon SYSTÉMATIQUE
  * comparaison au nombre de réussites attendues par pur hasard
  * robustesse au voisinage de la meilleure configuration
  * concentration du résultat sur un instrument
  * péage du spread recalculé sur la distance de risque RÉELLEMENT observée
  * durée de détention réelle (test de fidélité à la source)
  * R1 rejoué sur plusieurs points de la grille, pas seulement le défaut
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

from core.backtest.anchored_wf import run_walk_forward          # noqa: E402
from core.backtest.engine import run as run_engine              # noqa: E402
from core.data.instruments import get_spec                      # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from core.validation.causality import check as causality_check  # noqa: E402
from strategies.S001_fxalexg_swing.strategy import Strategy      # noqa: E402

MIN_TRADES = 20
MAX_DD_R = 12.0


def rule(c="=", n=96):
    print(c * n)


def section(title):
    print()
    rule()
    print(title)
    rule()


# ─────────────────────────────────────────────────────────────────────────────
def causality_sweep(symbols):
    """R1 sur plusieurs coins de la grille — un test qui ne couvre que les
    paramètres par défaut ne prouve rien sur les 127 autres cellules."""
    section("R1 — INVARIANT DE CAUSALITÉ SUR PLUSIEURS POINTS DE GRILLE")
    df = load_bars(symbols[0], "H1")
    combos = [
        {"htf": h, "k_htf": kh, "k_ltf": kl, "target": t}
        for h in ("H4", "D1") for kh in (2, 3) for kl in (2, 3)
        for t in ("struct", "ext27", "ext62", "rr3")
    ]
    bad = 0
    for c in combos:
        s = Strategy(c)
        s._symbol = symbols[0]
        rep = causality_check(s, df, symbols[0])
        tag = "OK" if rep.ok else "*** FUITE ***"
        if not rep.ok:
            bad += 1
            print(f"  {c}  -> {tag}")
            for cut in rep.cuts:
                if not cut.ok:
                    print(f"      {cut.fraction:.0%} : {cut.first_divergence}")
    print(f"  {len(combos)} combinaisons testées sur {symbols[0]} "
          f"({len(df)} barres) — {len(combos)-bad} OK, {bad} en fuite.")
    print("  VERDICT R1 :", "PASSÉ" if bad == 0 else "ÉCHOUÉ")
    return bad == 0


# ─────────────────────────────────────────────────────────────────────────────
def full_sample(symbols):
    """Statistiques plein échantillon par mode de cible.

    Ce n'est PAS un critère de validation (pas de hors-échantillon), c'est un
    diagnostic : il dit d'où vient le comportement, et il porte le test de
    fidélité (durée de détention)."""
    section("DIAGNOSTIC PLEIN ÉCHANTILLON (pas un critère — voir walk-forward)")
    print(f"  {'sym':<8}{'htf':<5}{'target':<8}{'n':>6}{'R':>9}{'R/trade':>9}"
          f"{'WR%':>7}{'PF':>7}{'risqPips':>10}{'drag%':>7}"
          f"{'TPn':>6}{'TPmed j':>9}{'TPp75 j':>9}")
    print("  " + "-" * 92)
    agg = defaultdict(list)
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        for htf in ("H4", "D1"):
            for tgt in ("struct", "ext27", "ext62", "rr3"):
                s = Strategy({"htf": htf, "target": tgt})
                s._symbol = sym
                p = s.params
                res = run_engine(s.generate_signals(s.precompute(df, p), p, len(df)),
                                 df, spec)
                if not res.trades:
                    continue
                risk = np.median([t.risk_distance for t in res.trades]) / spec.pip
                drag = 100 * spec.spread_pips / risk
                tp = [t.bars_held for t in res.trades if t.exit_reason == "TP"]
                pf = res.profit_factor
                print(f"  {sym:<8}{htf:<5}{tgt:<8}{res.n_trades:>6}"
                      f"{res.total_r:>+9.1f}{res.total_r/res.n_trades:>+9.3f}"
                      f"{res.win_rate:>7.1f}{(pf if pf else 0):>7.2f}"
                      f"{risk:>10.1f}{drag:>7.2f}"
                      f"{len(tp):>6}"
                      f"{(np.median(tp)/24 if tp else 0):>9.1f}"
                      f"{(np.percentile(tp,75)/24 if tp else 0):>9.1f}")
                agg[(htf, tgt)].append(res.total_r / res.n_trades)
        print()

    print("  Espérance moyenne par trade (R), moyenne sur les 7 instruments :")
    print(f"    {'htf':<5}{'target':<10}{'R/trade moyen':>15}{'instr. positifs':>18}")
    for (htf, tgt), v in sorted(agg.items()):
        print(f"    {htf:<5}{tgt:<10}{np.mean(v):>+15.4f}"
              f"{sum(1 for x in v if x > 0):>13}/{len(v)}")
    print()
    print("  Rappel : seuil de rentabilité brut = 0.000 R/trade. Le péage du")
    print("  spread est DÉJÀ inclus (le moteur le facture à l'entrée et à la sortie).")


# ─────────────────────────────────────────────────────────────────────────────
def walk_forward(symbols):
    section("WALK-FORWARD ANCRÉ — 4 fenêtres, hors échantillon")
    reports = {}
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s = Strategy()
        s._symbol = sym
        print(f"\n>>> {sym} — {len(df)} barres H1", flush=True)
        rep = run_walk_forward(s, df, spec,
                               min_trades=MIN_TRADES, max_dd_r=MAX_DD_R,
                               verbose=True)
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
    tot_strict = 0
    for sym, rep in reports.items():
        s = rep.strict()
        t = rep.tier1()
        oos = [r.total_test_trades for r in rep.results]
        best = max(rep.results, key=lambda r: r.avg_oos)
        allavg = np.mean([r.avg_oos for r in rep.results])
        tot_strict += len(s)
        print(f"  {sym:<12}{len(s):>8}{chance:>9.1f}{len(t):>8}"
              f"{int(np.median(oos)):>12}{allavg:>+11.2f}{best.avg_oos:>+14.2f}")
    print("  " + "-" * 76)
    print(f"  {'TOTAL':<12}{tot_strict:>8}{chance*len(reports):>9.1f}")
    print()
    print("  « trades OOS » = médiane, sur la grille, du nombre de trades hors")
    print(f"  échantillon cumulés sur les 4 fenêtres. Seuil de crédibilité : {MIN_TRADES}.")


def robustness(reports):
    section("ROBUSTESSE — LA MEILLEURE CELLULE EST-ELLE ISOLÉE ?")
    print("  Un edge réel survit au déplacement d'un paramètre. Si seule la")
    print("  cellule optimale est positive, c'est du sur-ajustement.")
    print()
    for sym, rep in reports.items():
        best = max(rep.results, key=lambda r: r.avg_oos)
        neigh = []
        for r in rep.results:
            diff = sum(1 for k in best.params
                       if r.params.get(k) != best.params[k])
            if diff == 1:
                neigh.append(r)
        pos = sum(1 for r in neigh if r.avg_oos > 0)
        print(f"  {sym:<9} meilleure = {best.label}")
        print(f"            moy OOS {best.avg_oos:+.2f} R sur {best.total_test_trades} trades ; "
              f"voisins immédiats positifs : {pos}/{len(neigh)}")
    print()
    print("  Référence : si le signe du résultat était aléatoire, on attendrait")
    print("  ~50 % de voisins positifs.")


def concentration(reports):
    section("CONCENTRATION — LE RÉSULTAT TIENT-IL À UN SEUL INSTRUMENT ?")
    contrib = {sym: max(r.avg_oos for r in rep.results)
               for sym, rep in reports.items()}
    pos = {k: v for k, v in contrib.items() if v > 0}
    tot = sum(pos.values())
    print(f"  {'instrument':<12}{'meilleure moy OOS':>20}{'part du total positif':>24}")
    print("  " + "-" * 58)
    for k, v in sorted(contrib.items(), key=lambda x: -x[1]):
        share = f"{100*v/tot:.0f} %" if v > 0 and tot > 0 else "-"
        print(f"  {k:<12}{v:>+20.2f}{share:>24}")


def main():
    symbols = Strategy().manifest().symbols
    print("s01_fxalexg_swing — WALK-FORWARD ANCRÉ ET DIAGNOSTICS")
    print(f"instruments : {', '.join(symbols)}")
    print(f"TF exécution : H1   |   structure : H4 / D1 (rééchantillonnées)")
    print(f"critères : Tier1 = PnL train > 0, >= {MIN_TRADES} trades, DD <= {MAX_DD_R} R")

    ok = causality_sweep(symbols)
    if not ok:
        print("\nR1 ÉCHOUÉ — arrêt. Aucun résultat n'est publiable.")
        return 1

    full_sample(symbols)
    reports = walk_forward(symbols)
    synthesis(reports)
    robustness(reports)
    concentration(reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
