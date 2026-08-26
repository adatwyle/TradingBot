#!/usr/bin/env python3
"""
tbot-prod-watcher.py — LE WATCHER DE MISE À JOUR DU PC PROD (SPEC_prod-watcher)
================================================================================

TÂCHE ENGLOBANTE (D-PW-1) : ce script est un WRAPPER qui lance la console
`tbot-factory.py` en processus ENFANT (jamais robinbot — le prototype ne se
déploie pas via ce canal, directive Adrian 2026-08-26), puis observe
cycliquement `origin/main`. Nouvelle version publiée par la CI → arrêt propre
de la factory (`.stop`, fin des ticks en vol), `git pull --ff-only`, tests
d'intégrité locaux, relance. Tests rouges → rollback au SHA précédent + alerte.

On ne se met JAMAIS à jour depuis l'intérieur du processus qu'on remplace :
un worker de la factory ne peut ni arrêter ni relancer son propre parent
proprement — d'où le wrapper.

GATE D'UPDATE `update_safe` (directive Adrian, GO 2026-08-26)
--------------------------------------------------------------
AVANT d'initier un redémarrage, le watcher consulte les status.json publiés
par les stratégies (contrat UI existant : `db_dir()/<S0NN>/<instance>/
status.json`, plus les études à `db_dir()/<étude>/status.json`) :

    update_safe: false  + update_safe_reason: "…"   → update DIFFÉRÉ
    update_safe absent (ou fichier absent/illisible) → SAFE (défaut)

Une stratégie annonce `update_safe: false` quand un update tomberait au
« vraiment mauvais moment » : position ouverte, décision d'entrée en cours,
fenêtre critique. Trivial tant que tout est RESEARCH ; obligatoire dès
PAPER/LIVE. Refus → re-check au poll suivant ; blocage prolongé
(> TBOT_WATCH_GATE_ALERT, défaut 3600 s) → alerte. Une interruption
momentanée reste acceptable par conception (état dans les fichiers, stops
côté serveur — R2) : le gate évite seulement le mauvais moment, il ne rend
pas l'update dangereux quand il force après décision humaine.

SÉQUENCE DE MISE À JOUR (PW-5)
-------------------------------
    1. diff HEAD..origin/main limité à `db-backup/` → pull SANS redémarrage
       (un commit de backup ne change pas le code — D-PW-5) ;
    2. sinon : OLD_SHA noté, gate consulté, `.stop` créé, attente de la
       sortie de la factory (fin des ticks en vol, timeout 1800 s → arbre
       tué + alerte « arrêt forcé ») ;
    3. `.stop` supprimé, `git pull --ff-only origin main` (échec ff → alerte,
       pas de retry, factory relancée sur OLD_SHA) ;
    4. `python -m pytest app -q` (D-PW-3). Vert → relance sur le nouveau
       code ; rouge → `git reset --hard OLD_SHA` + relance + alerte ROLLBACK ;
    5. anti-boucle : le SHA fautif est mémorisé (watcher-state.json) et n'est
       PAS retenté tant que `origin/main` n'a pas avancé au-delà.

VOCABULAIRE GIT FERMÉ (PW-11) : fetch, rev-parse, status, diff,
pull --ff-only, reset --hard <SHA enregistré>. Jamais : commit, push,
force-push, checkout de branche.

ALERTES (PW-9 + mission T4) : bandeau `!!` dans le log, ligne horodatée dans
`db_dir()/watcher/alerts.log` (fichier d'alerte lisible par le notifier), et
envoi Telegram direct best-effort via le token du notifier s'il existe
(D-PW-6) — jamais d'exception propagée si Telegram échoue, le token
n'apparaît jamais dans un log.

ÉTAT PUBLIÉ POUR L'UI (PW-8) : `db_dir()/watcher/status.json` réécrit à
chaque cycle (tmp+replace). `last_result` : up-to-date | updated |
rolled-back | dirty | error, plus l'extension `gate-blocked` (directive gate
postérieure à la spec v1.0.0 — le front affiche la valeur telle quelle).

SEAMS D'ENV (PW-10 — tout est résolu À L'APPEL, testable en tmp_path) :
    TBOT_WATCH_POLL          période de poll (défaut 300 s)
    TBOT_WATCH_STOP_TIMEOUT  attente sortie factory (défaut 1800 s)
    TBOT_WATCH_GATE_ALERT    seuil d'alerte de blocage gate (défaut 3600 s)
    TBOT_WATCH_DIR           défaut db_dir()/watcher
    TBOT_WATCH_LOCK[_STALE]  verrou single-instance (défaut 180 s stale)
    TBOT_WATCH_LOG_DIR       défaut <racine>/app/orchestrator/logs
    TBOT_WATCH_FACTORY_CMD   commande factory (liste JSON — tests)
    TBOT_WATCH_PYTEST_CMD    commande tests (liste JSON — tests)
    TBF_STOP / RBF_STOP      fichier .stop partagé avec la factory
    + les seams de core.paths (TBOT_PROJECT_ROOT, TBOT_DB_DIR)

USAGE
-----
    python app/orchestrator/tbot-prod-watcher.py           # la boucle prod
    python app/orchestrator/tbot-prod-watcher.py --once    # un seul cycle
    ou double-clic sur app/orchestrator/run-tbot-prod.bat  (PC prod)

PC dev : `run-tbot-factory.bat` inchangé — pas de watcher en dev (PW-13, le
dev pushe, il ne s'auto-met pas à jour). Arrêt : Ctrl-C (le watcher pose
`.stop`, attend la factory, sort) ou créer `.stop` à la main (la factory
sort, puis le watcher s'arrête aussi — un interrupteur par dépôt).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows propre
except Exception:  # noqa: BLE001
    pass

HERE = pathlib.Path(__file__).resolve().parent           # app/orchestrator
# `core` vit dans app/ ; script lancé en direct → app/ importable d'abord.
sys.path.insert(0, str(HERE.parent))
from core.paths import db_dir, project_root  # noqa: E402
from core.version import read_version        # noqa: E402

PYTHON = sys.executable or "python"

LOOP_SLEEP_SEC = 5            # respiration de la boucle (supervision factory)
UPTODATE_LOG_SEC = 3600       # heartbeat « à jour » max 1×/h (PW-2)
LOG_MAX_BYTES = 2 * 1024 * 1024
GIT_TIMEOUT_SEC = 300
TELEGRAM_TIMEOUT_SEC = 15


# == RÉSOLUTION (à l'appel, jamais à l'import — seams de test) =================
def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def poll_sec() -> int:
    return _env_int("TBOT_WATCH_POLL", 300)


def stop_timeout_sec() -> int:
    return _env_int("TBOT_WATCH_STOP_TIMEOUT", 1800)


def gate_alert_sec() -> int:
    return _env_int("TBOT_WATCH_GATE_ALERT", 3600)


def lock_stale_sec() -> int:
    return _env_int("TBOT_WATCH_LOCK_STALE", 180)


def crash_backoff_sec() -> int:
    return _env_int("TBOT_WATCH_CRASH_BACKOFF", 60)


def watch_dir() -> pathlib.Path:
    env = os.environ.get("TBOT_WATCH_DIR")
    return pathlib.Path(env) if env else db_dir() / "watcher"


def stop_file() -> pathlib.Path:
    """Le `.stop` PARTAGÉ avec la factory enfant (TBF_STOP côté tbot,
    RBF_STOP côté spec) — un interrupteur d'arrêt par dépôt."""
    env = os.environ.get("TBF_STOP") or os.environ.get("RBF_STOP")
    return (pathlib.Path(env) if env
            else project_root() / "app" / "orchestrator" / ".stop")


def lock_file() -> pathlib.Path:
    env = os.environ.get("TBOT_WATCH_LOCK")
    return (pathlib.Path(env) if env
            else project_root() / "app" / "orchestrator" / ".prod-watcher.lock")


def log_dir() -> pathlib.Path:
    env = os.environ.get("TBOT_WATCH_LOG_DIR") or os.environ.get("TBF_LOG_DIR")
    return (pathlib.Path(env) if env
            else project_root() / "app" / "orchestrator" / "logs")


def log_file() -> pathlib.Path:
    return log_dir() / "prod-watcher.log"


def alerts_file() -> pathlib.Path:
    """Fichier d'alerte LISIBLE PAR LE NOTIFIER (une ligne horodatée par
    alerte) — mission T4 ; le notifier pourra le consommer comme il consomme
    les lignes AUTO-OFF du panneau."""
    return watch_dir() / "alerts.log"


def state_file() -> pathlib.Path:
    return watch_dir() / "watcher-state.json"


def _cmd_from_env(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        cmd = json.loads(raw)
        if isinstance(cmd, list) and cmd and all(isinstance(t, str) for t in cmd):
            return cmd
    except ValueError:
        pass
    log(f"ATTENTION : {name} illisible (liste JSON attendue) — défaut utilisé.")
    return default


def factory_cmd() -> list[str]:
    """La console lancée en enfant : tbot-factory, JAMAIS robinbot
    (directive Adrian 2026-08-26 — le prototype ne passe pas par ce canal)."""
    return _cmd_from_env(
        "TBOT_WATCH_FACTORY_CMD",
        [PYTHON, str(project_root() / "app" / "orchestrator" / "tbot-factory.py")])


def pytest_cmd() -> list[str]:
    """Tests d'intégrité post-pull (D-PW-3) : la suite app, pas strategies/."""
    return _cmd_from_env("TBOT_WATCH_PYTEST_CMD",
                         [PYTHON, "-m", "pytest", "app", "-q"])


# == JOURNAL (PW-7 — rotation naïve 2 Mo, motif factory) =======================
def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rotate_if_needed() -> None:
    try:
        lf = log_file()
        if lf.exists() and lf.stat().st_size > LOG_MAX_BYTES:
            backup = lf.with_suffix(".log.1")
            backup.unlink(missing_ok=True)
            lf.rename(backup)
    except OSError:
        pass        # un log qui rate ne tue jamais la boucle


def log(msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)
    try:
        log_dir().mkdir(parents=True, exist_ok=True)
        _rotate_if_needed()
        with open(log_file(), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# == ALERTES (PW-9 + D-PW-6) ===================================================
# Dédoublonnage en mémoire : une condition PERSISTANTE (checkout sale, gate
# bloqué sur le même SHA) n'alerte qu'une fois — le log, lui, trace chaque
# cycle. La clé est levée quand la condition disparaît.
_alerted: set[str] = set()


def send_telegram(text: str) -> None:
    """Envoi DIRECT best-effort via le token du notifier (D-PW-6) : simple
    POST sendMessage, aucun couplage avec les curseurs du notifier. Token ou
    config absents → silence. Le token n'atteint JAMAIS un log."""
    try:
        # Même résolution que tbot-notify.py (TBOT_NOTIFY_DIR) — jamais le
        # dossier `notifier/` du prototype robinbot.
        ndir = pathlib.Path(os.environ.get("TBOT_NOTIFY_DIR")
                            or (db_dir() / "tbot-notify"))
        token = (ndir / "token.txt").read_text(encoding="utf-8-sig").strip()
        cfg = json.loads((ndir / "config.json").read_text(encoding="utf-8-sig"))
        chat_id = str(cfg.get("chat_id") or "").strip()
        if not token or not chat_id:
            return
        import requests  # import tardif : jamais requis hors envoi réel
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat_id, "text": text[:4000]},
                      timeout=TELEGRAM_TIMEOUT_SEC)
    except Exception:  # noqa: BLE001 — jamais d'exception propagée (PW-9)
        pass


def alert(msg: str, key: str | None = None) -> None:
    """Ligne(s) `!!` dans le log + alerts.log + Telegram best-effort.
    `key` dédoublonne une condition persistante (une alerte par épisode)."""
    if key is not None and key in _alerted:
        log(f"(alerte déjà émise) {msg.splitlines()[0]}")
        return
    bandeau = "!" * 74
    log(bandeau)
    for ligne in msg.splitlines():
        log("!! " + ligne)
    log(bandeau)
    try:
        watch_dir().mkdir(parents=True, exist_ok=True)
        with open(alerts_file(), "a", encoding="utf-8") as f:
            f.write(f"[{_ts()}] {' / '.join(msg.splitlines())}\n")
    except OSError:
        pass
    send_telegram(f"🚨 prod-watcher — {msg}")
    if key is not None:
        _alerted.add(key)


def clear_alert(key: str) -> None:
    _alerted.discard(key)


# == GIT (vocabulaire fermé PW-11, cwd = racine projet) ========================
def git(*args: str, timeout: int = GIT_TIMEOUT_SEC) -> subprocess.CompletedProcess:
    """Ne lève JAMAIS : timeout ou git introuvable rendent un code non nul
    explicite — la boucle du watcher ne meurt pas sur un incident réseau."""
    try:
        return subprocess.run(["git", *args], cwd=str(project_root()),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["git", *args], 124, "",
                                           f"git {args[0]} : timeout {timeout}s")
    except OSError as e:
        return subprocess.CompletedProcess(["git", *args], 127, "", repr(e))


def _first_line(r: subprocess.CompletedProcess) -> str:
    for src in (r.stderr, r.stdout):
        for ligne in (src or "").splitlines():
            if ligne.strip():
                return ligne.strip()[:150]
    return f"code {r.returncode}"


def rev_parse(ref: str) -> Optional[str]:
    r = git("rev-parse", ref, timeout=60)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def _abbrev() -> Optional[str]:
    """La branche courante (`git rev-parse --abbrev-ref HEAD`)."""
    r = git("rev-parse", "--abbrev-ref", "HEAD", timeout=60)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def diff_only_db_backup(old: str, new: str) -> bool:
    """True si le diff old..new ne touche QUE `db-backup/` (D-PW-5). Un diff
    VIDE (commit sans fichier) compte comme « pas de code » → pull sans
    redémarrage aussi."""
    r = git("diff", "--name-only", f"{old}..{new}", timeout=120)
    if r.returncode != 0:
        return False        # doute → séquence complète (conservateur)
    files = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    return all(f.startswith("db-backup/") for f in files)


# == ÉTAT PERSISTANT (anti-boucle de rollback, PW-5.6) =========================
def load_state() -> dict:
    try:
        data = json.loads(state_file().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    try:
        watch_dir().mkdir(parents=True, exist_ok=True)
        tmp = state_file().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, state_file())
    except OSError:
        pass    # un marqueur qui rate ne bloque pas — on risque un rejeu


# == GATE D'UPDATE update_safe (directive Adrian 2026-08-26) ===================
def gate_blockers() -> list[dict]:
    """[{source, reason}] pour chaque status.json sous db_dir() qui annonce
    `update_safe: false`. Deux profondeurs couvertes : les instances
    (<S0NN>/<instance>/status.json — contrat UI §3.1) et les études
    (<étude>/status.json). Champ absent, fichier absent ou illisible = SAFE
    (les études RESEARCH sont triviales — elles n'écrivent pas le champ)."""
    root = db_dir()
    if not root.is_dir():
        return []
    blockers: list[dict] = []
    try:
        candidates = sorted(root.glob("*/status.json")) + \
            sorted(root.glob("*/*/status.json"))
    except OSError:
        return []
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue                      # illisible = safe (contrat tolérant)
        if not isinstance(data, dict):
            continue
        safe = data.get("update_safe")
        if safe is None or safe:
            continue                      # absent ou true = safe
        try:
            source = str(path.parent.relative_to(root)).replace("\\", "/")
        except ValueError:
            source = str(path.parent)
        blockers.append({
            "source": source,
            "reason": str(data.get("update_safe_reason")
                          or "raison non fournie"),
        })
    return blockers


# Premier refus par SHA distant : pour dater le blocage et alerter au-delà du
# seuil. En mémoire process : un watcher relancé repart de zéro — acceptable,
# l'alerte re-partira après un nouveau seuil complet.
_gate_since: dict[str, float] = {}


# == VERROU SINGLE-INSTANCE (PW-3, mécanique stale de la factory) ==============
def lock_is_fresh() -> bool:
    lf = lock_file()
    if not lf.exists():
        return False
    try:
        return (time.time() - lf.stat().st_mtime) < lock_stale_sec()
    except OSError:
        return False


def write_lock() -> None:
    try:
        lock_file().parent.mkdir(parents=True, exist_ok=True)
        lock_file().write_text(f"pid {os.getpid()} :: {_ts()}\n", encoding="utf-8")
    except OSError:
        pass


def clear_lock() -> None:
    try:
        lock_file().unlink(missing_ok=True)
    except OSError:
        pass


# == FACTORY ENFANT (lancement, arrêt propre, arrêt forcé) =====================
def start_factory() -> Optional[subprocess.Popen]:
    """Lance la console tbot-factory en ENFANT, cwd = racine projet, MÊME
    console (sortie non redirigée — PW-1a)."""
    cmd = factory_cmd()
    log(f"lancement factory : {' '.join(cmd)}")
    try:
        return subprocess.Popen(cmd, cwd=str(project_root()))
    except Exception as e:  # noqa: BLE001
        log(f"ERREUR : lancement factory impossible ({e!r})")
        return None


def factory_lock_file() -> pathlib.Path:
    """Le verrou single-instance de la factory ENFANT — même résolution que
    tbot-factory.py (TBF_LOCK, sinon app/orchestrator/.tbot-factory.lock)."""
    env = os.environ.get("TBF_LOCK")
    return (pathlib.Path(env) if env
            else project_root() / "app" / "orchestrator" / ".tbot-factory.lock")


def _clear_factory_lock() -> None:
    """Après un arrêt FORCÉ (_kill_tree) la factory est MORTE mais son verrou
    reste frais (battement < TBF_LOCK_STALE) : sans ce nettoyage, la relance
    refuserait de démarrer jusqu'à 180 s et la sortie compterait comme un
    crash (backoff). Le processus détenteur n'existe plus — on retire."""
    try:
        factory_lock_file().unlink(missing_ok=True)
    except OSError:
        pass


def _kill_tree(proc: subprocess.Popen) -> None:
    """Tue TOUT l'arbre (tuer le seul parent orphelinerait les ticks)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass


def stop_factory(proc: subprocess.Popen) -> bool:
    """Arrêt PROPRE : pose `.stop`, attend la sortie (la factory laisse finir
    les ticks en vol), timeout → arbre tué + alerte « arrêt forcé » (PW-5.3).
    Le `.stop` est retiré dans tous les cas (PW-5.4). True = sortie propre."""
    sf = stop_file()
    try:
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(f"prod-watcher update {_ts()}\n", encoding="utf-8")
    except OSError as e:
        log(f"ERREUR : impossible de poser {sf} ({e!r}) — arrêt forcé direct.")
        _kill_tree(proc)
        _clear_factory_lock()               # factory morte, verrou orphelin (F7)
        return False
    clean = True
    try:
        log(f".stop posé — attente de la fin des ticks en vol "
            f"(timeout {stop_timeout_sec()}s)")
        proc.wait(timeout=stop_timeout_sec())
        log(f"factory sortie proprement (code {proc.returncode}).")
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        _clear_factory_lock()               # factory morte, verrou orphelin (F7)
        alert(f"arrêt forcé de la factory après {stop_timeout_sec()}s "
              f"(le .stop n'a pas suffi) — arbre tué, l'état sur disque "
              f"est intact.")
        clean = False
    finally:
        try:
            sf.unlink(missing_ok=True)
        except OSError:
            pass
    return clean


def run_pytest() -> bool:
    """Tests d'intégrité post-pull (PW-5.5). Échec de LANCEMENT = rouge :
    on ne met jamais en service un code qu'on n'a pas pu tester."""
    cmd = pytest_cmd()
    log(f"tests d'intégrité post-pull : {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, cwd=str(project_root()), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=_env_int("TBOT_WATCH_PYTEST_TIMEOUT", 1800))
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"tests : lancement impossible ({type(e).__name__}) — ROUGES.")
        return False
    tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-3:]
    for ligne in tail:
        log(f"  pytest | {ligne.strip()[:150]}")
    log(f"tests : {'VERTS' if r.returncode == 0 else f'ROUGES (code {r.returncode})'}")
    return r.returncode == 0


# == ÉTAT PUBLIÉ POUR L'UI (PW-8) ==============================================
def _current_version() -> Optional[str]:
    try:
        return read_version(project_root() / "VERSION")
    except (OSError, ValueError):
        return None


def write_status(current_sha: Optional[str], remote_sha: Optional[str],
                 last_result: str, detail: str, factory_alive: bool) -> None:
    payload = {
        "schema": 1,
        "generated_at_utc": _utc_iso(),
        "current_sha": current_sha,
        "current_version": _current_version(),
        "remote_sha": remote_sha,
        "last_check_utc": _utc_iso(),
        "last_update_utc": load_state().get("last_update_utc"),
        "last_result": last_result,
        "detail": detail,
        "factory_alive": factory_alive,
    }
    try:
        watch_dir().mkdir(parents=True, exist_ok=True)
        tmp = watch_dir() / "status.json.tmp"
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, watch_dir() / "status.json")
    except OSError:
        pass    # une UI aveugle un cycle vaut mieux qu'une boucle morte


# == LA SÉQUENCE DE MISE À JOUR (PW-5) =========================================
def perform_update(proc: Optional[subprocess.Popen], old_sha: str,
                   remote_sha: str) -> tuple[Optional[subprocess.Popen], str, str]:
    """Étapes 2-6 de PW-5 (le gate a déjà dit oui). Rend (proc, result, detail)."""
    log(f"mise à jour {old_sha[:9]} → {remote_sha[:9]} : arrêt propre de la factory.")
    if proc is not None and proc.poll() is None:
        stop_factory(proc)
    proc = None

    r = git("pull", "--ff-only", "origin", "main", timeout=GIT_TIMEOUT_SEC)
    if r.returncode != 0:
        alert(f"échec git pull --ff-only ({_first_line(r)}) — pas de retry "
              f"automatique, factory relancée sur {old_sha[:9]}.",
              key=f"ff:{remote_sha}")
        return start_factory(), "error", f"pull --ff-only échoué : {_first_line(r)}"

    if run_pytest():
        state = load_state()
        state.pop("bad_sha", None)
        state["last_update_utc"] = _utc_iso()
        save_state(state)
        log(f"mise à jour OK : {remote_sha[:9]} en service, factory relancée.")
        return start_factory(), "updated", f"{old_sha[:9]} → {remote_sha[:9]}"

    # Tests rouges → rollback au SHA enregistré (D-PW-4) + anti-boucle.
    git("reset", "--hard", old_sha, timeout=GIT_TIMEOUT_SEC)
    state = load_state()
    state["bad_sha"] = remote_sha
    save_state(state)
    proc = start_factory()
    alert(f"ROLLBACK : tests rouges sur {remote_sha[:9]} — retour à "
          f"{old_sha[:9]}, factory relancée. {remote_sha[:9]} ne sera pas "
          f"retenté tant que origin/main n'avance pas.",
          key=f"rollback:{remote_sha}")
    return proc, "rolled-back", (f"tests rouges sur {remote_sha[:9]} — "
                                 f"retour {old_sha[:9]}")


# == UN CYCLE DE POLL (PW-1b, PW-2, PW-4, PW-5 + gate) =========================
def check_cycle(proc: Optional[subprocess.Popen]
                ) -> tuple[Optional[subprocess.Popen], str, str]:
    """fetch + comparaison SHA + (le cas échéant) séquence de mise à jour.
    Écrit status.json (PW-8) et rend (proc, result, detail)."""
    result, detail = "error", ""
    head = remote = None
    try:
        r = git("fetch", "origin", "main", timeout=GIT_TIMEOUT_SEC)
        if r.returncode != 0:
            result, detail = "error", f"git fetch échoué : {_first_line(r)}"
            return proc, result, detail
        head = rev_parse("HEAD")
        remote = rev_parse("origin/main")
        if not head or not remote:
            result, detail = "error", "rev-parse HEAD/origin/main illisible"
            return proc, result, detail

        if head == remote:
            _gate_since.clear()
            result, detail = "up-to-date", ""
            return proc, result, detail

        # Anti-boucle de rollback (PW-5.6) : SHA fautif non retenté.
        bad = load_state().get("bad_sha")
        if bad == remote:
            result = "rolled-back"
            detail = (f"SHA fautif {remote[:9]} non retenté "
                      f"(origin/main n'a pas avancé depuis le rollback)")
            return proc, result, detail

        # PW-4 : checkout propre + branche main, sinon AUCUN pull.
        branch = _abbrev()
        porcelain = git("status", "--porcelain", timeout=120)
        dirty_why = None
        if branch != "main":
            dirty_why = f"branche courante '{branch}' ≠ main"
        elif porcelain.returncode != 0 or porcelain.stdout.strip():
            dirty_why = "working tree sale (git status --porcelain non vide)"
        if dirty_why:
            alert(f"checkout prod sale/divergent — {dirty_why}. Aucun pull, "
                  f"la factory continue sur {head[:9]}.", key="dirty")
            result, detail = "dirty", dirty_why
            return proc, result, detail
        clear_alert("dirty")

        # D-PW-5 : diff limité à db-backup/ → pull SANS redémarrage.
        if diff_only_db_backup(head, remote):
            r = git("pull", "--ff-only", "origin", "main", timeout=GIT_TIMEOUT_SEC)
            if r.returncode != 0:
                alert(f"échec git pull --ff-only (diff db-backup seul) : "
                      f"{_first_line(r)}", key=f"ff:{remote}")
                result, detail = "error", f"pull --ff-only échoué : {_first_line(r)}"
                return proc, result, detail
            log(f"pull db-backup {head[:9]} → {remote[:9]} — console non touchée.")
            result = "updated"
            detail = f"db-backup uniquement — pull sans redémarrage ({head[:9]} → {remote[:9]})"
            return proc, result, detail

        # GATE update_safe (directive Adrian) — AVANT d'initier le redémarrage.
        blockers = gate_blockers()
        if blockers:
            since = _gate_since.setdefault(remote, time.time())
            reasons = "; ".join(f"{b['source']}: {b['reason']}" for b in blockers)
            blocked_for = time.time() - since
            if blocked_for >= gate_alert_sec():
                alert(f"update {remote[:9]} bloqué par le gate update_safe "
                      f"depuis {int(blocked_for // 60)} min — {reasons}",
                      key=f"gate:{remote}")
            log(f"gate update_safe : update {remote[:9]} différé — {reasons}")
            result, detail = "gate-blocked", reasons
            return proc, result, detail
        _gate_since.pop(remote, None)
        clear_alert(f"gate:{remote}")

        proc, result, detail = perform_update(proc, head, remote)
        head = rev_parse("HEAD")            # reflète pull ou rollback
        return proc, result, detail
    finally:
        write_status(head, remote, result, detail,
                     factory_alive=proc is not None and proc.poll() is None)


# == LA BOUCLE (PW-1, PW-6) ====================================================
def stop_requested() -> bool:
    return stop_file().exists()


def print_header() -> None:
    log("=" * 78)
    log("prod-watcher — mise à jour automatique du PC prod (SPEC_prod-watcher)")
    log(f"racine    : {project_root()}")
    log(f"factory   : {' '.join(factory_cmd())}")
    log(f"poll      : {poll_sec()}s · stop timeout {stop_timeout_sec()}s · "
        f"gate alerte {gate_alert_sec()}s")
    log(f"état UI   : {watch_dir() / 'status.json'}")
    log(f"arrêt     : Ctrl-C, ou créer {stop_file()}")
    log("=" * 78)


def run(once: bool = False) -> int:
    if lock_is_fresh():
        holder = ""
        try:
            holder = lock_file().read_text(encoding="utf-8").strip()
        except OSError:
            pass
        log(f"REFUS DE DÉMARRER : un autre prod-watcher semble vivant "
            f"({lock_file().name}, {holder}). Deux watchers = deux factories "
            f"= interdit (PW-3).")
        return 1
    write_lock()
    print_header()

    proc: Optional[subprocess.Popen] = None
    last_poll = 0.0
    last_uptodate_log = 0.0
    crash_times: list[float] = []
    backoff_until = 0.0
    code = 0

    try:
        while True:
            now = time.time()
            write_lock()                    # battement : verrou frais

            # `.stop` manuel : la factory sort, puis le watcher aussi — la
            # console prod entière s'arrête (un interrupteur par dépôt).
            if stop_requested() and (proc is None or proc.poll() is not None):
                log(f"{stop_file().name} présent et factory sortie — "
                    f"arrêt du watcher (interrupteur manuel).")
                break

            # (a) PW-1a / PW-6 : la factory doit tourner ; crash → backoff.
            if proc is not None and proc.poll() is not None:
                rc = proc.returncode
                proc = None
                if not stop_requested():
                    crash_times = [t for t in crash_times if now - t < 3600]
                    crash_times.append(now)
                    if len(crash_times) >= 3:
                        alert(f"factory : 3 crashs en moins d'1 h (dernier "
                              f"code {rc}) — backoff 1 h.", key="crash3")
                        backoff_until = now + 3600
                        crash_times.clear()
                    else:
                        log(f"ATTENTION : factory sortie sans .stop (code {rc}) "
                            f"— relance dans {crash_backoff_sec()}s.")
                        backoff_until = now + crash_backoff_sec()
            if (proc is None and not once and now >= backoff_until
                    and not stop_requested()):
                proc = start_factory()

            # (b) PW-1b : poll git à la période TBOT_WATCH_POLL.
            if now - last_poll >= poll_sec():
                last_poll = now
                proc, result, detail = check_cycle(proc)
                if result == "up-to-date":
                    if now - last_uptodate_log >= UPTODATE_LOG_SEC:
                        head = rev_parse("HEAD") or "?"
                        log(f"à jour sur {head[:9]} (heartbeat).")
                        last_uptodate_log = now
                else:
                    log(f"cycle : {result}{' — ' + detail if detail else ''}")

            if once:
                break
            time.sleep(LOOP_SLEEP_SEC)

    except KeyboardInterrupt:
        log("Ctrl-C — arrêt propre : .stop pour la factory, on attend la fin "
            "des ticks en vol.")
        if proc is not None and proc.poll() is None:
            stop_factory(proc)
        code = 130
    finally:
        clear_lock()
        log("prod-watcher arrêté.")
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="prod-watcher — mise à jour automatique du PC prod "
                    "(wrapper englobant de la tbot factory).")
    ap.add_argument("--once", action="store_true",
                    help="un seul cycle de check (sonde) — ne lance pas la "
                         "factory si elle ne tourne pas déjà")
    a = ap.parse_args(argv)
    return run(once=a.once)


if __name__ == "__main__":
    raise SystemExit(main())
