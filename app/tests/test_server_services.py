"""
Tests de la vue services communs (/api/services, UI-5) + pages HTML (UI-8).

POURQUOI ce banc : la vue services agrège des surfaces disparates (verrou
factory, panneau, logs, Telegram, datasets, tickets, études scellées). Le banc
fige : factory vivante/morte selon le mtime du verrou (UI-T5), tickets
bloquants détectés et en tête (UI-T5), présence de token SANS fuite de la
valeur (UI-T5), section watcher conditionnelle, secrets jamais listés, et le
service des trois pages HTML + assets sans CDN.

    pytest app/tests/test_server_services.py -q
"""
from __future__ import annotations

import os
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


# ── factory : verrou, panneau, logs (UI-T5) ─────────────────────────────────
def test_factory_alive_when_lock_fresh(client, ui_env):
    lock = ui_env.tmp / "factory.lock"
    lock.write_text("pid 4242 :: 2026-08-26 12:00:00\n", encoding="utf-8")
    f = client.get("/api/services").get_json()["factory"]
    assert f["alive"] is True
    assert f["lock_age_sec"] < 180
    assert "4242" in f["lock_holder"]


def test_factory_dead_when_lock_stale_or_absent(client, ui_env):
    f = client.get("/api/services").get_json()["factory"]
    assert f["alive"] is False and f["lock_age_sec"] is None

    lock = ui_env.tmp / "factory.lock"
    lock.write_text("pid 4242\n", encoding="utf-8")
    old = time.time() - 3600                     # bien au-delà de 180 s
    os.utime(lock, (old, old))
    f = client.get("/api/services").get_json()["factory"]
    assert f["alive"] is False and f["lock_age_sec"] > 180


def test_factory_panel_and_auto_off_flag(client, ui_env):
    (ui_env.tmp / "panel.txt").write_text(
        "# panneau de test\n"
        "gex_S017 = on           # tick 900s\n"
        "cc_S017 = on:3600\n"
        "notify = off          # AUTO-OFF 2026-08-26 12:00:00 — sortie 3 — SCELLÉ VIOLÉ\n",
        encoding="utf-8")
    panel = client.get("/api/services").get_json()["factory"]["panel"]
    assert panel["present"] is True
    by_name = {w["worker"]: w for w in panel["workers"]}
    assert by_name["gex_S017"]["on"] is True
    assert by_name["cc_S017"]["cadence"] == 3600
    assert by_name["notify"]["on"] is False
    assert by_name["notify"]["auto_off"] is True         # affiché en rouge


def test_factory_log_tail_parsed_per_worker(client, ui_env):
    logs = ui_env.tmp / "logs"
    logs.mkdir()
    (logs / "tbot-factory.log").write_text(
        "[2026-08-26 18:26:10] lance [gex_S017]  → 20260826-182610.log\n"
        "[2026-08-26 18:26:11] fini  [gex_S017] OK en 0.6s\n"
        "[2026-08-26 18:27:00] info  [gateway] ressource externe indisponible (0.2s)\n"
        "[2026-08-26 18:28:00]   gex_S017          armé       29s ago\n",  # table ignorée
        encoding="utf-8")
    f = client.get("/api/services").get_json()["factory"]
    last = f["last_by_worker"]
    assert last["gex_S017"]["event"] == "fini"
    assert "OK en 0.6s" in last["gex_S017"]["detail"]
    assert last["gateway"]["event"] == "info"
    assert all(e["worker"] in ("gex_S017", "gateway") for e in f["recent"])


# ── telegram : présence token, JAMAIS la valeur (UI-T5) ─────────────────────
def test_telegram_token_present_without_value_leak(client, ui_env):
    secret = "8123456789:AAsecretSECRETsecret"
    (ui_env.tmp / "tg.env").write_text(f"TELEGRAM_BOT_TOKEN={secret}\n",
                                       encoding="utf-8")
    gw = ui_env.db / "gateway"
    gw.mkdir(parents=True)
    (gw / "gateway_token.txt").write_text("9999:AAgwSECRET", encoding="utf-8")
    (gw / "state.json").write_text('{"offset": 12, "n_served": 3}',
                                   encoding="utf-8")

    r = client.get("/api/services")
    tg = r.get_json()["telegram"]
    assert tg["notifier"]["token_present"] is True
    assert tg["gateway"]["token_present"] is True
    assert tg["gateway"]["state"]["offset"] == 12
    # La valeur du token n'apparaît NULLE PART dans la réponse.
    raw = r.get_data(as_text=True)
    assert secret not in raw and "AAgwSECRET" not in raw


def test_telegram_absent_tokens(client, ui_env):
    tg = client.get("/api/services").get_json()["telegram"]
    assert tg["notifier"]["token_present"] is False
    assert tg["gateway"]["token_present"] is False
    assert tg["notifier"]["state"] is None


# ── datas : datasets listés, secrets JAMAIS ─────────────────────────────────
def test_datas_listing_skips_secrets(client, ui_env):
    (ui_env.db / "S013" / "S013.AUD-CAD").mkdir(parents=True)
    (ui_env.db / "S013" / "S013.AUD-CAD" / "status.json").write_text(
        "{}", encoding="utf-8")
    (ui_env.db / "secrets").mkdir()
    (ui_env.db / "secrets" / "api_key.txt").write_text("TOPSECRET",
                                                       encoding="utf-8")
    (ui_env.db / "readme.txt").write_text("hello", encoding="utf-8")

    r = client.get("/api/services")
    names = [d["name"] for d in r.get_json()["datas"]]
    assert "S013" in names and "readme.txt" in names
    assert "secrets" not in names
    assert "TOPSECRET" not in r.get_data(as_text=True)


# ── backup + watcher (section conditionnelle) ───────────────────────────────
def test_watcher_null_when_absent_then_served(client, ui_env):
    assert client.get("/api/services").get_json()["watcher"] is None
    wdir = ui_env.db / "watcher"
    wdir.mkdir(parents=True)
    (wdir / "status.json").write_text('{"state": "IDLE"}', encoding="utf-8")
    assert client.get("/api/services").get_json()["watcher"] == {
        "state": "IDLE"}


def test_backup_status_served(client, ui_env):
    bdir = ui_env.db / "backup"
    bdir.mkdir(parents=True)
    (bdir / "status.json").write_text('{"last_push": "2026-08-26"}',
                                      encoding="utf-8")
    assert client.get("/api/services").get_json()["backup"][
        "last_push"] == "2026-08-26"


# ── tickets : bloquants ouverts détectés et en tête (UI-T5) ─────────────────
def _ticket(path, tid, *, status="open", blocking=False):
    path.write_text(
        f"---\nid: {tid}\nfrom: cc-S013\nto: cc-support\nstatus: {status}\n"
        f"blocking: {'true' if blocking else 'false'}\ncreated: 2026-08-26\n"
        f"---\n\n## Question\ntest\n", encoding="utf-8")


def test_tickets_blocking_open_first(client, ui_env):
    tdir = ui_env.root / "tickets"
    tdir.mkdir()
    _ticket(tdir / "TCK-001_normal.md", "TCK-001")
    _ticket(tdir / "TCK-002_bloquant.md", "TCK-002", blocking=True)
    _ticket(tdir / "TCK-003_clos.md", "TCK-003", status="closed",
            blocking=True)

    tk = client.get("/api/services").get_json()["tickets"]
    assert tk["n_open"] == 2
    assert tk["n_blocking_open"] == 1
    assert [t["id"] for t in tk["tickets"]] == ["TCK-002", "TCK-001",
                                                "TCK-003"]
    assert tk["tickets"][0]["blocking"] is True


def test_tickets_empty_dir_clean(client, ui_env):
    tk = client.get("/api/services").get_json()["tickets"]
    assert tk == {"n_open": 0, "n_blocking_open": 0, "tickets": []}


# ── études scellées héritées (UI-9) ─────────────────────────────────────────
def test_etudes_inherited_panels_present(client, ui_env):
    ui_env.write_study("gold_forward", fresh=True)
    etudes = {e["dossier"]: e
              for e in client.get("/api/services").get_json()["etudes"]}
    assert set(etudes) == {"gold_forward", "s13_forward", "macd_ai_paper",
                           "s14_sentiment"}
    assert etudes["gold_forward"]["vivante"] is True
    assert etudes["gold_forward"]["trades"] == 7
    assert etudes["s13_forward"]["vivante"] is False    # jamais passée


# ── pages HTML + assets (UI-8 : vanilla, pas de CDN) ────────────────────────
def test_html_pages_served(client, ui_env):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "NIVEAUX D'EXPLOITATION" in html
    assert 'data-page="index"' in html

    r = client.get("/strategy/S013")
    assert r.status_code == 200
    assert 'data-page="strategy"' in r.get_data(as_text=True)

    r = client.get("/services")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "SERVICES COMMUNS" in html
    assert 'data-page="services"' in html


def test_assets_served_without_cdn(client, ui_env):
    js = client.get("/ui/app.js")
    css = client.get("/ui/style.css")
    assert js.status_code == 200 and css.status_code == 200
    # D-UI-2 : aucun asset distant — ni http:// ni https:// dans le front.
    for page in ("/", "/services"):
        html = client.get(page).get_data(as_text=True)
        assert "https://" not in html and "http://" not in html
    assert "https://" not in js.get_data(as_text=True)


# ── port du serveur (seam TBOT_UI_PORT — worker « supervision », T4) ────────
def test_ui_port_seam(monkeypatch):
    """Défaut 8742 ; TBOT_UI_PORT le remplace (PC dev : 8790 jusqu'à E6) ;
    valeur illisible → défaut, jamais un crash de serveur de supervision."""
    from server.app import ui_port
    monkeypatch.delenv("TBOT_UI_PORT", raising=False)
    assert ui_port() == 8742
    monkeypatch.setenv("TBOT_UI_PORT", "8790")
    assert ui_port() == 8790
    monkeypatch.setenv("TBOT_UI_PORT", "pouet")
    assert ui_port() == 8742
