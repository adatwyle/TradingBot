"""
Tests de la garde « premier passage » des runners d'études (F4, phase X).

POURQUOI ce banc : un journal ABSENT au lancement d'un runner signifie une
étude PAS ENCORE BASCULÉE (studies/CUTOVER.md) — le journal vivant est encore
dans le prototype. Sans garde, le runner démarrerait un PREMIER PASSAGE et
écrirait un journal neuf : deux journaux parallèles pour la même étude,
l'entrelacement que le protocole interdit. La garde refuse (sortie 2) sauf
autorisation explicite TBOT_ALLOW_FIRST_PASS=1 (étude réellement neuve) ;
une étude déjà basculée (journal présent) passe sans variable.

    pytest studies/test_first_pass_guard.py -q
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from studies.first_pass import first_pass_refused  # noqa: E402

# (module runner, seam du dossier d'état, nom d'étude)
RUNNERS = [
    ("studies.gold_forward.run_forward",   "GOLD_FORWARD_DIR",  "gold_forward"),
    ("studies.s13_forward.run_forward",    "S13_FORWARD_DIR",   "s13_forward"),
    ("studies.macd_ai_paper.run_paper",    "MACD_AI_PAPER_DIR", "macd_ai_paper"),
    ("studies.alexg_paper.run_paper",      "ALEXG_PAPER_DIR",   "alexg_paper"),
    ("studies.s14_sentiment.run_sentiment", "S14_SENTIMENT_DIR", "s14_sentiment"),
]


# == LE HELPER LUI-MÊME ========================================================
def test_garde_declenchee_journal_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TBOT_ALLOW_FIRST_PASS", raising=False)
    jp = str(tmp_path / "journal.csv")
    assert first_pass_refused(jp, "gold_forward") is True
    err = capsys.readouterr().err
    assert "premier passage refusé" in err
    assert "CUTOVER" in err and "TBOT_ALLOW_FIRST_PASS" in err


def test_garde_levee_par_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TBOT_ALLOW_FIRST_PASS", "1")
    assert first_pass_refused(str(tmp_path / "journal.csv"), "x") is False
    assert capsys.readouterr().err == ""


def test_etude_existante_passe_sans_env(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TBOT_ALLOW_FIRST_PASS", raising=False)
    jp = tmp_path / "journal.csv"
    jp.write_text("en-tete\n", encoding="utf-8")
    assert first_pass_refused(str(jp), "x") is False
    assert capsys.readouterr().err == ""


# == LES 5 RUNNERS SORTENT EN 2 SUR JOURNAL ABSENT =============================
@pytest.mark.parametrize("module_name,seam,etude", RUNNERS)
def test_runner_refuse_le_premier_passage(module_name, seam, etude,
                                          tmp_path, monkeypatch, capsys):
    """Dossier d'état vide (aucun journal), pas d'autorisation → sortie 2
    AVANT toute écriture (le dossier reste vide) et AVANT tout accès MT5."""
    monkeypatch.delenv("TBOT_ALLOW_FIRST_PASS", raising=False)
    ddir = tmp_path / etude
    ddir.mkdir()
    monkeypatch.setenv(seam, str(ddir))
    mod = importlib.import_module(module_name)

    assert mod.main([]) == 2
    assert "premier passage refusé" in capsys.readouterr().err
    assert list(ddir.iterdir()) == []               # rien écrit


@pytest.mark.parametrize("module_name,seam,etude", RUNNERS)
def test_runner_appelle_la_garde_avant_execution(module_name, seam, etude):
    """L'étude basculée (journal présent) doit passer SANS variable d'env —
    vérifié statiquement : la garde est branchée sur paths.journal avant
    run_step/run_pass (l'exécution complète exigerait MT5/Finnhub)."""
    mod = importlib.import_module(module_name)
    src = open(mod.__file__, encoding="utf-8").read()
    assert "first_pass_refused(paths.journal" in src
