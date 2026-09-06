"""
S019 — or, entrée sur balayage de liquidité (« sabre laser »)

Source de l'hypothèse : `docs/sources/doudtrading/` — 35 lives publics de Cindy
« Doud Trading », 54 heures, plus 108 clips et 2 podcasts. Géométrie complète
dans `SYNTHESE_GEOMETRIE.md`.

CE QUI DISTINGUE S019 DE S018
------------------------------
S018 traduisait le podcast et s'est trompée : elle y avait traduit « récupérer le
milieu » par une entrée au retracement 50 %, et le verdict fut `NON RETENU`.
S019 ne traduit pas un discours — elle code **ce qui a été mesuré** sur ses
entrées réelles :

  * `studies/meteo_doud/VERDICT_croisement-entrees.md` — 20 de ses entrées,
    horodatées et validées par le prix, tombent sur un **balayage de liquidité**
    dans 60 % des cas contre 39 % au hasard à la même heure (p = 0,047).
  * Le raffinement « mèche de rejet » y est mesuré **non significatif**
    (30 % contre 18 %, p = 0,136) : il n'entre PAS dans cette stratégie. On ne
    copie pas un geste qui ne se distingue pas du hasard.
  * `studies/meteo_doud/VERDICT_annonces.md` — elle entre **après** le choc
    d'annonce (médiane +6 min), pas avant. Le choc EST le balayage.

LA RÈGLE, EN QUATRE TEMPS
--------------------------
À chaque barre clôturée, côté long (symétrique au short) :

  1. BALAYAGE      une barre j perce le plus-bas des `sweep_lookback` barres qui
                   la précèdent — la poche de liquidité est prise.
  2. RÉINTÉGRATION dans les `sweep_window` barres suivantes, une barre i
                   **clôture au-dessus** du niveau percé. C'est la clôture qui
                   valide, jamais la mèche : « il a cassé en impulsion mais il
                   n'a pas breaké en structure » (`5HoIRmOBSvM @070:03`).
  3. ENTRÉE        au close de la barre i.
  4. INVALIDATION  si le prix reste sous le niveau percé au-delà de la fenêtre,
                   le setup meurt sans entrée.

LE STOP EST STRUCTUREL, ET C'EST UNE CONTRAINTE MESURÉE
---------------------------------------------------------
Le stop se place sous **le plus-bas du balayage**, pas à une distance ATR fixe.
Deux raisons, l'une mesurée chez nous, l'autre dite par elle :

  * `VERDICT_croisement-entrees.md` § 3 : notre stop de 1,5 × ATR(H1) = 858 pips
    aurait coupé **40 % de ses entrées dans l'heure**, alors que 60 % atteignent
    +858 pips en sa faveur. Un stop métrique détruit ce qu'il prétend protéger.
  * *« un bon stop, ce n'est pas un stop confortable, c'est un **stop logique par
    rapport à la structure**. Si ton stop est évident, il est fragile »*
    (`tiktok/7593786219301997846`).

MAIS un stop structurel colle parfois trop près : les profondeurs de balayage
mesurées vont de **34 à 218 pips**, quand le spread réel de XAUUSD est de
**52 pips** (`TCK-018`). Un stop à 34 pips coûterait 150 % de son propre risque
en frais. D'où `min_stop_atr` : un **plancher de distance**, qui n'est pas un
confort mais une condition de survie. Le harnais imprime le rapport coût/R pour
que ce piège reste visible à chaque mesure.

CE QUE S019 NE FAIT PAS, ET POURQUOI
--------------------------------------
Elle ne reproduit ni les clôtures partielles ni le stop suiveur, qui sont le
cœur de la gestion de la source (`SYNTHESE_METHODE.md` § 1.7) et, d'après
l'arithmétique de `SPEC_doud-probabilites-et-angles-morts` § 1.4, l'essentiel de
son edge. Le moteur commun ne sait pas les exprimer et R9 interdit d'en écrire un
autre — c'est `TCK-014`.

**S019 mesure donc son ENTRÉE, avec une sortie que nous savons inférieure à la
sienne.** C'est la seule question que notre moteur sache poser aujourd'hui, et
elle est décisive : si le déclencheur n'a pas d'edge même seul, enrichir la
sortie ne le sauvera pas.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)
from strategies.S011_legacy_breakout.strategy import _atr  # indicateur commun, non recopié

# Heures serveur (GMT+2, mesuré) des fenêtres qu'elle déclare : session US dès
# 14h, session asiatique le soir, jamais Londres (`SYNTHESE_METHODE.md` § 1.5).
SESSION_DOUD = frozenset((14, 15, 16, 17, 18, 23, 0, 1, 2, 3))

WARMUP_BARS = 300


def _htf_trend(df: pd.DataFrame, days: int) -> np.ndarray:
    """+1 / −1 selon que la journée PRÉCÉDENTE a clos au-dessus de son EMA.

    Causalité : série journalière décalée d'un jour avant report sur les barres
    fines. À n'importe quelle barre du jour J, la valeur lue est celle du jour
    J−1, complètement close.
    """
    close = df["close"]
    daily = close.resample("1D").last().dropna()
    if len(daily) < 2:
        return np.zeros(len(df))
    ema = daily.ewm(span=days, adjust=False).mean()
    sign = np.sign(daily - ema)
    sign[ema.isna()] = 0.0
    return (sign.shift(1).reindex(close.index, method="ffill")
            .fillna(0.0).to_numpy(dtype=float))


class Strategy(StrategyModule):
    STRATEGY_ID = "S019_gold_sweep"
    MAGIC_NUMBER = 130019

    _MAX_CACHE = 8

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._cache: dict[tuple, Any] = {}

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Or — balayage de liquidité et réintégration",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:S019_gold_sweep",
            source="docs/sources/doudtrading/ (35 lives, 54 h) ; déclencheur mesuré "
                   "dans studies/meteo_doud/VERDICT_croisement-entrees.md",
            symbols=["XAUUSD"],
            timeframe="M15",
            warmup_bars=WARMUP_BARS,
            # 2 × 2 × 2 × 2 = 16 cellules. À 5 %, ≈ 0,8 réussite attendue par
            # pur hasard. Grille délibérément petite : chaque commutateur code
            # une hypothèse mesurée, aucun n'est là « pour voir ».
            param_grid={
                "min_stop_atr":   [0.5, 1.0],   # plancher de stop, en ATR
                "tp_r":           [2.0, 4.0],   # cible en multiples de R
                "htf_bias":       ["off", "daily_ema"],
                "session_filter": ["off", "doud"],
            },
            default_params={
                "sweep_lookback": 60,       # la poche de liquidité de référence
                "sweep_window": 5,          # délai max de réintégration
                "stop_buffer_atr": 0.10,    # marge sous le plus-bas balayé
                "min_stop_atr": 0.5,
                "tp_r": 2.0,
                "htf_bias": "off",
                "session_filter": "off",
                "side_mode": "both",
                "htf_ema_days": 20,
                "cooldown_bars": 3,
            },
            status="RESEARCH",
            notes=("Déclencheur mesuré à 60 % contre 39 % au hasard (p = 0,047). "
                   "La mèche de rejet est exclue : mesurée non significative. "
                   "Stop structurel avec plancher — un stop collé sous la mèche "
                   "coûterait plus en spread qu'il ne risque."),
        )

    # ── Précalcul ────────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Balayages, réintégrations et signaux, étiquetés par barre d'entrée.

        Renvoie un DataFrame : la couche indicateur de `core/validation/causality`
        compare alors aussi les colonnes entre passe complète et passe tronquée.
        Le balayage porte un balayage à état — je préfère être vérifié.
        """
        N = int(params["sweep_lookback"])
        W = int(params["sweep_window"])
        buf = float(params["stop_buffer_atr"])
        min_stop = float(params["min_stop_atr"])
        tp_r = float(params["tp_r"])
        side_mode = str(params["side_mode"])
        session = str(params["session_filter"])
        htf = str(params["htf_bias"])
        cooldown = int(params["cooldown_bars"])
        if side_mode not in ("both", "long_only"):
            raise ValueError(f"side_mode inconnu : {side_mode!r}")
        if session not in ("off", "doud"):
            raise ValueError(f"session_filter inconnu : {session!r}")
        if htf not in ("off", "daily_ema"):
            raise ValueError(f"htf_bias inconnu : {htf!r}")

        n = len(df)
        idx = df.index
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        atr = _atr(high, low, close)

        # Plus-bas / plus-haut de référence, décalés d'une barre : la barre
        # courante ne peut pas faire partie de la poche qu'elle est censée percer.
        ref_lo = pd.Series(low).rolling(N, min_periods=N).min().shift(1).to_numpy()
        ref_hi = pd.Series(high).rolling(N, min_periods=N).max().shift(1).to_numpy()

        hours = idx.hour.to_numpy()
        sess_ok = (np.ones(n, dtype=bool) if session == "off"
                   else np.isin(hours, list(SESSION_DOUD)))
        bias = (np.zeros(n) if htf == "off"
                else _htf_trend(df, int(params["htf_ema_days"])))
        allow_long = sess_ok & (np.ones(n, dtype=bool) if htf == "off" else bias > 0)
        allow_short = (sess_ok
                       & (np.ones(n, dtype=bool) if htf == "off" else bias < 0)
                       & (side_mode != "long_only"))

        sig_list: list[tuple[int, Signal]] = []
        dec_side = np.zeros(n)
        dec_stop = np.full(n, np.nan)
        dec_target = np.full(n, np.nan)
        dec_depth = np.full(n, np.nan)
        symbol = getattr(self, "_symbol", "UNKNOWN")

        start = max(WARMUP_BARS, N + 2)
        j = start
        next_free = start          # anti-rafale : une entrée par setup
        while j < n:
            a = atr[j]
            if not np.isfinite(a) or a <= 0:
                j += 1
                continue

            # ── 1. Balayage : la barre j perce la poche de référence ─────────
            swept_low = np.isfinite(ref_lo[j]) and low[j] < ref_lo[j]
            swept_high = np.isfinite(ref_hi[j]) and high[j] > ref_hi[j]
            if not swept_low and not swept_high:
                j += 1
                continue
            is_long = bool(swept_low)          # balayage bas -> on cherche un achat
            level = float(ref_lo[j] if is_long else ref_hi[j])

            # ── 2. Réintégration : une CLÔTURE repasse du bon côté ───────────
            hit = None
            last = min(n - 1, j + W)
            extreme = low[j] if is_long else high[j]
            for i in range(j, last + 1):
                extreme = min(extreme, low[i]) if is_long else max(extreme, high[i])
                if (close[i] > level) if is_long else (close[i] < level):
                    hit = i
                    break
            if hit is None:
                j = last + 1
                continue

            i = hit
            if i < next_free:
                j = i + 1
                continue
            allowed = allow_long[i] if is_long else allow_short[i]
            if not allowed:
                j = i + 1
                continue

            # ── 3. Stop structurel, avec plancher ────────────────────────────
            ai = float(atr[i])
            entry = float(close[i])
            if not np.isfinite(ai) or ai <= 0:
                j = i + 1
                continue
            struct = (float(extreme) - buf * ai) if is_long else (float(extreme) + buf * ai)
            floor_stop = (entry - min_stop * ai) if is_long else (entry + min_stop * ai)
            stop = min(struct, floor_stop) if is_long else max(struct, floor_stop)
            risk = abs(entry - stop)
            if risk <= 0:
                j = i + 1
                continue
            target = entry + tp_r * risk if is_long else entry - tp_r * risk

            depth = abs(level - float(extreme))
            sig_list.append((i, Signal(
                timestamp=idx[i], symbol=symbol,
                side=Side.LONG if is_long else Side.SHORT,
                entry=entry, stop=stop, target=target,
                reason=(f"balayage {'bas' if is_long else 'haut'} de la poche "
                        f"{N} barres (profondeur {depth / 0.01:.0f} pips) puis "
                        f"réintégration en clôture {i - j} barres plus tard"),
                meta={"sweep_idx": j, "level": round(level, 3),
                      "extreme": round(float(extreme), 3),
                      "depth_pips": round(depth / 0.01, 1),
                      "bars_to_reentry": i - j,
                      "stop_structurel": bool(stop == struct),
                      "risk_pips": round(risk / 0.01, 1)},
            )))
            dec_side[i] = 1.0 if is_long else -1.0
            dec_stop[i] = stop
            dec_target[i] = target
            dec_depth[i] = depth
            next_free = i + cooldown
            j = i + 1

        out = pd.DataFrame({"atr": atr, "ref_lo": ref_lo, "ref_hi": ref_hi,
                            "bias": bias, "dec_side": dec_side,
                            "dec_stop": dec_stop, "dec_target": dec_target,
                            "dec_depth": dec_depth}, index=idx)
        out.attrs["signals"] = sig_list
        return out

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        return [s for (i, s) in data.attrs["signals"] if i < end_idx]

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : le live appelle le code du backtest et ne
        retient que la décision de la barre courante."""
        bars = ctx.bars
        if len(bars) < WARMUP_BARS + 10:
            return None
        self._symbol = ctx.symbol
        data = self.precompute(bars, self.params)
        last = len(bars) - 1
        for i, sig in data.attrs["signals"]:
            if i == last:
                return sig
        return None
