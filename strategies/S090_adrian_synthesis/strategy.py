"""
s90_adrian_synthesis — « fade de l'échec » (excursion adverse >= threshold ATR,
cible ~1 ATR, dans le sens de la tendance supérieure).

Synthèse des quatre apparitions indépendantes du motif (s91 fenêtre asiatique,
s09 §2.7 trade retournement, s10 résidu NIKKEI, studies/grid_per_entry rang 3+).
Protocole d'instruction : research/HYPOTHESIS.md — FIGÉ avant tout backtest.

Construction du signal reprise À L'IDENTIQUE de la mesure décisive
(studies/grid_per_entry/signals.py, s_mult=1.0, sémantique « rang 3+ ») :
SuperTrend(10, 3.0) donne la tendance, ADX(14) > 20 gate, ancre = extrême de
jambe depuis le flip, entrée au close à chaque palier entier d'ATR au-delà de
`threshold_atr`, une fois par palier et par jambe. Stop `sl_atr` ATR, cible
`tp_atr` ATR, pas de sortie temporelle.

R9 : aucun moteur ici — exécution par core.backtest. R1 : tout est causal
(rolling / récursif avant, cumul avant) ; `generate_signals(data, p, T)` ne
lit que les lignes < T. `precompute` renvoie un DataFrame → la couche
indicateur du gardien de causalité est réellement couverte.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

ATR_PERIOD = 14
ST_PERIOD = 10
ST_MULT = 3.0
ADX_PERIOD = 14
ADX_GATE = 20.0
SPACING_ATR = 1.0          # palier fixe : 1,0 ATR (le s_mult=1.0 mesuré — figé)
WARMUP = 60

SYMBOLS = [
    # forex
    "EURUSD", "USDCHF", "USDJPY", "USDCAD", "AUDUSD",
    "EURCHF", "AUDCHF", "EURJPY", "AUDCAD",
    # indices
    "SP500", "NASDAQ", "DAX", "FTSE", "NIKKEI",
    # métaux / énergie
    "XAUUSD", "XAGUSD", "WTIUSD",
]


def _true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    prev = np.concatenate(([c[0]], c[:-1]))
    return np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))


def _supertrend(h: np.ndarray, l: np.ndarray, c: np.ndarray,
                period: int = ST_PERIOD, mult: float = ST_MULT) -> np.ndarray:
    """Sens SuperTrend causal : +1 (up) / -1 (down), NaN pendant le warmup."""
    tr = _true_range(h, l, c)
    atr = pd.Series(tr).rolling(period).mean().to_numpy()
    hl2 = (h + l) / 2.0
    ub = hl2 + mult * atr
    lb = hl2 - mult * atr
    n = len(c)
    trend = np.full(n, np.nan)
    fub = np.nan
    flb = np.nan
    t = 1.0
    for i in range(n):
        if not np.isfinite(atr[i]):
            continue
        if not np.isfinite(fub):          # première barre valide
            fub, flb = ub[i], lb[i]
            trend[i] = t
            continue
        fub = ub[i] if (ub[i] < fub or c[i - 1] > fub) else fub
        flb = lb[i] if (lb[i] > flb or c[i - 1] < flb) else flb
        if t == 1.0:
            t = 1.0 if c[i] > flb else -1.0
        else:
            t = -1.0 if c[i] < fub else 1.0
        trend[i] = t
    return trend


def _adx(h: np.ndarray, l: np.ndarray, c: np.ndarray,
         period: int = ADX_PERIOD) -> np.ndarray:
    """ADX de Wilder (ewm alpha=1/period, adjust=False) — strictement causal."""
    up = np.concatenate(([0.0], h[1:] - h[:-1]))
    dn = np.concatenate(([0.0], l[:-1] - l[1:]))
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = _true_range(h, l, c)
    alpha = 1.0 / period
    atr_w = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    pdi = 100.0 * pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean().to_numpy() \
        / np.where(atr_w > 0, atr_w, np.nan)
    mdi = 100.0 * pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean().to_numpy() \
        / np.where(atr_w > 0, atr_w, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        dx = 100.0 * np.abs(pdi - mdi) / np.where((pdi + mdi) > 0, pdi + mdi, np.nan)
    return pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().to_numpy()


class Strategy(StrategyModule):
    """Fade de l'excursion adverse profonde, avec la tendance supérieure."""

    STRATEGY_ID = "s90_adrian_synthesis"
    MAGIC_NUMBER = 130090     # réservé au registre (core/contracts/MAGIC_REGISTRY.md)

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Fade de l'échec (excursion ≥ k ATR, cible 1 ATR)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s90_adrian_synthesis",
            source="synthèse des VERDICT.md validés — research/HYPOTHESIS.md",
            symbols=list(SYMBOLS),
            timeframe="H1",
            warmup_bars=WARMUP,
            param_grid={
                "threshold_atr": [2, 3, 4],   # 3 = cellule primaire désignée d'avance
                "sl_atr": [1.0, 2.0],
                "tp_atr": [1.0],              # figé — rétraction partielle H90
            },
            default_params={"threshold_atr": 3, "sl_atr": 1.0, "tp_atr": 1.0},
            status="RESEARCH",
            notes="Grille 6 cellules dérivée de H90 (dose-réponse + voisinage), "
                  "pas de la performance. Cellule primaire : threshold 3 / sl 1 / tp 1.",
        )

    # ── Backtest path ────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        out = pd.DataFrame(index=df.index)
        out["high"] = h
        out["low"] = l
        out["close"] = c
        out["atr"] = pd.Series(_true_range(h, l, c)).rolling(ATR_PERIOD).mean().to_numpy()
        out["st_trend"] = _supertrend(h, l, c)
        out["adx"] = _adx(h, l, c)
        return out

    def generate_signals(self, data: pd.DataFrame, params: dict,
                         end_idx: int) -> list[Signal]:
        n = min(end_idx, len(data))
        threshold = int(params["threshold_atr"])
        sl_atr = float(params["sl_atr"])
        tp_atr = float(params["tp_atr"])

        idx = data.index
        high = data["high"].to_numpy()
        low = data["low"].to_numpy()
        close = data["close"].to_numpy()
        atr = data["atr"].to_numpy()
        trend = data["st_trend"].to_numpy()
        adx = data["adx"].to_numpy()

        out: list[Signal] = []
        prev_t = 0.0
        anchor = np.nan
        fired = 0          # palier entier max déjà tiré sur la jambe courante

        for i in range(WARMUP, n):
            t = trend[i]
            if not np.isfinite(t) or not np.isfinite(atr[i]) or atr[i] <= 0:
                continue
            if t != prev_t:                       # flip de tendance : nouvelle ancre
                prev_t = t
                anchor = high[i] if t > 0 else low[i]
                fired = 0
                continue
            if t > 0:
                if high[i] > anchor:              # nouvel extrême = jambe soldée
                    anchor = high[i]
                    fired = 0
                exc = anchor - close[i]
            else:
                if low[i] < anchor:
                    anchor = low[i]
                    fired = 0
                exc = close[i] - anchor

            spacing = SPACING_ATR * atr[i]
            if spacing <= 0:
                continue
            k = int(exc // spacing)
            if k < threshold or k <= fired:
                continue
            # Le palier compte comme tiré même si l'ADX le filtre : une seule
            # opportunité par palier et par jambe (sémantique de la mesure n°4).
            fired = k
            if not np.isfinite(adx[i]) or adx[i] <= ADX_GATE:
                continue

            entry = float(close[i])
            long = t > 0
            sl_d = sl_atr * atr[i]
            tp_d = tp_atr * atr[i]
            stop = entry - sl_d if long else entry + sl_d
            target = entry + tp_d if long else entry - tp_d
            out.append(Signal(
                timestamp=idx[i], symbol="", side=Side.LONG if long else Side.SHORT,
                entry=entry, stop=stop, target=target,
                reason=f"fade excursion k={k} (seuil {threshold} ATR, "
                       f"sl {sl_atr} / tp {tp_atr} ATR)",
                meta={"k": k, "threshold_atr": threshold},
            ))
        return out

    # ── Live path — délègue au chemin backtest (garantie structurelle R5) ────
    def on_bar(self, ctx: MarketContext):
        data = self.precompute(ctx.bars, self.params)
        sigs = self.generate_signals(data, self.params, len(ctx.bars))
        if sigs and pd.Timestamp(sigs[-1].timestamp) == ctx.bars.index[-1]:
            s = sigs[-1]
            return Signal(timestamp=s.timestamp, symbol=ctx.symbol, side=s.side,
                          entry=s.entry, stop=s.stop, target=s.target,
                          reason=s.reason, meta=s.meta)
        return None
