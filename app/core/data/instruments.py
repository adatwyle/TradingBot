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


# ── Spreads MESURES, par symbole et par annee ───────────────────────────────
# Distinct de `_CATALOG[...]["spread_pips"]` ci-dessus, qui reste une valeur
# FIGEE de reference historique — NE PAS la modifier : `_CATALOG["XAUUSD"]`
# (25,0 pips) est citee telle quelle par `studies/gold_forward/PROTOCOL.md`
# section 2.2 (etude scellee, en cours depuis le 14 aout 2026). La corriger
# deplacerait retroactivement le cout de valorisation d'un test deja en
# cours. Toute mesure NEUVE (nouvelle etude, nouveau sizing, audit spread)
# doit passer par `measured_spread_pips()` ci-dessous, jamais relire
# `_CATALOG` en pretendant que c'est une mesure a jour.
#
# Origine des nombres : mediane annuelle de la colonne "spread" des caches
# `C:/db/tradingBot/bars_cache/<symbole>_*.pkl` (colonne brute exprimee en
# POINTS de prix — 0,001 pour XAUUSD — convertie ici en pips au sens du
# catalogue, pip=0,01 pour XAUUSD). Mesure faite le 2026-09-06, identique en
# M15 (maille de reference retenue : intermediaire entre la cotation aux
# heures rondes et l'echantillonnage fin).
#
# ATTENTION — ces medianes NE SONT PAS identiques a toutes les mailles avant
# 2025, contrairement a ce qu'affirmait une premiere redaction. Mesure par
# maille :
#     annee    H1    M15    M5     M1
#     2021   50,0   50,0  51,0      -
#     2022   50,0   51,0  53,0      -
#     2023   50,0   54,0  56,0      -
#     2024   50,0   55,0  58,0   59,0
#     2025   65,0   65,0  65,0   65,0
#     2026   90,8   90,8  90,8   90,8
# En H1 la valeur reste collee au plancher du courtier : une barre horaire
# cote a l'heure ronde, moment liquide. Les mailles fines echantillonnent
# aussi les moments ou le spread s'ecarte. La convergence de 2025-2026
# s'explique par un plancher releve (82,8 points) que le spread ne quitte
# quasiment plus. Consequence pratique : pour valoriser une strategie a une
# maille donnee AVANT 2025, remesurer a cette maille plutot que de reprendre
# cette table telle quelle.
# Seul XAUUSD a ete mesure a ce jour ; les autres symboles n'ont pas encore
# d'entree ici (cf. comportement explicite de `measured_spread_pips` plus bas).
_MEASURED_SPREADS_PIPS: dict[str, dict[int, float]] = {
    "XAUUSD": {
        2021: 50.0,
        2022: 51.0,
        2023: 54.0,
        2024: 55.0,
        2025: 65.0,
        2026: 90.8,
    },
}


def measured_spread_pips(symbol: str, year: int | None = None) -> float:
    """
    Spread MESURE (median annuelle, en pips) pour `symbol`.

    `year=None` rend la valeur du regime courant, c'est-a-dire l'annee la
    plus recente presente dans la table de mesure (au 2026-09-06 : 2026,
    90,8 pips pour XAUUSD).

    Comportement volontairement strict, sans fallback silencieux : leve
    `KeyError` si `symbol` n'a aucune mesure enregistree, ou si `year` est
    demande explicitement mais absent de la table de ce symbole. Un retour
    silencieux (ex. repli automatique sur `_CATALOG`) masquerait un trou de
    mesure reel — mieux vaut un plantage explicite qu'un chiffre perime pris
    pour une mesure.
    """
    if symbol not in _MEASURED_SPREADS_PIPS:
        raise KeyError(
            f"aucun spread mesure enregistre pour '{symbol}'. "
            f"Symboles mesures : {sorted(_MEASURED_SPREADS_PIPS)}. "
            f"Mesurez-le (cf. docstring _MEASURED_SPREADS_PIPS) avant de "
            f"l'utiliser — pas de repli devine sur _CATALOG."
        )
    by_year = _MEASURED_SPREADS_PIPS[symbol]
    if year is None:
        year = max(by_year)
    if year not in by_year:
        raise KeyError(
            f"aucune mesure pour '{symbol}' en {year}. "
            f"Annees mesurees : {sorted(by_year)}."
        )
    return by_year[year]
