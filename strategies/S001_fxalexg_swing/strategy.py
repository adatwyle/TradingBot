"""
FXAlexG Swing HTF — stratégie s01_fxalexg_swing

Source : https://www.youtube.com/@fxalexg__
Trader : fxalexg (1.3M abo)

Reproduction mécanique de la méthode décrite par la source (voir
`research/ANALYSIS.md` pour la décomposition composant par composant) :

    1. STRUCTURE sur timeframe ÉLEVÉ (H4 ou D1, rééchantillonné depuis H1)
       Swings fractals -> biais haussier (HH+HL) / baissier (LL+LH) / neutre.
    2. RETRACEMENT obligatoire : on n'entre que dans la zone de retracement de
       la dernière jambe d'impulsion HTF. Jamais en chasse.
    3. ENTRÉE sur timeframe INFÉRIEUR (H1) : on attend qu'un swing contraire
       (lower high en biais baissier, higher low en biais haussier) se CONFIRME
       à l'intérieur de la zone. C'est le « j'anticipe le lower high » de la
       source, rendu mécanique.
    4. SET & FORGET : stop au-delà du swing d'entrée, cible à un multiple fixe
       du risque, aucune sortie temporelle. Les détentions longues (jours) sont
       une CONSÉQUENCE du risque ancré sur un swing HTF, pas une contrainte
       imposée.
    5. SÉLECTIVITÉ : une seule entrée par jambe.

CAUSALITÉ (R1) — comment elle est garantie
-------------------------------------------
Le point sensible d'une stratégie de structure est qu'un swing n'est PAS connu
au moment où il se forme : il faut `k` barres de plus pour savoir que le sommet
a tenu. Ici :

  * un swing fractal en position `j` (TF quelconque) n'est réputé CONNU qu'à
    partir de la barre `j + k` ;
  * un swing HTF n'est utilisable qu'à partir de l'instant où la barre HTF
    `j + k` est CLÔTURÉE (`htf_index[j+k] + durée_barre <= heure H1 courante`) ;
  * aucun indicateur non causal (pas de `shift(-1)`, pas de `center=True`).

Conséquence : `precompute(df)` puis filtrage à `end_idx` produit exactement le
même résultat que `precompute(df[:end_idx])`. C'est ce que teste R1.

Le rééchantillonnage H1 -> H4/D1 mérite une note : dans un tableau tronqué, le
DERNIER groupe HTF est partiel, donc son high/low peut différer du tableau
complet. Ce groupe partiel ne peut jamais influencer un signal, parce qu'un
swing ne devient utilisable qu'après clôture de la barre `j + k`, laquelle est
par construction postérieure à la fin des données tronquées. C'est vérifié
empiriquement par `core/validation/causality.py`.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Timeframe de structure -> (règle de rééchantillonnage pandas, durée d'une barre)
_HTF = {
    "H4": ("4h", pd.Timedelta(hours=4)),
    "D1": ("1D", pd.Timedelta(days=1)),
}

_BULL, _NEUTRAL, _BEAR = 1, 0, -1


# ─────────────────────────────────────────────────────────────────────────────
# Briques causales
# ─────────────────────────────────────────────────────────────────────────────

def _fractals(high: np.ndarray, low: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Swings de Williams.

    `sh[j] = True` si `high[j]` domine strictement les `k` barres à gauche et
    domine (au sens large) les `k` barres à droite. La stricte inégalité à
    gauche évite de compter deux fois un sommet plat.

    ATTENTION : ce tableau décrit une VÉRITÉ RÉTROSPECTIVE. Il n'est pas
    utilisable tel quel — l'appelant DOIT décaler de `k` barres pour obtenir
    l'instant où l'information devient disponible. Voir `_htf_structure` et
    `_scan`.
    """
    n = len(high)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    if n < 2 * k + 1:
        return sh, sl

    # wmax[s] = max(high[s : s+k])  — fenêtres glissantes, pas de boucle Python.
    wmax = sliding_window_view(high, k).max(axis=1)
    wmin = sliding_window_view(low, k).min(axis=1)
    j = np.arange(k, n - k)
    sh[j] = (high[j] > wmax[j - k]) & (high[j] >= wmax[j + 1])
    sl[j] = (low[j] < wmin[j - k]) & (low[j] <= wmin[j + 1])
    return sh, sl


def _htf_structure(df: pd.DataFrame, idx: pd.DatetimeIndex, htf: str, k: int):
    """Biais de structure et jambe d'impulsion courante, alignés sur chaque
    barre H1.

    Retourne quatre tableaux de longueur `len(idx)` :
        bias   : +1 haussier (HH+HL) / -1 baissier (LL+LH) / 0 neutre
        leg_h  : prix du dernier swing haut HTF connu
        leg_l  : prix du dernier swing bas HTF connu
        leg_id : identifiant de l'état de structure — change à chaque nouveau
                 swing connu. Sert à n'autoriser qu'une entrée par jambe.
    """
    rule, dur = _HTF[htf]
    htf_df = (df.resample(rule)
                .agg({"high": "max", "low": "min"})
                .dropna())

    n = len(idx)
    bias = np.zeros(n, dtype=np.int8)
    leg_h = np.full(n, np.nan)
    leg_l = np.full(n, np.nan)
    leg_id = np.zeros(n, dtype=np.int32)

    if len(htf_df) < 2 * k + 2:
        return bias, leg_h, leg_l, leg_id

    hh = htf_df["high"].to_numpy()
    ll = htf_df["low"].to_numpy()
    hidx = htf_df.index
    sh, sl = _fractals(hh, ll, k)

    # Événements = (instant où l'information devient disponible, type, prix).
    # L'instant de disponibilité est la CLÔTURE de la barre HTF j+k, jamais
    # celle de la barre j elle-même.
    events: list[tuple[pd.Timestamp, int, float]] = []
    for j in range(k, len(htf_df) - k):
        if sh[j]:
            events.append((hidx[j + k] + dur, +1, float(hh[j])))
        if sl[j]:
            events.append((hidx[j + k] + dur, -1, float(ll[j])))
    events.sort(key=lambda e: (e[0], e[1]))

    sh_prev = sh_last = sl_prev = sl_last = np.nan
    state = 0
    p = 0
    for i in range(n):
        t = idx[i]
        while p < len(events) and events[p][0] <= t:
            _, kind, price = events[p]
            if kind > 0:
                sh_prev, sh_last = sh_last, price
            else:
                sl_prev, sl_last = sl_last, price
            state += 1
            p += 1

        leg_id[i] = state
        if np.isnan(sh_prev) or np.isnan(sl_prev):
            continue

        leg_h[i] = sh_last
        leg_l[i] = sl_last
        if sh_last > sh_prev and sl_last > sl_prev:
            bias[i] = _BULL
        elif sh_last < sh_prev and sl_last < sl_prev:
            bias[i] = _BEAR

    return bias, leg_h, leg_l, leg_id


def _atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().to_numpy()


# ─────────────────────────────────────────────────────────────────────────────
# Stratégie
# ─────────────────────────────────────────────────────────────────────────────

class Strategy(StrategyModule):
    STRATEGY_ID = "s01_fxalexg_swing"
    MAGIC_NUMBER = 130001

    ATR_PERIOD = 14

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="FXAlexG Swing HTF",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s01_fxalexg_swing",
            source="https://www.youtube.com/@fxalexg__",
            # Généraliste : la méthode ne cible pas d'instrument particulier.
            # Restreint au catalogue de core/data/instruments.py.
            symbols=["EURUSD", "USDJPY", "USDCHF", "AUDUSD",
                     "USDCAD", "EURJPY", "XAUUSD"],
            timeframe="H1",          # TF d'exécution ; la structure vient de htf
            warmup_bars=500,
            param_grid={
                "htf":        ["H4", "D1"],
                "k_htf":      [2, 3],
                "k_ltf":      [2, 3],
                "retr_min":   [0.382, 0.5],
                "retr_max":   [0.786, 1.0],
                # Cible : structurelle (continuation de la jambe HTF, ce qui
                # produit les détentions de plusieurs jours que la source
                # décrit) ou multiple fixe du risque (contrôle).
                "target":     ["struct", "ext27", "ext62", "rr3"],
            },                        # 2*2*2*2*2*4 = 128 configurations
            default_params={
                "htf": "D1",
                "k_htf": 2,
                "k_ltf": 3,
                "retr_min": 0.382,
                "retr_max": 0.786,
                "target": "struct",
                "sl_buf_atr": 0.5,    # fixé, volontairement hors grille
            },
            status="RESEARCH",
            notes="Structure HTF (H4/D1) + entrée H1 sur retracement. Set & forget.",
        )

    # ── Précalcul ────────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Produit la LISTE COMPLÈTE des signaux, chacun étiqueté par l'indice
        de barre où la décision est prise.

        Tout le travail est fait ici parce que chaque décision ne dépend que du
        passé : `generate_signals` n'a plus qu'à couper la liste. C'est aussi ce
        qui rend le walk-forward rapide (8 appels par configuration).
        """
        idx = df.index
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        atr = _atr(df, self.ATR_PERIOD)

        bias, leg_h, leg_l, leg_id = _htf_structure(
            df, idx, params["htf"], int(params["k_htf"]))
        sh, sl = _fractals(highs, lows, int(params["k_ltf"]))

        signals = self._scan(idx, highs, lows, closes, atr,
                             bias, leg_h, leg_l, leg_id, sh, sl, params)
        return {"index": idx, "signals": signals}

    @staticmethod
    def _target(mode: str, entry: float, risk: float,
                anchor: float, span: float, *, short: bool) -> float:
        """Cible de la position.

        `struct` / `struct_ext` sont les cibles fidèles à la source : on vise la
        CONTINUATION de la jambe de structure (nouveau lower low / higher high),
        c'est-à-dire l'extrémité de la jambe HTF, éventuellement prolongée.
        C'est ce qui produit mécaniquement les détentions de plusieurs jours.

        `rr2` / `rr3` sont des cibles de CONTRÔLE, à multiple fixe du risque :
        elles permettent de voir si l'éventuel résultat vient de la structure ou
        simplement du choix du R:R.
        """
        if mode == "struct":
            return anchor
        if mode in ("ext27", "ext62"):
            e = 0.272 if mode == "ext27" else 0.618
            return anchor - e * span if short else anchor + e * span
        return entry - 3.0 * risk if short else entry + 3.0 * risk

    def _scan(self, idx, highs, lows, closes, atr,
              bias, leg_h, leg_l, leg_id, sh, sl, params) -> list[tuple[int, Signal]]:
        k_ltf = int(params["k_ltf"])
        rmin = float(params["retr_min"])
        rmax = float(params["retr_max"])
        tmode = str(params["target"])
        buf = float(params.get("sl_buf_atr", 0.5))
        warmup = self.manifest().warmup_bars
        symbol = getattr(self, "_symbol", "UNKNOWN")

        n = len(idx)
        out: list[tuple[int, Signal]] = []
        traded_leg = -1        # une seule entrée par état de structure

        for i in range(max(warmup, k_ltf + 1), n):
            b = bias[i]
            if b == _NEUTRAL:
                continue
            if leg_id[i] == traded_leg:
                continue

            j = i - k_ltf                 # le swing H1 devient connu à la barre i
            if j < 0:
                continue

            H, L = leg_h[i], leg_l[i]
            span = H - L
            if not np.isfinite(span) or span <= 0:
                continue

            a = atr[i]
            if not np.isfinite(a) or a <= 0:
                continue

            entry = float(closes[i])

            if b == _BEAR and sh[j]:
                # Lower high confirmé : est-il dans la zone de retracement ?
                level = (float(highs[j]) - L) / span
                if not (rmin <= level <= rmax):
                    continue
                stop = float(highs[j]) + buf * a
                if stop <= entry:
                    continue
                risk = stop - entry
                target = self._target(tmode, entry, risk, L, span, short=True)
                if target >= entry:
                    continue
                side = Side.SHORT

            elif b == _BULL and sl[j]:
                level = (H - float(lows[j])) / span
                if not (rmin <= level <= rmax):
                    continue
                stop = float(lows[j]) - buf * a
                if stop >= entry:
                    continue
                risk = entry - stop
                target = self._target(tmode, entry, risk, H, span, short=False)
                if target <= entry:
                    continue
                side = Side.LONG

            else:
                continue

            out.append((i, Signal(
                timestamp=idx[i], symbol=symbol, side=side,
                entry=entry, stop=stop, target=target,
                reason=(f"{params['htf']} {'LL/LH' if side == Side.SHORT else 'HH/HL'} "
                        f"+ retrace {level:.2f} + swing H1 confirmé"),
                meta={"retr": round(level, 3), "leg_id": int(leg_id[i]),
                      "risk": risk},
            )))
            traded_leg = leg_id[i]

        return out

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Coupe la liste précalculée. Rien à l'indice >= end_idx ne peut
        influencer le résultat : chaque signal est daté de la barre où la
        décision a été prise, et ne dépend que de [0, i]."""
        return [s for (i, s) in data["signals"] if i < end_idx]

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : réutilise EXACTEMENT le même code que le
        chemin backtest, puis ne garde que la décision de la barre courante.

        Il n'y a pas deux implémentations à faire diverger — c'est le seul
        moyen sûr d'éviter le « ça marchait en backtest »."""
        bars = ctx.bars
        if len(bars) < self.manifest().warmup_bars + 10:
            return None

        self._symbol = ctx.symbol
        data = self.precompute(bars, self.params)
        last = len(bars) - 1
        for i, sig in data["signals"]:
            if i == last:
                return sig
        return None
