"""
Tests de l'outil studies/verify-journal.py — sur journaux fabriqués en
tmp_path, sans MT5, sans toucher C:/db (les vrais journaux ne sont JAMAIS
approchés par un test).

Ce qui est vérifié, et pourquoi :
  (a) INTACT      — un journal chaîné valide rend 0 (le GO de bascule).
  (b) DÉPLACÉ     — le MÊME journal copié dans un autre dossier rend 0 :
      la chaîne ne hache que le contenu, jamais le chemin. C'est LA
      propriété qui autorise le déplacement C:/db/tbot -> C:/db/tradingBot
      sans réinitialiser la collecte (studies/CUTOVER.md).
  (c) ALTÉRÉ      — un octet réécrit dans une ligne passée rend 4.
  (d) TRONQUÉ     — un journal raccourci après state.json rend 4.
  (e) INTROUVABLE — dossier ou journal absent rend 2 (pas une altération).
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from studies.gold_forward import forward_step as fs  # noqa: E402


def _tool():
    """Charge l'outil (tiret dans le nom -> pas importable en module)."""
    spec = importlib.util.spec_from_file_location(
        "verify_journal_tool", os.path.join(HERE, "verify-journal.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_journal(dirpath) -> fs.Paths:
    """Un journal chaîné VALIDE de 2 lignes + state.json cohérent, via les
    fonctions mêmes de l'étude (append_journal pose les maillons)."""
    p = fs.Paths(str(dirpath))
    p.ensure()
    fs.init_journal(p.journal)
    n, sha = fs.append_journal(p.journal, [
        {"measured_at_utc": "2026-08-26T00:00:00Z", "event": "OPEN",
         "trade_id": "T1", "side": "LONG"},
        {"measured_at_utc": "2026-08-26T01:00:00Z", "event": "CLOSE",
         "trade_id": "T1", "side": "LONG", "pnl_r": "+1.0000"},
    ])
    fs.save_state(p.state, {"schema": 1, "journal_bytes": n,
                            "journal_sha256": sha})
    return p


def test_journal_intact_rend_0(tmp_path, capsys):
    _make_journal(tmp_path)
    assert _tool().main(["gold_forward", "--dir", str(tmp_path)]) == 0
    assert "journal intact" in capsys.readouterr().out


def test_journal_deplace_rend_0(tmp_path):
    """La chaîne est indépendante du chemin absolu : le même contenu copié
    ailleurs se vérifie à l'identique — propriété de bascule (T10 point 4)."""
    src = tmp_path / "avant"
    dst = tmp_path / "apres" / "gold_forward"
    _make_journal(src)
    shutil.copytree(src, dst)
    assert _tool().main(["gold_forward", "--dir", str(dst)]) == 0


def test_journal_altere_rend_4(tmp_path, capsys):
    p = _make_journal(tmp_path)
    raw = open(p.journal, "rb").read()
    # Réécrit un octet dans la PREMIÈRE ligne de données (maillon passé).
    tampered = raw.replace(b"OPEN", b"OPXN", 1)
    assert tampered != raw
    with open(p.journal, "wb") as f:
        f.write(tampered)
    assert _tool().main(["gold_forward", "--dir", str(tmp_path)]) == 4
    assert "ALTÉRÉ" in capsys.readouterr().err


def test_journal_tronque_rend_4(tmp_path):
    p = _make_journal(tmp_path)
    raw = open(p.journal, "rb").read()
    with open(p.journal, "wb") as f:
        f.write(raw[: len(raw) - 10])
    assert _tool().main(["gold_forward", "--dir", str(tmp_path)]) == 4


def test_dossier_absent_rend_2(tmp_path, capsys):
    assert _tool().main(
        ["gold_forward", "--dir", str(tmp_path / "nexiste_pas")]) == 2
    assert "introuvable" in capsys.readouterr().err


def test_journal_absent_rend_2(tmp_path):
    (tmp_path / "vide").mkdir()
    assert _tool().main(["gold_forward", "--dir", str(tmp_path / "vide")]) == 2


def test_sans_state_verifie_chaine_seule(tmp_path, capsys):
    """state.json absent -> la chaîne interne reste vérifiée (0 si intacte),
    avec avertissement — cas d'un journal inspecté hors de son dossier vivant."""
    p = _make_journal(tmp_path)
    os.remove(p.state)
    assert _tool().main(["gold_forward", "--dir", str(tmp_path)]) == 0
    assert "state.json absent" in capsys.readouterr().err
