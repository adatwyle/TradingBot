"""
Daily MACD Mean Reversion — stratégie s12_prt_macd_meanrev

Source : https://www.youtube.com/watch?v=1l7xWU-BU3w (ProRealTime, algo gratuit
« Daily MACD strategy », release juin 2022). Transcript 20:00-21:30.

LA LOGIQUE, EN UNE PHRASE
--------------------------
Sur indice en daily, LONG uniquement : acheter la faiblesse quand l'élan MACD
baisse depuis 5 jours ET que le MACD est sous zéro ET que le close est dans le
bas de son range récent ; sortir dès que le prix recasse le plus haut de la
veille. Mean reversion CLASSIQUE — la famille que la synthèse aipathways déclare
la seule largement vivante, jamais testée chez nous (s10 = divergence H1, autre
objet).

REPRODUCTION, PAS PORTAGE
--------------------------
Le code ProBuilder n'est pas disponible ; la logique vient du transcript (les
conditions y sont énoncées une à une). Ambiguïtés résolues en Phase 1 et FIGÉES
dans research/FALSIFICATION.md AVANT tout backtest :

  * « MACD value »            -> ligne MACD (EMA12 − EMA26), pas l'histogramme
  * « falling over 5 days »   -> macd[i] < macd[i-1] pour les 5 derniers pas
  * « near the low of the trading range » -> position du close dans le range
    high/low des `range_len` derniers jours ≤ `pos_max` (2 fenêtres × 2 seuils
    dans la grille)
  * sortie « close casse le plus haut de la veille » -> DÉGRADATION DÉCLARÉE
    n°1 : le moteur commun (R9) n'exprime que des cibles statiques. Cible posée
    à max(high[jour signal], close[veille]) — exacte pour une sortie dès le
    lendemain, conservatrice ensuite (le seuil source se recale vers le bas
    chaque jour de baisse, le nôtre non).
  * pas de stop dans la source -> R3 impose un stop : 10 ATR = proxy « sans
    stop » (chiffre le gap/krach au lieu de l'ignorer), 3 ATR = variante gérée.

CAUSALITÉ (R1)
--------------
Tous les indicateurs sont des rolling/ewm strictement passés (pas de
`shift(-1)`, pas de `center=True`). `precompute` renvoie un DataFrame pour que
la couche indicateur de `core/validation/causality.py` soit réellement
inspectée. `generate_signals` ne lit que des lignes < end_idx et chaque
condition à la barre i ne dépend que de [0, i].

R2/R3/R9 : aucune taille calculée, stop toujours renseigné, exécution
entièrement dans `core/backtest/engine.py`.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# ── Constantes fixées HORS grille (Phase 1, avant tout résultat) ─────────────
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9   # signal 9 déclaré mais la ligne
#                                                 seule est utilisée (cf. gel)
MACD_DOWN_DAYS = 5      # « consistently falling over a period of 5 days »
ATR_PERIOD = 14         # unité de risque pour le stop (la source n'a pas d'ATR)
WARMUP = 60             # EMA26 + range 20 + 5 baisses : large marge


class Strategy(StrategyModule):
    STRATEGY_ID = "s12_prt_macd_meanrev"
    MAGIC_NUMBER = 130012

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._symbol = "UNKNOWN"

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Daily MACD Mean Reversion (ProRealTime)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s12_prt_macd_meanrev",
            source="https://www.youtube.com/watch?v=1l7xWU-BU3w",
            # SP500 = l'instrument de la source. NASDAQ et DAX = transfert à
            # froid (même famille d'actifs, aucun réglage dédié).
            symbols=["SP500", "NASDAQ", "DAX"],
            timeframe="D1",
            warmup_bars=WARMUP,
            param_grid={
                "range_len": [10, 20],
                "pos_max": [0.20, 0.35],
                "no_friday": [False, True],
                "sl_atr": [3.0, 10.0],
            },                              # 16 cellules — figées au gel
            default_params={
                "range_len": 20,
                "pos_max": 0.20,
                "no_friday": False,
                "sl_atr": 10.0,             # proxy « sans stop » (fidélité source)
                # ── Addendum 2026-08-16 (post-gel, correction de FIDÉLITÉ pas
                # de performance — transcript indépendant prorealalgos/10) :
                # la source exige AUSSI close < close[1] ; et son MACD est
                # peut-être leur « S-MACD » normalisé par le prix. Défauts =
                # comportement gelé ; variantes testées hors grille, déclarées
                # dans FALSIFICATION.md §Addendum.
                "close_down": False,        # exiger close[i] < close[i-1]
                "macd_rel": False,          # MACD/close (proxy S-MACD)
            },
            # BACKTESTED = « mesuré », PAS « validé ». Verdict : PAS D'EDGE
            # (F1/F2/F3 déclenchées). Ne pas promouvoir en PAPER — décision
            # d'Adrian (R10).
            status="BACKTESTED",
            notes=("Mean reversion classique D1 long-only sur indice. Verdict "
                   "PAS D'EDGE : témoin aléatoire percentile 51,5 (SP500), "
                   "espérance négative à spread nul, et sur 1927-2026 les jours "
                   "sélectionnés font +0,8 %/an contre +6,4 %/an B&H (464 "
                   "trades). Post-release 2022-06-21 = beta pur. Voir "
                   "research/VERDICT.md."),
        )

    # ── Précalcul — DataFrame pour couverture indicateur R1 ──────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Indicateurs causaux uniquement. Le range dépend de `range_len` (grille)
        donc le harnais met en cache par jeu de paramètres complet — correct."""
        rl = int(params["range_len"])
        close = df["close"]
        high = df["high"]
        low = df["low"]

        ef = close.ewm(span=MACD_FAST, adjust=False).mean()
        es = close.ewm(span=MACD_SLOW, adjust=False).mean()
        macd = ef - es
        if bool(params.get("macd_rel", False)):
            macd = macd / close          # proxy S-MACD : MACD relatif au prix
        #                                  (signe inchangé, pente quasi inchangée)

        # 5 pas de baisse consécutifs, terminés à la barre courante.
        down = macd.diff() < 0
        down5 = down.copy()
        for k in range(1, MACD_DOWN_DAYS):
            down5 &= down.shift(k)

        # Addendum fidélité : « the close of today is weaker than yesterday ».
        closedn = (close < close.shift(1))

        # Range des `rl` derniers jours, barre courante INCLUSE (le close du
        # jour est connu à la clôture — c'est le moment de la décision).
        hh = high.rolling(rl).max()
        ll = low.rolling(rl).min()
        span = (hh - ll)
        pos = (close - ll) / span.where(span > 0)

        # ATR classique — sur données close-only (LONGHIST), TR dégénère en
        # |Δclose| : déclaré (dégradation n°5 du gel).
        pc = close.shift(1)
        tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()],
                       axis=1).max(axis=1)
        atr = tr.rolling(ATR_PERIOD).mean()

        # Cible de sortie : max(high du jour signal, close de la veille).
        # Sur OHLC réel ≈ high du jour ; sur close-only ≈ close de la veille.
        target_ref = pd.concat([high, pc], axis=1).max(axis=1)

        return pd.DataFrame({
            "close": close, "high": high, "low": low,
            "macd": macd,
            "down5": down5.fillna(False).astype(float),
            "closedn": closedn.fillna(False).astype(float),
            "range_pos": pos,
            "atr": atr,
            "target_ref": target_ref,
        }, index=df.index)

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Chaque signal à la barre i ne dépend que de [0, i] ; la coupe à
        end_idx est donc une simple troncature (invariant R1)."""
        pos_max = float(params["pos_max"])
        no_friday = bool(params["no_friday"])
        sl_m = float(params["sl_atr"])

        idx = data.index
        n = min(end_idx, len(data))
        close = data["close"].to_numpy()
        macd = data["macd"].to_numpy()
        down5 = data["down5"].to_numpy() > 0.5
        rpos = data["range_pos"].to_numpy()
        atr = data["atr"].to_numpy()
        tref = data["target_ref"].to_numpy()

        with np.errstate(invalid="ignore"):
            mask = (down5 & (macd < 0.0)
                    & np.isfinite(rpos) & (rpos <= pos_max)
                    & np.isfinite(atr) & (atr > 0.0))
        if bool(params.get("close_down", False)):
            mask &= data["closedn"].to_numpy() > 0.5
        cand = np.flatnonzero(mask[:n])
        cand = cand[cand >= WARMUP]

        out: list[Signal] = []
        for i in cand:
            i = int(i)
            ts = idx[i]
            if no_friday and ts.dayofweek == 4:
                continue                     # sa cellule « pas d'entrée vendredi »
            entry = float(close[i])
            target = float(tref[i])
            if not np.isfinite(target) or target <= entry:
                continue                     # pas de niveau de reprise au-dessus
            stop = entry - sl_m * float(atr[i])
            out.append(Signal(
                timestamp=ts, symbol=self._symbol, side=Side.LONG,
                entry=entry, stop=stop, target=target,
                reason=(f"MACD<0 en baisse {MACD_DOWN_DAYS}j, close à "
                        f"{100*rpos[i]:.0f}% du range — reprise visée {target:.2f}"),
                meta={"macd": round(float(macd[i]), 4),
                      "range_pos": round(float(rpos[i]), 3),
                      "atr": float(atr[i])},
            ))
        return out

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : même chemin de décision que le backtest, on ne
        garde que la barre courante."""
        bars = ctx.bars
        if len(bars) < WARMUP + 5:
            return None
        self._symbol = ctx.symbol
        data = self.precompute(bars, self.params)
        sigs = self.generate_signals(data, self.params, len(bars))
        last = bars.index[-1]
        for s in reversed(sigs):
            if pd.Timestamp(s.timestamp) == last:
                return s
        return None
