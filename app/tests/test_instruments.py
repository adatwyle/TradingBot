"""
Tests de core/data/instruments.py — le catalogue d'instruments.

POURQUOI ce banc : aucun test ne couvrait encore ce module avant l'ajout de
US30 (2026-09-12, cf. docs/data/INDICES_intraday_2026-09-12.md). Il fige le
contrat minimal : chaque symbole connu doit être servi par get_spec(), et
US30 doit être présent avec la convention pip=0.1 partagée par les autres
indices CFD (NASDAQ, DAX, SP500 — mêmes digits=2/point=0.01 côté MT5).

    pytest tests/test_instruments.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.data.instruments import get_spec, known_symbols  # noqa: E402


def test_us30_in_known_symbols():
    assert "US30" in known_symbols()


def test_us30_pip_matches_index_convention():
    spec = get_spec("US30")
    assert spec.pip == 0.1


def test_us30_max_spread_wider_than_spread():
    spec = get_spec("US30")
    assert spec.max_spread_pips > spec.spread_pips > 0


def test_known_symbols_sorted_and_nonempty():
    symbols = known_symbols()
    assert symbols == sorted(symbols)
    assert len(symbols) > 0


def test_get_spec_unknown_symbol_raises_keyerror():
    with pytest.raises(KeyError):
        get_spec("NOT_A_REAL_SYMBOL")


def test_get_spec_symbol_field_matches_lookup_key():
    for sym in ("US30", "NASDAQ", "DAX", "SP500", "EURUSD"):
        assert get_spec(sym).symbol == sym
