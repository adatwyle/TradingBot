"""
core/paths.py — SINGLE SOURCE OF TRUTH for layout and state-dir resolution.
===========================================================================

Repo layout (this project): the application code lives in `app/` while
`strategies/` and `studies/` live at the PROJECT root, next to `app/`:

    <project_root>/
    ├── app/            <- code (core/, orchestrator/, server/, tools/, tests/)
    ├── strategies/     <- one folder per strategy (manifest.yaml, ...)
    └── studies/        <- sealed transverse studies

The G3 prototype had everything at the repo root; every module resolved the
root as `parent of my own folder`. That heuristic breaks once the code moves
into `app/`, so the resolution lives HERE, once, and everybody imports it.

Live state (journals, status, caches, secrets, control panel) lives OUTSIDE
the repo in `C:\\db\\tradingBot\\` (RULE_db-separation). The prototype used
`C:\\db\\tbot\\` — that directory belongs to the system still IN PRODUCTION
and must never be touched by this codebase.

Everything is resolved at CALL time and overridable by environment variables:
that is the testability seam (tests mount a throwaway layout in tmp_path
without a single `if TEST` branch in production code).

    project_root()  RBF_ROOT, then TBOT_PROJECT_ROOT  or parent of app/
    app_root()      (fixed)                           the app/ directory itself
    db_dir()        TBOT_DB_DIR                       or C:\\db\\tradingBot
    panel_file()    RBF_PANEL                         or db_dir()/robinbot-panel.txt

RBF_ROOT is the factory's historical sandbox/test seam. It MUST steer EVERY
consumer — factory, workers, server, tools — to the same root: a sandboxed
launch must never make the supervision server read the REAL repo's manifests.

The control panel default is shared by the factory (writes AUTO-OFF), the
notifier and the pilot (both read it): the three MUST resolve the same file.
The prototype diverged here (factory wrote to <db>, notify/pilot read next to
the script) — documented defect, fixed by this module.
"""
from __future__ import annotations

import os
import pathlib

# app/core/paths.py -> parents[0]=core, parents[1]=app
APP_ROOT = pathlib.Path(__file__).resolve().parents[1]

DEFAULT_DB_DIR = r"C:\db\tradingBot"


def app_root() -> pathlib.Path:
    """The app/ directory (core/, orchestrator/, server/ live under it)."""
    return APP_ROOT


def project_root() -> pathlib.Path:
    """The repo root — parent of app/, where strategies/ and studies/ live.

    RBF_ROOT (the factory's historical sandbox/test seam) takes precedence,
    then TBOT_PROJECT_ROOT: ONE canonical resolution for every consumer, so a
    sandboxed launch steers the server and the tools too, not just the
    orchestrator scripts."""
    env = os.environ.get("RBF_ROOT") or os.environ.get("TBOT_PROJECT_ROOT")
    return pathlib.Path(env) if env else APP_ROOT.parent


def db_dir() -> pathlib.Path:
    """Live-state directory, OUTSIDE the repo (RULE_db-separation)."""
    env = os.environ.get("TBOT_DB_DIR")
    return pathlib.Path(env) if env else pathlib.Path(DEFAULT_DB_DIR)


def panel_file() -> pathlib.Path:
    """The control panel — ONE file per machine, shared factory/notify/pilot."""
    env = os.environ.get("RBF_PANEL")
    return pathlib.Path(env) if env else db_dir() / "robinbot-panel.txt"
