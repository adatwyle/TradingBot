"""
Tests de core/paths.py — la résolution UNIQUE de racine projet et d'état vivant.

POURQUOI ce banc : la migration E2 a déplacé le code dans app/ tandis que
strategies/ et studies/ restent à la racine projet. Chaque module du prototype
résolvait « la racine » comme le parent de son propre dossier — heuristique
morte avec le nouveau layout. La résolution vit désormais dans core/paths.py,
et ce banc la fige.

Il porte aussi le TEST DE RÉGRESSION du panneau : dans le prototype, la
factory écrivait les AUTO-OFF dans <db>/robinbot-panel.txt alors que notify
et pilot lisaient par défaut orchestrator/robinbot-panel.txt — un incident
pouvait éteindre un worker sans que les lecteurs le voient. Les trois modules
doivent résoudre LE MÊME chemin par défaut.

    pytest tests/test_paths.py -q
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core import paths  # noqa: E402

_ORCH = pathlib.Path(APP_DIR) / "orchestrator"

# Les seams d'environnement qui influencent la résolution : on les neutralise
# pour tester les DÉFAUTS, on les pose pour tester les surcharges.
_SEAMS = ("TBOT_PROJECT_ROOT", "TBOT_DB_DIR", "RBF_PANEL", "RBF_ROOT",
          "RBF_CATALOGUE")


def _sans_seams(monkeypatch):
    for k in _SEAMS:
        monkeypatch.delenv(k, raising=False)


def _charger(nom: str):
    """Charge un module orchestrateur à nom-à-tiret par chemin (leur forme
    d'import canonique dans les bancs du dépôt)."""
    spec = importlib.util.spec_from_file_location(
        nom.replace("-", "_") + "_paths_test", _ORCH / f"{nom}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# == LES DÉFAUTS ===============================================================
def test_project_root_par_defaut_est_le_parent_de_app(monkeypatch):
    _sans_seams(monkeypatch)
    assert paths.project_root() == pathlib.Path(APP_DIR).parent
    assert paths.app_root() == pathlib.Path(APP_DIR)


def test_db_dir_par_defaut_est_tradingbot_jamais_tbot(monkeypatch):
    """C:/db/tbot appartient au prototype EN EXPLOITATION — le nouveau code ne
    doit jamais y retomber par défaut."""
    _sans_seams(monkeypatch)
    assert paths.db_dir() == pathlib.Path(r"C:\db\tradingBot")
    assert "tbot" not in str(paths.db_dir()).lower().split("tradingbot")[0] \
        or str(paths.db_dir()).endswith("tradingBot")


def test_panel_par_defaut_dans_db_dir(monkeypatch):
    _sans_seams(monkeypatch)
    # Construit comme le code (base / nom) : portable Windows ET runner Linux CI.
    assert paths.panel_file() == pathlib.Path(r"C:\db\tradingBot") / "robinbot-panel.txt"


# == LES SURCHARGES (le seam de testabilité) ===================================
def test_surcharges_env(monkeypatch, tmp_path):
    _sans_seams(monkeypatch)
    monkeypatch.setenv("TBOT_PROJECT_ROOT", str(tmp_path / "racine"))
    monkeypatch.setenv("TBOT_DB_DIR", str(tmp_path / "db"))
    assert paths.project_root() == tmp_path / "racine"
    assert paths.db_dir() == tmp_path / "db"
    # RBF_ROOT prime sur TBOT_PROJECT_ROOT : c'est LE seam sandbox historique
    # de la factory, et il doit piloter TOUS les consommateurs.
    monkeypatch.setenv("RBF_ROOT", str(tmp_path / "sandbox"))
    assert paths.project_root() == tmp_path / "sandbox"
    monkeypatch.delenv("RBF_ROOT", raising=False)
    # Sans RBF_PANEL, le panneau suit db_dir.
    assert paths.panel_file() == tmp_path / "db" / "robinbot-panel.txt"
    # RBF_PANEL prime sur tout.
    monkeypatch.setenv("RBF_PANEL", str(tmp_path / "p.txt"))
    assert paths.panel_file() == tmp_path / "p.txt"


# == RÉGRESSION : RBF_ROOT PILOTE AUSSI LE SERVEUR ET LES TOOLS ================
def test_rbf_root_seul_pilote_factory_serveur_et_tools(monkeypatch, tmp_path):
    """Défaut relevé en revue : les scripts orchestrateur honoraient RBF_ROOT
    mais server/app.py et tools/new_strategy.py appelaient project_root() nu —
    un lancement sandboxé via RBF_ROOT seul faisait lire au serveur les
    manifests de la VRAIE racine. RBF_ROOT vit désormais DANS project_root()
    et doit suffire, seul, à orienter les trois."""
    _sans_seams(monkeypatch)
    racine = tmp_path / "sandbox"
    sdir = racine / "strategies" / "s99_sonde"
    sdir.mkdir(parents=True)
    (sdir / "manifest.yaml").write_text(
        'strategy_id: s99_sonde\ndisplay_name: "Sonde"\n'
        "magic_number: 130099\nstatus: RESEARCH\n", encoding="utf-8")
    monkeypatch.setenv("RBF_ROOT", str(racine))

    # La factory.
    factory = _charger("robinbot-factory")
    assert factory.ROOT == racine

    # Le serveur de supervision : il doit découvrir la stratégie de la sandbox.
    # (refonte SPEC_ui-dynamique : la découverte vit dans server/state.py et
    # se résout À L'APPEL via core.paths — RBF_ROOT doit suffire, seul.)
    from server.state import build_card, scan_strategy_folders
    assert scan_strategy_folders() == ["s99_sonde"]
    carte = build_card("s99_sonde", spark=False)
    assert carte["name"] == "Sonde" and carte["magic"] == 130099

    # L'outil de scaffolding : même racine pour le gabarit et la création.
    spec = importlib.util.spec_from_file_location(
        "new_strategy_paths_test", pathlib.Path(APP_DIR) / "tools" / "new_strategy.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    assert pathlib.Path(tool.ROOT) == racine


# == RÉGRESSION : UN SEUL PANNEAU POUR FACTORY, NOTIFY ET PILOT ================
def test_factory_notify_pilot_resolvent_le_meme_panneau(monkeypatch):
    """Défaut documenté du prototype : la factory écrivait ses AUTO-OFF dans
    <db>/robinbot-panel.txt, notify et pilot lisaient orchestrator/robinbot-
    panel.txt. Les trois doivent résoudre LE MÊME fichier par défaut."""
    _sans_seams(monkeypatch)
    factory = _charger("robinbot-factory")
    notify = _charger("robinbot-notify")
    pilot = _charger("robinbot-pilot")

    attendu = pathlib.Path(r"C:\db\tradingBot") / "robinbot-panel.txt"
    assert factory.PANEL_FILE == attendu
    assert pathlib.Path(notify.panel_path()) == attendu
    assert pilot.PANEL_FILE == attendu


def test_rbf_panel_suivi_par_les_trois(monkeypatch, tmp_path):
    """La surcharge RBF_PANEL (seam des tests, réglage par poste) reste
    fonctionnelle et identique pour les trois modules."""
    _sans_seams(monkeypatch)
    monkeypatch.setenv("RBF_PANEL", str(tmp_path / "panel.txt"))
    factory = _charger("robinbot-factory")
    notify = _charger("robinbot-notify")
    pilot = _charger("robinbot-pilot")
    assert factory.PANEL_FILE == tmp_path / "panel.txt"
    assert pathlib.Path(notify.panel_path()) == tmp_path / "panel.txt"
    assert pilot.PANEL_FILE == tmp_path / "panel.txt"


# == LE CATALOGUE PAR DÉFAUT DE LA FACTORY =====================================
def test_catalogue_workers_app_existent_studies_declarables(monkeypatch):
    """Les workers de la plateforme (migrés E2) doivent pointer des fichiers
    RÉELS sous la racine projet ; les workers d'études restent DÉCLARABLES
    (non migrés avant E3/E6) mais le gabarit du panneau les livre off — le
    panneau fail-closed couvre le reste (absent = OFF)."""
    _sans_seams(monkeypatch)
    factory = _charger("robinbot-factory")

    migres = {"gateway", "pilot", "portier", "mesureur", "notify", "supervision"}
    etudes = {"gold_forward", "s13_forward", "macd_ai_paper", "s14_sentiment",
              "alexg_paper"}
    noms = set(factory.WORKER_NAMES)
    assert migres <= noms
    assert etudes <= noms            # déclarables, même sans fichiers studies/

    for name in migres:
        _n, _cwd, spec, _i, _k = factory.WORKER_BY_NAME[name]
        rel = spec[3:].split()[0]
        assert (factory.ROOT / rel).exists(), f"{name}: {rel} absent de la racine"

    # Le gabarit du panneau (source du panneau d'une machine neuve) livre les
    # études OFF et les workers migrés ON.
    gabarit = (_ORCH / "robinbot-panel.exemple.txt").read_text(encoding="utf-8-sig")
    regles = {}
    for brute in gabarit.splitlines():
        ligne = brute.split("#", 1)[0].strip()
        if "=" in ligne:
            nom, _, val = ligne.partition("=")
            regles[nom.strip()] = val.strip().lower()
    for name in etudes:
        assert regles.get(name) == "off", f"{name} doit être off dans le gabarit"
    for name in migres:
        assert regles.get(name) == "on", f"{name} doit être on dans le gabarit"
