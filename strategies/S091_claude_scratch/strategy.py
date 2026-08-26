"""
Asian-window fade — stratégie s91_claude_scratch

Source : conception autonome (aucune source externe à reproduire)
Auteur : Claude Code, agent dédié s91_claude_scratch

HYPOTHÈSE H91 (figée en Phase 1, cf. research/ANALYSIS.md §3)
-------------------------------------------------------------
Dans la fenêtre de faible liquidité (heure serveur 22h-06h), une extension de
prix sur H1 n'est pas de l'information mais du bruit de carnet mince, et elle se
rétracte partiellement. L'effet n'existe que pour les paires dont aucune devise
n'a de session domestique à ce moment-là. Pour les paires JPY, cette même
fenêtre est la session de Tokyo — donc du vrai flux — et l'effet doit y être
absent ou inversé.

USDJPY et EURJPY sont donc déclarés dans le manifest non pas comme des candidats
mais comme un **CONTRÔLE NÉGATIF** : H91 prédit qu'ils échouent. S'ils
réussissent aussi bien que les quatre autres, le mécanisme invoqué est faux
(condition de falsification F2).

LA RÈGLE, EN TROIS LIGNES
-------------------------
    z = (close - SMA(20)) / ecart-type(20)
    si heure dans la fenêtre morte ET |z| >= z_min  ->  entrer CONTRE l'extension
    stop = sl_atr x ATR(24)   ;   cible = rr x risque

Aucun filtre supplémentaire. Chaque paramètre ajouté multiplie le nombre de faux
positifs disponibles dans la grille ; la grille (54 cellules) est là pour mesurer
la sensibilité de l'hypothèse, pas pour trouver une cellule gagnante.

CAUSALITÉ (R1)
--------------
Toutes les grandeurs dérivées sont des `rolling` pandas, donc strictement
causales : la valeur à l'indice i ne dépend que des indices <= i. Il en découle
que `precompute(df)[:T] == precompute(df[:T])`, qui est exactement l'invariant
de troncature. `generate_signals` ne lit jamais au-delà de `end_idx`.

ÉCONOMIE (calculée AVANT d'écrire ce fichier — ANALYSIS.md §4)
---------------------------------------------------------------
Sur la tranche d'entraînement, groupe éligible : dérive brute +2,66 pips contre
un spread aller-retour moyen de 2,30 pips, soit une marge de 16 %. C'est un
liseré, pas une marge. Le résultat hors échantillon attendu est nul ou marginal.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Fenêtres en HEURE SERVEUR MT5 (~ GMT+2/+3), calibrée par le projet sur le
# profil de volatilité EURUSD. Ce ne sont pas des heures UTC.
WINDOWS = {
    "large":   (22, 23, 0, 1, 2, 3, 4, 5, 6),   # zone morte mesurée du projet
    "etroite": (23, 0, 1, 2, 3, 4),             # coeur de la zone morte
}

Z_PERIOD = 20      # fixe, non grillé : c'est la définition de l'extension
ATR_PERIOD = 24    # fixe, non grillé : une journée de barres H1

# Les 4 instruments que le mécanisme rend éligibles, puis les 2 contrôles.
ELIGIBLE = ["EURUSD", "USDCHF", "USDCAD", "AUDUSD"]
CONTROL_JPY = ["USDJPY", "EURJPY"]


class Strategy(StrategyModule):
    STRATEGY_ID = "s91_claude_scratch"
    MAGIC_NUMBER = 130091

    # Le symbole n'est pas un paramètre de stratégie (il ne change aucun
    # indicateur) : le harnais le pose comme attribut, comme pour s01.
    _symbol: str = "EURUSD"

    # ── Déclaration ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Asian-window fade (H91)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s91_claude_scratch",
            source="conception autonome — hypothèse H91, research/ANALYSIS.md",
            symbols=ELIGIBLE + CONTROL_JPY,
            timeframe="H1",
            warmup_bars=50,          # > max(Z_PERIOD, ATR_PERIOD) avec marge
            param_grid={
                "z_min":  [1.5, 2.0, 2.5],
                "sl_atr": [2.0, 2.5, 3.0],
                "rr":     [0.75, 1.0, 1.5],
                "window": ["large", "etroite"],
            },                        # 3 x 3 x 3 x 2 = 54 configurations
            default_params={
                "z_min": 2.0,
                "sl_atr": 2.5,
                "rr": 1.0,
                "window": "large",
            },
            status="RESEARCH",
            notes=(
                "Contre-tendance en fenêtre de faible liquidité. "
                "USDJPY et EURJPY sont un CONTRÔLE NÉGATIF déclaré (F2), "
                "pas des candidats. Voir research/ANALYSIS.md."
            ),
        )

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Indicateurs, une seule fois. Tout est `rolling` donc causal.

        Ne dépend d'AUCUN paramètre de la grille : z_min, sl_atr, rr et window
        s'appliquent au moment de la décision, pas au calcul. Le cache du
        walk-forward est donc partagé par les 54 cellules.

        RENVOIE UN DataFrame, ET C'EST DÉLIBÉRÉ. `core/validation/causality.py`
        ne peut inspecter la COUCHE INDICATEUR que si `precompute` renvoie un
        DataFrame ; sur un objet opaque (dict, tuple), il retourne sans rien
        vérifier. Un dict aurait donc fait passer R1 sans que les indicateurs
        soient jamais comparés. Ce n'est pas une préférence de style : c'est ce
        qui met la stratégie sous le contrôle du gardien plutôt qu'à côté.
        """
        close = df["close"]
        high, low = df["high"], df["low"]

        mean = close.rolling(Z_PERIOD).mean()
        std = close.rolling(Z_PERIOD).std()
        z = (close - mean) / std.replace(0.0, np.nan)

        prev_close = close.shift(1)
        true_range = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        atr = true_range.rolling(ATR_PERIOD).mean()

        return pd.DataFrame(
            {
                "close": close.astype(float),
                "z": z.astype(float),
                "atr": atr.astype(float),
                "hour": df.index.hour.astype("int64"),
            },
            index=df.index,
        )

    def generate_signals(self, data, params: dict, end_idx: int) -> list[Signal]:
        """Signaux sur [0, end_idx). Rien à l'indice >= end_idx n'est lu."""
        z_min = float(params["z_min"])
        sl_atr = float(params["sl_atr"])
        rr = float(params["rr"])
        hours_ok = WINDOWS[params["window"]]

        idx = data.index
        hour = data["hour"].to_numpy()
        close = data["close"].to_numpy()
        z = data["z"].to_numpy()
        atr = data["atr"].to_numpy()

        start = self.manifest().warmup_bars
        stop_at = min(int(end_idx), len(close))

        in_window = np.isin(hour, hours_ok)
        signals: list[Signal] = []

        for i in range(start, stop_at):
            if not in_window[i]:
                continue
            zi, ai = z[i], atr[i]
            if not np.isfinite(zi) or not np.isfinite(ai) or ai <= 0.0:
                continue
            if abs(zi) < z_min:
                continue

            entry = float(close[i])
            risk = sl_atr * float(ai)
            if risk <= 0.0:
                continue

            # On entre CONTRE l'extension : z élevé = prix trop haut = vente.
            if zi > 0:
                side, stop, target = Side.SHORT, entry + risk, entry - rr * risk
            else:
                side, stop, target = Side.LONG, entry - risk, entry + rr * risk

            signals.append(Signal(
                timestamp=idx[i],
                symbol=self._symbol,
                side=side,
                entry=entry,
                stop=stop,
                target=target,
                reason=(f"fade z={zi:+.2f} h={int(hour[i]):02d} "
                        f"risque={risk:.5f}"),
                meta={"z": float(zi), "hour": int(hour[i]),
                      "atr": float(ai), "window": params["window"]},
            ))

        return signals

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """Décision sur la barre qui vient de clôturer.

        R5 / R6 — il n'existe volontairement PAS de seconde implémentation :
        cette méthode appelle littéralement `precompute` puis `generate_signals`
        et ne retient que la décision de la dernière barre. Les deux chemins ne
        peuvent donc pas diverger. Ce n'est pas une preuve de conformité, c'est
        une garantie structurelle (`core/validation/conformance.py` n'existe pas
        dans le dépôt — limite déclarée dans ANALYSIS.md §7.3).
        """
        bars = ctx.bars
        n = len(bars)
        if n <= self.manifest().warmup_bars:
            return None
        if ctx.own_position:            # une position à la fois
            return None

        previous = self._symbol
        self._symbol = ctx.symbol
        try:
            data = self.precompute(bars, self.params)
            signals = self.generate_signals(data, self.params, n)
        finally:
            self._symbol = previous

        if not signals:
            return None
        last = signals[-1]
        # Seule la barre courante déclenche un ordre.
        return last if pd.Timestamp(last.timestamp) == bars.index[n - 1] else None
