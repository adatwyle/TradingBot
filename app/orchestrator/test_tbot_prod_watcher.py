"""
Tests du prod-watcher — mise à jour automatique du PC prod (SPEC_prod-watcher
+ gate `update_safe`, directive Adrian GO 2026-08-26).

Ce banc couvre ce qui DÉCIDE : détection SHA + pull ff (PW-T1), non-
redémarrage sur diff db-backup/ seul (D-PW-5), gate update_safe (blocage,
raison, alerte au seuil, déblocage), rollback sur tests rouges + anti-boucle
SHA fautif (PW-T2), checkout sale → aucun pull (PW-T3), arrêt propre `.stop`
et arrêt forcé au timeout (PW-T4), verrou single-instance (PW-3).

TOUT git vit dans un dépôt JETABLE en tmp_path (deux clones : « remote » où
la CI publie, « local » = le checkout prod), branché par TBOT_PROJECT_ROOT.
AUCUNE commande git ne touche jamais le dépôt de travail — un garde-fou le
vérifie à chaque chargement du module. Telegram est mocké (aucun réseau).

    pytest app/orchestrator/test_tbot_prod_watcher.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_REAL_REPO = _HERE.parents[1]                     # C:/projects/tradingBot

_ENV_KEYS = (
    "TBOT_PROJECT_ROOT", "RBF_ROOT", "TBOT_DB_DIR", "TBOT_WATCH_DIR",
    "TBOT_WATCH_POLL", "TBOT_WATCH_STOP_TIMEOUT", "TBOT_WATCH_GATE_ALERT",
    "TBOT_WATCH_LOCK", "TBOT_WATCH_LOCK_STALE", "TBOT_WATCH_LOG_DIR",
    "TBOT_WATCH_FACTORY_CMD", "TBOT_WATCH_PYTEST_CMD", "TBF_STOP", "RBF_STOP",
    "TBF_LOG_DIR", "TBF_LOCK", "TBOT_NOTIFY_DIR", "TBOT_WATCH_CRASH_BACKOFF",
    "TBOT_WATCH_PYTEST_TIMEOUT",
)

PY_GREEN = [sys.executable, "-c", "raise SystemExit(0)"]
PY_RED = [sys.executable, "-c", "raise SystemExit(1)"]


def _git(cwd: pathlib.Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-c", "user.email=test@test", "-c", "user.name=test",
         "-c", "commit.gpgsign=false", *args],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git {args} : {r.stderr}"
    return r.stdout.strip()


class Depots:
    """Deux dépôts jetables : `remote` (où la CI publie main) et `local`
    (le checkout prod, cloné du remote)."""

    def __init__(self, tmp: pathlib.Path):
        self.remote = tmp / "remote"
        self.local = tmp / "local"
        _git(tmp, "init", "-b", "main", str(self.remote))
        self.commit_remote("a.txt", "v1", "c1: initial")
        _git(tmp, "clone", str(self.remote), str(self.local))

    def commit_remote(self, rel: str, contenu: str, msg: str) -> str:
        """Un commit publié sur origin/main (côté remote)."""
        f = self.remote / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contenu, encoding="utf-8")
        _git(self.remote, "add", "-A")
        _git(self.remote, "commit", "-m", msg)
        return _git(self.remote, "rev-parse", "HEAD")

    def sha_local(self) -> str:
        return _git(self.local, "rev-parse", "HEAD")

    def sha_remote(self) -> str:
        return _git(self.remote, "rev-parse", "HEAD")


@pytest.fixture
def env(tmp_path):
    """Environnement jetable complet + module watcher rechargé (état mémoire
    vierge : _alerted, _gate_since)."""
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    depots = Depots(tmp_path)
    db = tmp_path / "db"
    db.mkdir()
    os.environ["TBOT_PROJECT_ROOT"] = str(depots.local)
    os.environ["TBOT_DB_DIR"] = str(db)
    os.environ["TBOT_WATCH_DIR"] = str(db / "watcher")
    os.environ["TBOT_WATCH_LOCK"] = str(tmp_path / ".wlock")
    os.environ["TBOT_WATCH_LOG_DIR"] = str(tmp_path / "logs")
    os.environ["TBF_STOP"] = str(tmp_path / ".stop")
    os.environ["TBF_LOCK"] = str(tmp_path / ".tbot-factory.lock")
    os.environ["TBOT_NOTIFY_DIR"] = str(tmp_path / "notifier-absent")
    os.environ["TBOT_WATCH_PYTEST_CMD"] = json.dumps(PY_GREEN)
    os.environ["TBOT_WATCH_FACTORY_CMD"] = json.dumps(
        [sys.executable, "-c", "import time; time.sleep(60)"])

    spec = importlib.util.spec_from_file_location(
        "tbot_prod_watcher_test", _HERE / "tbot-prod-watcher.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # GARDE-FOU : jamais une commande git sur le dépôt de travail réel.
    assert mod.project_root() == depots.local
    assert mod.project_root() != _REAL_REPO

    mod.depots = depots
    mod.tmp = tmp_path
    yield mod
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


class FauxProc:
    """Une factory « vivante » sans processus réel."""

    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode


@pytest.fixture
def calme(env, monkeypatch):
    """Telegram + factory mockés : sends/starts/stops enregistrés."""
    sends, starts, stops = [], [], []
    monkeypatch.setattr(env, "send_telegram", lambda t: sends.append(t))
    monkeypatch.setattr(env, "start_factory",
                        lambda: starts.append(1) or FauxProc())
    monkeypatch.setattr(env, "stop_factory",
                        lambda p: stops.append(p) or True)
    env.sends, env.starts, env.stops = sends, starts, stops
    return env


def _status(env) -> dict:
    return json.loads(
        (pathlib.Path(os.environ["TBOT_WATCH_DIR"]) / "status.json")
        .read_text(encoding="utf-8"))


# == PW-T1 : détection SHA différent + pull ff + status.json ===================
def test_a_jour_puis_update_complet(calme):
    m = calme
    proc = FauxProc()

    # à jour : rien ne bouge
    proc, result, detail = m.check_cycle(proc)
    assert result == "up-to-date"
    st = _status(m)
    assert st["schema"] == 1 and st["last_result"] == "up-to-date"
    assert st["current_sha"] == st["remote_sha"] == m.depots.sha_local()
    assert st["factory_alive"] is True

    # la CI publie c2 (code) : arrêt propre, pull ff, tests verts, relance
    c2 = m.depots.commit_remote("a.txt", "v2", "c2: code change")
    proc, result, detail = m.check_cycle(proc)
    assert result == "updated"
    assert m.depots.sha_local() == c2                  # pull ff effectué
    assert m.stops and m.starts                        # stop puis relance
    st = _status(m)
    assert st["last_result"] == "updated"
    assert st["current_sha"] == c2
    assert st["last_update_utc"]                       # horodaté (PW-8)


# == D-PW-5 : diff limité à db-backup/ → pull SANS redémarrage =================
def test_db_backup_seul_pull_sans_redemarrage(env, monkeypatch):
    m = env
    monkeypatch.setattr(m, "send_telegram", lambda t: None)
    monkeypatch.setattr(
        m, "stop_factory",
        lambda p: pytest.fail("db-backup seul : la console ne doit PAS s'arrêter"))
    monkeypatch.setattr(
        m, "start_factory",
        lambda: pytest.fail("db-backup seul : aucune relance attendue"))

    c2 = m.depots.commit_remote("db-backup/S017/journal.csv", "x", "backup")
    proc = FauxProc()
    proc2, result, detail = m.check_cycle(proc)
    assert result == "updated"
    assert "sans redémarrage" in detail
    assert m.depots.sha_local() == c2
    assert proc2 is proc                               # même processus
    assert not m.stop_file().exists()                  # jamais de .stop posé


# == GATE update_safe (directive Adrian 2026-08-26) ============================
def _status_instance(db: pathlib.Path, short: str, inst: str, **champs):
    d = db / short / inst
    d.mkdir(parents=True, exist_ok=True)
    doc = {"schema": 1, "instance": inst, "mode": "PAPER",
           "generated_at_utc": "2026-08-26T12:00:00Z"}
    doc.update(champs)
    (d / "status.json").write_text(json.dumps(doc), encoding="utf-8")


def test_gate_blockers_scan(env):
    m = env
    db = pathlib.Path(os.environ["TBOT_DB_DIR"])
    assert m.gate_blockers() == []                     # db vide = safe

    # champ absent = safe (contrat UI : les RESEARCH n'écrivent rien)
    _status_instance(db, "S013", "S013.AUD-CAD")
    # update_safe true = safe
    _status_instance(db, "S017", "S017.SPY", update_safe=True)
    # étude profondeur 1, illisible = safe
    (db / "gold_forward").mkdir()
    (db / "gold_forward" / "status.json").write_text("{pas du json",
                                                     encoding="utf-8")
    assert m.gate_blockers() == []

    # refus explicite : bloque, avec source et raison
    _status_instance(db, "S013", "S013.AUD-CAD",
                     update_safe=False, update_safe_reason="position ouverte")
    blockers = m.gate_blockers()
    assert len(blockers) == 1
    assert blockers[0]["source"] == "S013/S013.AUD-CAD"
    assert blockers[0]["reason"] == "position ouverte"


def test_gate_bloque_puis_debloque(calme, monkeypatch):
    m = calme
    db = pathlib.Path(os.environ["TBOT_DB_DIR"])
    _status_instance(db, "S013", "S013.AUD-CAD",
                     update_safe=False, update_safe_reason="décision d'entrée en cours")
    c2 = m.depots.commit_remote("a.txt", "v2", "c2: code change")
    ancien = m.depots.sha_local()

    # bloqué : AUCUN .stop, AUCUN pull, re-check au poll suivant
    monkeypatch.setattr(
        m, "stop_factory",
        lambda p: pytest.fail("gate bloqué : la factory ne doit pas s'arrêter"))
    proc = FauxProc()
    proc, result, detail = m.check_cycle(proc)
    assert result == "gate-blocked"
    assert "décision d'entrée en cours" in detail
    assert m.depots.sha_local() == ancien              # pas de pull
    assert m.sends == []                               # sous le seuil : pas d'alerte
    assert _status(m)["last_result"] == "gate-blocked"

    # seuil d'alerte franchi (seam à 0 s) : UNE alerte, pas de spam
    os.environ["TBOT_WATCH_GATE_ALERT"] = "0"
    proc, result, _ = m.check_cycle(proc)
    assert result == "gate-blocked"
    assert len(m.sends) == 1 and "update_safe" in m.sends[0]
    proc, result, _ = m.check_cycle(proc)
    assert len(m.sends) == 1                           # dédoublonnée

    # la stratégie redevient safe → l'update part
    monkeypatch.setattr(m, "stop_factory", lambda p: m.stops.append(p) or True)
    _status_instance(db, "S013", "S013.AUD-CAD", update_safe=True)
    proc, result, detail = m.check_cycle(proc)
    assert result == "updated"
    assert m.depots.sha_local() == c2


# == PW-T2 : rollback sur tests rouges + anti-boucle SHA fautif ================
def test_rollback_et_antiboucle(calme):
    m = calme
    c1 = m.depots.sha_local()
    c2 = m.depots.commit_remote("a.txt", "v2", "c2: casse les tests")
    os.environ["TBOT_WATCH_PYTEST_CMD"] = json.dumps(PY_RED)

    proc, result, detail = m.check_cycle(FauxProc())
    assert result == "rolled-back"
    assert m.depots.sha_local() == c1                  # reset --hard OLD_SHA
    assert m.load_state()["bad_sha"] == c2             # SHA fautif mémorisé
    assert any("ROLLBACK" in s for s in m.sends)       # alerte partie
    assert "ROLLBACK" in m.alerts_file().read_text(encoding="utf-8")
    assert _status(m)["last_result"] == "rolled-back"

    # anti-boucle : tant que origin/main n'avance pas, AUCUNE retentative
    n_stops = len(m.stops)
    proc, result, detail = m.check_cycle(proc)
    assert result == "rolled-back"
    assert "non retenté" in detail
    assert m.depots.sha_local() == c1
    assert len(m.stops) == n_stops                     # pas de nouvel arrêt

    # origin/main avance (c3 corrige) : l'update repart et réussit
    os.environ["TBOT_WATCH_PYTEST_CMD"] = json.dumps(PY_GREEN)
    c3 = m.depots.commit_remote("a.txt", "v3", "c3: fix")
    proc, result, detail = m.check_cycle(proc)
    assert result == "updated"
    assert m.depots.sha_local() == c3
    assert "bad_sha" not in m.load_state()             # fautif purgé


# == PW-T3 : checkout sale → aucun pull ========================================
def test_checkout_sale_aucun_pull(calme):
    m = calme
    c1 = m.depots.sha_local()
    m.depots.commit_remote("a.txt", "v2", "c2")
    (m.depots.local / "a.txt").write_text("modif locale", encoding="utf-8")

    proc, result, detail = m.check_cycle(FauxProc())
    assert result == "dirty"
    assert m.depots.sha_local() == c1                  # AUCUN pull
    assert _status(m)["last_result"] == "dirty"
    assert len(m.sends) == 1                           # alerte « sale »
    assert "sale" in m.sends[0]

    # la condition persiste : log oui, re-alerte non (dédoublonnage)
    proc, result, _ = m.check_cycle(proc)
    assert result == "dirty" and len(m.sends) == 1

    # checkout nettoyé : l'update part normalement
    _git(m.depots.local, "checkout", "--", "a.txt")
    proc, result, _ = m.check_cycle(proc)
    assert result == "updated"


# == PW-T4 : arrêt propre `.stop`, arrêt forcé au timeout ======================
_FACTORY_DOCILE = """\
import pathlib, sys, time
stop = pathlib.Path(sys.argv[1])
limite = time.time() + 30
while time.time() < limite:
    if stop.exists():
        sys.exit(0)
    time.sleep(0.05)
sys.exit(7)
"""

_FACTORY_SOURDE = "import time; time.sleep(30)"


def test_arret_propre_via_stop(env, monkeypatch):
    m = env
    monkeypatch.setattr(m, "send_telegram", lambda t: None)
    script = m.tmp / "factory_docile.py"
    script.write_text(_FACTORY_DOCILE, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script),
                             os.environ["TBF_STOP"]])
    try:
        assert m.stop_factory(proc) is True            # sortie propre
        assert proc.returncode == 0
        assert not m.stop_file().exists()              # .stop retiré (PW-5.4)
    finally:
        if proc.poll() is None:
            proc.kill()


def test_arret_force_au_timeout(env, monkeypatch):
    m = env
    alertes = []
    monkeypatch.setattr(m, "send_telegram", lambda t: alertes.append(t))
    os.environ["TBOT_WATCH_STOP_TIMEOUT"] = "1"
    proc = subprocess.Popen([sys.executable, "-c", _FACTORY_SOURDE])
    try:
        debut = time.time()
        assert m.stop_factory(proc) is False           # forcé
        assert time.time() - debut < 25                # pas d'attente 30 s
        assert proc.poll() is not None                 # arbre tué
        assert any("forcé" in a for a in alertes)
        assert not m.stop_file().exists()
    finally:
        if proc.poll() is None:
            proc.kill()


def test_arret_force_supprime_le_verrou_factory(env, monkeypatch):
    """F7 : après un arrêt FORCÉ la factory est morte mais son verrou
    .tbot-factory.lock reste frais — sans nettoyage il bloquerait la relance
    jusqu'à 180 s (et la relance compterait crash). Le watcher le retire."""
    m = env
    monkeypatch.setattr(m, "send_telegram", lambda t: None)
    os.environ["TBOT_WATCH_STOP_TIMEOUT"] = "1"
    lock = m.factory_lock_file()
    lock.write_text("pid 12345 :: frais\n", encoding="utf-8")

    proc = subprocess.Popen([sys.executable, "-c", _FACTORY_SOURDE])
    try:
        assert m.stop_factory(proc) is False           # forcé
        assert not lock.exists()                       # verrou orphelin retiré
    finally:
        if proc.poll() is None:
            proc.kill()


def test_arret_propre_conserve_le_verrou_au_watcher(env, monkeypatch):
    """Contre-cas F7 : sur un arrêt PROPRE la factory gère son verrou
    elle-même (finally clear_lock) — le watcher n'y touche pas."""
    m = env
    monkeypatch.setattr(m, "send_telegram", lambda t: None)
    lock = m.factory_lock_file()
    lock.write_text("pid 12345 :: frais\n", encoding="utf-8")
    script = m.tmp / "factory_docile.py"
    script.write_text(_FACTORY_DOCILE, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script),
                             os.environ["TBF_STOP"]])
    try:
        assert m.stop_factory(proc) is True            # sortie propre
        assert lock.exists()                           # pas touché par le watcher
    finally:
        if proc.poll() is None:
            proc.kill()


# == PW-3 : verrou single-instance =============================================
def test_verrou_watcher(env):
    m = env
    assert m.lock_is_fresh() is False
    m.write_lock()
    assert m.lock_is_fresh() is True                   # deux watchers = interdit
    vieux = time.time() - (m.lock_stale_sec() + 10)
    os.utime(m.lock_file(), (vieux, vieux))
    assert m.lock_is_fresh() is False                  # watcher mort : on passe
    m.clear_lock()
    assert not m.lock_file().exists()


# == PW-11 : vocabulaire git fermé (inspection statique) =======================
def test_vocabulaire_git_ferme():
    """Le watcher ne connaît ni commit, ni push, ni checkout de branche."""
    src = (_HERE / "tbot-prod-watcher.py").read_text(encoding="utf-8")
    for interdit in ('git("commit"', 'git("push"', 'git("checkout"',
                     '"--force"', '"push"'):
        assert interdit not in src, f"vocabulaire git interdit : {interdit}"
