"""
Tests des routes d'analyse (SPEC_analytics-trades §6, AN-1, AN-4, AN-10/11,
AN-28, AN-31 — AN-T11, AN-T17 (HTTP), AN-T18 (HTTP)).

POURQUOI ce banc : le moteur (test_server_analytics.py) et l'adaptateur
(test_server_journal_adapter.py) sont testés purs ; ici on fige le CONTRAT
HTTP : le shell servi sans CDN, le 400 sur filtre hors domaine comme SEULE
erreur (AN-4), le « jamais un 500 » quand le moteur casse (D-AN-16), le 405
sur toute méthode autre que GET (UI-7), la pagination et le tri du journal
des trades (AN-T17), les positions ouvertes hors statistiques et la
séparation PAPER / LIVE du bandeau KPI (AN-T18), le tout sur le layout
jetable ``ui_env`` (journaux + ledger de fixtures, jamais C:\\db).

    pytest app/tests/test_server_analytics_routes.py -q
"""
from __future__ import annotations

import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

ANALYTICS_ROUTES = ("/api/analytics", "/api/analytics/trades",
                    "/api/analytics/kpi")


# ── lignes de journal gold (même forme que test_server_journal_adapter) ─────
def _open(trade_id, bar_time, *, side="SHORT", capital=10000.0,
          measured="2026-08-18T22:57:55Z"):
    return {"measured_at_utc": measured, "event": "OPEN", "trade_id": trade_id,
            "bar_time": bar_time, "side": side, "entry_price": 4345.081,
            "stop_price": 4368.801, "target_price": 4282.286,
            "size_lots": 0.0422, "risk_ccy": 100.0, "capital_after": capital}


def _close(trade_id, bar_time, *, side="SHORT", pnl=-100.53, pnl_r=-1.0053,
           reason="SL", capital=9899.47, measured="2026-08-19T13:59:42Z"):
    return {"measured_at_utc": measured, "event": "CLOSE", "trade_id": trade_id,
            "bar_time": bar_time, "side": side, "entry_price": 4345.081,
            "stop_price": 4368.801, "target_price": 4282.286,
            "size_lots": 0.0422, "risk_ccy": 100.0, "exit_price": 4368.801,
            "exit_reason": reason, "pnl_r": pnl_r, "pnl_ccy": pnl,
            "capital_after": capital}


def _snapshot(*roots):
    """Noms des fichiers/dossiers sous ``roots`` — preuve « rien créé »."""
    out = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            out.update(os.path.join(dirpath, n) for n in dirnames + filenames)
    return out


# ── AN-T11 : shell, layout vide, 405, lien analyse, S020 ────────────────────
def test_analytics_shell_served_without_cdn(client, ui_env):
    r = client.get("/analytics")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'data-page="analytics"' in html
    assert "https://" not in html and "http://" not in html
    assert 'href="/analytics"' in html


def test_api_analytics_empty_layout_is_200(client, ui_env):
    """Layout vide (aucune stratégie, ledger absent, aucun journal) :
    200, ``by_currency = {}``, AN-11 (source + warnings toujours présents,
    « ledger absent » = warning, pas une erreur), aucune création de DB."""
    before = _snapshot(ui_env.db, ui_env.root)
    r = client.get("/api/analytics")
    assert r.status_code == 200
    d = r.get_json()
    assert d["by_currency"] == {}
    assert d["header"]["n_trades"] == 0 and d["header"]["mode"] == "PAPER"
    assert d["filters"]["applied"]["mode"] == "PAPER"
    assert set(d["source"]) >= {"ledger_rows", "journal_rows", "dedup",
                                "ledger_present", "studies"}
    assert d["source"]["ledger_present"] is False
    assert any("ledger absent" in w for w in d["warnings"])
    assert d["open_positions"] == []
    assert "generated" in d and "version" in d
    assert _snapshot(ui_env.db, ui_env.root) == before
    assert not (ui_env.db / "ledger.db").exists()


def test_invalid_filter_is_400_json_only_error(client, ui_env):
    """AN-4 : valeur hors domaine ⇒ 400 ``{"error": "paramètre invalide :
    <nom>=<valeur>"}`` sur les deux routes filtrées."""
    for url in ("/api/analytics", "/api/analytics/trades"):
        r = client.get(url + "?mode=XX")
        assert r.status_code == 400, url
        assert r.get_json()["error"] == "paramètre invalide : mode=XX"
        r = client.get(url + "?source=bogus")
        assert r.status_code == 400
        assert r.get_json()["error"].startswith("paramètre invalide : source=")
        r = client.get(url + "?from=2026-13-40")
        assert r.status_code == 400
    # Une valeur valide (repeated keys) passe.
    r = client.get("/api/analytics?mode=LIVE&strategy=S011&strategy=S013")
    assert r.status_code == 200
    assert r.get_json()["filters"]["applied"]["strategy"] == ["S011", "S013"]


def test_write_methods_are_405(client, ui_env):
    """UI-7 / §6.4 : toute méthode autre que GET ⇒ 405 — rendu JSON comme
    les 400 de l'API (relecture tour 1), jamais la page HTML Flask."""
    for url in ANALYTICS_ROUTES + ("/analytics",):
        for r in (client.post(url), client.put(url), client.delete(url)):
            assert r.status_code == 405, url
            assert r.is_json and r.get_json()["error"] == "méthode non autorisée"


def test_analytics_generated_is_utc_zulu_on_nominal_degraded_and_400(
        client, ui_env, monkeypatch):
    """Relecture tour 1 : une seule convention d'horodatage sur les routes
    analytics — UTC suffixé Z (§6.1), y compris en réponse dégradée et 400."""
    from server import analytics

    def zulu(d):
        return d["generated"].endswith("Z") and len(d["generated"]) == 20

    for url in ANALYTICS_ROUTES:
        assert zulu(client.get(url).get_json()), url
    assert zulu(client.get("/api/analytics?mode=XX").get_json())

    def boom(*_a, **_k):
        raise RuntimeError("panne")
    monkeypatch.setattr(analytics, "build_analytics", boom)
    monkeypatch.setattr(analytics, "build_trades_page", boom)
    monkeypatch.setattr(analytics, "build_kpi", boom)
    for url in ANALYTICS_ROUTES:
        assert zulu(client.get(url).get_json()), url
    # /api/state garde sa convention locale (inchangé, hors périmètre).
    assert not client.get("/api/state").get_json()["generated"].endswith("Z")


def test_front_polling_guard_ignores_generated(client, ui_env):
    """AN-3 / D-AN-14 (relecture tour 1) : le garde « re-rendu seulement si
    le JSON diffère » compare le corps SANS ``generated`` (horodatage
    recalculé à chaque requête) — sinon le DOM est reconstruit à chaque
    poll de 10 s. Garde statique sur app.js, faute de banc JS."""
    js = client.get("/ui/app.js").get_data(as_text=True)
    assert "function payloadText(body)" in js
    assert "delete rest.generated" in js
    assert js.count("payloadText(res.body)") == 2      # refreshAnalytics + refreshJournal
    assert js.count("payloadText(body)") >= 1          # refreshIndexKpi
    assert "JSON.stringify(res.body)" not in js
    assert "JSON.stringify(body)" not in js


def test_nav_link_analyse_present_in_four_shells(client, ui_env):
    for page in ("/", "/strategy/S011", "/services", "/analytics"):
        html = client.get(page).get_data(as_text=True)
        assert 'href="/analytics">analyse</a>' in html, page


def test_api_strategy_s020_no_longer_404(client, ui_env):
    """LEGACY_STUDIES aligné sur ``journal_adapter.STUDIES`` : S020 porte
    son étude s20_forward sur sa carte."""
    ui_env.make_strategy("S020_balke_macd_cross", status="PAPER",
                         symbols=("EURUSD",))
    ui_env.write_study("s20_forward", fresh=True)
    r = client.get("/api/strategy/S020")
    assert r.status_code == 200
    assert [e["dossier"] for e in r.get_json()["card"]["etudes"]] == [
        "s20_forward"]


# ── D-AN-16 : le moteur casse ⇒ jamais un 500 ──────────────────────────────
def test_engine_failure_never_500(client, ui_env, monkeypatch):
    """Une exception du moteur APRÈS validation des filtres devient un
    sous-ensemble vide + warning explicite (le message n'est pas avalé)."""
    from server import analytics

    def boom(*_a, **_k):
        raise RuntimeError("disque en feu")

    monkeypatch.setattr(analytics, "build_analytics", boom)
    monkeypatch.setattr(analytics, "build_trades_page", boom)
    monkeypatch.setattr(analytics, "build_kpi", boom)

    r = client.get("/api/analytics?mode=LIVE&strategy=S011")
    assert r.status_code == 200
    d = r.get_json()
    assert d["by_currency"] == {} and d["header"]["n_trades"] == 0
    assert d["header"]["mode"] == "LIVE"
    assert d["filters"]["applied"]["strategy"] == ["S011"]
    assert any("disque en feu" in w and "RuntimeError" in w
               for w in d["warnings"])

    r = client.get("/api/analytics/trades?page=3&limit=50")
    assert r.status_code == 200
    d = r.get_json()
    assert d["rows"] == [] and d["total"] == 0
    assert d["page"] == 3 and d["limit"] == 50
    assert any("disque en feu" in w for w in d["warnings"])

    r = client.get("/api/analytics/kpi")
    assert r.status_code == 200
    d = r.get_json()
    assert d["PAPER"] == {} and d["LIVE"] == {}
    assert any("disque en feu" in w for w in d["warnings"])

    # Le 400 reste prioritaire : les filtres sont validés AVANT le moteur.
    assert client.get("/api/analytics?mode=XX").status_code == 400
    assert client.get("/api/analytics/trades?limit=0").status_code == 400


# ── journaux réels (format gold) via la route ───────────────────────────────
def test_api_analytics_on_journal_fixture(client, ui_env):
    """Un journal gold jetable (2 clos + 1 OPEN) : §6.1 rempli, l'étude
    visible dans ``source.studies`` avec ``chain_ok``, KPI CHF cohérents,
    position ouverte hors statistiques, aucun fichier créé."""
    ui_env.write_journal("gold_forward", [
        _open("SHORT_20260818_2100", "2026-08-18T21:00:00"),
        _close("SHORT_20260818_2100", "2026-08-19T12:00:00"),
        _open("LONG_20260821_0700", "2026-08-21T07:00:00", side="LONG",
              capital=9899.47, measured="2026-08-21T08:12:34Z"),
        _close("LONG_20260821_0700", "2026-08-22T10:00:00", side="LONG",
               pnl=257.4, pnl_r=2.6, reason="TP", capital=10156.87,
               measured="2026-08-22T11:00:00Z"),
        _open("SHORT_20260910_1400", "2026-09-10T14:00:00", capital=10156.87,
              measured="2026-09-10T15:34:53Z"),
    ])
    before = _snapshot(ui_env.db, ui_env.root)
    r = client.get("/api/analytics?mode=PAPER")
    assert r.status_code == 200
    d = r.get_json()
    study = d["source"]["studies"]["gold_forward"]
    assert study["strategy_id"] == "S011" and study["chain_ok"] is True
    assert study["closed"] == 2 and study["open"] == 1
    assert d["source"]["journal_rows"] == 2 and d["source"]["dedup"] == 0
    assert d["header"]["n_trades"] == 2
    assert d["header"]["source_kind"] == "journaux"
    assert d["header"]["base"] == {"CHF": 10000.0}
    k = d["by_currency"]["CHF"]["kpi"]
    assert k["total_trades"] == 2 and k["wins"] == 1 and k["losses"] == 1
    assert abs(k["net_pnl"] - 156.87) < 1e-6
    assert d["by_currency"]["CHF"]["curve"]["base"] == 10000.0
    assert len(d["by_currency"]["CHF"]["curve"]["points"]) == 2
    assert d["filters"]["options"]["instance"] == ["S011.XAU-USD"]
    assert [p["instance_id"] for p in d["open_positions"]] == ["S011.XAU-USD"]
    assert d["open_positions"][0]["source"] == "journal"
    # Seuls avertissements légitimes : ledger absent (AN-11) et les 4 autres
    # études du catalogue sans journal dans ce layout (§3.2) — jamais une
    # alerte sur gold_forward.
    assert all(("ledger absent" in w or "journal absent" in w)
               and "gold_forward" not in w for w in d["warnings"]), d["warnings"]
    assert _snapshot(ui_env.db, ui_env.root) == before

    # Chaîne altérée : lignes servies, alerte explicite, jamais une erreur.
    ui_env.write_journal("gold_forward", [
        _open("SHORT_20260818_2100", "2026-08-18T21:00:00"),
        _close("SHORT_20260818_2100", "2026-08-19T12:00:00"),
    ], chain=False)
    d = client.get("/api/analytics").get_json()
    assert d["source"]["studies"]["gold_forward"]["chain_ok"] is False
    assert any("journal altéré : gold_forward" in w for w in d["warnings"])
    assert d["header"]["n_trades"] == 1


# ── AN-T17 : journal des trades paginé ──────────────────────────────────────
def test_trades_route_pagination_and_sort(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", status="PAPER")
    ui_env.seed_ledger(ui_env.db / "ledger.db", [
        {"net": 100.0, "risk_amount": 100.0}, {"net": -50.0},
        {"net": 0.0}, {"net": 30.0}, {"net": -20.0, "risk_amount": 40.0}])

    d = client.get("/api/analytics/trades").get_json()
    assert set(d) >= {"generated", "version", "total", "page", "limit",
                      "rows", "warnings"}
    assert d["total"] == 5 and d["page"] == 1 and d["limit"] == 200
    assert len(d["rows"]) == 5
    closes = [r["close_time"] for r in d["rows"]]
    assert closes == sorted(closes, reverse=True)         # close_time desc
    row = d["rows"][0]
    assert {"pnl_r", "holding_h", "magic_ok", "arm", "source",
            "edge_cost_ccy"} <= set(row)
    assert "meta_json" not in row
    assert row["source"] == "ledger" and row["magic_ok"] is True
    assert row["holding_h"] == 2.0                        # ouvert 2 h avant
    assert row["pnl_r"] == -0.5                           # net / risk_amount
    assert d["rows"][-1]["pnl_r"] == 1.0
    assert d["rows"][1]["pnl_r"] is None                  # risque inconnu

    d = client.get("/api/analytics/trades?page=2&limit=2").get_json()
    assert d["total"] == 5 and len(d["rows"]) == 2
    assert d["page"] == 2 and d["limit"] == 2
    assert [r["net_pnl"] for r in d["rows"]] == [0.0, -50.0]

    d = client.get("/api/analytics/trades?page=4&limit=2").get_json()
    assert d["rows"] == [] and d["total"] == 5

    r = client.get("/api/analytics/trades?limit=5000")
    assert r.status_code == 400
    assert r.get_json()["error"] == "paramètre invalide : limit=5000"
    assert client.get("/api/analytics/trades?page=0").status_code == 400

    # Les filtres AN-4 s'appliquent aussi au journal.
    d = client.get("/api/analytics/trades?side=SHORT").get_json()
    assert d["total"] == 0 and d["rows"] == []


# ── AN-T18 : positions ouvertes + bandeau KPI PAPER / LIVE ──────────────────
def test_open_positions_and_kpi_route(client, ui_env):
    ui_env.make_strategy("S013_macd_fx", status="PAPER")
    ui_env.seed_ledger(ui_env.db / "ledger.db", [
        {"net": 100.0},                                   # clos PAPER
        {"side": "SHORT"},                                # ouvert PAPER (ledger)
        {"net": 40.0, "mode": "LIVE"},                    # clos LIVE
        {"net": -10.0, "mode": "BACKTEST"},               # jamais dans le kpi
    ])
    ui_env.write_journal("gold_forward", [
        _open("SHORT_20260910_1400", "2026-09-10T14:00:00")])  # OPEN seul

    d = client.get("/api/analytics?mode=PAPER").get_json()
    assert d["header"]["n_trades"] == 1
    assert d["by_currency"]["CHF"]["kpi"]["total_trades"] == 1
    opened = d["open_positions"]
    assert len(opened) == 2
    assert {p["source"] for p in opened} == {"ledger", "journal"}
    assert {p["instance_id"] for p in opened} == {"S013.AUD-CAD",
                                                  "S011.XAU-USD"}
    assert all(p["mode"] == "PAPER" for p in opened)
    assert all("net_pnl" not in p for p in opened)        # jamais de P&L flottant
    # Filtre instance : seule la position de l'instance demandée reste.
    d = client.get("/api/analytics?instance=S011.XAU-USD").get_json()
    assert [p["source"] for p in d["open_positions"]] == ["journal"]
    assert d["header"]["n_trades"] == 0

    r = client.get("/api/analytics/kpi")
    assert r.status_code == 200
    k = r.get_json()
    assert set(k) >= {"generated", "version", "PAPER", "LIVE", "warnings"}
    assert "BACKTEST" not in k
    assert k["PAPER"]["CHF"]["total_trades"] == 1
    assert abs(k["PAPER"]["CHF"]["net_pnl"] - 100.0) < 1e-6
    assert k["LIVE"]["CHF"]["total_trades"] == 1
    assert abs(k["LIVE"]["CHF"]["net_pnl"] - 40.0) < 1e-6
