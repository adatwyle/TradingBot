"""
Tests de core/ledger — la source unique de vérité des résultats (SPEC_ledger.md).

POURQUOI ce banc : aucune stratégie n'écrit ses propres agrégats — tout trade
(BACKTEST, PAPER, LIVE) atterrit dans le ledger qui sert le dashboard, Telegram
et le fisc. Le banc fige : les migrations user_version (v1 schema.sql, v2
instance_id), la décomposition brut/commission/swap/net (le net seul ne suffit
pas au fisc), les agrégats en CALENDRIER LOCAL (un trade de 23:30 UTC compte
le bon jour local), la semaine ISO à cheval sur deux années, et le refus de
toute addition inter-devises silencieuse.

La DB vit TOUJOURS dans tmp_path (seam db_path ou TBOT_LEDGER_DB) — jamais
C:\\db. Le fuseau local est injecté (UTC+1 fixe) pour un banc déterministe
quel que soit le poste.

    pytest tests/test_ledger.py -q
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from core.ledger import (  # noqa: E402
    Ledger, SCHEMA_VERSION,
    close_trade, open_trade, record_equity_snapshot, record_risk_event,
    record_trade,
)

SCHEMA_SQL = (pathlib.Path(APP_DIR) / "core" / "ledger" / "schema.sql"
              ).read_text(encoding="utf-8")

# Fuseau local INJECTÉ (UTC+1 fixe, sans DST) : le banc est déterministe
# sur n'importe quelle machine, y compris un runner CI en UTC.
TZ_PLUS1 = timezone(timedelta(hours=1))

_SEAMS = ("TBOT_LEDGER_DB", "TBOT_DB_DIR")


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    for k in _SEAMS:
        monkeypatch.delenv(k, raising=False)
    lg = Ledger(tmp_path / "ledger.db", local_tz=TZ_PLUS1)
    yield lg
    lg.close()


def _trade(ledger, *, close_utc, net=None, gross=100.0, commission=2.0,
           swap=1.0, strategy_id="S013", instance_id="S013.GLD-H1",
           mode="BACKTEST", currency="CHF", exit_reason="TP"):
    """Insère un trade CLOS (chemin bulk LG-6) ; net dérivé sauf si fourni."""
    if net is not None:
        gross, commission, swap = net, 0.0, 0.0
    open_utc = (datetime.fromisoformat(close_utc.replace("Z", "+00:00"))
                - timedelta(hours=1))
    return ledger.record_trade(
        strategy_id=strategy_id, instance_id=instance_id,
        strategy_version="1.0.0", magic_number=130013, mode=mode,
        symbol="XAUUSD", timeframe="H1", side="LONG", volume_lots=0.1,
        open_time=open_utc, open_price=2400.0, stop_price=2390.0,
        currency=currency, close_time=close_utc, close_price=2410.0,
        exit_reason=exit_reason, gross_pnl=gross, commission=commission,
        swap=swap)


# == LG-T1 : DB NEUVE — user_version 0→2, colonnes, idempotence ===============
def test_db_neuve_migre_0_vers_2_et_reouverture_idempotente(tmp_path):
    db = tmp_path / "neuve.db"
    with Ledger(db) as lg:
        assert lg.user_version == SCHEMA_VERSION == 2
        conn = sqlite3.connect(db)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            assert {"trades", "strategy_state", "risk_events",
                    "equity_snapshots", "backtest_runs"} <= tables
            vues = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view'")}
            assert {"v_tax_detail", "v_tax_summary"} <= vues
            for table in ("trades", "equity_snapshots"):
                cols = {r[1] for r in conn.execute(
                    f"PRAGMA table_info({table})")}
                assert "instance_id" in cols, table
            index = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")}
            assert {"idx_trades_instance", "idx_equity_instance"} <= index
        finally:
            conn.close()
    # Réouverture : rien ne bouge, rien ne casse.
    with Ledger(db) as lg2:
        assert lg2.user_version == 2


def test_wal_et_pragmas_actifs(ledger):
    assert ledger._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert ledger._conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert ledger._conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


# == LG-T2 : DB « v1 » PRÉEXISTANTE — migration v2 sans perte =================
def test_db_v1_preexistante_migre_sans_perte(tmp_path):
    """Une DB créée à la main depuis schema.sql (user_version 0, sans
    instance_id) doit monter en v2 en gardant ses lignes."""
    db = tmp_path / "heritee.db"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        """INSERT INTO trades (strategy_id, strategy_version, magic_number,
               mode, symbol, timeframe, side, volume_lots, open_time,
               open_price, stop_price, close_time, close_price, exit_reason,
               gross_pnl, commission, swap, net_pnl)
           VALUES ('s02_creamer_auction','0.9',130002,'PAPER','#US500','M15',
                   'LONG',1.0,'2026-08-01T10:00:00Z',5000.0,4990.0,
                   '2026-08-01T12:00:00Z',5010.0,'TP',50.0,1.5,0.5,48.0)""")
    conn.commit()
    conn.close()

    with Ledger(db, local_tz=TZ_PLUS1) as lg:
        assert lg.user_version == 2
        rows = lg.closed_trades()
        assert len(rows) == 1
        assert rows[0]["strategy_id"] == "s02_creamer_auction"
        assert rows[0]["net_pnl"] == 48.0
        assert rows[0]["instance_id"] is None      # colonne ajoutée, pas devinée


# == LG-T3 : open/close — net, stop, double close, mode =======================
def test_open_close_decompose_net(ledger):
    tid = ledger.open_trade(
        strategy_id="S013", instance_id="S013.GLD-H1",
        strategy_version="1.0.0", magic_number=130013, mode="PAPER",
        symbol="XAUUSD", timeframe="H1", side="LONG", volume_lots=0.1,
        open_time="2026-08-20T09:00:00Z", open_price=2400.0,
        stop_price=2390.0, meta={"setup": "breakout"})
    assert isinstance(tid, int)
    # Encore ouverte : absente des trades clos.
    assert ledger.closed_trades() == []
    ledger.close_trade(tid, close_time="2026-08-20T15:00:00Z",
                       close_price=2412.0, exit_reason="TP",
                       gross_pnl=120.0, commission=2.5, swap=1.5)
    (row,) = ledger.closed_trades()
    assert row["gross_pnl"] == 120.0
    assert row["commission"] == 2.5
    assert row["swap"] == 1.5
    assert row["net_pnl"] == pytest.approx(120.0 - 2.5 - 1.5)
    assert row["close_time"] == "2026-08-20T15:00:00Z"


def test_stop_obligatoire_et_non_nul(ledger):
    base = dict(strategy_id="S013", instance_id="S013.GLD-H1",
                strategy_version="1.0.0", magic_number=130013, mode="PAPER",
                symbol="XAUUSD", timeframe="H1", side="LONG",
                volume_lots=0.1, open_time="2026-08-20T09:00:00Z",
                open_price=2400.0)
    with pytest.raises(ValueError, match="stop"):
        ledger.open_trade(stop_price=None, **base)
    with pytest.raises(ValueError, match="stop"):
        ledger.open_trade(stop_price=0.0, **base)


def test_double_close_refuse(ledger):
    tid = ledger.open_trade(
        strategy_id="S013", instance_id="S013.GLD-H1",
        strategy_version="1.0.0", magic_number=130013, mode="PAPER",
        symbol="XAUUSD", timeframe="H1", side="SHORT", volume_lots=0.1,
        open_time="2026-08-20T09:00:00Z", open_price=2400.0,
        stop_price=2410.0)
    fermeture = dict(close_time="2026-08-20T10:00:00Z", close_price=2395.0,
                     exit_reason="SL", gross_pnl=-50.0)
    ledger.close_trade(tid, **fermeture)
    with pytest.raises(ValueError, match="already closed"):
        ledger.close_trade(tid, **fermeture)
    with pytest.raises(ValueError, match="unknown"):
        ledger.close_trade(99999, **fermeture)


def test_vocabulaires_valides_sans_defaut_silencieux(ledger):
    base = dict(strategy_id="S013", instance_id="S013.GLD-H1",
                strategy_version="1.0.0", magic_number=130013,
                symbol="XAUUSD", timeframe="H1", volume_lots=0.1,
                open_time="2026-08-20T09:00:00Z", open_price=2400.0,
                stop_price=2390.0)
    with pytest.raises(ValueError, match="mode"):
        ledger.open_trade(mode="live", side="LONG", **base)   # casse stricte
    with pytest.raises(ValueError, match="side"):
        ledger.open_trade(mode="LIVE", side="BUY", **base)
    tid = ledger.open_trade(mode="LIVE", side="LONG", **base)
    with pytest.raises(ValueError, match="exit_reason"):
        ledger.close_trade(tid, close_time="2026-08-20T10:00:00Z",
                           close_price=2405.0, exit_reason="STOPPED",
                           gross_pnl=5.0)
    with pytest.raises(ValueError, match="mode"):
        ledger.record_equity_snapshot(strategy_id="S013",
                                      instance_id="S013.GLD-H1",
                                      mode="SIMU", equity=10_000.0)
    with pytest.raises(ValueError, match="event_type"):
        ledger.record_risk_event(event_type="PANIC", trigger="test")
    with pytest.raises(ValueError, match="open_time"):
        ledger.open_trade(mode="LIVE", side="LONG",
                          **{**base, "open_time": "pas-une-date"})


# == LG-T4 : AGRÉGATS — calendrier local, semaine ISO, mois vide ==============
def _jeu_bords(ledger):
    """Jeu synthétique (fuseau local = UTC+1) :

    - 2026-01-15T23:30Z  → local 2026-01-16 00:30  (bascule de minuit)
    - 2026-01-15T22:30Z  → local 2026-01-15 23:30  (même jour)
    - 2025-12-28T10:00Z  → local dimanche 28.12    → semaine ISO 2025-W52
    - 2025-12-29T10:00Z  → local lundi 29.12       → semaine ISO 2026-W01
      (semaine à cheval : jour de 2025, semaine ISO de 2026)
    - mars 2026          → un trade ; FÉVRIER RESTE VIDE
    """
    _trade(ledger, close_utc="2026-01-15T23:30:00Z", net=10.0)
    _trade(ledger, close_utc="2026-01-15T22:30:00Z", net=20.0)
    _trade(ledger, close_utc="2025-12-28T10:00:00Z", net=5.0)
    _trade(ledger, close_utc="2025-12-29T10:00:00Z", net=7.0)
    _trade(ledger, close_utc="2026-03-10T12:00:00Z", net=30.0)


def test_pnl_by_day_bascule_minuit_locale(ledger):
    _jeu_bords(ledger)
    jours = {r["day"]: r for r in ledger.pnl_by_day("2026-01-01",
                                                    "2026-01-31")}
    # 23:30 UTC compte le LENDEMAIN local (00:30 UTC+1) — pas le 15.
    assert jours["2026-01-15"]["net"] == 20.0
    assert jours["2026-01-16"]["net"] == 10.0
    assert jours["2026-01-15"]["n_trades"] == 1
    assert jours["2026-01-16"]["n_trades"] == 1


def test_pnl_by_week_iso_a_cheval_sur_deux_annees(ledger):
    _jeu_bords(ledger)
    semaines = {r["week"]: r for r in ledger.pnl_by_week()}
    # Dimanche 28.12.2025 → 2025-W52 ; lundi 29.12.2025 → 2026-W01 (ISO).
    assert semaines["2025-W52"]["net"] == 5.0
    assert semaines["2026-W01"]["net"] == 7.0


def test_pnl_by_month_mois_vide_absent(ledger):
    _jeu_bords(ledger)
    mois = {r["month"]: r for r in ledger.pnl_by_month("2026-01-01",
                                                       "2026-03-31")}
    assert set(mois) == {"2026-01", "2026-03"}    # février vide = pas de ligne
    assert mois["2026-01"]["net"] == 30.0          # 10 + 20
    assert mois["2026-03"]["net"] == 30.0


def test_pnl_by_year_et_decomposition(ledger):
    _trade(ledger, close_utc="2026-05-05T10:00:00Z",
           gross=100.0, commission=2.0, swap=1.0)
    _trade(ledger, close_utc="2026-06-05T10:00:00Z",
           gross=50.0, commission=1.0, swap=0.5)
    (annee,) = ledger.pnl_by_year()
    assert annee["year"] == "2026"
    assert annee["n_trades"] == 2
    assert annee["gross"] == 150.0
    assert annee["commission"] == 3.0
    assert annee["swap"] == 1.5
    assert annee["net"] == pytest.approx(145.5)


def test_agregats_filtres_par_strategie_et_instance(ledger):
    """Multi-instances d'une même stratégie : la vue stratégie agrège tout,
    la vue instance sépare."""
    _trade(ledger, close_utc="2026-04-01T10:00:00Z", net=10.0,
           strategy_id="S013", instance_id="S013.GLD-H1")
    _trade(ledger, close_utc="2026-04-01T11:00:00Z", net=20.0,
           strategy_id="S013", instance_id="S013.SPX-M15")
    _trade(ledger, close_utc="2026-04-01T12:00:00Z", net=40.0,
           strategy_id="S007", instance_id="S007.EUR-H4")

    (s013,) = ledger.pnl_by_day(strategy_id="S013")
    assert s013["net"] == 30.0 and s013["n_trades"] == 2
    (gld,) = ledger.pnl_by_day(instance_id="S013.GLD-H1")
    assert gld["net"] == 10.0
    (tout,) = ledger.pnl_by_day()
    assert tout["net"] == 70.0


def test_agregats_par_mode(ledger):
    _trade(ledger, close_utc="2026-04-02T10:00:00Z", net=11.0, mode="PAPER")
    _trade(ledger, close_utc="2026-04-02T11:00:00Z", net=22.0, mode="LIVE")
    (paper,) = ledger.pnl_by_day(mode="PAPER")
    assert paper["net"] == 11.0
    (live,) = ledger.pnl_by_day(mode="LIVE")
    assert live["net"] == 22.0


# == LG-14 : DEVISES — jamais d'addition inter-devises silencieuse ============
def test_multi_devises_lignes_separees(ledger):
    _trade(ledger, close_utc="2026-04-03T10:00:00Z", net=10.0,
           currency="CHF")
    _trade(ledger, close_utc="2026-04-03T11:00:00Z", net=99.0,
           currency="USD", instance_id="S013.SPX-M15")
    lignes = ledger.pnl_by_day()
    assert len(lignes) == 2                        # une ligne PAR devise
    par_devise = {r["currency"]: r["net"] for r in lignes}
    assert par_devise == {"CHF": 10.0, "USD": 99.0}
    # Une seule devise : une seule ligne, devise annoncée.
    (chf,) = ledger.pnl_by_day(instance_id="S013.GLD-H1",
                               date_from="2026-04-03", date_to="2026-04-03")
    assert chf["currency"] == "CHF"


# == LG-T5 : day_trades — format Telegram =====================================
def test_day_trades_ordre_et_champs_telegram(ledger):
    _trade(ledger, close_utc="2026-01-15T14:00:00Z", net=-5.0,
           instance_id="S013.SPX-M15", exit_reason="SL")
    _trade(ledger, close_utc="2026-01-15T08:00:00Z", net=12.0,
           instance_id="S013.GLD-H1", exit_reason="TP")
    _trade(ledger, close_utc="2026-01-15T23:30:00Z", net=99.0)  # lendemain local
    lignes = ledger.day_trades("2026-01-15")
    assert lignes == [
        {"close_time_local": "09:00", "instance_id": "S013.GLD-H1",
         "exit_reason": "TP", "net_pnl": 12.0},
        {"close_time_local": "15:00", "instance_id": "S013.SPX-M15",
         "exit_reason": "SL", "net_pnl": -5.0},
    ]
    # Le trade de 23:30 UTC appartient au jour local SUIVANT.
    (lendemain,) = ledger.day_trades("2026-01-16")
    assert lendemain["close_time_local"] == "00:30"
    assert lendemain["net_pnl"] == 99.0


# == LG-T6 : VUES FISCALES — héritées, non réécrites, cohérentes ==============
def test_vues_fiscales_coherentes(ledger):
    _trade(ledger, close_utc="2026-02-10T10:00:00Z",
           gross=100.0, commission=2.0, swap=1.0)               # net +97
    _trade(ledger, close_utc="2026-02-11T10:00:00Z",
           gross=-40.0, commission=1.0, swap=0.0)               # net -41
    _trade(ledger, close_utc="2025-11-01T10:00:00Z", net=10.0)  # autre année

    detail = ledger.tax_detail(2026)
    assert len(detail) == 2
    assert all(d["tax_year"] == "2026" for d in detail)

    (resume,) = ledger.tax_summary(2026)
    assert resume["n_trades"] == 2
    assert resume["n_wins"] == 1
    assert resume["n_losses"] == 1
    assert resume["gains"] == 97.0
    assert resume["losses"] == -41.0
    assert resume["total_commission"] == 3.0
    assert resume["total_swap"] == 1.0
    assert resume["net_result"] == pytest.approx(56.0)
    assert ledger.tax_summary(2024) == []


# == LG-7/LG-12 : equity — snapshot et courbe ================================
def test_equity_snapshot_et_courbe(ledger):
    for i, ts in enumerate(["2026-08-20T10:00:00Z", "2026-08-20T11:00:00Z",
                            "2026-08-20T12:00:00Z"]):
        ledger.record_equity_snapshot(
            strategy_id="S013", instance_id="S013.GLD-H1", mode="PAPER",
            equity=10_000.0 + i * 100, timestamp=ts)
    ledger.record_equity_snapshot(
        strategy_id="S013", instance_id="S013.SPX-M15", mode="PAPER",
        equity=5_000.0, timestamp="2026-08-20T10:30:00Z")

    courbe = ledger.equity_curve(strategy_id="S013",
                                 instance_id="S013.GLD-H1", mode="PAPER")
    assert courbe == [("2026-08-20T10:00:00Z", 10_000.0),
                      ("2026-08-20T11:00:00Z", 10_100.0),
                      ("2026-08-20T12:00:00Z", 10_200.0)]
    # limit garde les N plus RÉCENTS, restitués en ordre chronologique.
    assert ledger.equity_curve(strategy_id="S013",
                               instance_id="S013.GLD-H1",
                               limit=2) == courbe[-2:]
    # Sans filtre instance : les deux instances de S013.
    assert len(ledger.equity_curve(strategy_id="S013")) == 4


def test_equity_snapshot_timestamp_defaut_utc_z(ledger):
    avant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger.record_equity_snapshot(strategy_id="S013",
                                  instance_id="S013.GLD-H1",
                                  mode="BACKTEST", equity=1_000.0)
    ((ts, _),) = ledger.equity_curve(strategy_id="S013")
    assert ts.endswith("Z") and ts >= avant


# == LG-8 : risk_events ======================================================
def test_record_risk_event(ledger):
    ledger.record_risk_event(event_type="HALT", trigger="3 pertes de suite",
                             strategy_id="S013", value_before=1.0,
                             value_after=0.0, detail={"losses": 3})
    (row,) = ledger._conn.execute("SELECT * FROM risk_events").fetchall()
    assert row["event_type"] == "HALT"
    assert row["strategy_id"] == "S013"
    assert '"losses": 3' in row["detail_json"]
    assert row["timestamp"].endswith("Z")
    # Événement global : strategy_id NULL accepté.
    ledger.record_risk_event(event_type="KILL_SWITCH", trigger="panneau")


# == LG-10 : closed_trades — filtres et bornes ================================
def test_closed_trades_filtres_dates_locales_et_limit(ledger):
    _trade(ledger, close_utc="2026-01-15T23:30:00Z", net=1.0)  # local 16.01
    _trade(ledger, close_utc="2026-01-16T10:00:00Z", net=2.0)  # local 16.01
    _trade(ledger, close_utc="2026-01-17T10:00:00Z", net=3.0)  # local 17.01
    rows = ledger.closed_trades(date_from="2026-01-16", date_to="2026-01-16")
    assert [r["net_pnl"] for r in rows] == [1.0, 2.0]
    rows = ledger.closed_trades(date_from=date(2026, 1, 17))
    assert [r["net_pnl"] for r in rows] == [3.0]
    assert len(ledger.closed_trades(limit=2)) == 2
    with pytest.raises(ValueError, match="mode"):
        ledger.closed_trades(mode="INVALIDE")


# == LG-1 : RÉSOLUTION DU CHEMIN — seams, jamais C:\\db en test ===============
def test_seam_tbot_ledger_db_prime(tmp_path, monkeypatch):
    cible = tmp_path / "seam" / "explicite.db"
    monkeypatch.setenv("TBOT_LEDGER_DB", str(cible))
    monkeypatch.setenv("TBOT_DB_DIR", str(tmp_path / "db_dir"))
    with Ledger() as lg:
        assert lg.db_path == cible
        assert cible.exists()                      # parent créé, DB ouverte


def test_fallback_db_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("TBOT_LEDGER_DB", raising=False)
    monkeypatch.setenv("TBOT_DB_DIR", str(tmp_path / "etat"))
    with Ledger() as lg:
        assert lg.db_path == tmp_path / "etat" / "tradingbot.db"


# == D-LG-5 : FONCTIONS MODULE DE COMMODITÉ ==================================
def test_fonctions_module_one_shot(tmp_path, monkeypatch):
    db = tmp_path / "module.db"
    monkeypatch.setenv("TBOT_LEDGER_DB", str(db))
    tid = open_trade(
        strategy_id="S013", instance_id="S013.GLD-H1",
        strategy_version="1.0.0", magic_number=130013, mode="PAPER",
        symbol="XAUUSD", timeframe="H1", side="LONG", volume_lots=0.1,
        open_time="2026-08-20T09:00:00Z", open_price=2400.0,
        stop_price=2390.0)
    close_trade(tid, close_time="2026-08-20T10:00:00Z", close_price=2405.0,
                exit_reason="MANUAL", gross_pnl=50.0, commission=1.0)
    tid2 = record_trade(
        db_path=db, strategy_id="S013", instance_id="S013.SPX-M15",
        strategy_version="1.0.0", magic_number=130013, mode="BACKTEST",
        symbol="#US500", timeframe="M15", side="SHORT", volume_lots=1.0,
        open_time="2026-08-19T09:00:00Z", open_price=5000.0,
        stop_price=5010.0, close_time="2026-08-19T11:00:00Z",
        close_price=4990.0, exit_reason="TP", gross_pnl=100.0)
    record_equity_snapshot(strategy_id="S013", instance_id="S013.GLD-H1",
                           mode="PAPER", equity=10_049.0)
    record_risk_event(event_type="COOLDOWN", trigger="test module")
    with Ledger(db, local_tz=TZ_PLUS1) as lg:
        assert {r["id"] for r in lg.closed_trades()} == {tid, tid2}
        assert (r := lg.closed_trades(instance_id="S013.GLD-H1"))[0][
            "net_pnl"] == 49.0 and len(r) == 1
        assert len(lg.equity_curve(strategy_id="S013")) == 1
