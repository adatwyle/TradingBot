"""
Cribleur de dérive — une entrée contient-elle de l'information directionnelle ?

    PYTHONIOENCODING=utf-8 python studies/derive_screener/screener.py

POURQUOI CET OUTIL EXISTE
--------------------------
Le 2026-09-06, S019 a coûté deux campagnes de walk-forward complètes (16 cellules,
120 000 puis 359 000 barres) pour conclure que son déclencheur d'entrée ne contenait
aucune information. Le lendemain, la même conclusion a été obtenue en quatre minutes
en regardant la loi de chemin des trades : les probabilités de continuation collaient
à la martingale à moins de trois points.

Ce module généralise cette économie. Avant de construire une stratégie sur une
hypothèse d'entrée, on demande d'abord : le chemin qui suit cette entrée a-t-il une
dérive ? Une entrée sans dérive ne peut être sauvée par aucune sortie — c'est le
théorème d'arrêt optionnel, pas une opinion.

CE QU'IL MESURE, EXACTEMENT
----------------------------
Pour chaque entrée candidate (instant, sens), on pose un stop à sl·ATR et une cible à
tp·ATR, et on demande lequel est touché le premier. Le score est l'espérance en R :

    E[R] = P(cible en premier) x (tp/sl) - P(stop en premier) x 1

Sous absence de dérive, E[R] = 0 — et c'est vrai POUR TOUTE GÉOMÉTRIE, par le théorème
d'arrêt optionnel. Un E[R] significativement positif est de l'information exploitable.

UNE PREMIÈRE VERSION DE CET OUTIL ÉTAIT FAUSSE, ET LE TÉMOIN L'A DIT
---------------------------------------------------------------------
La version du 2026-09-07 posait des barrières SYMÉTRIQUES (±k·ATR). Son témoin positif
— la famille de la v1 — en ressortait NÉGATIF (-0,075) alors que la v1 rend +0,236 R
par trade au percentile 100 du hasard. Le critère de validité, écrit avant la mesure,
a donc invalidé l'outil.

La cause : la v1 gagne avec 34,6 % de réussite parce qu'elle vise 4 ATR en risquant
1,5. Son avantage vit dans l'ASYMÉTRIE du gain, et un test symétrique le jette. Une
mesure de dérive doit donc se faire À LA GÉOMÉTRIE OÙ L'ON COMPTE JOUER, jamais à une
géométrie de convenance.

Second défaut révélé par le témoin : à barrières très rapprochées (0,5 ATR), toutes les
entrées rendaient -0,09, y compris les entrées TIRÉES AU HASARD. Les deux barrières
tombent alors souvent dans la même barre, où la convention tranche contre nous. La
mesure est donc refusée sous un écartement minimal, et le nombre de résolutions
ambiguës est désormais affiché.

Trois précautions qui font la différence entre une mesure et une illusion :

  1. RISQUE UNIFORME. Toutes les entrées candidates sont évaluées avec le même stop
     (k·ATR) et la même cible. Sans cela on comparerait des placements de stop, pas
     des entrées.
  2. PAS DE CHEVAUCHEMENT. Une position à la fois : tant qu'une entrée n'est pas
     résolue, les suivantes sont ignorées. Des trades qui se chevauchent partagent le
     même bout de chemin et gonflent artificiellement la significativité.
  3. TÉMOIN. Des entrées tirées au hasard aux mêmes instants et dans les mêmes
     proportions de sens doivent rendre E ≈ 0. Si ce n'est pas le cas, le cribleur
     est faux et aucun autre chiffre n'est interprétable.

CE QU'IL NE MESURE PAS
-----------------------
Le coût de bord. Les barrières sont franchies au prix nu. Une entrée dont la dérive
est plus petite que le spread est sans valeur en pratique : le tableau final affiche
donc la dérive EN PIPS à côté du spread mesuré, pour que la comparaison soit
impossible à éviter.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from strategies.S011_legacy_breakout.strategy import _atr  # noqa: E402

PIP = 0.01
LONG, SHORT = 1, -1


# ─────────────────────────────────────────────────────────────────────────────
# Le cribleur
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Verdict:
    nom: str
    n: int
    e: float                 # espérance en R à la géométrie testée
    ic_bas: float
    ic_haut: float
    p_favorable: float       # taux de réussite observé
    p_equilibre: float       # taux de réussite d'équilibre = sl/(sl+tp)
    derive_pips: float       # E[R] converti en pips, à comparer au spread
    risque_median_pips: float
    horizon_median: float    # barres jusqu'à résolution
    non_resolus: int
    ambigus: int             # résolus dans la même barre — tranchés contre nous

    @property
    def significatif(self) -> bool:
        """L'intervalle de confiance à 95 % exclut-il zéro ?"""
        return self.ic_bas > 0.0 or self.ic_haut < 0.0


def _premier_passage(hi: np.ndarray, lo: np.ndarray, i: int, entry: float,
                     d_sl: float, d_tp: float, side: int, horizon: int):
    """Rend (issue, barres, ambigu). issue = +1 cible, -1 stop, None non résolu.

    Le stop prime dans la même barre — convention pessimiste du moteur commun. Le
    cas est compté séparément : quand il devient fréquent, la mesure est biaisée
    contre nous et cesse d'être lisible.
    """
    end = min(len(hi), i + 1 + horizon)
    if end <= i + 1:
        return None, 0, False
    h, l = hi[i + 1:end], lo[i + 1:end]
    if side == LONG:
        fav, adv = h >= entry + d_tp, l <= entry - d_sl
    else:
        fav, adv = l <= entry - d_tp, h >= entry + d_sl
    wf, wa = np.flatnonzero(fav), np.flatnonzero(adv)
    tf = int(wf[0]) if len(wf) else None
    ta = int(wa[0]) if len(wa) else None
    if tf is None and ta is None:
        return None, 0, False
    if tf is None:
        return -1, ta, False
    if ta is None:
        return +1, tf, False
    if ta < tf:
        return -1, ta, False
    if tf < ta:
        return +1, tf, False
    return -1, ta, True                     # même barre : le stop prime


def cribler(bars: pd.DataFrame, entrees: Iterable[tuple[int, int]], nom: str,
            sl_atr: float = 1.5, tp_atr: float = 4.0, horizon: int = 400,
            atr_period: int = 14) -> Verdict:
    """Mesure l'espérance en R d'un jeu d'entrées (index de barre, sens), à la
    géométrie (sl_atr, tp_atr) demandée.

    Les entrées qui se chevauchent sont écartées : tant qu'une position n'est pas
    résolue, on n'en ouvre pas d'autre. Des trades qui partagent un bout de chemin
    gonflent la significativité sans apporter d'information.
    """
    atr = _atr(bars["high"].to_numpy(), bars["low"].to_numpy(),
               bars["close"].to_numpy(), atr_period)
    hi = bars["high"].to_numpy()
    lo = bars["low"].to_numpy()
    cl = bars["close"].to_numpy()
    rr = tp_atr / sl_atr

    gains: list[float] = []
    risques: list[float] = []
    horizons: list[int] = []
    non_resolus = ambigus = 0
    libre_a = -1

    for i, side in sorted(entrees):
        if i <= libre_a or i + 1 >= len(bars):
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        d_sl, d_tp = sl_atr * a, tp_atr * a
        entry = cl[i]
        issue, t, amb = _premier_passage(hi, lo, i, entry, d_sl, d_tp, side, horizon)
        if issue is None:
            non_resolus += 1
            libre_a = i + horizon           # la position aurait immobilisé le capital
            continue
        ambigus += int(amb)
        libre_a = i + 1 + t
        gains.append(rr if issue > 0 else -1.0)
        risques.append(d_sl / PIP)
        horizons.append(t)

    n = len(gains)
    p_eq = sl_atr / (sl_atr + tp_atr)
    if n < 30:
        return Verdict(nom, n, float("nan"), float("nan"), float("nan"),
                       float("nan"), p_eq, float("nan"),
                       float(np.median(risques)) if risques else float("nan"),
                       float(np.median(horizons)) if horizons else float("nan"),
                       non_resolus, ambigus)

    x = np.array(gains, dtype=float)
    e = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(n))
    risque_med = float(np.median(risques))
    return Verdict(
        nom=nom, n=n, e=e, ic_bas=e - 1.96 * se, ic_haut=e + 1.96 * se,
        p_favorable=float((x > 0).mean()), p_equilibre=p_eq,
        derive_pips=e * risque_med, risque_median_pips=risque_med,
        horizon_median=float(np.median(horizons)),
        non_resolus=non_resolus, ambigus=ambigus,
    )


def temoin(bars: pd.DataFrame, entrees: list[tuple[int, int]], nom: str,
           seed: int, tirages: int = 20, **kw) -> tuple[float, float]:
    """Même effectif, mêmes proportions de sens, instants tirés au hasard.

    Rend la moyenne et l'écart-type des espérances obtenues. Doit encadrer zéro,
    sinon le cribleur lui-même est en cause.
    """
    if not entrees:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    sides = np.array([s for _, s in entrees])
    n = len(entrees)
    lo_i, hi_i = 100, len(bars) - 401
    if hi_i <= lo_i:
        return float("nan"), float("nan")
    out = []
    for _ in range(tirages):
        idx = rng.integers(lo_i, hi_i, size=n)
        sd = rng.permutation(sides)
        v = cribler(bars, list(zip(idx.tolist(), sd.tolist())), nom, **kw)
        if np.isfinite(v.e):
            out.append(v.e)
    if not out:
        return float("nan"), float("nan")
    return float(np.mean(out)), float(np.std(out, ddof=1)) if len(out) > 1 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Les candidats — liste ARRÊTÉE avant toute exécution (PLAN § T5)
# ─────────────────────────────────────────────────────────────────────────────

def _sweep(bars: pd.DataFrame, lookback: int, window: int, sens: int
           ) -> list[tuple[int, int]]:
    """Balayage puis réintégration. sens=LONG : un plus-bas est percé puis la
    clôture repasse au-dessus. sens=SHORT : le miroir exact."""
    hi, lo, cl = (bars[c].to_numpy() for c in ("high", "low", "close"))
    out: list[tuple[int, int]] = []
    n = len(bars)
    for j in range(lookback, n - 1):
        if sens == LONG:
            ref = lo[j - lookback:j].min()
            perce = lo[j] < ref and cl[j] <= ref
        else:
            ref = hi[j - lookback:j].max()
            perce = hi[j] > ref and cl[j] >= ref
        if not perce:
            continue
        for m in range(j + 1, min(j + 1 + window, n)):
            if (sens == LONG and cl[m] > ref) or (sens == SHORT and cl[m] < ref):
                out.append((m, sens))
                break
    return out


def _donchian(bars: pd.DataFrame, periode: int = 40) -> list[tuple[int, int]]:
    """Cassure de canal — la famille de la v1. Sert de TÉMOIN POSITIF : si le
    cribleur ne la voit pas, il est faux."""
    hi, lo, cl = (bars[c].to_numpy() for c in ("high", "low", "close"))
    out = []
    for i in range(periode, len(bars) - 1):
        if cl[i] > hi[i - periode:i].max():
            out.append((i, LONG))
        elif cl[i] < lo[i - periode:i].min():
            out.append((i, SHORT))
    return out


def _equilibre(bars: pd.DataFrame, jambe: int = 20, ratio: float = 0.5,
               tol: float = 0.1) -> list[tuple[int, int]]:
    """Repli à la moitié de la dernière jambe — le « D4 » de S018, cœur annoncé
    de la v2 et mesuré nul en H1."""
    hi, lo, cl = (bars[c].to_numpy() for c in ("high", "low", "close"))
    out = []
    for i in range(jambe, len(bars) - 1):
        h, l = hi[i - jambe:i].max(), lo[i - jambe:i].min()
        amp = h - l
        if amp <= 0:
            continue
        mid = l + ratio * amp
        if abs(cl[i] - mid) > tol * amp:
            continue
        # sens donné par la jambe : un repli dans une jambe haussière est un achat
        monte = np.argmax(hi[i - jambe:i]) > np.argmin(lo[i - jambe:i])
        out.append((i, LONG if monte else SHORT))
    return out


def _psychologique(bars: pd.DataFrame, pas: float = 50.0, tol_atr: float = 0.15
                   ) -> list[tuple[int, int]]:
    """Réaction sur un niveau rond. Elle en parle comme d'un aimant ET d'un piège :
    « le marché va réagir sur des prix psychologiques » mais « c'est là où le
    marché va vous piéger »."""
    cl = bars["close"].to_numpy()
    lo, hi = bars["low"].to_numpy(), bars["high"].to_numpy()
    atr = _atr(bars["high"].to_numpy(), bars["low"].to_numpy(),
               bars["close"].to_numpy(), 14)
    out = []
    for i in range(20, len(bars) - 1):
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        niveau = round(cl[i] / pas) * pas
        # la barre touche le niveau et le rejette
        if lo[i] <= niveau <= hi[i] and abs(cl[i] - niveau) < tol_atr * a:
            continue                       # clôture collée : pas de rejet net
        if lo[i] <= niveau <= hi[i]:
            out.append((i, LONG if cl[i] > niveau else SHORT))
    return out


def _mi_asiatique(bars: pd.DataFrame) -> list[tuple[int, int]]:
    """Le milieu de la plage asiatique comme support/résistance de la session US.
    « on attend bien les 2665 midasian pour ceux qui le savent »."""
    idx = bars.index
    cl = bars["close"].to_numpy()
    lo, hi = bars["low"].to_numpy(), bars["high"].to_numpy()
    heure = idx.hour.to_numpy()
    jour = idx.normalize()
    asie = (heure >= 23) | (heure <= 6)
    df = pd.DataFrame({"jour": jour, "asie": asie, "hi": hi, "lo": lo})
    mids: dict = {}
    for j, g in df[df["asie"]].groupby("jour"):
        if len(g) >= 4:
            mids[j] = (g["hi"].max() + g["lo"].min()) / 2.0
    out = []
    veille = {j: mids.get(j - pd.Timedelta(days=1)) for j in df["jour"].unique()}
    for i in range(1, len(bars)):
        if heure[i] < 8:                    # on ne joue le mid qu'en séance
            continue
        m = veille.get(jour[i]) or mids.get(jour[i])
        if m is None:
            continue
        if lo[i] <= m <= hi[i]:
            out.append((i, LONG if cl[i] > m else SHORT))
    return out


def _extremes_veille(bars: pd.DataFrame) -> list[tuple[int, int]]:
    """Plus-haut et plus-bas du jour précédent — les repères les plus universels,
    et les seuls qui existent même en territoire vierge."""
    jour = bars.index.normalize()
    d = pd.DataFrame({"jour": jour, "hi": bars["high"].to_numpy(),
                      "lo": bars["low"].to_numpy()})
    agg = d.groupby("jour").agg(h=("hi", "max"), l=("lo", "min"))
    prev = agg.shift(1)
    cl = bars["close"].to_numpy()
    lo, hi = bars["low"].to_numpy(), bars["high"].to_numpy()
    out = []
    for i in range(len(bars)):
        j = jour[i]
        if j not in prev.index:
            continue
        ph, pl = prev.loc[j, "h"], prev.loc[j, "l"]
        if np.isnan(ph) or np.isnan(pl):
            continue
        if lo[i] <= ph <= hi[i]:
            out.append((i, LONG if cl[i] > ph else SHORT))
        elif lo[i] <= pl <= hi[i]:
            out.append((i, LONG if cl[i] > pl else SHORT))
    return out


def _compression(bars: pd.DataFrame, fenetre: int = 20, seuil: float = 0.6
                 ) -> list[tuple[int, int]]:
    """Compression de volatilité puis expansion — sa « salade de doji » suivie
    d'une décision. Elle la décrit comme un ÉTAT d'indécision, pas un signal :
    c'est la sortie de cet état qu'on teste."""
    rng = (bars["high"] - bars["low"]).to_numpy()
    cl = bars["close"].to_numpy()
    moy = pd.Series(rng).rolling(fenetre).mean().to_numpy()
    out = []
    for i in range(fenetre + 1, len(bars) - 1):
        if not np.isfinite(moy[i - 1]) or moy[i - 1] <= 0:
            continue
        comprime = rng[i - 1] < seuil * moy[i - 1]
        expansion = rng[i] > moy[i - 1]
        if comprime and expansion:
            out.append((i, LONG if cl[i] > cl[i - 1] else SHORT))
    return out


CANDIDATS: dict[str, Callable[[pd.DataFrame], list[tuple[int, int]]]] = {
    "1 balayage haussier":   lambda b: _sweep(b, 60, 5, LONG),
    "2 balayage baissier":   lambda b: _sweep(b, 60, 5, SHORT),
    "3 equilibre 50%":       _equilibre,
    "4 cassure donchian":    _donchian,        # témoin positif attendu
    "5 niveau rond 50":      _psychologique,
    "6 mi-asiatique":        _mi_asiatique,
    "7 extremes veille":     _extremes_veille,
    "8 compression":         _compression,
}


def _v1_reelle(bars: pd.DataFrame) -> list[tuple[int, int]]:
    """LE TÉMOIN POSITIF — la stratégie v1 elle-même, à ses paramètres scellés.

    On n'approxime pas : on importe S011 et on lui demande ses signaux. Si le
    cribleur ne voit pas de dérive ici, il ne mesure pas ce qu'il prétend, et
    aucune autre ligne du tableau n'est lisible. Paramètres repris de
    `studies/gold_forward/PROTOCOL.md` § 2.2 (cellule scellée).
    """
    from strategies.S011_legacy_breakout.strategy import Strategy  # import local

    p = {"adx_min": 20, "donchian": 40, "er_min": 0.0, "fr_max": 1.0,
         "tp_m": 4.0, "sl_m": 1.5, "atr_vol_ratio": 0.8,
         "adx_rising_lookback": 5, "rsi_long_max": 75, "rsi_short_min": 25}
    s = Strategy(p)
    s._symbol = "XAUUSD"
    sigs = s.generate_signals(s.precompute(bars, p), p, len(bars))
    pos = {t: i for i, t in enumerate(bars.index)}
    out = []
    for sg in sigs:
        i = pos.get(pd.Timestamp(sg.timestamp))
        if i is not None:
            out.append((i, LONG if sg.side.value == "LONG" else SHORT))
    return out


CANDIDATS["0 TEMOIN v1 (S011)"] = _v1_reelle
