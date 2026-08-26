"""
Tests de la factory — le superviseur lui-même.

POURQUOI ce banc existe (tardivement) : l'arrêt propre par `.stop` restait
bloqué pour toujours, parce qu'il attendait la fin de TOUS les workers alors
qu'un service persistant ne finit jamais. Le bug s'est révélé à la main le
2026-08-18, pas au banc — il n'y avait pas de banc. On couvre donc en
priorité ce qui décide : qui part, qui s'arrête, ce que dit le panneau.

Le catalogue est injecté par `RBF_CATALOGUE` (seam prévu dans le module) :
aucun vrai runner scellé n'est jamais lancé ici.

    pytest orchestrator/test_robinbot_factory.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import time

import pytest

_HERE = pathlib.Path(__file__).resolve().parent


def _charger(tmp: pathlib.Path, catalogue: list[dict]):
    """Recharge le module avec un catalogue jetable (il est lu à l'import)."""
    os.environ["RBF_CATALOGUE"] = json.dumps(catalogue)
    os.environ["RBF_ROOT"] = str(tmp)
    os.environ["RBF_PANEL"] = str(tmp / "panel.txt")
    os.environ["RBF_LOG_DIR"] = str(tmp / "logs")
    os.environ["RBF_LOCK"] = str(tmp / ".lock")
    os.environ["RBF_STOP"] = str(tmp / ".stop")
    spec = importlib.util.spec_from_file_location(
        "robinbot_factory_test", _HERE / "robinbot-factory.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CATALOGUE = [
    {"name": "etude", "spec": "py:studies/x/run.py", "interval": 3600, "kind": "tick"},
    {"name": "serveur", "spec": "py:server/app.py", "interval": 60, "kind": "service"},
]


@pytest.fixture
def usine(tmp_path):
    mod = _charger(tmp_path, CATALOGUE)
    yield mod
    for k in ("RBF_CATALOGUE", "RBF_ROOT", "RBF_PANEL", "RBF_LOG_DIR",
              "RBF_LOCK", "RBF_STOP"):
        os.environ.pop(k, None)


class FauxProc:
    def __init__(self, pid=4242):
        self.pid = pid


# == L'ARRÊT PROPRE (le bug du 2026-08-18) =====================================
def test_un_service_en_vol_ne_bloque_pas_l_arret(usine):
    """Le drain n'attend QUE les ticks : attendre un service persistant, c'est
    attendre pour toujours."""
    usine._running["serveur"] = FauxProc()
    assert usine._ticks_en_vol() == []          # le service ne compte pas

    usine._running["etude"] = FauxProc(4243)
    assert usine._ticks_en_vol() == ["etude"]   # le tick, si


def test_arreter_services_ne_tue_que_les_services(usine, monkeypatch):
    tues = []
    monkeypatch.setattr(usine.subprocess, "run",
                        lambda cmd, **kw: tues.append(cmd[2]))
    usine._running["serveur"] = FauxProc(111)
    usine._running["etude"] = FauxProc(222)
    usine.arreter_services()
    assert tues == ["111"]                      # le tick de mesure est épargné


# == LE PANNEAU ================================================================
def test_worker_absent_du_panneau_est_off(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("etude = on\n", encoding="utf-8")
    panel = usine.read_panel()
    assert usine.due("etude", panel, time.time()) is True
    assert usine.due("serveur", panel, time.time()) is False   # absent = OFF


def test_panneau_introuvable_eteint_tout(usine, tmp_path):
    (tmp_path / "panel.txt").unlink(missing_ok=True)
    panel = usine.read_panel()
    assert panel == {}
    assert usine.due("etude", panel, time.time()) is False


def test_cadence_forcee_et_ligne_illisible(usine, tmp_path):
    (tmp_path / "panel.txt").write_text(
        "etude = on:120\nserveur = on:pouet\n# commentaire\nordure\n",
        encoding="utf-8")
    panel = usine.read_panel()
    assert panel["etude"] == (True, 120)
    assert panel["serveur"] == (True, None)     # cadence illisible -> catalogue
    assert "ordure" not in panel


def test_off_respecte(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("etude = off\n", encoding="utf-8")
    assert usine.due("etude", usine.read_panel(), time.time()) is False


# == QUI PART, QUAND ===========================================================
def test_pas_deux_ticks_du_meme_worker(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("etude = on\n", encoding="utf-8")
    panel = usine.read_panel()
    usine._running["etude"] = FauxProc()
    assert usine.due("etude", panel, time.time()) is False


def test_cadence_respectee(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("etude = on:100\n", encoding="utf-8")
    panel = usine.read_panel()
    maintenant = time.time()
    usine._last_run["etude"] = maintenant
    assert usine.due("etude", panel, maintenant + 50) is False
    assert usine.due("etude", panel, maintenant + 101) is True


# == CONSTRUCTION DES COMMANDES ================================================
def test_build_cmd_script_et_module(usine, tmp_path):
    # Sans __init__.py : lancement en script.
    cmd = usine.build_cmd("py:studies/x/run.py")
    assert cmd[0] == usine.PYTHON and cmd[1].endswith("run.py")

    # Chaîne de packages complète : lancement en -m (forme des .bat d'origine).
    for d in (tmp_path / "studies", tmp_path / "studies" / "x"):
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").write_text("", encoding="utf-8")
    assert usine.build_cmd("py:studies/x/run.py")[1:3] == ["-m", "studies.x.run"]


def test_build_cmd_claude_passe_par_cmd(usine):
    """Sous Windows `claude` est un shim .cmd : CreateProcess ne résout pas un
    argv nu."""
    cmd = usine.build_cmd("claude:analyse")
    assert cmd[:2] == ["cmd", "/c"] and "--output-format" in cmd


def test_spec_inconnue_refusee(usine):
    with pytest.raises(ValueError):
        usine.build_cmd("bash:rm -rf /")


# == INCIDENTS ET VERROU =======================================================
def test_incident_eteint_le_worker_dans_le_panneau(usine, tmp_path):
    (tmp_path / "panel.txt").write_text("etude = on\nserveur = on\n",
                                        encoding="utf-8")
    usine.panel_set_off("etude", "sortie 3 — SCELLÉ VIOLÉ")
    texte = (tmp_path / "panel.txt").read_text(encoding="utf-8")
    assert "etude = off" in texte and "AUTO-OFF" in texte
    assert "serveur = on" in texte                  # le reste intact
    assert usine.read_panel()["etude"][0] is False


def test_verrou_frais_puis_perime(usine, tmp_path):
    usine.write_lock()
    assert usine.lock_is_fresh() is True
    vieux = time.time() - (usine.LOCK_STALE_SEC + 10)
    os.utime(tmp_path / ".lock", (vieux, vieux))
    assert usine.lock_is_fresh() is False           # factory morte : on passe


def test_stop_present_refuse_de_demarrer(usine, tmp_path):
    (tmp_path / ".stop").write_text("", encoding="utf-8")
    assert usine.stop_requested() is True
    assert usine.run(dry=True, once=True) == 1      # refus explicite
