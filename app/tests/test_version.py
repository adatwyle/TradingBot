"""
Tests de core/version.py — parsing du fichier VERSION racine (SPEC_ci-cd CI-T1).

POURQUOI ce banc : la CI (job publish), le watcher prod et l'UI lisent tous la
même source de version. Un contenu invalide doit être une erreur explicite —
jamais un tag ou un affichage silencieusement faux.

    pytest tests/test_version.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.version import DEFAULT_VERSION_FILE, read_version  # noqa: E402


def test_format_valide(tmp_path):
    f = tmp_path / "VERSION"
    f.write_text("1.0.0\n", encoding="utf-8")
    assert read_version(f) == "1.0.0"


def test_format_valide_multi_digits(tmp_path):
    f = tmp_path / "VERSION"
    f.write_text("12.34.567", encoding="utf-8")
    assert read_version(f) == "12.34.567"


@pytest.mark.parametrize("contenu", [
    "",                # vide
    "1.0",             # BUILD manquant
    "v1.0.0",          # préfixe v interdit (le tag l'ajoute, pas le fichier)
    "1.0.0-rc1",       # suffixe interdit
    "1.0.0.0",         # quatre segments
    "abc",             # pas une version
    "1 . 0 . 0",       # espaces internes
])
def test_format_invalide(tmp_path, contenu):
    f = tmp_path / "VERSION"
    f.write_text(contenu, encoding="utf-8")
    with pytest.raises(ValueError):
        read_version(f)


def test_fichier_absent(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_version(tmp_path / "VERSION")


def test_fichier_racine_reel_est_valide():
    # Le VERSION du repo doit toujours être lisible : c'est lui que la CI tagge.
    assert read_version() == read_version(DEFAULT_VERSION_FILE)
