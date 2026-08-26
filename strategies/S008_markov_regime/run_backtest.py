"""
HARNAIS D'ÉVALUATION — s08_markov_regime
=========================================

R9 ET CE QUE CE FICHIER FAIT (ET NE FAIT PAS)
----------------------------------------------
Aucune boucle de backtest n'est écrite ici. Toute simulation passe par
`core.backtest.allocation_engine.run_allocation`, sans exception. Ce fichier
ORCHESTRE : il charge les barres, construit les specs, découpe les fenêtres et
appelle le moteur avec des `end_idx` — paramètre explicitement prévu par le
contrat d'allocation.

`core/backtest/anchored_wf.py` est câblé sur le contrat ÉPISODIQUE (il appelle
`generate_signals()` et raisonne en R par trade) : il ne sait pas évaluer une
courbe d'equity. Les FENÊTRES sont donc importées de lui, pas redéfinies, pour
que les découpages restent comparables d'une stratégie à l'autre. Même lacune de
`core/` que celle signalée par s07 ; non corrigée (interdiction d'y toucher).

USAGE
-----
    python -m strategies.s08_markov_regime.run_backtest            # tout
    python -m strategies.s08_markov_regime.run_backtest --quick    # sans WF ni HMM
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.allocation_engine import run_allocation
from core.backtest.anchored_wf import WINDOWS
from core.backtest.engine import InstrumentSpec
from core.data.source import load_bars
from strategies.s08_markov_regime.strategy import (
    Strategy, is_short_symbol, short_symbol,
)

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERS ET DONNÉES
# ─────────────────────────────────────────────────────────────────────────────
# Les instruments que la source cite explicitement : indice actions (S&P 500,
# NASDAQ) et Bitcoin. Élargissement ensuite (or, DAX) pour le contrôle de
# concentration exigé par docs/METHODOLOGY.md §6.
BROKER = {"SP500": "SP500", "NASDAQ": "NASDAQ",
          "BTCUSD": "#BTCUSD", "ETHUSD": "#ETHUSD",
          "XAUUSD": "XAUUSD", "DAX": "DAX"}

DAYS = 365 * 20      # on demande tout ce que le serveur veut bien rendre

# ─────────────────────────────────────────────────────────────────────────────
# COÛTS — mesurés sur MT5, pas repris d'un catalogue périmé
# ─────────────────────────────────────────────────────────────────────────────
# `core/data/instruments.py` donne SP500 spread_pips=5.0 avec pip=0.1, soit 0,5
# point d'indice. Le relevé MT5 du jour (`symbol_info().spread` en POINTS, avec
# `point=0.01`) donne 110 points = 1,10 point d'indice. Le catalogue a été
# calibré quand l'indice valait moitié moins. On utilise la mesure, exprimée
# directement en unités de prix (`pip=1.0`), et on la trace.
#
#   symbole     spread live      point      -> unités de prix    % du prix courant
#   #US500      110 pts          0.01          1,10               0,0141 %
#   #NAS100     220 pts          0.01          2,20               0,0073 %
#   #BTCUSD      82 pts          1.0          82,0                0,1298 %
#
# Slippage : non mesurable sur des barres. Retenu à 10 % du spread, ordre de
# grandeur cohérent avec docs/METHODOLOGY.md. Les résultats restent optimistes
# d'un montant inconnu — c'est dit, pas caché.
MEASURED = {
    "SP500":  dict(spread=1.10, slip=0.11),
    "NASDAQ": dict(spread=2.20, slip=0.22),
    "BTCUSD": dict(spread=82.0, slip=8.20),
    "ETHUSD": dict(spread=4.60, slip=0.46),
    "XAUUSD": dict(spread=0.30, slip=0.03),
    "DAX":    dict(spread=2.00, slip=0.20),
}

# Coût de portage (swap), NON modélisé par `allocation_engine` — il ne facture
# que le coût de bord sur le turnover. Relevé MT5 : `swap_mode=3` (montant en
# devise par lot et par jour), `trade_contract_size=1`.
#
#   #US500   swap_long = -1,3498 /jour sur un prix de 7 781,67 -> 6,33 %/an
#   #NAS100  swap_long = -5,2042 /jour sur 30 047,47           -> 6,32 %/an
#   #BTCUSD  swap_long = -29,715 /jour sur 63 196              -> 17,16 %/an
#
# Chiffré à part et rapporté à côté des résultats bruts, jamais fondu dedans.
# À noter : le buy & hold d'un CFD paie ce portage 100 % du temps, la stratégie
# seulement quand elle est investie. Le portage joue donc EN FAVEUR de la
# stratégie, et l'ignorer des deux côtés la désavantage — sens conservateur.
SWAP_ANNUAL_PCT = {"SP500": 6.33, "NASDAQ": 6.32, "BTCUSD": 17.16,
                   "ETHUSD": 14.4, "XAUUSD": 2.0, "DAX": 4.0}


def make_specs(symbols: list[str], cost_mult: float = 1.0) -> dict[str, InstrumentSpec]:
    """`pip=1.0` : le spread est donné directement en unités de prix.

    LIMITE DU MODÈLE DE COÛT, mesurée et déclarée. `InstrumentSpec` porte un
    spread FIXE en prix, et le moteur en déduit `cost_rate = edge / open`. Sur
    un actif dont le prix varie d'un facteur 10 sur l'échantillon, ce coût
    relatif dérive d'autant : sur BTC à 300 USD (2015), 82 USD de spread
    représenteraient 27 % — absurde. Le modèle est donc PESSIMISTE au début de
    l'échantillon et un peu optimiste à la fin.

    On ne « corrige » pas en calibrant sur la médiane des prix : ce serait une
    statistique de tout l'échantillon, donc une violation de R1 — exactement le
    bug qu'`allocation_engine` documente avoir eu et corrigé. L'ablation de coût
    (`cost_mult=0`) mesure l'enjeu à la place.
    """
    specs: dict[str, InstrumentSpec] = {}
    for s in symbols:
        if is_short_symbol(s):
            continue
        m = MEASURED[s]
        specs[s] = InstrumentSpec(
            symbol=s, pip=1.0, spread_pips=m["spread"] * cost_mult,
            max_spread_pips=max(m["spread"] * 3.0, 1e-9),
            pip_value_per_lot=1.0, slippage_pips=m["slip"] * cost_mult,
        )
    # Jambes short synthétiques : coût de bord à ZÉRO, délibérément.
    # La série synthétique peut tendre vers zéro (un short maintenu depuis 2014
    # sur BTC aurait tout perdu) ; `edge / open` y explose et produit une equity
    # dépourvue de sens. Les deux échappatoires — calibrer sur la médiane
    # (statistique de tout l'échantillon, violation R1) ou sur le niveau de
    # départ (explosion) — sont refusées.
    # Ce choix AVANTAGE les shorts. Il est retenu parce que la conclusion qu'il
    # permet est conservatrice dans le seul sens utile : si les shorts
    # n'apportent rien alors qu'ils sont gratuits, ils n'apporteront rien en les
    # faisant payer. S'ils apportaient beaucoup, ce serait NON MESURÉ, pas acquis.
    for s in [x for x in symbols if is_short_symbol(x)]:
        specs[s] = InstrumentSpec(symbol=s, pip=1.0, spread_pips=0.0,
                                  max_spread_pips=1e9, pip_value_per_lot=1.0,
                                  slippage_pips=0.0)
    return specs


DATA_DEFECTS: list[str] = []


def _drop_corrupt_bars(sym: str, df: pd.DataFrame) -> pd.DataFrame:
    """Retire les barres à prix nul ou négatif.

    DÉFAUT DE DONNÉES RÉEL, TROUVÉ ICI ET SIGNALÉ — NON CORRIGÉ DANS core/
    ------------------------------------------------------------------------
    `load_bars("#BTCUSD", "D1")` renvoie une barre entièrement à zéro le
    2015-01-07 (open = high = low = close = 0, tick_volume = 1). Conséquences
    mesurées AVANT ce filtre, sur le run BTCUSD complet :

        B&H BTCUSD : CAGR -100,00 %, Sharpe -2,28, total -100,0 %

    Le buy & hold de Bitcoin sur 12 ans ressortait donc à -100 %. Le rendement
    open->open vaut -100 % le 2015-01-07 puis +inf le lendemain ; `cumprod`
    écrase tout à zéro et l'infini ne le rattrape pas.

    C'est la RÉFÉRENCE CENTRALE de cette étude qui était détruite — et elle
    l'était en silence, sans exception ni avertissement. Toute stratégie du
    projet qui consomme BTCUSD en D1 est concernée. Le nettoyage se fait ici
    parce que `core/` est interdit d'écriture ; le constat est remonté tel quel.
    """
    bad = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    if bad.any():
        dates = ", ".join(str(d.date()) for d in df.index[bad][:5])
        DATA_DEFECTS.append(
            f"{sym} : {int(bad.sum())} barre(s) à prix nul retirée(s) ({dates}). "
            f"Sans ce filtre, le B&H de {sym} ressort à -100 %.")
    return df[~bad]


def load_universe(symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Barres D1 alignées sur l'index COMMUN.

    L'alignement est une exigence de `run_allocation`, qui prend l'index du
    premier symbole comme référence. Un désalignement produirait des rendements
    calculés sur des dates qui ne se correspondent pas — silencieusement.

    Effet de bord à connaître : mélanger un indice (5 j/semaine) et BTC
    (7 j/semaine) supprime les week-ends du calendrier de BTC. Les runs
    mono-instrument, eux, gardent le calendrier natif.
    """
    raw = {}
    for s in symbols:
        df = load_bars(BROKER.get(s, s), "D1", days=DAYS)
        if df is None or len(df) < 500:
            raise RuntimeError(f"{s} : {0 if df is None else len(df)} barres, insuffisant")
        raw[s] = _drop_corrupt_bars(s, df)
    common = None
    for df in raw.values():
        common = df.index if common is None else common.intersection(df.index)
    common = common.sort_values()
    return {s: df.loc[common, ["open", "high", "low", "close"]].astype(float)
            for s, df in raw.items()}


def build_short_series(df: pd.DataFrame) -> pd.DataFrame:
    """Série dont le rendement open->open est l'exact opposé du réel.

    `open_s[i] = open_s[i-1] . (1 - r[i])`, `r[i]` = rendement open->open réel.
    Le moteur calcule `pct_change()` sur les ouvertures et obtient donc `-r[i]` :
    c'est la définition d'une position courte non financée.

    Causal : `open_s[i]` ne dépend que des barres d'indice <= i. Vérifié par
    troncature dans `validate_r1.py`, pas supposé ici.
    """
    r = df["open"].pct_change().fillna(0.0).to_numpy()
    synth = 100.0 * np.cumprod(1.0 - r)
    scale = synth / df["open"].to_numpy()
    return pd.DataFrame({"open": synth,
                         "high": df["low"].to_numpy() * scale,
                         "low": df["high"].to_numpy() * scale,
                         "close": df["close"].to_numpy() * scale}, index=df.index)


def with_shorts(bars: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = dict(bars)
    for s, df in bars.items():
        out[short_symbol(s)] = build_short_series(df)
    return out


def periods_per_year(idx: pd.Index) -> float:
    years = (idx[-1] - idx[0]).days / 365.25
    return float(len(idx) / years) if years > 0 else 252.0


# ─────────────────────────────────────────────────────────────────────────────
# ÉVALUATION
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Run:
    label: str
    res: object
    weights: pd.DataFrame
    invested_pct: float
    n_rebal: int
    universe: list[str]


def evaluate(bars: dict[str, pd.DataFrame], params: dict, universe: list[str],
             end_idx: int | None = None, cost_mult: float = 1.0,
             label: str = "") -> Run:
    strat = Strategy(params=params, universe=universe)
    base = {s: d for s, d in bars.items() if not is_short_symbol(s)}
    data = strat.precompute(base, strat.params)
    n = len(next(iter(bars.values()))) if end_idx is None else end_idx
    allocs = strat.generate_allocations(data, strat.params, n)
    specs = make_specs(list(bars), cost_mult=cost_mult)
    ppy = periods_per_year(next(iter(bars.values())).index[:n])
    res = run_allocation(allocs, bars, specs, end_idx=n, periods_per_year=ppy)
    w = res.weights_history
    return Run(label=label, res=res, weights=w,
               invested_pct=100.0 * float((w.sum(axis=1) > 1e-9).mean()),
               n_rebal=int((w.diff().abs().sum(axis=1) > 1e-12).sum()),
               universe=list(universe))


def segment(equity: pd.Series, a: int, b: int, ppy: float) -> tuple[float, float, float, float]:
    """(total %, CAGR %, Sharpe, DD max %) sur [a, b)."""
    eq = equity.iloc[a:b]
    if len(eq) < 3 or eq.iloc[0] <= 0:
        return 0.0, 0.0, 0.0, 0.0
    eq = eq / eq.iloc[0]
    rets = eq.pct_change().dropna()
    years = len(eq) / ppy
    cagr = float(eq.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
    sd = float(rets.std())
    sharpe = float(rets.mean() / sd * np.sqrt(ppy)) if sd > 1e-12 else 0.0
    dd = float(((eq / eq.cummax()) - 1.0).min())
    return 100 * float(eq.iloc[-1] - 1.0), 100 * cagr, sharpe, 100 * dd


def bh_segment(bars: dict[str, pd.DataFrame], sym: str, a: int, b: int) -> float:
    o = bars[sym]["open"].iloc[a:b]
    return 100.0 * float(o.iloc[-1] / o.iloc[0] - 1.0) if len(o) > 1 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 1 — VARIANTES SUR PLEIN ÉCHANTILLON
# ─────────────────────────────────────────────────────────────────────────────
VARIANTS = [
    # label,                            surcharges de paramètres
    ("markov causal step=20 prop",      dict()),
    ("markov causal step=20 binaire",   dict(size_mode="binary")),
    ("markov causal step=1  binaire",   dict(size_mode="binary", step=1)),
    ("markov FUITÉ step=20 binaire",    dict(size_mode="binary", causal=False)),
    ("markov FUITÉ step=1  binaire",    dict(size_mode="binary", causal=False, step=1)),
    ("naïf momentum 20j",               dict(signal_source="naive", size_mode="binary")),
    ("markov horizon=5 (P^n)",          dict(size_mode="binary", horizon=5)),
    ("markov horizon=5 (scalaire)",     dict(size_mode="binary", horizon=5,
                                             scalar_power=True)),
]


def block_full_sample(sym: str, bars_long: dict, bars_ls: dict) -> tuple[list[str], dict]:
    L = []
    idx = bars_long[sym].index
    ppy = periods_per_year(idx)
    L.append("#" * 96)
    L.append(f"# {sym} — {len(idx)} barres D1 ({idx[0].date()} -> {idx[-1].date()}) "
             f"· {ppy:.0f} barres/an")
    L.append("#" * 96)
    L.append("")

    runs: dict[str, Run] = {}
    for shorts, tag, bars in ((False, "long only", bars_long),
                              (True, "avec shorts", bars_ls)):
        L.append(f"  --- {tag} " + "-" * (88 - len(tag)))
        L.append(f"  {'variante':<32} {'CAGR':>8} {'Sharpe':>8} {'DD max':>9} "
                 f"{'total':>12} {'inv%':>7} {'rebal':>7}")
        L.append("  " + "-" * 88)
        for label, over in VARIANTS:
            p = dict(over); p["enable_shorts"] = shorts
            key = f"{sym}|{label}|{'S' if shorts else 'L'}"
            try:
                r = evaluate(bars, p, [sym], label=label)
            except Exception as e:                      # noqa: BLE001
                L.append(f"  {label:<32} ÉCHEC : {e}")
                continue
            runs[key] = r
            m = r.res.metrics
            L.append(f"  {label:<32} {m.cagr_pct:>7.2f}% {m.sharpe:>8.2f} "
                     f"{m.max_dd_pct:>8.2f}% {m.total_return_pct:>11.1f}% "
                     f"{r.invested_pct:>6.1f}% {r.n_rebal:>7}")
        L.append("")

    # Références : identiques pour toutes les variantes, sorties une fois.
    ref = runs.get(f"{sym}|markov causal step=20 prop|L")
    if ref is not None:
        L.append("  RÉFÉRENCES (rendues par le moteur, non optionnelles) :")
        for name, m in sorted(ref.res.benchmarks.items(), key=lambda kv: -kv[1].sharpe):
            L.append(f"    {name:<28} CAGR {m.cagr_pct:>7.2f}%  Sharpe {m.sharpe:>6.2f}"
                     f"  DD {m.max_dd_pct:>7.2f}%  total {m.total_return_pct:>10.1f}%")
        L.append("")
    return L, runs


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 2 — F1 : CONTRIBUTION MARGINALE, POSITION PAR POSITION
# ─────────────────────────────────────────────────────────────────────────────
def block_f1(sym: str, runs: dict) -> list[str]:
    L = ["  F1 — CONTRIBUTION MARGINALE DE L'APPAREIL (comparaison position par position)",
         "  " + "-" * 88]
    a = runs.get(f"{sym}|markov causal step=20 binaire|S")
    b = runs.get(f"{sym}|naïf momentum 20j|S")
    if a is None or b is None:
        return L + ["  (variantes manquantes)", ""]

    wa, wb = a.weights, b.weights
    cols = sorted(set(wa.columns) | set(wb.columns))
    wa = wa.reindex(columns=cols, fill_value=0.0)
    wb = wb.reindex(columns=cols, fill_value=0.0)
    warm = Strategy().manifest().warmup_bars
    wa, wb = wa.iloc[warm:], wb.iloc[warm:]

    same = (wa - wb).abs().sum(axis=1) < 1e-9
    n = len(wa)
    # Direction nette : + si le poids est sur la jambe longue, - sur la courte.
    def net(w):
        lng = w[[c for c in cols if not is_short_symbol(c)]].sum(axis=1)
        sht = w[[c for c in cols if is_short_symbol(c)]].sum(axis=1)
        return np.sign(lng - sht)
    da, db = net(wa), net(wb)

    L.append(f"  n = {n} barres après warmup")
    L.append(f"  poids IDENTIQUES à 1e-9 près : {100*float(same.mean()):.2f} % des barres")
    L.append(f"  même DIRECTION (long/short/plat) : {100*float((da == db).mean()):.2f} %")
    L.append(f"  seuil F1 déclaré avant mesure : concordance >= 95 % ET |dCAGR| < 1 pt")
    ca = a.res.metrics.cagr_pct
    cb = b.res.metrics.cagr_pct
    L.append(f"  CAGR markov {ca:+.2f} %  vs  naïf {cb:+.2f} %   (écart {ca-cb:+.2f} pt)")
    trig = (float(same.mean()) >= 0.95) and (abs(ca - cb) < 1.0)
    L.append(f"  -> F1 {'DÉCLENCHÉE' if trig else 'NON déclenchée'}")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 3 — F5 : AMPLEUR DU BIAIS DE FUITE
# ─────────────────────────────────────────────────────────────────────────────
def block_f5(sym: str, runs: dict) -> list[str]:
    L = ["  F5 — LE VERDICT CHANGE-T-IL DE SIGNE SELON QU'ON CORRIGE LA FUITE ?",
         "  " + "-" * 88]
    pairs = [("step=20", f"{sym}|markov causal step=20 binaire|S",
              f"{sym}|markov FUITÉ step=20 binaire|S"),
             ("step=1", f"{sym}|markov causal step=1  binaire|S",
              f"{sym}|markov FUITÉ step=1  binaire|S")]
    for tag, kc, kl in pairs:
        rc, rl = runs.get(kc), runs.get(kl)
        if rc is None or rl is None:
            continue
        mc, ml = rc.res.metrics, rl.res.metrics
        L.append(f"  {tag:<9} causal CAGR {mc.cagr_pct:>7.2f}%  Sharpe {mc.sharpe:>6.2f}"
                 f"   |   FUITÉ CAGR {ml.cagr_pct:>7.2f}%  Sharpe {ml.sharpe:>6.2f}"
                 f"   |   écart CAGR {ml.cagr_pct - mc.cagr_pct:+7.2f} pt")
        if ml.cagr_pct > 0 >= mc.cagr_pct:
            L.append("            -> F5 DÉCLENCHÉE : rentable seulement AVEC la fuite.")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 4 — ABLATION DU SPREAD + PORTAGE
# ─────────────────────────────────────────────────────────────────────────────
def block_costs(sym: str, bars_ls: dict) -> list[str]:
    L = ["  ABLATION DU SPREAD (docs/METHODOLOGY.md §5.1) ET COÛT DE PORTAGE",
         "  " + "-" * 88]
    L.append(f"  {'coût':<16} {'CAGR':>9} {'Sharpe':>8} {'DD max':>9} {'total':>12}")
    L.append("  " + "-" * 60)
    base = dict(size_mode="binary", enable_shorts=True)
    inv = None
    for mult, tag in ((0.0, "nul"), (1.0, "nominal"), (2.0, "pessimiste x2")):
        r = evaluate(bars_ls, base, [sym], cost_mult=mult)
        m = r.res.metrics
        inv = r.invested_pct if mult == 1.0 else inv
        L.append(f"  {tag:<16} {m.cagr_pct:>8.2f}% {m.sharpe:>8.2f} "
                 f"{m.max_dd_pct:>8.2f}% {m.total_return_pct:>11.1f}%")
    rate = SWAP_ANNUAL_PCT.get(sym, 0.0)
    L.append("")
    L.append(f"  Portage NON modélisé par le moteur : swap long {rate:.2f} %/an sur {sym}.")
    L.append(f"  Stratégie investie {inv:.1f} % du temps -> ~{rate*inv/100:.2f} %/an de "
             f"portage, contre {rate:.2f} %/an pour un buy & hold CFD (investi 100 %).")
    L.append("  Le portage joue donc EN FAVEUR de la stratégie ; l'omettre des deux côtés")
    L.append("  la désavantage. Sens conservateur, conservé tel quel.")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 5 — CONTRÔLE LONG / SHORT
# ─────────────────────────────────────────────────────────────────────────────
def block_legs(sym: str, runs: dict) -> list[str]:
    L = ["  CONTRÔLE LONG / SHORT (docs/METHODOLOGY.md §5.2)", "  " + "-" * 88]
    r = runs.get(f"{sym}|markov causal step=20 binaire|S")
    if r is None:
        return L + ["  (variante manquante)", ""]
    L.append("  Rendement annualisé PAR JOUR DÉTENU, par jambe :")
    for s, v in sorted(r.res.leg_contribution.items(), key=lambda kv: -kv[1]):
        L.append(f"    {s:<14} {v:>+8.2f} %")
    L.append("  Temps passé :")
    for s, pct in sorted(r.res.metrics.time_in_asset.items(), key=lambda kv: -kv[1]):
        L.append(f"    {s:<14} {pct:>6.1f} %")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 6 — WALK-FORWARD ANCRÉ
# ─────────────────────────────────────────────────────────────────────────────
def grid(pg: dict[str, list]) -> list[dict]:
    keys = sorted(pg)
    return [dict(zip(keys, c)) for c in product(*(pg[k] for k in keys))]


def block_wf(sym: str, bars_ls: dict) -> list[str]:
    m = Strategy().manifest()
    configs = grid(m.param_grid)
    n = len(next(iter(bars_ls.values())))
    ppy = periods_per_year(next(iter(bars_ls.values())).index)
    L = ["  WALK-FORWARD ANCRÉ — fenêtres importées de core.backtest.anchored_wf",
         "  " + "-" * 88]
    L.append(f"  {n} barres · {len(configs)} configurations · sélection sur le "
             f"Sharpe du TRAIN uniquement")
    L.append(f"  Espérance de hasard : {len(configs)} x 0,05 = {len(configs)*0.05:.1f} "
             f"« réussites » par pur hasard au seuil 5 %.")
    L.append("")
    base = dict(size_mode="binary", enable_shorts=True)

    rows = []
    for wi, (tr, te) in enumerate(WINDOWS, 1):
        tr_end, te_end = int(n * tr), int(n * te)
        best, score = None, -np.inf
        for cfg in configs:
            p = dict(base); p.update(cfg)
            try:
                r = evaluate(bars_ls, p, [sym], end_idx=tr_end)
            except Exception:                            # noqa: BLE001
                continue
            _, _, sh, _ = segment(r.res.equity, 0, tr_end, ppy)
            if np.isfinite(sh) and sh > score:
                best, score = cfg, sh
        if best is None:
            L.append(f"  W{wi} : aucune configuration évaluable")
            continue
        p = dict(base); p.update(best)
        r = evaluate(bars_ls, p, [sym], end_idx=te_end)
        tot, cagr, sh, dd = segment(r.res.equity, tr_end, te_end, ppy)
        bh = bh_segment(bars_ls, sym, tr_end, te_end)
        rows.append((wi, best, score, tot, sh, dd, bh))

    L.append(f"  {'W':>2} {'config retenue':<38} {'train Sh':>9} {'OOS tot%':>9} "
             f"{'OOS Sh':>8} {'OOS DD%':>9} {'B&H tot%':>10}")
    L.append("  " + "-" * 92)
    for wi, cfg, sc, tot, sh, dd, bh in rows:
        lbl = " ".join(f"{k}={v}" for k, v in sorted(cfg.items()))
        L.append(f"  {wi:>2} {lbl:<38} {sc:>9.2f} {tot:>9.2f} {sh:>8.2f} "
                 f"{dd:>9.2f} {bh:>10.2f}")
    if rows:
        pos = sum(1 for r in rows if r[3] > 0)
        beat = sum(1 for r in rows if r[3] > r[6])
        mean = float(np.mean([r[3] for r in rows]))
        L.append("")
        L.append(f"  fenêtres OOS positives : {pos}/{len(rows)} · "
                 f"battant le B&H : {beat}/{len(rows)} · rendement OOS moyen "
                 f"{mean:+.2f} %")
        L.append(f"  seuil F3 déclaré avant mesure : < 3/4 positives OU moyenne "
                 f"négative -> F3 déclenchée")
        L.append(f"  -> F3 {'DÉCLENCHÉE' if (pos < 3 or mean < 0) else 'NON déclenchée'}")
        L.append(f"  configurations retenues différentes d'une fenêtre à l'autre : "
                 f"{len({tuple(sorted(r[1].items())) for r in rows})}/{len(rows)} "
                 f"(un changement à chaque fenêtre = la grille suit le bruit)")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 7 — MARKOV CACHÉ
# ─────────────────────────────────────────────────────────────────────────────
def block_hmm(sym: str, bars_ls: dict) -> list[str]:
    L = ["  MARKOV CACHÉ (concept 9) — les deux versions, comme exigé",
         "  " + "-" * 88]
    L.append("  `docs/sources/aipathways/SYNTHESE.md` R7 classe déjà en rejet le HMM")
    L.append("  ajusté sur l'échantillon complet puis utilisé pour l'étiqueter. Il est")
    L.append("  reproduit ici uniquement pour chiffrer ce qu'il rapporte artificiellement.")
    L.append("")
    L.append(f"  {'version':<34} {'CAGR':>9} {'Sharpe':>8} {'DD max':>9} {'inv%':>7}")
    L.append("  " + "-" * 72)
    for mode, tag in (("causal", "HMM glissant (honnête)"),
                      ("leaky", "HMM plein échantillon (LE PIÈGE)")):
        p = dict(size_mode="binary", enable_shorts=True,
                 signal_source="hmm_agree", hmm_mode=mode)
        try:
            r = evaluate(bars_ls, p, [sym])
        except Exception as e:                           # noqa: BLE001
            L.append(f"  {tag:<34} ÉCHEC : {e}")
            continue
        m = r.res.metrics
        L.append(f"  {tag:<34} {m.cagr_pct:>8.2f}% {m.sharpe:>8.2f} "
                 f"{m.max_dd_pct:>8.2f}% {r.invested_pct:>6.1f}%")
    L.append("")
    return L


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="sans walk-forward ni HMM")
    ap.add_argument("--symbols", default="SP500,NASDAQ,BTCUSD")
    ap.add_argument("--out", default="results.txt")
    a = ap.parse_args()

    L = ["=" * 96,
         "s08_markov_regime — ÉVALUATION COMPLÈTE",
         "=" * 96,
         "Contrat : ALLOCATION. Moteur : core.backtest.allocation_engine.run_allocation.",
         "Shorts : séries synthétiques SYM~S (coût de bord nul, cf. make_specs).",
         "Conditions de falsification déclarées AVANT mesure : research/FALSIFICATION.md",
         ""]

    all_runs = {}
    for sym in a.symbols.split(","):
        bars_long = load_universe([sym])
        bars_ls = with_shorts(bars_long)
        blk, runs = block_full_sample(sym, bars_long, bars_ls)
        all_runs.update(runs)
        L += blk
        L += block_f1(sym, runs)
        L += block_f5(sym, runs)
        L += block_legs(sym, runs)
        L += block_costs(sym, bars_ls)
        if not a.quick:
            L += block_hmm(sym, bars_ls)
            L += block_wf(sym, bars_ls)

    # Multi-actifs, sur l'index commun.
    syms = a.symbols.split(",")
    if len(syms) > 1:
        bars = load_universe(syms)
        bars_ls = with_shorts(bars)
        L.append("#" * 96)
        L.append(f"# PORTEFEUILLE {'+'.join(syms)} — index commun, "
                 f"{len(next(iter(bars.values())))} barres")
        L.append("#" * 96)
        r = evaluate(bars_ls, dict(size_mode="binary", enable_shorts=True), syms)
        L.append(r.res.render())
        L.append("")

    if DATA_DEFECTS:
        L.append("#" * 96)
        L.append("# DÉFAUTS DE DONNÉES DÉTECTÉS (signalés, non corrigés dans core/)")
        L.append("#" * 96)
        for d in sorted(set(DATA_DEFECTS)):
            L.append(f"  {d}")
        L.append("")

    txt = "\n".join(L)
    print(txt)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
