"""
Walk-forward ancré + diagnostics — s91_claude_scratch.

    python strategies/s91_claude_scratch/backtests/run_wf.py > backtests/anchored_wf.txt

N'implémente AUCUN moteur (R9) : tout passe par `core.backtest.anchored_wf` et
`core.backtest.engine`. Ce script orchestre et imprime les diagnostics que la
méthodologie du projet exige, plus les cinq conditions de falsification
déclarées AVANT le backtest dans `research/ANALYSIS.md` §6 :

  F1  espérance brute à spread NUL <= 0 sur les 4 éligibles   -> H91 réfutée
  F2  les 2 paires JPY ne font pas moins bien que les 4       -> H91 réfutée
  F3  STRICT <= hasard (54 x 0,05 x 4 = 10,8)                 -> H91 réfutée
  F4  résultat porté par 1 instrument (>60 %) ou 1 seul sens  -> non concluant
  F5  effectif OOS médian < 20 par instrument                 -> non concluant
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

from core.backtest.anchored_wf import run_walk_forward          # noqa: E402
from core.backtest.engine import run as run_engine              # noqa: E402
from core.data.instruments import get_spec                      # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from core.validation.causality import check as causality_check  # noqa: E402
from strategies.S091_claude_scratch.strategy import (            # noqa: E402
    CONTROL_JPY, ELIGIBLE, Strategy,
)

MIN_TRADES = 20
MAX_DD_R = 12.0
ALL_SYMBOLS = ELIGIBLE + CONTROL_JPY


def rule(c="=", n=100):
    print(c * n)


def section(t):
    print()
    rule()
    print(t)
    rule()


def _bars(sym):
    return load_bars(sym, "H1")


def _run(sym, params, spec=None):
    """Un plein échantillon pour une cellule. Passe par le moteur commun."""
    df = _bars(sym)
    spec = spec or get_spec(sym)
    s = Strategy(params)
    s._symbol = sym
    return run_engine(s.generate_signals(s.precompute(df, s.params), s.params,
                                         len(df)), df, spec)


# ─────────────────────────────────────────────────────────────────────────────
def causality_sweep():
    """R1 sur plusieurs coins de la grille. Un test qui ne couvre que les
    paramètres par défaut ne prouve rien sur les 53 autres cellules."""
    section("R1 — INVARIANT DE CAUSALITÉ SUR PLUSIEURS POINTS DE LA GRILLE")
    df = _bars(ALL_SYMBOLS[0])
    combos = [{"z_min": z, "sl_atr": k, "rr": r, "window": w}
              for z in (1.5, 2.0, 2.5) for k in (2.0, 3.0)
              for r in (0.75, 1.5) for w in ("large", "etroite")]
    bad = 0
    for c in combos:
        s = Strategy(c)
        s._symbol = ALL_SYMBOLS[0]
        rep = causality_check(s, df, ALL_SYMBOLS[0])
        if not rep.ok:
            bad += 1
            print(f"  {c}  -> *** FUITE ***")
            for cut in rep.cuts:
                if not cut.ok:
                    print(f"      {cut.fraction:.0%} : {cut.first_divergence}")
    print(f"  {len(combos)} combinaisons testées sur {ALL_SYMBOLS[0]} "
          f"({len(df)} barres) — {len(combos)-bad} OK, {bad} en fuite.")
    print("  VERDICT R1 :", "PASSÉ" if bad == 0 else "ÉCHOUÉ")
    return bad == 0


# ─────────────────────────────────────────────────────────────────────────────
def full_sample_and_ablation():
    """Plein échantillon, spread réel vs spread nul, et contrôle long/short.

    Porte F1 (le signal existe-t-il seulement, hors coûts ?) et F2 (le clivage
    JPY prédit par le mécanisme est-il là ?).
    """
    section("DIAGNOSTIC PLEIN ÉCHANTILLON + ABLATION DU SPREAD + CONTRÔLE LONG/SHORT")
    print("  Ce n'est PAS un critère de validation (aucun hors-échantillon).")
    print("  C'est le diagnostic qui dit d'où vient le comportement.")
    print()
    print("  Cellule : configuration PAR DÉFAUT (z_min 2.0, sl_atr 2.5, rr 1.0,")
    print("  fenêtre large). Choisie en Phase 1, pas après coup.")
    print()
    hdr = (f"  {'instrument':<10}{'groupe':<10}{'n':>6}{'R réel':>9}{'R/tr réel':>11}"
           f"{'R/tr nul':>10}{'coût':>9}{'WR%':>7}{'PF':>6}"
           f"{'nL':>5}{'R/tr L':>9}{'nS':>5}{'R/tr S':>9}")
    print(hdr)
    print("  " + "-" * 98)

    stats = {}
    for sym in ALL_SYMBOLS:
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE"
        spec = get_spec(sym)
        res = _run(sym, {})
        free = _run(sym, {}, dataclasses.replace(spec, spread_pips=0.0))
        if not res.trades:
            print(f"  {sym:<10}{grp:<10}   aucun trade")
            continue
        rpt = res.total_r / res.n_trades
        rpt0 = free.total_r / free.n_trades if free.n_trades else np.nan
        L = [t.pnl_r for t in res.trades if t.side.value == "LONG"]
        S = [t.pnl_r for t in res.trades if t.side.value == "SHORT"]
        pf = res.profit_factor or 0.0
        stats[sym] = dict(grp=grp, n=res.n_trades, rpt=rpt, rpt0=rpt0,
                          L=np.mean(L) if L else np.nan,
                          S=np.mean(S) if S else np.nan,
                          total=res.total_r)
        print(f"  {sym:<10}{grp:<10}{res.n_trades:>6}{res.total_r:>+9.1f}{rpt:>+11.4f}"
              f"{rpt0:>+10.4f}{rpt0-rpt:>+9.4f}{res.win_rate:>7.1f}{pf:>6.2f}"
              f"{len(L):>5}{(np.mean(L) if L else np.nan):>+9.4f}"
              f"{len(S):>5}{(np.mean(S) if S else np.nan):>+9.4f}")

    el = [stats[s] for s in ELIGIBLE if s in stats]
    ct = [stats[s] for s in CONTROL_JPY if s in stats]
    print("  " + "-" * 98)
    print(f"  {'MOY ÉLIGIBLE':<20}{sum(d['n'] for d in el):>6}"
          f"{'':>9}{np.mean([d['rpt'] for d in el]):>+11.4f}"
          f"{np.mean([d['rpt0'] for d in el]):>+10.4f}")
    print(f"  {'MOY CONTRÔLE JPY':<20}{sum(d['n'] for d in ct):>6}"
          f"{'':>9}{np.mean([d['rpt'] for d in ct]):>+11.4f}"
          f"{np.mean([d['rpt0'] for d in ct]):>+10.4f}")

    print()
    print("  --- F1 : le signal existe-t-il hors coûts ? ---")
    m0 = np.mean([d["rpt0"] for d in el])
    print(f"  Espérance brute à SPREAD NUL, moyenne sur les 4 éligibles : {m0:+.4f} R/trade")
    print(f"  F1 déclenchée (<= 0) : {'OUI -> H91 RÉFUTÉE' if m0 <= 0 else 'non'}")
    print()
    print("  --- F2 : le clivage JPY prédit par le mécanisme ---")
    me, mc = np.mean([d["rpt"] for d in el]), np.mean([d["rpt"] for d in ct])
    print(f"  R/trade éligibles {me:+.4f}  vs  contrôle JPY {mc:+.4f}  "
          f"(écart {me-mc:+.4f})")
    print(f"  F2 déclenchée (JPY >= éligibles) : "
          f"{'OUI -> mécanisme faux' if mc >= me else 'non'}")
    print()
    print("  --- F4a : contrôle directionnel ---")
    for sym, d in stats.items():
        same = (d["L"] > 0) == (d["S"] > 0)
        print(f"  {sym:<10} long {d['L']:+.4f}  short {d['S']:+.4f}   "
              f"{'cohérent' if same else '*** un seul sens porte le résultat ***'}")
    return stats


# ─────────────────────────────────────────────────────────────────────────────
def walk_forward():
    section("WALK-FORWARD ANCRÉ — 4 fenêtres, hors échantillon")
    reports = {}
    for sym in ALL_SYMBOLS:
        df = _bars(sym)
        s = Strategy()
        s._symbol = sym
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        print(f"\n>>> {sym} [{grp}] — {len(df)} barres H1", flush=True)
        rep = run_walk_forward(s, df, get_spec(sym), min_trades=MIN_TRADES,
                               max_dd_r=MAX_DD_R, verbose=True)
        print(rep.render(top=8))
        reports[sym] = rep
    return reports


def synthesis(reports):
    section("SYNTHÈSE — TABLEAU PAR INSTRUMENT (F3, F5)")
    n_cfg = next(iter(reports.values())).n_configs
    chance = n_cfg * 0.05
    print(f"  Grille : {n_cfg} configurations par instrument.")
    print(f"  Un edge NUL produirait ~{chance:.1f} « STRICT pass » par instrument")
    print(f"  par pur hasard, soit ~{chance*len(ELIGIBLE):.1f} sur les 4 éligibles.")
    print()
    print(f"  {'instrument':<11}{'groupe':<14}{'STRICT':>8}{'attendu':>9}{'TIER1':>7}"
          f"{'trades OOS':>12}{'moy OOS R':>11}{'meilleur':>10}")
    print("  " + "-" * 82)
    strict_el = strict_ct = 0
    oos_med = {}
    for sym, rep in reports.items():
        s, t = rep.strict(), rep.tier1()
        oos = [r.total_test_trades for r in rep.results]
        oos_med[sym] = int(np.median(oos))
        best = max(rep.results, key=lambda r: r.avg_oos)
        allavg = np.mean([r.avg_oos for r in rep.results])
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        if sym in ELIGIBLE:
            strict_el += len(s)
        else:
            strict_ct += len(s)
        print(f"  {sym:<11}{grp:<14}{len(s):>8}{chance:>9.1f}{len(t):>7}"
              f"{oos_med[sym]:>12}{allavg:>+11.2f}{best.avg_oos:>+10.2f}")
    print("  " + "-" * 82)
    print(f"  {'TOTAL ÉLIGIBLE':<25}{strict_el:>8}{chance*len(ELIGIBLE):>9.1f}")
    print(f"  {'TOTAL CONTRÔLE JPY':<25}{strict_ct:>8}{chance*len(CONTROL_JPY):>9.1f}")
    print()
    print("  --- F3 : STRICT contre hasard, sur les éligibles ---")
    print(f"  observé {strict_el}  vs  attendu {chance*len(ELIGIBLE):.1f}")
    print(f"  F3 déclenchée (<= hasard) : "
          f"{'OUI -> H91 RÉFUTÉE' if strict_el <= chance*len(ELIGIBLE) else 'non'}")
    print()
    print("  --- F5 : puissance statistique ---")
    med = int(np.median([oos_med[s] for s in ELIGIBLE]))
    print(f"  Effectif OOS médian sur les éligibles : {med} trades (seuil {MIN_TRADES})")
    print(f"  F5 déclenchée (< {MIN_TRADES}) : "
          f"{'OUI -> NON CONCLUANT' if med < MIN_TRADES else 'non'}")


def robustness(reports):
    section("ROBUSTESSE — LA MEILLEURE CELLULE EST-ELLE ISOLÉE ?")
    print("  Un edge réel survit au déplacement d'un paramètre. Si seule la")
    print("  cellule optimale est positive, c'est du sur-ajustement.")
    print("  Référence : si le signe était aléatoire, ~50 % de voisins positifs.")
    print()
    for sym, rep in reports.items():
        best = max(rep.results, key=lambda r: r.avg_oos)
        neigh = [r for r in rep.results
                 if sum(1 for k in best.params if r.params.get(k) != best.params[k]) == 1]
        pos = sum(1 for r in neigh if r.avg_oos > 0)
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE"
        print(f"  {sym:<10}[{grp}] meilleure = {best.label}")
        print(f"            moy OOS {best.avg_oos:+.2f} R sur "
              f"{best.total_test_trades} trades ; voisins positifs : "
              f"{pos}/{len(neigh)}")


def concentration(reports):
    section("CONCENTRATION — LE RÉSULTAT TIENT-IL À UN SEUL INSTRUMENT ? (F4b)")
    contrib = {s: max(r.avg_oos for r in rep.results) for s, rep in reports.items()}
    el = {k: v for k, v in contrib.items() if k in ELIGIBLE}
    pos = {k: v for k, v in el.items() if v > 0}
    tot = sum(pos.values())
    print(f"  {'instrument':<12}{'groupe':<14}{'meilleure moy OOS':>20}{'part éligible':>16}")
    print("  " + "-" * 64)
    for k, v in sorted(contrib.items(), key=lambda x: -x[1]):
        grp = "ÉLIGIBLE" if k in ELIGIBLE else "CONTRÔLE JPY"
        share = f"{100*v/tot:.0f} %" if (k in pos and tot > 0) else "-"
        print(f"  {k:<12}{grp:<14}{v:>+20.2f}{share:>16}")
    print()
    if tot > 0:
        top = max(pos.values()) / tot
        print(f"  Part du plus gros contributeur éligible : {100*top:.0f} %")
        print(f"  F4b déclenchée (> 60 %) : "
              f"{'OUI -> NON CONCLUANT' if top > 0.60 else 'non'}")
    else:
        print("  Aucun instrument éligible avec une moyenne OOS positive.")
        print("  F4b sans objet : il n'y a pas de résultat positif à concentrer.")


def main():
    print("s91_claude_scratch — ASIAN-WINDOW FADE (H91) — WALK-FORWARD ET DIAGNOSTICS")
    print(f"éligibles     : {', '.join(ELIGIBLE)}")
    print(f"contrôle JPY  : {', '.join(CONTROL_JPY)}  (H91 prédit qu'ils ÉCHOUENT)")
    print("timeframe     : H1   |   fenêtre = heure SERVEUR 22-06h (ou 23-04h)")
    print(f"critères      : Tier1 = PnL train > 0, >= {MIN_TRADES} trades, DD <= {MAX_DD_R} R")
    print()
    print("Conditions de falsification déclarées AVANT ce run — ANALYSIS.md §6.")

    if not causality_sweep():
        print("\nR1 ÉCHOUÉ — arrêt. Aucun résultat n'est publiable.")
        return 1

    full_sample_and_ablation()
    reports = walk_forward()
    synthesis(reports)
    robustness(reports)
    concentration(reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
