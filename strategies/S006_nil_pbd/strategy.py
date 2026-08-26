"""
PBD Impulse-Range (Patrick Nil) — `s06_nil_pbd`

Source  : https://www.youtube.com/watch?v=2ZmIn274eds
Trader  : Patrick Nil (Robbins World Cup, 5 années consécutives)
Analyse : research/ANALYSIS.md — lire §4 et §5 AVANT d'interpréter un chiffre


CE QUE DIT LA SOURCE, LITTÉRALEMENT
------------------------------------
    « you have a big impulse up and then you have a range and that's what I am
      looking [for] »                                                    (5:41)
    « No, I trade AFTER the impulse. (…) or I trade the range. If the range is
      good you can always play ping pong in the range till it goes out »  (6:35)
    « normally the profit target is under the impulse — most time it goes back
      to the beginning »                                                (18:05)
    « sometimes I do it over the zone or over the top or in the middle, or I
      look where the volume was in the last candles »                   (18:05)
    « I have the market profile volume based from the weekly and there you can
      see on the value area highs and lows — they are so important »     (9:39)
    « for the trade I take the 15 minutes chart »                       (10:33)

DEUX MODES, TESTÉS SÉPARÉMENT — ils ne sont PAS mélangés dans une même grille
    mode="fade"   (A) vendre le haut du range, acheter le bas — le « ping pong »
    mode="break"  (B) jouer la sortie du range

Ce sont deux hypothèses économiques opposées (le range tient / le range cède).
Les fondre dans une grille commune reviendrait à laisser l'optimiseur choisir
son camp cellule par cellule, ce qui produit un faux positif garanti.


LE MODÈLE, ÉTAT PAR ÉTAT (tout est dans `precompute`, donc inspecté par R1)
---------------------------------------------------------------------------
1. IMPULSION — sur une fenêtre glissante de `imp_bars` barres M15 :
       |close[i] - close[i-W]|  >=  imp_atr × ATR[i-W]        (amplitude)
       |net| / (plus_haut - plus_bas de la fenêtre) >= imp_eff (directionnalité)
   Le second test écarte les fenêtres qui parcourent la distance en zigzag :
   une impulsion est un déplacement, pas une agitation.

       origine   = extrémité opposée de la fenêtre  -> la CIBLE de la source
       extrême   = extrémité atteinte
       hauteur   = extrême - origine

2. RANGE — les barres qui suivent l'impulsion. Ses bornes à la barre i sont le
   plus haut / plus bas des barres [début, i-1] — STRICTEMENT antérieures à i.
   C'est ce qui évite l'auto-signal : sans cette exclusion, toute nouvelle
   extrémité déclencherait mécaniquement un signal de fade contre elle-même.

   Le range meurt si sa largeur dépasse `range_frac` × hauteur d'impulsion
   (ce n'est plus une consolidation), s'il dure plus de `range_life` barres,
   ou si une clôture sort de ses bornes (cassure).

   Il devient tradable après `range_min_bars` barres : avant, il n'y a pas
   encore de range, juste deux ou trois bougies.

3. PROFIL DE VOLUME HEBDOMADAIRE — POC + value area 70 %, calculé sur la
   SEMAINE PRÉCÉDENTE COMPLÈTE et reporté sur la semaine en cours. Filtre
   optionnel `va_filter` : ne trader une borne de range que si elle coïncide
   (à `va_tol` × ATR) avec VAH, VAL ou POC.

   AVERTISSEMENT — ce n'est PAS son profil de volume. MT5 Swissquote ne publie
   aucun volume réel (`real_volume = 0`, voir core/data/source.py). Le profil
   est bâti sur le `tick_volume`, qui compte les changements de cotation, pas
   les contrats. Aux moments de faible activité les deux corrèlent mal. La
   grille contient `va_filter` ∈ {0, 1} précisément pour MESURER cet écart au
   lieu de le supposer négligeable.


CAUSALITÉ (R1) — les trois points sensibles, tous traités
----------------------------------------------------------
1. `precompute` renvoie un **DataFrame**, jamais un dict. C'est délibéré :
   `core/validation/causality.py::_compare_precompute` ne compare les
   indicateurs que si l'objet est un DataFrame ; un dict passe à travers la
   couche indicateur sans être vu (c'est arrivé à s91). Le profil de volume
   glissant est exactement le genre de calcul où une fuite se cacherait, donc
   il DOIT être exposé colonne par colonne au gardien.

2. Le profil hebdomadaire n'utilise que des semaines RÉVOLUES. Les barres de la
   semaine w lisent le profil de w-1. Une troncature en milieu de semaine w
   laisse w-1 intacte : les valeurs sur [0, T) sont identiques que le
   DataFrame soit complet ou coupé.

3. Les bornes du range à la barre i excluent la barre i (point 2 ci-dessus).
   Aucun `rolling(center=True)`, aucun `shift(-1)`, aucune normalisation sur
   l'échantillon entier.


CE QUI N'EST PAS REPRODUIT — assumé, pas masqué
------------------------------------------------
* Il est **totalement discrétionnaire** (« you must feel the market a little
  bit », 4:24). Le modèle codé est donc structurellement plus pauvre.
* Footprint / order flow pour affiner l'entrée : donnée absente. Il déclare
  lui-même ne pas s'en servir systématiquement, ce qui rend le test défendable
  — c'est une amputation, pas une équivalence.
* Sortie en temps : il tient « four hours to three days ». Le harnais commun
  n'expose pas `max_hold_bars` au walk-forward ; les positions courent donc
  jusqu'au stop, à la cible, ou à la fin de tranche. Mesuré séparément dans
  `backtests/run_analysis.py`.
* Éviter les news majeures (23:28) : non modélisé, faute de calendrier.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)

# Colonnes produites par `precompute`. Toutes numériques et toutes exposées au
# gardien de causalité — c'est le but du DataFrame.
_COLS = (
    "close", "high", "low", "atr",
    "vah", "val", "poc",
    "rng_hi", "rng_lo", "rng_age",
    "imp_dir", "imp_origin", "imp_extreme", "imp_height",
    "brk",
)


def _atr(df: pd.DataFrame, n: int) -> pd.Series:
    """ATR de Wilder, strictement causal."""
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _week_profile(h: np.ndarray, l: np.ndarray, v: np.ndarray,
                  n_bins: int, va_pct: float) -> tuple[float, float, float]:
    """POC + value area d'une semaine, en volume-par-prix.

    Chaque barre répartit son volume UNIFORMÉMENT sur les paliers de prix
    qu'elle traverse. C'est la construction standard d'un profil de volume à
    partir de barres OHLC : sans tick data, on ne sait pas où le volume s'est
    réellement concentré dans la barre, et l'hypothèse uniforme est la seule
    qui n'invente rien.

    Value area = plus petit intervalle CONTIGU autour du POC contenant
    `va_pct` du volume total, étendu du côté le plus chargé à chaque pas.
    C'est la définition Market Profile classique (Steidlmayer).
    """
    lo, hi = float(np.min(l)), float(np.max(h))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.nan, np.nan, np.nan

    edges = np.linspace(lo, hi, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    hist = np.zeros(n_bins, dtype=float)

    # Indices de paliers couverts par chaque barre.
    i0 = np.clip(np.searchsorted(edges, l, side="right") - 1, 0, n_bins - 1)
    i1 = np.clip(np.searchsorted(edges, h, side="right") - 1, 0, n_bins - 1)
    for a, b, vol in zip(i0, i1, v):
        if b < a:
            a, b = b, a
        hist[a:b + 1] += vol / (b - a + 1)

    total = hist.sum()
    if total <= 0:
        return np.nan, np.nan, np.nan

    p = int(np.argmax(hist))
    acc = hist[p]
    lo_i = hi_i = p
    target = va_pct * total
    while acc < target and (lo_i > 0 or hi_i < n_bins - 1):
        down = hist[lo_i - 1] if lo_i > 0 else -1.0
        up = hist[hi_i + 1] if hi_i < n_bins - 1 else -1.0
        if up >= down:
            hi_i += 1
            acc += hist[hi_i]
        else:
            lo_i -= 1
            acc += hist[lo_i]

    return float(centers[p]), float(edges[hi_i + 1]), float(edges[lo_i])


def _weekly_value_areas(df: pd.DataFrame, n_bins: int, va_pct: float
                        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """POC/VAH/VAL de la semaine PRÉCÉDENTE, alignés sur chaque barre.

    Causalité : les barres de la semaine w reçoivent le profil de w-1, qui est
    entièrement révolue. Une troncature du DataFrame en milieu de semaine w ne
    peut donc pas modifier une seule valeur sur [0, T).
    """
    n = len(df)
    poc = np.full(n, np.nan)
    vah = np.full(n, np.nan)
    val = np.full(n, np.nan)
    if n == 0:
        return poc, vah, val

    iso = df.index.isocalendar()
    wk = (np.asarray(iso["year"]) * 100 + np.asarray(iso["week"])).astype(np.int64)

    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    v = (df["tick_volume"].to_numpy(dtype=float)
         if "tick_volume" in df.columns else np.ones(n))

    # Frontières des semaines, dans l'ordre chronologique.
    change = np.flatnonzero(np.diff(wk) != 0) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [n]))

    prev: tuple[float, float, float] | None = None
    for s, e in zip(starts, ends):
        if prev is not None:
            poc[s:e], vah[s:e], val[s:e] = prev
        prev = _week_profile(h[s:e], l[s:e], v[s:e], n_bins, va_pct)

    return poc, vah, val


class Strategy(StrategyModule):
    STRATEGY_ID = "s06_nil_pbd"
    MAGIC_NUMBER = 130006

    # ── Déclaration ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="PBD Impulse-Range (Patrick Nil)",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s06_nil_pbd",
            source="https://www.youtube.com/watch?v=2ZmIn274eds",
            symbols=["DAX", "WTIUSD"],      # « I'm an oil trader », chart DAX
            timeframe="M15",                # « for the trade I take the 15 minutes chart »
            warmup_bars=600,                # ATR + fenêtre d'impulsion + 1 semaine M15
            # ── GRILLE — mode FADE, la lecture première de la source ────────
            # 32 cellules -> ~1,6 réussite STRICT attendue par pur hasard.
            # `imp_eff`, `range_min_bars`, `range_life`, `range_frac` sont FIXES :
            # les mettre dans la grille multiplierait les faux positifs sans
            # tester une affirmation de la source (il ne les chiffre jamais).
            # La grille du mode BREAK est déclarée dans manifest.yaml et passée
            # explicitement par backtests/run_wf.py — voir l'en-tête du module.
            param_grid={
                "stop_mode": ["edge025", "edge05", "edge10", "extreme"],
                "target_mode": ["pingpong", "impulse_start"],
                "imp_atr": [1.5, 2.5],
                "va_filter": [0, 1],
            },
            default_params={
                # ── mode ──────────────────────────────────────────────────
                "mode": "fade",          # "fade" (A) | "break" (B)
                # ── impulsion ─────────────────────────────────────────────
                "imp_bars": 12,          # 3 h de M15 : une « impulsion » de séance
                "imp_atr": 2.0,          # amplitude minimale, en ATR
                "imp_eff": 0.60,         # directionnalité : déplacement / amplitude
                # ── range ─────────────────────────────────────────────────
                "range_min_bars": 12,    # 3 h avant qu'un range existe
                "range_life": 192,       # 2 jours de bougies M15
                "range_frac": 0.60,      # largeur max, en fraction de l'impulsion
                # ── sorties ───────────────────────────────────────────────
                "stop_mode": "edge05",
                "target_mode": "pingpong",
                "stop_atr": 1.5,         # utilisé par stop_mode="atr"
                "tgt_mult": 1.0,         # mode break : cible = mult × hauteur range
                # ── profil de volume ──────────────────────────────────────
                "va_filter": 0,          # 0 = sans filtre, 1 = coïncidence VA exigée
                "va_tol": 0.5,           # tolérance de coïncidence, en ATR
                "va_bins": 60,
                "va_pct": 0.70,          # value area 70 % — standard Market Profile
                # ── divers ────────────────────────────────────────────────
                "atr_len": 14,
                "_symbol": "",           # renseigné par le harnais ; cosmétique
            },
            status="RESEARCH",
            notes=("Deux modes exclusifs (fade / break) testés séparément. "
                   "Le profil de volume est bâti sur tick_volume faute de volume "
                   "réel : ce n'est pas la même grandeur que celle qu'utilise la "
                   "source. Voir research/ANALYSIS.md §4."),
        )

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        """Impulsions, ranges et profil hebdomadaire — un DataFrame causal.

        Renvoie DÉLIBÉRÉMENT un DataFrame : c'est la seule forme que la couche
        indicateur de R1 sait inspecter. Voir l'en-tête du module.
        """
        n = len(df)
        W = int(params["imp_bars"])
        imp_atr = float(params["imp_atr"])
        imp_eff = float(params["imp_eff"])
        rmin = int(params["range_min_bars"])
        rlife = int(params["range_life"])
        rfrac = float(params["range_frac"])

        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        atr = _atr(df, int(params["atr_len"])).to_numpy(dtype=float)

        # ── Détection d'impulsion, vectorisée et causale ──────────────────
        # rolling(W) n'utilise que [i-W+1, i] ; shift(W) n'utilise que le passé.
        roll_hi = df["high"].rolling(W).max().to_numpy(dtype=float)
        roll_lo = df["low"].rolling(W).min().to_numpy(dtype=float)
        net = close - np.concatenate((np.full(W, np.nan), close[:-W])) if n > W \
            else np.full(n, np.nan)
        atr_ref = np.concatenate((np.full(W, np.nan), atr[:-W])) if n > W \
            else np.full(n, np.nan)
        span = roll_hi - roll_lo

        with np.errstate(invalid="ignore"):
            is_imp = (np.abs(net) >= imp_atr * atr_ref) & (span > 0) \
                & (np.abs(net) / np.where(span > 0, span, np.nan) >= imp_eff)
        is_imp = np.nan_to_num(is_imp, nan=False).astype(bool)

        # ── Profil de volume hebdomadaire (semaine précédente) ────────────
        poc, vah, val = _weekly_value_areas(df, int(params["va_bins"]),
                                            float(params["va_pct"]))

        # ── Automate impulsion -> range, un seul passage ──────────────────
        rng_hi = np.full(n, np.nan)
        rng_lo = np.full(n, np.nan)
        rng_age = np.full(n, np.nan)
        c_dir = np.full(n, np.nan)
        c_org = np.full(n, np.nan)
        c_ext = np.full(n, np.nan)
        c_hgt = np.full(n, np.nan)
        brk = np.zeros(n, dtype=float)

        active = False
        form_start = 0
        rh = rl = np.nan
        d = org = ext = hgt = np.nan

        for i in range(n):
            if active:
                age = i - form_start          # barres RÉVOLUES du range avant i
                if age >= 1:
                    if (rh - rl) > rfrac * hgt or age > rlife:
                        active = False
                if active and age >= rmin:
                    rng_hi[i] = rh
                    rng_lo[i] = rl
                    rng_age[i] = age
                    c_dir[i] = d
                    c_org[i] = org
                    c_ext[i] = ext
                    c_hgt[i] = hgt
                    if close[i] > rh:
                        brk[i] = 1.0
                    elif close[i] < rl:
                        brk[i] = -1.0
                if active:
                    # La barre i n'entre dans les bornes qu'APRÈS avoir été
                    # évaluée : c'est ce qui interdit l'auto-signal.
                    rh = high[i] if not np.isfinite(rh) else max(rh, high[i])
                    rl = low[i] if not np.isfinite(rl) else min(rl, low[i])
                    if brk[i] != 0.0:
                        active = False        # la cassure clôt le range

            if not active and is_imp[i]:
                up = net[i] > 0
                d = 1.0 if up else -1.0
                ext = roll_hi[i] if up else roll_lo[i]
                org = roll_lo[i] if up else roll_hi[i]
                hgt = abs(ext - org)
                if hgt > 0:
                    active = True
                    form_start = i + 1
                    rh = rl = np.nan

        return pd.DataFrame(
            {
                "close": close, "high": high, "low": low, "atr": atr,
                "vah": vah, "val": val, "poc": poc,
                "rng_hi": rng_hi, "rng_lo": rng_lo, "rng_age": rng_age,
                "imp_dir": c_dir, "imp_origin": c_org,
                "imp_extreme": c_ext, "imp_height": c_hgt,
                "brk": brk,
            },
            index=df.index,
        )

    # ── Signaux ──────────────────────────────────────────────────────────────
    def generate_signals(self, data: pd.DataFrame, params: dict,
                         end_idx: int) -> list[Signal]:
        """Signaux sur [0, end_idx). Rien au-delà ne peut influencer la sortie :
        la boucle s'arrête à end_idx et toutes les colonnes sont causales."""
        mode = str(params["mode"])
        n = min(int(end_idx), len(data))
        if n <= 0:
            return []

        idx = data.index
        close = data["close"].to_numpy()
        high = data["high"].to_numpy()
        low = data["low"].to_numpy()
        atr = data["atr"].to_numpy()
        rhi = data["rng_hi"].to_numpy()
        rlo = data["rng_lo"].to_numpy()
        idir = data["imp_dir"].to_numpy()
        iorg = data["imp_origin"].to_numpy()
        iext = data["imp_extreme"].to_numpy()
        brk = data["brk"].to_numpy()
        vah = data["vah"].to_numpy()
        vlo = data["val"].to_numpy()
        poc = data["poc"].to_numpy()

        sym = str(params.get("_symbol", "")) or "?"
        va_on = bool(int(params["va_filter"]))
        va_tol = float(params["va_tol"])
        stop_mode = str(params["stop_mode"])
        tgt_mode = str(params["target_mode"])
        stop_atr = float(params["stop_atr"])
        tgt_mult = float(params["tgt_mult"])

        out: list[Signal] = []

        # Seules les barres portant un range actif peuvent produire un signal
        # (~12-18 % de l'historique). Filtrer en amont évite de balayer 72 000
        # barres huit fois par cellule de grille ; le résultat est identique.
        cand = np.flatnonzero(np.isfinite(rhi[:n]) & np.isfinite(rlo[:n]))

        for i in cand:
            hi, lo = rhi[i], rlo[i]
            if hi <= lo:
                continue
            a = atr[i]
            if not np.isfinite(a) or a <= 0:
                continue

            h_rng = hi - lo
            c = close[i]

            if mode == "fade":
                # Rejet d'une borne : la barre la touche et referme à l'intérieur.
                if high[i] >= hi and c < hi:
                    side, edge = Side.SHORT, hi
                elif low[i] <= lo and c > lo:
                    side, edge = Side.LONG, lo
                else:
                    continue
                if va_on and not self._near_va(edge, vah[i], vlo[i], poc[i], va_tol * a):
                    continue

                if side == Side.SHORT:
                    stop = self._fade_stop(stop_mode, True, hi, h_rng, iext[i],
                                           idir[i], c, stop_atr * a)
                    tgt = self._fade_target(tgt_mode, True, lo, idir[i], iorg[i])
                else:
                    stop = self._fade_stop(stop_mode, False, lo, h_rng, iext[i],
                                           idir[i], c, stop_atr * a)
                    tgt = self._fade_target(tgt_mode, False, hi, idir[i], iorg[i])
                why = (f"fade {'haut' if side == Side.SHORT else 'bas'} de range "
                       f"post-impulsion ({stop_mode}/{tgt_mode}"
                       f"{', VA' if va_on else ''})")

            elif mode == "break":
                if brk[i] > 0:
                    side, edge = Side.LONG, hi
                elif brk[i] < 0:
                    side, edge = Side.SHORT, lo
                else:
                    continue
                if va_on and not self._near_va(edge, vah[i], vlo[i], poc[i], va_tol * a):
                    continue

                mid = 0.5 * (hi + lo)
                if side == Side.LONG:
                    stop = {"mid": mid, "opp": lo}.get(stop_mode, c - stop_atr * a)
                    tgt = c + tgt_mult * h_rng
                else:
                    stop = {"mid": mid, "opp": hi}.get(stop_mode, c + stop_atr * a)
                    tgt = c - tgt_mult * h_rng
                why = (f"cassure de range post-impulsion "
                       f"({stop_mode}/x{tgt_mult:g}{', VA' if va_on else ''})")
            else:
                raise ValueError(f"mode inconnu : {mode!r} (attendu fade|break)")

            # Le contrat Signal refuse un stop du mauvais côté ; une géométrie
            # dégénérée (cassure qui referme au-delà du stop) est écartée, pas
            # rattrapée par un ajustement qui inventerait un niveau.
            if not np.isfinite(stop) or not np.isfinite(tgt):
                continue
            if side == Side.LONG and not (stop < c < tgt):
                continue
            if side == Side.SHORT and not (tgt < c < stop):
                continue

            out.append(Signal(
                timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                symbol=sym, side=side, entry=float(c),
                stop=float(stop), target=float(tgt),
                reason=why, confidence=1.0,
                meta={"mode": mode, "rng_hi": float(hi), "rng_lo": float(lo),
                      "imp_dir": float(idir[i]) if np.isfinite(idir[i]) else None},
            ))

        return out

    # ── Aides de niveaux ─────────────────────────────────────────────────────
    @staticmethod
    def _near_va(level: float, vah: float, val: float, poc: float,
                 tol: float) -> bool:
        """Coïncidence avec un niveau du profil hebdomadaire.

        « if the impulse and the range is on the same level as the market
        profile, it's even better » (12:37).
        """
        for x in (vah, val, poc):
            if np.isfinite(x) and abs(level - x) <= tol:
                return True
        return False

    @staticmethod
    def _fade_stop(mode: str, short: bool, edge: float, h_rng: float,
                   imp_ext: float, imp_dir: float, entry: float,
                   atr_dist: float) -> float:
        """Les variantes qu'il énumère (18:05), traitées en PARAMÈTRE.

        « sometimes I do it over the zone or over the top or in the middle, or
        I look where the volume was in the last candles. »

        edge025/05/10  « over the zone » — au-delà de la borne, de 25/50/100 %
                       de la hauteur du range
        extreme        « over the top » — au-delà de l'extrême de l'impulsion,
                       quand celui-ci est effectivement plus loin que la borne
        atr            distance de volatilité, substitut assumé de « where the
                       volume was in the last candles »
        """
        buf = {"edge025": 0.25, "edge05": 0.50, "edge10": 1.00}.get(mode)
        if buf is not None:
            return edge + buf * h_rng if short else edge - buf * h_rng
        if mode == "extreme":
            if short and np.isfinite(imp_ext) and imp_dir > 0 and imp_ext > edge:
                return imp_ext + 0.10 * h_rng
            if (not short) and np.isfinite(imp_ext) and imp_dir < 0 and imp_ext < edge:
                return imp_ext - 0.10 * h_rng
            # L'extrême est du mauvais côté : repli sur la borne large,
            # jamais sur un niveau plus serré qui flatterait le R:R.
            return edge + h_rng if short else edge - h_rng
        return entry + atr_dist if short else entry - atr_dist

    @staticmethod
    def _fade_target(mode: str, short: bool, opposite_edge: float,
                     imp_dir: float, imp_origin: float) -> float:
        """« most time it goes back to the beginning » (18:05).

        pingpong        borne opposée du range — le « ping pong » littéral
        impulse_start   origine de l'impulsion, mais SEULEMENT pour la jambe
                        qui va contre l'impulsion. Sur la jambe qui va dans son
                        sens, l'origine est derrière l'entrée : la cible n'a
                        aucun sens et on retombe sur la borne opposée.
        """
        if mode == "impulse_start" and np.isfinite(imp_origin):
            if (short and imp_dir > 0) or ((not short) and imp_dir < 0):
                return imp_origin
        return opposite_edge

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5/R6 par construction : appelle littéralement le chemin backtest et
        ne retient que la décision de la barre courante. Il n'existe pas deux
        implémentations susceptibles de diverger."""
        p = dict(self.params)
        p["_symbol"] = ctx.symbol
        data = self.precompute(ctx.bars, p)
        n = len(ctx.bars)
        sigs = self.generate_signals(data, p, n)
        if not sigs:
            return None
        last = sigs[-1]
        if pd.Timestamp(last.timestamp) != pd.Timestamp(ctx.bars.index[n - 1]):
            return None
        return last
