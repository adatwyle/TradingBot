"""
Tests du worker backup GitHub (SPEC_backup-github, mission T8).

Ce banc couvre ce qui DÉCIDE : l'allowlist fail-closed + exclusions absolues
(BK-T1 — un token/secret n'atteint JAMAIS le miroir, même présent dans db),
le plafond 10 Mo signalé-pas-copié (BK-3), l'idempotence (BK-T2 — deuxième
passage sans changement = AUCUN commit), le miroir avec suppression (BK-T3),
le commit restreint `-- db-backup/` sur working tree sale (BK-T4), la garde
24 h + `.push-now` + `--now` + branche ≠ dev → no-op (BK-T5), le push rejeté
→ fetch + rebase + retry (BK-T6), le garde-fou `.gitignore` (BK-8 : les
ré-inclusions `!db-backup/...` du .gitignore RÉEL laissent passer l'allowlist,
un pattern hostile déclenche l'avertissement), et status.json (BK-10).

TOUT git vit dans un dépôt JETABLE en tmp_path : remote = BARE LOCAL (aucun
push réseau, jamais), local = clone sur branche dev, branché par
TBOT_PROJECT_ROOT ; la source est un faux db_dir() en tmp (TBOT_DB_DIR).
AUCUNE commande ne touche jamais le vrai dépôt ni le vrai C:/db — un
garde-fou le vérifie à chaque chargement du module. Le .gitignore du dépôt
jetable est la COPIE du .gitignore racine réel : les ré-inclusions T8 sont
testées contre les vrais patterns.

    pytest app/orchestrator/test_tbot_backup.py -q
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
_REAL_REPO = _HERE.parents[1]                     # C:/projects/tradingBot
_REAL_GITIGNORE = (_REAL_REPO / ".gitignore").read_text(encoding="utf-8")

_ENV_KEYS = ("TBOT_PROJECT_ROOT", "RBF_ROOT", "TBF_ROOT",
             "TBOT_DB_DIR", "TBOT_BACKUP_DIR")


def _git(cwd: pathlib.Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-c", "user.email=test@test", "-c", "user.name=test",
         "-c", "commit.gpgsign=false", *args],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"git {args} : {r.stderr}"
    return r.stdout.strip()


class Depot:
    """Un remote BARE local (aucun réseau) + un clone `local` sur dev — le
    checkout que le worker committe et pushe."""

    def __init__(self, tmp: pathlib.Path):
        self.remote = tmp / "remote.git"
        self.local = tmp / "local"
        _git(tmp, "init", "--bare", str(self.remote))
        _git(tmp, "clone", str(self.remote), str(self.local))
        _git(self.local, "checkout", "-B", "dev")
        # Identité locale : le WORKER committe sans -c — hermétique au global.
        _git(self.local, "config", "user.email", "test@test")
        _git(self.local, "config", "user.name", "test")
        _git(self.local, "config", "commit.gpgsign", "false")
        (self.local / "README.md").write_text("readme v1\n", encoding="utf-8")
        # Le .gitignore RÉEL du dépôt : les ré-inclusions !db-backup/ sont
        # testées contre les vrais patterns racine (*.log, logs/, *token*…).
        (self.local / ".gitignore").write_text(_REAL_GITIGNORE, encoding="utf-8")
        _git(self.local, "add", "-A")
        _git(self.local, "commit", "-m", "c1: initial")
        _git(self.local, "push", "-u", "origin", "dev")

    def sha_local(self) -> str:
        return _git(self.local, "rev-parse", "HEAD")

    def sha_remote_dev(self) -> str:
        return _git(self.remote, "rev-parse", "dev")

    def n_commits(self) -> int:
        return int(_git(self.local, "rev-list", "--count", "HEAD"))

    def head_files(self) -> list[str]:
        out = _git(self.local, "show", "--name-only", "--pretty=format:", "HEAD")
        return [l.strip() for l in out.splitlines() if l.strip()]

    def head_message(self) -> str:
        return _git(self.local, "log", "-1", "--pretty=%s")

    def advance_remote(self, tmp: pathlib.Path) -> str:
        """Un AUTRE poste pushe sur origin/dev (pour le rejet de push BK-7)."""
        other = tmp / "other"
        if not other.exists():
            _git(tmp, "clone", str(self.remote), str(other))
            _git(other, "checkout", "dev")
        (other / "README.md").write_text(f"readme {datetime.now()}\n",
                                         encoding="utf-8")
        _git(other, "add", "-A")
        _git(other, "commit", "-m", "c-other: code change elsewhere")
        _git(other, "push", "origin", "dev")
        return _git(other, "rev-parse", "HEAD")


@pytest.fixture
def env(tmp_path):
    """Environnement jetable complet + module backup chargé depuis le fichier
    (nom à tirets → importlib)."""
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    depot = Depot(tmp_path)
    db = tmp_path / "db"
    db.mkdir()
    os.environ["TBOT_PROJECT_ROOT"] = str(depot.local)
    os.environ["TBOT_DB_DIR"] = str(db)
    os.environ["TBOT_BACKUP_DIR"] = str(db / "backup")

    spec = importlib.util.spec_from_file_location(
        "tbot_backup_test", _HERE / "tbot-backup.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # GARDE-FOU : jamais une commande git sur le dépôt de travail réel,
    # jamais une lecture du vrai C:/db.
    assert mod.project_root() == depot.local
    assert mod.project_root() != _REAL_REPO
    assert mod.db_dir() == db

    mod.depot = depot
    mod.db = db
    mod.tmp = tmp_path
    yield mod
    for k in _ENV_KEYS:
        os.environ.pop(k, None)


def _status(env) -> dict:
    return json.loads(
        (pathlib.Path(os.environ["TBOT_BACKUP_DIR"]) / "status.json")
        .read_text(encoding="utf-8"))


def _age_last_success(env, hours: float) -> None:
    """Vieillit last_success_utc pour piloter la garde 24 h (BK-9)."""
    sf = pathlib.Path(os.environ["TBOT_BACKUP_DIR"]) / "status.json"
    doc = json.loads(sf.read_text(encoding="utf-8"))
    t = datetime.now(timezone.utc) - timedelta(hours=hours)
    doc["last_success_utc"] = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    sf.write_text(json.dumps(doc), encoding="utf-8")


def _seed_minimal(db: pathlib.Path) -> None:
    (db / "S017").mkdir(parents=True, exist_ok=True)
    (db / "S017" / "journal.csv").write_text("t;evt\n1;open\n", encoding="utf-8")


# == BK-T1 : allowlist fail-closed + exclusions absolues =======================
def test_allowlist_et_exclusions(env):
    m, db = env, env.db
    # ---- éligibles (allowlist noms exacts, toute profondeur + panneau racine)
    eligibles = {
        "S017/journal.csv": "t;evt\n",
        "S017/S017.SPY/status.json": "{}",
        "notifier/config.json": '{"chat_id": "123"}',   # chat_id ≠ credential
        "events.csv": "a\n",
        "deep/nested/dir/state.json": "{}",
        "robinbot-panel.txt": "gex = on\n",             # panneau : racine
        "tbot-panel.txt": "backup = on\n",              # panneau tbot : racine
    }
    # ---- jamais copiés (BK-2 prioritaire sur BK-1, ou hors allowlist)
    interdits = {
        "secrets/config.json": "{}",                    # segment secrets
        "secrets/token.txt": "SECRET",                  # secrets + nom token
        "notifier/token.txt": "123:ABC",                # nom token
        "gateway/api_key.txt": "k",                     # nom key
        "S017/my_secret_notes.json": "x",               # nom secret
        "datasets/journal.csv": "big",                  # segment datasets
        "bars_cache/status.json": "{}",                 # segment bars_cache
        "x/cache/state.json": "{}",                     # segment cache
        "ledger/ledger.db": "bin",                      # extension .db
        "ledger/ledger.db-wal": "bin",                  # extension .db-wal
        "data/frame.parquet": "bin",                    # extension .parquet
        "data/model.pkl": "bin",                        # extension .pkl
        "notifier/notify.log": "l1",                    # extension .log
        "notes.txt": "libre",                           # inconnu = fail-closed
        "S017/robinbot-panel.txt": "x",                 # panneau HORS racine
        "backup/.push-now": "",                         # le déclencheur
    }
    for rel, contenu in {**eligibles, **interdits}.items():
        f = db / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contenu, encoding="utf-8")

    assert m.main(["--now"]) == 0
    mirror = m.depot.local / "db-backup"

    for rel in eligibles:
        assert (mirror / rel).is_file(), f"éligible absent du miroir : {rel}"
    for rel in interdits:
        assert not (mirror / rel).exists(), f"interdit copié : {rel}"

    # Défense en profondeur : AUCUNE trace token/secret/db dans tout le miroir.
    tous = [p.name.lower() for p in mirror.rglob("*") if p.is_file()]
    for motif in ("token", "secret"):
        assert not any(motif in n for n in tous), f"motif {motif} dans le miroir"
    assert not any(n.endswith((".db", ".db-wal", ".log", ".parquet")) for n in tous)

    # Le commit ne porte QUE db-backup/ et exactement les éligibles.
    committed = m.depot.head_files()
    assert all(f.startswith("db-backup/") for f in committed)
    assert set(committed) == {f"db-backup/{r}" for r in eligibles}
    # Message horodaté [skip ci] (D-BK-4) + pushé sur origin/dev.
    assert re.fullmatch(r"backup: db-backup \d{4}-\d{2}-\d{2} \d{2}:\d{2} "
                        r"\[skip ci\]", m.depot.head_message())
    assert m.depot.sha_remote_dev() == m.depot.sha_local()

    st = _status(m)
    assert st["schema"] == 1 and st["last_result"] == "pushed"
    assert st["n_files"] == len(eligibles) and st["n_changed"] == len(eligibles)
    assert st["last_success_utc"] and st["skipped_oversize"] == []


# == BK-3 : plafond 10 Mo — signalé, pas copié =================================
def test_plafond_10mo(env):
    m, db = env, env.db
    _seed_minimal(db)
    gros = db / "S017" / "status.json"
    gros.write_bytes(b"x" * (10 * 1024 * 1024 + 1))

    assert m.main(["--now"]) == 0
    mirror = m.depot.local / "db-backup"
    assert (mirror / "S017" / "journal.csv").is_file()
    assert not (mirror / "S017" / "status.json").exists()
    st = _status(m)
    assert st["skipped_oversize"] == ["S017/status.json"]
    assert st["last_result"] == "pushed"


# == BK-T2 : idempotence — deuxième passage = AUCUN commit =====================
def test_idempotence_aucun_commit_vide(env):
    m, db = env, env.db
    _seed_minimal(db)
    assert m.main(["--now"]) == 0
    n = m.depot.n_commits()

    assert m.main(["--now"]) == 0                      # rien n'a changé
    assert m.depot.n_commits() == n                    # AUCUN commit vide
    st = _status(m)
    assert st["last_result"] == "nothing-to-do" and st["n_changed"] == 0
    assert st["last_success_utc"]                      # un passage réussi


# == BK-T3 : miroir — modification → recopie ; suppression → suppression =======
def test_miroir_modification_et_suppression(env):
    m, db = env, env.db
    _seed_minimal(db)
    (db / "S017" / "status.json").write_text('{"v":1}', encoding="utf-8")
    assert m.main(["--now"]) == 0
    mirror = m.depot.local / "db-backup"

    # modification → recopie + nouveau commit
    n = m.depot.n_commits()
    (db / "S017" / "journal.csv").write_text("t;evt\n1;open\n2;close\n",
                                             encoding="utf-8")
    assert m.main(["--now"]) == 0
    assert m.depot.n_commits() == n + 1
    assert (mirror / "S017" / "journal.csv").read_text(encoding="utf-8") \
        == "t;evt\n1;open\n2;close\n"
    assert m.depot.head_files() == ["db-backup/S017/journal.csv"]

    # suppression source → suppression miroir (D-BK-3), commit de suppression
    (db / "S017" / "status.json").unlink()
    assert m.main(["--now"]) == 0
    assert m.depot.n_commits() == n + 2
    assert not (mirror / "S017" / "status.json").exists()
    assert _git(m.depot.local, "status", "--porcelain", "--", "db-backup/") == ""


# == BK-T4 : commit restreint — working tree sale hors db-backup/ ==============
def test_commit_restreint_working_tree_sale(env):
    m, db = env, env.db
    _seed_minimal(db)
    # Salir le dépôt HORS db-backup/ : modif tracked + fichier neuf non suivi.
    (m.depot.local / "README.md").write_text("readme MODIFIÉ\n", encoding="utf-8")
    (m.depot.local / "stray.py").write_text("# stray\n", encoding="utf-8")

    assert m.main(["--now"]) == 0
    committed = m.depot.head_files()
    assert committed == ["db-backup/S017/journal.csv"]  # RIEN d'autre embarqué
    # La saleté est toujours là, non commitée.
    porcelain = _git(m.depot.local, "status", "--porcelain")
    assert " README.md" in porcelain and "?? stray.py" in porcelain


# == BK-T5 : garde 24 h, .push-now, --now, branche ≠ dev =======================
def test_garde_24h_et_declencheurs(env):
    m, db = env, env.db
    _seed_minimal(db)
    assert m.main(["--now"]) == 0                      # succès initial
    n = m.depot.n_commits()

    # < 24 h + du neuf dans db → tick normal = veille, AUCUN commit
    (db / "S017" / "state.json").write_text("{}", encoding="utf-8")
    assert m.main([]) == 0
    assert m.depot.n_commits() == n

    # .push-now → passe immédiatement, et le fichier est CONSOMMÉ
    pn = pathlib.Path(os.environ["TBOT_BACKUP_DIR"]) / ".push-now"
    pn.parent.mkdir(parents=True, exist_ok=True)
    pn.write_text("", encoding="utf-8")
    assert m.main([]) == 0
    assert m.depot.n_commits() == n + 1
    assert not pn.exists()                             # supprimé (BK-9)

    # dernier succès vieilli > 24 h → tick normal repart seul
    (db / "S017" / "events.csv").write_text("e\n", encoding="utf-8")
    _age_last_success(m, hours=25)
    assert m.main([]) == 0
    assert m.depot.n_commits() == n + 2


def test_branche_main_noop(env):
    m, db = env, env.db
    _seed_minimal(db)
    _git(m.depot.local, "checkout", "-B", "main")

    assert m.main(["--now"]) == 0                      # sortie 0, pas une erreur
    assert not (m.depot.local / "db-backup").exists()  # AUCUN miroir écrit
    assert m.depot.n_commits() == 1                    # aucun commit
    assert _status(m)["last_result"] == "skipped-branch"

    # retour sur dev : le backup repart normalement
    _git(m.depot.local, "checkout", "dev")
    assert m.main(["--now"]) == 0
    assert _status(m)["last_result"] == "pushed"


# == BK-T6 : push rejeté (remote a avancé) → fetch + rebase + retry ============
def test_push_rejete_rebase_retry(env):
    m, db = env, env.db
    _seed_minimal(db)
    autre = m.depot.advance_remote(m.tmp)              # origin/dev avance

    assert m.main(["--now"]) == 0                      # rebase + retry OK
    st = _status(m)
    assert st["last_result"] == "pushed"
    # Le remote porte LES DEUX : le commit tiers ET le commit backup rebasé.
    assert m.depot.sha_remote_dev() == m.depot.sha_local()
    tous = _git(m.depot.local, "log", "--pretty=%s")
    assert "c-other: code change elsewhere" in tous
    assert "[skip ci]" in m.depot.head_message()
    assert (m.depot.local / "db-backup" / "S017" / "journal.csv").is_file()
    assert autre in _git(m.depot.local, "rev-list", "HEAD")


def test_push_impossible_sortie_2_commit_conserve(env):
    m, db = env, env.db
    _seed_minimal(db)
    # Remote injoignable : l'URL pointe vers un chemin inexistant.
    _git(m.depot.local, "remote", "set-url", "origin",
         str(m.tmp / "absent.git"))

    assert m.main(["--now"]) == 2                      # BK-11 : push impossible
    assert m.depot.n_commits() == 2                    # commit LOCAL conservé
    assert m.depot.head_files() == ["db-backup/S017/journal.csv"]
    st = _status(m)
    assert st["last_result"] == "error"
    assert st["last_success_utc"] is None              # pas un succès
    assert any("push" in w or "rebase" in w for w in st["warnings"])


# == BK-8 : garde-fou .gitignore ===============================================
def test_gitignore_reel_reinclusions_laissent_passer(env):
    """Le .gitignore racine RÉEL (copié dans le dépôt jetable) ignore logs/ —
    les ré-inclusions !db-backup/ doivent laisser passer un fichier éligible
    sous un segment logs/, sans avertissement BK-8."""
    m, db = env, env.db
    f = db / "gateway" / "logs" / "state.json"
    f.parent.mkdir(parents=True)
    f.write_text("{}", encoding="utf-8")

    assert m.main(["--now"]) == 0
    assert "db-backup/gateway/logs/state.json" in m.depot.head_files()
    assert _status(m)["warnings"] == []                # aucun trou silencieux


def test_gitignore_hostile_avertissement(env):
    """Un pattern qui avale un fichier allowlisté → avertissement status.json
    (BK-8) : le fichier serait silencieusement absent du backup."""
    m, db = env, env.db
    _seed_minimal(db)
    (db / "events.csv").write_text("e\n", encoding="utf-8")
    gi = m.depot.local / ".gitignore"
    gi.write_text(gi.read_text(encoding="utf-8") + "\ndb-backup/**/events.csv\n",
                  encoding="utf-8")

    assert m.main(["--now"]) == 0
    committed = m.depot.head_files()
    assert "db-backup/S017/journal.csv" in committed
    assert "db-backup/events.csv" not in committed     # avalé par .gitignore
    st = _status(m)
    assert any("events.csv" in w and ".gitignore" in w for w in st["warnings"])


# == F8 : source vidée ≠ ordre de purge ========================================
def test_source_videe_purge_refusee(env):
    """db_dir existe mais ne contient plus AUCUN fichier éligible alors que le
    miroir en porte : symptôme (source vidée par accident, seam cassé) — la
    purge D-BK-3 est REFUSÉE, aucune suppression, alerte explicite."""
    m, db = env, env.db
    _seed_minimal(db)
    assert m.main(["--now"]) == 0                      # miroir peuplé
    n = m.depot.n_commits()

    (db / "S017" / "journal.csv").unlink()             # la source se vide
    assert m.main(["--now"]) == 1                      # refus, pas un miroir vide
    assert (m.depot.local / "db-backup" / "S017" / "journal.csv").is_file()
    assert m.depot.n_commits() == n                    # aucune destruction commitée
    st = _status(m)
    assert st["last_result"] == "error"
    assert any("purge refusée" in w for w in st["warnings"])

    # La source revit → le passage suivant repart normalement.
    _seed_minimal(db)
    (db / "S017" / "journal.csv").write_text("t;evt\n1;open\n2;close\n",
                                             encoding="utf-8")
    assert m.main(["--now"]) == 0
    assert _status(m)["last_result"] == "pushed"


def test_source_et_miroir_vides_comportement_normal(env):
    """Contre-cas F8 : sélection vide + miroir vide (première vie du poste) =
    rien à faire, pas une erreur."""
    m = env
    assert m.main(["--now"]) == 0
    assert _status(m)["last_result"] == "nothing-to-do"


# == Robustesse : db_dir absent ≠ source vide ==================================
def test_db_dir_absent_ne_vide_jamais_le_miroir(env):
    m, db = env, env.db
    _seed_minimal(db)
    assert m.main(["--now"]) == 0
    n = m.depot.n_commits()

    os.environ["TBOT_DB_DIR"] = str(m.tmp / "disparu")
    os.environ["TBOT_BACKUP_DIR"] = str(m.tmp / "disparu" / "backup")
    assert m.main(["--now"]) == 1                      # erreur, PAS un miroir vide
    assert (m.depot.local / "db-backup" / "S017" / "journal.csv").is_file()
    assert m.depot.n_commits() == n                    # aucune destruction commitée


# == Enregistrement usine : catalogue + panneau gabarit ========================
def test_catalogue_et_panneau_portent_backup():
    """Le worker est au catalogue tbot-factory (3600 s, tick, py pur) et le
    gabarit du panneau livre `backup = on` (py pur 0 token, inerte hors dev)."""
    factory = (_HERE / "tbot-factory.py").read_text(encoding="utf-8")
    assert "py:app/orchestrator/tbot-backup.py" in factory
    assert re.search(r'\(\s*"backup",\s*ROOT,\s*'
                     r'"py:app/orchestrator/tbot-backup\.py",\s*3600,\s*"tick"\)',
                     factory)
    panel = (_HERE / "tbot-panel.exemple.txt").read_text(encoding="utf-8")
    assert re.search(r"^backup\s*=\s*on\b", panel, re.MULTILINE)
