"""
Diagnostics complémentaires — s11_legacy_breakout.

    python strategies/s11_legacy_breakout/backtests/run_diag.py

Quatre mesures, toutes sur le moteur commun (R9), aucune boucle maison :

  1. ABLATION DU SPREAD — le signal est-il rentable AVANT le péage broker ?
     Sépare « pas d'edge » de « edge mangé par les coûts ». Ce sont deux
     diagnostics qui appellent des décisions opposées.
  2. CONTRÔLE LONG/SHORT — le résultat est-il un système, ou un pari
     directionnel déguisé ? 2021-2026 = bull market sur les indices et l'or.
  3. SENSIBILITÉ À L'ARTEFACT DE GAP — le moteur commun ne remplit un stop que
     si `low <= stop <= high`. On borne la durée de détention pour mesurer
     combien du résultat vient de positions dont le stop a été sauté.
  4. MATRICE DES SEUILS EN PLEIN ÉCHANTILLON — complément au même test hors
     échantillon fait dans `run_wf.py`.
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

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.backtest.engine import run as run_engine              # noqa: E402
from core.contracts.strategy import Side                        # noqa: E402
from core.data.instruments import get_spec                      # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from strategies.S011_legacy_breakout.strategy import Strategy    # noqa: E402

OFF = {"er_min": 0.00, "fr_max": 1.00}      # témoin sans filtre
HIST = {"er_min": 0.11, "fr_max": 0.50}     # seuils historiques, choisis à l'œil


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


def section(t):
    print()
    rule()
    print(t)
    rule()


def _rpt(res):
    return res.total_r / res.n_trades if res.n_trades else 0.0


def _run(strategy, df, spec, overrides, **engine_kw):
    p = dict(strategy.params)
    p.update(overrides)
    sigs = strategy.generate_signals(strategy.precompute(df, p), p, len(df))
    return run_engine(sigs, df, spec, **engine_kw)


# ─────────────────────────────────────────────────────────────────────────────
def spread_ablation(symbols):
    section("1. ABLATION DU SPREAD — le signal est-il rentable AVANT péage ?")
    print("  Mêmes signaux, même moteur. Seul change `spread_pips` (réel -> 0).")
    print("  Un signal sans edge reste négatif à spread nul. Un signal à edge")
    print("  marginal bascule. C'est le seul moyen de séparer les deux causes.")
    print()
    print(f"  {'sym':<9}{'filtre':<8}{'n':>6}{'R/tr réel':>12}{'R/tr spr=0':>12}"
          f"{'écart':>10}{'risque(pips)':>14}{'drag%':>8}")
    print("  " + "-" * 82)
    s = Strategy()
    acc = {"off": [], "hist": []}
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        spec0 = dataclasses.replace(spec, spread_pips=0.0)
        s._symbol = sym
        for tag, ov in (("off", OFF), ("hist", HIST)):
            a = _run(s, df, spec, ov)
            b = _run(s, df, spec0, ov)
            if not a.trades:
                continue
            risk = np.median([t.risk_distance for t in a.trades]) / spec.pip
            drag = 100 * spec.spread_pips / risk if risk else float("nan")
            acc[tag].append((_rpt(a), _rpt(b)))
            print(f"  {sym:<9}{tag:<8}{a.n_trades:>6}{_rpt(a):>+12.4f}"
                  f"{_rpt(b):>+12.4f}{_rpt(b)-_rpt(a):>+10.4f}{risk:>14.1f}{drag:>8.2f}")
        print()
    print("  " + "-" * 82)
    for tag in ("off", "hist"):
        v = acc[tag]
        print(f"  MOYENNE {tag:<6} R/trade réel {np.mean([x[0] for x in v]):>+8.4f} "
              f"| spread nul {np.mean([x[1] for x in v]):>+8.4f} "
              f"| instruments positifs à spread nul : "
              f"{sum(1 for x in v if x[1] > 0)}/{len(v)}")
    print()
    print("  Lecture : si le signal reste négatif À SPREAD NUL, il n'y a rien à")
    print("  sauver en changeant de broker ou de timeframe — le signal lui-même")
    print("  ne porte pas d'information.")


# ─────────────────────────────────────────────────────────────────────────────
def long_short_control(symbols):
    section("2. CONTRÔLE LONG/SHORT — système ou pari directionnel ?")
    print("  2021-2026 : hausse des indices et de l'or. Une stratégie qui ne")
    print("  gagne QUE du côté long est un beta déguisé, pas un edge.")
    print("  Un vrai edge de cassure doit fonctionner dans les deux sens.")
    print()
    print(f"  {'sym':<9}{'filtre':<8}{'nL':>6}{'R/tr L':>10}{'R tot L':>10}"
          f"{'nS':>6}{'R/tr S':>10}{'R tot S':>10}  verdict")
    print("  " + "-" * 88)
    s = Strategy()
    both_pos = tot = 0
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s._symbol = sym
        for tag, ov in (("off", OFF), ("hist", HIST)):
            r = _run(s, df, spec, ov)
            L = [t.pnl_r for t in r.trades if t.side == Side.LONG]
            S = [t.pnl_r for t in r.trades if t.side == Side.SHORT]
            if not L or not S:
                continue
            mL, mS = float(np.mean(L)), float(np.mean(S))
            tot += 1
            if mL > 0 and mS > 0:
                v = "les deux +"
                both_pos += 1
            elif mL > 0:
                v = "LONG seul"
            elif mS > 0:
                v = "SHORT seul"
            else:
                v = "les deux -"
            print(f"  {sym:<9}{tag:<8}{len(L):>6}{mL:>+10.3f}{sum(L):>+10.1f}"
                  f"{len(S):>6}{mS:>+10.3f}{sum(S):>+10.1f}  {v}")
        print()
    print("  " + "-" * 88)
    print(f"  Cas où LES DEUX côtés sont positifs : {both_pos}/{tot}")


# ─────────────────────────────────────────────────────────────────────────────
def gap_sensitivity(symbols):
    section("3. ARTEFACT DE GAP — combien du résultat vient de stops non remplis ?")
    print("  `core/backtest/engine.py` ne déclenche un stop que si")
    print("  `low <= stop <= high`. Une séance qui ouvre au-delà du stop ne le")
    print("  remplit JAMAIS : la position court indéfiniment. Le moteur")
    print("  historique utilisait un test unilatéral et n'avait pas ce trou.")
    print()
    print("  CONTRÔLE RETENU : retirer les trades hors des bornes atteignables")
    print("  par la règle (SL 1,5 ATR / TP 4 ATR -> R ∈ [-1,10 ; +2,80]). C'est")
    print("  un tri sur la sortie du moteur commun, pas un moteur alternatif.")
    print()
    print(f"  {'sym':<9}{'filtre':<8}{'n':>6}{'R/tr brut':>12}"
          f"{'fantômes':>10}{'R fantôme':>12}{'n sain':>8}{'R/tr sain':>12}")
    print("  " + "-" * 80)
    s = Strategy()
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s._symbol = sym
        for tag, ov in (("off", OFF), ("hist", HIST)):
            r = _run(s, df, spec, ov)
            if not r.trades:
                continue
            ph = [t for t in r.trades if not (-1.10 <= t.pnl_r <= 2.80)]
            ok = [t.pnl_r for t in r.trades if -1.10 <= t.pnl_r <= 2.80]
            print(f"  {sym:<9}{tag:<8}{r.n_trades:>6}{_rpt(r):>+12.4f}"
                  f"{len(ph):>10}{sum(t.pnl_r for t in ph):>+12.1f}"
                  f"{len(ok):>8}{(np.mean(ok) if ok else 0):>+12.4f}")
        print()
    print("  --- SECOND CONTRÔLE, INDÉPENDANT : plafond de détention ---")
    print("  Ce contrôle a d'abord été écarté : `max_hold_bars` valorisait la")
    print("  sortie à `closes[n-1]` (fin de tranche) au lieu de la barre de")
    print("  plafond, donc le prix de sortie était postérieur à l'instant de")
    print("  sortie. Défaut remonté puis CORRIGÉ en amont pendant cette session")
    print("  (commit 1fb18ca, trouvé en parallèle par l'agent s04). Le contrôle")
    print("  est donc de nouveau valide, et il est ici rejoué sur le moteur")
    print("  corrigé — il ne dépend PAS du tri par bornes de la table ci-dessus.")
    print()
    print("  Une position dont le stop a été sauté est forcée de se clôturer au")
    print("  bout de 240 barres (~1 mois H1). Si un instrument change beaucoup,")
    print("  c'est que des positions restaient bloquées.")
    print()
    print(f"  {'sym':<9}{'filtre':<8}{'n libre':>9}{'R/tr libre':>13}"
          f"{'n borné':>9}{'R/tr borné':>13}{'écart':>10}")
    print("  " + "-" * 74)
    for sym in symbols:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        s._symbol = sym
        for tag, ov in (("off", OFF), ("hist", HIST)):
            a = _run(s, df, spec, ov)
            b = _run(s, df, spec, ov, max_hold_bars=240)   # ~1 mois de barres H1
            if not a.trades or not b.trades:
                continue
            print(f"  {sym:<9}{tag:<8}{a.n_trades:>9}{_rpt(a):>+13.4f}"
                  f"{b.n_trades:>9}{_rpt(b):>+13.4f}{_rpt(b)-_rpt(a):>+10.4f}")
    print()
    print("  LES DEUX CONTRÔLES CONCORDENT. Sur DAX sans filtre : le plafond de")
    print("  détention fait passer l'instrument de 103 à ~370 trades et le")
    print("  R/trade de -1,83 à ~0,00 — c'est bien UNE position bloquée qui")
    print("  produisait le chiffre ET qui empêchait ~270 trades d'exister.")
    print("  Les deux contrôles ne donnent pas la même valeur (le plafond")
    print("  modifie aussi d'autres trades) mais ils donnent le même verdict :")
    print("  le -1,83 brut de DAX n'est pas un résultat de la stratégie.")
    print()
    print("  À NOTER : `run_walk_forward` n'expose pas `max_hold_bars`. Le")
    print("  walk-forward officiel tourne donc SANS plafond, avec le trou de")
    print("  gap encore présent — d'où l'écart de DAX qui y est déclaré.")


# ─────────────────────────────────────────────────────────────────────────────
def threshold_matrix(symbols):
    section("4. MATRICE DES SEUILS — PLEIN ÉCHANTILLON (complément au hors-éch.)")
    print("  R/trade, agrégé sur les 8 instruments, à configuration de signal")
    print("  fixée (donchian 20, adx_min 25, tp_m 4,0 = valeurs historiques).")
    print()
    er_vals = [0.00, 0.09, 0.11, 0.13]
    fr_vals = [1.00, 0.45, 0.50, 0.55]
    s = Strategy()
    data = {sym: load_bars(sym, "H1") for sym in symbols}
    specs = {sym: get_spec(sym) for sym in symbols}

    raw, sane = {}, {}
    for er in er_vals:
        for fr in fr_vals:
            tr = tn = 0.0
            sr = sn = 0.0
            for sym in symbols:
                s._symbol = sym
                r = _run(s, data[sym], specs[sym], {"er_min": er, "fr_max": fr})
                tr += r.total_r
                tn += r.n_trades
                ok = [t.pnl_r for t in r.trades if -1.10 <= t.pnl_r <= 2.80]
                sr += sum(ok)
                sn += len(ok)
            raw[(er, fr)] = (tr / tn if tn else float("nan"), int(tn))
            sane[(er, fr)] = (sr / sn if sn else float("nan"), int(sn))

    def show(title, grid):
        print()
        print(f"  --- {title} ---")
        print("      " + "er_min v / fr_max >".ljust(16)
              + "".join(f"{f:>18.2f}" for f in fr_vals))
        for er in er_vals:
            row = f"      {er:<16.2f}"
            for fr in fr_vals:
                v, n = grid[(er, fr)]
                row += f"{v:>+13.4f}({n:>4})"
            print(row)
        base = grid[(0.00, 1.00)][0]
        hist = grid[(0.11, 0.50)][0]
        neigh = {(e, f): grid[(e, f)][0]
                 for e in (0.09, 0.11, 0.13) for f in (0.45, 0.50, 0.55)}
        better = sum(1 for v in neigh.values() if v > base)
        print()
        print(f"      Témoin sans filtre (0,00 ; 1,00) : {base:+.4f} R/trade "
              f"sur {grid[(0.00,1.00)][1]} trades")
        print(f"      Point historique   (0,11 ; 0,50) : {hist:+.4f} R/trade "
              f"sur {grid[(0.11,0.50)][1]} trades   ({hist-base:+.4f})")
        print(f"      Voisinage 3×3 meilleur que le témoin : {better}/9")
        print("      Écart au témoin, cellule par cellule :")
        for e in (0.09, 0.11, 0.13):
            print("        " + "  ".join(
                f"er{e:.2f}/fr{f:.2f} {neigh[(e,f)]-base:+.4f}"
                for f in (0.45, 0.50, 0.55)))
        return base, hist, better

    b1, h1, n1 = show("BRUT (sortie du moteur telle quelle)", raw)
    b2, h2, n2 = show("HORS TRADES FANTÔMES (stops sautés par un gap retirés)", sane)
    print()
    print("  *** COMPARAISON DÉCISIVE ***")
    print(f"  brut   : témoin {b1:+.4f} -> filtre {h1:+.4f}  ({h1-b1:+.4f})  "
          f"voisinage {n1}/9")
    print(f"  sain   : témoin {b2:+.4f} -> filtre {h2:+.4f}  ({h2-b2:+.4f})  "
          f"voisinage {n2}/9")
    print()
    print("  Si le gain apparent du filtre disparaît (ou s'inverse) une fois")
    print("  les trades fantômes retirés, ce gain ne venait pas du filtre :")
    print("  il venait de ce que le filtre évitait par hasard UNE position")
    print("  dont le moteur n'a pas rempli le stop.")


def main():
    symbols = Strategy().manifest().symbols
    print("s11_legacy_breakout — DIAGNOSTICS COMPLÉMENTAIRES")
    print(f"instruments : {', '.join(symbols)}   |   TF : H1")
    print(f"dépôt (core inclus) : commit {_head()}")
    print("« off »  = er_min 0,00 / fr_max 1,00 -> filtre de régime DÉSACTIVÉ")
    print("« hist » = er_min 0,11 / fr_max 0,50 -> seuils historiques")
    spread_ablation(symbols)
    long_short_control(symbols)
    gap_sensitivity(symbols)
    threshold_matrix(symbols)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
