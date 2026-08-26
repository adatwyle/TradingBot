"""
Walk-forward ancré + diagnostics — s11_legacy_breakout.

    python strategies/s11_legacy_breakout/backtests/run_wf.py

N'implémente AUCUN moteur (R9) : tout passe par `core.backtest.anchored_wf` et
`core.backtest.engine`. Ce script orchestre et imprime les diagnostics que la
méthodologie du projet exige, plus celui qui est propre à cette stratégie :

  * R1 rejoué sur 16 points de la grille, pas seulement le défaut
  * effectif hors échantillon SYSTÉMATIQUE
  * comparaison au nombre de réussites attendues par pur hasard
  * comptage des trades « fantômes » (stop franchi par un gap — artefact moteur)
  * ROBUSTESSE DES SEUILS DU FILTRE : matrice 4×4 (er_min × fr_max), la
    question centrale de cette stratégie
  * robustesse au voisinage de la meilleure configuration
  * concentration du résultat sur un instrument
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

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.backtest.anchored_wf import run_walk_forward          # noqa: E402
from core.backtest.engine import run as run_engine              # noqa: E402
from core.data.instruments import get_spec                      # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from core.validation.causality import check as causality_check  # noqa: E402
from strategies.S011_legacy_breakout.strategy import Strategy    # noqa: E402

MIN_TRADES = 20
MAX_DD_R = 12.0

# Bornes du P&L d'un trade « sain » : SL = 1,5 ATR, TP = tp_m × ATR.
# Un trade hors de ces bornes n'est pas un trade de la stratégie — c'est un stop
# franchi par un gap de week-end que le moteur commun ne remplit pas (il exige
# `low <= stop <= high`). Voir la section GAP ci-dessous.
SANE_MIN, SANE_MAX = -1.10, 2.80


def _head():
    """Empreinte du dépôt : sans elle, un résultat n'est pas reproductible —
    `core/` a bougé pendant la production de ce dossier."""
    import subprocess
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "core"],
                                        cwd=ROOT, text=True).strip()
        return f"{sha}{' (core modifié localement)' if dirty else ''}"
    except Exception:
        return "inconnu"


def rule(c="=", n=96):
    print(c * n)


def section(title):
    print()
    rule()
    print(title)
    rule()


def _rpt(res):
    """R/trade — la seule lecture honnête quand on compare des jeux de trades
    d'effectifs différents (un filtre RETIRE des trades : le total baisse
    mécaniquement, ça ne dit rien sur la qualité de ce qui est retiré)."""
    return res.total_r / res.n_trades if res.n_trades else 0.0


# ─────────────────────────────────────────────────────────────────────────────
def causality_sweep(symbols):
    """R1 sur 16 coins de la grille. Un test qui ne couvre que les paramètres
    par défaut ne prouve rien sur les 127 autres cellules — et le point fragile
    de cette stratégie (le décalage d'agrégation de `failed_rate`) dépend
    justement de `donchian` et des seuils."""
    section("R1 — INVARIANT DE CAUSALITÉ SUR 16 POINTS DE GRILLE")
    print("  Point sensible : `failed_rate200` consulte close[j+1..j+3] pour")
    print("  évaluer une cassure ; sa causalité tient au décalage d'agrégation")
    print("  (fenêtre arrêtée à i-4). C'est exactement ce que ce test contrôle.")
    print()
    df = load_bars(symbols[0], "H1")
    combos = [
        {"er_min": e, "fr_max": f, "donchian": d, "tp_m": t}
        for e in (0.00, 0.11) for f in (1.00, 0.50)
        for d in (20, 40) for t in (3.0, 4.0)
    ]
    bad = 0
    for c in combos:
        s = Strategy(c)
        s._symbol = symbols[0]
        rep = causality_check(s, df, symbols[0])
        if not rep.ok:
            bad += 1
            print(f"  {c}  -> *** FUITE ***")
            for cut in rep.cuts:
                if not cut.ok:
                    print(f"      {cut.fraction:.0%} : {cut.first_divergence}")
    print(f"  {len(combos)} combinaisons testées sur {symbols[0]} "
          f"({len(df)} barres) — {len(combos)-bad} OK, {bad} en fuite.")
    print("  VERDICT R1 :", "PASSÉ" if bad == 0 else "ÉCHOUÉ")
    return bad == 0


# ─────────────────────────────────────────────────────────────────────────────
def gap_artifact(symbols):
    """Comptage des trades dont le stop a été franchi par un gap.

    `core/backtest/engine.py` ne déclenche un stop que si `low <= stop <= high`.
    Quand une séance ouvre au-delà du stop, celui-ci n'est JAMAIS rempli et la
    position reste ouverte — potentiellement des années. Le moteur historique
    utilisait un test unilatéral (`low <= stop`) et n'avait pas ce trou.

    Ce n'est pas un défaut de la stratégie, mais ça contamine les instruments à
    séance (indices). Il faut le chiffrer AVANT de lire le moindre résultat.
    """
    section("ARTEFACT DE GAP — stops non remplis par le moteur commun")
    print("  Le moteur exige `low <= stop <= high`. Un gap de week-end qui saute")
    print("  par-dessus le stop ne le remplit pas : la position reste ouverte.")
    print("  Borne d'un trade sain ici : R ∈ [-1,10 ; +2,80].")
    print()
    print(f"  {'sym':<9}{'n':>6}{'R tot':>10}{'R/trade':>10}{'fantômes':>10}"
          f"{'R fantôme':>12}{'R/trade sain':>14}{'max barres':>12}")
    print("  " + "-" * 84)
    s = Strategy()
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s._symbol = sym
        p = dict(s.params)
        p.update({"er_min": 0.0, "fr_max": 1.0})     # témoin sans filtre
        res = run_engine(s.generate_signals(s.precompute(df, p), p, len(df)), df, spec)
        if not res.trades:
            continue
        ph = [t for t in res.trades if not (SANE_MIN <= t.pnl_r <= SANE_MAX)]
        sane = [t for t in res.trades if SANE_MIN <= t.pnl_r <= SANE_MAX]
        print(f"  {sym:<9}{res.n_trades:>6}{res.total_r:>+10.1f}{_rpt(res):>+10.3f}"
              f"{len(ph):>10}{sum(t.pnl_r for t in ph):>+12.1f}"
              f"{(np.mean([t.pnl_r for t in sane]) if sane else 0):>+14.3f}"
              f"{max(t.bars_held for t in res.trades):>12}")
    print()
    print("  Lecture : là où « R fantôme » domine « R tot », le chiffre de")
    print("  l'instrument mesure le moteur, pas la stratégie.")


# ─────────────────────────────────────────────────────────────────────────────
def full_sample(symbols):
    """Plein échantillon — DIAGNOSTIC, pas un critère (aucun hors-échantillon).

    Sert à répondre séparément aux deux hypothèses :
      H1 : le signal de cassure a-t-il un edge SANS filtre ?
      H2 : le filtre au point historique (0,11 ; 0,50) améliore-t-il le R/trade ?
    """
    section("DIAGNOSTIC PLEIN ÉCHANTILLON — H1 (signal seul) vs H2 (filtre historique)")
    print("  « sans filtre » = er_min 0,00 / fr_max 1,00.")
    print("  « filtre hist. » = er_min 0,11 / fr_max 0,50 (valeurs choisies à l'œil).")
    print("  Le filtre se juge sur le R/TRADE : il retire des trades, donc le")
    print("  total baisse mécaniquement — ça ne dit rien sur leur qualité.")
    print()
    print(f"  {'sym':<9}{'n sans':>8}{'R/tr sans':>11}{'WR%':>7}"
          f"{'n filtré':>10}{'R/tr filtré':>13}{'WR%':>7}"
          f"{'Δ R/trade':>12}{'% retirés':>11}")
    print("  " + "-" * 88)
    s = Strategy()
    agg = []
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s._symbol = sym
        out = {}
        for tag, ov in (("off", {"er_min": 0.0, "fr_max": 1.0}),
                        ("hist", {"er_min": 0.11, "fr_max": 0.50})):
            p = dict(s.params)
            p.update(ov)
            out[tag] = run_engine(
                s.generate_signals(s.precompute(df, p), p, len(df)), df, spec)
        a, b = out["off"], out["hist"]
        d = _rpt(b) - _rpt(a)
        agg.append((sym, _rpt(a), _rpt(b), d))
        cut = 100.0 * (1 - b.n_trades / a.n_trades) if a.n_trades else 0.0
        print(f"  {sym:<9}{a.n_trades:>8}{_rpt(a):>+11.3f}{(a.win_rate or 0):>7.1f}"
              f"{b.n_trades:>10}{_rpt(b):>+13.3f}{(b.win_rate or 0):>7.1f}"
              f"{d:>+12.3f}{cut:>11.1f}")
    print("  " + "-" * 88)
    print(f"  {'MOYENNE':<9}{'':>8}{np.mean([x[1] for x in agg]):>+11.3f}{'':>7}"
          f"{'':>10}{np.mean([x[2] for x in agg]):>+13.3f}{'':>7}"
          f"{np.mean([x[3] for x in agg]):>+12.3f}")
    print()
    print(f"  Instruments où le filtre historique AMÉLIORE le R/trade : "
          f"{sum(1 for x in agg if x[3] > 0)}/{len(agg)}   (hasard : {len(agg)/2:.1f})")
    return agg


# ─────────────────────────────────────────────────────────────────────────────
def walk_forward(symbols):
    section("WALK-FORWARD ANCRÉ — 4 fenêtres, hors échantillon, 128 configurations")
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
    print(f"  Un edge NUL produirait ~{chance:.1f} « STRICT pass » par pur hasard,")
    print(f"  soit ~{chance*len(reports):.0f} sur les {len(reports)} instruments.")
    print()
    print(f"  {'instrument':<12}{'STRICT':>8}{'attendu':>9}{'TIER1':>8}"
          f"{'trades OOS':>12}{'moy OOS R':>11}{'meilleur moy':>14}")
    print("  " + "-" * 76)
    tot = 0
    for sym, rep in reports.items():
        s = rep.strict()
        oos = [r.total_test_trades for r in rep.results]
        best = max(rep.results, key=lambda r: r.avg_oos)
        tot += len(s)
        print(f"  {sym:<12}{len(s):>8}{chance:>9.1f}{len(rep.tier1()):>8}"
              f"{int(np.median(oos)):>12}"
              f"{np.mean([r.avg_oos for r in rep.results]):>+11.2f}"
              f"{best.avg_oos:>+14.2f}")
    print("  " + "-" * 76)
    print(f"  {'TOTAL':<12}{tot:>8}{chance*len(reports):>9.1f}")
    print()
    print("  « trades OOS » = médiane, sur la grille, du nombre de trades hors")
    print(f"  échantillon cumulés sur les 4 fenêtres. Seuil de crédibilité : {MIN_TRADES}.")
    return tot, chance * len(reports)


# ─────────────────────────────────────────────────────────────────────────────
def filter_robustness(reports):
    """LE TEST CENTRAL DE CETTE STRATÉGIE.

    Les seuils (0,11 ; 0,50) ont été choisis par inspection visuelle, et un
    contrôle antérieur avait montré que DAX ne passait qu'au point exact. Si
    l'avantage n'existe qu'en ce point, c'est du sur-ajustement, pas un filtre.

    Critère fixé AVANT mesure (ANALYSIS § 6) : robuste seulement si
    l'amélioration reste positive sur la MAJORITÉ du voisinage 3×3.
    """
    section("*** ROBUSTESSE DES SEUILS DU FILTRE — LA QUESTION CENTRALE ***")
    print("  Chaque cellule agrège les 8 configurations de signal (donchian ×")
    print("  adx_min × tp_m) partageant ce couple de seuils, hors échantillon.")
    print("  Métrique : R par TRADE (pas R total — un filtre retire des trades).")
    print()
    print("  er_min=0,00 et fr_max=1,00 DÉSACTIVENT la moitié correspondante du")
    print("  filtre. La cellule (0,00 ; 1,00) est le témoin sans filtre.")

    er_vals = [0.00, 0.09, 0.11, 0.13]
    fr_vals = [1.00, 0.45, 0.50, 0.55]

    def cell_rpt(rep, er, fr):
        tot_r = tot_n = 0.0
        for r in rep.results:
            if abs(r.params["er_min"] - er) < 1e-9 and abs(r.params["fr_max"] - fr) < 1e-9:
                tot_r += sum(r.oos_series)
                tot_n += r.total_test_trades
        return (tot_r / tot_n if tot_n else float("nan")), tot_n

    per_sym = {}
    for sym, rep in reports.items():
        print()
        print(f"  --- {sym} : R/trade hors échantillon (effectif entre parenthèses) ---")
        print("      " + "er_min v / fr_max >".ljust(15)
              + "".join(f"{f:>16.2f}" for f in fr_vals))
        grid = {}
        for er in er_vals:
            row = f"      {er:<15.2f}"
            for fr in fr_vals:
                v, n = cell_rpt(rep, er, fr)
                grid[(er, fr)] = (v, n)
                row += f"{v:>+11.3f}({n:>3})"
            print(row)
        per_sym[sym] = grid
        base = grid[(0.00, 1.00)][0]
        hist = grid[(0.11, 0.50)][0]
        neigh = [grid[(e, f)][0] for e in (0.09, 0.11, 0.13) for f in (0.45, 0.50, 0.55)]
        better = sum(1 for v in neigh if v > base)
        print(f"      témoin sans filtre {base:+.3f} | point historique {hist:+.3f} "
              f"({hist-base:+.3f}) | voisinage 3×3 meilleur que le témoin : {better}/9")

    # ── Agrégation : PIÈGE À ÉVITER ────────────────────────────────────────
    # Moyenner chaque cellule sur « les instruments où elle est finie » compare
    # des jeux d'instruments différents d'une cellule à l'autre. Sur DAX, le
    # témoin sans filtre a ZÉRO trade hors échantillon (la position dont le
    # moteur n'a pas rempli le stop bloque tout le reste), donc le témoin
    # s'agrégerait sur 7 instruments et le filtre sur 8. Le filtre paraîtrait
    # meilleur sans que rien ne l'ait rendu meilleur.
    retained = [s for s in per_sym
                if all(per_sym[s][(e, f)][1] >= MIN_TRADES
                       and np.isfinite(per_sym[s][(e, f)][0])
                       for e in er_vals for f in fr_vals)]
    dropped = [s for s in per_sym if s not in retained]
    print()
    rule("-")
    print(f"  AGRÉGÉ SUR {len(retained)} INSTRUMENTS — moyenne des R/trade hors échantillon")
    rule("-")
    print(f"  Retenus : {', '.join(retained)}")
    if dropped:
        print(f"  ÉCARTÉS : {', '.join(dropped)} — au moins une cellule sous "
              f"{MIN_TRADES} trades hors échantillon.")
        for s in dropped:
            worst = min(per_sym[s][(e, f)][1]
                        for e in er_vals for f in fr_vals)
            print(f"     {s} : cellule la plus mince = {worst} trades. "
                  f"Le comparer cellule par cellule n'a pas de sens.")
    print("  (Toute cellule est moyennée sur EXACTEMENT le même jeu")
    print("   d'instruments — sinon la comparaison est truquée.)")
    print()
    print("      " + "er_min v / fr_max >".ljust(15)
          + "".join(f"{f:>12.2f}" for f in fr_vals))
    agg = {}
    for er in er_vals:
        row = f"      {er:<15.2f}"
        for fr in fr_vals:
            vals = [per_sym[s][(er, fr)][0] for s in retained]
            agg[(er, fr)] = np.mean(vals) if vals else float("nan")
            row += f"{agg[(er, fr)]:>+12.4f}"
        print(row)

    base = agg[(0.00, 1.00)]
    hist = agg[(0.11, 0.50)]
    neigh = {(e, f): agg[(e, f)] for e in (0.09, 0.11, 0.13) for f in (0.45, 0.50, 0.55)}
    better = sum(1 for v in neigh.values() if v > base)
    print()
    print(f"  Témoin sans filtre (0,00 ; 1,00) : {base:+.4f} R/trade")
    print(f"  Point historique   (0,11 ; 0,50) : {hist:+.4f} R/trade  "
          f"({hist-base:+.4f})")
    print(f"  Voisinage 3×3 meilleur que le témoin : {better}/9")
    print()
    print("  Détail du voisinage 3×3 (écart au témoin) :")
    for e in (0.09, 0.11, 0.13):
        print("      " + "  ".join(f"er{e:.2f}/fr{f:.2f} {neigh[(e,f)]-base:+.4f}"
                                   for f in (0.45, 0.50, 0.55)))

    # Décompte instrument par instrument : plus robuste qu'une moyenne, qu'un
    # seul instrument peut dominer.
    print()
    print("  DÉCOMPTE PAR INSTRUMENT (le plus informatif — une moyenne peut être")
    print("  portée par un seul instrument) :")
    print(f"      {'instrument':<12}{'témoin':>10}{'point hist.':>13}{'écart':>10}"
          f"{'voisinage 3×3':>16}")
    print("      " + "-" * 61)
    tot_better = tot_cells = 0
    n_improved = 0
    for s in retained:
        g = per_sym[s]
        b = g[(0.00, 1.00)][0]
        h = g[(0.11, 0.50)][0]
        nb = sum(1 for e in (0.09, 0.11, 0.13) for f in (0.45, 0.50, 0.55)
                 if g[(e, f)][0] > b)
        tot_better += nb
        tot_cells += 9
        n_improved += (h > b)
        print(f"      {s:<12}{b:>+10.3f}{h:>+13.3f}{h-b:>+10.3f}{f'{nb}/9':>16}")
    print("      " + "-" * 61)
    print(f"      Instruments où le point historique améliore : "
          f"{n_improved}/{len(retained)}  (hasard : {len(retained)/2:.1f})")
    print(f"      Cellules du voisinage meilleures que leur témoin : "
          f"{tot_better}/{tot_cells} = {100*tot_better/tot_cells:.0f} %  "
          f"(hasard : 50 %)")
    print()
    robust = (tot_better > tot_cells / 2) and (n_improved > len(retained) / 2)
    if robust and hist > base:
        print("  -> Critère ANALYSIS § 6 : le filtre AMÉLIORE et l'amélioration")
        print("     SURVIT au déplacement des seuils. Non sur-ajusté à ce test.")
    elif hist > base or n_improved > len(retained) / 2:
        print("  -> Critère ANALYSIS § 6 : le point historique améliore MAIS son")
        print("     voisinage ne suit pas. SUR-AJUSTEMENT — le gain n'est pas")
        print("     attribuable au filtre, mais au choix du point.")
    else:
        print("  -> Critère ANALYSIS § 6 : le point historique n'améliore même")
        print("     pas le témoin. H2 est réfutée sans avoir à discuter la")
        print("     robustesse.")
    return agg, base, hist, better


# ─────────────────────────────────────────────────────────────────────────────
def robustness(reports):
    section("ROBUSTESSE — LA MEILLEURE CELLULE EST-ELLE ISOLÉE ?")
    print("  Un edge réel survit au déplacement d'UN paramètre. Si seule la")
    print("  cellule optimale est positive, c'est du sur-ajustement.")
    print("  Référence : si le signe était aléatoire, ~50 % de voisins positifs.")
    print()
    for sym, rep in reports.items():
        best = max(rep.results, key=lambda r: r.avg_oos)
        neigh = [r for r in rep.results
                 if sum(1 for k in ("er_min", "fr_max", "donchian", "adx_min", "tp_m")
                        if r.params[k] != best.params[k]) == 1]
        pos = sum(1 for r in neigh if r.avg_oos > 0)
        print(f"  {sym:<9} meilleure = {best.label}")
        print(f"            moy OOS {best.avg_oos:+.2f} R sur "
              f"{best.total_test_trades} trades ; voisins positifs : {pos}/{len(neigh)}")


def concentration(reports):
    section("CONCENTRATION — LE RÉSULTAT TIENT-IL À UN SEUL INSTRUMENT ?")
    print("  Un book dont 93 % du résultat vient d'un instrument n'est pas un")
    print("  système, c'est un pari (méthodologie projet).")
    print()
    contrib = {s: max(r.avg_oos for r in rep.results) for s, rep in reports.items()}
    tot = sum(v for v in contrib.values() if v > 0)
    print(f"  {'instrument':<12}{'meilleure moy OOS':>20}{'part du total positif':>24}")
    print("  " + "-" * 58)
    for k, v in sorted(contrib.items(), key=lambda x: -x[1]):
        share = f"{100*v/tot:.0f} %" if v > 0 and tot > 0 else "-"
        print(f"  {k:<12}{v:>+20.2f}{share:>24}")


def main():
    symbols = Strategy().manifest().symbols
    print("s11_legacy_breakout — WALK-FORWARD ANCRÉ ET DIAGNOSTICS")
    print(f"instruments : {', '.join(symbols)}")
    print("TF exécution : H1")
    print(f"dépôt (core inclus) : commit {_head()}")
    print(f"critères : Tier1 = PnL train > 0, ≥ {MIN_TRADES} trades, DD ≤ {MAX_DD_R} R")
    print()
    print("AVERTISSEMENT — aucun chiffre S2 antérieur n'est repris : le moteur")
    print("historique valorisait les résiduels à closes[-1] (lookahead). Tout")
    print("ce qui suit est mesuré de zéro.")

    if not causality_sweep(symbols):
        print("\nR1 ÉCHOUÉ — arrêt. Aucun résultat n'est publiable.")
        return 1

    gap_artifact(symbols)
    full_sample(symbols)
    reports = walk_forward(symbols)
    synthesis(reports)
    filter_robustness(reports)
    robustness(reports)
    concentration(reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
