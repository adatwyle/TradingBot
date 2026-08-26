"""
server/services.py — the common-services view (UI-5), read-only.
================================================================

Everything is a defensive read of what already exists on disk:

  - factory   : the tbot console lock (fresh mtime = alive), the control
    panel (on/off/cadence, AUTO-OFF lines flagged), and the parsed tail of
    the factory logs (last results per worker).
  - telegram  : notifier + gateway — token PRESENCE only (the value is
    never read, let alone served), state.json cursors.
  - datas     : datasets under db_dir() (name, size, date) — the secrets
    folder is never listed.
  - backup    : db_dir()/backup/status.json (SPEC_backup-github).
  - watcher   : db_dir()/watcher/status.json — null when absent, the front
    hides the section (SPEC_prod-watcher).
  - tickets   : tickets/TCK-*.md front-matter, open blocking ones first.
  - études    : the inherited sealed studies (UI-9 — until E6).

Seams mirror the factory's own (TBF_LOCK, TBF_LOG_DIR, TBF_PANEL,
TBF_LOCK_STALE) so a test mounts a throwaway factory without touching
production paths.
"""
from __future__ import annotations

import os
import pathlib
import re
import time

from core.paths import app_root, db_dir, project_root
from server.state import LEGACY_STUDIES, load_json_quiet, study_state

# Same default as tbot-factory.py: a lock older than this belongs to a dead
# console and the factory is reported down.
def lock_stale_sec() -> int:
    try:
        return int(os.environ.get("TBF_LOCK_STALE") or 180)
    except ValueError:
        return 180


def orchestrator_dir() -> pathlib.Path:
    return app_root() / "orchestrator"


def lock_file() -> pathlib.Path:
    env = os.environ.get("TBF_LOCK")
    return pathlib.Path(env) if env else orchestrator_dir() / ".tbot-factory.lock"


def log_dir() -> pathlib.Path:
    env = os.environ.get("TBF_LOG_DIR")
    return pathlib.Path(env) if env else orchestrator_dir() / "logs"


def panel_file() -> pathlib.Path:
    env = os.environ.get("TBF_PANEL")
    return pathlib.Path(env) if env else db_dir() / "tbot-panel.txt"


def tickets_dir() -> pathlib.Path:
    return project_root() / "tickets"


# ── factory ─────────────────────────────────────────────────────────────────
# `[2026-08-26 18:26:11] fini  [gex_S017] OK en 0.6s` and friends (lance /
# info / ERREUR / TIMEOUT / ATTENTION / INCIDENT) — one regex, verb kept.
_LOG_LINE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s+"
    r"(?P<verb>\S+)\s*\[(?P<worker>[^\]]+)\]\s*(?P<detail>.*)$")

# Both names exist in the wild: the tbot console (going forward) writes
# tbot-factory.log, the prototype console wrote factory.log (named by the
# spec).  Parse whichever is present.
FACTORY_LOG_NAMES = ("tbot-factory.log", "factory.log")

TAIL_LINES = 200


def _tail_lines(path: pathlib.Path, n: int = TAIL_LINES) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()[-n:]
    except OSError:
        return []


def parse_factory_log(path: pathlib.Path, console: str) -> list[dict]:
    """Worker events from the last TAIL_LINES of one factory log —
    status-table rows (no [worker] bracket after a verb) do not match and
    are skipped by construction."""
    events = []
    for raw in _tail_lines(path):
        m = _LOG_LINE.match(raw.rstrip())
        if not m:
            continue
        verb = m.group("verb")
        if verb in ("WORKER",):        # status table header safety
            continue
        events.append({
            "console": console,
            "ts": m.group("ts"),
            "event": verb,
            "worker": m.group("worker"),
            "detail": m.group("detail").strip(),
        })
    return events


def read_panel() -> dict:
    """The control panel as displayed (UI-5): every worker line with its
    on/off, forced cadence and AUTO-OFF flag (shown red by the front)."""
    path = panel_file()
    if not path.is_file():
        return {"file": str(path), "present": False, "workers": []}
    workers = []
    try:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            code, _, comment = raw.partition("#")
            code = code.strip()
            if not code or "=" not in code:
                continue
            name, val = (s.strip() for s in code.split("=", 1))
            if not name:
                continue
            val = val.lower()
            cadence = None
            if ":" in val:
                val, _, brut = val.partition(":")
                val = val.strip()
                try:
                    cadence = int(brut.strip())
                except ValueError:
                    cadence = None
            workers.append({
                "worker": name,
                "on": val in ("on", "true", "1", "yes", "oui"),
                "cadence": cadence,
                "auto_off": "AUTO-OFF" in comment,
                "comment": comment.strip(),
            })
    except OSError:
        return {"file": str(path), "present": True, "workers": [],
                "error": "panneau illisible"}
    return {"file": str(path), "present": True, "workers": workers}


def build_factory() -> dict:
    lock = lock_file()
    alive, age, holder = False, None, None
    if lock.is_file():
        try:
            age = time.time() - lock.stat().st_mtime
            alive = age < lock_stale_sec()
            holder = lock.read_text(encoding="utf-8").strip()[:120]
        except OSError:
            pass

    events: list[dict] = []
    for name in FACTORY_LOG_NAMES:
        path = log_dir() / name
        if path.is_file():
            events.extend(parse_factory_log(path, name))
    events.sort(key=lambda e: e["ts"])

    last_by_worker: dict[str, dict] = {}
    for ev in events:
        if ev["event"] in ("lance", "fini", "info", "ERREUR", "TIMEOUT",
                           "ATTENTION", "INCIDENT"):
            last_by_worker[ev["worker"]] = ev

    return {
        "alive": alive,
        "lock_age_sec": round(age, 1) if age is not None else None,
        "lock_holder": holder,
        "panel": read_panel(),
        "last_by_worker": last_by_worker,
        "recent": events[-30:],
    }


# ── telegram (token presence only — the value is NEVER read) ────────────────
def _notifier_token_file() -> pathlib.Path:
    env = os.environ.get("ROBINBOT_TELEGRAM_ENV")
    if env:
        return pathlib.Path(env)
    return (pathlib.Path(os.path.expanduser("~")) / ".claude" / "channels"
            / "telegram" / ".env")


def _gateway_dir() -> pathlib.Path:
    env = os.environ.get("ROBINBOT_GATEWAY_DIR")
    return pathlib.Path(env) if env else db_dir() / "gateway"


def _safe_state(path: pathlib.Path) -> dict | None:
    """state.json with any *token*-named key dropped — belt and braces:
    those files hold cursors, never secrets, but the UI leaks nothing."""
    st = load_json_quiet(path)
    if st is None:
        return None
    return {k: v for k, v in st.items() if "token" not in k.lower()}


def _mtime_iso(path: pathlib.Path) -> str | None:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S",
                             time.localtime(path.stat().st_mtime))
    except OSError:
        return None


def build_telegram() -> dict:
    notify_dir = pathlib.Path(os.environ.get("ROBINBOT_NOTIFY_DIR")
                              or (db_dir() / "notifier"))
    gw_dir = _gateway_dir()
    notify_state = notify_dir / "state.json"
    gw_state = gw_dir / "state.json"
    return {
        "notifier": {
            "token_present": _notifier_token_file().is_file(),
            "state": _safe_state(notify_state),
            "state_modified": _mtime_iso(notify_state),
        },
        "gateway": {
            "token_present": (gw_dir / "gateway_token.txt").is_file(),
            "state": _safe_state(gw_state),
            "state_modified": _mtime_iso(gw_state),
        },
    }


# ── datas ───────────────────────────────────────────────────────────────────
_DATAS_SKIP = {"secrets"}          # never listed, not even by name
_DATAS_FILE_CAP = 20000            # pathological-tree guard


def _dir_stats(root: pathlib.Path) -> tuple[int, int, float]:
    """(n_files, total_bytes, latest_mtime) — bounded walk."""
    n, size, latest = 0, 0, 0.0
    stack = [root]
    while stack and n < _DATAS_FILE_CAP:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(pathlib.Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        st = entry.stat()
                        n += 1
                        size += st.st_size
                        latest = max(latest, st.st_mtime)
                        if n >= _DATAS_FILE_CAP:
                            break
        except OSError:
            continue
    return n, size, latest


def build_datas() -> list[dict]:
    root = db_dir()
    if not root.is_dir():
        return []
    out = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return []
    for entry in entries:
        if entry.name in _DATAS_SKIP:
            continue
        try:
            if entry.is_dir():
                n, size, latest = _dir_stats(entry)
                out.append({"name": entry.name, "kind": "dir",
                            "n_files": n, "size_bytes": size,
                            "modified": time.strftime(
                                "%Y-%m-%dT%H:%M:%S",
                                time.localtime(latest)) if latest else None})
            else:
                st = entry.stat()
                out.append({"name": entry.name, "kind": "file",
                            "n_files": 1, "size_bytes": st.st_size,
                            "modified": time.strftime(
                                "%Y-%m-%dT%H:%M:%S",
                                time.localtime(st.st_mtime))})
        except OSError:
            continue
    return out


# ── tickets ─────────────────────────────────────────────────────────────────
def parse_ticket(path: pathlib.Path) -> dict | None:
    """Front-matter of one TCK-*.md (id, from, to, status, blocking)."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip()
    if not fields:
        return None
    slug = path.stem.partition("_")[2] or path.stem
    return {
        "id": fields.get("id", path.stem),
        "from": fields.get("from", "?"),
        "to": fields.get("to", "?"),
        "status": fields.get("status", "?"),
        "blocking": fields.get("blocking", "").lower() == "true",
        "created": fields.get("created"),
        "title": slug.replace("-", " "),
        "file": path.name,
    }


def build_tickets() -> dict:
    """Open blocking tickets first (shown red, UI-5), then open, then rest."""
    tdir = tickets_dir()
    tickets = []
    if tdir.is_dir():
        for path in sorted(tdir.glob("TCK-*.md")):
            t = parse_ticket(path)
            if t:
                tickets.append(t)

    def rank(t: dict) -> tuple:
        is_open = t["status"] == "open"
        return (0 if (is_open and t["blocking"]) else 1 if is_open else 2,
                t["id"])

    tickets.sort(key=rank)
    return {
        "n_open": sum(1 for t in tickets if t["status"] == "open"),
        "n_blocking_open": sum(1 for t in tickets
                               if t["status"] == "open" and t["blocking"]),
        "tickets": tickets,
    }


# ── inherited sealed studies (UI-9) ─────────────────────────────────────────
def build_etudes() -> list[dict]:
    out = []
    for folder, strat, label in LEGACY_STUDIES:
        e = study_state(folder)
        e.update({"dossier": folder, "strategie": strat, "libelle": label})
        out.append(e)
    return out


# ── the /api/services payload ───────────────────────────────────────────────
def build_services() -> dict:
    watcher_file = db_dir() / "watcher" / "status.json"
    backup_file = db_dir() / "backup" / "status.json"
    return {
        "factory": build_factory(),
        "telegram": build_telegram(),
        "datas": build_datas(),
        "backup": (load_json_quiet(backup_file)
                   or ({"error": "status.json illisible"}
                       if backup_file.is_file() else None)),
        # Section shown ONLY if the file exists (SPEC_prod-watcher) — null
        # means « no watcher on this machine », the front hides it.
        "watcher": (load_json_quiet(watcher_file)
                    or ({"error": "status.json illisible"}
                        if watcher_file.is_file() else None)),
        "tickets": build_tickets(),
        "etudes": build_etudes(),
    }
