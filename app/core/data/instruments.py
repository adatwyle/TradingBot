"""
CATALOGUE D'INSTRUMENTS
=======================
Caractéristiques broker (pip, spread, valeur du pip). Une stratégie ne code
jamais ça en dur : elle reçoit un InstrumentSpec du backtester.

Spreads relevés sur Swissquote MT5, conditions normales. `max_spread` sert de
garde-fou : au-delà, le backtester refuse d'ouvrir (news, rollover).
"""
from __future__ import annotations

from core.backtest.engine import InstrumentSpec

_CATALOG: dict[str, dict] = {
    # ── Forex majeurs ────────────────────────────────────────────────────
    "EURUSD": dict(pip=0.0001, spread_pips=1.9, max_spread_pips=3.0, pip_value_per_lot=10.0),
    "USDCHF": dict(pip=0.0001, spread_pips=2.2, max_spread_pips=4.0, pip_value_per_lot=11.0),
    "USDJPY": dict(pip=0.01,   spread_pips=2.8, max_spread_pips=5.0, pip_value_per_lot=6.7),
    "USDCAD": dict(pip=0.0001, spread_pips=3.1, max_spread_pips=5.0, pip_value_per_lot=7.3),
    "AUDUSD": dict(pip=0.0001, spread_pips=2.0, max_spread_pips=3.5, pip_value_per_lot=10.0),
    # ── Croisées ─────────────────────────────────────────────────────────
    "EURCHF": dict(pip=0.0001, spread_pips=3.5, max_spread_pips=6.0, pip_value_per_lot=11.0),
    "AUDCHF": dict(pip=0.0001, spread_pips=2.2, max_spread_pips=4.0, pip_value_per_lot=11.0),
    "EURJPY": dict(pip=0.01,   spread_pips=3.6, max_spread_pips=6.0, pip_value_per_lot=6.7),
    "EURCAD": dict(pip=0.0001, spread_pips=3.8, max_spread_pips=6.0, pip_value_per_lot=7.3),
    "CADCHF": dict(pip=0.0001, spread_pips=3.4, max_spread_pips=6.0, pip_value_per_lot=11.0),
    "CHFJPY": dict(pip=0.01,   spread_pips=3.9, max_spread_pips=7.0, pip_value_per_lot=6.7),
    "AUDCAD": dict(pip=0.0001, spread_pips=3.2, max_spread_pips=5.5, pip_value_per_lot=7.3),
    "EURAUD": dict(pip=0.0001, spread_pips=3.4, max_spread_pips=6.0, pip_value_per_lot=6.5),
    # ── Croisées GBP / NZD — l'univers travaillé par la source fxalexg ───
    # Ajoutées le 2026-08-22. Leur ABSENCE avait forcé s93 à substituer
    # GBPUSD/EURJPY à GBPJPY/GBPCHF (manifest s93, research/ANALYSIS.md) : la
    # mesure de s93 ne porte donc pas sur l'univers réel de la source.
    # spread_pips = MÉDIANE mesurée sur 4000 barres H1 Swissquote (colonne
    # `spread` de MT5), max_spread_pips = p99 de la même mesure — pas un
    # instantané. pip_value_per_lot mesuré via trade_tick_value/trade_tick_size,
    # donc en CHF (devise du compte, conforme au docstring d'InstrumentSpec).
    # NOTE : les entrées historiques ci-dessus sont en USD (EURUSD=10.0 ; en CHF
    # ce serait ~8.0). Divergence signalée, PAS corrigée ici — elle changerait
    # le sizing des études déjà scellées.
    "EURGBP": dict(pip=0.0001, spread_pips=1.8, max_spread_pips=3.3,  pip_value_per_lot=10.93),
    "GBPUSD": dict(pip=0.0001, spread_pips=2.3, max_spread_pips=6.5,  pip_value_per_lot=8.01),
    "GBPJPY": dict(pip=0.01,   spread_pips=6.7, max_spread_pips=18.0, pip_value_per_lot=5.04),
    "GBPCHF": dict(pip=0.0001, spread_pips=5.4, max_spread_pips=17.0, pip_value_per_lot=10.00),
    "GBPAUD": dict(pip=0.0001, spread_pips=4.2, max_spread_pips=18.5, pip_value_per_lot=5.75),
    "GBPNZD": dict(pip=0.0001, spread_pips=8.2, max_spread_pips=20.0, pip_value_per_lot=4.79),
    "GBPCAD": dict(pip=0.0001, spread_pips=4.8, max_spread_pips=16.5, pip_value_per_lot=5.82),
    "NZDUSD": dict(pip=0.0001, spread_pips=5.0, max_spread_pips=7.0,  pip_value_per_lot=8.01),
    "NZDJPY": dict(pip=0.01,   spread_pips=4.1, max_spread_pips=10.0, pip_value_per_lot=5.04),
    "AUDNZD": dict(pip=0.0001, spread_pips=7.1, max_spread_pips=11.0, pip_value_per_lot=4.79),
    "AUDJPY": dict(pip=0.01,   spread_pips=4.1, max_spread_pips=8.0,  pip_value_per_lot=5.04),
    "CADJPY": dict(pip=0.01,   spread_pips=4.0, max_spread_pips=9.0,  pip_value_per_lot=5.04),
    "EURNZD": dict(pip=0.0001, spread_pips=9.3, max_spread_pips=21.2, pip_value_per_lot=4.79),
    # ── Indices (CFD) ────────────────────────────────────────────────────
    "SP500":  dict(pip=0.1, spread_pips=5.0,  max_spread_pips=12.0, pip_value_per_lot=1.0),
    "NASDAQ": dict(pip=0.1, spread_pips=8.0,  max_spread_pips=20.0, pip_value_per_lot=1.0),
    "DAX":    dict(pip=0.1, spread_pips=8.0,  max_spread_pips=20.0, pip_value_per_lot=1.0),
    "FTSE":   dict(pip=0.1, spread_pips=8.0,  max_spread_pips=18.0, pip_value_per_lot=1.0),
    "NIKKEI": dict(pip=1.0, spread_pips=10.0, max_spread_pips=25.0, pip_value_per_lot=1.0),
    # ── Matières premières / crypto ──────────────────────────────────────
    "XAUUSD": dict(pip=0.01,  spread_pips=25.0, max_spread_pips=60.0, pip_value_per_lot=1.0),
    "XAGUSD": dict(pip=0.001, spread_pips=25.0, max_spread_pips=60.0, pip_value_per_lot=5.0),
    "WTIUSD": dict(pip=0.01,  spread_pips=3.0,  max_spread_pips=8.0,  pip_value_per_lot=10.0),
    "BTCUSD": dict(pip=1.0,   spread_pips=30.0, max_spread_pips=90.0, pip_value_per_lot=1.0),
}


def get_spec(symbol: str) -> InstrumentSpec:
    if symbol not in _CATALOG:
        raise KeyError(
            f"instrument '{symbol}' absent du catalogue. "
            f"Ajoutez-le dans core/data/instruments.py — ne devinez pas ses "
            f"caractéristiques dans la stratégie."
        )
    return InstrumentSpec(symbol=symbol, **_CATALOG[symbol])


def known_symbols() -> list[str]:
    return sorted(_CATALOG)
