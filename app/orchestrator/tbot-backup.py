#!/usr/bin/env python3
"""
tbot-backup.py — WORKER DE SAUVEGARDE GITHUB (SPEC_backup-github, mission T8)
==============================================================================

Pousse cycliquement les journaux et états LÉGERS de C:/db/tradingBot/ vers le
dépôt (dossier `db-backup/`, arborescence miroir), commit automatique sur
`dev`, message horodaté `backup: db-backup YYYY-MM-DD HH:MM [skip ci]`
(D-BK-4 — un backup ne déclenche ni tests ni publication), puis
`git push origin dev`. Idempotent, SILENCIEUX si rien n'a changé (aucun
commit vide — BK-5). Jamais les secrets, les datasets ni les caches (D4).

SÉLECTION FAIL-CLOSED (D-BK-2) — le doute n'ouvre rien
-------------------------------------------------------
ALLOWLIST de NOMS EXACTS, à toute profondeur sous db_dir() (BK-1) :
    journal.csv, status.json, state.json, config.json, events.csv
plus, à la RACINE seulement : le panneau de contrôle (robinbot-panel.txt et
tbot-panel.txt — hors repo comme surface de contrôle, mais son contenu est un
état à sauvegarder). Un fichier nouveau/inconnu n'est JAMAIS poussé par
accident.

EXCLUSIONS ABSOLUES, prioritaires sur l'allowlist (BK-2, défense en
profondeur) : tout chemin contenant un segment secrets/datasets/bars_cache/
cache/db-backup ; tout nom contenant token/key/secret ; extensions .db,
.db-wal, .db-shm, .parquet, .pkl, .log ; le fichier `.push-now` ; et le
dossier d'état du worker lui-même (TBOT_BACKUP_DIR — sinon son propre
status.json, réécrit à chaque passage, rendrait le miroir toujours « changé »
et le worker jamais silencieux). Plafond 10 Mo par fichier (D-BK-6) :
au-delà = dataset égaré, signalé dans status.json (`skipped_oversize`),
pas copié (BK-3).

MIROIR AVEC SUPPRESSION (D-BK-3) : un fichier disparu de la source est
supprimé de db-backup/ — le repo reflète l'état COURANT, l'historique git
garde le passé.

BRANCHE (D-BK-5) : actif UNIQUEMENT si le checkout courant est sur `dev`.
Sur `main` (PC prod) : sortie 0 + note de log (`skipped-branch`) — le contrat
CI interdit tout push direct sur main ; un seul poste écrivain.

DÉCLENCHEMENT (D-BK-1 / BK-9) : tick factory 3600 s + GARDE INTERNE 24 h
(état `last_success_utc` dans status.json). À la demande : fichier
`<TBOT_BACKUP_DIR>/.push-now` (consommé à la prise en compte) ou flag CLI
`--now`. Pas dû → sortie 0 immédiate, une ligne de log au plus.

COMMIT RESTREINT (BK-6) : `git add -A -- db-backup/` puis commit avec
pathspec `-- db-backup/` — JAMAIS un fichier hors db-backup/ embarqué, même
si le reste du working tree est sale. PUSH (BK-7) : rejet (remote a avancé) →
fetch + rebase origin/dev (db-backup/ n'a qu'un seul écrivain : le rebase
passe toujours proprement) puis UN SEUL retry ; échec encore → sortie 2, le
commit local reste en place (retenté au prochain déclenchement).

GARDE-FOU DE COHÉRENCE (BK-8) : `git check-ignore` sur les fichiers
éligibles — un fichier allowlisté que `.gitignore` avale serait silencieusement
absent du backup : avertissement dans status.json. Le `.gitignore` racine
porte des ré-inclusions ciblées `!db-backup/...` pour les noms de l'allowlist.

ÉTAT PUBLIÉ (BK-10, affiché par l'UI) : `<TBOT_BACKUP_DIR>/status.json`
(écriture atomique tmp+replace) : schema, generated_at_utc, last_success_utc,
last_result pushed|nothing-to-do|skipped-branch|error, n_files, n_changed,
skipped_oversize, warnings.

CODES DE SORTIE (BK-11, contrat factory) : 0 OK (y c. rien à faire, pas dû,
mauvaise branche) · 2 push impossible (réseau / rejet persistant) · 1 erreur
inattendue. JAMAIS 3/4 (aucun scellé ici).

SEAMS D'ENV (BK-12 — tout est résolu À L'APPEL, testable en tmp_path) :
    TBOT_BACKUP_DIR            défaut db_dir()/backup (état + .push-now)
    RBF_ROOT / TBOT_PROJECT_ROOT   le dépôt cible (via core.paths)
    TBOT_DB_DIR                la source (via core.paths)
Les tests montent un dépôt git jetable (remote = bare local) et un faux
db_dir() en tmp_path — jamais le vrai dépôt, jamais le vrai C:/db.

USAGE
-----
    python app/orchestrator/tbot-backup.py          # tick factory (garde 24 h)
    python app/orchestrator/tbot-backup.py --now    # backup immédiat
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows propre
except Exception:  # noqa: BLE001
    pass

HERE = pathlib.Path(__file__).resolve().parent           # app/orchestrator
# `core` vit dans app/ ; script lancé en direct → app/ importable d'abord.
sys.path.insert(0, str(HERE.parent))
from core.paths import db_dir, project_root  # noqa: E402

# == SÉLECTION (BK-1 / BK-2 / BK-3 — donnée FROIDE, fail-closed) ===============
ALLOWED_NAMES = {"journal.csv", "status.json", "state.json",
                 "config.json", "events.csv"}
# À la racine de db_dir() seulement : le panneau de contrôle. Deux noms — le
# panneau du prototype (robinbot-panel.txt, défaut core.paths) et celui de la
# tbot factory (tbot-panel.txt) — même surface, deux consoles.
ROOT_ALLOWED_NAMES = {"robinbot-panel.txt", "tbot-panel.txt"}
EXCLUDED_SEGMENTS = {"secrets", "datasets", "bars_cache", "cache", "db-backup"}
EXCLUDED_NAME_PARTS = ("token", "key", "secret")
EXCLUDED_SUFFIXES = (".db", ".db-wal", ".db-shm", ".parquet", ".pkl", ".log")
MAX_FILE_BYTES = 10 * 1024 * 1024                        # D-BK-6
GUARD_SEC = 24 * 3600                                    # garde interne BK-9
GIT_TIMEOUT_SEC = 300
BRANCH = "dev"                                           # D-BK-5


# == RÉSOLUTION (à l'appel, jamais à l'import — seams de test) =================
def backup_state_dir() -> pathlib.Path:
    env = os.environ.get("TBOT_BACKUP_DIR")
    return pathlib.Path(env) if env else db_dir() / "backup"


def status_file() -> pathlib.Path:
    return backup_state_dir() / "status.json"


def push_now_file() -> pathlib.Path:
    return backup_state_dir() / ".push-now"


def mirror_dir() -> pathlib.Path:
    return project_root() / "db-backup"


# == JOURNAL ===================================================================
def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


# == GIT (cwd = racine projet, ne lève jamais) =================================
def git(*args: str, timeout: int = GIT_TIMEOUT_SEC) -> subprocess.CompletedProcess:
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


def current_branch() -> str:
    r = git("rev-parse", "--abbrev-ref", "HEAD", timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


# == SÉLECTION DES FICHIERS (BK-1/BK-2/BK-3) ===================================
def is_excluded(rel: pathlib.PurePath) -> bool:
    """BK-2 — exclusions absolues, PRIORITAIRES sur l'allowlist. Comparaisons
    en minuscules : sur Windows, `TOKEN.txt` est le même danger que
    `token.txt` (fail-closed : l'exclusion large ne coûte qu'un renommage)."""
    name = rel.name.lower()
    if any(seg.lower() in EXCLUDED_SEGMENTS for seg in rel.parts[:-1]):
        return True
    if name == ".push-now":
        return True
    if any(part in name for part in EXCLUDED_NAME_PARTS):
        return True
    if name.endswith(EXCLUDED_SUFFIXES):
        return True
    return False


def eligible_files() -> tuple[list[pathlib.PurePath], list[str]]:
    """-> (chemins relatifs éligibles, chemins relatifs ignorés pour taille).
    Allowlist de noms EXACTS (BK-1) après les exclusions (BK-2) ; le dossier
    d'état du worker (TBOT_BACKUP_DIR) n'est jamais une source."""
    src = db_dir()
    state = backup_state_dir()
    try:
        state_resolved = state.resolve()
    except OSError:
        state_resolved = state
    files: list[pathlib.PurePath] = []
    oversize: list[str] = []
    for f in sorted(src.rglob("*")):
        try:
            if not f.is_file():
                continue
            if f.resolve().is_relative_to(state_resolved):
                continue                # l'état du worker n'est pas la charge
            rel = f.relative_to(src)
            if is_excluded(rel):
                continue
            at_root = len(rel.parts) == 1
            if rel.name not in ALLOWED_NAMES and not (
                    at_root and rel.name in ROOT_ALLOWED_NAMES):
                continue                # fail-closed : inconnu = jamais poussé
            if f.stat().st_size > MAX_FILE_BYTES:
                oversize.append(rel.as_posix())          # BK-3 : signalé,
                continue                                 # pas copié
            files.append(rel)
        except OSError:
            continue                    # fichier volatil/verrouillé : au suivant
    return files, oversize


# == MIROIR (BK-4 / D-BK-3) ====================================================
def _same_content(src: pathlib.Path, dst: pathlib.Path) -> bool:
    """Taille+mtime d'abord, octets en cas de doute (BK-4)."""
    try:
        ss, ds = src.stat(), dst.stat()
        if ss.st_size != ds.st_size:
            return False
        if int(ss.st_mtime) == int(ds.st_mtime):
            return True
        return src.read_bytes() == dst.read_bytes()
    except OSError:
        return False


def mirror_files(files: list[pathlib.PurePath],
                 warnings: list[str]) -> int:
    """Copie ce qui diffère, supprime du miroir ce qui a disparu de la source
    (D-BK-3), élague les dossiers vides. Rend le nombre de changements."""
    src_root, dst_root = db_dir(), mirror_dir()
    expected = set(files)
    changed = 0
    for rel in files:
        src, dst = src_root / rel, dst_root / rel
        if dst.exists() and _same_content(src, dst):
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)      # copy2 : mtime préservé → comparaison
            changed += 1                # taille+mtime stable au prochain tour
        except OSError as e:
            warnings.append(f"copie impossible {rel.as_posix()} : {e!r}")
    if dst_root.is_dir():
        for f in sorted(dst_root.rglob("*"), reverse=True):
            try:
                if f.is_file() and f.relative_to(dst_root) not in expected:
                    f.unlink()          # miroir avec suppression (D-BK-3)
                    changed += 1
                elif f.is_dir():
                    f.rmdir()           # ne tombe que si vide
            except OSError:
                pass
    return changed


# == GARDE-FOU .gitignore (BK-8) ===============================================
def ignored_by_gitignore(files: list[pathlib.PurePath]) -> list[str]:
    """Les chemins db-backup/<rel> qu'un pattern `.gitignore` avale : un
    fichier allowlisté ignoré serait silencieusement ABSENT du backup."""
    if not files:
        return []
    # STDIN en OCTETS, jamais en mode texte : sous Windows la traduction
    # universelle des fins de ligne transformerait chaque `\n` en `\r\n` et
    # git recevrait des chemins terminés par `\r` — aucun match, garde-fou
    # silencieusement AVEUGLE (constaté au banc de test, famille de la leçon
    # « ligne de commande Windows » du gateway).
    paths = "\n".join(f"db-backup/{rel.as_posix()}" for rel in files)
    try:
        r = subprocess.run(["git", "check-ignore", "--stdin"],
                           cwd=str(project_root()),
                           input=paths.encode("utf-8"),
                           capture_output=True, timeout=GIT_TIMEOUT_SEC,
                           check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if r.returncode not in (0, 1):      # 0 = matchs, 1 = aucun, 128 = erreur
        return []
    out = r.stdout.decode("utf-8", errors="replace")
    return [l.strip() for l in out.splitlines() if l.strip()]


# == ÉTAT PUBLIÉ (BK-10) =======================================================
def load_status() -> dict:
    try:
        data = json.loads(status_file().read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_status(last_result: str, n_files: int, n_changed: int,
                 skipped_oversize: list[str], warnings: list[str],
                 success: bool) -> None:
    """Écriture ATOMIQUE (tmp+replace). `last_success_utc` n'avance que sur
    passage réussi (pushed / nothing-to-do) — c'est l'état de la garde 24 h."""
    prev = load_status()
    payload = {
        "schema": 1,
        "generated_at_utc": _utc_iso(),
        "last_success_utc": _utc_iso() if success else prev.get("last_success_utc"),
        "last_result": last_result,
        "n_files": n_files,
        "n_changed": n_changed,
        "skipped_oversize": skipped_oversize,
        "warnings": warnings,
    }
    try:
        backup_state_dir().mkdir(parents=True, exist_ok=True)
        tmp = status_file().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, status_file())
    except OSError as e:
        log(f"ATTENTION : status.json inécrivable ({e!r}) — le backup, lui, est fait.")


# == GARDE 24 h + À LA DEMANDE (BK-9) ==========================================
def _due(force: bool) -> tuple[bool, str]:
    """-> (dû, raison). `.push-now` est CONSOMMÉ à la prise en compte."""
    if force:
        return True, "--now"
    pn = push_now_file()
    if pn.exists():
        try:
            pn.unlink()
        except OSError as e:
            log(f"ATTENTION : .push-now non supprimable ({e!r}) — rejeu possible.")
        return True, ".push-now"
    last = load_status().get("last_success_utc")
    if not last:
        return True, "aucun backup réussi connu"
    try:
        t = datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return True, "last_success_utc illisible"
    age = (datetime.now(timezone.utc) - t).total_seconds()
    if age >= GUARD_SEC:
        return True, f"dernier succès il y a {int(age // 3600)} h"
    return False, ""


# == LE PASSAGE (miroir + commit + push) =======================================
def run(force: bool = False) -> int:
    due, reason = _due(force)
    if not due:
        log("veille : dernier backup réussi < 24 h — rien à faire (BK-9).")
        return 0

    branch = current_branch()
    if branch != BRANCH:
        # D-BK-5 : jamais actif hors dev — le backup des données prod sera
        # re-décidé à E6. Sortie 0 : ce n'est PAS une erreur.
        log(f"branche courante '{branch or '?'}' ≠ {BRANCH} — backup inactif "
            f"sur ce poste (D-BK-5).")
        write_status("skipped-branch", 0, 0, [], [], success=False)
        return 0

    if not db_dir().is_dir():
        # Une source ABSENTE n'est pas une source vide : vider le miroir sur
        # un db_dir disparu committerait une destruction. On crie, on ne
        # touche à rien.
        log(f"ERREUR : db_dir() introuvable ({db_dir()}) — aucun miroir, "
            f"aucune suppression.")
        write_status("error", 0, 0, [], [f"db_dir introuvable : {db_dir()}"],
                     success=False)
        return 1

    warnings: list[str] = []
    files, oversize = eligible_files()
    for rel in oversize:
        log(f"ATTENTION : {rel} > 10 Mo — dataset égaré ? non copié (D-BK-6).")
    n_changed = mirror_files(files, warnings)

    # BK-8 — un fichier allowlisté que .gitignore avale serait silencieusement
    # absent : détecté ici (avant commit : le trou existe même sans commit).
    for ignored in ignored_by_gitignore(files):
        warnings.append(f"ignoré par .gitignore (absent du backup) : {ignored}")
        log(f"ATTENTION : {ignored} est avalé par .gitignore — ré-inclusion "
            f"`!db-backup/...` à ajouter (BK-8).")

    r = git("status", "--porcelain", "--", "db-backup/", timeout=120)
    if r.returncode != 0:
        log(f"ERREUR : git status impossible ({_first_line(r)}).")
        write_status("error", len(files), n_changed, oversize,
                     warnings + [f"git status : {_first_line(r)}"], success=False)
        return 1
    if not r.stdout.strip():
        # BK-5 — idempotence/silence : aucun commit, aucun push.
        log(f"rien à faire : miroir déjà à jour ({len(files)} fichiers suivis).")
        write_status("nothing-to-do", len(files), 0, oversize, warnings,
                     success=True)
        return 0

    r = git("add", "-A", "--", "db-backup/")
    if r.returncode != 0:
        log(f"ERREUR : git add impossible ({_first_line(r)}).")
        write_status("error", len(files), n_changed, oversize,
                     warnings + [f"git add : {_first_line(r)}"], success=False)
        return 1

    # BK-6 — pathspec restreint : jamais un fichier hors db-backup/ embarqué,
    # même si le reste du working tree est sale.
    msg = f"backup: db-backup {datetime.now().strftime('%Y-%m-%d %H:%M')} [skip ci]"
    r = git("commit", "-m", msg, "--", "db-backup/")
    if r.returncode != 0:
        log(f"ERREUR : git commit impossible ({_first_line(r)}).")
        write_status("error", len(files), n_changed, oversize,
                     warnings + [f"git commit : {_first_line(r)}"], success=False)
        return 1
    log(f"commit : {msg} ({n_changed} changement(s), {len(files)} fichiers).")

    # BK-7 — push, et sur rejet : fetch + rebase (un seul écrivain sur
    # db-backup/ → rebase toujours propre) puis UN retry.
    r = git("push", "origin", BRANCH)
    if r.returncode != 0:
        log(f"push rejeté ({_first_line(r)}) — fetch + rebase origin/{BRANCH} "
            f"puis un retry (BK-7).")
        git("fetch", "origin")
        rb = git("rebase", f"origin/{BRANCH}")
        if rb.returncode != 0:
            git("rebase", "--abort")
            log(f"ERREUR : rebase impossible ({_first_line(rb)}) — commit local "
                f"conservé, retenté au prochain déclenchement.")
            write_status("error", len(files), n_changed, oversize,
                         warnings + [f"rebase : {_first_line(rb)}"], success=False)
            return 2
        r = git("push", "origin", BRANCH)
        if r.returncode != 0:
            log(f"push encore rejeté ({_first_line(r)}) — sortie 2, commit "
                f"local conservé (BK-7).")
            write_status("error", len(files), n_changed, oversize,
                         warnings + [f"push : {_first_line(r)}"], success=False)
            return 2

    log(f"push OK sur origin/{BRANCH} (déclencheur : {reason}).")
    write_status("pushed", len(files), n_changed, oversize, warnings,
                 success=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="tbot-backup — journaux/états légers de C:/db/tradingBot/ "
                    "vers db-backup/ (commit [skip ci] + push origin dev).")
    ap.add_argument("--now", action="store_true",
                    help="backup immédiat (bypass de la garde 24 h)")
    a = ap.parse_args(argv)
    try:
        return run(force=a.now)
    except Exception as e:  # noqa: BLE001 — BK-11 : 1 = erreur inattendue
        log(f"ERREUR inattendue : {type(e).__name__} — {e}")
        try:
            write_status("error", 0, 0, [], [f"inattendue : {e!r}"], success=False)
        except Exception:  # noqa: BLE001
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
