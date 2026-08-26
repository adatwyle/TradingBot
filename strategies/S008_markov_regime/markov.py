"""
NOYAU MATHÉMATIQUE — chaîne de Markov sur régimes de marché
============================================================

Tout le calcul de la stratégie s08 vit ici, séparé de `strategy.py` pour une
raison précise : ces fonctions doivent pouvoir être testées et comparées entre
elles (causale / fuitée, recouvrante / non recouvrante, matricielle / scalaire)
sans passer par le contrat d'allocation.

LES QUATRE POINTS OÙ UNE IMPLÉMENTATION NAÏVE SE TROMPE
--------------------------------------------------------

1. **La grille d'échantillonnage doit être ancrée sur la barre 0.**
   L'auteur dit « attendre 20 jours avant l'observation suivante ». Si on ancre
   cette grille sur la DERNIÈRE barre disponible, la troncature du backtest
   décale toute la grille : le même jour de 2018 appartient à la grille quand on
   arrête en 2024 et n'y appartient plus quand on arrête en 2026. C'est une
   violation de R1 par la porte de derrière — invisible au niveau du signal la
   plupart du temps. Ancrage sur 0 : la grille est un invariant de l'historique.

2. **Une transition n'est connue qu'à son ARRIVÉE.**
   La paire (état en j, état en j+step) devient observable à j+step, pas à j.
   Compter une paire à l'instant j revient à connaître l'état futur. Toute la
   comptabilité est donc indexée par l'instant d'ARRIVÉE.

3. **`P^n` est une puissance de MATRICE.**
   La source décrit `0,6 × 0,6` — l'exponentiation d'un scalaire. C'est faux
   pour une chaîne de Markov : la distribution à n pas est `e_état · P^n`. Les
   deux ne coïncident pas, et leurs limites sont opposées : le scalaire tend
   vers 0, `P^n` tend vers la distribution stationnaire. Les deux sont
   implémentées ici, la fausse uniquement pour chiffrer l'écart.

4. **Le pas d'échantillonnage change la SÉMANTIQUE du signal.**
   Avec `step=1` la matrice décrit « l'état demain ». Avec `step=20` — la
   correction de l'auteur — elle décrit « l'état dans 20 jours ». Ce n'est plus
   la même question. L'auteur ne le mentionne jamais. Les deux sont produites.

CONVENTION D'ÉTATS
------------------
    0 = bear     1 = sideways     2 = bull     -1 = indéfini (warmup)
Ordonnée pour que l'indice croisse avec la direction : utile pour mapper les
états d'un HMM, dont les composantes sont triées par moyenne.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BEAR, SIDE, BULL, UNDEF = 0, 1, 2, -1
N_STATES = 3


# ─────────────────────────────────────────────────────────────────────────────
# États
# ─────────────────────────────────────────────────────────────────────────────
def rolling_return(close: np.ndarray, window: int) -> np.ndarray:
    """Rendement cumulé sur `window` barres. `r[i] = close[i]/close[i-w] - 1`.

    Causal par construction : ne lit que [i-w, i].
    """
    r = np.full(len(close), np.nan)
    if len(close) > window:
        r[window:] = close[window:] / close[:-window] - 1.0
    return r


def classify(ret: np.ndarray, thr_up: float, thr_dn: float) -> np.ndarray:
    """Rendement -> état. Les seuils sont ceux de la source (+5 % / -5 %)."""
    st = np.full(len(ret), UNDEF, dtype=np.int64)
    ok = np.isfinite(ret)
    st[ok & (ret > thr_up)] = BULL
    st[ok & (ret < thr_dn)] = BEAR
    st[ok & (ret >= thr_dn) & (ret <= thr_up)] = SIDE
    return st


# ─────────────────────────────────────────────────────────────────────────────
# Comptage des transitions
# ─────────────────────────────────────────────────────────────────────────────
def transition_pairs(states: np.ndarray, step: int) -> list[tuple[int, int, int]]:
    """Paires (état de départ, état d'arrivée, instant où la paire est CONNUE).

    `step = 1`  -> transitions consécutives : fenêtres de 20 j qui se
                   chevauchent sur 19 j. C'est la version que l'auteur qualifie
                   d'artefact, et il a raison.
    `step = w`  -> grille ancrée sur la première barre définie, un point tous
                   les `step` pas. Aucun recouvrement entre deux fenêtres
                   successives si `step >= window`.

    L'ancrage est le premier indice où l'état est défini — donc une fonction de
    l'historique, jamais de l'endroit où on arrête le backtest (cf. point 1 du
    docstring de module).
    """
    if step < 1:
        raise ValueError("step >= 1")
    defined = np.flatnonzero(states >= 0)
    if defined.size == 0:
        return []
    anchor = int(defined[0])

    pairs = []
    j = anchor
    n = len(states)
    while j + step < n:
        a, b = states[j], states[j + step]
        if a >= 0 and b >= 0:
            pairs.append((int(a), int(b), int(j + step)))
        j += step
    return pairs


def cumulative_counts(states: np.ndarray, step: int) -> np.ndarray:
    """Comptes cumulés de transitions connus À CHAQUE BARRE.

    Retourne un tableau `(n, 3, 3)` où `C[i, a, b]` est le nombre de transitions
    a->b **observées jusqu'à la barre i incluse**. C'est la quantité causale :
    la matrice utilisée pour décider en i n'a le droit de contenir que ça.
    """
    n = len(states)
    inc = np.zeros((n, N_STATES, N_STATES), dtype=np.float64)
    for a, b, t in transition_pairs(states, step):
        inc[t, a, b] += 1.0
    return np.cumsum(inc, axis=0)


def normalize(counts: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """Comptes -> matrice stochastique, avec lissage de Laplace.

    `alpha` n'est pas cosmétique : sur une grille non recouvrante, les premières
    fenêtres du walk-forward ne disposent que de quelques dizaines de
    transitions, et certaines lignes sont vides. Sans lissage, la ligne d'un
    état jamais rencontré est indéfinie ; avec, elle vaut l'uniforme, donc un
    signal nul. C'est le comportement voulu : « je ne sais pas » -> pas de pari.

    Contrepartie honnête : `alpha` tire aussi les lignes peu peuplées vers
    l'uniforme, donc vers un signal plus faible. Il amortit, il ne crée rien.
    """
    c = counts + alpha
    return c / c.sum(axis=-1, keepdims=True)


def matrix_power_rows(P: np.ndarray, n: int) -> np.ndarray:
    """`P^n`, la VRAIE prévision à n pas d'une chaîne de Markov.

    Accepte un empilement `(..., 3, 3)` pour traiter toutes les barres d'un coup.
    """
    if n < 1:
        raise ValueError("horizon >= 1")
    out = P.copy()
    for _ in range(n - 1):
        out = out @ P
    return out


def scalar_power_signal(sig: np.ndarray, n: int) -> np.ndarray:
    """La version de la SOURCE : `0,6 -> 0,6² -> 0,6³`. Mathématiquement fausse.

    Conservée uniquement pour chiffrer l'écart avec `P^n`. Le signe est préservé
    (élever un signal négatif à une puissance paire le rendrait positif, ce qui
    n'a aucun sens même dans sa propre logique).
    """
    return np.sign(sig) * np.abs(sig) ** n


# ─────────────────────────────────────────────────────────────────────────────
# Signal
# ─────────────────────────────────────────────────────────────────────────────
def markov_signal(states: np.ndarray, step: int, *, horizon: int = 1,
                  alpha: float = 1.0, causal: bool = True,
                  scalar_power: bool = False) -> dict[str, np.ndarray]:
    """`P(bull | état) − P(bear | état)`, barre par barre.

    `causal=True`  : la matrice à la barre i n'utilise que les transitions dont
                     l'arrivée est <= i. C'est R1, et c'est la « correction n°2 »
                     de la source.
    `causal=False` : la matrice de PLEIN ÉCHANTILLON est utilisée partout — donc
                     un signal qui connaît des transitions non encore survenues.
                     Reproduit la version « v1 » que l'auteur dit avoir corrigée.
                     Sert exclusivement à chiffrer l'ampleur du biais.

    Renvoie signal, p_bull, p_bear, effectif de transitions connu, et la
    persistance instantanée `P(état|état)` — cette dernière est ce que l'auteur
    appelle « stickiness », et sa chute entre `step=1` et `step=20` est la
    mesure de son artefact n°1.
    """
    n = len(states)
    C = cumulative_counts(states, step)
    if not causal:
        C = np.repeat(C[-1][None, :, :], n, axis=0)

    P = normalize(C, alpha)                       # (n, 3, 3)
    Pn = P if horizon == 1 else matrix_power_rows(P, horizon)

    idx = np.arange(n)
    st = states.copy()
    valid = st >= 0
    safe = np.where(valid, st, 0)

    p_bull = Pn[idx, safe, BULL]
    p_bear = Pn[idx, safe, BEAR]
    sig = p_bull - p_bear

    if scalar_power and horizon > 1:
        # Recalcul depuis l'horizon 1, puis exponentiation scalaire : c'est
        # littéralement ce que décrit la source.
        s1 = P[idx, safe, BULL] - P[idx, safe, BEAR]
        sig = scalar_power_signal(s1, horizon)
        p_bull = np.full(n, np.nan)
        p_bear = np.full(n, np.nan)

    sig = np.where(valid, sig, 0.0)
    persist = np.where(valid, P[idx, safe, safe], np.nan)
    ntrans = C.sum(axis=(1, 2))

    return {"signal": sig, "p_bull": np.where(valid, p_bull, np.nan),
            "p_bear": np.where(valid, p_bear, np.nan),
            "n_trans": ntrans, "persistence": persist}


def stationary_matrix(states: np.ndarray, step: int, alpha: float = 1.0
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Matrice de plein échantillon et ses comptes bruts. Pour le rapport."""
    C = cumulative_counts(states, step)[-1]
    return normalize(C, alpha), C


# ─────────────────────────────────────────────────────────────────────────────
# Markov caché — implémentation directe (hmmlearn absent de l'environnement)
# ─────────────────────────────────────────────────────────────────────────────
def _gauss_logpdf(x: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    sd = np.maximum(sd, 1e-9)
    z = (x[:, None] - mu[None, :]) / sd[None, :]
    return -0.5 * z * z - np.log(sd)[None, :] - 0.5 * np.log(2 * np.pi)


def fit_gaussian_hmm(x: np.ndarray, k: int = N_STATES, n_iter: int = 60,
                     seed_quantiles: bool = True) -> dict:
    """Baum-Welch sur émissions gaussiennes univariées.

    Initialisation DÉTERMINISTE par quantiles : deux appels sur les mêmes
    données donnent exactement le même modèle. Ce n'est pas un détail de
    confort — sans cela, l'invariant de troncature R1 échouerait pour une raison
    qui n'aurait rien à voir avec une fuite (bruit d'initialisation aléatoire),
    et on ne saurait plus lire le résultat du test.

    Les composantes sont renvoyées TRIÉES par moyenne croissante, donc
    l'indice 0 est le régime le plus baissier et l'indice k-1 le plus haussier.
    Ce tri est ce qui rend les états comparables d'un réajustement à l'autre :
    Baum-Welch n'a aucune raison de conserver l'ordre des étiquettes.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 50:
        raise ValueError("historique trop court pour un HMM")

    if seed_quantiles:
        qs = np.quantile(x, np.linspace(0.15, 0.85, k))
        mu = qs.astype(float)
    else:
        mu = np.linspace(x.min(), x.max(), k)
    sd = np.full(k, float(np.std(x)) or 1e-6)
    A = np.full((k, k), 1.0 / k)
    pi = np.full(k, 1.0 / k)

    for _ in range(n_iter):
        logB = _gauss_logpdf(x, mu, sd)
        B = np.exp(logB - logB.max(axis=1, keepdims=True))

        # Forward-backward avec mise à l'échelle (évite le sous-dépassement).
        alpha_ = np.zeros((n, k))
        scale = np.zeros(n)
        alpha_[0] = pi * B[0]
        scale[0] = alpha_[0].sum() or 1e-300
        alpha_[0] /= scale[0]
        for t in range(1, n):
            alpha_[t] = (alpha_[t - 1] @ A) * B[t]
            scale[t] = alpha_[t].sum() or 1e-300
            alpha_[t] /= scale[t]

        beta_ = np.zeros((n, k))
        beta_[-1] = 1.0
        for t in range(n - 2, -1, -1):
            beta_[t] = (A @ (B[t + 1] * beta_[t + 1])) / scale[t + 1]

        gamma = alpha_ * beta_
        gamma /= np.maximum(gamma.sum(axis=1, keepdims=True), 1e-300)

        xi = np.zeros((k, k))
        for t in range(n - 1):
            m = np.outer(alpha_[t], B[t + 1] * beta_[t + 1]) * A / scale[t + 1]
            xi += m
        A_new = xi / np.maximum(xi.sum(axis=1, keepdims=True), 1e-300)

        w = gamma.sum(axis=0)
        mu_new = (gamma * x[:, None]).sum(axis=0) / np.maximum(w, 1e-300)
        var = (gamma * (x[:, None] - mu_new[None, :]) ** 2).sum(axis=0) / np.maximum(w, 1e-300)
        sd_new = np.sqrt(np.maximum(var, 1e-18))

        if (np.max(np.abs(mu_new - mu)) < 1e-12
                and np.max(np.abs(sd_new - sd)) < 1e-12):
            mu, sd, A, pi = mu_new, sd_new, A_new, gamma[0]
            break
        mu, sd, A, pi = mu_new, sd_new, A_new, gamma[0]

    order = np.argsort(mu)
    return {"mu": mu[order], "sd": sd[order], "A": A[np.ix_(order, order)],
            "pi": pi[order]}


def hmm_viterbi(x: np.ndarray, model: dict) -> np.ndarray:
    """Étiquetage par Viterbi. Utilisé UNIQUEMENT en avant.

    Attention : Viterbi est un décodage GLOBAL — l'étiquette de t dépend de
    toute la séquence fournie. Appelé sur `x[:i+1]` et lu en i, il reste causal ;
    appelé sur toute la série puis lu en i, il ne l'est pas. `hmm_states_causal`
    ci-dessous ne fait que le premier usage, et `hmm_states_leaky` que le second,
    exprès, pour que l'écart soit mesurable.
    """
    k = len(model["mu"])
    logB = _gauss_logpdf(x, model["mu"], model["sd"])
    logA = np.log(np.maximum(model["A"], 1e-300))
    delta = np.log(np.maximum(model["pi"], 1e-300)) + logB[0]
    psi = np.zeros((len(x), k), dtype=np.int64)
    for t in range(1, len(x)):
        m = delta[:, None] + logA
        psi[t] = np.argmax(m, axis=0)
        delta = m.max(axis=0) + logB[t]
    path = np.zeros(len(x), dtype=np.int64)
    path[-1] = int(np.argmax(delta))
    for t in range(len(x) - 2, -1, -1):
        path[t] = psi[t + 1, path[t + 1]]
    return path


def hmm_states_leaky(rets: np.ndarray, k: int = N_STATES) -> np.ndarray:
    """LE PIÈGE, reproduit exprès. Ajuste sur tout l'échantillon, étiquette le
    même échantillon. Les frontières d'état connaissent toute l'histoire.

    `docs/sources/aipathways/SYNTHESE.md` R7 classe ce défaut en rejet. Il est
    reproduit ici pour une seule raison : chiffrer ce qu'il rapporte
    artificiellement. Il n'est jamais présenté comme un résultat.
    """
    x = np.nan_to_num(rets, nan=0.0)
    model = fit_gaussian_hmm(x, k)
    return hmm_viterbi(x, model)


def hmm_states_causal(rets: np.ndarray, k: int = N_STATES, *,
                      min_bars: int = 500, refit_every: int = 60) -> np.ndarray:
    """Version honnête : réajustement en fenêtre étendue, étiquetage en avant.

    À la barre i, le modèle utilisé a été ajusté sur `rets[:m]` avec
    `m <= i`, et l'étiquette de i vient d'un décodage sur `rets[:i+1]`
    uniquement. Aucune information postérieure à i n'intervient.

    `refit_every` est un compromis assumé de coût : réajuster à chaque barre
    coûterait ~2 800 exécutions de Baum-Welch par instrument. Réajuster tous les
    60 jours ouvrés (~3 mois) est ce que ferait un praticien, et c'est
    CONSERVATEUR au sens de R1 — le modèle est en retard sur les données, jamais
    en avance.

    Le maillage de réajustement est ancré sur la barre 0, pour la même raison
    que la grille de transitions (point 1 du docstring de module).
    """
    n = len(rets)
    x = np.nan_to_num(rets, nan=0.0)
    out = np.full(n, UNDEF, dtype=np.int64)
    if n <= min_bars:
        return out

    model = None
    last_fit = -1
    for i in range(min_bars, n):
        if last_fit < 0 or (i - last_fit) >= refit_every:
            try:
                model = fit_gaussian_hmm(x[:i], k)
                last_fit = i
            except ValueError:
                continue
        if model is None:
            continue
        # Décodage sur [0, i] : l'étiquette lue est la dernière du chemin.
        out[i] = int(hmm_viterbi(x[:i + 1], model)[-1])
    return out


def hmm_states_causal_fast(rets: np.ndarray, k: int = N_STATES, *,
                           min_bars: int = 500, refit_every: int = 60
                           ) -> np.ndarray:
    """Même chose, mais l'étiquette est le filtre en avant (argmax de
    `P(état_i | r_0..r_i)`) au lieu d'un Viterbi complet relancé à chaque barre.

    Pourquoi cette variante existe : `hmm_states_causal` relance un Viterbi sur
    `[0, i]` pour CHAQUE i, soit un coût quadratique (~4 milliards d'opérations
    sur 2 800 barres). C'est inutilisable dans une grille. Le filtre en avant
    est strictement causal, se calcule en une passe, et c'est d'ailleurs ce
    qu'un système en production utiliserait : en direct, on n'a pas le futur
    pour lisser le passé.

    Les deux sont fournies ; l'écart entre elles est mesuré une fois et rapporté.
    """
    n = len(rets)
    x = np.nan_to_num(rets, nan=0.0)
    out = np.full(n, UNDEF, dtype=np.int64)
    if n <= min_bars:
        return out

    model, last_fit = None, -1
    alpha_ = None
    for i in range(n):
        if i >= min_bars and (last_fit < 0 or (i - last_fit) >= refit_every):
            try:
                model = fit_gaussian_hmm(x[:i], k)
                last_fit = i
                alpha_ = None            # le modèle a changé : on repart du filtre
            except ValueError:
                pass
        if model is None:
            continue
        logb = _gauss_logpdf(x[i:i + 1], model["mu"], model["sd"])[0]
        b = np.exp(logb - logb.max())
        if alpha_ is None:
            alpha_ = model["pi"] * b
        else:
            alpha_ = (alpha_ @ model["A"]) * b
        s = alpha_.sum()
        alpha_ = alpha_ / s if s > 0 else np.full(k, 1.0 / k)
        out[i] = int(np.argmax(alpha_))
    return out
