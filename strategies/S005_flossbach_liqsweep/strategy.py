"""
Liquidation Sweep — `s05_flossbach_liqsweep`

Source  : https://www.youtube.com/watch?v=BewBId1gbqQ  (IQ Capital)
Trader  : Tim Flossbach
Analyse : research/ANALYSIS.md — lire le §4 AVANT d'interpréter le moindre chiffre.


CE QUE FAIT CETTE STRATÉGIE
---------------------------
Reproduction de la séquence qu'il décrit, dans son ordre :

    1. amas de liquidité = >= `min_cluster` extrêmes de swing NON BALAYÉS dont
       les prix tiennent dans une bande de `band_atr` x ATR ;
    2. BALAYAGE : le prix traverse l'amas (low < niveau pour un amas bas) ;
    3. on N'ENTRE PAS sur le balayage — c'est l'erreur qu'il dit avoir corrigée
       (« the biggest problem I did in my past years was to enter way too
       fast ») ;
    4. structure de retournement : un sommet intermédiaire se forme après le
       balayage, PUIS un creux plus haut que l'extrême du balayage ;
    5. ENTRÉE à la cassure nette de ce sommet (close > sommet + 0,1 x ATR) ;
    6. STOP sous l'extrême du balayage OU sous le creux plus haut (les deux
       formulations sont dans le transcript — les deux sont en grille) ;
    7. CIBLE = amas opposé. Si R:R < 2 -> pas de trade (règle dure, répétée
       trois fois dans l'entretien).

Symétrique en short. Les deux sens sont autorisés : « you should always be open
for both sides ».


LE SUBSTITUT DE LIQUIDITÉ — la limite principale, écrite ici pour ne pas la rater
--------------------------------------------------------------------------------
Sa détection repose sur X-Ray / X-Ray Pro, qui agrègent les carnets d'ordres
d'exchanges crypto. Cette donnée n'existe pas chez nous (`real_volume = 0`, pas
de carnet). Le proxy est dérivé de SA description, pas inventé :

    « you will see the top of the last structure here, and just randomly the
      liquidation is directly in these zones »          (17:00)
    « if you see that in one specific zone there's not one liquidity but there
      is a lot a lot a lot of combined liquidity »      (25:44, réponse à
                                                         « comment faire sans
                                                          l'indicateur ? »)

-> amas = plusieurs extrêmes de structure non balayés, serrés en prix.

Ce que le proxy PERD : la magnitude en dollars, la liquidité hors extrêmes de
swing, et surtout l'hypothèse que les stops d'un CFD forex Swissquote se
concentrent aux mêmes endroits que les liquidations d'exchanges crypto. Un
échec ne réfute donc pas sa méthode — il réfute NOTRE PROXY de sa méthode.


PARAMÈTRE `require_sweep` — le contrôle de F3
---------------------------------------------
`require_sweep=False` déclenche exactement le même moteur de retournement
(sommet intermédiaire + creux plus haut + cassure nette + cible sur amas +
R:R >= 2) mais SANS exiger de balayage préalable. C'est le groupe de contrôle
de la condition de falsification F3 (ANALYSIS.md §7) : si le contrôle fait
aussi bien, l'ingrédient « liquidation sweep » n'apporte rien et la méthode se
réduit à un breakout de structure. Ce paramètre n'est PAS dans la grille de
recherche — c'est un instrument de mesure, pas un réglage.


CAUSALITÉ (R1) — trois points sensibles, tous traités
-----------------------------------------------------
1. `precompute` renvoie un **DataFrame**, pas un dict. C'est délibéré : le
   gardien `core/validation/causality.py::_compare_precompute` retourne
   silencieusement sur un objet opaque, et une stratégie qui renvoie un dict
   ÉCHAPPE au contrôle de la couche indicateur (piège rencontré par s91). Ici
   R1 inspecte réellement atr, ema_htf, volratio, et surtout les colonnes de
   décision sig_side / sig_entry / sig_stop / sig_target.

2. Un pivot fractal d'ordre `piv` centré en j n'est CONFIRMÉ qu'en j + piv. La
   boucle ne l'insère dans les structures qu'à cet instant : à la barre i on ne
   connaît que les pivots d'indice <= i - piv. Aucun pivot « du futur » n'est
   visible.

3. Toute la machine à états (amas, balayage, structure, entrée, cible) tient
   dans UNE boucle avant qui n'accède jamais à un indice > i. `generate_signals`
   ne fait que relire les colonnes déjà calculées et s'arrête à `end_idx`.
   `precompute(df[:T])` produit donc exactement les mêmes valeurs sur [0, T)
   que `precompute(df)`.
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from core.contracts.strategy import (
    MarketContext, Side, Signal, StrategyManifest, StrategyModule,
)


# ─────────────────────────────────────────────────────────────────────────────
# Indicateurs — tous strictement causaux
# ─────────────────────────────────────────────────────────────────────────────

def _atr(df: pd.DataFrame, n: int) -> np.ndarray:
    """ATR de Wilder. La valeur en i n'utilise que [0, i]."""
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy(dtype=float)


def _ema(s: pd.Series, n: int) -> np.ndarray:
    return s.ewm(span=n, adjust=False, min_periods=n).mean().to_numpy(dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# Amas de liquidité
# ─────────────────────────────────────────────────────────────────────────────

def _cluster_below(levels: list[float], ref: float, band: float,
                   min_n: int) -> Optional[tuple[float, int]]:
    """Amas d'extrêmes NON BALAYÉS situé sous `ref`, le plus proche de `ref`.

    Renvoie (niveau, effectif) où `niveau` = le prix le PLUS BAS de l'amas :
    c'est le point à partir duquel toute la liquidité de la zone est consommée,
    donc le seuil de balayage. Renvoie None s'il n'existe aucun groupe d'au
    moins `min_n` extrêmes tenant dans `band`.
    """
    xs = sorted(x for x in levels if x < ref)
    if len(xs) < min_n:
        return None
    best = None
    # Fenêtre glissante : le plus haut groupe (donc le plus proche de ref) gagne.
    for a in range(len(xs)):
        b = a
        while b + 1 < len(xs) and xs[b + 1] - xs[a] <= band:
            b += 1
        if b - a + 1 >= min_n:
            best = (xs[a], b - a + 1)      # xs[a] = borne basse du groupe
    return best


def _cluster_above(levels: list[float], ref: float, band: float,
                   min_n: int) -> Optional[tuple[float, int]]:
    """Idem au-dessus de `ref`. Le niveau renvoyé est le prix le PLUS HAUT de
    l'amas le plus proche de `ref`."""
    xs = sorted((x for x in levels if x > ref), reverse=True)
    if len(xs) < min_n:
        return None
    best = None
    for a in range(len(xs)):
        b = a
        while b + 1 < len(xs) and xs[a] - xs[b + 1] <= band:
            b += 1
        if b - a + 1 >= min_n:
            best = (xs[a], b - a + 1)
    return best


def _target_below(levels: list[float], ref: float, band: float, min_n: int,
                  stop_dist: float, min_rr: float, mode: str) -> Optional[float]:
    """Cible d'un SHORT : amas non balayé sous `ref`.

    mode="nearest"  -> l'amas le plus proche (lecture littérale : « the target
                       point was obviously the top of short liquidation »).
                       Si son R:R est insuffisant, PAS DE TRADE — c'est sa
                       règle (« if the reward risk is small, will you not take
                       the trade? — No, never ever »).
    mode="first_rr" -> le premier amas, en descendant, qui atteint min_rr.
                       Lecture plus favorable : il vise « a very big range » et
                       prend des profits partiels aux amas intermédiaires.
    """
    xs = sorted((x for x in levels if x < ref), reverse=True)
    groups: list[float] = []
    for a in range(len(xs)):
        b = a
        while b + 1 < len(xs) and xs[a] - xs[b + 1] <= band:
            b += 1
        if b - a + 1 >= min_n:
            groups.append(xs[a])          # borne haute = première touchée
    if not groups:
        return None
    if mode == "nearest":
        return groups[0]
    for g in groups:
        if stop_dist > 0 and (ref - g) / stop_dist >= min_rr:
            return g
    return None


def _target_above(levels: list[float], ref: float, band: float, min_n: int,
                  stop_dist: float, min_rr: float, mode: str) -> Optional[float]:
    """Cible d'un LONG. Symétrique de `_target_below`."""
    xs = sorted(x for x in levels if x > ref)
    groups: list[float] = []
    for a in range(len(xs)):
        b = a
        while b + 1 < len(xs) and xs[b + 1] - xs[a] <= band:
            b += 1
        if b - a + 1 >= min_n:
            groups.append(xs[a])
    if not groups:
        return None
    if mode == "nearest":
        return groups[0]
    for g in groups:
        if stop_dist > 0 and (g - ref) / stop_dist >= min_rr:
            return g
    return None


class Strategy(StrategyModule):
    STRATEGY_ID = "s05_flossbach_liqsweep"
    MAGIC_NUMBER = 130005

    # ── Déclaration ──────────────────────────────────────────────────────────
    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Tim Flossbach - Liquidation Sweep",
            version="1.0.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s05_flossbach_liqsweep",
            source="https://www.youtube.com/watch?v=BewBId1gbqQ",
            # 4 familles. Il affirme l'universalité (« everything I show here is
            # possible in every market »). Crypto impossible : BTCUSD absent du
            # catalogue Swissquote — or toute sa démonstration est sur Bitcoin.
            symbols=["EURUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD",
                     "XAUUSD", "XAGUSD", "SP500", "NASDAQ", "DAX", "WTIUSD"],
            timeframe="H4",          # « my most favorite time frame to enter big positions »
            warmup_bars=260,
            param_grid={
                # 64 cellules -> ~3,2 réussites STRICT attendues par PUR HASARD
                # et par instrument. Chiffre à garder sous les yeux.
                "band_atr":    [0.5, 1.0],     # largeur de la bande d'agglomération
                "min_cluster": [2, 3],         # « a lot a lot of combined liquidity »
                "stop_ref":    ["sweep", "higherlow"],   # les deux formulations du transcript
                "htf_mode":    ["off", "with"],          # « always respect the higher time frame »
                "chop_max":    [99.0, 1.5],    # « if the liquidity is shaking too much »
                "target_mode": ["nearest", "first_rr"],
            },
            # DÉFAUT = la lecture littérale de l'exemple qu'il DÉROULE (23:07 à
            # 31:08), pas la lecture littérale de ses maximes générales. Les
            # deux divergent, et c'est documenté :
            #   stop_ref="higherlow"  « I placed my stop loss below this low
            #                           here », après le creux plus haut (31:08)
            #   htf_mode="off"        dans cet exemple il prend un LONG « in a
            #                           consolidation after a longer downtrend »
            #                           (23:07) : sa propre entrée est refusée
            #                           par un filtre EMA200 directionnel strict
            #   target_mode="first_rr" « I want to figure out a very big range »
            #                           (31:08) — il vise un amas lointain, pas
            #                           le premier venu
            default_params={
                "band_atr": 1.0,
                "min_cluster": 2,
                "stop_ref": "higherlow",
                "htf_mode": "off",
                "chop_max": 99.0,
                "target_mode": "first_rr",
                # ── HORS GRILLE : ce sont SES règles, pas des variables ──────
                "min_rr": 2.0,        # « 95% of my trades are minimum 2:1, never below »
                "piv": 3,             # ordre du pivot fractal
                "brk_atr": 0.1,       # « I need a very clear breakout »
                # La structure de retournement exige 4 pivots successifs, donc
                # ~4 x (2 x piv + 1) = 28 barres au minimum. 48 laisse la
                # structure se former sans la tronquer arbitrairement.
                # Sensibilité 24 / 96 mesurée dans research/ : conclusion
                # inchangée.
                "setup_bars": 48,     # péremption d'un setup armé
                "max_age": 300,       # âge max d'un extrême encore « en mémoire »
                "reach_atr": 6.0,     # distance max de recherche d'un amas
                "atr_len": 14,
                "htf_ema": 200,       # « below the 200 day average, obviously downtrend »
                "stop_buf_atr": 0.1,
                # ── INSTRUMENTS DE MESURE, pas des réglages (voir en-tête) ───
                "require_sweep": True,   # False = contrôle F3 (sans balayage)
                "need_hl": True,         # False = entrée à la cassure SANS
                                         # attendre le creux plus haut, pour
                                         # mesurer l'apport de l'étape 5
                "_symbol": "",
            },
            status="RESEARCH",
            notes=("Proxy de liquidité = amas d'extrêmes de swing non balayés "
                   "(ANALYSIS.md §4). L'indicateur propriétaire X-Ray n'est pas "
                   "disponible ; un échec réfute le proxy, pas la méthode."),
        )

    # ── Chemin backtest ──────────────────────────────────────────────────────
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Toute la machine à états, dans UNE boucle avant.

        Renvoie un DataFrame (et non un dict) pour que le gardien R1 inspecte
        réellement la couche indicateur — voir l'en-tête du module.
        """
        n = len(df)
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)

        atr = _atr(df, int(params["atr_len"]))
        ema_htf = _ema(df["close"], int(params["htf_ema"]))
        # Expansion de volatilité : proxy de « high candles up, high candles
        # down ». Rapport ATR rapide / ATR lent, strictement causal.
        atr_f = _atr(df, 5)
        atr_s = _atr(df, 50)
        with np.errstate(invalid="ignore", divide="ignore"):
            volratio = np.where(atr_s > 0, atr_f / atr_s, np.nan)

        piv = int(params["piv"])
        band_atr = float(params["band_atr"])
        min_cluster = int(params["min_cluster"])
        min_rr = float(params["min_rr"])
        brk_atr = float(params["brk_atr"])
        setup_bars = int(params["setup_bars"])
        max_age = int(params["max_age"])
        reach_atr = float(params["reach_atr"])
        stop_buf = float(params["stop_buf_atr"])
        stop_ref = str(params["stop_ref"])
        htf_mode = str(params["htf_mode"])
        chop_max = float(params["chop_max"])
        target_mode = str(params["target_mode"])
        require_sweep = bool(params["require_sweep"])
        need_hl = bool(params.get("need_hl", True))
        warm = int(self.manifest().warmup_bars)

        # Entonnoir de diagnostic. Publié dans `DataFrame.attrs` — ni une
        # colonne (R1 comparerait un compteur cumulatif) ni un état de la
        # stratégie : uniquement un instrument de mesure pour research/.
        diag = {"armed": 0, "expired": 0, "struct_ok": 0, "brk": 0,
                "rej_htf": 0, "rej_chop": 0, "rej_stop": 0,
                "rej_target": 0, "rej_rr": 0, "fired": 0}

        sig_side = np.zeros(n, dtype=float)     # +1 long, -1 short, 0 rien
        sig_entry = np.full(n, np.nan)
        sig_stop = np.full(n, np.nan)
        sig_target = np.full(n, np.nan)
        sig_ncluster = np.zeros(n, dtype=float)

        # Extrêmes confirmés : (indice, prix, balayé ?)
        ph: list[list] = []       # sommets
        pl: list[list] = []       # creux

        # États armés. None = pas de setup en cours de ce côté.
        #   {"sweep": prix extrême du balayage, "bar": barre du balayage,
        #    "hi"/"lo": sommet/creux intermédiaire, "hl"/"lh": creux plus haut /
        #    sommet plus bas}
        long_st: Optional[dict] = None
        short_st: Optional[dict] = None

        for i in range(n):
            a = atr[i]

            # ── 1. Confirmation des pivots (causal : centre en i - piv) ──────
            #
            # ORDRE CRITIQUE — l'état « balayé » utilisé plus bas est celui de
            # la FIN DE LA BARRE i-1. Si on marquait d'abord les extrêmes
            # balayés par la barre i, l'amas disparaîtrait exactement sur la
            # barre qui le balaie, et aucun balayage ne serait jamais détecté.
            # Le marquage par la barre i se fait donc en fin de boucle (§5).
            hi_i, lo_i = high[i], low[i]
            j = i - piv
            if j - piv >= 0:
                seg_h = high[j - piv: i + 1]
                seg_l = low[j - piv: i + 1]
                if high[j] >= seg_h.max():
                    # Déjà balayé si le prix l'a traversé entre j+1 et i-1.
                    swept = bool(high[j + 1: i].max() > high[j]) if i > j + 1 else False
                    ph.append([j, float(high[j]), swept])
                if low[j] <= seg_l.min():
                    swept = bool(low[j + 1: i].min() < low[j]) if i > j + 1 else False
                    pl.append([j, float(low[j]), swept])

            # Purge des extrêmes trop anciens (mémoire bornée).
            if len(ph) > 400:
                ph = [p for p in ph if i - p[0] <= max_age]
            if len(pl) > 400:
                pl = [p for p in pl if i - p[0] <= max_age]

            if i < warm or not np.isfinite(a) or a <= 0:
                # Même hors période de chauffe, l'état « balayé » doit rester à
                # jour, sinon l'historique des extrêmes est faux.
                for p in ph:
                    if not p[2] and hi_i > p[1]:
                        p[2] = True
                for p in pl:
                    if not p[2] and lo_i < p[1]:
                        p[2] = True
                continue

            band = band_atr * a
            reach = reach_atr * a
            c = close[i]

            unswept_lo = [p[1] for p in pl
                          if not p[2] and i - p[0] <= max_age and p[1] > c - reach]
            unswept_hi = [p[1] for p in ph
                          if not p[2] and i - p[0] <= max_age and p[1] < c + reach]
            # Pour la CIBLE : tout extrême non balayé au-delà du prix, quel que
            # soit le côté déjà consommé.
            tgt_hi = [p[1] for p in ph if not p[2] and i - p[0] <= max_age]
            tgt_lo = [p[1] for p in pl if not p[2] and i - p[0] <= max_age]

            # ── 3. Détection du BALAYAGE (ou armement direct si contrôle F3) ──
            if long_st is None:
                cl = _cluster_below(unswept_lo, c, band, min_cluster)
                if cl is not None and (lo_i < cl[0] or not require_sweep):
                    long_st = {"sweep": float(lo_i), "bar": i, "hi": None,
                               "hi_bar": -1, "hl": None, "n": cl[1]}
                    diag["armed"] += 1
            if short_st is None:
                ch = _cluster_above(unswept_hi, c, band, min_cluster)
                if ch is not None and (hi_i > ch[0] or not require_sweep):
                    short_st = {"sweep": float(hi_i), "bar": i, "lo": None,
                                "lo_bar": -1, "lh": None, "n": ch[1]}
                    diag["armed"] += 1

            # ── 4. Structure de retournement + entrée ────────────────────────
            fired = 0
            entry = stop = target = np.nan
            ncl = 0.0

            # ---- LONG ----
            if long_st is not None:
                st = long_st
                if i - st["bar"] > setup_bars:
                    long_st = None
                    diag["expired"] += 1
                else:
                    if lo_i < st["sweep"]:
                        # Le balayage se poursuit : la structure repart de zéro.
                        st["sweep"] = float(lo_i)
                        st["hi"] = None
                        st["hl"] = None
                        st["bar"] = i
                    else:
                        # Sommet intermédiaire = dernier pivot haut confirmé
                        # APRÈS le balayage.
                        for p in reversed(ph):
                            if p[0] > st["bar"] and p[0] <= i - piv:
                                if st["hi"] is None or p[0] > st["hi_bar"]:
                                    st["hi"], st["hi_bar"] = p[1], p[0]
                                break
                        # Creux plus haut, formé après ce sommet.
                        if st["hi"] is not None:
                            for p in reversed(pl):
                                if p[0] > st["hi_bar"] and p[1] > st["sweep"]:
                                    st["hl"] = p[1]
                                    break
                        ok_htf = (htf_mode == "off") or (
                            np.isfinite(ema_htf[i]) and c > ema_htf[i])
                        ok_chop = (not np.isfinite(volratio[i])) or (volratio[i] <= chop_max)
                        struct = st["hi"] is not None and (st["hl"] is not None or not need_hl)
                        if struct:
                            diag["struct_ok"] += 1
                        if struct and c > st["hi"] + brk_atr * a:
                            diag["brk"] += 1
                            if not ok_htf:
                                diag["rej_htf"] += 1
                            elif not ok_chop:
                                diag["rej_chop"] += 1
                            else:
                                e = c
                                ref_lo = st["hl"] if (stop_ref != "sweep" and st["hl"] is not None) else st["sweep"]
                                s = ref_lo - stop_buf * a
                                if s >= e:
                                    diag["rej_stop"] += 1
                                else:
                                    t = _target_above(tgt_hi, e, band, min_cluster,
                                                      e - s, min_rr, target_mode)
                                    if t is None:
                                        diag["rej_target"] += 1
                                    elif (t - e) / (e - s) < min_rr:
                                        diag["rej_rr"] += 1
                                    else:
                                        fired, entry, stop, target = 1, e, s, t
                                        ncl = float(st["n"])
                                        diag["fired"] += 1
                            long_st = None

            # ---- SHORT ----
            if short_st is not None and fired == 0:
                st = short_st
                if i - st["bar"] > setup_bars:
                    short_st = None
                    diag["expired"] += 1
                else:
                    if hi_i > st["sweep"]:
                        st["sweep"] = float(hi_i)
                        st["lo"] = None
                        st["lh"] = None
                        st["bar"] = i
                    else:
                        for p in reversed(pl):
                            if p[0] > st["bar"] and p[0] <= i - piv:
                                if st["lo"] is None or p[0] > st["lo_bar"]:
                                    st["lo"], st["lo_bar"] = p[1], p[0]
                                break
                        if st["lo"] is not None:
                            for p in reversed(ph):
                                if p[0] > st["lo_bar"] and p[1] < st["sweep"]:
                                    st["lh"] = p[1]
                                    break
                        ok_htf = (htf_mode == "off") or (
                            np.isfinite(ema_htf[i]) and c < ema_htf[i])
                        ok_chop = (not np.isfinite(volratio[i])) or (volratio[i] <= chop_max)
                        struct = st["lo"] is not None and (st["lh"] is not None or not need_hl)
                        if struct:
                            diag["struct_ok"] += 1
                        if struct and c < st["lo"] - brk_atr * a:
                            diag["brk"] += 1
                            if not ok_htf:
                                diag["rej_htf"] += 1
                            elif not ok_chop:
                                diag["rej_chop"] += 1
                            else:
                                e = c
                                ref_hi = st["lh"] if (stop_ref != "sweep" and st["lh"] is not None) else st["sweep"]
                                s = ref_hi + stop_buf * a
                                if s <= e:
                                    diag["rej_stop"] += 1
                                else:
                                    t = _target_below(tgt_lo, e, band, min_cluster,
                                                      s - e, min_rr, target_mode)
                                    if t is None:
                                        diag["rej_target"] += 1
                                    elif (e - t) / (s - e) < min_rr:
                                        diag["rej_rr"] += 1
                                    else:
                                        fired, entry, stop, target = -1, e, s, t
                                        ncl = float(st["n"])
                                        diag["fired"] += 1
                            short_st = None
            elif short_st is not None and fired != 0:
                # Un long a tiré sur cette barre : le short armé reste en attente.
                pass

            sig_side[i] = fired
            sig_entry[i] = entry
            sig_stop[i] = stop
            sig_target[i] = target
            sig_ncluster[i] = ncl

            # ── 5. Marquage « balayé » par la barre i — TOUJOURS EN DERNIER ──
            for p in ph:
                if not p[2] and hi_i > p[1]:
                    p[2] = True
            for p in pl:
                if not p[2] and lo_i < p[1]:
                    p[2] = True

        out_df = pd.DataFrame(
            {
                "close": close,
                "atr": atr,
                "ema_htf": ema_htf,
                "volratio": volratio,
                "sig_side": sig_side,
                "sig_entry": sig_entry,
                "sig_stop": sig_stop,
                "sig_target": sig_target,
                "sig_ncluster": sig_ncluster,
            },
            index=df.index,
        )
        out_df.attrs["diag"] = diag
        return out_df

    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Relecture des colonnes de décision. Rien au-delà de `end_idx`."""
        n = min(int(end_idx), len(data))
        idx = data.index
        side = data["sig_side"].to_numpy()
        entry = data["sig_entry"].to_numpy()
        stop = data["sig_stop"].to_numpy()
        target = data["sig_target"].to_numpy()
        ncl = data["sig_ncluster"].to_numpy()
        sym = str(params.get("_symbol", "")) or "?"

        out: list[Signal] = []
        for i in range(n):
            s = side[i]
            if s == 0 or not np.isfinite(entry[i]):
                continue
            rr = (abs(target[i] - entry[i]) / abs(entry[i] - stop[i])
                  if entry[i] != stop[i] else 0.0)
            out.append(Signal(
                timestamp=pd.Timestamp(idx[i]).to_pydatetime(),
                symbol=sym,
                side=Side.LONG if s > 0 else Side.SHORT,
                entry=float(entry[i]),
                stop=float(stop[i]),
                target=float(target[i]),
                reason=(f"{'balayage' if params.get('require_sweep', True) else 'CONTROLE sans balayage'} "
                        f"d'un amas de {int(ncl[i])} extremes non balayes, "
                        f"puis structure de retournement et cassure nette ; "
                        f"cible = amas oppose ; R:R {rr:.2f}"),
                confidence=1.0,
                meta={"n_cluster": int(ncl[i]), "rr": round(rr, 2),
                      "require_sweep": bool(params.get("require_sweep", True))},
            ))
        return out

    # ── Chemin live ──────────────────────────────────────────────────────────
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """R5/R6 par construction : appelle littéralement le chemin backtest et
        ne retient que la décision de la barre courante. Il n'existe pas deux
        implémentations pouvant diverger."""
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
