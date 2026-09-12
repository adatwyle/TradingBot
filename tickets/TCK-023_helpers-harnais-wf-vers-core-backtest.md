---
id: TCK-023
from: cc-support
to: cc-app
status: open
blocking: false
created: 2026-09-13
---

## Question

Les harnais `backtests/run_wf.py` de S020, S022, S023 et S024 portent chacun leur copie
des mêmes helpers : `spec_with` (même instrument, autre spread), `measured_spread_pips`
(colonne `spread` MT5 → pips du catalogue), `head` (dépôt), `stats`, `by_year`,
`DispositifEnDefaut`, plus le boilerplate `sys.path` / `rule` / `section` / `cells`.
Les copies ont déjà divergé une fois (S023 remettait `slippage_pips` à 0 et laissait
passer une médiane de spread nulle — corrigé en Phase X du 2026-09-13, aligné sur
S022/S024). `on_bar` est aussi octet pour octet identique dans les quatre `strategy.py`.

Faut-il remonter ces helpers dans `core/backtest` (et `on_bar` comme défaut de
`StrategyModule`) plutôt que de laisser chaque cc-stratégie recopier ?

## Proposition de résolution

1. `core/backtest/harness.py` (nouveau, sous tests) : `spec_with(spec, spread_pips)`
   — `max_spread_pips` relevé, `slippage_pips` repris tel quel ; `measured_spread_pips(bars, spec)`
   — médiane 365 j, point = pip/10 (indices 2 décimales compris), `None` si médiane ≤ 0 / NaN ;
   `stats(res)`, `by_year(res)`, `repo_head()`, `DispositifEnDefaut`.
2. `on_bar` par défaut sur `StrategyModule` (`core/strategy_module.py` ou équivalent), les
   quatre stratégies l'héritent sans le recopier.
3. Les quatre `run_wf.py` importent depuis `core.backtest.harness` ; leurs `results.json`
   doivent rester identiques au bit près (mesures scellées de la nuit du 12.09) — c'est le
   test de non-régression du refactor.
4. Les tests d'invariance par troncature des `test_s02x_strategy.py` (S022:238-247,
   S023:273-280, S024:210-223) réécrivent `core.validation.causality.check` : à remplacer
   par un appel direct dans le même lot.

Interdits inchangés : `app/core/backtest/engine.py`, `anchored_wf.py`, études scellées.
Préférence cc-support : option 1+2+3 en un seul ticket, 4 en bonus si le lot reste court.

## Réponse

<cc-app>
