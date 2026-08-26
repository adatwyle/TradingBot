"""
SUPERVISION SERVER — read-only, dynamic UI (SPEC_ui-dynamique v1.0.0)
=====================================================================

Replaces the inherited prototype server (regex injection of STRATS/LEDGER
into a hand-written dashboard.html — deleted, UI-9).  This server SERVES
STATE, it never creates it:

  - discovery is dynamic (UI-1): ``strategies/S0NN_*`` is scanned at every
    request — a new folder with a manifest.yaml appears immediately, an
    unreadable manifest shows as « manifest invalide », never silently absent;
  - performance comes from the §3 contract: ``status.json`` per instance
    under ``db_dir()/<S0NN>/<instance>/`` (written by the strategies) plus
    the ledger for history — aggregated AT SERVE TIME;
  - the declared level (manifest ``status:``, R7) is CONFRONTED with reality
    and divergences are displayed (D-UI-4, inherited, non-negotiable);
  - STRICTLY read-only (UI-7): every route is GET, no action is wired, no
    order can ever leave this process.  The supervision that could act on
    positions will live behind the risk layer — never in a viewing server.

Front: HTML + vanilla JS, no build step, no CDN (D-UI-2); curves are
client-side SVG (D-UI-3).  Served from ``app/server/ui/``.

Launch: ``python app/server/app.py`` → http://127.0.0.1:8742 (UI-10, the
factory's « supervision » worker).  Paths via core.paths exclusively —
TBOT_PROJECT_ROOT / TBOT_DB_DIR are the test seams.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

from flask import Flask, jsonify, send_from_directory

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/
# `core` and `server` live in app/ ; direct launch -> make app/ importable.
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.version import read_version                     # noqa: E402
from server import services as services_mod               # noqa: E402
from server import state as state_mod                     # noqa: E402

UI_DIR = os.path.join(APP_DIR, "server", "ui")


def _version() -> str:
    """UI-6 — the applicative version, visibly broken when unreadable
    (never a silent fallback, never a 500 on a supervision page)."""
    try:
        return read_version()
    except (OSError, ValueError):
        return "VERSION illisible"


def _stamp() -> dict:
    """The global banner data every payload carries (UI-6)."""
    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "version": _version(),
    }


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    # ── pages (HTML shells — the data always comes from the JSON API) ──────
    @app.route("/")
    def index():
        return send_from_directory(UI_DIR, "index.html")

    @app.route("/strategy/<sid>")
    def strategy_page(sid: str):
        # The shell is served for any id: the page itself renders the API's
        # 404 as an explicit « stratégie inconnue » state.
        return send_from_directory(UI_DIR, "strategy.html")

    @app.route("/services")
    def services_page():
        return send_from_directory(UI_DIR, "services.html")

    @app.route("/ui/<path:filename>")
    def ui_asset(filename: str):
        return send_from_directory(UI_DIR, filename)

    # ── JSON API (UI-7 — all GET, strictly read-only) ──────────────────────
    @app.route("/api/state")
    def api_state():
        return jsonify({**_stamp(), **state_mod.build_state()})

    @app.route("/api/strategy/<sid>")
    def api_strategy(sid: str):
        folder = state_mod.resolve_folder(sid)
        if folder is None:
            return jsonify({**_stamp(),
                            "error": f"stratégie inconnue : {sid}"}), 404
        return jsonify({**_stamp(),
                        **state_mod.build_strategy_detail(folder)})

    @app.route("/api/services")
    def api_services():
        return jsonify({**_stamp(), **services_mod.build_services()})

    @app.route("/api/equity/<sid>/<instance>")
    def api_equity(sid: str, instance: str):
        folder = state_mod.resolve_folder(sid)
        if folder is None:
            return jsonify({**_stamp(),
                            "error": f"stratégie inconnue : {sid}"}), 404
        short = state_mod.short_id(folder)
        return jsonify(state_mod.equity_points(short, instance))

    return app


app = create_app()


def ui_port() -> int:
    """UI port — TBOT_UI_PORT env seam, default 8742 (UI-10).

    The dev PC keeps 8742 busy with the prototype server until E6: set
    TBOT_UI_PORT=8790 there (documented in tbot-panel.exemple.txt).  An
    unreadable value falls back to the default — a supervision server must
    start, not crash on a typo."""
    try:
        return int(os.environ.get("TBOT_UI_PORT") or 8742)
    except ValueError:
        return 8742


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=ui_port(), debug=False)
