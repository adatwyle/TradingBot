"""
Fixtures partagées des tests du serveur de supervision (SPEC_ui-dynamique).

Le principe : TOUT l'état vit dans un layout jetable monté dans tmp_path via
les seams officiels (TBOT_PROJECT_ROOT, TBOT_DB_DIR, TBOT_LEDGER_DB, TBF_*,
TBOT_GATEWAY_DIR/TBOT_NOTIFY_DIR) — jamais C:\\db, jamais le dépôt réel,
jamais la factory vivante.
Chaque seam est posé explicitement : un test qui oublierait un seam lirait la
machine réelle, et ce genre de fuite a déjà pollué un run complet.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture()
def ui_env(tmp_path, monkeypatch):
    """Layout jetable complet + helpers de fabrication de fixtures."""
    root = tmp_path / "repo"
    (root / "strategies").mkdir(parents=True)
    db = tmp_path / "db"
    db.mkdir()

    # RBF_ROOT prime sur TBOT_PROJECT_ROOT dans core.paths — purge d'abord.
    for var in ("RBF_ROOT", "TBF_LOCK_STALE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("TBOT_PROJECT_ROOT", str(root))
    monkeypatch.setenv("TBOT_DB_DIR", str(db))
    monkeypatch.setenv("TBOT_LEDGER_DB", str(db / "ledger.db"))
    # Seams factory : la console RÉELLE (verrou, logs, panneau) ne doit
    # jamais transparaître dans un test.
    monkeypatch.setenv("TBF_LOCK", str(tmp_path / "factory.lock"))
    monkeypatch.setenv("TBF_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("TBF_PANEL", str(tmp_path / "panel.txt"))
    # Seams Telegram tbot (TBOT_*, jamais ROBINBOT_*) : les vrais dossiers
    # d'état ne doivent pas rendre token_present vrai sur le poste de dev.
    monkeypatch.setenv("TBOT_GATEWAY_DIR", str(db / "tbot-gateway"))
    monkeypatch.setenv("TBOT_NOTIFY_DIR", str(db / "tbot-notify"))

    def make_strategy(folder="S013_macd_fx", *, status="PAPER",
                      symbols=("AUDCAD",), manifest_text=None,
                      display_name=None, magic=130013):
        sdir = root / "strategies" / folder
        sdir.mkdir(parents=True, exist_ok=True)
        if manifest_text is None:
            syms = ", ".join(symbols)
            manifest_text = (
                f'strategy_id: {folder.lower()}\n'
                f'display_name: "{display_name or folder}"\n'
                f"magic_number: {magic}\n"
                f"status: {status}\n"
                f"symbols: [{syms}]\n")
        (sdir / "manifest.yaml").write_text(manifest_text, encoding="utf-8")
        return sdir

    def write_status(short, instance, *, fresh=True, mode="PAPER",
                     corrupt=False, **over):
        d = db / short / instance
        d.mkdir(parents=True, exist_ok=True)
        p = d / "status.json"
        if corrupt:
            p.write_text("{pas du json", encoding="utf-8")
            return p
        now = datetime.now(timezone.utc)
        ts = now - (timedelta(hours=1) if fresh else timedelta(days=3))
        doc = {
            "schema": 1, "instance": instance, "strategy": short,
            "mode": mode, "generated_at_utc": _iso(ts),
            "last_bar_time": _iso(ts - timedelta(hours=1)),
            "n_closed_total": 42, "cum_r": 3.75, "pnl_chf": 812.50,
            "capital": 4812.50, "open_position": None, "error": None,
        }
        doc.update(over)
        p.write_text(json.dumps(doc), encoding="utf-8")
        return p

    def write_study(folder, *, fresh=True, **over):
        d = db / folder
        d.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        ts = now - (timedelta(hours=1) if fresh else timedelta(days=3))
        doc = {"generated_at_utc": _iso(ts), "n_closed_total": 7,
               "cum_r": 1.25, "capital": 10123.0, "open_position": None}
        doc.update(over)
        (d / "status.json").write_text(json.dumps(doc), encoding="utf-8")

    return SimpleNamespace(root=root, db=db, tmp=tmp_path,
                           make_strategy=make_strategy,
                           write_status=write_status,
                           write_study=write_study, iso=_iso)


@pytest.fixture()
def client(ui_env):
    """Client Flask de test sur le serveur de supervision."""
    from server.app import create_app
    app = create_app()
    app.testing = True
    return app.test_client()
