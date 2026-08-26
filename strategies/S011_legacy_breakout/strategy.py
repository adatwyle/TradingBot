"""
Legacy S2 — cassure Donchian + filtre de régime — stratégie s11_legacy_breakout

Source : projet TBOT 2026, code historique interne
        (`BacktestEngine_prototype/.../s2_breakout.py` et `s2_breakout_filtered.py`)
Trader : TBOT interne

RE-DÉRIVATION, PAS PORTAGE
---------------------------
Le code historique est lu comme une SPÉCIFICATION, jamais comme une preuve : le
moteur de cette époque valorisait les positions résiduelles à `closes[-1]`
(dernière barre du tableau COMPLET) et a contaminé des mois de walk-forward.
Aucun chiffre antérieur n'est repris. Voir `research/ANALYSIS.md` § 1.

LA RÈGLE, EN SIX POINTS
------------------------
À chaque barre clôturée, dans cet ordre :

  1. FILTRE DE RÉGIME — halte des nouvelles entrées si
         ER200 < er_min   OU   failed_rate200 > fr_max
     (ne ferme jamais une position ouverte ; voir plus bas)
  2. VOLATILITÉ        ATR(14) > atr_vol_ratio × SMA50(ATR)
  3. TENDANCE          ADX(14) > adx_min  ET  ADX(i) > ADX(i − adx_rising_lookback)
  4. DÉCLENCHEUR       close > max(high des N barres PRÉCÉDENTES)   -> LONG
                       close < min(low  des N barres PRÉCÉDENTES)   -> SHORT
  5. DIRECTION         +DI > −DI (long) / −DI > +DI (short)
  6. ANTI-EXTRÊME      RSI < rsi_long_max (long) / RSI > rsi_short_min (short)

  Stop  = entrée ∓ sl_m × ATR      Cible = entrée ± tp_m × ATR      Set & forget.

LES SEUILS DU FILTRE SONT DES PARAMÈTRES, PAS DES CONSTANTES
-------------------------------------------------------------
Les valeurs historiques (er_min = 0,11 ; fr_max = 0,50) ont été choisies par
INSPECTION VISUELLE des distributions gagnants/perdants, et un test antérieur
avait montré que DAX ne passait qu'au point exact. Elles sont donc exposées dans
`param_grid` avec leur voisinage, plus une valeur de DÉSACTIVATION :

    er_min = 0.00  ->  `ER200 < 0` est toujours faux   -> filtre ER inactif
    fr_max = 1.00  ->  `taux > 1`  est toujours faux    -> filtre FR inactif

La cellule (0.00, 1.00) est le TÉMOIN sans filtre. C'est elle qui répond à
« le signal de cassure a-t-il un edge par lui-même ? », séparément de
« le filtre ajoute-t-il quelque chose ? ».

CAUSALITÉ (R1) — le point fragile est `failed_rate`
----------------------------------------------------
`fail[j]` regarde délibérément `close[j+1 … j+3]` : on ne peut pas savoir qu'une
cassure a échoué avant qu'elle échoue. La causalité ne tient QU'AU décalage
d'agrégation : à la barre `i`, la fenêtre s'arrête à `j = i − horizon − 1 = i−4`,
dont l'évaluation n'a consommé que `close[… i−1]`.

    dépendance de fr200[i]  ⊆  [0, i−1]        -> causal
    dépendance de er200[i]  ⊆  [0, i]          -> causal

Ce décalage est reproduit à l'identique depuis l'historique. Le supprimer
introduirait une fuite parfaitement invisible dans les résultats.

SÉPARATION DES RESPONSABILITÉS (R2, R9)
----------------------------------------
Cette classe n'exécute rien : elle émet des `Signal`. Le moteur commun applique
le spread, le SL/TP, la position unique, le cooldown (2 barres) et le circuit
breaker (3 pertes -> 24 barres) — exactement les valeurs de l'historique, qui se
trouvent être les défauts de `core/backtest/engine.py`.

Le trailing / passage au point mort de l'historique (option non-défaut) N'EST PAS
reproduit : le moteur commun ne déplace pas de stop, et R9 interdit d'en écrire
un autre. Limite documentée dans `research/ANALYSIS.md` § 4 et § 8.1.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Horizon de la « cassure ratée » : revenue dans le canal en moins de 3 barres.
# Valeur historique, non paramétrable — c'est la définition du filtre, pas un
# réglage. La rendre libre gonflerait la grille sans tester d'hypothèse.
FAILED_HORIZON = 3
ER_LOOKBACK = 100        # ER de Kaufman à 100 barres
ER_SMOOTH = 200          # moyenné sur 200 barres
FR_WINDOW = 200          # taux de cassures ratées sur ~200 cassures
ATR_PERIOD = 14
RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_SMA_PERIOD = 50


# ─────────────────────────────────────────────────────────────────────────────
# Indicateurs — tous causaux, tous vectorisés
# ─────────────────────────────────────────────────────────────────────────────

def _true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    pc = np.empty_like(close)
    pc[0] = close[0]
    pc[1:] = close[:-1]
    return np.maximum(high - low, np.maximum(np.abs(high - pc), np.abs(low - pc)))


def _atr(high, low, close, period: int = ATR_PERIOD) -> np.ndarray:
    """SMA du True Range — reprise littérale de `indicators.add_atr`."""
    tr = _true_range(high, low, close)
    return pd.Series(tr).rolling(period).mean().to_numpy()


def _rsi(close: np.ndarray, period: int = RSI_PERIOD) -> np.ndarray:
    """RSI de Wilder — reprise littérale de `indicators.add_rsi`."""
    s = pd.Series(close)
    delta = s.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).to_numpy()


def _adx(high, low, close, period: int = ADX_PERIOD):
    """ADX / ±DI — variante MT5 `iADX` (PAS la variante Wilder `iADXW`).

    Reprise littérale de `indicators.add_adx` :
        1. DI brut par barre = 100 × DM / TR (instantané, non lissé)
        2. lissage EMA α = 2/(période+1), buffers amorcés à 0
        3. DX = 100 × |+DI − −DI| / (+DI + −DI)
        4. ADX = EMA(DX), même α

    La boucle Python de l'original est remplacée par des opérations vectorisées
    strictement équivalentes (la récurrence EMA est celle de
    `ewm(adjust=False)`), pour rendre les 128 configurations calculables.
    """
    n = len(high)
    alpha = 2.0 / (period + 1.0)

    up = np.zeros(n)
    dn = np.zeros(n)
    up[1:] = high[1:] - high[:-1]
    dn[1:] = low[:-1] - low[1:]

    pos_raw = np.where(up > 0.0, up, 0.0)
    neg_raw = np.where(dn > 0.0, dn, 0.0)
    # Une seule direction gagne ; égalité -> les deux à zéro.
    pos = np.where(pos_raw > neg_raw, pos_raw, 0.0)
    neg = np.where(neg_raw > pos_raw, neg_raw, 0.0)

    tr = _true_range(high, low, close)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw_pdi = np.where(tr != 0.0, 100.0 * pos / tr, 0.0)
        raw_ndi = np.where(tr != 0.0, 100.0 * neg / tr, 0.0)
    raw_pdi[0] = 0.0
    raw_ndi[0] = 0.0

    pdi = pd.Series(raw_pdi).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    ndi = pd.Series(raw_ndi).ewm(alpha=alpha, adjust=False).mean().to_numpy()

    di_sum = pdi + ndi
    with np.errstate(divide="ignore", invalid="ignore"):
        dx = np.where(di_sum != 0.0, 100.0 * np.abs(pdi - ndi) / di_sum, 0.0)
    adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    return adx, pdi, ndi


def _efficiency_ratio(close: np.ndarray) -> np.ndarray:
    """ER de Kaufman à 100 barres, moyenné sur 200 barres.

    ER100[i] = |close[i] − close[i−100]| / Σ|Δclose| sur la même fenêtre.
    1 = trajectoire rectiligne, ~0 = aller-retour stérile.

    Dépendance ⊆ [0, i]. Causal.
    """
    n = len(close)
    er = np.full(n, np.nan)
    if n <= ER_LOOKBACK:
        return er
    cs = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(close)))])
    net = np.abs(close[ER_LOOKBACK:] - close[:-ER_LOOKBACK])
    gross = cs[ER_LOOKBACK:] - cs[:n - ER_LOOKBACK]
    with np.errstate(divide="ignore", invalid="ignore"):
        er[ER_LOOKBACK:] = np.where(gross > 0.0, net / gross, 0.0)
    return (pd.Series(er)
            .rolling(ER_SMOOTH, min_periods=ER_LOOKBACK)
            .mean().to_numpy())


def _failed_breakout_rate(close: np.ndarray, dh_prev: np.ndarray,
                          dl_prev: np.ndarray) -> np.ndarray:
    """Proportion des ~200 dernières cassures Donchian revenues dans le canal
    en moins de `FAILED_HORIZON` barres.

    CAUSALITÉ — lire avant de modifier.
    `fail[j]` consulte `close[j+1 … j+3]`, donc regarde le futur DE j. C'est
    inévitable : une cassure ne peut pas être déclarée ratée avant de l'être.
    Ce qui rend l'indicateur causal, c'est uniquement l'agrégation décalée :

        à la barre i, la fenêtre s'arrête à  j = i − FAILED_HORIZON − 1 = i − 4
        et  fail[i−4]  n'a consommé que  close[… i−1].

    Retirer ce décalage produirait une fuite indétectable à l'œil.
    """
    n = len(close)
    fr = np.full(n, np.nan)
    m = n - FAILED_HORIZON
    if m <= 0:
        return fr

    c = close[:m]
    dh = dh_prev[:m]
    dl = dl_prev[:m]
    fwd = [close[k:k + m] for k in range(1, FAILED_HORIZON + 1)]

    up_brk = ~np.isnan(dh) & (c > dh)
    dn_brk = ~up_brk & ~np.isnan(dl) & (c < dl)      # `elif` de l'historique

    back_up = np.zeros(m, dtype=bool)
    back_dn = np.zeros(m, dtype=bool)
    for f in fwd:
        back_up |= (f <= dh)
        back_dn |= (f >= dl)

    brk = np.zeros(n, dtype=np.int64)
    fail = np.zeros(n, dtype=np.int64)
    brk[:m] = (up_brk | dn_brk).astype(np.int64)
    fail[:m] = ((up_brk & back_up) | (dn_brk & back_dn)).astype(np.int64)

    brk_cs = np.concatenate([[0], np.cumsum(brk)])
    fail_cs = np.concatenate([[0], np.cumsum(fail)])

    first = FR_WINDOW + 10          # 210 — borne historique, conservée
    if n <= first:
        return fr
    i = np.arange(first, n)
    end = i - FAILED_HORIZON - 1
    start = np.maximum(0, end - FR_WINDOW)
    b = brk_cs[end + 1] - brk_cs[start]
    f = fail_cs[end + 1] - fail_cs[start]
    with np.errstate(divide="ignore", invalid="ignore"):
        fr[first:] = np.where(b >= 5, f / np.maximum(b, 1), np.nan)
    return fr


# ─────────────────────────────────────────────────────────────────────────────
# Stratégie
# ─────────────────────────────────────────────────────────────────────────────

class Strategy(StrategyModule):
    STRATEGY_ID = "s11_legacy_breakout"
    MAGIC_NUMBER = 130011

    # Le walk-forward appelle `precompute` une fois par cellule de grille (128).
    # ADX/ATR/RSI/ER ne dépendent d'AUCUN paramètre de la grille, et le canal
    # Donchian ne dépend que de `donchian`. On mémorise ces deux étages, sinon
    # 90 % du temps de calcul est du travail refait à l'identique.
    _MAX_CACHE = 8

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._base: dict[tuple, Any] = {}
        self._chan: dict[tuple, Any] = {}

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Legacy S2 — cassure Donchian + filtre de régime",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s11_legacy_breakout",
            source="projet TBOT 2026, historique (s2_breakout.py / s2_breakout_filtered.py)",
            # S2 visait « indices et forex tendanciels ». DAX est retenu
            # explicitement : c'est l'instrument où le test de sensibilité
            # antérieur signalait un pic isolé sur (0,11 ; 0,50).
            symbols=["DAX", "NASDAQ", "SP500", "FTSE", "NIKKEI",
                     "XAUUSD", "EURJPY", "USDJPY"],
            timeframe="H1",
            # ER100 lissé sur 200 -> 300 ; taux de cassures ratées -> 210.
            warmup_bars=400,
            param_grid={
                # ── LE FILTRE DE RÉGIME EST DANS LA GRILLE ──────────────────
                # 0.00 / 1.00 = filtre DÉSACTIVÉ (témoin, teste le signal seul).
                # Les autres valeurs forment le voisinage 3×3 du point
                # historique (0,11 ; 0,50), choisi à l'œil -> à contrôler.
                "er_min":   [0.00, 0.09, 0.11, 0.13],
                "fr_max":   [1.00, 0.45, 0.50, 0.55],
                # ── Signal ──────────────────────────────────────────────────
                "donchian": [20, 40],
                "adx_min":  [20, 25],
                "tp_m":     [3.0, 4.0],
            },                                  # 4 × 4 × 2 × 2 × 2 = 128
            default_params={
                "er_min": 0.11,                 # valeur historique
                "fr_max": 0.50,                 # valeur historique
                "donchian": 20,
                "adx_min": 25,
                "tp_m": 4.0,
                # Fixés aux valeurs historiques, volontairement hors grille :
                # les faire varier gonflerait le nombre de faux positifs sans
                # tester d'hypothèse supplémentaire.
                "sl_m": 1.5,
                "atr_vol_ratio": 0.8,
                "adx_rising_lookback": 5,
                "rsi_long_max": 75.0,
                "rsi_short_min": 25.0,
            },
            status="RESEARCH",
            notes=("Cassure Donchian + ADX croissant + croisement DI + filtre ATR, "
                   "avec halte de régime ER/cassures-ratées. Seuils du filtre "
                   "exposés en grille (0.00/1.00 = désactivé)."),
        )

    # ── Caches ───────────────────────────────────────────────────────────────
    @staticmethod
    def _data_key(df: pd.DataFrame) -> tuple:
        """Identité d'un jeu de barres. Doit distinguer `df` de `df[:T]` — c'est
        exactement ce que compare l'invariant R1."""
        return (len(df),
                int(df.index[0].value),
                int(df.index[-1].value),
                float(df["close"].iloc[-1]))

    @staticmethod
    def _put(cache: dict, key, value):
        if len(cache) >= Strategy._MAX_CACHE:
            cache.pop(next(iter(cache)))
        cache[key] = value
        return value

    def _base_indicators(self, df: pd.DataFrame, dkey: tuple):
        """Indépendants de la grille : ATR, SMA(ATR), RSI, ADX/±DI, ER."""
        if dkey in self._base:
            return self._base[dkey]
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)

        atr = _atr(high, low, close)
        atr_sma = pd.Series(atr).rolling(ATR_SMA_PERIOD).mean().to_numpy()
        rsi = _rsi(close)
        adx, pdi, ndi = _adx(high, low, close)
        er200 = _efficiency_ratio(close)
        return self._put(self._base, dkey,
                         (high, low, close, atr, atr_sma, rsi, adx, pdi, ndi, er200))

    def _channel(self, df: pd.DataFrame, dkey: tuple, period: int):
        """Canal de Donchian décalé d'une barre + taux de cassures ratées.

        Le décalage `_prev` est essentiel : comparer le close à un extrême qui
        INCLUT la barre courante rendrait la condition presque tautologique.
        """
        key = (dkey, period)
        if key in self._chan:
            return self._chan[key]
        high = df["high"]
        low = df["low"]
        dh = high.rolling(period, min_periods=period).max().shift(1).to_numpy()
        dl = low.rolling(period, min_periods=period).min().shift(1).to_numpy()
        fr200 = _failed_breakout_rate(df["close"].to_numpy(dtype=float), dh, dl)
        return self._put(self._chan, key, (dh, dl, fr200))

    # ── Précalcul ────────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Produit les indicateurs ET la liste complète des signaux, étiquetés
        par l'indice de la barre où la décision est prise.

        Chaque décision ne dépend que de `[0, i]` (et de `[0, i−1]` pour le
        taux de cassures ratées) : `generate_signals` n'a donc plus qu'à couper
        la liste, ce qui rend l'invariant R1 vrai par construction — et
        vérifiable, ce qui n'est pas la même chose.

        VALEUR DE RETOUR : un `DataFrame`, pas un dict opaque. C'est délibéré.
        `core/validation/causality.py` a une seconde couche qui compare les
        INDICATEURS entre passe complète et passe tronquée — elle attrape les
        fuites trop petites pour faire basculer un signal sur CE jeu de données,
        mais qui en feraient basculer sur un autre. Cette couche ne s'applique
        QUE si `precompute` renvoie un DataFrame ; un objet opaque obtient un
        laissez-passer. Vu que la causalité de `failed_rate` tient à un simple
        décalage d'agrégation, je préfère être vérifié qu'exempté.

        La liste de signaux voyage dans `.attrs`, hors des colonnes comparées.
        """
        dkey = self._data_key(df)
        (high, low, close, atr, atr_sma, rsi,
         adx, pdi, ndi, er200) = self._base_indicators(df, dkey)
        dh, dl, fr200 = self._channel(df, dkey, int(params["donchian"]))

        n = len(df)
        idx = df.index
        warmup = self.manifest().warmup_bars
        lb = int(params["adx_rising_lookback"])
        er_min = float(params["er_min"])
        fr_max = float(params["fr_max"])
        adx_min = float(params["adx_min"])
        vol_ratio = float(params["atr_vol_ratio"])
        sl_m = float(params["sl_m"])
        tp_m = float(params["tp_m"])
        rsi_hi = float(params["rsi_long_max"])
        rsi_lo = float(params["rsi_short_min"])

        def _pack(sig_list, cols):
            out = pd.DataFrame(cols, index=idx)
            out.attrs["signals"] = sig_list
            return out

        if n <= warmup + lb + 1:
            return _pack([], {"atr": atr, "adx": adx, "er200": er200,
                              "fr200": fr200, "dh_prev": dh, "dl_prev": dl})

        adx_back = np.full(n, np.nan)
        adx_back[lb:] = adx[:-lb]

        # ── Filtre de régime : halte si le marché ne va nulle part OU si les
        #    cassures récentes ont échoué. NaN = pas d'information -> autorisé
        #    (comportement de l'historique, conservé tel quel).
        halt_er = ~np.isnan(er200) & (er200 < er_min)
        halt_fr = ~np.isnan(fr200) & (fr200 > fr_max)
        regime_ok = ~(halt_er | halt_fr)

        finite = (np.isfinite(atr) & (atr > 0)
                  & np.isfinite(atr_sma) & (atr_sma > 0)
                  & np.isfinite(dh) & np.isfinite(dl)
                  & np.isfinite(adx) & np.isfinite(adx_back))

        with np.errstate(invalid="ignore"):
            vol_ok = atr > atr_sma * vol_ratio
            trend_ok = (adx > adx_min) & (adx > adx_back)
            up_break = close > dh
            dn_break = ~up_break & (close < dl)      # `elif` de l'historique
            long_ok = up_break & (pdi > ndi) & (rsi < rsi_hi)
            short_ok = dn_break & (ndi > pdi) & (rsi > rsi_lo)

        gate = finite & regime_ok & vol_ok & trend_ok
        gate[:max(warmup, lb + 1)] = False

        longs = np.flatnonzero(gate & long_ok)
        shorts = np.flatnonzero(gate & short_ok)

        symbol = getattr(self, "_symbol", "UNKNOWN")
        out: list[tuple[int, Signal]] = []
        # Décisions matérialisées en colonnes numériques : la couche indicateur
        # de R1 compare aussi celles-ci, donc la DÉCISION elle-même est
        # contrôlée barre par barre, et pas seulement la liste finale.
        dec_side = np.zeros(n)
        dec_stop = np.full(n, np.nan)
        dec_target = np.full(n, np.nan)
        for i, is_long in sorted([(int(i), True) for i in longs]
                                 + [(int(i), False) for i in shorts]):
            a = float(atr[i])
            entry = float(close[i])
            if is_long:
                stop, target = entry - sl_m * a, entry + tp_m * a
                side = Side.LONG
                tag = f"cassure haute Donchian{int(params['donchian'])}"
            else:
                stop, target = entry + sl_m * a, entry - tp_m * a
                side = Side.SHORT
                tag = f"cassure basse Donchian{int(params['donchian'])}"
            if stop == entry:
                continue                    # ATR nul : rien à risquer, rien à faire
            out.append((i, Signal(
                timestamp=idx[i], symbol=symbol, side=side,
                entry=entry, stop=stop, target=target,
                reason=(f"{tag} + ADX {adx[i]:.1f} croissant + DI confirmé "
                        f"+ ATR {atr[i] / atr_sma[i]:.2f}× sa SMA50"),
                meta={"adx": round(float(adx[i]), 2),
                      "er200": (None if np.isnan(er200[i]) else round(float(er200[i]), 4)),
                      "fr200": (None if np.isnan(fr200[i]) else round(float(fr200[i]), 4)),
                      "risk": abs(entry - stop)},
            )))
            dec_side[i] = 1.0 if is_long else -1.0
            dec_stop[i] = stop
            dec_target[i] = target

        return _pack(out, {
            # indicateurs
            "atr": atr, "atr_sma": atr_sma, "rsi": rsi,
            "adx": adx, "pdi": pdi, "ndi": ndi,
            "er200": er200, "fr200": fr200,
            "dh_prev": dh, "dl_prev": dl,
            # décisions
            "dec_side": dec_side, "dec_stop": dec_stop, "dec_target": dec_target,
        })

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Coupe la liste précalculée à `end_idx`.

        Rien d'indice ≥ end_idx ne peut influencer la sortie : chaque signal est
        daté de la barre où la décision a été prise, et cette décision ne
        dépend que du passé. C'est ce que vérifie R1 — la garantie n'est pas
        dans ce commentaire, elle est dans `backtests/causality.txt`.
        """
        return [s for (i, s) in data.attrs["signals"] if i < end_idx]

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : le chemin live appelle LITTÉRALEMENT le code du
        chemin backtest, puis ne retient que la décision de la barre courante.

        Il n'existe pas deux implémentations pouvant diverger — c'est le seul
        moyen sûr d'éviter le « ça marchait en backtest ». Ce n'est pas une
        preuve (`core/validation/conformance.py` n'existe pas dans le dépôt),
        c'est une garantie structurelle.
        """
        bars = ctx.bars
        if len(bars) < self.manifest().warmup_bars + 10:
            return None
        self._symbol = ctx.symbol
        data = self.precompute(bars, self.params)
        last = len(bars) - 1
        for i, sig in data.attrs["signals"]:
            if i == last:
                return sig
        return None
