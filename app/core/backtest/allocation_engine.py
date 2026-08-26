"""
MOTEUR DE BACKTEST — STRATÉGIES D'ALLOCATION
=============================================

Simule une suite de répartitions cibles et produit une **courbe d'equity**, pas
une liste de trades. Complément de `engine.py`, qui traite les stratégies
épisodiques (entrée / stop / cible).

CE QUI CHANGE
-------------
Une allocation n'a ni stop ni cible : la mesure pertinente n'est pas le R par
trade mais la trajectoire du capital. D'où CAGR, Sharpe, drawdown, et le temps
passé dans chaque instrument.

LES BENCHMARKS SONT INTÉGRÉS, PAS OPTIONNELS
---------------------------------------------
`docs/METHODOLOGY.md` pose comme critère n°1 : **battre ce qu'on obtient sans
aucun effort**. Le harnais épisodique ne savait pas y répondre — il rendait des
R sans référence. Ici, toute évaluation renvoie systématiquement :

  - buy & hold de CHAQUE instrument de l'univers
  - équipondération naïve et constante
  - cash

L'agent s04 a montré pourquoi ça compte : sa stratégie battait les trois buy &
hold et **perdait quand même contre un 50/50 immobile**. Sans le benchmark naïf
dans le rapport, on concluait à un edge.

CONVENTION D'EXÉCUTION
----------------------
Décision à la clôture de la barre i, **rebalancement à l'ouverture de i+1**.
C'est la convention de la source et elle évite le lookahead d'exécution.

COÛTS
-----
Payés sur la **portion effectivement échangée** : passer de 100 % Nasdaq à 100 %
or coûte deux fois le coût de bord, mais réduire de 100 % à 90 % ne coûte que
sur les 10 %. Coût de bord = demi-spread + slippage, comme dans `engine.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from core.backtest.engine import InstrumentSpec
from core.contracts.allocation import Allocation

TRADING_DAYS = 252


@dataclass
class EquityMetrics:
    """Mesures d'une courbe d'equity. `n_periods` accompagne toujours le reste :
    un Sharpe sur six observations mensuelles ne veut rien dire."""
    total_return_pct: float
    cagr_pct: float
    sharpe: float
    max_dd_pct: float
    n_periods: int
    n_switches: int = 0
    time_in_asset: dict[str, float] = field(default_factory=dict)  # % du temps

    def row(self, label: str) -> str:
        return (f"  {label:<28} {self.cagr_pct:>8.2f} % {self.sharpe:>8.2f} "
                f"{self.max_dd_pct:>9.2f} % {self.total_return_pct:>10.1f} %")


@dataclass
class AllocationResult:
    equity: pd.Series
    metrics: EquityMetrics
    benchmarks: dict[str, EquityMetrics]
    weights_history: pd.DataFrame
    leg_contribution: dict[str, float]      # rendement annualisé PAR JOUR DÉTENU
    periods_per_year: float

    # ── Le verdict que la méthodologie exige ────────────────────────────────
    def beats_all_benchmarks(self, metric: str = "sharpe") -> bool:
        mine = getattr(self.metrics, metric)
        return all(mine > getattr(b, metric) for b in self.benchmarks.values())

    def best_benchmark(self, metric: str = "sharpe") -> tuple[str, EquityMetrics]:
        return max(self.benchmarks.items(), key=lambda kv: getattr(kv[1], metric))

    def render(self) -> str:
        L = []
        L.append("=" * 78)
        L.append("ALLOCATION — COURBE D'EQUITY ET RÉFÉRENCES")
        L.append("=" * 78)
        L.append(f"{self.metrics.n_periods} périodes · "
                 f"{self.metrics.n_switches} bascules")
        L.append("")
        L.append(f"  {'':<28} {'CAGR':>10} {'Sharpe':>8} {'DD max':>11} {'total':>12}")
        L.append("  " + "-" * 72)
        L.append(self.metrics.row("STRATÉGIE"))
        L.append("  " + "-" * 72)
        for name, m in sorted(self.benchmarks.items(),
                              key=lambda kv: -kv[1].sharpe):
            L.append(m.row(name))
        L.append("")

        if self.metrics.time_in_asset:
            L.append("  Temps passé par instrument :")
            for sym, pct in sorted(self.metrics.time_in_asset.items(),
                                   key=lambda kv: -kv[1]):
                L.append(f"    {sym:<14} {pct:>6.1f} %")
            L.append("")

        if self.leg_contribution:
            L.append("  Rendement annualisé PAR JOUR DÉTENU (ignore le temps passé) :")
            L.append("  Une jambe qui fait moins bien que détenir l'actif n'apporte rien.")
            for sym, r in sorted(self.leg_contribution.items(), key=lambda kv: -kv[1]):
                ref = self.benchmarks.get(f"B&H {sym}")
                cmp_ = f"   (B&H {sym} : {ref.cagr_pct:+.2f} %)" if ref else ""
                L.append(f"    {sym:<14} {r:>+8.2f} %{cmp_}")
            L.append("")

        # Le verdict de la méthodologie, écrit noir sur blanc.
        name, best = self.best_benchmark("sharpe")
        if self.metrics.sharpe > best.sharpe:
            L.append(f"  VERDICT : bat toutes les références. Meilleure = {name} "
                     f"(Sharpe {best.sharpe:.2f} contre {self.metrics.sharpe:.2f}).")
        else:
            L.append(f"  VERDICT : NE BAT PAS « {name} » "
                     f"(Sharpe {best.sharpe:.2f} contre {self.metrics.sharpe:.2f}).")
            L.append("  Critère n°1 de la méthodologie non satisfait : une stratégie qui")
            L.append("  ne bat pas l'effort zéro n'a pas d'intérêt, quel que soit son DD.")
        return "\n".join(L)


def _metrics(equity: pd.Series, periods_per_year: float,
             n_switches: int = 0,
             time_in_asset: Optional[dict] = None) -> EquityMetrics:
    eq = equity.dropna()
    if len(eq) < 2 or eq.iloc[0] <= 0:
        return EquityMetrics(0.0, 0.0, 0.0, 0.0, len(eq))

    rets = eq.pct_change().dropna()
    total = float(eq.iloc[-1] / eq.iloc[0] - 1.0)
    years = len(eq) / periods_per_year
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    sd = float(rets.std())
    sharpe = float(rets.mean() / sd * np.sqrt(periods_per_year)) if sd > 1e-12 else 0.0
    dd = float(((eq / eq.cummax()) - 1.0).min())

    return EquityMetrics(
        total_return_pct=100.0 * total, cagr_pct=100.0 * cagr, sharpe=sharpe,
        max_dd_pct=100.0 * dd, n_periods=len(eq), n_switches=n_switches,
        time_in_asset=time_in_asset or {},
    )


def run_allocation(
    allocations: list[Allocation],
    bars: dict[str, pd.DataFrame],
    specs: dict[str, InstrumentSpec],
    end_idx: Optional[int] = None,
    *,
    periods_per_year: float = TRADING_DAYS,
) -> AllocationResult:
    """Simule les répartitions et renvoie equity, métriques et références.

    `end_idx` : même contrat que le moteur épisodique — rien au-delà ne doit
    influencer le résultat. R1 s'applique.
    """
    symbols = sorted(bars)
    index = bars[symbols[0]].index
    n = len(index) if end_idx is None else min(end_idx, len(index))
    if n < 3:
        raise ValueError("historique trop court")

    idx = index[:n]
    # Rendements open->open. ATTENTION à la convention d'indice :
    #     rets[j] = open[j] / open[j-1] - 1
    # c'est-à-dire le rendement réalisé ENTRE open[j-1] ET open[j].
    opens = pd.DataFrame({s: bars[s]["open"].iloc[:n] for s in symbols}, index=idx)
    rets = opens.pct_change().fillna(0.0)

    # Répartition en vigueur à chaque barre : la dernière décidée, portée en avant.
    #
    # Une `Allocation` décrit le portefeuille ENTIER, pas un ajout : un symbole
    # absent de `weights` pèse zéro. Le report se fait donc par LIGNE, jamais
    # colonne par colonne — sinon une jambe remplacée resterait investie et la
    # somme des poids dépasserait 1. Symptôme observé avant correction : un
    # portefeuille « investi » 185 % du temps.
    # DÉCALAGE DE DEUX, ET C'EST LE POINT DÉLICAT DE CE MODULE
    #
    # Décision à la CLÔTURE de la barre i, exécution à l'OUVERTURE de i+1. La
    # première variation réellement subie va donc de open[i+1] à open[i+2],
    # c'est-à-dire `rets[i+2]` dans la convention ci-dessus.
    #
    # Une première version posait le poids en `i+1`, ce qui le faisait toucher
    # `rets[i+1]` = open[i] -> open[i+1] : un mouvement qui commence AVANT la
    # décision. Sur une stratégie qui entre le jour où le prix franchit une
    # borne — donc un jour de forte variation — la journée d'entrée était
    # encaissée gratuitement. Résultat mesuré par l'agent s07 : 107 278 %
    # contre 901 % pour le buy & hold.
    #
    # R1 ne peut PAS attraper ce défaut : ce n'est pas une fuite depuis le
    # futur, c'est un décalage systématique. L'invariant de troncature reste
    # vrai à chaque coupure. D'où le test déterministe dédié.
    target = pd.DataFrame(np.nan, index=idx, columns=symbols)
    for a in sorted(allocations, key=lambda x: x.timestamp):
        ts = pd.Timestamp(a.timestamp)
        if ts not in target.index:
            continue
        pos = target.index.get_loc(ts)
        if pos + 2 >= n:
            continue                      # décidée trop tard pour être appliquée
        row = {s: float(a.weights.get(s, 0.0)) for s in symbols}
        target.iloc[pos + 2] = [row[s] for s in symbols]
    held = target.ffill().fillna(0.0)      # avant la 1re décision : cash

    # Coûts sur la portion réellement échangée.
    #
    # Le coût de bord est un montant en prix (pips) ; on le convertit en
    # pourcentage AU PRIX DE LA BARRE OÙ L'ÉCHANGE A LIEU. Une première version
    # divisait par la médiane des ouvertures — donc par une statistique de tout
    # l'échantillon. Le coût d'une barre de 2021 changeait selon qu'on arrêtait
    # le backtest en 2022 ou en 2024 : violation de R1, détectée par
    # `tests/test_allocation_engine.py` avant qu'une stratégie s'en serve.
    turnover = held.diff().abs().fillna(held.abs())
    edge = pd.Series({s: (specs[s].spread_pips / 2.0 + specs[s].slippage_pips)
                         * specs[s].pip for s in symbols})
    cost_rate = edge / opens.clip(lower=1e-12)     # local à chaque barre
    costs = (turnover * cost_rate).sum(axis=1)

    port_ret = (held * rets).sum(axis=1) - costs
    equity = (1.0 + port_ret).cumprod()

    # Bascules = changement d'instrument dominant.
    dom = held.idxmax(axis=1).where(held.max(axis=1) > 0, "CASH")
    n_switches = int((dom != dom.shift()).sum() - 1)

    time_in = {s: 100.0 * float((held[s] > 0).mean()) for s in symbols}
    time_in["CASH"] = 100.0 * float((held.sum(axis=1) < 1e-9).mean())

    # Contribution par jambe : rendement annualisé PAR JOUR DÉTENU. Une jambe
    # peu tenue mais excellente ne doit pas être noyée par le temps passé.
    leg = {}
    for s in symbols:
        mask = held[s] > 0
        if mask.sum() > 2:
            r = (held[s] * rets[s])[mask]
            leg[s] = 100.0 * (float((1.0 + r).prod()) ** (periods_per_year / mask.sum()) - 1.0)

    # ── Références, systématiques ───────────────────────────────────────────
    benchmarks: dict[str, EquityMetrics] = {}
    for s in symbols:
        benchmarks[f"B&H {s}"] = _metrics((1.0 + rets[s]).cumprod(), periods_per_year)
    if len(symbols) > 1:
        eq_w = 1.0 / len(symbols)
        naive = (1.0 + (rets * eq_w).sum(axis=1)).cumprod()
        benchmarks[f"naïf {'/'.join(symbols)} équipondéré"] = _metrics(naive, periods_per_year)
    benchmarks["cash (0 %)"] = EquityMetrics(0.0, 0.0, 0.0, 0.0, n)

    return AllocationResult(
        equity=equity,
        metrics=_metrics(equity, periods_per_year, n_switches, time_in),
        benchmarks=benchmarks,
        weights_history=held,
        leg_contribution=leg,
        periods_per_year=periods_per_year,
    )
