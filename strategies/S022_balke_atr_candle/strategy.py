"""
S022 — ATR Candle Breakout : bougie anormalement grande fermant sur son extrême (René Balke).

Source : EA gratuit « ATR Candle Breakout » de BM Trading, page produit
https://bmtrading.de/en/expert-advisors/atr-candle-breakout/ et billet de blog
https://bmtrading.de/en/blog/atr-candle-breakout-ea/ (2026-06-09, or/XAUUSD, backtest
tick 11 ans + comparaison live). Guide d'entrées officiel :
`docs/sources/renebalke/ea_inputs/ATR Candle Breakout EA Inputs.pdf`. Réglages qu'il
trade en live, dictés dans la vidéo `qgsi-u0kOVw` et repris dans
`docs/sources/renebalke/EA_inputs_et_reglages-live_2026-09-12.md` § 2.4.

La règle est reproduite ICI TELLE QUELLE — pas une variante « améliorée » :

  MESURE   ATR(`ATR Period`) sur l'unité de temps de signal — « the average size of
           recent candles », la définition du « normal » de l'EA.
  OUTLIER  « A signal candle must be larger than this multiple of the ATR to count as
           a breakout » → amplitude (haut − bas) de la bougie close > `ATR Multiplier`
           × ATR. L'ATR de référence est celui des barres STRICTEMENT ANTÉRIEURES
           (décalage 1) : la grosse bougie ne gonfle pas sa propre référence.
  CONVICTION « The candle also has to close near its own extreme — near its high for a
           buy, near its low for a sell » : (haut − close) ≤ `Close proximity` × amplitude
           pour un achat, (close − bas) ≤ `Close proximity` × amplitude pour une vente.
           « Lower values are stricter ». On suit le sens de la bougie.
  CORPS    `Min candle body-to-range ratio` : corps/amplitude ≥ x, « Set to 0 to disable ».
           Sa valeur live n'est pas dite → 0 (désactivé), hypothèse fidèle déclarée.
  SORTIES  « Stop Loss / Take Profit (% of open price) » : stop et cible en pourcentage
           du prix d'entrée. Live : TP 2 %, SL 0,5 % (RR 4).
  FILTRES  tendance MA HTF, confirmation ATR multi-unités, fenêtre horaire, support /
           résistance : TOUS DÉSACTIVÉS dans son live → non implémentés ici, et c'est
           délibéré (les implémenter ouvrirait une grille que son réglage ne justifie pas).
  DIVERS   une position par symbole ; pas de trailing (désactivé en live) ; le sizing
           (« Risk per trade (fixed money amount) ») appartient à la couche risque (R2).

Réglages live reproduits en défauts : H1, ATR 200, × 2,5, proximité 25 %, TP 2 %,
SL 0,5 %, filtres off, corps 0.

Ce que la plateforme ajoute et qui N'EST PAS dans son EA : le coût de bord réel du
courtier, le bras témoin aléatoire, et — en second bras d'information seulement — le
refroidissement et le coupe-circuit communs. Par la doctrine Adrian du 2026-09-12,
S022 déclare ses propres règles : **pas de coupe-circuit**. Avec un taux de réussite
annoncé ≈ 23 %, trois pertes d'affilée arrivent une fois sur deux (0,77³ ≈ 46 %) ; un
coupe-circuit à 3 pertes couperait la règle, pas le risque. Le bras « règles communes »
est mesuré à côté pour rendre ce coût visible.

DÉFINITION DE L'ATR — ambiguïté déclarée, pas tranchée en douce. L'indicateur iATR de
MT5 est une MOYENNE SIMPLE du True Range sur la période ; l'ATR original de Wilder est
un lissage récursif. L'EA de Balke appelle iATR (c'est l'ATR standard de la plateforme),
donc `atr_mode = "sma"` est le défaut fidèle. `"wilder"` existe comme paramètre HORS
GRILLE, uniquement pour instruire un écart de fidélité (cf. research/FALSIFICATION.md
§ « échec du dispositif ») — ce n'est pas un réglage à optimiser.

    Écart transitoire assumé sur la branche « wilder » : la récurrence α = 1/P est
    amorcée sur TR[0] (`ewm(adjust=False)`), là où le Wilder canonique s'amorce sur la
    moyenne simple des P premiers True Range. L'écart décroît en (1 − 1/P)^n, est sans
    effet sur une mesure de six ans, et cette branche ne sert qu'au diagnostic. Le
    comportement est épinglé par `test_atr_mode_wilder_suit_la_recurrence_annoncee`.

LE SENS DE LA BOUGIE est une interprétation, déclarée : « close near its own extreme »
n'exige pas explicitement une bougie haussière pour un achat. Nous demandons close >
open pour un achat et close < open pour une vente (« The EA then trades in the direction
of that breakout »). Mesuré sur l'or H1, six ans : cette condition écarte 21 bougies
outlier sur les 857 qui ferment près d'un extrême — 2,5 %, sans effet sur les
conclusions.

CAUSALITÉ (R1) : ATR décalé d'une barre, aucune valeur à l'indice i ne dépend d'un
indice > i. generate_signals à la barre i ne dépend que de [0, i]. on_bar délègue au
même code (R5). Stop toujours renseigné (R3).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

ATR_PERIOD = 200          # réglage live : « ATR Period 200 » sur H1
WARMUP_MARGIN = 10
WARMUP_BARS = ATR_PERIOD + WARMUP_MARGIN      # 210
SIDE_MODES = ("both", "long_only", "short_only")
ATR_MODES = ("sma", "wilder")


def _validate(params: dict) -> tuple:
    """Lit et contrôle les paramètres. Lève ValueError plutôt que de deviner."""
    atr_period = int(params.get("atr_period", ATR_PERIOD))
    atr_mult = float(params.get("atr_mult", 2.5))
    proximity = float(params.get("proximity", 0.25))
    sl_pct = float(params.get("sl_pct", 0.005))
    tp_pct = float(params.get("tp_pct", 0.02))
    min_body = float(params.get("min_body_ratio", 0.0))
    side_mode = str(params.get("side_mode", "both"))
    atr_mode = str(params.get("atr_mode", "sma")).lower()

    if side_mode not in SIDE_MODES:
        raise ValueError(f"side_mode inconnu : {side_mode} (attendu {SIDE_MODES})")
    if atr_mode not in ATR_MODES:
        raise ValueError(f"atr_mode inconnu : {atr_mode} (attendu {ATR_MODES})")
    if atr_period < 2:
        raise ValueError(f"atr_period doit valoir au moins 2 (reçu {atr_period})")
    if atr_mult <= 0:
        raise ValueError(f"atr_mult doit être strictement positif (reçu {atr_mult})")
    if not (0.0 < proximity <= 1.0):
        raise ValueError(f"proximity doit être dans ]0, 1] (reçu {proximity})")
    if sl_pct <= 0 or tp_pct <= 0:
        raise ValueError("sl_pct et tp_pct doivent être strictement positifs")
    if not (0.0 <= min_body <= 1.0):
        raise ValueError(f"min_body_ratio doit être dans [0, 1] (reçu {min_body})")
    return atr_period, atr_mult, proximity, sl_pct, tp_pct, min_body, side_mode, atr_mode


class Strategy(StrategyModule):

    STRATEGY_ID = "S022_balke_atr_candle"
    MAGIC_NUMBER = 130022

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._symbol = "XAUUSD"

    # ── manifeste ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id="S022_balke_atr_candle",
            display_name="ATR Candle Breakout — grosse bougie fermant sur son extrême (René Balke)",
            version="1.0.0",
            magic_number=130022,
            author="claude:S022_balke_atr_candle",
            source="https://bmtrading.de/en/blog/atr-candle-breakout-ea/",
            symbols=["XAUUSD"],
            timeframe="H1",
            warmup_bars=WARMUP_BARS,
            # 12 cellules, autour de ses réglages live, cible fixée à ses 2 %.
            # `atr_period` et `tp_pct` ne sont PAS balayés : ce sont ses valeurs
            # dictées, et les balayer transformerait une reproduction en réglage.
            param_grid={
                "atr_mult": [2.0, 2.5, 3.0],
                "proximity": [0.25, 0.35],
                "sl_pct": [0.005, 0.01],
            },
            default_params={
                "atr_period": ATR_PERIOD,
                "atr_mult": 2.5,
                "proximity": 0.25,
                "tp_pct": 0.02,
                "sl_pct": 0.005,
                "min_body_ratio": 0.0,
                "atr_mode": "sma",
                "side_mode": "both",
            },
            status="BACKTESTED",   # mesuré le 2026-09-12 — « mesuré » ne vaut PAS « validé »
                                   # (R10), et la mesure est négative : research/VERDICT.md
            notes=("Reproduction fidèle des réglages live (H1, ATR 200 × 2,5, "
                   "proximité 25 %, TP 2 % / SL 0,5 %, filtres désactivés). Critères "
                   "écrits avant la mesure : research/FALSIFICATION.md."),
        )

    # ── indicateurs ────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        atr_period, *_rest = _validate(params)
        atr_mode = _rest[-1]
        high, low, close, opn = df["high"], df["low"], df["close"], df["open"]
        prev = close.shift(1)
        # True Range. À la première barre il n'y a pas de close précédent : max(axis=1)
        # ignore les NaN et retombe sur (haut − bas), ce que fait aussi MT5.
        tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()],
                       axis=1).max(axis=1)
        if atr_mode == "sma":
            atr = tr.rolling(atr_period).mean()          # iATR de MT5
        else:
            atr = tr.ewm(alpha=1.0 / atr_period, adjust=False,
                         min_periods=atr_period).mean()  # Wilder (diagnostic)

        out = pd.DataFrame(index=df.index)
        out["open"], out["high"], out["low"], out["close"] = opn, high, low, close
        out["rng"] = high - low
        out["body"] = close - opn
        # DÉCALAGE 1 : la référence de « normalité » ne contient jamais la bougie
        # qu'elle doit juger. Sans ce décalage une bougie 3× l'ATR relève l'ATR
        # d'elle-même et se disqualifie partiellement — la règle mesurée ne serait
        # plus celle de l'EA.
        out["atr_ref"] = atr.shift(1)
        return out

    # ── signaux ────────────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        (atr_period, atr_mult, proximity, sl_pct, tp_pct,
         min_body, side_mode, _atr_mode) = _validate(params)

        warmup = atr_period + WARMUP_MARGIN
        n = min(int(end_idx), len(data))
        if n <= warmup:
            return []

        idx = data.index
        high = data["high"].to_numpy(dtype=float)
        low = data["low"].to_numpy(dtype=float)
        close = data["close"].to_numpy(dtype=float)
        rng = data["rng"].to_numpy(dtype=float)
        body = data["body"].to_numpy(dtype=float)
        atr = data["atr_ref"].to_numpy(dtype=float)

        with np.errstate(invalid="ignore"):
            big = np.isfinite(atr) & (atr > 0) & (rng > 0) & (rng > atr_mult * atr)
            if min_body > 0.0:
                big &= np.abs(body) >= min_body * rng
            up = big & (body > 0) & ((high - close) <= proximity * rng)
            dn = big & (body < 0) & ((close - low) <= proximity * rng)
        if side_mode == "long_only":
            dn[:] = False
        elif side_mode == "short_only":
            up[:] = False

        hits = np.flatnonzero((up | dn)[:n])
        out: list[Signal] = []
        for i in hits:
            if i < warmup:
                continue
            long = bool(up[i])
            entry = float(close[i])
            if long:
                stop, target, side = entry * (1 - sl_pct), entry * (1 + tp_pct), Side.LONG
            else:
                stop, target, side = entry * (1 + sl_pct), entry * (1 - tp_pct), Side.SHORT
            r = float(rng[i])
            out.append(Signal(
                timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                symbol=self._symbol, side=side,
                entry=entry, stop=stop, target=target,
                reason=(f"bougie {r / float(atr[i]):.1f}×ATR{atr_period} "
                        f"{'haussière' if long else 'baissière'}, close à "
                        f"{(100.0 * ((high[i] - entry) if long else (entry - low[i])) / r):.0f} % "
                        f"de l'extrême · sl {sl_pct:.2%} tp {tp_pct:.2%}"),
                meta={"atr": float(atr[i]), "range": r,
                      "range_over_atr": float(r / atr[i]),
                      "close_to_extreme": float(((high[i] - entry) if long else (entry - low[i])) / r),
                      "body_ratio": float(abs(body[i]) / r)},
            ))
        return out

    # ── live : même code que le backtest (R5) ─────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        self._symbol = ctx.symbol
        data = self.precompute(ctx.bars, self.params)
        sigs = self.generate_signals(data, self.params, len(ctx.bars))
        if sigs and pd.Timestamp(sigs[-1].timestamp) == pd.Timestamp(ctx.bars.index[-1]):
            return sigs[-1]
        return None
