"""
AlexG AI Judge — stratégie s93_alexg_ai_judge (couche 1 : détecteur mécanique v2)

Source : https://www.youtube.com/@fxalexg__
Trader : fxalexg + juge IA

Détecteur mécanique de la spec publique 2025 de fxalexg (docs/sources/fxalexg/
SYNTHESE.md §1). RÉGLÉ POUR LE RAPPEL, PAS POUR LA PRÉCISION : il attrape les
candidats, le tri est le travail du juge IA (couche 2, voir judge/). C'est la
leçon de s01 : le paquet sans la sélection teste autre chose que le trader.

Portes MÉCANIQUES (rejet dur, ce sont ses règles non négociables) :
    1. Trend : 2 timeframes CONSÉCUTIFS en sync (W+D ou D+4H), structure sur
       CORPS de bougie, pivot = ≥2 bougies de retracement (fractal corps k=2).
    2. Prix revenu DANS une AOI valide (zone ≤ 60 pips, ≥ 3 touches en corps,
       sur W ou D, lookback 3 ans) — jamais d'entrée sur break.
    3. Déclencheur : shift de structure par BODY CLOSE sur le TF d'entrée (H1)
       — croisement du dernier pivot contraire. « Un shift minuscule compte
       quand même » : aucun seuil de taille.
    4. SL structurel derrière le dernier pivot H1 ; TP avant le prochain point
       de structure daily ; R:R ≥ 2 sinon rejet mécanique.
    5. Filtres temporels : entrées lundi→jeudi uniquement (pas de dimanche
       soir, pas de vendredi, dernière entrée jeudi soir).

CONFLUENCES OBJECTIVABLES (jamais des portes — consignées dans Signal.meta
["dossier"], l'entrée du juge) : TF sync (2 ou 3), qualité de l'AOI (largeur,
touches, W et/ou D, les deux), profondeur de retracement, netteté du break en
ATR, engulfing à la clôture, head & shoulders avec break+retest de neckline,
distance au niveau psychologique rond (00/50), position/distance à l'EMA
(période jamais publiée par la source — EMA 50 H1, choix documenté), R:R,
session (London/NY/Asie). Le COT est ajouté PAR LE PIPELINE d'extraction
(judge/), pas ici : la stratégie ne lit que des barres.

CAUSALITÉ (R1)
--------------
Même discipline que s01 : un pivot fractal (corps, k=2) n'est CONNU qu'à la
clôture de la barre j+2 de son timeframe ; un pivot HTF n'est utilisable qu'à
la clôture de cette barre HTF (label + durée de barre). Tous les états (biais,
jambes, zones AOI, niveaux daily) évoluent par ÉVÉNEMENTS datés de leur instant
de disponibilité, rejoués séquentiellement sur l'index H1. `precompute(df)` +
coupe à `end_idx` == `precompute(df[:end_idx])` — vérifié par
core/validation/causality.py.
"""
from __future__ import annotations

import bisect
from typing import Any, Optional

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Timeframe -> (règle resample pandas, durée d'une barre)
_HTF = {
    "W":  ("7D", pd.Timedelta(days=7)),   # ancré sur la 1re barre : semaine Sun->Sun
    "D":  ("1D", pd.Timedelta(days=1)),
    "H4": ("4h", pd.Timedelta(hours=4)),
}
_BULL, _NEUTRAL, _BEAR = 1, 0, -1
_K = 2   # pivot = >= 2 bougies de retracement (règle source, 05 @ 00:06:0)


# ─────────────────────────────────────────────────────────────────────────────
# Briques causales
# ─────────────────────────────────────────────────────────────────────────────

def _body_arrays(o: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Corps de bougie : « the wicks are just wicks » (06 @ 00:12:0)."""
    return np.maximum(o, c), np.minimum(o, c)


def _fractals(bhi: np.ndarray, blo: np.ndarray, k: int = _K):
    """Pivots sur CORPS. sh[j] : le corps haut de j domine k barres à gauche
    (strict) et k à droite (large). Vérité rétrospective — l'appelant décale de
    k barres pour obtenir l'instant de disponibilité."""
    n = len(bhi)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    if n < 2 * k + 1:
        return sh, sl
    wmax = sliding_window_view(bhi, k).max(axis=1)
    wmin = sliding_window_view(blo, k).min(axis=1)
    j = np.arange(k, n - k)
    sh[j] = (bhi[j] > wmax[j - k]) & (bhi[j] >= wmax[j + 1])
    sl[j] = (blo[j] < wmin[j - k]) & (blo[j] <= wmin[j + 1])
    return sh, sl


def _htf_events(df: pd.DataFrame, tf: str) -> list[tuple[pd.Timestamp, int, float, pd.Timestamp]]:
    """Pivots d'un timeframe rééchantillonné, datés de leur DISPONIBILITÉ.

    Retourne [(avail_time, kind ±1, prix_corps, bar_time)], triés. Un pivot en
    j n'est disponible qu'à la clôture de la barre HTF j+k : label + durée.
    """
    rule, dur = _HTF[tf]
    h = (df.resample(rule)
           .agg({"open": "first", "close": "last"})
           .dropna())
    if len(h) < 2 * _K + 2:
        return []
    bhi, blo = _body_arrays(h["open"].to_numpy(), h["close"].to_numpy())
    sh, sl = _fractals(bhi, blo)
    hidx = h.index
    ev = []
    for j in range(_K, len(h) - _K):
        if sh[j]:
            ev.append((hidx[j + _K] + dur, +1, float(bhi[j]), hidx[j]))
        if sl[j]:
            ev.append((hidx[j + _K] + dur, -1, float(blo[j]), hidx[j]))
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev


class _TFState:
    """Machine à états de structure d'un timeframe, rejouée par événements.

    Biais : HH+HL = bull, LL+LH = bear, sinon neutre — même définition que la
    source (suite de higher highs / higher lows sur corps)."""

    def __init__(self, events):
        self.events = events
        self.p = 0
        self.sh_prev = self.sh_last = self.sl_prev = self.sl_last = np.nan
        self.pivots: list[tuple[pd.Timestamp, int, float]] = []  # (bar_time, kind, price)
        self.changed = False

    def advance(self, t: pd.Timestamp) -> None:
        self.changed = False
        while self.p < len(self.events) and self.events[self.p][0] <= t:
            _, kind, price, bt = self.events[self.p]
            if kind > 0:
                self.sh_prev, self.sh_last = self.sh_last, price
            else:
                self.sl_prev, self.sl_last = self.sl_last, price
            self.pivots.append((bt, kind, price))
            self.changed = True
            self.p += 1

    @property
    def bias(self) -> int:
        if np.isnan(self.sh_prev) or np.isnan(self.sl_prev):
            return _NEUTRAL
        if self.sh_last > self.sh_prev and self.sl_last > self.sl_prev:
            return _BULL
        if self.sh_last < self.sh_prev and self.sl_last < self.sl_prev:
            return _BEAR
        return _NEUTRAL

    @property
    def leg(self) -> tuple[float, float]:
        return (self.sl_last, self.sh_last)   # (bas, haut) de la structure courante


def _cluster_zones(pivots: list[tuple[pd.Timestamp, int, float]],
                   now: pd.Timestamp, lookback_days: int,
                   width: float, touch_min: int) -> list[dict]:
    """AOI = grappe de pivots-corps dans le lookback, étendue ≤ `width`,
    ≥ `touch_min` touches. Chaque pivot est une touche en corps (c'est la
    définition la plus fidèle disponible sur OHLC : un pivot corps est un
    niveau touché puis rejeté)."""
    cutoff = now - pd.Timedelta(days=lookback_days)
    pts = sorted((p, t) for (t, _, p) in pivots if t >= cutoff)
    zones: list[dict] = []
    i = 0
    while i < len(pts):
        j = i
        while j + 1 < len(pts) and pts[j + 1][0] - pts[i][0] <= width:
            j += 1
        n = j - i + 1
        if n >= touch_min:
            grp = pts[i:j + 1]
            zones.append({
                "lo": grp[0][0], "hi": grp[-1][0], "n": n,
                "last_touch": max(t for _, t in grp),
            })
            i = j + 1
        else:
            i += 1
    return zones


def _atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().to_numpy()


def _hs_neckline_retest(pivots: list[tuple[int, int, float]],
                        closes: np.ndarray, blo: np.ndarray, bhi: np.ndarray,
                        i: int, atr_i: float, *, long: bool,
                        window: int = 150) -> bool:
    """Head & shoulders (inverse pour un long) avec BREAK + RETEST de neckline.

    pivots : [(j, kind, price)] H1 CONNUS à la barre i (délai k déjà appliqué).
    Motif : trois pivots du même côté [a, tête, b] dans `window` barres, tête
    extrême, neckline = moyenne des deux pivots opposés intercalés ; puis un
    body close au-delà de la neckline (break), puis un retour du corps à
    ≤ 0.3 ATR de la neckline (retest) — avant la barre i.
    """
    kind_side = -1 if long else +1     # épaules/tête = pivots bas pour un long
    side = [p for p in pivots if p[1] == kind_side and i - p[0] <= window]
    other = [p for p in pivots if p[1] == -kind_side and i - p[0] <= window]
    if len(side) < 3 or len(other) < 2:
        return False
    a, head, b = side[-3], side[-2], side[-1]
    if long:
        if not (head[2] < a[2] and head[2] < b[2]):
            return False
    else:
        if not (head[2] > a[2] and head[2] > b[2]):
            return False
    between = [p for p in other if a[0] < p[0] < b[0]]
    if not between:
        return False
    neck = float(np.mean([p[2] for p in between]))
    # break puis retest, entre l'épaule droite et la barre courante
    broke = retested = False
    for j in range(b[0] + 1, i + 1):
        if not broke:
            if (long and closes[j] > neck) or (not long and closes[j] < neck):
                broke = True
        else:
            if long and blo[j] <= neck + 0.3 * atr_i:
                retested = True
                break
            if not long and bhi[j] >= neck - 0.3 * atr_i:
                retested = True
                break
    return broke and retested


# ─────────────────────────────────────────────────────────────────────────────
# Stratégie
# ─────────────────────────────────────────────────────────────────────────────

class Strategy(StrategyModule):
    STRATEGY_ID = "s93_alexg_ai_judge"
    MAGIC_NUMBER = 130093

    ATR_PERIOD = 14

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="AlexG AI Judge",
            version="0.2.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s93_alexg_ai_judge",
            source="https://www.youtube.com/@fxalexg__",
            # Paires documentées de la source : GBPJPY/GBPCHF absentes du
            # catalogue et des données -> substituées par GBPUSD/EURJPY
            # (couverture GBP et JPY), écart documenté dans research/.
            symbols=["EURUSD", "USDJPY", "USDCHF", "AUDCAD", "GBPUSD", "EURJPY"],
            timeframe="H1",
            warmup_bars=2500,        # il faut ~15 semaines pour 4 pivots W corps
            param_grid={},           # PAS d'optimisation : l'étude porte sur le juge
            default_params={
                "pip": 0.0001,       # fixé par le runner selon l'instrument
                "aoi_width_pips": 60.0,
                "aoi_touch_min": 3,
                "aoi_lookback_days": 1095,   # 1-3 ans (05 @ 00:13:3) — borne haute
                "visit_window": 48,  # le prix doit avoir été DANS l'AOI < 48 h
                "rr_min": 2.0,
                "sl_buf_atr": 0.1,
                "tp_margin_atr": 0.1,
                "ema_period": 50,    # période JAMAIS publiée — choix documenté
                "min_gap_bars": 6,
            },
            status="RESEARCH",
            notes="Détecteur v2 fxalexg (rappel), dossier de confluences par "
                  "candidat dans Signal.meta['dossier']. Le tri = juge IA.",
        )

    # ── Précalcul ────────────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        idx = df.index
        o = df["open"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        bhi, blo = _body_arrays(o, c)
        atr = _atr(df, self.ATR_PERIOD)
        ema = df["close"].ewm(span=int(params["ema_period"]), adjust=False).mean().to_numpy()
        wd = idx.weekday.to_numpy()
        hod = idx.hour.to_numpy()

        states = {tf: _TFState(_htf_events(df, tf)) for tf in ("W", "D", "H4")}

        # Pivots H1 (corps, k=2) — connus à j+k
        sh1, sl1 = _fractals(bhi, blo)
        h1_events: list[tuple[int, int, float]] = []   # (known_at, kind, price) avec j implicite
        h1_ev_full: list[tuple[int, int, float, int]] = []
        for j in np.flatnonzero(sh1 | sl1):
            if sh1[j]:
                h1_ev_full.append((j + _K, +1, float(bhi[j]), int(j)))
            if sl1[j]:
                h1_ev_full.append((j + _K, -1, float(blo[j]), int(j)))
        h1_ev_full.sort(key=lambda e: e[0])

        funnel: dict[str, int] = {}
        ind: dict[str, np.ndarray] = {
            "bias_w": np.zeros(len(idx), dtype=np.int8),
            "bias_d": np.zeros(len(idx), dtype=np.int8),
            "bias_h4": np.zeros(len(idx), dtype=np.int8),
            "last_ph": np.full(len(idx), np.nan),
            "last_pl": np.full(len(idx), np.nan),
            "n_zones_w": np.zeros(len(idx), dtype=np.int16),
            "n_zones_d": np.zeros(len(idx), dtype=np.int16),
        }
        signals = self._scan(df, idx, o, c, bhi, blo, atr, ema, wd, hod,
                             states, h1_ev_full, params, funnel, ind)

        # R1 couche indicateur : precompute renvoie un DataFrame de colonnes
        # par barre, réellement comparé par core/validation/causality.py.
        out = pd.DataFrame(ind, index=idx)
        out["atr"] = atr
        out["ema"] = ema
        out.attrs["signals"] = signals
        out.attrs["funnel"] = funnel
        return out

    # ── Le scan séquentiel ───────────────────────────────────────────────────
    def _scan(self, df, idx, o, c, bhi, blo, atr, ema, wd, hod,
              states, h1_events, params,
              funnel: Optional[dict] = None,
              ind: Optional[dict] = None) -> list[tuple[int, Signal]]:
        if funnel is None:
            funnel = {}

        def tick(key: str) -> None:
            funnel[key] = funnel.get(key, 0) + 1
        pip = float(params["pip"])
        width = float(params["aoi_width_pips"]) * pip
        touch_min = int(params["aoi_touch_min"])
        lookback = int(params["aoi_lookback_days"])
        visit_win = int(params["visit_window"])
        rr_min = float(params["rr_min"])
        sl_buf = float(params["sl_buf_atr"])
        tp_margin = float(params["tp_margin_atr"])
        min_gap = int(params["min_gap_bars"])
        warmup = self.manifest().warmup_bars
        symbol = getattr(self, "_symbol", "UNKNOWN")

        n = len(idx)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)

        zones = {"W": [], "D": []}          # zones AOI courantes par TF
        d_highs: list[float] = []           # niveaux structure daily (triés)
        d_lows: list[float] = []
        h1_piv: list[tuple[int, int, float]] = []   # (j, kind, price) connus
        h1_p = 0
        last_ph: Optional[float] = None     # dernier pivot haut H1 connu
        last_pl: Optional[float] = None
        # dernière visite d'AOI par direction : (bar, zone_dict, tf)
        last_visit = {1: (-10**9, None, ""), -1: (-10**9, None, "")}
        last_sig = {1: -10**9, -1: -10**9}
        out: list[tuple[int, Signal]] = []

        for i in range(n):
            t = idx[i]

            # 1) événements HTF
            for tf, st in states.items():
                st.advance(t)
                if st.changed and tf in zones:
                    zones[tf] = _cluster_zones(st.pivots, t, lookback, width, touch_min)
                if st.changed and tf == "D":
                    cut = t - pd.Timedelta(days=lookback)
                    d_highs = sorted(p for (bt, k, p) in st.pivots if k > 0 and bt >= cut)
                    d_lows = sorted(p for (bt, k, p) in st.pivots if k < 0 and bt >= cut)

            # 2) pivots H1
            while h1_p < len(h1_events) and h1_events[h1_p][0] <= i:
                known, kind, price, j = h1_events[h1_p]
                h1_piv.append((j, kind, price))
                if kind > 0:
                    last_ph = price
                else:
                    last_pl = price
                h1_p += 1

            if ind is not None:
                ind["bias_w"][i] = states["W"].bias
                ind["bias_d"][i] = states["D"].bias
                ind["bias_h4"][i] = states["H4"].bias
                if last_ph is not None:
                    ind["last_ph"][i] = last_ph
                if last_pl is not None:
                    ind["last_pl"][i] = last_pl
                ind["n_zones_w"][i] = len(zones["W"])
                ind["n_zones_d"][i] = len(zones["D"])

            if i < warmup:
                continue
            tick('bars')
            a = atr[i]
            if not np.isfinite(a) or a <= 0:
                continue

            # 3) direction : 2 TF consécutifs en sync
            bw, bd, b4 = states["W"].bias, states["D"].bias, states["H4"].bias
            if bd != _NEUTRAL and bw == bd:
                direction = bd
                sync = "W+D+H4" if b4 == bd else "W+D"
            elif bd != _NEUTRAL and b4 == bd:
                direction = bd
                sync = "D+H4"
            else:
                # pas de sync -> une visite hors sync ne compte pas.
                continue
            tick('sync')

            # 4) visite d'AOI (corps de la barre DANS une zone valide, côté
            #    retracement, zone contenue dans la jambe de son TF)
            for tf in ("W", "D"):
                leg_lo, leg_hi = states[tf].leg
                if not (np.isfinite(leg_lo) and np.isfinite(leg_hi)) or leg_hi <= leg_lo:
                    continue
                tol = 0.1 * (leg_hi - leg_lo)
                for z in zones[tf]:
                    if not (z["lo"] >= leg_lo - tol and z["hi"] <= leg_hi + tol):
                        continue      # hors du dernier HH/HL
                    if blo[i] <= z["hi"] and bhi[i] >= z["lo"]:
                        mid = 0.5 * (z["lo"] + z["hi"])
                        if direction == _BULL and mid <= c[i] + 0.5 * a:
                            last_visit[1] = (i, dict(z), tf)
                        elif direction == _BEAR and mid >= c[i] - 0.5 * a:
                            last_visit[-1] = (i, dict(z), tf)

            vbar, vzone, vtf = last_visit[direction]
            if vzone is None or i - vbar > visit_win:
                continue
            tick('aoi_visit')

            # 5) filtre temporel : entrées lundi(0) -> jeudi(3) uniquement
            if wd[i] not in (0, 1, 2, 3):
                continue
            if i - last_sig[direction] < min_gap:
                continue
            tick('time_ok')

            long = direction == _BULL
            entry = float(c[i])

            # 6) shift de structure H1 par body close (croisement du dernier
            #    pivot contraire — première barre du cross uniquement)
            if long:
                if last_ph is None or not (c[i] > last_ph and c[i - 1] <= last_ph):
                    continue
                shift_lvl = last_ph
            else:
                if last_pl is None or not (c[i] < last_pl and c[i - 1] >= last_pl):
                    continue
                shift_lvl = last_pl
            tick('shift')

            # 7) SL structurel derrière le dernier pivot H1 de retracement
            # derrière le dernier pivot H1 (le pivot de retracement) ; la
            # bordure de zone n'est que le repli si aucun pivot n'est connu
            if long:
                anchor = last_pl if last_pl is not None else vzone["lo"]
                stop = anchor - sl_buf * a
                if stop >= entry:
                    continue
            else:
                anchor = last_ph if last_ph is not None else vzone["hi"]
                stop = anchor + sl_buf * a
                if stop <= entry:
                    continue
            risk = abs(entry - stop)
            tick('sl_ok')

            # 8) TP : avant le prochain point de structure daily
            # prochain point de structure daily au-delà de l'entrée ; si le
            # prix est déjà au-dessus de tout niveau récent (tendance en
            # extension), le point de structure pertinent est l'extrême de la
            # jambe daily courante (la continuation que la source vise).
            d_lo_leg, d_hi_leg = states["D"].leg
            if long:
                lv = [p for p in d_highs if p > entry + risk * 0.5]
                if np.isfinite(d_hi_leg) and d_hi_leg > entry + risk * 0.5:
                    lv.append(float(d_hi_leg))
                if not lv:
                    continue
                target = min(lv) - tp_margin * a
                if target <= entry:
                    continue
            else:
                lv = [p for p in d_lows if p < entry - risk * 0.5]
                if np.isfinite(d_lo_leg) and d_lo_leg < entry - risk * 0.5:
                    lv.append(float(d_lo_leg))
                if not lv:
                    continue
                target = max(lv) + tp_margin * a
                if target >= entry:
                    continue

            tick('tp_found')
            rr = abs(target - entry) / risk
            if rr < rr_min:
                continue
            tick('rr_ok')

            # 9) dossier de confluences objectivables
            leg_lo_d, leg_hi_d = states["D"].leg
            span_d = leg_hi_d - leg_lo_d if np.isfinite(leg_hi_d) and np.isfinite(leg_lo_d) else np.nan
            retrace = np.nan
            if np.isfinite(span_d) and span_d > 0:
                retrace = (leg_hi_d - entry) / span_d if long else (entry - leg_lo_d) / span_d

            # zone sur l'autre TF au même endroit ?
            other_tf = "D" if vtf == "W" else "W"
            both = any(z["lo"] <= entry <= z["hi"] or
                       (blo[i] <= z["hi"] and bhi[i] >= z["lo"])
                       for z in zones[other_tf])

            engulf = (c[i] > o[i] and c[i - 1] < o[i - 1]
                      and o[i] <= c[i - 1] and c[i] >= o[i - 1]) if long else \
                     (c[i] < o[i] and c[i - 1] > o[i - 1]
                      and o[i] >= c[i - 1] and c[i] <= o[i - 1])

            hs = _hs_neckline_retest(h1_piv, c, blo, bhi, i, a, long=long)

            grid50 = 50.0 * pip
            round_dist = float(min(entry % grid50, grid50 - entry % grid50) / pip)

            sess = ("london" if 9 <= hod[i] < 15 else
                    "newyork" if 15 <= hod[i] < 23 else "asia")

            dossier = {
                "side": "LONG" if long else "SHORT",
                "tf_sync": sync,
                "aoi_tf": vtf,
                "aoi_width_pips": round((vzone["hi"] - vzone["lo"]) / pip, 1),
                "aoi_touches": int(vzone["n"]),
                "aoi_dist_atr": round(abs(entry - 0.5 * (vzone["lo"] + vzone["hi"])) / a, 2),
                "aoi_both_tf": bool(both),
                "retrace_frac": round(float(retrace), 2) if np.isfinite(retrace) else None,
                "shift_break_atr": round(abs(entry - shift_lvl) / a, 2),
                "engulfing": bool(engulf),
                "hs_neckline_retest": bool(hs),
                "round_dist_pips": round(round_dist, 1),
                "ema_side_with_trade": bool((entry > ema[i]) == long),
                "ema_dist_atr": round(abs(entry - ema[i]) / a, 2),
                "rr": round(rr, 2),
                "sl_pips": round(risk / pip, 1),
                "tp_pips": round(abs(target - entry) / pip, 1),
                "atr_pips": round(a / pip, 1),
                "session": sess,
                "bars_since_aoi_visit": int(i - vbar),
            }

            out.append((i, Signal(
                timestamp=idx[i], symbol=symbol,
                side=Side.LONG if long else Side.SHORT,
                entry=entry, stop=float(stop), target=float(target),
                reason=f"v2 {sync} {'bull' if long else 'bear'} + AOI {vtf} "
                       f"({vzone['n']}t/{dossier['aoi_width_pips']}p) + shift H1, rr {rr:.1f}",
                meta={"dossier": dossier, "bar": int(i)},
            )))
            last_sig[direction] = i

        return out

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Coupe la liste précalculée — chaque signal est daté de la barre où
        la décision est prise et ne dépend que de [0, i]."""
        sigs = data.attrs["signals"] if isinstance(data, pd.DataFrame) else data["signals"]
        return [s for (i, s) in sigs if i < end_idx]

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5 par construction : réutilise exactement le chemin backtest et ne
        garde que la décision de la barre courante."""
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
