"""
PHASE 1 — ÉCONOMIE DU TRADE, CALCULÉE AVANT D'ÉCRIRE LA STRATÉGIE
=================================================================

Ce script ne produit AUCUN signal et ne backteste rien. Il répond à une seule
question, celle que la méthodologie du projet impose de trancher avant de coder :

    « Pour la géométrie que j'envisage, et à l'heure de la journée que j'envisage,
      le péage du spread est-il inférieur à la marge que je peux espérer ? »

Trois mesures :
  1. Le profil horaire de volatilité par instrument (fait mesuré du projet :
     3,7× d'écart entre creux et pic sur EURUSD — à re-vérifier sur les 6).
  2. Le péage `spread / distance de risque` en fonction de la fenêtre horaire
     ET du multiple d'ATR — c'est le seul levier disponible sur H1.
  3. L'autocorrélation des rendements H1 conditionnée à l'heure : le signe de
     l'effet de retour à la moyenne, mesuré AVANT de construire une règle.
     C'est le test le moins cher de l'hypothèse H91.

    python strategies/s91_claude_scratch/research/economics.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data.instruments import get_spec              # noqa: E402
from core.data.source import calibrate_server_offset    # noqa: E402
from core.data.source import load_bars, spread_cost_analysis  # noqa: E402

SYMBOLS = ["EURUSD", "USDCHF", "USDJPY", "USDCAD", "AUDUSD", "EURJPY"]

# Fenêtres horaires en HEURE SERVEUR (≈ GMT+2/+3, calibré par le projet).
# PEAK   = chevauchement Londres / New York, le pic mesuré du projet.
# DEAD   = zone morte asiatique tardive / pré-Londres.
PEAK = list(range(13, 18))     # 13,14,15,16,17
DEAD = list(range(22, 24)) + list(range(0, 7))


def rule(c="=", n=96):
    print(c * n)


def section(t):
    print()
    rule()
    print(t)
    rule()


def atr_pips(df: pd.DataFrame, pip: float, n: int = 24) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean() / pip


# ─────────────────────────────────────────────────────────────────────────────
def volatility_profile():
    section("1. PROFIL HORAIRE DE VOLATILITÉ — le fait mesuré est-il général ?")
    print("  Amplitude moyenne d'une barre H1 (pips), par heure serveur.")
    print("  Le projet a mesuré 3,7× d'écart creux/pic sur EURUSD. Vérification")
    print("  sur les 6 instruments : si le cycle n'est pas général, l'hypothèse")
    print("  H91 ne peut pas être portée par un panier.")
    print()
    print(f"  {'instrument':<11}{'creux h':>9}{'pips':>8}{'pic h':>7}{'pips':>8}"
          f"{'ratio':>8}{'PEAK 13-17':>12}{'DEAD 22-06':>12}{'PEAK/DEAD':>11}")
    print("  " + "-" * 88)
    for sym in SYMBOLS:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        cal = calibrate_server_offset(df, spec.pip)
        prof = cal["profile"]
        pk = float(prof.reindex(PEAK).mean())
        dd = float(prof.reindex(DEAD).mean())
        print(f"  {sym:<11}{cal['trough_server_hour']:>9}{cal['trough_range_pips']:>8.1f}"
              f"{cal['peak_server_hour']:>7}{cal['peak_range_pips']:>8.1f}"
              f"{cal['ratio']:>8.2f}{pk:>12.1f}{dd:>12.1f}{pk/dd:>11.2f}")


# ─────────────────────────────────────────────────────────────────────────────
def toll_by_window():
    section("2. PÉAGE DU SPREAD PAR FENÊTRE HORAIRE ET PAR GÉOMÉTRIE")
    print("  drag = spread / distance de risque. C'est le coût en R par trade,")
    print("  indépendant du R:R. C'est LUI qu'il faut battre en espérance brute.")
    print()
    print("  Deux façons de dimensionner le stop :")
    print("    ATR global   = ATR(24) toutes heures confondues (stop identique)")
    print("    ATR fenêtre  = ATR moyen des barres de la fenêtre visée")
    print()
    print(f"  {'instrument':<11}{'spread':>8}{'ATRglob':>9}"
          f"{'ATR@PEAK':>10}{'ATR@DEAD':>10}"
          f"{'drag 2.0x':>11}{'drag 2.5x':>11}{'drag 3.0x':>11}"
          f"{'dragDEAD2.5':>13}")
    print("  " + "-" * 94)
    rows = []
    for sym in SYMBOLS:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        a = atr_pips(df, spec.pip)
        a_glob = float(a.median())
        hours = df.index.hour
        a_peak = float(a[np.isin(hours, PEAK)].median())
        a_dead = float(a[np.isin(hours, DEAD)].median())
        d = lambda mult, base: 100 * spec.spread_pips / (mult * base)
        rows.append((sym, d(2.5, a_glob), d(2.5, a_dead)))
        print(f"  {sym:<11}{spec.spread_pips:>8.1f}{a_glob:>9.1f}"
              f"{a_peak:>10.1f}{a_dead:>10.1f}"
              f"{d(2.0,a_glob):>10.2f}%{d(2.5,a_glob):>10.2f}%{d(3.0,a_glob):>10.2f}%"
              f"{d(2.5,a_dead):>12.2f}%")
    print()
    print(f"  Médiane drag @ ATR global × 2.5 : "
          f"{np.median([r[1] for r in rows]):.2f} %")
    print(f"  Médiane drag @ ATR zone morte × 2.5 : "
          f"{np.median([r[2] for r in rows]):.2f} %")
    print()
    print("  Rappel de la fonction de référence du projet (sl=2.0 ATR, rr=2.0) :")
    for sym in SYMBOLS:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        r = spread_cost_analysis(df, spec.spread_pips, spec.pip, 2.0, 2.0)
        print(f"    {sym:<9} drag {r['drag_pct']:>6.2f}%  "
              f"pénalité {r['wr_penalty_points']:>5.2f} pts WR  "
              f"(risque {r['risk_pips']:>5.1f} pips)")


# ─────────────────────────────────────────────────────────────────────────────
def reversion_signature():
    section("3. SIGNATURE DE RETOUR À LA MOYENNE, CONDITIONNÉE À L'HEURE")
    print("  Test le moins cher de H91, AVANT toute règle de trading.")
    print()
    print("  Pour chaque barre : z = (close - MM20) / ecart-type(20).")
    print("  On regarde le rendement des 4 barres SUIVANTES, signé contre z.")
    print("  Un retour à la moyenne donne une valeur POSITIVE (le prix revient).")
    print("  Une continuation donne une valeur NÉGATIVE.")
    print("  Unité : pips, spread NON déduit (on mesure le signal brut).")
    print()
    print("  Sous-échantillon : |z| >= 1.5 seulement (les extensions).")
    print()
    hdr = (f"  {'instrument':<11}{'n PEAK':>8}{'rev PEAK':>10}"
           f"{'n DEAD':>8}{'rev DEAD':>10}{'n AUTRE':>9}{'rev AUTRE':>11}"
           f"{'n TOUT':>8}{'rev TOUT':>10}")
    print(hdr)
    print("  " + "-" * 86)
    agg = {"PEAK": [], "DEAD": [], "AUTRE": [], "TOUT": []}
    for sym in SYMBOLS:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        c = df["close"]
        ma = c.rolling(20).mean()
        sd = c.rolling(20).std()
        z = (c - ma) / sd
        fwd = (c.shift(-4) - c) / spec.pip          # rendement futur en pips
        rev = -np.sign(z) * fwd                      # >0 = ça revient
        hours = df.index.hour
        sel = z.abs() >= 1.5
        out = []
        for name, mask in (("PEAK", np.isin(hours, PEAK)),
                           ("DEAD", np.isin(hours, DEAD)),
                           ("AUTRE", ~np.isin(hours, PEAK + DEAD)),
                           ("TOUT", np.ones(len(df), bool))):
            m = sel & mask & rev.notna()
            v = rev[m]
            out.append((int(m.sum()), float(v.mean()) if len(v) else np.nan))
            agg[name].append(float(v.mean()) if len(v) else np.nan)
        print(f"  {sym:<11}" + "".join(
            f"{n:>8}{r:>+10.3f}" if i < 2 else
            (f"{n:>9}{r:>+11.3f}" if i == 2 else f"{n:>8}{r:>+10.3f}")
            for i, (n, r) in enumerate(out)))
    print("  " + "-" * 86)
    print(f"  {'MOYENNE':<11}{'':>8}{np.nanmean(agg['PEAK']):>+10.3f}"
          f"{'':>8}{np.nanmean(agg['DEAD']):>+10.3f}"
          f"{'':>9}{np.nanmean(agg['AUTRE']):>+11.3f}"
          f"{'':>8}{np.nanmean(agg['TOUT']):>+10.3f}")
    print()
    print("  LECTURE — prédiction de H91 : rev PEAK > 0 ET rev PEAK > rev DEAD.")
    print("  Si rev PEAK <= 0, l'hypothèse est morte avant la première ligne de")
    print("  stratégie et il faut le dire.")


def main():
    print("s91_claude_scratch — PHASE 1 : ÉCONOMIE DU TRADE (aucun backtest ici)")
    print(f"instruments : {', '.join(SYMBOLS)}")
    print("timeframe   : H1   |   heures = HEURE SERVEUR MT5 (≈ GMT+2/+3)")
    volatility_profile()
    toll_by_window()
    reversion_signature()
    print()
    rule()
    print("FIN — ces chiffres décident si la stratégie mérite d'être écrite.")
    rule()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
