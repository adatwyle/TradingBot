"""
s09 — Phase 1 : économie du trade et calibration horaire, AVANT implémentation.

Mesure uniquement des propriétés des DONNÉES (pas de backtest de stratégie) :
  1. décalage horaire serveur Swissquote (calibrate_server_offset) — les bornes
     3h-6h de Balke sont en heure serveur IC Markets (GMT+2/+3) ; une erreur
     d'une heure fabrique une autre stratégie.
  2. taille du range de session (3-6h etc.) par instrument, en pips et en % du
     prix — c'est la distance de risque du SL "range".
  3. le péage : spread / distance de risque (drag), pour SL=range et SL=1 %.
  4. distribution de l'heure de première cassure du range (à titre descriptif,
     pour choisir max_hold_bars — la sortie 18h est approximée en barres).

Sortie : research/economics.txt
"""
from __future__ import annotations

import io
import os
import pickle
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.data.source import CACHE_DIR, calibrate_server_offset  # noqa: E402
from core.data.instruments import get_spec                        # noqa: E402
from core.backtest.engine import InstrumentSpec                   # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "economics.txt")

# GBPUSD n'est pas au catalogue core (interdit d'y toucher hors registre) :
# spec construite ICI, spread relevé sur la colonne `spread` du cache (points
# MT5 -> pips : USDJPY/GBPUSD cotés en 3/5 décimales, 1 pip = 10 points).
GBPUSD_FALLBACK_SPREAD_PIPS = 1.5   # remplacé par la mesure ci-dessous

CONFIGS = {
    # instrument : (fenêtre de range serveur, heure de clôture, sl_pct)
    "USDJPY": ((3, 6), 18),
    "GBPUSD": ((4, 12), 18),   # approx H1 de son 4:00-11:30
    "XAUUSD": ((3, 6), 19),    # approx H1 de son 3:05-6:05, clôture 18:55
    "EURJPY": ((3, 6), 18),    # témoin (échec live documenté)
}


def load(symbol: str) -> pd.DataFrame:
    path = os.path.join(CACHE_DIR, f"{symbol}_H1_1855d.pkl")
    with open(path, "rb") as f:
        df = pickle.load(f)
    zero = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    return df[~zero]


def spec_for(symbol: str, df: pd.DataFrame) -> InstrumentSpec:
    if symbol == "GBPUSD":
        # spread cache = points MT5 (5e décimale) ; médiane -> pips
        med_pts = float(df["spread"].median()) if "spread" in df else np.nan
        sp = med_pts / 10.0 if np.isfinite(med_pts) and med_pts > 0 else GBPUSD_FALLBACK_SPREAD_PIPS
        return InstrumentSpec(symbol="GBPUSD", pip=0.0001, spread_pips=round(sp, 1),
                              max_spread_pips=round(3 * sp, 1), pip_value_per_lot=10.0)
    return get_spec(symbol)


def session_range_stats(df: pd.DataFrame, spec: InstrumentSpec,
                        win: tuple[int, int], close_h: int, buf: io.StringIO):
    h = df.index.hour
    day = df.index.normalize()
    in_rng = (h >= win[0]) & (h < win[1])
    sub = df[in_rng]
    g = sub.groupby(sub.index.normalize())
    rng_high = g["high"].max()
    rng_low = g["low"].min()
    n_bars = g.size()
    complete = n_bars == (win[1] - win[0])
    rng = (rng_high - rng_low)[complete]
    mid = ((rng_high + rng_low) / 2)[complete]
    rng_pips = rng / spec.pip
    rng_pct = 100 * rng / mid

    # médiane du spread réel du cache (points MT5 -> pips = /10 pour FX 5-3 déc,
    # XAUUSD coté 2 décimales chez Swissquote : 1 point = 0.01 = 1 pip catalogue)
    med_spread_pts = float(df["spread"].median()) if "spread" in df else np.nan

    buf.write(f"\n=== {spec.symbol} — fenêtre {win[0]}h-{win[1]}h, clôture {close_h}h ===\n")
    buf.write(f"  barres H1 : {len(df)}   jours avec range complet : {int(complete.sum())}\n")
    buf.write(f"  spread catalogue : {spec.spread_pips} pips"
              f"   (médiane colonne cache : {med_spread_pts:.0f} points MT5)\n")
    buf.write(f"  taille du range : méd {rng_pips.median():.1f} pips "
              f"(p25 {rng_pips.quantile(.25):.1f}, p75 {rng_pips.quantile(.75):.1f}) "
              f"= {rng_pct.median():.3f} %% du prix (p25 {rng_pct.quantile(.25):.3f}, "
              f"p75 {rng_pct.quantile(.75):.3f})\n")
    buf.write(f"  part des jours dans le filtre 0.2-0.4 %% : "
              f"{100*((rng_pct>=0.2)&(rng_pct<=0.4)).mean():.0f} %%   "
              f"filtre 0.15-0.85 %% : {100*((rng_pct>=0.15)&(rng_pct<=0.85)).mean():.0f} %%\n")

    # péage : drag = spread / distance de risque
    drag_range = 100 * spec.spread_pips / rng_pips.median()
    pct1_pips = (0.01 * mid / spec.pip).median()
    drag_pct1 = 100 * spec.spread_pips / pct1_pips
    buf.write(f"  drag SL=range  : spread/risque = {drag_range:.2f} %%  "
              f"(= péage attendu en R/trade : {drag_range/100:.4f})\n")
    buf.write(f"  drag SL=1%%     : distance 1%% méd = {pct1_pips:.0f} pips -> "
              f"drag {drag_pct1:.2f} %% ({drag_pct1/100:.4f} R/trade)\n")

    # heure de première cassure en close H1 (descriptif, pour max_hold_bars)
    first_break = []
    dfx = df[(h >= win[1]) & (h < close_h)]
    rh = rng_high.reindex(dfx.index.normalize()).to_numpy()
    rl = rng_low.reindex(dfx.index.normalize()).to_numpy()
    cl = dfx["close"].to_numpy()
    hh = dfx.index.hour.to_numpy()
    dd = dfx.index.normalize().to_numpy()
    seen = set()
    for i in range(len(dfx)):
        d = dd[i]
        if d in seen or not np.isfinite(rh[i]):
            continue
        if cl[i] > rh[i] or cl[i] < rl[i]:
            first_break.append(hh[i])
            seen.add(d)
    fb = pd.Series(first_break)
    if len(fb):
        buf.write(f"  1re cassure (close H1) : {len(fb)} jours cassants "
                  f"({100*len(fb)/int(complete.sum()):.0f} %% des jours) ; heure méd "
                  f"{fb.median():.0f}h, p75 {fb.quantile(.75):.0f}h, p90 {fb.quantile(.90):.0f}h\n")
        buf.write(f"    -> barres de tenue jusqu'à {close_h}h : méd "
                  f"{close_h - fb.median() - 1:.0f}, p10 {close_h - fb.quantile(.90) - 1:.0f}\n")


def main():
    buf = io.StringIO()
    buf.write("s09 — économie du trade et calibration (Phase 1)\n")
    buf.write("=" * 70 + "\n")

    # 1. décalage serveur
    eur = load("EURUSD")
    cal = calibrate_server_offset(eur)
    buf.write("\n--- calibration fuseau serveur (profil de volatilité EURUSD) ---\n")
    for k in ("peak_server_hour", "implied_offset_gmt", "trough_server_hour",
              "peak_range_pips", "trough_range_pips", "ratio"):
        buf.write(f"  {k} : {cal[k]}\n")
    buf.write("  Lecture : pic Londres/NY ~13:00 GMT à l'heure serveur "
              f"{cal['peak_server_hour']} => serveur = GMT+{cal['implied_offset_gmt']}.\n"
              "  IC Markets (broker Balke) : GMT+2 hiver / GMT+3 été, même convention\n"
              "  « heure de New York + 7 » que la plupart des brokers MT5.\n")

    usd = load("USDJPY")
    cal2 = calibrate_server_offset(usd, pip=0.01)
    buf.write(f"  contrôle USDJPY : pic serveur {cal2['peak_server_hour']}h "
              f"(offset GMT+{cal2['implied_offset_gmt']}), ratio {cal2['ratio']}\n")

    # 2-4. par instrument
    for sym, (win, close_h) in CONFIGS.items():
        df = load(sym)
        spec = spec_for(sym, df)
        session_range_stats(df, spec, win, close_h, buf)

    txt = buf.getvalue()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
