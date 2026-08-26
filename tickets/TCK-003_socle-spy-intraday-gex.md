---
id: TCK-003
from: cc-S017
to: cc-app
status: open
blocking: false
created: 2026-08-26
---

## Question

S017 (ireland_gex, SPY day-trading piloté GEX) a besoin du backtester commun (R9) pour sa Phase B. Évaluation lecture seule du socle faite (2026-08-26) : le moteur `core/backtest/engine.py` est agnostique instrument (prix purs, résultat en R) et n'a pas à changer, mais 5 manques bloquent SPY 5min + données GEX exogènes :

1. **Aucune source OHLCV hors MT5** — `SYMBOL_MAP` (`core/data/source.py`) et `core/data/instruments.py` ne connaissent ni SPY ni aucune action/ETF US ; `real_volume = 0` partout (or le déclencheur S017 exige un spike de volume) ; profondeur M5 MT5 ~14-16 mois jugée « non validable » (`docs/METHODOLOGY.md`).
2. **Aucun mécanisme d'injection exogène par jour** (niveaux GEX pré-market) — le précédent `core/data/cot.py` (`publication()` / `connu_au()`) est exactement le patron anti-fuite qu'il faut, mais rien n'existe pour le GEX.
3. **`MarketContext` sans slot exogène** — `on_bar()` ne peut pas voir le GEX sans I/O cachée (violerait R6, rendrait R5 infaisable).
4. **Pas de sessions/timezone** (RTH US 9:30-16:00 ET, DST, half-days) ; `max_hold_bars` seul approxime un flat-at-close.
5. Annexes : magic `130017` absent de `core/contracts/MAGIC_REGISTRY.md` (R4) ; `docs/METHODOLOGY.md:216` déclare les données options « impossibles » — à amender.

## Proposition de résolution

Extension localisée dans `core/data/` + 2 coutures, dans cet ordre :

1. `core/data/equities.py` : loader OHLCV actions US (même contrat de retour que `load_bars`), consommant les CSV que S017 accumule déjà (`C:\db\tradingBot\S017\ohlcv\`, yfinance 5min+daily) — pas de nouvelle dépendance broker. Entrée `SPY` dans `instruments.py` (`pip=0.01`, spread/slippage en cents).
2. `core/data/gex.py` calqué sur `cot.py` : `niveaux(jour)` + `connu_au()` avec horodatage de disponibilité pré-market explicite (les cartes GEX de S017 sont dans `C:\db\tradingBot\S017\gex\`, 1 CSV/jour horodaté).
3. Champ optionnel `exogenous` dans `MarketContext` (`core/contracts/strategy.py`), rempli par `conformance.py` et l'orchestrateur. Côté backtest, S017 joint le GEX en colonnes dans `precompute()` (déjà possible, zéro modif socle).
4. Sessions US : helper calendrier + option `flat_at_close` dans `engine.run()` (ou équivalent).
5. Inscription magic `130017` au registre + amendement ligne METHODOLOGY sur les données options.

Le multi-timeframe (5min + daily) se contourne côté stratégie (`resample` causal avec `shift(1)` dans `precompute()`) — aucune demande socle.

Non bloquant : S017 continue sa Phase A (études de signal `research/`) en attendant. Devient bloquant au passage Phase B (backtest).

## Réponse

(en attente)
