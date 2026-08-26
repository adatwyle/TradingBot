"""
Tests du serveur de supervision — découverte, contrat de perf, niveaux.

POURQUOI ce banc : le prototype affichait des dashboards non connectés ; la
refonte (SPEC_ui-dynamique) exige que TOUT vienne du disque au moment de
servir. Le banc fige : la découverte à la requête (UI-T1 — pas de cache au
démarrage), la tolérance du contrat status.json (UI-T2 — valide/absent/
corrompu sans jamais un 500), la confrontation déclaré/réel (UI-T3 — un
manifeste qui ment s'affiche en divergence), la cohérence des agrégats avec
un ledger de fixtures (UI-T4), et l'état vide propre (aucune stratégie, db
absente → pages servies).

    pytest app/tests/test_server_state.py -q
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.ledger import Ledger  # noqa: E402


# ── UI-T1 : découverte dynamique à la requête ───────────────────────────────
def test_discovery_between_two_requests(client, ui_env):
    r1 = client.get("/api/state")
    assert r1.status_code == 200
    assert r1.get_json()["strategies"] == []

    ui_env.make_strategy("S099_new_one", status="RESEARCH")
    r2 = client.get("/api/state")           # même serveur, aucun redémarrage
    ids = [s["id"] for s in r2.get_json()["strategies"]]
    assert ids == ["S099_new_one"]


def test_underscore_folders_ignored(client, ui_env):
    ui_env.make_strategy("_TEMPLATE")
    ui_env.make_strategy("S001_real")
    ids = [s["id"] for s in client.get("/api/state").get_json()["strategies"]]
    assert ids == ["S001_real"]


def test_invalid_manifest_never_silently_absent(client, ui_env):
    # YAML cassé ET manifest manquant : la carte s'affiche en erreur (UI-1).
    sdir = ui_env.root / "strategies" / "S050_broken"
    sdir.mkdir(parents=True)
    (sdir / "manifest.yaml").write_text("{{::pas du yaml", encoding="utf-8")
    (ui_env.root / "strategies" / "S051_missing").mkdir()

    strategies = {s["id"]: s
                  for s in client.get("/api/state").get_json()["strategies"]}
    assert "S050_broken" in strategies
    assert "manifest invalide" in strategies["S050_broken"]["manifest_error"]
    assert "S051_missing" in strategies
    assert strategies["S051_missing"]["manifest_error"] == "manifest.yaml absent"


# ── UI-T2 : status.json valide / absent / corrompu ──────────────────────────
def test_status_valid_absent_corrupt_states(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", symbols=("AUDCAD", "EURJPY", "SPY"))
    ui_env.write_status("S013", "S013.AUD-CAD", fresh=True)
    ui_env.write_status("S013", "S013.SPY", corrupt=True)
    # S013.EUR-JPY : pas de fichier — « jamais passée », état légitime.

    r = client.get("/api/state")
    assert r.status_code == 200                     # jamais un 500 (UI-T2)
    card = r.get_json()["strategies"][0]
    by_inst = {i["instance"]: i for i in card["instances"]}

    ok = by_inst["S013.AUD-CAD"]
    assert ok["state"] == "ok" and ok["alive"] is True
    assert ok["n_closed_total"] == 42 and ok["cum_r"] == 3.75
    assert by_inst["S013.EUR-JPY"]["state"] == "never"
    assert by_inst["S013.SPY"]["state"] == "unreadable"


def test_stale_status_soft_alert(client, ui_env):
    # Frais > 24 h : instance affichée avec « dernier passage », pas vivante.
    ui_env.make_strategy("S013_macd_fx")
    ui_env.write_status("S013", "S013.AUD-CAD", fresh=False)
    card = client.get("/api/state").get_json()["strategies"][0]
    inst = card["instances"][0]
    assert inst["state"] == "ok" and inst["alive"] is False
    assert inst["age_sec"] > 24 * 3600


def test_undeclared_instance_on_disk_still_shown(client, ui_env):
    # Une instance qui TOURNE mais que le manifeste a oubliée doit se voir.
    ui_env.make_strategy("S013_macd_fx", symbols=("AUDCAD",))
    ui_env.write_status("S013", "S013.XAU-USD", fresh=True)
    card = client.get("/api/state").get_json()["strategies"][0]
    names = {i["instance"] for i in card["instances"]}
    assert names == {"S013.AUD-CAD", "S013.XAU-USD"}


# ── UI-T3 : divergences déclaré / réel ──────────────────────────────────────
def test_divergence_paper_declared_without_living_instance(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", status="PAPER")   # aucune instance vive
    n = client.get("/api/state").get_json()["niveaux"]
    assert "S013_macd_fx" in n["paper"]
    assert any("S013" in d and "PAPER" in d and "aucune instance vivante" in d
               for d in n["divergences"])


def test_divergence_living_instance_but_declared_dev(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", status="RESEARCH")
    ui_env.write_status("S013", "S013.AUD-CAD", fresh=True)
    n = client.get("/api/state").get_json()["niveaux"]
    # L'activité réelle remonte la carte en PAPER, divergence affichée.
    assert "S013_macd_fx" in n["paper"] and "S013_macd_fx" not in n["dev"]
    assert any("S013" in d and "RESEARCH" in d and "attendu PAPER" in d
               for d in n["divergences"])


def test_no_divergence_when_declared_matches_real(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", status="PAPER")
    ui_env.write_status("S013", "S013.AUD-CAD", fresh=True)
    n = client.get("/api/state").get_json()["niveaux"]
    assert n["divergences"] == []


def test_divergence_live_declared_without_live_instance(client, ui_env):
    ui_env.make_strategy("S001_armed", status="LIVE")
    n = client.get("/api/state").get_json()["niveaux"]
    assert "S001_armed" in n["prod"]
    assert any("S001" in d and "LIVE" in d for d in n["divergences"])


def test_living_legacy_study_counts_as_real_paper(client, ui_env):
    # Étude scellée héritée vivante -> la stratégie instanciée vaut PAPER réel.
    ui_env.make_strategy("S011_legacy_breakout", status="BACKTESTED")
    ui_env.write_study("gold_forward", fresh=True)
    n = client.get("/api/state").get_json()["niveaux"]
    assert "S011_legacy_breakout" in n["paper"]
    assert any("S011" in d and "attendu PAPER" in d for d in n["divergences"])


def test_levels_placement(client, ui_env):
    ui_env.make_strategy("S001_live", status="LIVE")
    ui_env.make_strategy("S002_paper", status="PAPER")
    ui_env.write_status("S002", "S002.AUD-CAD", fresh=True)
    ui_env.make_strategy("S003_dev", status="RESEARCH")
    ui_env.make_strategy("S004_done", status="RETIRED")
    n = client.get("/api/state").get_json()["niveaux"]
    assert n["prod"] == ["S001_live"]
    assert n["paper"] == ["S002_paper"]
    assert n["dev"] == ["S003_dev"]
    assert n["retired"] == ["S004_done"]


# ── UI-T4 : agrégats cohérents avec un ledger de fixtures ───────────────────
def _seed_ledger(path, short="S013", instance="S013.AUD-CAD"):
    base = dict(strategy_id=short, instance_id=instance,
                strategy_version="1.0.0", magic_number=130013, mode="PAPER",
                symbol="AUDCAD", timeframe="D1", side="LONG", volume_lots=0.1,
                open_price=0.9, stop_price=0.89, currency="CHF")
    t0 = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    with Ledger(path) as lg:
        for i, (gross, com) in enumerate([(100.0, 2.0), (-50.0, 2.0),
                                          (30.0, 2.0)]):
            lg.record_trade(open_time=t0 + timedelta(days=i, hours=-2),
                            close_time=t0 + timedelta(days=i),
                            close_price=0.91, exit_reason="TP",
                            gross_pnl=gross, commission=com, **base)


def test_strategy_detail_aggregates_match_fixture_ledger(client, ui_env):
    ui_env.make_strategy("S013_macd_fx")
    _seed_ledger(ui_env.db / "ledger.db")

    r = client.get("/api/strategy/S013")
    assert r.status_code == 200
    d = r.get_json()
    # 3 trades clos, nets 98 / -52 / 28 -> total 74, plus récent en tête.
    assert len(d["trades"]) == 3
    assert d["trades"][0]["close_time"] > d["trades"][-1]["close_time"]
    year = d["aggregates"]["year"]
    assert len(year) == 1 and year[0]["n_trades"] == 3
    assert abs(year[0]["net"] - 74.0) < 1e-6
    assert len(d["aggregates"]["day"]) == 3
    # Repli §3.2 : pas d'equity_snapshots -> cumul des net_pnl clos.
    cum = d["equity"]["S013.AUD-CAD"]
    assert [p[1] for p in cum] == [98.0, 46.0, 74.0]


def test_equity_route_snapshots_take_precedence(client, ui_env):
    ui_env.make_strategy("S013_macd_fx")
    path = ui_env.db / "ledger.db"
    _seed_ledger(path)
    with Ledger(path) as lg:
        for i, eq in enumerate([1000.0, 1100.0]):
            lg.record_equity_snapshot(
                strategy_id="S013", instance_id="S013.AUD-CAD", mode="PAPER",
                equity=eq,
                timestamp=datetime(2026, 8, 25, i, 0, tzinfo=timezone.utc))
    r = client.get("/api/equity/S013/S013.AUD-CAD")
    assert r.status_code == 200
    pts = r.get_json()
    assert [p[1] for p in pts] == [1000.0, 1100.0]


def test_equity_route_unknown_strategy_404(client, ui_env):
    r = client.get("/api/equity/S404/S404.AUD-CAD")
    assert r.status_code == 404


def test_api_strategy_unknown_is_404_json(client, ui_env):
    r = client.get("/api/strategy/S404")
    assert r.status_code == 404
    assert "inconnue" in r.get_json()["error"]


def test_api_strategy_accepts_short_and_folder_ids(client, ui_env):
    ui_env.make_strategy("S013_macd_fx")
    assert client.get("/api/strategy/S013").status_code == 200
    assert client.get("/api/strategy/S013_macd_fx").status_code == 200


# ── /api/state : payload complet (UI-7) ─────────────────────────────────────
def test_api_state_payload_complete(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", status="PAPER")
    ui_env.write_status("S013", "S013.AUD-CAD", fresh=True)
    d = client.get("/api/state").get_json()
    assert set(d) >= {"generated", "version", "niveaux", "strategies"}
    assert set(d["niveaux"]) == {"prod", "paper", "dev", "retired",
                                 "divergences"}
    card = d["strategies"][0]
    assert set(card) >= {"id", "short", "name", "magic", "declared",
                         "manifest_error", "alive", "instances"}
    inst = card["instances"][0]
    # La carte UI-3 : trades clos, R cumulé, PnL CHF, position, dernier
    # passage, données de sparkline.
    assert set(inst) >= {"instance", "n_closed_total", "cum_r", "pnl_chf",
                         "open_position", "generated_at_utc", "alive",
                         "equity"}
    import re
    assert re.match(r"^\d+\.\d+\.\d+$", d["version"])


# ── état vide propre : aucune stratégie, db absente ─────────────────────────
def test_empty_state_serves_everything(client, ui_env, monkeypatch):
    shutil.rmtree(ui_env.root / "strategies")
    monkeypatch.setenv("TBOT_DB_DIR", str(ui_env.tmp / "nodb"))        # absente
    monkeypatch.setenv("TBOT_LEDGER_DB", str(ui_env.tmp / "nodb" / "l.db"))

    d = client.get("/api/state")
    assert d.status_code == 200
    assert d.get_json()["strategies"] == []
    assert client.get("/api/services").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/services").status_code == 200
    assert client.get("/strategy/S013").status_code == 200      # shell servi
    assert client.get("/api/strategy/S013").status_code == 404  # 404 JSON
    # La db ABSENTE ne doit pas avoir été créée par une lecture (read-only).
    assert not (ui_env.tmp / "nodb").exists()


# ── lecture seule stricte (UI-7) : aucune route d'écriture ──────────────────
def test_no_write_methods(client, ui_env):
    for url in ("/api/state", "/api/services", "/"):
        assert client.post(url).status_code == 405
        assert client.delete(url).status_code == 405
