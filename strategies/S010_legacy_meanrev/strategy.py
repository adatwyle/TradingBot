"""
Legacy S1 — divergence MACD + S/R (retour à la moyenne H1) — s10_legacy_meanrev

Source : projet TBOT 2026, code historique
    BacktestEngine_prototype/.../grid_search_v12_multi_variant.py  (check_signal)
    BacktestEngine_prototype/.../indicators.py                     (indicateurs)

RÉ-IMPLÉMENTATION, PAS UN PORTAGE
----------------------------------
Le code historique n'est PAS importé. Il a été lu pour comprendre la logique,
puis réécrit contre le contrat `StrategyModule`. Motif : tous les résultats S1
publiés avant le 15.08.2026 sont contaminés par un lookahead de `fast_bt_multi`
(clôture résiduelle à `closes[-1]` au lieu de `closes[n-1]`). Réutiliser ce code
reviendrait à hériter du doute. Voir `research/ANALYSIS.md` §0.

LA LOGIQUE, EN UNE PHRASE
--------------------------
Sur H1, hors tendance forte (ADX bas), quand l'élan MACD cesse de confirmer le
prix (divergence, ou simple inflexion de l'histogramme) ET que le RSI est en
zone extrême ET que le prix touche un niveau S/R récent — on parie sur le retour
à la moyenne. SL et TP en multiples d'ATR, set & forget.

TROIS VARIANTES, PAS SIX
-------------------------
L'historique expose STRICT / WIDE_TOL / RSI40 / NO_SR / HI_cons / HI_aggr. À la
lecture de `check_signal`, il n'y a que TROIS branches de code ; les six noms
sont des jeux de paramètres. Compter six « stratégies » là où il y a trois
hypothèses gonfle le taux de faux positifs sans rien tester de plus. On porte
donc trois variantes et on met les seuils RSI dans la grille.

    DIV_SR    divergence MACD + RSI + proximité S/R   (= STRICT / WIDE_TOL / RSI40)
    DIV_NOSR  divergence MACD + RSI + direction ±DI   (= NO_SR)
    HIST_INF  inflexion histogramme + RSI + S/R       (= HI_cons / HI_aggr)

CAUSALITÉ (R1) — comment elle est garantie
-------------------------------------------
Le point sensible est la divergence : un creux d'histogramme n'existe qu'après
confirmation. Ici :

  * un creux/sommet fractal en `t` (fenêtre ±DIV_K) n'est réputé CONNU qu'à la
    barre `t + DIV_K` ; l'événement de divergence est daté de cet instant-là ;
  * les niveaux S/R à la barre `i` ne proviennent que de swings entièrement
    contenus dans `[i - SR_LOOKBACK, i - 1]` et confirmés avant `i` ;
  * aucun indicateur non causal (pas de `shift(-1)`, pas de `center=True`) ;
  * `generate_signals` ne fait que TRONQUER une liste de signaux déjà datés.

Conséquence : `precompute(df)` puis coupe à `end_idx` == `precompute(df[:end_idx])`.
C'est exactement ce que teste `core/validation/causality.py`.

R2 / R3 / R9 : aucune taille de position n'est calculée, `stop` est toujours
renseigné, et l'exécution (spread, SL/TP, cooldown, disjoncteur) appartient
entièrement à `core/backtest/engine.py`.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# ── Constantes fixées HORS grille ────────────────────────────────────────────
# Valeurs médianes de l'usage historique, arrêtées en Phase 1 AVANT tout
# résultat. Les faire varier reviendrait à agrandir la grille pour rattraper un
# résultat décevant — interdit.
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9   # signal = SMA (comportement MT5)
RSI_PERIOD = 14
ADX_PERIOD = 14
ATR_PERIOD = 14

SR_LOOKBACK = 50        # profondeur de recherche des niveaux S/R
SR_SWING = 5            # demi-fenêtre d'un swing S/R
SR_TOL = 0.006          # proximité relative au niveau (historique : 0.004-0.010)

DIV_K = 5               # demi-fenêtre d'un extremum d'histogramme
DIV_GAP_MIN = 5         # écart minimal entre deux extrema comparés
DIV_GAP_MAX = 50        # écart maximal
DIV_HOLD = 6            # nb de barres pendant lesquelles la divergence reste active
#                         (l'historique gardait ~7 barres via "recent <= lookback+2")

WARMUP = 300            # MACD 26 + ADX/RSI/ATR 14 + S/R 50 + divergence 60 : large marge


# ─────────────────────────────────────────────────────────────────────────────
# Indicateurs — tous causaux, tous vectorisés
# ─────────────────────────────────────────────────────────────────────────────

def _macd_hist(close: pd.Series) -> np.ndarray:
    """MACD façon MT5 : ligne = EMA12 - EMA26, signal = SMA(9) de la ligne.

    MT5 `iMACD` lisse le signal en SMA, pas en EMA (contrairement à TradingView).
    L'historique faisait ce choix explicitement ; on le conserve.
    """
    ef = close.ewm(span=MACD_FAST, adjust=False).mean()
    es = close.ewm(span=MACD_SLOW, adjust=False).mean()
    line = ef - es
    signal = line.rolling(MACD_SIGNAL).mean()
    return (line - signal).to_numpy()


def _rsi(close: pd.Series, period: int = RSI_PERIOD) -> np.ndarray:
    d = close.diff()
    gain = d.where(d > 0, 0.0)
    loss = (-d).where(d < 0, 0.0)
    ag = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).to_numpy()


def _atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().to_numpy()


def _adx(df: pd.DataFrame, period: int = ADX_PERIOD):
    """ADX / +DI / -DI selon l'algorithme MT5 `ADX.mq5`, PAS la variante Wilder.

    MT5 calcule un DI BRUT par barre (`100 * DM / TR`, instantané) puis le lisse
    en EMA classique (alpha = 2/(p+1)), les tampons étant amorcés à 0. Wilder,
    lui, lisse les DM avant de diviser. Les deux donnent des valeurs
    sensiblement différentes, et c'est la version MT5 qu'utilisait l'historique
    — donc c'est elle qui définit ce que `adx_max` veut dire ici.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    n = len(high)
    alpha = 2.0 / (period + 1.0)

    raw_p = np.zeros(n)
    raw_n = np.zeros(n)
    if n > 1:
        up = high[1:] - high[:-1]
        dn = low[:-1] - low[1:]
        up = np.where(up < 0.0, 0.0, up)
        dn = np.where(dn < 0.0, 0.0, dn)
        # Une seule direction l'emporte ; égalité -> les deux à zéro.
        p = np.where(up > dn, up, 0.0)
        m = np.where(dn > up, dn, 0.0)
        tr = np.maximum.reduce([
            np.abs(high[1:] - low[1:]),
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1]),
        ])
        nz = tr != 0.0
        raw_p[1:][nz] = 100.0 * p[nz] / tr[nz]
        raw_n[1:][nz] = 100.0 * m[nz] / tr[nz]

    # EMA amorcée à 0 : pandas `adjust=False` part de la 1re valeur, qui vaut 0
    # ici — équivalent exact à la récurrence de ADX.mq5 démarrant à i = 1.
    pdi = pd.Series(raw_p).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    ndi = pd.Series(raw_n).ewm(alpha=alpha, adjust=False).mean().to_numpy()

    s = pdi + ndi
    dx = np.where(s != 0.0, 100.0 * np.abs(pdi - ndi) / np.where(s == 0.0, 1.0, s), 0.0)
    adx = pd.Series(dx).ewm(alpha=alpha, adjust=False).mean().to_numpy()
    return adx, pdi, ndi


def _rolling_extreme(a: np.ndarray, k: int, mode: str) -> np.ndarray:
    """min (ou max) glissant CENTRÉ sur ±k. Renvoie NaN sur les bords.

    Utilisé UNIQUEMENT pour détecter des fractals. Un fractale en `t` calculé
    ainsi lit les barres jusqu'à `t + k` : il n'est donc utilisable qu'à partir
    de `t + k`. Tous les appelants respectent ce décalage — c'est le coeur de R1.
    """
    n = len(a)
    out = np.full(n, np.nan)
    w = 2 * k + 1
    if n < w:
        return out
    win = sliding_window_view(a, w)
    out[k:n - k] = win.min(axis=1) if mode == "min" else win.max(axis=1)
    return out


def _divergence_events(hist: np.ndarray, lows: np.ndarray, highs: np.ndarray,
                       n: int) -> tuple[np.ndarray, np.ndarray]:
    """Divergences MACD, datées de l'instant où elles deviennent CONNUES.

    Un creux d'histogramme en `t` est un fractale (minimum sur ±DIV_K) : il n'est
    confirmé qu'à `t + DIV_K`. On compare alors ce creux au creux confirmé
    PRÉCÉDENT :

        divergence haussière  <=>  le prix fait un plus-bas plus bas
                                   ET l'histogramme fait un plus-bas plus haut

    L'événement est daté de `t + DIV_K` et reste actif DIV_HOLD barres, ce qui
    reproduit la fenêtre d'activité d'environ 7 barres de l'implémentation
    historique. Voir `research/ANALYSIS.md` §4.1 pour la substitution assumée.
    """
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    if n < 2 * DIV_K + 2:
        return bull, bear

    hmin = _rolling_extreme(hist, DIV_K, "min")
    hmax = _rolling_extreme(hist, DIV_K, "max")
    lmin = _rolling_extreme(lows, DIV_K, "min")
    hhigh = _rolling_extreme(highs, DIV_K, "max")

    with np.errstate(invalid="ignore"):
        troughs = np.flatnonzero((hist <= hmin) & (hist < 0) & np.isfinite(hmin))
        peaks = np.flatnonzero((hist >= hmax) & (hist > 0) & np.isfinite(hmax))

    def emit(idxs, flags, price_ext, better_price, better_hist):
        for a, b in zip(idxs[:-1], idxs[1:]):
            gap = b - a
            if gap < DIV_GAP_MIN or gap > DIV_GAP_MAX:
                continue
            if not better_price(price_ext[b], price_ext[a]):
                continue
            if not better_hist(hist[b], hist[a]):
                continue
            known = b + DIV_K              # instant de confirmation du 2e extremum
            if known >= n:
                continue
            flags[known:min(n, known + DIV_HOLD + 1)] = True

    # Haussière : prix plus-bas plus BAS, histogramme plus-bas plus HAUT.
    emit(troughs, bull, lmin, lambda x, y: x < y, lambda x, y: x > y)
    # Baissière : prix plus-haut plus HAUT, histogramme plus-haut plus BAS.
    emit(peaks, bear, hhigh, lambda x, y: x > y, lambda x, y: x < y)
    return bull, bear


def _sr_distance(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, n: int):
    """Distance RELATIVE au support / à la résistance le plus proche.

    Reproduit la fenêtre de l'historique : à la barre `i`, les niveaux
    admissibles sont les swings (±SR_SWING) dont la fenêtre complète tient dans
    `[i - SR_LOOKBACK, i - 1]`, soit des swings d'indice
    `[i - SR_LOOKBACK + SR_SWING, i - SR_SWING - 1]`.

    Le clustering de l'historique (regroupement des niveaux à 0,1 %) est retiré :
    il déplace un niveau d'au plus 0,1 % du prix, contre une tolérance testée de
    0,4 % à 1,0 %, et jamais dans le sens qui compte (si le prix est proche d'un
    swing il est proche du barycentre de son groupe). Voir ANALYSIS §4.2.

    Retourne (rel_sup, rel_res) : distance / prix, NaN si aucun niveau.
    """
    sh_max = _rolling_extreme(highs, SR_SWING, "max")
    sl_min = _rolling_extreme(lows, SR_SWING, "min")
    with np.errstate(invalid="ignore"):
        is_res = (highs >= sh_max) & np.isfinite(sh_max)
        is_sup = (lows <= sl_min) & np.isfinite(sl_min)

    res_lvl = np.where(is_res, highs, np.nan)
    sup_lvl = np.where(is_sup, lows, np.nan)

    # Fenêtre glissante des niveaux visibles, décalée du délai de confirmation.
    span = SR_LOOKBACK - 2 * SR_SWING          # nb de swings candidats
    lag = SR_SWING + 1                          # le plus récent utilisable est i-lag
    rel_sup = np.full(n, np.nan)
    rel_res = np.full(n, np.nan)
    if n < SR_LOOKBACK + 1 or span < 1:
        return rel_sup, rel_res

    pad = np.full(span - 1, np.nan)
    for lvl, out in ((sup_lvl, rel_sup), (res_lvl, rel_res)):
        # win[i] = niveaux d'indices [i - span + 1, i]
        win = sliding_window_view(np.concatenate([pad, lvl]), span)
        start = lag + span - 1                 # 1re barre où la fenêtre est complète
        if start >= n:
            continue
        sub = win[:n - lag][start - lag:]       # aligné sur les barres [start, n)
        c = closes[start:n][:, None]
        with np.errstate(invalid="ignore"):
            d = np.abs(sub - c)
            allnan = np.all(~np.isfinite(d), axis=1)
            d[:, 0] = np.where(allnan, np.inf, d[:, 0])
            out[start:n] = np.nanmin(d, axis=1) / closes[start:n]
    rel_sup[~np.isfinite(rel_sup)] = np.nan
    rel_res[~np.isfinite(rel_res)] = np.nan
    return rel_sup, rel_res


# ─────────────────────────────────────────────────────────────────────────────
# Stratégie
# ─────────────────────────────────────────────────────────────────────────────

class Strategy(StrategyModule):
    STRATEGY_ID = "s10_legacy_meanrev"
    MAGIC_NUMBER = 130010

    # Cache des indicateurs. Aucun paramètre de la grille n'influence les
    # indicateurs (ce ne sont que des seuils de filtrage), donc les recalculer
    # pour chacune des 108 cellules serait du gaspillage pur. La clé inclut la
    # longueur et les bornes temporelles : un tableau tronqué a forcément une
    # clé différente, ce qui préserve la validité du test R1.
    _CACHE_MAX = 4

    def __init__(self, params: Optional[dict] = None):
        super().__init__(params)
        self._ind_cache: dict[tuple, dict] = {}
        self._symbol = "UNKNOWN"

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Legacy S1 — divergence MACD + S/R",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s10_legacy_meanrev",
            source="projet TBOT 2026, historique (grid_search_v12_multi_variant.py)",
            # Les 4 « survivants » du walk-forward contaminé (SP500, NIKKEI,
            # FTSE, AUDCHF) + 4 instruments qu'il avait écartés. Le panier est
            # choisi pour rendre la comparaison possible, pas pour flatter.
            symbols=["SP500", "NIKKEI", "FTSE", "AUDCHF",
                     "EURUSD", "EURCHF", "AUDUSD", "USDJPY"],
            timeframe="H1",
            warmup_bars=WARMUP,
            param_grid={
                "variant":  ["DIV_SR", "DIV_NOSR", "HIST_INF"],
                "rsi_band": [30, 35, 40],   # borne basse ; haute = 100 - basse
                "adx_max":  [25, 35, 50],
                "sl_atr":   [1.5, 2.5],
                "rr":       [1.0, 2.0],     # TP = rr * SL
            },                               # 3*3*3*2*2 = 108 configurations
            default_params={
                "variant": "DIV_SR",
                "rsi_band": 35,
                "adx_max": 35,
                "sl_atr": 2.0,
                "rr": 2.0,
            },
            # BACKTESTED = « mesuré », PAS « validé ». Verdict : PAS D'EDGE sur
            # 7 des 8 instruments, NON CONCLUSIF sur NIKKEI. Ne pas promouvoir
            # en PAPER — c'est une décision d'Adrian, pas la mienne (R10).
            status="BACKTESTED",
            notes=("Retour à la moyenne H1. 3 variantes = les 3 chemins de code "
                   "réels des 6 variantes historiques. Chiffres antérieurs au "
                   "15.08.2026 contaminés par lookahead — voir research/. "
                   "Mesuré : -0.0017 R/trade (spread réel), -0.0271 avec 0.5 pip "
                   "de slippage ; 19 STRICT contre ~43 attendues du hasard."),
        )

    # ── Indicateurs (mis en cache, indépendants des paramètres) ──────────────
    def _indicators(self, df: pd.DataFrame) -> dict:
        key = (len(df), df.index[0].value, df.index[-1].value)
        hit = self._ind_cache.get(key)
        if hit is not None:
            return hit

        n = len(df)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        hist = _macd_hist(df["close"])
        rsi = _rsi(df["close"])
        atr = _atr(df)
        adx, pdi, ndi = _adx(df)
        bull_div, bear_div = _divergence_events(hist, lows, highs, n)
        rel_sup, rel_res = _sr_distance(highs, lows, closes, n)

        # Inflexion de l'histogramme (variante HIST_INF), strictement causale :
        # h[i] > h[i-1] et h[i-1] <= h[i-2] et h[i] < 0.
        bull_inf = np.zeros(n, dtype=bool)
        bear_inf = np.zeros(n, dtype=bool)
        if n > 2:
            bull_inf[2:] = (hist[2:] > hist[1:-1]) & (hist[1:-1] <= hist[:-2]) & (hist[2:] < 0)
            bear_inf[2:] = (hist[2:] < hist[1:-1]) & (hist[1:-1] >= hist[:-2]) & (hist[2:] > 0)

        data = dict(index=df.index, highs=highs, lows=lows, closes=closes,
                    rsi=rsi, atr=atr, adx=adx, pdi=pdi, ndi=ndi,
                    bull_div=bull_div, bear_div=bear_div,
                    bull_inf=bull_inf, bear_inf=bear_inf,
                    rel_sup=rel_sup, rel_res=rel_res)

        if len(self._ind_cache) >= self._CACHE_MAX:
            self._ind_cache.pop(next(iter(self._ind_cache)))
        self._ind_cache[key] = data
        return data

    # ── Précalcul ────────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Produit la LISTE COMPLÈTE des signaux, chacun étiqueté par l'indice de
        la barre où la décision est prise.

        Tout le travail est fait ici parce que chaque décision ne dépend que du
        passé : `generate_signals` n'a plus qu'à couper la liste.
        """
        d = self._indicators(df)
        return {"index": d["index"], "signals": self._scan(d, params)}

    def _scan(self, d: dict, params: dict) -> list[tuple[int, Signal]]:
        variant = str(params["variant"])
        lo = float(params["rsi_band"])
        hi = 100.0 - lo
        adx_max = float(params["adx_max"])
        sl_m = float(params["sl_atr"])
        tp_m = sl_m * float(params["rr"])
        sym = self._symbol

        idx = d["index"]
        closes, rsi, atr, adx = d["closes"], d["rsi"], d["atr"], d["adx"]
        pdi, ndi = d["pdi"], d["ndi"]
        rel_sup, rel_res = d["rel_sup"], d["rel_res"]

        if variant == "HIST_INF":
            trig_up, trig_dn = d["bull_inf"], d["bear_inf"]
        else:
            trig_up, trig_dn = d["bull_div"], d["bear_div"]
        use_sr = variant != "DIV_NOSR"

        n = len(closes)
        out: list[tuple[int, Signal]] = []

        # Le déclencheur est rare (divergence) ou modérément fréquent
        # (inflexion) : on n'itère que sur les barres où il est armé. Aucune
        # barre écartée ici ne pourrait produire un signal — les deux branches
        # ci-dessous exigent `trig_up[i]` ou `trig_dn[i]`.
        candidates = np.flatnonzero(trig_up | trig_dn)
        for i in candidates[candidates >= WARMUP]:
            i = int(i)
            a = atr[i]
            if not np.isfinite(a) or a <= 0:
                continue
            if not np.isfinite(adx[i]) or adx[i] > adx_max:
                continue          # tendance trop forte : pas de retour à la moyenne
            r = rsi[i]
            if not np.isfinite(r):
                continue

            price = float(closes[i])

            if trig_up[i] and r < lo:
                # Confirmation de LIEU : au support, ou (variante NO_SR) la
                # pression vendeuse domine encore — on achète l'excès.
                ok = (np.isfinite(rel_sup[i]) and rel_sup[i] <= SR_TOL) if use_sr \
                    else (ndi[i] > pdi[i])
                if ok:
                    stop = price - sl_m * a
                    target = price + tp_m * a
                    out.append((i, Signal(
                        timestamp=idx[i], symbol=sym, side=Side.LONG,
                        entry=price, stop=stop, target=target,
                        reason=(f"{variant} LONG — RSI {r:.0f}<{lo:.0f}, "
                                f"ADX {adx[i]:.0f}<={adx_max:.0f}"),
                        meta={"rsi": round(float(r), 1),
                              "adx": round(float(adx[i]), 1),
                              "atr": float(a)},
                    )))
                    continue      # une seule décision par barre

            if trig_dn[i] and r > hi:
                ok = (np.isfinite(rel_res[i]) and rel_res[i] <= SR_TOL) if use_sr \
                    else (pdi[i] > ndi[i])
                if ok:
                    stop = price + sl_m * a
                    target = price - tp_m * a
                    out.append((i, Signal(
                        timestamp=idx[i], symbol=sym, side=Side.SHORT,
                        entry=price, stop=stop, target=target,
                        reason=(f"{variant} SHORT — RSI {r:.0f}>{hi:.0f}, "
                                f"ADX {adx[i]:.0f}<={adx_max:.0f}"),
                        meta={"rsi": round(float(r), 1),
                              "adx": round(float(adx[i]), 1),
                              "atr": float(a)},
                    )))
        return out

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Coupe la liste précalculée. Rien à l'indice >= end_idx ne peut
        influencer le résultat : chaque signal est daté de la barre où la
        décision a été prise, et ne dépend que de [0, i]."""
        return [s for (i, s) in data["signals"] if i < end_idx]

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : réutilise EXACTEMENT le même code que le chemin
        backtest, puis ne garde que la décision de la barre courante.

        Il n'existe pas deux implémentations pouvant diverger — c'est le seul
        moyen sûr d'éviter le « ça marchait en backtest »."""
        bars = ctx.bars
        if len(bars) < WARMUP + 10:
            return None
        self._symbol = ctx.symbol
        data = self.precompute(bars, self.params)
        last = len(bars) - 1
        for i, sig in data["signals"]:
            if i == last:
                return sig
        return None
