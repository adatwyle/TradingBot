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

Analytics (SPEC_analytics-trades, parité Trade Buddy) : ``/analytics`` +
``/api/analytics``, ``/api/analytics/trades``, ``/api/analytics/kpi`` —
calculés à chaque requête par server/analytics.py sur le ledger ∪ les
journaux forward (adaptateur lecture seule).  Un filtre hors domaine est la
SEULE erreur rendue (400, AN-4) ; tout le reste dégrade en ``warnings[]``
(D-AN-16), jamais un 500.

Launch: ``python app/server/app.py`` → http://127.0.0.1:8742 (UI-10, the
factory's « supervision » worker).  Paths via core.paths exclusively —
TBOT_PROJECT_ROOT / TBOT_DB_DIR are the test seams.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/
# `core` and `server` live in app/ ; direct launch -> make app/ importable.
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.version import read_version                     # noqa: E402
from server import analytics as analytics_mod             # noqa: E402
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


def _stamp_analytics() -> dict:
    """Bandeau des réponses analytics (nominales, dégradées et 400) : même
    horodatage UTC suffixé ``Z`` que ``build_analytics`` (§6.1) — pas la
    convention locale de ``/api/state``."""
    return {"generated": analytics_mod.generated_utc(), "version": _version()}


# ── analytics : repli « jamais un 500 » (D-AN-16) ───────────────────────────
def _degraded(error: Exception) -> str:
    """Le warning explicite qui remplace une panne de calcul — le message
    d'origine est conservé (tronqué), jamais avalé."""
    return f"analyse indisponible : {type(error).__name__} — {str(error)[:200]}"


def empty_analytics(filters, error: Exception) -> dict:
    """Le payload §6.1 d'un sous-ensemble vide (``by_currency = {}``) quand
    le moteur casse APRÈS validation des filtres : la page reste servie, le
    problème est lisible dans AVERTISSEMENTS."""
    return {
        **_stamp_analytics(),
        "filters": {"applied": filters.applied(), "options": {}},
        "source": {"ledger_rows": 0, "journal_rows": 0, "dedup": 0,
                   "ledger_present": False, "studies": {}},
        "header": {"mode": filters.mode, "n_strategies": 0, "n_instances": 0,
                   "n_trades": 0, "base": {}, "base_kind": "zero",
                   "source_kind": "aucune"},
        "by_currency": {},
        "open_positions": [],
        "warnings": [_degraded(error)],
    }


def empty_trades_page(page: int, limit: int, error: Exception) -> dict:
    """Le repli AN-28 : page vide, pagination conservée, warning explicite."""
    return {**_stamp_analytics(), "total": 0, "page": page, "limit": limit,
            "rows": [], "warnings": [_degraded(error)]}


def empty_kpi(error: Exception) -> dict:
    """Le repli AN-31 : aucun mode non vide, warning explicite."""
    return {**_stamp_analytics(), "PAPER": {}, "LIVE": {},
            "warnings": [_degraded(error)]}


def _invalid_filter(error: ValueError):
    """AN-4 — la seule erreur rendue : ``400 {"error": "paramètre invalide :
    <nom>=<valeur>"}``."""
    return jsonify({**_stamp_analytics(), "error": str(error)}), 400


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        # UI-7 / §6.4 : les méthodes d'écriture n'existent pas — la réponse
        # est JSON comme les 400/404 de l'API, pas la page HTML Flask.
        return jsonify({**_stamp(), "error": "méthode non autorisée"}), 405

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

    @app.route("/analytics")
    def analytics_page():
        # AN-1 — le shell « analyse » ; les données viennent de /api/analytics.
        return send_from_directory(UI_DIR, "analytics.html")

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

    # ── analytics (SPEC_analytics-trades §6 — GET seulement, UI-7) ─────────
    # Les filtres sont validés D'ABORD (400 = la seule erreur, AN-4) ; le
    # moteur tourne ensuite sous un filet : une exception devient un
    # sous-ensemble vide + warning (D-AN-16), jamais un 500.
    @app.route("/api/analytics")
    def api_analytics():
        try:
            filters = analytics_mod.parse_filters(request.args)
        except ValueError as e:
            return _invalid_filter(e)
        try:
            return jsonify(analytics_mod.build_analytics(request.args))
        except Exception as e:  # noqa: BLE001 — D-AN-16, warning explicite
            return jsonify(empty_analytics(filters, e))

    @app.route("/api/analytics/trades")
    def api_analytics_trades():
        try:
            analytics_mod.parse_filters(request.args)
            page, limit = analytics_mod.parse_paging(request.args)
        except ValueError as e:
            return _invalid_filter(e)
        try:
            return jsonify(analytics_mod.build_trades_page(request.args))
        except Exception as e:  # noqa: BLE001 — D-AN-16, warning explicite
            return jsonify(empty_trades_page(page, limit, e))

    @app.route("/api/analytics/kpi")
    def api_analytics_kpi():
        try:
            return jsonify(analytics_mod.build_kpi())
        except Exception as e:  # noqa: BLE001 — D-AN-16, warning explicite
            return jsonify(empty_kpi(e))

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
