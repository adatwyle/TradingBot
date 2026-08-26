"""
HARNAIS D'ÉVALUATION — s07_ionita_gaussian
==========================================

R9 ET CE QUE CE FICHIER FAIT (ET NE FAIT PAS)
----------------------------------------------
R9 interdit à une stratégie d'écrire sa propre boucle de backtest. Elle n'en
écrit pas : toute simulation passe par `core.backtest.allocation_engine.
run_allocation`, sans exception. Ce fichier ORCHESTRE — il charge les barres,
construit les specs, découpe les fenêtres et appelle le moteur avec des
`end_idx`. Le contrat d'allocation prévoit explicitement ce paramètre
(« Même contrat `end_idx` que le chemin épisodique »).

Cette orchestration existe parce que `core/backtest/anchored_wf.py` est câblé
sur le contrat ÉPISODIQUE : il appelle `strategy.generate_signals()` et
`run_engine()`, et raisonne en R par trade. Il ne sait pas évaluer une courbe
d'equity. Deuxième lacune de `core/` signalée par cette stratégie, non corrigée
(interdiction de toucher à `core/`).

Les fenêtres sont IMPORTÉES de `core.backtest.anchored_wf.WINDOWS`, pas
redéfinies : les découpages doivent rester comparables entre stratégies.

VÉRIFICATION D'ACCORD AVEC LE MOTEUR
-------------------------------------
Pour mesurer une tranche hors échantillon, il faut un buy & hold restreint à
cette tranche — que `run_allocation` ne rend pas (ses benchmarks portent sur
[0, end_idx)). On le reconstruit donc à partir des ouvertures, et
`_assert_benchmark_agreement()` vérifie que cette reconstruction reproduit
EXACTEMENT le benchmark du moteur sur [0, T). Tant que l'accord tient, la
dérivation par tranche est fondée sur le même calcul que core/, pas sur un
calcul parallèle.

USAGE
-----
    python -m strategies.s07_ionita_gaussian.run_backtest
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, replace
from itertools import product
from typing import Optional

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.allocation_engine import run_allocation
from core.backtest.anchored_wf import WINDOWS
from core.backtest.engine import InstrumentSpec
from core.data.source import load_bars
from strategies.s07_ionita_gaussian.strategy import (
    Strategy, short_symbol, is_short_symbol, base_symbol,
)

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERS
# ─────────────────────────────────────────────────────────────────────────────
# Le « Trend Radar » n'est pas reproductible : l'univers est FIXE et déclaré.
# On liste ici tout ce que le broker offre en crypto — deux lignes. Ce n'est pas
# un choix, c'est l'inventaire complet (cf. research/ANALYSIS.md §univers).
UNIVERSE_CRYPTO = ["BTCUSD", "ETHUSD"]

# Correspondance nom interne -> symbole broker.
#
# LACUNE DE core/ SIGNALÉE : `core/data/instruments.py` déclare bien "BTCUSD"
# dans son catalogue, mais `core/data/source.py::SYMBOL_MAP` ne le traduit pas
# vers "#BTCUSD". Conséquence mesurée :
#     load_bars("BTCUSD", "D1")  -> None      (échec silencieux)
#     load_bars("#BTCUSD", "D1") -> 3248 barres
# Toute stratégie qui ferait confiance au catalogue obtiendrait None sans
# message. Non corrigé ici (interdiction de modifier core/), contourné en
# passant le symbole broker.
BROKER = {"BTCUSD": "#BTCUSD", "ETHUSD": "#ETHUSD"}

# ─────────────────────────────────────────────────────────────────────────────
# COÛTS — mesurés sur MT5, pas devinés, pas repris d'un catalogue périmé
# ─────────────────────────────────────────────────────────────────────────────
# `core/data/instruments.py` donne BTCUSD spread_pips=30 (pip=1.0), soit 30 USD.
# Le spread médian réellement relevé sur les barres H1 depuis 2024 est de 83
# points = 83 USD, sur un prix médian de 76 733 -> 0,108 % du prix. Le catalogue
# a été calibré à une époque où BTC valait bien moins ; l'utiliser tel quel
# sous-estimerait le coût d'un facteur ~2,8. On utilise la mesure.
#
# `ETHUSD` est tout simplement absent du catalogue. Le renseigner ici n'est pas
# « deviner dans la stratégie » (ce que `get_spec` interdit à juste titre) :
# c'est reporter une mesure faite sur l'instrument réel, et la tracer.
#
# Slippage : non mesurable sur des barres. Retenu à ~10 % du spread, ordre de
# grandeur cohérent avec docs/METHODOLOGY.md (« davantage sur indices CFD »).
# Les résultats restent optimistes d'un montant inconnu — c'est dit.
MEASURED = {
    #              pip    spread_pts  slip_pts   prix médian (pour info)
    "BTCUSD": dict(pip=1.0, spread_pips=83.0, slippage_pips=8.0, px=76733.0),
    "ETHUSD": dict(pip=0.1, spread_pips=46.0, slippage_pips=5.0, px=2720.2),
}

# Coût de portage (swap). MT5 : swap_mode=3 (CURRENCY_MARGIN), donc un montant
# en devise par lot et par jour, contract_size=1.
#   BTCUSD  swap_long = -29,7151 USD/jour  sur un prix médian de 76 733
#           -> 0,0387 %/jour -> ~14,1 %/an (≈18 %/an avec le rollover triple)
#   ETHUSD  swap_long =  -1,0712 USD/jour  sur 2 720,2  -> 0,0394 %/jour
#
# `allocation_engine` ne modélise PAS le swap : il ne facture que le coût de
# bord sur le turnover. Ce coût est donc chiffré séparément (`carry_drag`) et
# rapporté à côté des résultats bruts, jamais fondu dedans.
SWAP_ANNUAL_PCT = {"BTCUSD": 14.1, "ETHUSD": 14.4}


def make_specs(symbols: list[str], cost_mult: float = 1.0) -> dict[str, InstrumentSpec]:
    """Specs pour les instruments réels ET leurs jambes short synthétiques.

    `cost_mult` sert l'ablation du spread (`docs/METHODOLOGY.md` §5.1) : 0 pour
    le coût nul, 1 pour le nominal, 2 pour le pessimiste.

    LIMITE CONNUE DU MODÈLE DE COÛT, mesurée et déclarée
    -----------------------------------------------------
    `InstrumentSpec` porte un spread FIXE EN POINTS, et le moteur en déduit un
    coût relatif `edge / open`. Sur un actif dont le prix varie d'un facteur 40
    au cours de l'échantillon, ce coût relatif dérive dans les mêmes proportions.
    Mesuré sur notre BTCUSD :

        prix 6 297 (nov. 2018) -> coût 0,786 % par unité échangée
        prix 36 397 (médiane)  -> coût 0,136 %
        prix 125 098 (sommet)  -> coût 0,040 %

    Le spread réellement relevé aujourd'hui vaut 0,108 % du prix. Le modèle est
    donc à peu près juste au milieu de l'échantillon, PESSIMISTE dans sa
    première moitié, un peu optimiste à la fin. Le biais joue contre la
    stratégie sur la période ancienne — c'est le sens conservateur.

    On ne « corrige » pas en calibrant sur la médiane des prix : ce serait une
    statistique de tout l'échantillon, donc une violation de R1. C'est
    exactement le bug qu'`allocation_engine` documente avoir eu et corrigé
    (« le coût d'une barre de 2021 changeait selon qu'on arrêtait le backtest en
    2022 ou en 2024 »). L'ablation de coût mesure l'enjeu à la place.
    """
    specs: dict[str, InstrumentSpec] = {}
    for s in symbols:
        if is_short_symbol(s):
            continue
        m = MEASURED[s]
        specs[s] = InstrumentSpec(
            symbol=s, pip=m["pip"], spread_pips=m["spread_pips"] * cost_mult,
            max_spread_pips=max(m["spread_pips"] * 3.0, 1e-9),
            pip_value_per_lot=1.0, slippage_pips=m["slippage_pips"] * cost_mult,
        )

    # ── Jambes short : coût de bord mis à ZÉRO, délibérément ────────────────
    # La série synthétique part de 100 et termine à 0,47 (BTC) / 0,06 (ETH) —
    # un short maintenu depuis 2018 aurait effectivement tout perdu. Or le
    # moteur calcule `cost_rate = edge / open` : sur une série qui tend vers
    # zéro, le coût relatif explose. Mesuré avec un `pip` calibré sur le niveau
    # de départ : jusqu'à 82 % par rotation sur ETH, ce qui produisait une
    # equity NÉGATIVE — un résultat vide de sens.
    #
    # Les deux échappatoires sont mauvaises :
    #   - calibrer `pip` sur la médiane de la série -> statistique de tout
    #     l'échantillon -> violation de R1, refusée.
    #   - calibrer sur le niveau de départ -> explosion, refusée.
    #
    # On facture donc ZÉRO coût de bord sur les jambes short, et on le dit. Ce
    # choix AVANTAGE les shorts. Il est retenu parce que la conclusion qu'il
    # permet est conservatrice dans le seul sens utile : si les shorts
    # n'apportent rien alors même qu'ils sont gratuits, ils n'apporteront rien
    # en les faisant payer. Si à l'inverse ils apportaient beaucoup, le
    # résultat serait à considérer comme NON MESURÉ, pas comme acquis.
    for s in [x for x in symbols if is_short_symbol(x)]:
        specs[s] = InstrumentSpec(
            symbol=s, pip=1.0, spread_pips=0.0, max_spread_pips=1e9,
            pip_value_per_lot=1.0, slippage_pips=0.0,
        )
    return specs


# ─────────────────────────────────────────────────────────────────────────────
# DONNÉES
# ─────────────────────────────────────────────────────────────────────────────
def load_universe(symbols: list[str], days: int = 365 * 12) -> dict[str, pd.DataFrame]:
    """Charge les barres D1 et les aligne sur l'index commun.

    L'alignement est une exigence de `run_allocation`, qui prend l'index du
    premier symbole comme référence. Un désalignement produirait des rendements
    calculés sur des dates qui ne se correspondent pas — silencieusement.
    """
    raw: dict[str, pd.DataFrame] = {}
    for s in symbols:
        df = load_bars(BROKER.get(s, s), "D1", days=days)
        if df is None or len(df) < 500:
            raise RuntimeError(
                f"{s} ({BROKER.get(s, s)}) : {0 if df is None else len(df)} barres. "
                f"Insuffisant.")
        raw[s] = df

    common = None
    for df in raw.values():
        common = df.index if common is None else common.intersection(df.index)
    common = common.sort_values()
    return {s: df.loc[common, ["open", "high", "low", "close"]].astype(float)
            for s, df in raw.items()}


def build_short_series(df: pd.DataFrame) -> pd.DataFrame:
    """Série synthétique dont le rendement open->open est l'opposé du réel.

    `open_s[i] = open_s[i-1] . (1 - r[i])` avec `r[i]` le rendement open->open
    de la série réelle entre i-1 et i. Le moteur, qui calcule `pct_change()` sur
    les ouvertures, obtient alors exactement `-r[i]` : c'est la définition d'une
    position courte non financée, hors coût de portage.

    Causal : `open_s[i]` ne dépend que de barres d'indice <= i. Vérifié par
    troncature dans `validate_r1.check_synthetic_shorts()`, pas supposé ici.

    Le financement du short n'est PAS inclus (le moteur ne sait pas le porter) ;
    il est chiffré à part comme celui des longs.
    """
    r = df["open"].pct_change().fillna(0.0).to_numpy()
    synth_open = 100.0 * np.cumprod(1.0 - r)
    # high/low/close ne servent pas au moteur (il n'utilise que `open`), mais on
    # les remplit de façon cohérente plutôt que de laisser des colonnes fausses.
    scale = synth_open / df["open"].to_numpy()
    return pd.DataFrame(
        {"open": synth_open,
         "high": df["low"].to_numpy() * scale,
         "low": df["high"].to_numpy() * scale,
         "close": df["close"].to_numpy() * scale},
        index=df.index,
    )


def with_shorts(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = dict(bars)
    for s, df in bars.items():
        out[short_symbol(s)] = build_short_series(df)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# ÉVALUATION
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SliceMetrics:
    """Performance sur une tranche [a, b) — stratégie et références."""
    label: str
    n_periods: int
    n_rebalances: int          # jours où la répartition cible change
    strat_total_pct: float
    strat_cagr_pct: float
    strat_sharpe: float
    strat_maxdd_pct: float
    bh: dict[str, float]       # nom -> rendement total % sur la tranche
    invested_pct: float        # % du temps avec au moins une ligne ouverte


def _segment_metrics(equity: pd.Series, a: int, b: int,
                     ppy: float = 365.0) -> tuple[float, float, float, float]:
    """(total %, CAGR %, Sharpe, DD max %) sur [a, b) d'une courbe d'equity."""
    eq = equity.iloc[a:b]
    if len(eq) < 3 or eq.iloc[0] <= 0:
        return 0.0, 0.0, 0.0, 0.0
    eq = eq / eq.iloc[0]
    rets = eq.pct_change().dropna()
    total = float(eq.iloc[-1] - 1.0)
    years = len(eq) / ppy
    cagr = float(eq.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
    sd = float(rets.std())
    sharpe = float(rets.mean() / sd * np.sqrt(ppy)) if sd > 1e-12 else 0.0
    dd = float(((eq / eq.cummax()) - 1.0).min())
    return 100 * total, 100 * cagr, sharpe, 100 * dd


def _bh_equity(bars: dict[str, pd.DataFrame], n: int) -> dict[str, pd.Series]:
    """Buy & hold de chaque ligne + équipondéré naïf, sur [0, n).

    Reconstruit à partir des ouvertures, exactement comme `run_allocation`.
    L'accord avec le moteur est vérifié par `_assert_benchmark_agreement`.
    """
    syms = sorted(s for s in bars if not is_short_symbol(s))
    opens = pd.DataFrame({s: bars[s]["open"].iloc[:n] for s in syms})
    rets = opens.pct_change().fillna(0.0)
    out = {f"B&H {s}": (1.0 + rets[s]).cumprod() for s in syms}
    if len(syms) > 1:
        out["naïf équipondéré"] = (1.0 + (rets * (1.0 / len(syms))).sum(axis=1)).cumprod()
    return out


def _assert_benchmark_agreement(result, bars, n) -> str:
    """La reconstruction du B&H doit reproduire celle du moteur, au bit près."""
    mine = _bh_equity(bars, n)
    msgs = []
    for name, m in result.benchmarks.items():
        if not name.startswith("B&H ") or is_short_symbol(name[4:]):
            continue
        if name not in mine:
            continue
        eq = mine[name]
        total = 100.0 * float(eq.iloc[-1] / eq.iloc[0] - 1.0)
        d = abs(total - m.total_return_pct)
        msgs.append(f"    {name:<18} moteur {m.total_return_pct:>10.2f} %   "
                    f"reconstruit {total:>10.2f} %   écart {d:.2e}")
        if d > 1e-6:
            msgs.append(f"    *** DÉSACCORD sur {name} : dérivation par tranche "
                        f"non fondée ***")
    return "\n".join(msgs)


def evaluate(bars: dict[str, pd.DataFrame], params: dict,
             universe: list[str], a: int, b: int,
             label: str, cost_mult: float = 1.0) -> tuple[SliceMetrics, object]:
    """Simule sur [0, b) et mesure la tranche [a, b)."""
    strat = Strategy(params=params, universe=universe)
    data = strat.precompute({s: df for s, df in bars.items()
                             if not is_short_symbol(s)}, strat.params)
    allocs = strat.generate_allocations(data, strat.params, b)
    specs = make_specs(list(bars), cost_mult=cost_mult)
    res = run_allocation(allocs, bars, specs, end_idx=b, periods_per_year=365.0)

    total, cagr, sharpe, dd = _segment_metrics(res.equity, a, b)
    w = res.weights_history
    changed = (w.diff().abs().sum(axis=1) > 1e-12).iloc[a:b]
    invested = (w.sum(axis=1) > 1e-9).iloc[a:b]

    bh = {}
    for name, eq in _bh_equity(bars, b).items():
        seg = eq.iloc[a:b]
        bh[name] = 100.0 * float(seg.iloc[-1] / seg.iloc[0] - 1.0) if len(seg) > 1 else 0.0

    return SliceMetrics(
        label=label, n_periods=b - a, n_rebalances=int(changed.sum()),
        strat_total_pct=total, strat_cagr_pct=cagr, strat_sharpe=sharpe,
        strat_maxdd_pct=dd, bh=bh,
        invested_pct=100.0 * float(invested.mean()),
    ), res


def carry_drag_pct(invested_pct: float, symbols: list[str]) -> float:
    """Coût de portage annualisé, non modélisé par le moteur.

    Approximation de premier ordre : taux de swap annuel moyen des lignes de
    l'univers, pondéré par la fraction du temps où le portefeuille est investi.
    Suffisant pour dire si le portage change le verdict ; insuffisant pour un
    chiffre au dixième de point.
    """
    rate = float(np.mean([SWAP_ANNUAL_PCT[s] for s in symbols if s in SWAP_ANNUAL_PCT]))
    return rate * invested_pct / 100.0


# ─────────────────────────────────────────────────────────────────────────────
# WALK-FORWARD ANCRÉ
# ─────────────────────────────────────────────────────────────────────────────
def grid(param_grid: dict[str, list]) -> list[dict]:
    keys = sorted(param_grid)
    return [dict(zip(keys, combo)) for combo in product(*(param_grid[k] for k in keys))]


def walk_forward(bars: dict[str, pd.DataFrame], universe: list[str],
                 base_params: dict, param_grid: dict[str, list],
                 select_on: str = "sharpe") -> tuple[str, dict]:
    """Fenêtres ancrées de `core`. Sélection sur train, mesure sur test.

    La sélection se fait sur le Sharpe du TRAIN uniquement — jamais sur le test.
    C'est la seule façon d'obtenir un chiffre hors échantillon qui veuille dire
    quelque chose.
    """
    n = len(next(iter(bars.values())))
    configs = grid(param_grid)
    L = []
    L.append("=" * 78)
    L.append("WALK-FORWARD ANCRÉ — fenêtres importées de core.backtest.anchored_wf")
    L.append("=" * 78)
    L.append(f"{n} barres D1 · {len(configs)} configurations · sélection sur "
             f"{select_on} du TRAIN")
    L.append(f"Espérance de hasard : {len(configs)} configs x 0,05 = "
             f"{len(configs) * 0.05:.1f} « réussites » par pur hasard au seuil 5 %.")
    L.append("")

    rows = []
    for wi, (tr_frac, te_frac) in enumerate(WINDOWS, 1):
        tr_end, te_end = int(n * tr_frac), int(n * te_frac)
        best, best_score = None, -np.inf
        for cfg in configs:
            p = dict(base_params); p.update(cfg)
            try:
                m, _ = evaluate(bars, p, universe, 0, tr_end, "train")
            except Exception:
                continue
            score = m.strat_sharpe if select_on == "sharpe" else m.strat_cagr_pct
            if np.isfinite(score) and score > best_score:
                best, best_score = cfg, score
        if best is None:
            L.append(f"W{wi} : aucune configuration évaluable.")
            continue

        p = dict(base_params); p.update(best)
        mt, _ = evaluate(bars, p, universe, 0, tr_end, "train")
        me, _ = evaluate(bars, p, universe, tr_end, te_end, "test")
        rows.append((wi, best, mt, me))

    L.append(f"  {'W':>2} {'config retenue':<34} {'train Sh':>9} "
             f"{'OOS tot%':>9} {'OOS Sh':>8} {'OOS DD%':>9} {'rebal':>6} {'inv%':>6}")
    L.append("  " + "-" * 92)
    for wi, cfg, mt, me in rows:
        lbl = " ".join(f"{k}={v}" for k, v in sorted(cfg.items()))
        L.append(f"  {wi:>2} {lbl:<34} {mt.strat_sharpe:>9.2f} "
                 f"{me.strat_total_pct:>9.2f} {me.strat_sharpe:>8.2f} "
                 f"{me.strat_maxdd_pct:>9.2f} {me.n_rebalances:>6} "
                 f"{me.invested_pct:>6.1f}")
    L.append("")

    if rows:
        L.append("  Comparaison hors échantillon aux références, fenêtre par fenêtre :")
        names = sorted(rows[0][3].bh)
        L.append(f"  {'W':>2} {'stratégie':>11} " +
                 " ".join(f"{nm:>20}" for nm in names))
        L.append("  " + "-" * (16 + 21 * len(names)))
        wins = 0
        for wi, _, _, me in rows:
            cells = " ".join(f"{me.bh[nm]:>20.2f}" for nm in names)
            L.append(f"  {wi:>2} {me.strat_total_pct:>11.2f} {cells}")
            if all(me.strat_total_pct > me.bh[nm] for nm in names):
                wins += 1
        L.append("")
        L.append(f"  Fenêtres où la stratégie bat TOUTES les références : "
                 f"{wins} / {len(rows)}")
        oos = [me.strat_total_pct for _, _, _, me in rows]
        L.append(f"  Rendement OOS moyen : {np.mean(oos):+.2f} % "
                 f"(fenêtres : {', '.join(f'{x:+.1f}' for x in oos)})")
        L.append(f"  Fenêtres OOS positives : "
                 f"{sum(1 for x in oos if x > 0)} / {len(oos)}")
    L.append("")
    return "\n".join(L), {"rows": rows, "n_configs": len(configs)}


# ─────────────────────────────────────────────────────────────────────────────
def full_report() -> str:
    L = []
    universe = UNIVERSE_CRYPTO
    bars = load_universe(universe)
    n = len(next(iter(bars.values())))
    idx = next(iter(bars.values())).index

    L.append("=" * 78)
    L.append("s07_ionita_gaussian — ÉVALUATION COMPLÈTE")
    L.append("=" * 78)
    L.append(f"Univers  : {', '.join(universe)}  (inventaire crypto COMPLET du broker)")
    L.append(f"Période  : {idx[0].date()} -> {idx[-1].date()}  ({n} barres D1, "
             f"{n / 365.25:.1f} ans)")
    L.append(f"Coûts    : spread mesuré sur MT5 + slippage ; swap chiffré à part")
    L.append("")

    strat = Strategy(universe=universe)
    base = dict(strat.params)

    # ── Accord de la reconstruction des benchmarks avec le moteur ───────────
    m0, res0 = evaluate(bars, base, universe, 0, n, "plein")
    L.append("CONTRÔLE — accord avec les références du moteur core/ :")
    L.append(_assert_benchmark_agreement(res0, bars, n))
    L.append("")

    # ── Plein échantillon, les deux modes de poids ─────────────────────────
    L.append("=" * 78)
    L.append("PLEIN ÉCHANTILLON (in-sample, réglages par défaut de la source)")
    L.append("=" * 78)
    L.append("  Réglages : période=144, pôles=4, mult=1,414 — valeurs par défaut")
    L.append("  du Pine Script d'origine. Aucune optimisation à ce stade.")
    L.append("")
    for mode in ("normalized", "absolute"):
        for shorts in (False, True):
            p = dict(base); p["weight_mode"] = mode; p["enable_shorts"] = shorts
            b = with_shorts(bars) if shorts else bars
            u = universe
            m, res = evaluate(b, p, u, 0, n, f"{mode}/{shorts}")
            tag = f"poids {mode:<10} shorts {'oui' if shorts else 'non'}"
            drag = carry_drag_pct(m.invested_pct, universe)
            L.append(f"  {tag}")
            L.append(f"      total {m.strat_total_pct:>10.1f} %   "
                     f"CAGR {m.strat_cagr_pct:>7.2f} %   Sharpe {m.strat_sharpe:>5.2f}   "
                     f"DD {m.strat_maxdd_pct:>7.2f} %")
            L.append(f"      investi {m.invested_pct:>5.1f} % du temps   "
                     f"{m.n_rebalances} rebalancements   "
                     f"portage non modelise env. -{drag:.1f} %/an")
            L.append("")
    L.append("  RÉFÉRENCES sur la même période :")
    for name, v in sorted(m0.bh.items(), key=lambda kv: -kv[1]):
        L.append(f"      {name:<22} {v:>12.1f} %")
    L.append("")

    # ── Verdict natif du moteur : Sharpe ET drawdown des références ────────
    # Indispensable pour trancher F1, qui exige que le rendement ET le Sharpe
    # soient inférieurs. Comparer les seuls rendements totaux escamoterait
    # l'argument central de l'auteur, qui porte sur le couple rendement/risque.
    L.append("=" * 78)
    L.append("VERDICT NATIF DU MOTEUR core/ (poids normalized, long seul)")
    L.append("=" * 78)
    L.append(res0.render())
    L.append("")

    # ── Ablation du spread (METHODOLOGY §5.1) ──────────────────────────────
    L.append("=" * 78)
    L.append("ABLATION DU COÛT — séparer « pas d'edge » de « edge mangé par les coûts »")
    L.append("=" * 78)
    L.append("  Les deux diagnostics appellent des décisions OPPOSÉES :")
    L.append("    négatif avec coûts, positif sans -> signal réel, structure de coût")
    L.append("      inadaptée. Piste : broker moins cher, moins de rotation.")
    L.append("    négatif dans les deux cas -> il n'y a rien à sauver.")
    L.append("")
    L.append(f"  {'coût':<22} {'total %':>12} {'CAGR %':>9} {'Sharpe':>8} {'DD %':>9}")
    L.append("  " + "-" * 64)
    for mult, lbl in ((0.0, "nul (0x)"), (1.0, "nominal (1x)"), (2.0, "pessimiste (2x)")):
        p = dict(base); p["weight_mode"] = "normalized"; p["enable_shorts"] = False
        m, _ = evaluate(bars, p, universe, 0, n, lbl, cost_mult=mult)
        L.append(f"  {lbl:<22} {m.strat_total_pct:>12.1f} {m.strat_cagr_pct:>9.2f} "
                 f"{m.strat_sharpe:>8.2f} {m.strat_maxdd_pct:>9.2f}")
    L.append("")
    L.append("  Rappel : le coût de PORTAGE (~14 %/an sur un long crypto CFD) n'est")
    L.append("  dans AUCUNE de ces lignes — le moteur ne le modélise pas. Il s'ajoute.")
    L.append("")

    # ── Contrôle de concentration (METHODOLOGY §5.2 / F5) ──────────────────
    L.append("=" * 78)
    L.append("CONCENTRATION — la performance vient-elle d'une seule ligne ?")
    L.append("=" * 78)
    for sym in universe:
        p = dict(base); p["weight_mode"] = "normalized"; p["enable_shorts"] = False
        solo = {sym: bars[sym]}
        try:
            m, _ = evaluate(solo, p, [sym], 0, n, sym)
            bh = m.bh.get(f"B&H {sym}", float("nan"))
            L.append(f"  {sym:<10} stratégie seule {m.strat_total_pct:>10.1f} %   "
                     f"B&H {bh:>10.1f} %   écart {m.strat_total_pct - bh:>+9.1f} pt   "
                     f"DD {m.strat_maxdd_pct:>7.2f} %")
        except Exception as e:
            L.append(f"  {sym:<10} non évaluable : {e}")
    L.append("")

    # ── Test de plateau (METHODOLOGY §4 / F3) ──────────────────────────────
    # Un edge réel est une colline, pas une aiguille. On balaie la grille
    # entière en plein échantillon et on regarde si la performance est LISSE
    # autour de la cellule retenue par le walk-forward, ou si elle s'effondre
    # dès qu'on bouge d'un cran.
    L.append("=" * 78)
    L.append("TEST DE PLATEAU — la performance survit-elle au déplacement du réglage ?")
    L.append("=" * 78)
    L.append("  Grille complète, plein échantillon, poids normalized, long seul.")
    L.append("")
    L.append(f"  {'période':>8} {'pôles':>6} {'mult':>7} {'total %':>12} "
             f"{'Sharpe':>8} {'DD %':>9}")
    L.append("  " + "-" * 56)
    plateau = []
    for period in strat.manifest().param_grid["period"]:
        for poles in strat.manifest().param_grid["poles"]:
            for mult in strat.manifest().param_grid["mult"]:
                p = dict(base); p["weight_mode"] = "normalized"
                p["enable_shorts"] = False
                p.update({"period": period, "poles": poles, "mult": mult})
                try:
                    m, _ = evaluate(bars, p, universe, 0, n, "plateau")
                except Exception:
                    continue
                plateau.append((period, poles, mult, m.strat_total_pct,
                                m.strat_sharpe, m.strat_maxdd_pct))
    for row in plateau:
        L.append(f"  {row[0]:>8} {row[1]:>6} {row[2]:>7} {row[3]:>12.1f} "
                 f"{row[4]:>8.2f} {row[5]:>9.2f}")
    if plateau:
        sh = [r[4] for r in plateau]
        pos = sum(1 for r in plateau if r[3] > 0)
        beat = sum(1 for r in plateau if r[3] > max(m0.bh.values()))
        L.append("")
        L.append(f"  {len(plateau)} cellules · Sharpe médian {np.median(sh):.2f} "
                 f"· min {min(sh):.2f} · max {max(sh):.2f}")
        L.append(f"  Cellules à rendement positif        : {pos} / {len(plateau)}")
        L.append(f"  Cellules battant la MEILLEURE référence ({max(m0.bh.values()):.0f} %) : "
                 f"{beat} / {len(plateau)}")
        L.append("  Lecture : un edge robuste donne un Sharpe homogène sur la grille.")
        L.append("  Un pic isolé entouré de cellules médiocres est un sur-ajustement.")
    L.append("")

    # ── Walk-forward ───────────────────────────────────────────────────────
    for mode in ("normalized", "absolute"):
        p = dict(base); p["weight_mode"] = mode; p["enable_shorts"] = False
        L.append("")
        L.append(f"### WALK-FORWARD — poids {mode}, long seul")
        txt, _ = walk_forward(bars, universe, p, strat.manifest().param_grid)
        L.append(txt)

    p = dict(base); p["weight_mode"] = "normalized"; p["enable_shorts"] = True
    L.append("")
    L.append("### WALK-FORWARD — poids normalized, long + short")
    txt, _ = walk_forward(with_shorts(bars), universe, p,
                          strat.manifest().param_grid)
    L.append(txt)

    return "\n".join(L)


def main() -> int:
    report = full_report()

    # La console Windows est en cp1252 : un `print` direct de texte accentué y
    # lève UnicodeEncodeError et perd TOUT le rapport après des minutes de
    # calcul. Le fichier est donc écrit AVANT l'affichage, et l'affichage est
    # rendu tolérant. L'ordre compte : on ne perd jamais un résultat calculé.
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "anchored_wf.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report + "\n")

    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(report.encode(enc, errors="replace").decode(enc) + "\n")
    print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
