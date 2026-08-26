"""
MACD Forex Design Search — stratégie s13_macd_fx

Source : mandat Adrian (« teste le Daily MACD mean reversion sur forex » +
« développe une stratégie MACD gagnante sur des paires forex »).

TROIS FAMILLES DANS UN SEUL MODULE — le protocole est une EXPLORATION
------------------------------------------------------------------------
  * `mr`    : s12 transposé, symétrique. LONG = MACD en baisse n jours ET < 0 ;
              SHORT miroir (hausse n jours ET > 0). Sortie « reprise » s12.
  * `cross` : croisement ligne/signal ou ligne/zéro — la référence interne
              (famille probablement morte, gardée comme étalon).
  * `ext`   : extrême de distribution — MACD/ATR sous (sur) son percentile
              glissant bas (haut) → fade. Différences vs s90 déclarées dans
              research/ANALYSIS.md §4.3 AVANT toute mesure.

Chaque cellule déclare son SENS (`direction`) : les deux sens sont mesurés
séparément (F6) — le forex n'a pas la dérive séculière qui justifierait un
long-only.

Le protocole complet (hold-out scellé 2025-02-16, falsifications F1-F8,
grilles figées) est dans research/FALSIFICATION.md, commité avant tout backtest.

CAUSALITÉ (R1)
--------------
Tous les indicateurs sont des ewm/rolling strictement passés (pas de
shift(-1), pas de center=True) ; les quantiles glissants incluent la barre
courante et rien au-delà. `precompute` renvoie un DataFrame pour que la couche
indicateur de `core/validation/causality.py` soit réellement inspectée.
`generate_signals` à la barre i ne dépend que de [0, i].

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

# ── Constantes fixées HORS grille (gel 2026-08-17) ───────────────────────────
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
ATR_PERIOD = 14
RANGE_LEN = 20          # fenêtre du filtre de range (famille mr)
RANGE_Q = 0.25          # « près du bas/haut » = position dans le range ≤/≥ q
WARMUP = 60

# Sorties admissibles (figées) : nom -> (style, sl_atr, tp_atr)
EXITS = {
    "sym3":       ("sym", 3.0, None),
    "sym10":      ("sym", 10.0, None),
    "atr_1.5_1.5": ("atr", 1.5, 1.5),
    "atr_2_3":    ("atr", 3.0, 2.0),
    "hold20_sl3": ("hold", 3.0, None),   # cible None — max_hold_bars=20 côté moteur
}


class Strategy(StrategyModule):
    STRATEGY_ID = "s13_macd_fx"
    MAGIC_NUMBER = 130013

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._symbol = "UNKNOWN"

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="MACD Forex Design Search",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s13_macd_fx",
            source="s12 + mandat Adrian",
            # Post-verdict : la survivante (AUDCAD) + la jumelle en
            # observation d'hypothèse (EURJPY). L'univers d'exploration
            # complet (9 paires) est documenté dans research/FALSIFICATION.md.
            symbols=["AUDCAD", "EURJPY"],
            timeframe="D1",
            warmup_bars=WARMUP,
            # Les grilles réelles sont pilotées par les runners (une par
            # famille — cf. FALSIFICATION.md). Le param_grid du manifest reste
            # minimal pour que les CLI génériques restent exécutables.
            param_grid={
                "n_down": [3, 4, 5],
                "direction": ["long", "short"],
            },
            # Défauts = la cellule SURVIVANTE du hold-out (figée — ne pas
            # re-régler). Les autres clés restent pour les familles
            # d'exploration (sans effet quand family="ext").
            default_params={
                "family": "ext",         # mr | cross | ext
                "direction": "long",     # long | short
                "n_down": 5,             # mr : jours consécutifs de pente
                "range_filter": False,   # mr : close près du bas/haut du range
                "trigger": "sig",        # cross : sig | zero
                "lookback": 252,         # ext : fenêtre du percentile
                "q": 0.10,               # ext : quantile bas (haut = 1-q)
                "exit": "atr_1.5_1.5",   # cf. EXITS
            },
            # BACKTESTED = « mesuré », PAS « validé ». Verdict : EDGE CANDIDAT
            # (faible) — hold-out scellé +0,58 R/t x 11 trades, percentile 96
            # (AUDCAD). Suite proposée : forward scellé zéro argent. PAS de
            # promotion PAPER — décision Adrian (R10). Voir research/VERDICT.md.
            status="BACKTESTED",
            notes=("Exploration 756 cellules MACD forex D1 — familles mr/cross "
                   "mortes, survivante ext-long AUDCAD. Protocole gelé "
                   "6405c80, liste close 5fbedec. research/VERDICT.md."),
        )

    # ── Précalcul — DataFrame pour couverture indicateur R1 ──────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        close, high, low = df["close"], df["high"], df["low"]

        ef = close.ewm(span=MACD_FAST, adjust=False).mean()
        es = close.ewm(span=MACD_SLOW, adjust=False).mean()
        macd = ef - es
        sig = macd.ewm(span=MACD_SIGNAL, adjust=False).mean()

        # ATR classique (unité de risque et normalisation de `ext`).
        pc = close.shift(1)
        tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()],
                       axis=1).max(axis=1)
        atr = tr.rolling(ATR_PERIOD).mean()

        n_down = int(params.get("n_down", 5))
        d = macd.diff()
        dn = (d < 0)
        up = (d > 0)
        run_dn = dn.copy()
        run_up = up.copy()
        for k in range(1, n_down):
            run_dn &= dn.shift(k)
            run_up &= up.shift(k)

        # Position du close dans le range 20 j (barre courante incluse — la
        # décision se prend au close du jour, qui est connu).
        hh = high.rolling(RANGE_LEN).max()
        ll = low.rolling(RANGE_LEN).min()
        span = (hh - ll)
        rpos = (close - ll) / span.where(span > 0)

        # Croisements (barre courante vs veille — strictement causal).
        x_sig_up = (macd > sig) & (macd.shift(1) <= sig.shift(1))
        x_sig_dn = (macd < sig) & (macd.shift(1) >= sig.shift(1))
        x_zero_up = (macd > 0) & (macd.shift(1) <= 0)
        x_zero_dn = (macd < 0) & (macd.shift(1) >= 0)

        # Extrême de distribution : MACD normalisé ATR, percentile glissant.
        lb = int(params.get("lookback", 252))
        q = float(params.get("q", 0.05))
        macd_n = macd / atr.where(atr > 0)
        q_lo = macd_n.rolling(lb).quantile(q)
        q_hi = macd_n.rolling(lb).quantile(1.0 - q)

        # Cibles « reprise » s12 (statiques, posées au signal — dégradation
        # déclarée) : long = max(high jour, close veille) ; short miroir.
        tref_hi = pd.concat([high, pc], axis=1).max(axis=1)
        tref_lo = pd.concat([low, pc], axis=1).min(axis=1)

        return pd.DataFrame({
            "close": close, "high": high, "low": low,
            "macd": macd, "sig": sig, "atr": atr,
            "run_dn": run_dn.fillna(False).astype(float),
            "run_up": run_up.fillna(False).astype(float),
            "rpos": rpos,
            "x_sig_up": x_sig_up.fillna(False).astype(float),
            "x_sig_dn": x_sig_dn.fillna(False).astype(float),
            "x_zero_up": x_zero_up.fillna(False).astype(float),
            "x_zero_dn": x_zero_dn.fillna(False).astype(float),
            "macd_n": macd_n, "q_lo": q_lo, "q_hi": q_hi,
            "tref_hi": tref_hi, "tref_lo": tref_lo,
        }, index=df.index)

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        family = str(params.get("family", "mr"))
        direction = str(params.get("direction", "long"))
        exit_name = str(params.get("exit", "sym10"))
        style, sl_m, tp_m = EXITS[exit_name]
        long = direction == "long"

        n = min(end_idx, len(data))
        idx = data.index
        close = data["close"].to_numpy()
        macd = data["macd"].to_numpy()
        atr = data["atr"].to_numpy()

        with np.errstate(invalid="ignore"):
            if family == "mr":
                if long:
                    mask = (data["run_dn"].to_numpy() > 0.5) & (macd < 0.0)
                else:
                    mask = (data["run_up"].to_numpy() > 0.5) & (macd > 0.0)
                if bool(params.get("range_filter", False)):
                    rpos = data["rpos"].to_numpy()
                    ok = np.isfinite(rpos)
                    mask &= ok & ((rpos <= RANGE_Q) if long else (rpos >= 1.0 - RANGE_Q))
            elif family == "cross":
                trig = str(params.get("trigger", "sig"))
                col = {("sig", True): "x_sig_up", ("sig", False): "x_sig_dn",
                       ("zero", True): "x_zero_up", ("zero", False): "x_zero_dn"}[(trig, long)]
                mask = data[col].to_numpy() > 0.5
            elif family == "ext":
                mn = data["macd_n"].to_numpy()
                if long:
                    thr = data["q_lo"].to_numpy()
                    mask = np.isfinite(mn) & np.isfinite(thr) & (mn <= thr)
                else:
                    thr = data["q_hi"].to_numpy()
                    mask = np.isfinite(mn) & np.isfinite(thr) & (mn >= thr)
            else:
                raise ValueError(f"famille inconnue : {family}")

            mask &= np.isfinite(atr) & (atr > 0.0)

        cand = np.flatnonzero(mask[:n])
        cand = cand[cand >= WARMUP]

        tref = data["tref_hi" if long else "tref_lo"].to_numpy()
        out: list[Signal] = []
        for i in cand:
            i = int(i)
            entry = float(close[i])
            a = float(atr[i])
            if style == "sym":
                target = float(tref[i])
                if not np.isfinite(target):
                    continue
                if (long and target <= entry) or (not long and target >= entry):
                    continue             # pas de niveau de reprise du bon côté
            elif style == "atr":
                target = entry + tp_m * a if long else entry - tp_m * a
            else:                        # hold : pas de cible, horizon fixe moteur
                target = None
            stop = entry - sl_m * a if long else entry + sl_m * a
            out.append(Signal(
                timestamp=idx[i], symbol=self._symbol,
                side=Side.LONG if long else Side.SHORT,
                entry=entry, stop=stop, target=target,
                reason=f"{family}/{direction}/{exit_name}",
                meta={"macd": round(float(macd[i]), 6), "atr": a},
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
