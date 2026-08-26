"""
WALK-FORWARD ANCRÉ
==================

Le harnais de validation commun. Une stratégie fournit ses signaux, ce module
cherche ses paramètres sur l'entraînement et mesure hors échantillon.

FENÊTRES
--------
    W1  train [0-60%]  test (60-70%]
    W2  train [0-70%]  test (70-80%]
    W3  train [0-80%]  test (80-90%]
    W4  train [0-90%]  test (90-100%]

L'entraînement part toujours de zéro (« ancré ») : c'est la situation réelle
d'un trader qui accumule de l'historique.

CRITÈRES
--------
STRICT      profitable sur train ET positif hors échantillon sur LES 4 fenêtres
TIER1       PnL train > 0, DD train < seuil, nombre de trades suffisant

Le critère STRICT s'est révélé fragile : sur ce projet, 4 des 5 paires validées
en avril l'ont cassé en juillet dès que 3 mois de données neuves sont arrivées —
sans perdre d'argent, simplement parce qu'UNE fenêtre passait en négatif.
Les deux critères sont donc rapportés côte à côte, jamais l'un seul.

TOUJOURS LU AVEC LE NOMBRE DE TRADES
------------------------------------
Un « strict pass » sur 19 trades a déjà été pris pour un succès ici. L'intervalle
de confiance à 95 % du taux de réussite allait de 27 % à 68 %, seuil de
rentabilité 28,6 % — donc indistinguable du hasard. Toute sortie affiche
l'effectif, et le nombre de configurations testées (une grille de 144 produit
~7 « réussites » par pur hasard).

BRAS TÉMOIN — ENTRÉE ALÉATOIRE
------------------------------
POURQUOI CE MODULE CONTIENT UN GÉNÉRATEUR ALÉATOIRE.

La convention `n_configs × 0,05` ci-dessus est une commodité, pas une mesure.
Elle suppose que chaque cellule de la grille est un test INDÉPENDANT au seuil de
5 %. C'est faux ici : deux cellules voisines (donchian 20 vs 40, tp_m 3 vs 4)
produisent presque les mêmes trades. Le nombre de tests réellement indépendants
est très inférieur au nombre de cellules, donc `n × 0,05` surestime le hasard —
et nous ne savons même pas de combien. Un verdict rendu sur cette base est
arbitraire dans un sens inconnu.

Le bras témoin remplace cette convention par une DISTRIBUTION NULLE MESURÉE.
Pour chaque configuration et chaque fenêtre, on tire N jeux d'entrées aléatoires
qui partagent EXACTEMENT le dispositif de risque de la stratégie :

    * même effectif de trades
    * même répartition long / short
    * mêmes distances de stop et de cible, exprimées en ATR (donc comparables
      d'un instrument et d'un régime de volatilité à l'autre)
    * mêmes heures de séance autorisées, si la stratégie en filtre

Seul le MOMENT de l'entrée change. Les tirages passent par le même moteur, sur
les mêmes barres, avec le même spread et les mêmes contraintes (position unique,
cooldown, circuit breaker). Ce qui reste de l'écart entre la stratégie et cette
distribution est ce que le choix du moment apporte — rien d'autre.

CE QUE CETTE MESURE ABSORBE ET QUE LA CONVENTION IGNORE
    * la dérive directionnelle de la période (un LONG aléatoire sur un marché
      qui monte gagne de l'argent sans aucune compétence) ;
    * le coût du spread, payé aux deux extrémités par les deux bras ;
    * la structure de volatilité propre à l'instrument ;
    * la corrélation entre cellules de la grille, puisqu'on ne compte plus des
      « réussites » sur une grille mais un percentile par configuration.

C'est la version calculable de la règle d'arrêt que `docs/METHODOLOGY.md` § 8
impose déjà en production (« halte si la performance glissante passe sous ce que
produirait une entrée aléatoire ») et que le harnais de recherche ne savait pas
évaluer.

EFFET SECONDAIRE ASSUMÉ — la barre monte, et c'est le but
    Sur un instrument en tendance, l'entrée aléatoire LONG est rentable par
    simple beta. Le témoin relève donc le seuil, parfois beaucoup. C'est
    exactement ce que le contrôle long/short de la méthodologie cherchait à la
    main. On le MESURE (`null_long_rpt` / `null_short_rpt` sont rapportés
    séparément) au lieu de le neutraliser.

REPRODUCTIBILITÉ
    Le générateur est semé explicitement (`seed`). Deux exécutions du même
    rapport donnent les mêmes percentiles, sinon le rapport n'est pas
    vérifiable. Le témoin est OPTIONNEL et désactivé par défaut : il n'entre
    dans aucun calcul de R, il ajoute une colonne de lecture.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.backtest.engine import BacktestResult, ExecutedTrade, InstrumentSpec
from core.backtest.engine import run as run_engine
from core.contracts.strategy import Side, Signal, StrategyModule

WINDOWS = [(0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.00)]

# Deux facons de constituer la fenetre d'entrainement :
#   ANCHORED  l'entrainement part toujours de 0 et grandit. Simule un trader qui
#             accumule de l'historique et ne jette rien.
#   ROLLING   l'entrainement est une fenetre de largeur fixe qui glisse. Simule
#             un trader qui s'adapte au regime recent et oublie l'ancien.
# Aucune n'est « la bonne » : elles repondent a des questions differentes.
# L'ancree dilue le regime recent dans l'ancien ; la glissante teste
# l'adaptation mais voit moins d'histoire par fenetre.
MODE_ANCHORED = "anchored"
MODE_ROLLING = "rolling"

# Graine par defaut du bras temoin. Explicite et figee : un percentile qui
# change d'une execution a l'autre n'est pas un resultat, c'est une anecdote.
CONTROL_SEED = 20260816
CONTROL_DRAWS = 200
ATR_PERIOD = 14


# ═════════════════════════════════════════════════════════════════════════════
# BRAS TÉMOIN — ENTRÉE ALÉATOIRE À DISPOSITIF DE RISQUE IDENTIQUE
# Voir l'en-tête du module pour le POURQUOI. Ci-dessous, le COMMENT.
# ═════════════════════════════════════════════════════════════════════════════

def _atr(bars: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    """ATR (moyenne mobile du True Range).

    Sert UNIQUEMENT d'unité de mesure pour rejouer les distances de stop et de
    cible de la stratégie. Exprimer ces distances en ATR plutôt qu'en prix est
    ce qui rend le témoin comparable : sur XAUUSD entre 2021 et 2026 le prix
    double, un stop « à 12 dollars » ne veut donc pas dire la même chose au
    début et à la fin de l'échantillon, alors qu'un stop « à 1,5 ATR » si.
    """
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    prev = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    return pd.Series(tr).rolling(period).mean().to_numpy()


@dataclass
class ControlArm:
    """Distribution nulle empirique d'une configuration.

    `draws_r` est le R hors échantillon de chaque tirage aléatoire, agrégé sur
    les mêmes fenêtres que la stratégie. `strategy_r` est le chiffre de la
    stratégie. Le percentile est la seule lecture qui compte.
    """
    n_draws: int
    strategy_r: float
    draws_r: np.ndarray
    n_trades_ref: int                 # effectif de la stratégie (la référence)
    n_trades_draws: np.ndarray        # effectif réellement exécuté par tirage
    long_frac: float                  # part de LONG, imposée identique
    draws_long_rpt: np.ndarray        # R/trade des entrées LONG aléatoires
    draws_short_rpt: np.ndarray       # R/trade des entrées SHORT aléatoires
    seed: int
    windows_covered: int = 0

    @property
    def percentile(self) -> float:
        """Rang de la stratégie dans la distribution nulle, en pourcentage.

        Les ex aequo comptent pour moitié : sans ça, une distribution nulle
        dégénérée (tous les tirages à 0 R) donnerait 0 ou 100 selon le sens de
        la comparaison, pour une information nulle.
        """
        d = self.draws_r
        return float(100.0 * (np.sum(d < self.strategy_r)
                              + 0.5 * np.sum(d == self.strategy_r)) / len(d))

    @property
    def null_median(self) -> float:
        return float(np.median(self.draws_r))

    @property
    def null_mean(self) -> float:
        return float(np.mean(self.draws_r))

    @property
    def null_p95(self) -> float:
        return float(np.percentile(self.draws_r, 95))

    @property
    def median_draw_trades(self) -> float:
        return float(np.median(self.n_trades_draws))

    @property
    def effectif_ok(self) -> bool:
        """L'effectif des tirages colle-t-il à celui de la stratégie ?

        Le moteur peut refuser un signal aléatoire (position deja ouverte,
        cooldown, circuit breaker). Tant que l'ecart reste sous 15 %, les deux
        bras comparent bien la meme quantite de risque pris. Au-dela, le
        percentile compare un effectif a un autre et ne veut plus rien dire :
        on le signale plutot que de le taire.
        """
        if not self.n_trades_ref:
            return False
        return abs(self.median_draw_trades - self.n_trades_ref) <= 0.15 * self.n_trades_ref

    @property
    def beta_directionnel(self) -> float:
        """Écart LONG − SHORT du R/trade aléatoire, en R.

        C'est la dérive directionnelle de la période, mesurée sans stratégie :
        positif = une entrée longue au hasard gagnait de l'argent sur ces
        barres. Là où ce chiffre est gros, tout « edge » majoritairement long
        doit d'abord battre ce beta avant de prétendre à quoi que ce soit.
        """
        lo = self.draws_long_rpt[np.isfinite(self.draws_long_rpt)]
        sh = self.draws_short_rpt[np.isfinite(self.draws_short_rpt)]
        if not len(lo) or not len(sh):
            return float("nan")
        return float(np.mean(lo) - np.mean(sh))

    def line(self) -> str:
        """Ligne de rapport, toujours accompagnée de l'effectif."""
        lo = self.draws_long_rpt[np.isfinite(self.draws_long_rpt)]
        sh = self.draws_short_rpt[np.isfinite(self.draws_short_rpt)]
        lt = f"{np.mean(lo):+.3f}" if len(lo) else "   n/a"
        st = f"{np.mean(sh):+.3f}" if len(sh) else "   n/a"
        warn = "" if self.effectif_ok else "  [EFFECTIF TÉMOIN ÉCARTÉ]"
        return (f"témoin aléatoire : percentile {self.percentile:>5.1f}  "
                f"| nul méd {self.null_median:>+7.2f} R, p95 {self.null_p95:>+7.2f} R "
                f"| {self.n_draws} tirages de {self.n_trades_ref} trades "
                f"(exéc. méd. {self.median_draw_trades:.0f}, "
                f"{100*self.long_frac:.0f} % long) "
                f"| R/trade aléatoire L {lt} / S {st}{warn}")


def _reference_profile(trades: list[ExecutedTrade],
                       atr_at: dict) -> Optional[dict]:
    """Extrait de trades réels le gabarit à rejouer au hasard.

    On ne copie PAS les prix : on copie la FORME du risque (sens, stop en ATR,
    cible en ATR, heure de séance). C'est ce qui garantit que le témoin ne
    diffère de la stratégie que par le moment de l'entrée.
    """
    sides, sl_atr, tp_atr, hours = [], [], [], []
    for t in trades:
        a = atr_at.get(pd.Timestamp(t.entry_time))
        if a is None or not np.isfinite(a) or a <= 0:
            continue                     # sans ATR, pas de gabarit — on jette
        sides.append(t.side)
        sl_atr.append(t.risk_distance / a)
        tp_atr.append(abs(t.target_price - t.entry_price) / a
                      if t.target_price is not None else np.nan)
        hours.append(pd.Timestamp(t.entry_time).hour)
    if not sides:
        return None
    return {"sides": sides, "sl_atr": np.array(sl_atr),
            "tp_atr": np.array(tp_atr), "hours": hours}


def _allowed_positions(idx: pd.DatetimeIndex, atr: np.ndarray,
                       profile: dict, n_bars: int) -> np.ndarray:
    """Barres où une entrée aléatoire a le droit de tomber.

    Filtre d'heures de séance : on ne le RECOPIE que si la stratégie en a
    visiblement un. Sur un petit effectif, le simple fait de n'avoir tradé qu'à
    certaines heures est un accident d'échantillonnage, pas une règle — imposer
    ce sous-ensemble au témoin lui donnerait un avantage ou un handicap que la
    stratégie n'a jamais eu. On n'applique donc la contrainte que si la
    stratégie couvre moins de 80 % des heures disponibles ET a assez de trades
    pour que ce soit un choix et non un hasard.
    """
    ok = np.isfinite(atr) & (atr > 0)
    ok[:ATR_PERIOD] = False
    ok[n_bars - 1:] = False              # il faut une barre suivante pour exécuter

    hod = idx.hour.to_numpy()
    available = set(np.unique(hod[ok]).tolist())
    used = set(profile["hours"])
    n_ref = len(profile["sides"])
    if available and len(used) < 0.8 * len(available) and n_ref >= 2 * len(available):
        ok &= np.isin(hod, sorted(used))
    return np.flatnonzero(ok)


def _draw_entry_bars(rng: np.random.Generator, allowed: np.ndarray, n: int) -> np.ndarray:
    """Tire n barres d'entrée réparties sur toute la fenêtre.

    Échantillonnage STRATIFIÉ : la fenêtre est découpée en n blocs de largeur
    égale et une barre est tirée au hasard dans chaque bloc. Deux raisons, et
    aucune n'est cosmétique :

      1. Un tirage uniforme pur agglutine les entrées ; le moteur en refuse
         alors la moitié (position déjà ouverte, cooldown) et le témoin se
         retrouve avec deux fois moins de trades que la stratégie. On ne
         comparerait plus la même quantité de risque pris.
      2. Les trades de la stratégie sont eux aussi étalés (le moteur lui
         interdit de se superposer). Un témoin aggloméré ne serait pas « la
         même stratégie sans le timing », il serait une autre stratégie.

    Le moment de l'entrée reste bien aléatoire à l'intérieur de son bloc.
    """
    m = len(allowed)
    if m == 0 or n <= 0:
        return np.empty(0, dtype=int)
    if n >= m:
        return allowed.copy()
    edges = np.linspace(0, m, n + 1).astype(int)
    picks = [rng.integers(edges[k], max(edges[k] + 1, edges[k + 1]))
             for k in range(n)]
    return allowed[np.clip(np.array(picks), 0, m - 1)]


def _random_signals(rng: np.random.Generator, idx: pd.DatetimeIndex,
                    close: np.ndarray, atr: np.ndarray, allowed: np.ndarray,
                    profile: dict, symbol: str) -> list[Signal]:
    """Un jeu d'entrées aléatoires au dispositif de risque identique.

    Les sens et les couples (stop, cible) sont PERMUTÉS, pas retirés d'une loi
    ajustée : le multi-ensemble est donc rigoureusement identique à celui de la
    stratégie. Même nombre de longs, mêmes distances, même R:R. Seule la date
    change.
    """
    n = len(profile["sides"])
    bars_at = _draw_entry_bars(rng, allowed, n)
    if not len(bars_at):
        return []

    sides = [profile["sides"][k] for k in rng.permutation(n)]
    # Stop et cible voyagent ENSEMBLE : les dissocier fabriquerait des R:R que
    # la stratégie n'a jamais pris.
    pair = rng.permutation(n)
    sl = profile["sl_atr"][pair]
    tp = profile["tp_atr"][pair]

    out: list[Signal] = []
    for k, j in enumerate(np.sort(bars_at)):
        a = float(atr[j])
        entry = float(close[j])
        long = sides[k] == Side.LONG
        dist = float(sl[k]) * a
        if dist <= 0:
            continue
        stop = entry - dist if long else entry + dist
        if stop == entry:
            continue                     # rien à risquer, rien à faire
        target = None
        if np.isfinite(tp[k]):
            td = float(tp[k]) * a
            target = entry + td if long else entry - td
        out.append(Signal(
            timestamp=idx[j], symbol=symbol,
            side=Side.LONG if long else Side.SHORT,
            entry=entry, stop=stop, target=target,
            reason="témoin — entrée aléatoire, dispositif de risque identique",
        ))
    return out


def _slice_draws(bars_slice: pd.DataFrame, spec: InstrumentSpec,
                 atr_slice: np.ndarray, profile: dict,
                 rng: np.random.Generator, draws: int,
                 engine_kwargs: Optional[dict] = None) -> dict:
    """Fait tourner `draws` jeux aléatoires sur UNE tranche de barres.

    La tranche est passée telle quelle au moteur commun (R9) : même exécution,
    même spread, mêmes contraintes que la stratégie. Un résiduel encore ouvert
    à la fin de la tranche est valorisé à sa dernière barre, exactement comme
    la tranche de test de la stratégie.

    `engine_kwargs` DOIT être celui de la stratégie comparée : un témoin qui
    garde ses positions indéfiniment face à une stratégie coupée à heure fixe
    (max_hold_bars) ne rejoue pas le même dispositif de risque, et le
    percentile perd son sens.
    """
    ek = engine_kwargs or {}
    idx = bars_slice.index
    close = bars_slice["close"].to_numpy(dtype=float)
    n_bars = len(bars_slice)
    allowed = _allowed_positions(idx, atr_slice, profile, n_bars)

    tot_r = np.zeros(draws)
    tot_n = np.zeros(draws, dtype=int)
    long_r = np.full(draws, np.nan)
    long_n = np.zeros(draws, dtype=int)
    short_r = np.full(draws, np.nan)
    short_n = np.zeros(draws, dtype=int)

    for d in range(draws):
        sigs = _random_signals(rng, idx, close, atr_slice, allowed,
                               profile, spec.symbol)
        res = run_engine(sigs, bars_slice, spec, **ek) if sigs else BacktestResult()
        tot_r[d] = res.total_r
        tot_n[d] = res.n_trades
        lo = [t.pnl_r for t in res.trades if t.side == Side.LONG]
        sh = [t.pnl_r for t in res.trades if t.side == Side.SHORT]
        long_r[d], long_n[d] = (float(np.sum(lo)) if lo else np.nan), len(lo)
        short_r[d], short_n[d] = (float(np.sum(sh)) if sh else np.nan), len(sh)

    return {"r": tot_r, "n": tot_n,
            "long_r": long_r, "long_n": long_n,
            "short_r": short_r, "short_n": short_n}


def control_arm(bars: pd.DataFrame, spec: InstrumentSpec,
                ref_trades: list[ExecutedTrade], strategy_r: float,
                *, draws: int = CONTROL_DRAWS, seed: int = CONTROL_SEED,
                atr: Optional[np.ndarray] = None,
                engine_kwargs: Optional[dict] = None) -> Optional[ControlArm]:
    """Distribution nulle d'UNE tranche, face aux trades observés.

    Retourne None si les trades de référence ne permettent pas de construire un
    gabarit — pas de résultat sans effectif. C'est la même discipline que le
    reste du harnais : mieux vaut une case vide qu'un percentile inventé sur
    trois trades.
    """
    if not ref_trades or len(bars) <= ATR_PERIOD + 2:
        return None
    a = _atr(bars) if atr is None else atr
    atr_at = {ts: a[i] for i, ts in enumerate(bars.index)}
    profile = _reference_profile(ref_trades, atr_at)
    if profile is None:
        return None

    rng = np.random.default_rng(seed)
    agg = _slice_draws(bars, spec, a, profile, rng, draws, engine_kwargs=engine_kwargs)
    n_ref = len(profile["sides"])
    with np.errstate(invalid="ignore", divide="ignore"):
        lrpt = agg["long_r"] / np.where(agg["long_n"] > 0, agg["long_n"], np.nan)
        srpt = agg["short_r"] / np.where(agg["short_n"] > 0, agg["short_n"], np.nan)
    return ControlArm(
        n_draws=draws, strategy_r=strategy_r, draws_r=agg["r"],
        n_trades_ref=n_ref, n_trades_draws=agg["n"],
        long_frac=sum(1 for s in profile["sides"] if s == Side.LONG) / n_ref,
        draws_long_rpt=lrpt, draws_short_rpt=srpt, seed=seed, windows_covered=1,
    )


@dataclass
class WindowResult:
    index: int
    train_end: int
    test_end: int
    train: BacktestResult
    test: BacktestResult          # tranche de test seule

    @property
    def train_r(self) -> float:
        return self.train.total_r

    @property
    def oos_r(self) -> float:
        return self.test.total_r


@dataclass
class ConfigResult:
    label: str
    params: dict
    windows: list[WindowResult] = field(default_factory=list)
    full_sample: Optional[BacktestResult] = None   # l'illusion : tout l'historique
    control: Optional["ControlArm"] = None         # distribution nulle, si calculée

    @property
    def oos_series(self) -> list[float]:
        return [w.oos_r for w in self.windows]

    @property
    def avg_oos(self) -> float:
        s = self.oos_series
        return float(np.mean(s)) if s else 0.0

    @property
    def total_test_trades(self) -> int:
        return sum(w.test.n_trades for w in self.windows)

    @property
    def illusion_r(self) -> float:
        """Ce qu'un backtest naif afficherait : optimise ET mesure sur tout
        l'historique. C'est le chiffre que montrent les captures d'ecran."""
        return self.full_sample.total_r if self.full_sample else 0.0

    @property
    def honest_r(self) -> float:
        """La somme des tranches hors echantillon uniquement."""
        return float(sum(self.oos_series))

    @property
    def degradation_pct(self) -> Optional[float]:
        """Part du profit apparent qui disparait une fois l'illusion retiree.

        N'a de sens QUE si le plein echantillon montre un gain : on ne peut pas
        « perdre » un rendement qui n'a jamais existe. Une config negative des
        le depart retourne None — le recit de l'illusion ne s'applique pas.
        """
        ill = self.illusion_r
        if ill <= 1e-9:
            return None
        return 100.0 * (ill - self.honest_r) / ill

    @property
    def strict_pass(self) -> bool:
        """Profitable sur train ET OOS positif sur les 4 fenêtres."""
        if len(self.windows) < len(WINDOWS):
            return False
        return all(w.train_r > 0 and w.oos_r > 0 for w in self.windows)

    def tier1_pass(self, min_trades: int, max_dd_r: float) -> bool:
        if len(self.windows) < len(WINDOWS):
            return False
        last = self.windows[-1].train
        return (last.total_r > 0
                and last.n_trades >= min_trades
                and last.max_drawdown_r <= max_dd_r)


@dataclass
class WalkForwardReport:
    strategy_id: str
    symbol: str
    bars: int
    n_configs: int
    results: list[ConfigResult]
    elapsed_s: float
    min_trades: int
    max_dd_r: float
    mode: str = MODE_ANCHORED

    def strict(self) -> list[ConfigResult]:
        return sorted([r for r in self.results if r.strict_pass],
                      key=lambda r: -r.avg_oos)

    def tier1(self) -> list[ConfigResult]:
        return sorted([r for r in self.results if r.tier1_pass(self.min_trades, self.max_dd_r)],
                      key=lambda r: -r.avg_oos)

    def render(self, top: int = 8) -> str:
        L = []
        L.append("=" * 96)
        L.append(f"WALK-FORWARD — {self.strategy_id} / {self.symbol}")
        L.append("=" * 96)
        L.append(f"{self.bars} barres · {self.n_configs} configurations · {self.elapsed_s:.0f}s")
        L.append(f"Tier 1 : PnL train > 0, ≥ {self.min_trades} trades, DD ≤ {self.max_dd_r:.1f} R")
        L.append("")

        # Une grille produit mécaniquement des réussites par hasard.
        # ATTENTION : cette attente suppose des cellules INDÉPENDANTES. Elles ne
        # le sont pas — deux configurations voisines produisent presque les
        # mêmes trades. Le chiffre est donc une borne haute de commodité, pas
        # une mesure. Le bras témoin ci-dessous est la version mesurée.
        chance = self.n_configs * 0.05
        s, t = self.strict(), self.tier1()
        L.append(f"STRICT : {len(s)}/{self.n_configs}   "
                 f"(≈{chance:.0f} attendues par pur hasard si l'edge est nul —")
        L.append("          convention analytique : suppose les cellules "
                 "indépendantes, elles ne le sont pas)")
        L.append(f"TIER 1 : {len(t)}/{self.n_configs}")
        L.append("")

        def table(title, rows):
            L.append(f"--- {title} ---")
            if not rows:
                L.append("    aucune")
                L.append("")
                return
            L.append(f"    {'configuration':<44} {'W1':>7} {'W2':>7} {'W3':>7} {'W4':>7} "
                     f"{'moy':>7} {'trades':>7}")
            L.append("    " + "-" * 88)
            for r in rows[:top]:
                oos = " ".join(f"{v:>+7.2f}" for v in r.oos_series)
                flag = "  [MINCE]" if r.total_test_trades < self.min_trades else ""
                L.append(f"    {r.label:<44} {oos} {r.avg_oos:>+7.2f} "
                         f"{r.total_test_trades:>7}{flag}")
                if r.control is not None:
                    L.append(f"        {r.control.line()}")
            L.append("")

        table("STRICT (4/4 fenêtres)", s)
        table("TIER 1", t)

        if not s and not t:
            near = sorted(self.results, key=lambda r: -r.avg_oos)[:3]
            L.append("--- meilleurs échecs (pour information) ---")
            for r in near:
                oos = " ".join(f"{v:>+7.2f}" for v in r.oos_series)
                L.append(f"    {r.label:<44} {oos} {r.avg_oos:>+7.2f} "
                         f"{r.total_test_trades:>7}")
                if r.control is not None:
                    L.append(f"        {r.control.line()}")
            L.append("")

        # ── L'ILLUSION IN-SAMPLE ────────────────────────────────────────
        by_illusion = sorted([r for r in self.results if r.illusion_r > 0],
                             key=lambda r: -r.illusion_r)
        if by_illusion:
            L.append("--- L'ILLUSION IN-SAMPLE ---")
            L.append("    Ce qu'un backtest naïf afficherait (optimisé ET mesuré sur")
            L.append("    tout l'historique) face au résultat hors échantillon.")
            L.append("")
            L.append(f"    {'meilleure config plein échantillon':<44} {'illusion':>10} "
                     f"{'honnête':>10} {'perdu':>8}")
            L.append("    " + "-" * 76)
            for r in by_illusion[:3]:
                deg = r.degradation_pct
                dtxt = f"{deg:>7.0f} %" if deg is not None else "      —"

                L.append(f"    {r.label:<44} {r.illusion_r:>+10.2f} "
                         f"{r.honest_r:>+10.2f} {dtxt}")
            top_deg = by_illusion[0].degradation_pct
            if top_deg is not None:
                L.append("")
                L.append(f"    => {top_deg:.0f} % du rendement affiché par la meilleure config")
                L.append("       disparaît une fois l'optimisation retirée.")
            L.append("")

        # ── LE BRAS TÉMOIN ──────────────────────────────────────────────
        armed = [r for r in self.results if r.control is not None]
        if armed:
            c0 = armed[0].control
            L.append("--- BRAS TÉMOIN : ENTRÉE ALÉATOIRE ---")
            L.append("    Chaque configuration affichée ci-dessus est comparée à "
                     f"{c0.n_draws} jeux")
            L.append("    d'entrées TIRÉES AU HASARD ayant le même effectif, la même")
            L.append("    répartition long/short, les mêmes stops et cibles en ATR et")
            L.append("    les mêmes heures de séance. Seul le moment de l'entrée change.")
            L.append(f"    Graine {c0.seed} — le rapport est rejouable à l'identique.")
            L.append("")
            L.append("    Percentile 50 = la stratégie fait ce que ferait un tirage au")
            L.append("    sort. Il faut dépasser 95 pour parler d'un edge, et encore :")
            L.append("    les configurations affichées ont été SÉLECTIONNÉES sur ces")
            L.append("    mêmes données, donc leur percentile est optimiste.")
            L.append("")
            betas = [r.control.beta_directionnel for r in armed
                     if np.isfinite(r.control.beta_directionnel)]
            if betas:
                b = float(np.median(betas))
                L.append(f"    Beta directionnel mesuré : {b:+.3f} R/trade d'écart entre")
                L.append("    une entrée LONG au hasard et une entrée SHORT au hasard.")
                if b > 0.05:
                    L.append("    => la période MONTE. Une stratégie majoritairement longue")
                    L.append("       doit d'abord battre ce beta ; le témoin l'exige, la")
                    L.append("       convention n×0,05 ne le voyait pas.")
                elif b < -0.05:
                    L.append("    => la période BAISSE. Symétrique du cas précédent pour")
                    L.append("       une stratégie majoritairement short.")
                else:
                    L.append("    => pas de dérive directionnelle exploitable sur la période.")
            L.append("")

        L.append(f"Mode : {self.mode}"
                 + ("  (entraînement ancré à l'origine)" if self.mode == MODE_ANCHORED
                    else "  (fenêtre d'entraînement glissante)"))
        L.append("Résultats en R (multiples du risque) — indépendants du sizing.")
        L.append("[MINCE] = effectif insuffisant : un « pass » n'y est pas une preuve.")
        if armed:
            L.append("[EFFECTIF TÉMOIN ÉCARTÉ] = le moteur a refusé trop de signaux")
            L.append("    aléatoires ; les deux bras ne comparent plus le même nombre")
            L.append("    de trades et le percentile est à lire avec méfiance.")
        return "\n".join(L)


def _grid(param_grid: dict[str, list]) -> list[dict]:
    if not param_grid:
        return [{}]
    keys = sorted(param_grid)
    return [dict(zip(keys, combo))
            for combo in itertools.product(*(param_grid[k] for k in keys))]


def _label(params: dict) -> str:
    return "_".join(f"{k}{params[k]}" for k in sorted(params)) or "default"


def run_walk_forward(
    strategy: StrategyModule,
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    *,
    param_grid: Optional[dict] = None,
    min_trades: int = 20,
    max_dd_r: float = 12.0,
    mode: str = MODE_ANCHORED,
    train_frac: float = 0.50,
    verbose: bool = True,
    engine_kwargs: Optional[dict] = None,
) -> WalkForwardReport:
    """Explore la grille sur chaque fenêtre ancrée.

    Le précalcul est mis en cache par sous-ensemble de paramètres qui influence
    les indicateurs : c'est le poste coûteux (S/R, swings), inutile de le
    refaire pour chaque cellule de grille.

    `engine_kwargs` est transmis tel quel à `run_engine` (max_hold_bars,
    cooldown_bars, cb_losses…). Il manquait, et son absence a bloqué deux
    dossiers de suite : s91 (§7.1) puis la reproduction du range breakout de
    session, dont la SORTIE À HEURE FIXE est la moitié du contrat — sans
    max_hold_bars, le harnais testait une autre stratégie que celle annoncée,
    en silence. Un harnais qui ne sait pas exprimer la règle de sortie ne
    mesure pas la stratégie, il mesure son propre défaut.
    """
    t0 = time.time()
    ek = engine_kwargs or {}
    m = strategy.manifest()
    grid = _grid(param_grid if param_grid is not None else m.param_grid)
    n = len(bars)

    # Bornes de fenetre. En ancre, l'entrainement part de 0 ; en glissant, il
    # demarre `train_frac` de l'historique avant la fin de l'entrainement.
    bounds = []
    for a, b in WINDOWS:
        tr_end = int(n * a)
        te_end = int(n * b) if b < 1.0 else n
        tr_start = 0 if mode == MODE_ANCHORED else max(0, tr_end - int(n * train_frac))
        bounds.append((tr_start, tr_end, te_end))

    cache: dict[tuple, Any] = {}
    results: list[ConfigResult] = []

    for gi, params in enumerate(grid):
        full = dict(strategy.params)
        full.update(params)

        key = tuple(sorted(full.items()))
        if key not in cache:
            cache[key] = strategy.precompute(bars, full)
        data = cache[key]

        cr = ConfigResult(label=_label(params), params=full)

        # L'ILLUSION : optimise ET mesure sur tout l'historique. C'est le chiffre
        # qu'affiche un backtest naif, celui des captures d'ecran a 300 %.
        cr.full_sample = run_engine(
            strategy.generate_signals(data, full, n), bars, spec, end_idx=n, **ek)

        for wi, (tr_start, tr_end, te_end) in enumerate(bounds):
            sig_tr = strategy.generate_signals(data, full, tr_end)
            sig_te = strategy.generate_signals(data, full, te_end)

            # En mode glissant, l'entrainement ignore ce qui precede la fenetre.
            if tr_start > 0:
                win_start = bars.index[tr_start]     # ne PAS nommer t0 : le chrono l'utilise
                sig_tr = [x for x in sig_tr if pd.Timestamp(x.timestamp) >= win_start]

            res_tr = run_engine(sig_tr, bars, spec, end_idx=tr_end, **ek)
            res_te_full = run_engine(sig_te, bars, spec, end_idx=te_end, **ek)

            # Tranche de test seule = trades entrés après la fin du train.
            cut = bars.index[tr_end - 1]
            slice_only = BacktestResult(
                trades=[t for t in res_te_full.trades if t.entry_time > cut]
            )
            cr.windows.append(WindowResult(wi + 1, tr_end, te_end, res_tr, slice_only))

        results.append(cr)
        if verbose and (gi + 1) % max(1, len(grid) // 10) == 0:
            print(f"    {gi+1}/{len(grid)} configurations", flush=True)

    return WalkForwardReport(
        strategy_id=strategy.STRATEGY_ID, symbol=spec.symbol, bars=n,
        n_configs=len(grid), results=results, elapsed_s=time.time() - t0,
        min_trades=min_trades, max_dd_r=max_dd_r, mode=mode,
    )


def attach_control_arm(
    report: WalkForwardReport,
    bars: pd.DataFrame,
    spec: InstrumentSpec,
    *,
    draws: int = CONTROL_DRAWS,
    seed: int = CONTROL_SEED,
    configs: Optional[list[ConfigResult]] = None,
    top: int = 8,
    verbose: bool = True,
    engine_kwargs: Optional[dict] = None,
) -> WalkForwardReport:
    """Calcule la distribution nulle des configurations affichées.

    N'ALTÈRE AUCUN R. Le walk-forward est déjà fini quand cette fonction est
    appelée ; elle ne fait qu'ajouter une lecture. C'est délibéré : un témoin
    qui modifierait les chiffres qu'il est censé juger serait inutilisable, et
    la comparaison aux dossiers archivés deviendrait impossible.

    On ne le calcule QUE pour les configurations effectivement affichées : le
    coût est `draws × 4 fenêtres` exécutions de moteur par configuration, ce qui
    est hors de question sur une grille de 128 cellules — et sans intérêt, la
    question ne se pose que pour les candidates qu'on regarde.

    Chaque tirage est agrégé sur les 4 fenêtres AVEC LE MÊME INDICE : le tirage
    d numéro 7 de W1 s'additionne au tirage 7 de W2, etc. On obtient ainsi une
    distribution de « R hors échantillon total » directement comparable au
    `honest_r` de la stratégie, et non une somme de médianes qui n'aurait aucun
    sens statistique.
    """
    if configs is None:
        seen, configs = set(), []
        pool = report.strict()[:top] + report.tier1()[:top]
        if not pool:
            pool = sorted(report.results, key=lambda r: -r.avg_oos)[:3]
        for r in pool:
            if id(r) not in seen:
                seen.add(id(r))
                configs.append(r)

    atr_full = _atr(bars)
    for ci, cr in enumerate(configs):
        tot_r = np.zeros(draws)
        tot_n = np.zeros(draws, dtype=int)
        long_r = np.zeros(draws)
        long_n = np.zeros(draws, dtype=int)
        short_r = np.zeros(draws)
        short_n = np.zeros(draws, dtype=int)
        n_ref = n_long = covered = 0

        for w in cr.windows:
            refs = w.test.trades
            if not refs:
                continue                 # fenêtre sans trade : rien à comparer
            sl = bars.iloc[w.train_end:w.test_end]
            atr_sl = atr_full[w.train_end:w.test_end]
            if len(sl) <= ATR_PERIOD + 2:
                continue
            profile = _reference_profile(
                refs, {ts: atr_sl[i] for i, ts in enumerate(sl.index)})
            if profile is None:
                continue

            # Graine dérivée de (graine de base, configuration, fenêtre) : deux
            # fenêtres ne partagent pas la même suite aléatoire, et le rapport
            # entier est rejouable à l'identique.
            rng = np.random.default_rng(seed + 1000 * ci + w.index)
            agg = _slice_draws(sl, spec, atr_sl, profile, rng, draws, engine_kwargs=engine_kwargs)
            tot_r += agg["r"]
            tot_n += agg["n"]
            long_r += np.nan_to_num(agg["long_r"])
            long_n += agg["long_n"]
            short_r += np.nan_to_num(agg["short_r"])
            short_n += agg["short_n"]
            n_ref += len(profile["sides"])
            n_long += sum(1 for s in profile["sides"] if s == Side.LONG)
            covered += 1

        if not covered or not n_ref:
            cr.control = None            # pas de résultat sans effectif
            continue

        with np.errstate(invalid="ignore", divide="ignore"):
            lrpt = long_r / np.where(long_n > 0, long_n, np.nan)
            srpt = short_r / np.where(short_n > 0, short_n, np.nan)
        cr.control = ControlArm(
            n_draws=draws, strategy_r=cr.honest_r, draws_r=tot_r,
            n_trades_ref=n_ref, n_trades_draws=tot_n,
            long_frac=n_long / n_ref, draws_long_rpt=lrpt, draws_short_rpt=srpt,
            seed=seed, windows_covered=covered,
        )
        if verbose:
            print(f"    témoin {ci+1}/{len(configs)} — {cr.label} : "
                  f"percentile {cr.control.percentile:.1f}", flush=True)
    return report
