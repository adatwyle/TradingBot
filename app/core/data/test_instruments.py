"""
Tests du catalogue d'instruments (`core/data/instruments.py`).

POURQUOI ce banc existe : `_CATALOG["XAUUSD"]["spread_pips"]` (25,0 pips) est
une valeur FIGEE citee telle quelle par `studies/gold_forward/PROTOCOL.md`
section 2.2 (etude scellee, en cours depuis le 14 aout 2026). Le spread REEL
mesure sur les caches a depuis derive (90,8 pips medians sur les 365 derniers
jours, mesure du 2026-09-06) — un ecart de x3,6 avec la valeur du catalogue.
`measured_spread_pips()` rend ce spread mesure SANS toucher a la constante
historique. Le premier test ci-dessous est un test de NON-REGRESSION : il
protege `studies/gold_forward` d'un futur commit qui "corrigerait" par erreur
`_CATALOG["XAUUSD"]["spread_pips"]` pour le faire coller a la mesure — ce qui
deplacerait retroactivement le cout de valorisation d'un test deja en cours.

    pytest app/core/data/test_instruments.py -q
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from core.data.instruments import get_spec, measured_spread_pips


def test_catalogue_xauusd_spread_reste_fige_a_25_pips():
    """
    Non-regression : `studies/gold_forward/PROTOCOL.md` §2.2 cite cette
    valeur telle quelle pour un test scelle en cours depuis le 14 aout 2026.
    Si ce test casse, quelqu'un a touche `_CATALOG["XAUUSD"]["spread_pips"]`
    — NE PAS "corriger" cette assertion, corriger le commit qui a modifie le
    catalogue (cf. docstring de `_MEASURED_SPREADS_PIPS` dans instruments.py).
    """
    assert get_spec("XAUUSD").spread_pips == 25.0


def test_measured_spread_regime_courant_xauusd():
    # Omission de l'annee -> regime courant (2026, mesure du 2026-09-06).
    assert measured_spread_pips("XAUUSD") == pytest.approx(90.8)
    assert measured_spread_pips("XAUUSD", year=2026) == pytest.approx(90.8)


@pytest.mark.parametrize(
    "year, attendu",
    [
        (2021, 50.0),
        (2022, 51.0),
        (2023, 54.0),
        (2024, 55.0),
        (2025, 65.0),
        (2026, 90.8),
    ],
)
def test_measured_spread_annees_connues_xauusd(year, attendu):
    assert measured_spread_pips("XAUUSD", year=year) == pytest.approx(attendu)


def test_measured_spread_symbole_inconnu_leve():
    # Comportement explicite choisi : lever, jamais de repli silencieux sur
    # _CATALOG (masquerait un trou de mesure reel).
    with pytest.raises(KeyError):
        measured_spread_pips("EURUSD")


def test_measured_spread_annee_inconnue_leve():
    with pytest.raises(KeyError):
        measured_spread_pips("XAUUSD", year=2020)
