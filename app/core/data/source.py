"""
COUCHE DE DONNÉES — accès unique à MT5 Swissquote
==================================================

Toutes les stratégies et le backtester passent par ici. Personne n'appelle
`MetaTrader5` directement : ça garantit que tout le monde voit exactement les
mêmes barres, et que le cache est partagé.

CE QUE CONTIENNENT NOS DONNÉES — vérifié, pas supposé
------------------------------------------------------
    colonnes : time, open, high, low, close, tick_volume, spread, real_volume

    tick_volume  = nombre de CHANGEMENTS DE COTATION sur la barre.
                   Ce n'est PAS un volume de contrats.
    real_volume  = 0 sur tous nos instruments (forex OTC et CFD synthétiques
                   Swissquote n'ont pas de volume centralisé publié).

Conséquence directe : toute stratégie fondée sur le volume échangé, le delta
bid/ask, l'absorption ou un footprint est **irréalisable ici**. Ce n'est pas
une limite de réglage, c'est l'absence de la donnée. Voir
`docs/METHODOLOGY.md`.

FUSEAU HORAIRE
--------------
Les horodatages MT5 sont naïfs et en heure serveur (≈ GMT+2/+3), pas en UTC.
Calibré empiriquement sur le profil de volatilité EURUSD : le pic
Londres/New York (~13:00 GMT) tombe à l'heure serveur 16. Écart mesuré entre
l'heure la plus creuse (7,0 pips) et le pic (25,7 pips) : 3,7×.
`calibrate_server_offset()` permet de refaire la mesure si le broker change.
"""
from __future__ import annotations

import os
import pickle
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from core.paths import db_dir as _db_dir  # noqa: E402

CACHE_DIR = os.path.join(str(_db_dir()), "bars_cache")

# Nom interne -> symbole broker. Le reste du code n'utilise QUE les noms internes.
SYMBOL_MAP = {
    "SP500":  "#US500",
    "NASDAQ": "#NAS100",
    "DAX":    "#DE40",
    "FTSE":   "#GB100",
    "NIKKEI": "#NIK225",
    "WTIUSD": "OILUSD",
}

_TF = {"M5": 5, "M15": 15, "H1": 16385, "H4": 16388, "D1": 16408}  # constantes MT5


def broker_symbol(name: str) -> str:
    return SYMBOL_MAP.get(name, name)


def _cache_path(symbol: str, timeframe: str, days: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = symbol.replace("#", "").replace("/", "")
    return os.path.join(CACHE_DIR, f"{safe}_{timeframe}_{days}d.pkl")


def load_bars(symbol: str, timeframe: str = "H1", days: int = 365 * 5 + 30,
              use_cache: bool = True, max_age_hours: int = 12) -> Optional[pd.DataFrame]:
    """Charge l'historique OHLC d'un instrument.

    Retourne un DataFrame indexé par datetime (heure serveur), colonnes
    open/high/low/close/tick_volume/spread — ou None si indisponible.

    Le cache évite de retélécharger 30 000 barres à chaque backtest. Il expire
    après `max_age_hours` pour que la fenêtre glissante reste à jour : c'est ce
    glissement qui, en juillet, a servi de forward-test involontaire et révélé
    que 4 de nos 5 paires validées ne tenaient plus.
    """
    if not timeframe:
        raise ValueError("timeframe requis (le manifest de la stratégie le déclare)")

    path = _cache_path(symbol, timeframe, days)
    if use_cache and os.path.exists(path):
        age = (datetime.now().timestamp() - os.path.getmtime(path)) / 3600
        if age < max_age_hours:
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass  # cache corrompu : on retélécharge

    df = _fetch_mt5(symbol, timeframe, days)
    if df is not None and use_cache:
        try:
            with open(path, "wb") as f:
                pickle.dump(df, f)
        except Exception:
            pass
    return df


def _fetch_mt5(symbol: str, timeframe: str, days: int) -> Optional[pd.DataFrame]:
    import MetaTrader5 as mt5

    if timeframe not in _TF:
        raise ValueError(f"timeframe inconnu : {timeframe} (attendu {list(_TF)})")

    sym = broker_symbol(symbol)
    if not mt5.initialize():
        return None
    try:
        if mt5.symbol_info(sym) is None:
            return None
        end = datetime.now()
        rates = mt5.copy_rates_range(sym, _TF[timeframe], end - timedelta(days=days), end)
        if rates is None or len(rates) < 100:
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")

        keep = [c for c in ("open", "high", "low", "close", "tick_volume", "spread")
                if c in df.columns]
        df = df[keep]

        # Barres corrompues serveur : prix entièrement à zéro. Cas réel trouvé
        # par l'agent s08 sur #BTCUSD D1 (barre du 2015-01-07, OHLC = 0). Une
        # seule suffit à détruire silencieusement toute statistique de
        # rendement : le buy & hold de BTCUSD ressortait à -100 % de CAGR,
        # Sharpe -2,28, sans le moindre avertissement. On refuse de servir ça.
        zero = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
        if zero.any():
            print(f"[DATA] {sym} {timeframe}: {int(zero.sum())} barre(s) à prix "
                  f"nul écartée(s) ({', '.join(str(t) for t in df.index[zero][:3])}"
                  f"{'…' if zero.sum() > 3 else ''})")
            df = df[~zero]

        return df
    finally:
        mt5.shutdown()


def calibrate_server_offset(df: pd.DataFrame, pip: float = 0.0001) -> dict:
    """Déduit le décalage horaire du serveur depuis le profil de volatilité.

    Le chevauchement Londres/New York (~13:00 GMT) est le pic de volatilité de
    toute paire liquide. Trouver l'heure SERVEUR de ce pic donne le décalage
    sans avoir à faire confiance à la documentation du broker.
    """
    rng = (df["high"] - df["low"]) / pip
    profile = rng.groupby(df.index.hour).mean()
    peak = int(profile.idxmax())
    trough = int(profile.idxmin())
    return {
        "peak_server_hour": peak,
        "implied_offset_gmt": peak - 13,
        "trough_server_hour": trough,
        "peak_range_pips": round(float(profile.max()), 1),
        "trough_range_pips": round(float(profile.min()), 1),
        "ratio": round(float(profile.max() / profile.min()), 2),
        "profile": profile,
    }


def spread_cost_analysis(df: pd.DataFrame, spread_pips: float, pip: float,
                         sl_atr_mult: float = 2.0, rr: float = 2.0) -> dict:
    """Chiffre le péage payé au broker, en POINTS DE WIN RATE.

    Le spread est un coût FIXE par trade ; la taille du mouvement visé dépend du
    timeframe. Le rapport des deux dit si une stratégie peut seulement exister.

    Mesuré en août 2026 : H1 coûte 2,14 points de win rate, H4 1,04, D1 0,46.
    S5 affichait 27-28 % de réussite pour un seuil de rentabilité à 25 % — soit
    2-3 points de marge brute. Le péage H1 en consommait 2,14. La stratégie ne
    pouvait pas être rentable sur H1, quelle que soit la qualité du signal.
    """
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr_pips = float(tr.rolling(14).mean().median()) / pip

    risk_pips = sl_atr_mult * atr_pips
    drag = spread_pips / risk_pips if risk_pips else float("nan")
    return {
        "atr_pips": round(atr_pips, 1),
        "risk_pips": round(risk_pips, 1),
        "spread_pips": spread_pips,
        "drag_pct": round(100 * drag, 2),
        "wr_penalty_points": round(100 * drag / (1 + rr), 2),
        "breakeven_wr_pct": round(100 / (1 + rr), 1),
    }
