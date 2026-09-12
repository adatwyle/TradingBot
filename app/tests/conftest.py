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

    # ── journaux forward jetables (SPEC_analytics-trades §8) ────────────
    # Trois en-têtes réels : gold (mono-instrument), s13/s20 (arm + symbol),
    # alexg/macd_ai (signal_id, decision, reason…). Le helper choisit le
    # plus petit en-tête qui porte toutes les clés fournies, sauf override.
    gold_cols = ["measured_at_utc", "event", "trade_id", "bar_time", "side",
                 "entry_price", "stop_price", "target_price", "size_lots",
                 "risk_ccy", "exit_price", "exit_reason", "pnl_r", "pnl_ccy",
                 "capital_after", "chain"]
    arm_cols = gold_cols[:2] + ["arm", "symbol"] + gold_cols[2:]
    alexg_cols = ["measured_at_utc", "event", "arm", "symbol", "signal_id",
                  "trade_id", "bar_time", "side", "entry_price", "stop_price",
                  "target_price", "size_lots", "risk_ccy", "exit_price",
                  "exit_reason", "pnl_r", "pnl_r_nocost", "pnl_ccy",
                  "capital_after", "decision", "size_frac", "sl_adjust",
                  "tp_adjust", "reason", "chain"]

    def _journal_columns(rows):
        keys = set()
        for r in rows:
            keys |= set(r)
        for cols in (gold_cols, arm_cols, alexg_cols):
            if keys <= set(cols):
                return cols
        return alexg_cols + sorted(keys - set(alexg_cols))

    def _csv_line(values):
        import csv
        import io
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerow(values)
        return buf.getvalue()

    def _default_params(study, rows):
        symbols = sorted({r.get("symbol") for r in rows if r.get("symbol")})
        params = {"study": study, "timeframe": "H1",
                  "sizing": {"capital_initial": 10000.0,
                             "risk_per_trade_pct": 1.0}}
        if symbols:
            params["instruments"] = {
                s: next((r.get("arm") for r in rows
                         if r.get("symbol") == s and r.get("arm")), "PRIMARY")
                for s in symbols}
            params["specs"] = {
                s: {"symbol": s, "pip": 0.0001, "spread_pips": 2.0,
                    "max_spread_pips": 4.0, "pip_value_per_lot": 10.0,
                    "slippage_pips": 0.5} for s in symbols}
        else:
            params["instrument"] = "XAUUSD"
            params["spec"] = {"symbol": "XAUUSD", "pip": 0.01,
                              "spread_pips": 25.0, "max_spread_pips": 60.0,
                              "pip_value_per_lot": 1.0, "slippage_pips": 0.0}
        return params

    def write_journal(study, rows, *, chain=True, params=..., state=...,
                      strategy_folder=..., columns=None):
        """journal.csv chaîné SHA-256 (algorithme des études) + params.json
        + state.json jetables. ``chain=False`` ⇒ maillon falsifié sur la
        1ʳᵉ ligne de données. ``params``/``state``/``strategy_folder`` :
        ``...`` = défaut sensé, ``None`` = rien n'est écrit, sinon la valeur
        (dict ou nom de dossier) est utilisée telle quelle."""
        import hashlib
        cols = columns or _journal_columns(rows)
        d = db / study
        d.mkdir(parents=True, exist_ok=True)
        raw = _csv_line(cols).encode("utf-8")
        for i, r in enumerate(rows):
            link = hashlib.sha256(raw).hexdigest()
            if not chain and i == 0:
                link = "0" * 64
            cells = [r.get(c, "") if c != "chain" else link for c in cols]
            raw += _csv_line(cells).encode("utf-8")
        (d / "journal.csv").write_bytes(raw)

        if params is ...:
            params = _default_params(study, rows)
        if params is not None:
            sdir = root / "studies" / study
            sdir.mkdir(parents=True, exist_ok=True)
            (sdir / "params.json").write_text(json.dumps(params),
                                              encoding="utf-8")
        if state is ...:
            state = {"schema": 1, "started_at": "2026-08-16T20:59:28Z",
                     "journal_bytes": len(raw),
                     "journal_sha256": hashlib.sha256(raw).hexdigest()}
        if state is not None:
            (d / "state.json").write_text(json.dumps(state), encoding="utf-8")

        if strategy_folder is ...:
            from server.journal_adapter import STUDY_STRATEGY
            sid = STUDY_STRATEGY.get(study)
            strategy_folder = f"{sid}_fixture" if sid else None
        if strategy_folder:
            sid = strategy_folder.split("_", 1)[0]
            symbols = sorted({r.get("symbol") for r in rows if r.get("symbol")})
            if not symbols and params:
                symbols = [params.get("instrument")
                           or (params.get("spec") or {}).get("symbol")
                           or "XAUUSD"]
            magic = 130000 + int(sid[1:]) if sid[1:].isdigit() else 130013
            syms = ", ".join(symbols)
            make_strategy(strategy_folder, manifest_text=(
                f"strategy_id: {strategy_folder.lower()}\n"
                f'display_name: "{strategy_folder}"\n'
                f'version: "1.0.0"\n'
                f"magic_number: {magic}\n"
                f"status: PAPER\n"
                f"symbols: [{syms}]\n"))
        return d / "journal.csv"

    def seed_ledger(path, trades):
        """Ledger jetable : une entrée par dict de ``trades`` (clés de
        ``Ledger.record_trade`` ; ``net`` = raccourci de ``gross_pnl`` ;
        ``close_time=None`` ⇒ position ouverte via ``open_trade``). Plusieurs
        instances, modes, devises, mois et trades à 0 acceptés. Retourne les
        ids ledger."""
        from core.ledger import Ledger
        t0 = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
        ids = []
        with Ledger(path) as lg:
            for i, t in enumerate(trades):
                t = dict(t)
                base = dict(strategy_id="S013", instance_id="S013.AUD-CAD",
                            strategy_version="1.0.0", magic_number=130013,
                            mode="PAPER", symbol="AUDCAD", timeframe="D1",
                            side="LONG", volume_lots=0.1, open_price=0.9,
                            stop_price=0.89, currency="CHF",
                            open_time=t0 + timedelta(days=i, hours=-2))
                if "net" in t:
                    t.setdefault("gross_pnl", t.pop("net"))
                close_time = t.pop("close_time",
                                   t0 + timedelta(days=i)
                                   if "gross_pnl" in t else None)
                base.update(t)
                if close_time is None:
                    ids.append(lg.open_trade(**base))
                    continue
                base.setdefault("close_price", 0.91)
                base.setdefault("exit_reason", "TP")
                base.setdefault("gross_pnl", 0.0)
                ids.append(lg.record_trade(close_time=close_time, **base))
        return ids

    return SimpleNamespace(root=root, db=db, tmp=tmp_path,
                           make_strategy=make_strategy,
                           write_status=write_status,
                           write_study=write_study, iso=_iso,
                           write_journal=write_journal,
                           seed_ledger=seed_ledger)


@pytest.fixture()
def client(ui_env):
    """Client Flask de test sur le serveur de supervision."""
    from server.app import create_app
    app = create_app()
    app.testing = True
    return app.test_client()
