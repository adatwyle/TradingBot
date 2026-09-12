"""
S020 — MACD cross + filtre ligne zéro, SL/TP en % du prix (René Balke).

Source : « Use AI to Automate ANY MT5 Indicator with one Prompt » (BM Trading,
2026-08-23, https://www.youtube.com/watch?v=-9HUV9I_s-c). L'auteur dicte la règle en
clair à [01:00]-[08:30] et la fait tourner dans le Strategy Tester sur US Tech à
[16:30]-[19:30]. Elle est reproduite ICI TELLE QUELLE — pas une variante « améliorée » :

  ENTRÉE   la ligne MACD (EMA12 − EMA26 du close) croise la ligne de signal
           (EMA9 de la MACD) à la hausse → achat ; à la baisse → vente. [01:00]
  FILTRE   optionnel : achat seulement si la MACD est SOUS zéro au croisement,
           vente seulement si elle est AU-DESSUS. [01:30] [06:20]
  SORTIE   stop et cible = un pourcentage du prix d'entrée, chacun réglable
           (démo : 2 % / 2 %). [07:15] [16:55]
  DIVERS   une position par symbole (ajout de l'IA, conservé par l'auteur) [15:20] ;
           unité de temps = paramètre [06:20] ; sizing par montant ou % de risque
           (couche risque, hors stratégie — R2).

Ce que la plateforme ajoute et qui N'EST PAS dans la vidéo : le coût de bord réel,
le refroidissement et le coupe-circuit du moteur commun (règles communes contre les
pertes consécutives — directive Adrian 2026-09-12), le bras témoin aléatoire.

Voisinage interne, déclaré pour ne pas le redécouvrir : S013 contient une famille
`cross` (croisement ligne/signal ou ligne/zéro, sorties ATR, forex D1) jugée « probablement
morte, gardée comme étalon ». La règle de Balke en diffère par la COMBINAISON
croisement + filtre zéro, la géométrie en % et les instruments (indices, intraday).
C'est une donnée d'entrée, pas un verdict : S020 fait son propre run.

CAUSALITÉ (R1) : ewm strictement passés, croisement lu par shift(1). generate_signals
à la barre i ne dépend que de [0, i]. on_bar délègue au même code (R5).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9      # défauts MT5, appliqués tels quels [00:50]
WARMUP_BARS = 60


class Strategy(StrategyModule):

    def __init__(self, params: Optional[dict] = None):
        self.params = dict(self.manifest().default_params)
        if params:
            self.params.update(params)
        self._symbol = "NASDAQ"

    # ── manifeste ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id="S020_balke_macd_cross",
            display_name="MACD cross + filtre zéro, SL/TP en % (René Balke)",
            version="1.0.0",
            magic_number=130020,
            author="claude:S020_balke_macd_cross",
            source="https://www.youtube.com/watch?v=-9HUV9I_s-c",
            symbols=["NASDAQ", "SP500", "DAX", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"],
            timeframe="H1",
            warmup_bars=WARMUP_BARS,
            # 18 cellules : la règle a trois réglages et l'auteur dit lui-même que
            # les % « ne comptent pas tant que ça » — on regarde donc autour de sa
            # démo (2 %/2 %) sans aller chercher plus loin.
            param_grid={
                "zero_filter": [False, True],
                "sl_pct": [0.005, 0.01, 0.02],
                "tp_pct": [0.01, 0.02, 0.04],
            },
            default_params={
                "zero_filter": True,          # il l'active à [18:40] après l'avoir oublié
                "sl_pct": 0.02,
                "tp_pct": 0.02,
                "side_mode": "both",
            },
            status="RESEARCH",
            notes=("Reproduction fidèle de la règle dictée dans la vidéo. Pas de "
                   "réglage après lecture des résultats : research/FALSIFICATION.md "
                   "fixe les seuils d'avance."),
        )

    # ── indicateurs ────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        close = df["close"]
        ef = close.ewm(span=MACD_FAST, adjust=False).mean()
        es = close.ewm(span=MACD_SLOW, adjust=False).mean()
        macd = ef - es
        sig = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()
        diff = macd - sig
        prev = diff.shift(1)
        out = pd.DataFrame(index=df.index)
        out["close"] = close
        out["macd"] = macd
        out["signal"] = sig
        # croisement = changement de signe de (macd − signal) entre i−1 et i
        out["x_up"] = ((prev <= 0.0) & (diff > 0.0)).astype(float)
        out["x_dn"] = ((prev >= 0.0) & (diff < 0.0)).astype(float)
        return out

    # ── signaux ────────────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        zero_filter = bool(params.get("zero_filter", True))
        sl_pct = float(params.get("sl_pct", 0.02))
        tp_pct = float(params.get("tp_pct", 0.02))
        side_mode = str(params.get("side_mode", "both"))
        if side_mode not in ("both", "long_only", "short_only"):
            raise ValueError(f"side_mode inconnu : {side_mode}")
        if sl_pct <= 0 or tp_pct <= 0:
            raise ValueError("sl_pct et tp_pct doivent être strictement positifs")

        n = min(end_idx, len(data))
        idx = data.index
        close = data["close"].to_numpy()
        macd = data["macd"].to_numpy()
        x_up = data["x_up"].to_numpy() > 0.5
        x_dn = data["x_dn"].to_numpy() > 0.5

        out: list[Signal] = []
        for i in range(WARMUP_BARS, n):
            if not np.isfinite(macd[i]):
                continue
            long = short = False
            if x_up[i] and side_mode != "short_only":
                long = (macd[i] < 0.0) if zero_filter else True
            if x_dn[i] and side_mode != "long_only":
                short = (macd[i] > 0.0) if zero_filter else True
            if not (long or short):
                continue
            entry = float(close[i])
            if long:
                stop, target, side = entry * (1 - sl_pct), entry * (1 + tp_pct), Side.LONG
            else:
                stop, target, side = entry * (1 + sl_pct), entry * (1 - tp_pct), Side.SHORT
            out.append(Signal(
                timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                symbol=self._symbol, side=side,
                entry=entry, stop=stop, target=target,
                reason=(f"MACD {'↑' if long else '↓'} signal"
                        f"{' · zéro' if zero_filter else ''} · sl {sl_pct:.1%} tp {tp_pct:.1%}"),
                meta={"macd": float(macd[i]), "zero_filter": zero_filter},
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
