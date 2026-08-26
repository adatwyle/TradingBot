"""
PHASE 1 (suite) — EXPLORATION SUR LA TRANCHE D'ENTRAÎNEMENT UNIQUEMENT
======================================================================

POURQUOI CE SECOND SCRIPT EXISTE
---------------------------------
`economics.py` a exploré les 5,1 ans complets. Il a réfuté mon intuition de
départ (le retour à la moyenne serait concentré au pic Londres/NY) et suggéré
l'inverse. Reformuler l'hypothèse sur cette base, puis la « tester » sur les
mêmes données, serait du sur-ajustement déguisé en découverte.

Ce script refait donc la mesure sur **les 60 % premiers pourcents de
l'historique uniquement** — exactement la première fenêtre d'entraînement du
walk-forward ancré. L'hypothèse H91 est formulée à partir de CE tableau et de
lui seul. Les tranches de test (60-100 %) restent non vues.

Ce n'est pas une garantie parfaite : j'ai vu le tableau plein échantillon
d'`economics.py` avant d'écrire ceci, et cette contamination est déclarée dans
ANALYSIS.md §8. Mais la formulation, les seuils et la sélection d'instruments
sont fixés ici, sur le train, et gelés avant tout backtest.

CE QUI EST MESURÉ
-----------------
La dérive moyenne favorable après une extension, en pips, comparée
DIRECTEMENT au spread aller-retour. Critère a priori :

    dérive brute (pips)  >  spread aller-retour (pips)

Si aucune cellule (seuil z × horizon) ne satisfait ça, la stratégie ne doit pas
être écrite, et c'est le livrable de la Phase 1.

    python strategies/s91_claude_scratch/research/explore_train.py
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

from core.data.instruments import get_spec   # noqa: E402
from core.data.source import load_bars       # noqa: E402

SYMBOLS = ["EURUSD", "USDCHF", "USDJPY", "USDCAD", "AUDUSD", "EURJPY"]
JPY = {"USDJPY", "EURJPY"}

TRAIN_FRAC = 0.60                       # = première fenêtre du walk-forward ancré

PEAK = list(range(13, 18))
DEAD = list(range(22, 24)) + list(range(0, 7))


def rule(c="=", n=100):
    print(c * n)


def section(t):
    print()
    rule()
    print(t)
    rule()


def train_slice(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[:int(len(df) * TRAIN_FRAC)]


# ─────────────────────────────────────────────────────────────────────────────
def drift_table():
    """Dérive favorable moyenne (pips) vs spread, par seuil z et horizon."""
    section("A. DÉRIVE APRÈS EXTENSION vs SPREAD — LE CALCUL QUI DÉCIDE")
    print("  z = (close - MM20) / ecart-type(20), barres H1.")
    print("  dérive = -signe(z) x (close[t+H] - close[t]), en pips. >0 = ça revient.")
    print("  Fenêtre horaire : DEAD (serveur 22-06h).")
    print("  Tranche : 60 % PREMIERS de l'historique (entraînement).")
    print()
    print("  Le nombre à battre est le SPREAD ALLER-RETOUR de l'instrument.")
    print()
    for H in (4, 6, 8, 12):
        print(f"  --- horizon H = {H} barres ---")
        print(f"  {'instrument':<11}{'spread':>8}" +
              "".join(f"{'z>=' + str(zt):>11}" for zt in (1.5, 2.0, 2.5, 3.0)) +
              f"{'n(z>=2.0)':>11}")
        print("  " + "-" * 84)
        for sym in SYMBOLS:
            df = train_slice(load_bars(sym, "H1"))
            spec = get_spec(sym)
            c = df["close"]
            z = (c - c.rolling(20).mean()) / c.rolling(20).std()
            drift = -np.sign(z) * (c.shift(-H) - c) / spec.pip
            inwin = np.isin(df.index.hour, DEAD)
            cells, n20 = [], 0
            for zt in (1.5, 2.0, 2.5, 3.0):
                m = (z.abs() >= zt) & inwin & drift.notna()
                cells.append(float(drift[m].mean()) if m.sum() else np.nan)
                if zt == 2.0:
                    n20 = int(m.sum())
            tag = " (JPY)" if sym in JPY else ""
            print(f"  {sym + tag:<11}{spec.spread_pips:>8.1f}" +
                  "".join(f"{v:>+11.2f}" for v in cells) + f"{n20:>11}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
def window_split():
    """Le clivage horaire, et le clivage JPY / non-JPY, sur le train."""
    section("B. CLIVAGE HORAIRE ET CLIVAGE JPY — sur entraînement seul")
    print("  Dérive moyenne (pips), horizon 8 barres, |z| >= 2.0.")
    print()
    print(f"  {'instrument':<11}{'spread':>8}{'DEAD':>10}{'PEAK':>10}{'AUTRE':>10}"
          f"{'n DEAD':>9}{'DEAD-spread':>13}")
    print("  " + "-" * 74)
    grp = {"nonJPY": [], "JPY": []}
    for sym in SYMBOLS:
        df = train_slice(load_bars(sym, "H1"))
        spec = get_spec(sym)
        c = df["close"]
        z = (c - c.rolling(20).mean()) / c.rolling(20).std()
        drift = -np.sign(z) * (c.shift(-8) - c) / spec.pip
        h = df.index.hour
        vals = {}
        for name, mask in (("DEAD", np.isin(h, DEAD)),
                           ("PEAK", np.isin(h, PEAK)),
                           ("AUTRE", ~np.isin(h, PEAK + DEAD))):
            m = (z.abs() >= 2.0) & mask & drift.notna()
            vals[name] = (float(drift[m].mean()) if m.sum() else np.nan, int(m.sum()))
        net = vals["DEAD"][0] - spec.spread_pips
        grp["JPY" if sym in JPY else "nonJPY"].append(net)
        tag = " (JPY)" if sym in JPY else ""
        print(f"  {sym + tag:<11}{spec.spread_pips:>8.1f}"
              f"{vals['DEAD'][0]:>+10.2f}{vals['PEAK'][0]:>+10.2f}{vals['AUTRE'][0]:>+10.2f}"
              f"{vals['DEAD'][1]:>9}{net:>+13.2f}")
    print("  " + "-" * 74)
    print(f"  Marge nette moyenne (dérive DEAD - spread) :")
    print(f"     non-JPY (4 paires) : {np.nanmean(grp['nonJPY']):>+7.2f} pips")
    print(f"     JPY     (2 paires) : {np.nanmean(grp['JPY']):>+7.2f} pips")
    print()
    print("  MÉCANISME TESTÉ : la fenêtre 22-06h serveur est creuse pour les")
    print("  paires sans devise asiatique, mais c'est la SESSION DE TOKYO pour")
    print("  les paires JPY (ATR@DEAD ≈ ATR global, cf. economics.txt §1).")
    print("  H91 prédit donc : marge > 0 sur les non-JPY, <= 0 sur les JPY.")


# ─────────────────────────────────────────────────────────────────────────────
def geometry():
    """Distance de risque et drag, dans la fenêtre retenue, sur le train."""
    section("C. GÉOMÉTRIE DU TRADE — ATR de la fenêtre DEAD (entraînement)")
    print("  Le stop est dimensionné sur l'ATR(24), calculé sur toutes les barres")
    print("  (causal, pas de moyenne par heure). Voici ce qu'il vaut dans DEAD.")
    print()
    print(f"  {'instrument':<11}{'ATR DEAD':>10}{'risq 2.0x':>11}{'risq 2.5x':>11}"
          f"{'drag 2.0x':>11}{'drag 2.5x':>11}{'seuilWR rr1':>13}")
    print("  " + "-" * 78)
    for sym in SYMBOLS:
        df = train_slice(load_bars(sym, "H1"))
        spec = get_spec(sym)
        h_, l_, c_ = df["high"], df["low"], df["close"]
        pc = c_.shift(1)
        tr = pd.concat([h_ - l_, (h_ - pc).abs(), (l_ - pc).abs()], axis=1).max(axis=1)
        atr = (tr.rolling(24).mean() / spec.pip)
        a = float(atr[np.isin(df.index.hour, DEAD)].median())
        r2, r25 = 2.0 * a, 2.5 * a
        d2, d25 = spec.spread_pips / r2, spec.spread_pips / r25
        print(f"  {sym:<11}{a:>10.1f}{r2:>11.1f}{r25:>11.1f}"
              f"{100*d2:>10.2f}%{100*d25:>10.2f}%{100*(1+d25)/2:>12.1f}%")
    print()
    print("  seuilWR rr1 = taux de réussite requis à R:R 1.0, spread inclus.")
    print("  Sans spread il serait de 50,0 %. L'écart est le péage, en points de WR.")


def main():
    print("s91_claude_scratch — PHASE 1 : EXPLORATION SUR ENTRAÎNEMENT SEUL")
    print(f"instruments : {', '.join(SYMBOLS)}")
    print(f"tranche     : 60 % premiers de l'historique (= train de la fenêtre W1)")
    print("heures      : HEURE SERVEUR MT5 (~ GMT+2/+3)")
    for sym in SYMBOLS:
        df = load_bars(sym, "H1")
        t = train_slice(df)
        print(f"    {sym:<9} {len(df):>6} barres -> train {len(t):>6} "
              f"({t.index[0].date()} .. {t.index[-1].date()})")
    drift_table()
    window_split()
    geometry()
    print()
    rule()
    print("FIN — l'hypothèse H91 est figée à partir de ces chiffres, et de rien d'autre.")
    rule()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
