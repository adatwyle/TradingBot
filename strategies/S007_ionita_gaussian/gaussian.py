"""
LE CANAL GAUSSIEN — filtre de John Ehlers à N pôles, implémenté causalement
===========================================================================

Ce module ne contient QUE l'indicateur. Il est isolé de `strategy.py` pour une
raison précise : c'est le seul endroit du projet où un `filtfilt` pourrait se
glisser, et on veut pouvoir le tester seul, sans le reste.

CE QU'EST LE FILTRE
-------------------
Ehlers construit un passe-bas à N pôles en cascadant N fois le même filtre à un
pôle. Sa fonction de transfert est :

                        alpha^N
    H(z) =  ---------------------------- ,      x = 1 - alpha
              ( 1 - x . z^-1 ) ^ N

En développant le dénominateur par le binôme de Newton :

    ( 1 - x z^-1 )^N  =  SUM_k  C(N,k) . (-x)^k . z^-k

la récurrence temporelle devient

    y[i] = alpha^N . s[i]  +  SUM_{k>=1} (-1)^(k+1) . C(N,k) . x^k . y[i-k]

C'est exactement la formule `f_filt9x` du Pine Script « Gaussian Channel » de
DonovanWall, celle que la source utilise — les coefficients alternent de signe
et sont les binomiaux. On la retrouve terme à terme pour N = 1..9.

Les coefficients viennent de la période d'échantillonnage :

    beta  = (1 - cos(2.pi/period)) / ( 2^(1/N) - 1 )
    alpha = -beta + sqrt(beta^2 + 2.beta)

POURQUOI C'EST CAUSAL, ET COMMENT ON LE PROUVE
-----------------------------------------------
`y[i]` ne dépend que de `s[i]` et de `y[i-1..i-N]`. Aucun indice supérieur à `i`
n'apparaît. C'est la définition d'un filtre causal, et c'est exactement ce que
`scipy.signal.lfilter` calcule.

Le piège est `scipy.signal.filtfilt`, qui applique le même filtre en avant PUIS
en arrière pour annuler le déphasage. Le résultat en `i` dépend alors de tout le
futur. Sur ce projet, ce bug précis a contaminé des mois de walk-forward.

`prove_causality()` en bas de ce fichier fait la démonstration numérique :
on recalcule le filtre sur une série tronquée et on montre que l'écart est
**exactement nul** (pas « petit » : nul au bit près), puis on montre que la
variante `filtfilt` produit, elle, un écart non nul. Ce n'est pas une
affirmation dans un commentaire, c'est une mesure.

On n'utilise volontairement PAS `scipy` pour le calcul de production : la
récurrence est écrite à la main en NumPy. Motif : `lfilter` est correct, mais
importer `scipy.signal` dans le module rend un `filtfilt` accidentel possible à
une lettre près. Ici, il n'y a rien à mal appeler. `scipy` n'est importé que
dans la fonction de preuve, pour fabriquer le contre-exemple.
"""
from __future__ import annotations

from math import comb, cos, pi, sqrt

import numpy as np
import pandas as pd


def gaussian_coefficients(period: int, poles: int) -> tuple[float, np.ndarray]:
    """Renvoie (alpha, coefficients de récurrence sur y[i-1..i-N]).

    Le k-ième coefficient rendu (k = 0 pour y[i-1]) vaut
    (-1)^k . C(N, k+1) . x^(k+1), déjà signé : la récurrence est une simple
    somme pondérée, sans alternance à gérer par l'appelant.
    """
    if period < 2:
        raise ValueError(f"période doit être >= 2, reçu {period}")
    if not (1 <= poles <= 9):
        raise ValueError(f"poles doit être dans [1, 9], reçu {poles}")

    beta = (1.0 - cos(2.0 * pi / period)) / (2.0 ** (1.0 / poles) - 1.0)
    alpha = -beta + sqrt(beta * beta + 2.0 * beta)
    x = 1.0 - alpha

    coeffs = np.array(
        [((-1.0) ** k) * comb(poles, k + 1) * (x ** (k + 1)) for k in range(poles)],
        dtype=np.float64,
    )
    return alpha, coeffs


def gaussian_filter(series: np.ndarray, period: int, poles: int) -> np.ndarray:
    """Filtre gaussien N pôles, causal, appliqué à `series`.

    Amorçage : `y[i] = s[i]` tant que `i < poles` (les termes y[i-k] n'existent
    pas encore). C'est la convention `nz()` du Pine Script d'origine, qui traite
    les valeurs manquantes comme nulles — à ceci près qu'on initialise sur le
    prix plutôt que sur zéro, ce qui évite un transitoire de plusieurs centaines
    de barres. La conséquence est bornée : le manifest déclare un `warmup_bars`
    largement supérieur à la durée du transitoire, et rien de ce qui précède le
    warmup n'est utilisé pour décider.

    Cette convention d'amorçage est elle-même causale : `y[i]` ne dépend que de
    `s[i]`. C'est vérifié par l'invariant de troncature, pas supposé.
    """
    s = np.asarray(series, dtype=np.float64)
    n = s.size
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out

    alpha, coeffs = gaussian_coefficients(period, poles)
    a_n = alpha ** poles

    for i in range(n):
        if i < poles or not np.isfinite(s[i]):
            out[i] = s[i]
            continue
        acc = a_n * s[i]
        for k in range(poles):
            acc += coeffs[k] * out[i - 1 - k]
        out[i] = acc
    return out


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True range classique. `tr[0] = high[0] - low[0]` (pas de close précédent)."""
    h = np.asarray(high, dtype=np.float64)
    l = np.asarray(low, dtype=np.float64)
    c = np.asarray(close, dtype=np.float64)
    prev = np.empty_like(c)
    prev[0] = c[0]
    prev[1:] = c[:-1]
    return np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))


def gaussian_channel(df: pd.DataFrame, period: int, poles: int,
                     mult: float, source: str = "hlc3") -> pd.DataFrame:
    """Canal gaussien complet : ligne centrale, bandes, tendance.

    Colonnes rendues :
        filter  la sortie du filtre appliquée au prix source
        upper   filter + mult . (true range filtré)
        lower   filter - mult . (true range filtré)
        trend   +1 si le filtre monte, -1 s'il descend, 0 s'il est plat
                (« Green » / « Red » / « Grey » dans le vocabulaire de la source)

    `source` = hlc3 par défaut, comme le Pine Script d'origine.
    """
    h = df["high"].to_numpy(dtype=np.float64)
    l = df["low"].to_numpy(dtype=np.float64)
    c = df["close"].to_numpy(dtype=np.float64)

    if source == "hlc3":
        src = (h + l + c) / 3.0
    elif source == "close":
        src = c
    elif source == "ohlc4":
        src = (df["open"].to_numpy(dtype=np.float64) + h + l + c) / 4.0
    else:
        raise ValueError(f"source inconnue : {source} (hlc3 | close | ohlc4)")

    filt = gaussian_filter(src, period, poles)
    ftr = gaussian_filter(true_range(h, l, c), period, poles)

    prev = np.empty_like(filt)
    prev[0] = filt[0]
    prev[1:] = filt[:-1]
    trend = np.sign(filt - prev)

    return pd.DataFrame(
        {
            "filter": filt,
            "upper": filt + mult * ftr,
            "lower": filt - mult * ftr,
            "trend": trend,
        },
        index=df.index,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Preuve de causalité — mesure, pas déclaration
# ─────────────────────────────────────────────────────────────────────────────
def prove_causality(df: pd.DataFrame, period: int = 144, poles: int = 4,
                    mult: float = 1.414, cuts=(0.6, 0.7, 0.8, 0.9)) -> dict:
    """Compare le filtre causal et sa variante aller-retour sur données tronquées.

    Renvoie, pour chaque coupure T, l'écart maximal entre le canal calculé sur
    l'historique complet et le canal calculé sur `df[:T]`, restreint à [0, T).

    Attendu :
      - version causale (celle qu'on utilise)  -> écart EXACTEMENT 0
      - version filtfilt (le contre-exemple)   -> écart > 0

    Le contre-exemple n'est pas décoratif : il montre que le test a le pouvoir
    de détecter la fuite qu'on prétend éviter. Un test qui ne peut pas échouer
    ne prouve rien.
    """
    from scipy.signal import filtfilt, lfilter  # local : ne pollue pas le module

    alpha, coeffs = gaussian_coefficients(period, poles)
    b = np.array([alpha ** poles], dtype=np.float64)
    # a = coefficients du dénominateur (1 - x z^-1)^N, signe opposé à `coeffs`
    a = np.concatenate([[1.0], -coeffs])

    src_full = ((df["high"] + df["low"] + df["close"]) / 3.0).to_numpy(dtype=np.float64)
    n = len(src_full)

    out = {"period": period, "poles": poles, "n_bars": n, "cuts": []}
    for frac in cuts:
        T = int(n * frac)

        causal_full = gaussian_channel(df, period, poles, mult)
        causal_trunc = gaussian_channel(df.iloc[:T], period, poles, mult)
        dev_causal = {
            col: float(np.nanmax(np.abs(
                causal_full[col].to_numpy()[:T] - causal_trunc[col].to_numpy()[:T])))
            for col in ("filter", "upper", "lower", "trend")
        }

        # Contre-exemple : le même filtre, appliqué en aller-retour.
        ff_full = filtfilt(b, a, src_full)
        ff_trunc = filtfilt(b, a, src_full[:T])
        dev_filtfilt = float(np.nanmax(np.abs(ff_full[:T] - ff_trunc)))

        # Contrôle : lfilter (causal, scipy) doit lui aussi donner zéro.
        lf_full = lfilter(b, a, src_full)
        lf_trunc = lfilter(b, a, src_full[:T])
        dev_lfilter = float(np.nanmax(np.abs(lf_full[:T] - lf_trunc)))

        out["cuts"].append({
            "fraction": frac, "T": T,
            "causal_max_dev": dev_causal,
            "lfilter_max_dev": dev_lfilter,
            "filtfilt_max_dev": dev_filtfilt,
        })
    return out
