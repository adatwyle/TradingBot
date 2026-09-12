"""
Tests du moteur d'analyse des trades — server/analytics.py (SPEC_analytics-trades).

POURQUOI ce banc : la page « analyse » rejoue n'importe quel sous-ensemble de
trades clos en KPI, courbe, heatmap, répartitions et synthèse — chaque formule
est figée ici sur le jeu J5 de la spec (§8, valeur par valeur), puis sur des
jeux synthétiques pour les cas limites : N = 0 sans division par zéro, base
zéro sans %, dates de filtre en calendrier LOCAL, union ledger ∪ journaux
dédoublonnée, ledger absent sans création de DB, drawdown partagé entre KPI et
courbe (D-AN-9), Sharpe sur le R annualisé, groupe « magic divergent ».

Aucune fixture conftest : tout est en mémoire (fixtures _analytics_fixtures),
les rares tests disque montent leur propre tmp_path via monkeypatch.

    pytest app/tests/test_server_analytics.py -q
"""
from __future__ import annotations

import math
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import analytics as an  # noqa: E402
from _analytics_fixtures import (  # noqa: E402
    J5_BASE, FakeSources, j5_raw, j5_rows, journal_row, make_row,
    synthetic_rows,
)

TZ2 = timezone(timedelta(hours=2))


# ── §3.1 — normalisation ────────────────────────────────────────────────────
def test_normalize_rows_meta_tolerant_pnl_r_arm_source_ref():
    raw = [
        # meta invalide -> {}, pnl_r dérivé net / risk_amount, ticket -> ref
        dict(make_row(net=25.0, risk=50.0, ticket=77, rid=1,
                      close="2026-08-03T10:00:00Z"), meta_json="{pas du json"),
        # meta porte pnl_r et arm ; pas de ticket -> id
        make_row(net=-10.0, pnl_r=-0.25, arm="OBSERVATION", rid=3, risk=None,
                 close="2026-08-02T10:00:00Z"),
        # risk_amount 0 et pas de meta -> pnl_r None ; source_ref déjà porté
        make_row(net=5.0, risk=0.0, rid=9, source_ref="T-9",
                 close="2026-08-04T10:00:00Z"),
    ]
    rows = an.normalize_rows(raw, "ledger")
    assert [r["id"] for r in rows] == [3, 1, 9]           # tri close_time
    by_id = {r["id"]: r for r in rows}
    assert by_id[1]["meta_json"] == {} and by_id[1]["pnl_r"] == 0.5
    assert by_id[1]["source_ref"] == "77" and by_id[1]["arm"] is None
    assert by_id[3]["pnl_r"] == -0.25 and by_id[3]["arm"] == "OBSERVATION"
    assert by_id[3]["source_ref"] == "3"
    assert by_id[9]["pnl_r"] is None and by_id[9]["source_ref"] == "T-9"
    assert all(r["source"] == "ledger" for r in rows)
    assert set(an.ROW_KEYS) <= set(rows[0])


def test_normalize_rows_drops_invalid_close_time_with_warning():
    raw = [make_row(net=1.0, close="2026-08-03T10:00:00Z", rid=1),
           dict(make_row(net=2.0, close="2026-08-03T10:00:00Z", rid=2),
                close_time="pas une date")]
    warnings: list[str] = []
    rows = an.normalize_rows(raw, "journal", warnings)
    assert [r["id"] for r in rows] == [1]
    assert warnings and "close_time invalide" in warnings[0]


# ── AN-T5 — KPI ─────────────────────────────────────────────────────────────
def test_kpi_j5_reference_values():
    k = an.kpi(j5_rows(), J5_BASE)
    assert (k["total_trades"], k["wins"], k["losses"], k["zeros"]) == (5, 2, 2, 1)
    assert (k["long"], k["short"]) == (3, 2)
    assert k["win_rate"] == 0.4
    assert k["net_pnl"] == 60.0 and k["avg_per_trade"] == 12.0
    assert k["gross_profit"] == 130.0 and k["gross_loss"] == -70.0
    assert k["profit_factor"] == pytest.approx(1.857, abs=0.01)
    assert k["avg_win"] == 65.0 and k["avg_loss"] == -35.0
    assert k["expectancy"] == 12.0                       # pas 5 (Trade Buddy)
    assert k["max_drawdown"] == 50.0
    assert k["max_dd_pct"] == pytest.approx(0.0455, abs=1e-4)
    assert k["recovery_factor"] == 1.2
    assert k["current_drawdown"] == 40.0
    assert k["recovered_pct"] == pytest.approx(0.20)
    assert k["sum_r"] == 1.2 and k["avg_r"] == 0.24
    assert k["recovery_days"] is None and k["dd_duration_days"] == 1.0


def test_kpi_empty_never_divides_by_zero():
    k = an.kpi([], 1000.0)
    assert k["total_trades"] == 0 and k["win_rate"] == 0.0
    assert k["net_pnl"] == 0.0 and k["expectancy"] == 0.0
    for key in ("profit_factor", "avg_win", "avg_loss", "avg_r",
                "recovery_factor", "recovered_pct", "max_dd_pct"):
        assert k[key] is None, key
    assert k["max_drawdown"] == 0.0 and k["current_drawdown"] == 0.0


def test_kpi_without_losses_profit_factor_null():
    rows = an.normalize_rows([make_row(net=10.0, close="2026-08-03T10:00:00Z"),
                              make_row(net=0.0, close="2026-08-04T10:00:00Z")],
                             "ledger")
    k = an.kpi(rows)
    assert k["profit_factor"] is None and k["avg_loss"] is None
    assert k["wins"] == 1 and k["zeros"] == 1 and k["win_rate"] == 0.5


# ── AN-T6 — courbe et heatmap ───────────────────────────────────────────────
def test_curve_j5_reference_series():
    c = an.curve(j5_rows(), J5_BASE)
    assert c["base"] == 1000.0 and c["base_kind"] == "capital"
    assert c["decimated"] is False
    assert [p[1] for p in c["points"]] == [1100.0, 1050.0, 1050.0, 1080.0, 1060.0]
    assert [p[2] for p in c["points"]] == [0.0, -50.0, -50.0, -20.0, -40.0]
    assert c["points"][1][3] == pytest.approx(-0.0455, abs=1e-4)
    assert c["points"][0][0] == "2026-08-03T10:00:00Z"


def test_curve_base_zero_has_null_pct():
    c = an.curve(j5_rows(), None)
    assert c["base"] == 0.0 and c["base_kind"] == "zero"
    assert [p[1] for p in c["points"]] == [100.0, 50.0, 50.0, 80.0, 60.0]
    assert all(p[3] is None for p in c["points"])
    assert an.kpi(j5_rows(), None)["max_dd_pct"] is None


def test_curve_decimated_last_balance_of_day_over_2000_points():
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    raws = [make_row(net=1.0, rid=i, close=t0 + timedelta(hours=i))
            for i in range(2400)]                       # 100 jours × 24
    rows = an.normalize_rows(raws, "ledger")
    c = an.curve(rows, 1000.0, local_tz=timezone.utc)
    assert c["decimated"] is True and len(c["points"]) == 100
    assert c["points"][-1][1] == 1000.0 + 2400        # dernier solde global
    assert c["points"][0][1] == 1000.0 + 24           # dernier solde du jour 1


def test_curve_decimated_keeps_intraday_trough_so_kpi_max_dd_survives():
    """Relecture tour 1 : la décimation « dernier solde du jour » effaçait
    le creux intra-journalier (max DD du KPI absent de la courbe, D-AN-9).
    2 001 trades (3 par jour) avec un creux de −500 récupéré le même jour :
    la courbe décimée porte min(dd) = −max_drawdown et son dernier point
    le drawdown courant."""
    t0 = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    raws = []
    for i in range(2001):
        day, slot = divmod(i, 3)
        net = 1.0
        if day == 100:                 # creux −500 le matin, effacé à midi
            net = (-500.0, 500.0, 1.0)[slot]
        raws.append(make_row(net=net, rid=i + 1,
                             close=t0 + timedelta(days=day, hours=4 * slot)))
    rows = an.normalize_rows(raws, "ledger")
    c = an.curve(rows, 10000.0, local_tz=timezone.utc)
    k = an.kpi(rows, 10000.0)
    assert c["decimated"] is True
    assert 2000 // 3 < len(c["points"]) <= 2 * 667
    assert k["max_drawdown"] == 500.0
    assert min(p[2] for p in c["points"]) == -k["max_drawdown"]
    assert c["points"][-1][2] == -k["current_drawdown"]
    assert c["points"][-1][1] == 10000.0 + 2001 - 500 + 500 - 2  # solde final
    # Les points restent des points RÉELS de la série, dans l'ordre du temps.
    assert [p[0] for p in c["points"]] == sorted(p[0] for p in c["points"])
    trough = [p for p in c["points"] if p[2] == -500.0]
    assert len(trough) == 1 and trough[0][3] == pytest.approx(-500 / 10300, abs=1e-4)


def test_decimate_by_day_emits_trough_then_last_only_when_distinct():
    def mk(t, bal, dd):
        return {"t": t, "balance": bal, "peak": bal - dd, "dd": dd, "dd_pct": None}
    series = [mk("2026-01-01T08:00:00Z", 100.0, 0.0),
              mk("2026-01-01T10:00:00Z", 40.0, -60.0),
              mk("2026-01-01T12:00:00Z", 90.0, -10.0),
              mk("2026-01-02T08:00:00Z", 95.0, -5.0),
              mk("2026-01-02T10:00:00Z", 120.0, 0.0)]
    out = an._decimate_by_day(series, timezone.utc)
    assert [(p["t"], p["dd"]) for p in out] == [
        ("2026-01-01T10:00:00Z", -60.0), ("2026-01-01T12:00:00Z", -10.0),
        ("2026-01-02T08:00:00Z", -5.0), ("2026-01-02T10:00:00Z", 0.0)]
    # Égalité de dd : le dernier point l'emporte (un seul point émis).
    flat = [mk("2026-01-03T08:00:00Z", 1.0, 0.0), mk("2026-01-03T09:00:00Z", 2.0, 0.0)]
    assert an._decimate_by_day(flat, timezone.utc) == [flat[1]]
    assert an._decimate_by_day([], timezone.utc) == []


def test_heatmap_totals_and_pct():
    h = an.heatmap(j5_rows(), J5_BASE)
    assert h["years"] == [2026]
    assert h["total"] == {"net": 60.0, "n_trades": 5, "sum_r": 1.2, "pct": 0.06}
    assert h["cells"]["2026-08"]["net"] == 60.0
    assert h["year_totals"]["2026"]["net"] == 60.0
    assert h["month_totals"]["08"]["n_trades"] == 5
    assert h["total"]["net"] == an.kpi(j5_rows())["net_pnl"]


def test_heatmap_month_column_sums_over_years_and_base_zero():
    raws = [make_row(net=10.0, close="2025-03-10T10:00:00Z", pnl_r=0.1),
            make_row(net=20.0, close="2026-03-12T10:00:00Z", pnl_r=0.2),
            make_row(net=-5.0, close="2026-07-01T10:00:00Z", pnl_r=-0.05)]
    rows = an.normalize_rows(raws, "ledger")
    h = an.heatmap(rows, 1000.0)
    assert h["years"] == [2025, 2026]
    assert h["month_totals"]["03"] == {"net": 30.0, "n_trades": 2, "sum_r": 0.3,
                                       "pct": 0.03}
    assert h["year_totals"]["2026"]["net"] == 15.0
    assert h["total"]["net"] == 25.0
    h0 = an.heatmap(rows, None)
    assert h0["total"]["pct"] is None
    assert all(c["pct"] is None for c in h0["cells"].values())


def test_by_month_fills_empty_months():
    raws = [make_row(net=10.0, close="2026-01-10T10:00:00Z"),
            make_row(net=-4.0, close="2026-04-10T10:00:00Z")]
    m = an.by_month(an.normalize_rows(raws, "ledger"), 1000.0)
    assert [x["month"] for x in m] == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert m[1] == {"month": "2026-02", "net": 0.0, "n_trades": 0, "sum_r": 0.0,
                    "pct": 0.0}
    assert m[3]["net"] == -4.0 and m[3]["pct"] == -0.004
    assert an.by_month([], 1000.0) == []


# ── AN-T7 — filtres ─────────────────────────────────────────────────────────
def test_parse_filters_defaults_and_repeated_keys():
    f = an.parse_filters({})
    assert f.mode == "PAPER" and f.source == "auto" and f.curve_base == "auto"
    assert f.weekday_key == "open" and f.dist_unit == "r"
    assert f.applied()["from"] is None and f.applied()["strategy"] == []
    f = an.parse_filters({"strategy": ["S011", "S013"], "mode": "LIVE",
                          "magic": ["130011", "130013"], "from": "2026-08-01",
                          "to": "2026-08-31", "arm": "none", "symbol": "",
                          "weekday": ["mon", "fri"]})
    assert f.strategy == ["S011", "S013"] and f.mode == "LIVE"
    assert f.magic == [130011, 130013] and f.symbol == []
    assert (f.date_from, f.date_to) == ("2026-08-01", "2026-08-31")
    assert f.arm == ["none"] and f.weekday == ["mon", "fri"]


@pytest.mark.parametrize("args, name", [
    ({"mode": "DEMO"}, "mode=DEMO"),
    ({"mode": ["PAPER", "LIVE"]}, "mode=PAPER,LIVE"),
    ({"strategy": "gold"}, "strategy=gold"),
    ({"instance": "XAUUSD"}, "instance=XAUUSD"),
    ({"symbol": "XAU USD"}, "symbol=XAU USD"),
    ({"side": "BUY"}, "side=BUY"),
    ({"weekday": "monday"}, "weekday=monday"),
    ({"exit_reason": "STOP"}, "exit_reason=STOP"),
    ({"arm": "PRIMAIRE"}, "arm=PRIMAIRE"),
    ({"magic": "abc"}, "magic=abc"),
    ({"from": "01.08.2026"}, "from=01.08.2026"),
    ({"from": "2026-08-31", "to": "2026-08-01"}, "to=2026-08-01"),
    ({"source": "csv"}, "source=csv"),
    ({"curve_base": "fixed"}, "curve_base=fixed"),
    ({"weekday_key": "entry"}, "weekday_key=entry"),
    ({"dist_unit": "pips"}, "dist_unit=pips"),
])
def test_parse_filters_out_of_domain_raises(args, name):
    with pytest.raises(ValueError) as e:
        an.parse_filters(args)
    assert str(e.value) == f"paramètre invalide : {name}"


def _mixed_rows():
    raws = [
        make_row(net=10.0, rid=1, side="LONG", exit_reason="TP",
                 close="2026-08-03T10:00:00Z"),
        make_row(net=-5.0, rid=2, side="SHORT", exit_reason="SL",
                 close="2026-08-04T10:00:00Z"),
        make_row(net=7.0, rid=3, side="LONG", exit_reason="SL", strategy="S013",
                 instance="S013.EUR-JPY", symbol="EURJPY", magic=130013,
                 close="2026-08-05T10:00:00Z", arm="OBSERVATION"),
    ]
    return an.normalize_rows(raws, "ledger")


def test_filter_and_between_params_or_within():
    rows = _mixed_rows()
    f = an.parse_filters({"exit_reason": ["TP", "SL"]})          # OR intra
    assert [r["id"] for r in an.filter_rows(rows, f)] == [1, 2, 3]
    f = an.parse_filters({"exit_reason": "SL", "side": "LONG"})   # AND inter
    assert [r["id"] for r in an.filter_rows(rows, f)] == [3]
    f = an.parse_filters({"magic": "130013"})
    assert [r["id"] for r in an.filter_rows(rows, f)] == [3]
    f = an.parse_filters({"arm": "none"})
    assert [r["id"] for r in an.filter_rows(rows, f)] == [1, 2]
    f = an.parse_filters({"arm": ["OBSERVATION"], "instance": "S013.EUR-JPY"})
    assert [r["id"] for r in an.filter_rows(rows, f)] == [3]


def test_filter_from_to_inclusive_on_local_date():
    rows = an.normalize_rows([make_row(net=1.0, rid=1,
                                       close="2026-08-03T23:30:00Z")], "ledger")
    f = an.parse_filters({"from": "2026-08-04", "to": "2026-08-04"})
    assert len(an.filter_rows(rows, f, local_tz=TZ2)) == 1      # 4 août local
    assert an.filter_rows(rows, f, local_tz=timezone.utc) == []  # 3 août UTC
    f = an.parse_filters({"to": "2026-08-03"})
    assert an.filter_rows(rows, f, local_tz=TZ2) == []
    assert len(an.filter_rows(rows, f, local_tz=timezone.utc)) == 1


def test_weekday_key_open_vs_close_changes_bucket():
    # Ouvert lundi 3 août 08:00Z, clos mardi 4 août 10:00Z.
    rows = an.normalize_rows([make_row(net=1.0, open_time="2026-08-03T08:00:00Z",
                                       close="2026-08-04T10:00:00Z")], "ledger")
    assert an.weekday_of(rows[0], "open", timezone.utc) == "mon"
    assert an.weekday_of(rows[0], "close", timezone.utc) == "tue"
    f_open = an.parse_filters({"weekday": "tue"})
    f_close = an.parse_filters({"weekday": "tue", "weekday_key": "close"})
    assert an.filter_rows(rows, f_open, timezone.utc) == []
    assert len(an.filter_rows(rows, f_close, timezone.utc)) == 1
    wd = {e["weekday"]: e["n_trades"]
          for e in an.by_key(rows, "weekday", weekday_key="close",
                             local_tz=timezone.utc)}
    assert wd["tue"] == 1 and wd["mon"] == 0


# ── AN-T8 — options dépendantes ─────────────────────────────────────────────
def test_options_symbol_depends_on_strategy_but_strategy_lists_all():
    rows = _mixed_rows()
    manifests = {"S011": {"display_name": "Or", "retired": False, "magic": 130011},
                 "S013": {"display_name": "MACD", "retired": True, "magic": 130013}}
    opt = an.options(rows, an.parse_filters({"strategy": "S011"}),
                     manifests=manifests)
    assert opt["symbol"] == ["XAUUSD"]
    assert [s["id"] for s in opt["strategy"]] == ["S011", "S013"]
    assert opt["strategy"][1] == {"id": "S013", "display_name": "MACD",
                                  "retired": True}
    assert opt["instance"] == ["S011.XAU-USD"]
    assert opt["arm"] == ["none"] and opt["magic"] == [130011]


def test_options_follow_domain_order():
    rows = _mixed_rows()
    opt = an.options(rows, an.parse_filters({}), local_tz=timezone.utc)
    assert opt["side"] == ["LONG", "SHORT"]
    assert opt["exit_reason"] == ["SL", "TP"]           # ordre du domaine
    assert opt["weekday"] == ["mon", "tue", "wed"]
    assert opt["arm"] == ["OBSERVATION", "none"]
    assert opt["magic"] == [130011, 130013]
    assert opt["instance"] == ["S011.XAU-USD", "S013.EUR-JPY"]
    assert opt["strategy"][0]["display_name"] == "S011"    # repli sans manifest
    # Un filtre sur le paramètre lui-même ne réduit pas ses propres options.
    opt2 = an.options(rows, an.parse_filters({"side": "SHORT"}))
    assert opt2["side"] == ["LONG", "SHORT"] and opt2["exit_reason"] == ["SL"]


# ── AN-T9 — modes et devises ────────────────────────────────────────────────
def test_mode_is_exclusive_and_currencies_never_added():
    raws = [make_row(net=10.0, rid=1, close="2026-08-03T10:00:00Z"),
            make_row(net=100.0, rid=2, mode="BACKTEST", close="2026-08-03T11:00:00Z"),
            make_row(net=7.0, rid=3, currency="EUR", instance="S011.XAG-USD",
                     symbol="XAGUSD", close="2026-08-04T10:00:00Z")]
    out = an.build_analytics({"mode": "PAPER"}, sources=FakeSources(ledger=raws))
    assert sorted(out["by_currency"]) == ["CHF", "EUR"]
    assert out["by_currency"]["CHF"]["kpi"] == an.kpi(
        an.normalize_rows(raws[:1], "ledger"), None)
    assert out["by_currency"]["CHF"]["kpi"]["net_pnl"] == 10.0
    assert out["by_currency"]["EUR"]["kpi"]["net_pnl"] == 7.0
    assert out["header"]["n_trades"] == 2 and out["header"]["mode"] == "PAPER"
    bt = an.build_analytics({"mode": "BACKTEST"}, sources=FakeSources(ledger=raws))
    assert bt["header"]["n_trades"] == 1 and bt["by_currency"]["CHF"]["kpi"]["net_pnl"] == 100.0


# ── AN-T10 — sources ────────────────────────────────────────────────────────
def test_collect_rows_dedup_on_run_id_and_source_ref_ledger_wins():
    ledger = [make_row(net=10.0, ticket=None, rid=1, source_ref="SHORT_1",
                       close="2026-08-03T10:00:00Z"),
              make_row(net=3.0, ticket=42, rid=2, close="2026-08-04T10:00:00Z")]
    journals = [journal_row(trade_id="SHORT_1", net=-999.0,
                            close="2026-08-03T10:00:00Z"),
                journal_row(trade_id="42", net=-999.0, close="2026-08-04T10:00:00Z"),
                journal_row(trade_id="LONG_2", net=5.0, close="2026-08-05T10:00:00Z")]
    got = an.collect_rows(an.parse_filters({}),
                          sources=FakeSources(ledger=ledger, journals=journals))
    assert got["source"] == {"ledger_rows": 2, "journal_rows": 1, "dedup": 2,
                             "ledger_present": True, "studies": {}}
    assert [(r["source"], r["net_pnl"]) for r in got["rows"]] == [
        ("ledger", 10.0), ("ledger", 3.0), ("journal", 5.0)]
    assert got["warnings"] == []


def test_collect_rows_ledger_absent_serves_journals_with_warning():
    journals = [journal_row(trade_id="A", net=5.0, close="2026-08-05T10:00:00Z")]
    src = FakeSources(ledger=None, journals=journals,
                      report={"studies": {"gold_forward": {"strategy_id": "S011",
                                                           "chain_ok": False}},
                              "warnings": ["journal altéré : gold_forward"]})
    got = an.collect_rows(an.parse_filters({}), sources=src)
    assert got["source"]["ledger_present"] is False
    assert got["source"]["ledger_rows"] == 0 and got["source"]["journal_rows"] == 1
    assert "ledger absent" in got["warnings"]
    assert "journal altéré : gold_forward" in got["warnings"]
    assert got["source"]["studies"]["gold_forward"]["chain_ok"] is False


def test_collect_rows_source_ledger_ignores_journals_and_journals_ignores_ledger():
    src = FakeSources(ledger=j5_raw(),
                      journals=[journal_row(trade_id="A", net=5.0,
                                            close="2026-08-05T10:00:00Z")])
    got = an.collect_rows(an.parse_filters({"source": "ledger"}), sources=src)
    assert got["source"]["journal_rows"] == 0 and len(got["rows"]) == 5
    assert "closed_rows_journals" not in src.calls
    src2 = FakeSources(ledger=None, journals=src._journals)
    got2 = an.collect_rows(an.parse_filters({"source": "journals"}), sources=src2)
    assert len(got2["rows"]) == 1 and "ledger absent" not in got2["warnings"]
    assert "closed_rows_ledger" not in src2.calls


def test_broken_source_becomes_explicit_warning_never_raises():
    class Broken(FakeSources):
        def closed_rows_journals(self):
            raise OSError("disque en feu")
    got = an.collect_rows(an.parse_filters({}), sources=Broken(ledger=j5_raw()))
    assert len(got["rows"]) == 5
    assert any("closed_rows_journals illisible" in w and "disque en feu" in w
               for w in got["warnings"])


def test_default_sources_never_create_ledger_db(tmp_path, monkeypatch):
    for var in ("RBF_ROOT",):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("TBOT_PROJECT_ROOT", str(tmp_path / "repo"))
    monkeypatch.setenv("TBOT_DB_DIR", str(tmp_path / "db"))
    ledger_path = tmp_path / "db" / "ledger.db"
    monkeypatch.setenv("TBOT_LEDGER_DB", str(ledger_path))
    fake_adapter = SimpleNamespace(
        journal_closed_trades=lambda: [journal_row(trade_id="A", net=5.0,
                                                   close="2026-08-05T10:00:00Z")],
        journal_open_trades=lambda: [],
        journal_capital_initial=lambda: {"S011.XAU-USD": 10000.0},
        journal_report=lambda: {"studies": {"gold_forward": {"closed": 1}},
                                "warnings": []},
    )
    src = an.DefaultSources(journal_mod=fake_adapter)
    out = an.build_analytics({}, sources=src)
    assert not ledger_path.exists() and not (tmp_path / "db").exists()
    assert "ledger absent" in out["warnings"]
    assert out["source"]["ledger_present"] is False
    assert out["header"]["n_trades"] == 1
    assert out["header"]["base"] == {"CHF": 10000.0}
    assert out["by_currency"]["CHF"]["curve"]["base_kind"] == "capital"
    assert out["source"]["studies"] == {"gold_forward": {"closed": 1}}
    assert out["filters"]["options"]["strategy"] == [
        {"id": "S011", "display_name": "S011", "retired": False}]


def test_default_sources_missing_adapter_is_warning(tmp_path, monkeypatch):
    monkeypatch.delenv("RBF_ROOT", raising=False)
    monkeypatch.setenv("TBOT_PROJECT_ROOT", str(tmp_path / "repo"))
    monkeypatch.setenv("TBOT_DB_DIR", str(tmp_path / "db"))
    monkeypatch.setenv("TBOT_LEDGER_DB", str(tmp_path / "db" / "ledger.db"))
    # Simule l'absence du module quel que soit l'ordre des tests : entrée
    # sys.modules à None ET attribut du package retiré (un import antérieur
    # par un autre test aurait sinon satisfait ``from server import …``).
    import server as server_pkg
    monkeypatch.setitem(sys.modules, "server.journal_adapter", None)
    monkeypatch.delattr(server_pkg, "journal_adapter", raising=False)
    out = an.build_analytics({}, sources=an.DefaultSources())
    assert out["by_currency"] == {} and out["header"]["n_trades"] == 0
    assert any("adaptateur journaux indisponible" in w for w in out["warnings"])
    assert "ledger absent" in out["warnings"]


def test_read_manifests_from_disk(tmp_path, monkeypatch):
    monkeypatch.delenv("RBF_ROOT", raising=False)
    monkeypatch.setenv("TBOT_PROJECT_ROOT", str(tmp_path))
    sdir = tmp_path / "strategies"
    (sdir / "S011_gold").mkdir(parents=True)
    (sdir / "S011_gold" / "manifest.yaml").write_text(
        'display_name: "Or"\nmagic_number: 130011\nstatus: RETIRED\n',
        encoding="utf-8")
    (sdir / "S050_broken").mkdir()
    (sdir / "S050_broken" / "manifest.yaml").write_text("{{::", encoding="utf-8")
    m = an.read_manifests()
    assert m["S011"] == {"display_name": "Or", "retired": True, "magic": 130011,
                         "folder": "S011_gold"}
    assert m["S050"]["display_name"] == "S050_broken" and m["S050"]["magic"] == 0


# ── AN-T12 — répartitions ───────────────────────────────────────────────────
def _two_by_two():
    raws = [
        make_row(net=100.0, rid=1, pnl_r=1.0, close="2026-08-03T10:00:00Z"),
        make_row(net=-30.0, rid=2, pnl_r=-0.3, instance="S011.XAG-USD",
                 symbol="XAGUSD", close="2026-08-04T11:00:00Z"),
        make_row(net=50.0, rid=3, pnl_r=0.5, strategy="S013", magic=130013,
                 instance="S013.EUR-JPY", symbol="EURJPY",
                 close="2026-08-05T12:00:00Z"),
        make_row(net=10.0, rid=4, pnl_r=0.1, strategy="S013", magic=130013,
                 instance="S013.AUD-CAD", symbol="AUDCAD",
                 close="2026-08-06T13:00:00Z"),
    ]
    return an.normalize_rows(raws, "ledger")


def test_by_key_instance_symbol_strategy_sums_and_sort():
    rows = _two_by_two()
    total = an.kpi(rows)["net_pnl"]
    inst = an.by_key(rows, "instance", bases={"S011.XAU-USD": 1000.0})
    assert [e["instance"] for e in inst] == ["S011.XAU-USD", "S013.EUR-JPY",
                                             "S013.AUD-CAD", "S011.XAG-USD"]
    assert sum(e["net"] for e in inst) == total
    assert inst[0] == {"instance": "S011.XAU-USD", "symbol": "XAUUSD",
                       "n_trades": 1, "win_rate": 1.0, "net": 100.0,
                       "profit_factor": None, "sum_r": 1.0, "max_drawdown": 0.0}
    assert inst[-1]["max_drawdown"] == 30.0
    sym = an.by_key(rows, "symbol")
    assert [e["symbol"] for e in sym] == ["XAUUSD", "EURJPY", "AUDCAD", "XAGUSD"]
    assert sum(e["net"] for e in sym) == total
    strat = an.by_key(rows, "strategy",
                      manifests={"S013": {"display_name": "MACD", "magic": 130013}})
    assert [(e["strategy_id"], e["net"]) for e in strat] == [("S011", 70.0),
                                                              ("S013", 60.0)]
    assert strat[1]["display_name"] == "MACD"
    assert [i["instance"] for i in strat[0]["instances"]] == ["S011.XAU-USD",
                                                               "S011.XAG-USD"]
    assert sum(e["net"] for e in strat) == total


def test_by_key_sorts_on_raw_net_not_rounded():
    """Relecture tour 1 : tri sur le net brut — deux groupes à 100.004 et
    100.001 (tous deux 100.0 arrondis) gardent leur ordre réel."""
    raws = [make_row(net=100.004, rid=1, close="2026-08-03T10:00:00Z"),
            make_row(net=100.001, rid=2, close="2026-08-04T10:00:00Z",
                     instance="S011.XAG-USD", symbol="XAGUSD")]
    rows = an.normalize_rows(raws, "ledger")
    assert [e["instance"] for e in an.by_key(rows, "instance")] == [
        "S011.XAU-USD", "S011.XAG-USD"]
    raws[0]["net_pnl"], raws[1]["net_pnl"] = 100.001, 100.004
    rows = an.normalize_rows(raws, "ledger")
    assert [e["instance"] for e in an.by_key(rows, "instance")] == [
        "S011.XAG-USD", "S011.XAU-USD"]
    assert [e["symbol"] for e in an.by_key(rows, "symbol")] == ["XAGUSD", "XAUUSD"]
    assert an._raw_net(rows) == pytest.approx(200.005)


def test_sort_rows_tie_break_numeric_id_then_text_ref():
    """Relecture tour 1 : deux trades clos à la même seconde — départage
    numérique sur ``id`` (ordre du ledger), pas lexical ('10' < '9')."""
    same = "2026-08-03T10:00:00Z"
    raws = [make_row(net=1.0, rid=10, close=same), make_row(net=1.0, rid=9, close=same),
            make_row(net=1.0, rid=None, source_ref="T_B", close=same),
            make_row(net=1.0, rid=None, source_ref="T_A", close=same)]
    rows = an.normalize_rows(raws, "ledger")
    assert [r["source_ref"] for r in rows] == ["9", "10", "T_A", "T_B"]
    assert an._id_key({"id": "7"}) == (0, 7, "")
    assert an._id_key({"id": None, "source_ref": "x"}) == (1, 0, "x")
    assert an._id_key({}) == (1, 0, "")


def test_by_key_weekday_and_hour_have_fixed_shapes():
    rows = _two_by_two()
    wd = an.by_key(rows, "weekday", local_tz=timezone.utc)
    assert [e["weekday"] for e in wd] == list(an.WEEKDAYS)
    assert {e["weekday"]: e["n_trades"] for e in wd if e["n_trades"]} == {
        "mon": 1, "tue": 1, "wed": 1, "thu": 1}
    assert sum(e["net"] for e in wd) == 130.0
    hrs = an.by_key(rows, "hour", local_tz=timezone.utc)
    assert [e["hour"] for e in hrs] == list(range(24))
    # open_time = close − 2 h : 08, 09, 10, 11 UTC
    assert {e["hour"] for e in hrs if e["n_trades"]} == {8, 9, 10, 11}
    hrs2 = an.by_key(rows, "hour", local_tz=TZ2)
    assert {e["hour"] for e in hrs2 if e["n_trades"]} == {10, 11, 12, 13}
    with pytest.raises(ValueError):
        an.by_key(rows, "planet")


# ── AN-T20 / AN-T12 — magic divergent ───────────────────────────────────────
def test_magic_divergent_grouped_apart_and_flagged():
    rows = an.normalize_rows(
        [make_row(net=10.0, rid=1, close="2026-08-03T10:00:00Z"),
         make_row(net=-4.0, rid=2, magic=999, close="2026-08-04T10:00:00Z")],
        "ledger")
    manifests = {"S011": {"display_name": "Or", "magic": 130011}}
    strat = an.by_key(rows, "strategy", manifests=manifests)
    assert [e["strategy_id"] for e in strat] == ["S011", an.MAGIC_DIVERGENT]
    assert strat[0]["net"] == 10.0 and strat[1]["net"] == -4.0
    assert an.magic_ok(rows[0], manifests) and not an.magic_ok(rows[1], manifests)
    assert an.trade_row_out(rows[1], manifests)["magic_ok"] is False
    # Sans manifeste (ou magic 0) : rien à confronter -> ok.
    assert an.magic_ok(rows[1], {}) and an.magic_ok(rows[1], {"S011": {"magic": 0}})
    assert [e["strategy_id"] for e in an.by_key(rows, "strategy")] == ["S011"]


# ── AN-T13 — distribution ───────────────────────────────────────────────────
def test_distribution_r_fixed_bins_with_open_ends():
    raws = [make_row(net=0.0, rid=i, pnl_r=r, close=f"2026-08-0{i}T10:00:00Z")
            for i, r in enumerate((-3.5, -3.0, 0.2, 4.9, 5.0), start=1)]
    raws.append(make_row(net=1.0, rid=6, risk=None, close="2026-08-06T10:00:00Z"))
    d = an.distribution(an.normalize_rows(raws, "ledger"), "r")
    assert d["unit"] == "r" and d["n_without_r"] == 1
    assert len(d["bins"]) == 18
    assert d["bins"][0] == {"lo": None, "hi": -3.0, "n": 1}
    assert d["bins"][-1] == {"lo": 5.0, "hi": None, "n": 1}
    hits = {(b["lo"], b["hi"]): b["n"] for b in d["bins"] if b["n"]}
    assert hits == {(None, -3.0): 1, (-3.0, -2.5): 1, (0.0, 0.5): 1,
                    (4.5, 5.0): 1, (5.0, None): 1}
    assert sum(b["n"] for b in d["bins"]) == 5


def test_distribution_ccy_sixteen_bins_and_single_bin():
    raws = [make_row(net=10.0 * i, rid=i, close=f"2026-08-{i + 1:02d}T10:00:00Z")
            for i in range(16)]
    d = an.distribution(an.normalize_rows(raws, "ledger"), "ccy")
    assert d["unit"] == "ccy" and len(d["bins"]) == 16
    assert d["bins"][0]["lo"] == 0.0 and d["bins"][-1]["hi"] == 150.0
    assert all(b["n"] == 1 for b in d["bins"])
    same = an.normalize_rows([make_row(net=5.0, rid=i,
                                       close=f"2026-08-0{i}T10:00:00Z")
                              for i in (1, 2, 3)], "ledger")
    assert an.distribution(same, "ccy")["bins"] == [{"lo": 5.0, "hi": 5.0, "n": 3}]
    assert an.distribution([], "ccy") == {"unit": "ccy", "bins": [], "n_without_r": 0}


# ── AN-T14 — summary ────────────────────────────────────────────────────────
def test_summary_j5_values():
    s = an.summary(j5_rows(), J5_BASE)
    assert s["volume"]["long_win_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert s["volume"]["short_win_rate"] == 0.0
    assert s["volume"]["zeros"] == 1 and s["volume"]["win_rate"] == 0.4
    assert (s["pnl"]["best_trade"], s["pnl"]["worst_trade"]) == (100.0, -50.0)
    assert (s["pnl"]["best_r"], s["pnl"]["worst_r"]) == (2.0, -1.0)
    assert s["pnl"]["pct_trades_ge_1r"] == 0.2
    assert s["pnl"]["sum_risk"] == 250.0 and s["pnl"]["expectancy"] == 12.0
    assert s["risk"]["max_drawdown"] == 50.0 and s["risk"]["recovered_pct"] == 0.2
    assert s["risk"]["sharpe_r"] is None and s["risk"]["sortino_r"] is None
    assert s["risk"]["sharpe_r_annual"] is None
    assert s["streaks"]["current_streak"] == {"kind": "loss", "len": 1}
    assert s["streaks"]["avg_holding_h"] == 2.0
    assert s["streaks"]["median_holding_h"] == 2.0
    assert s["streaks"]["max_holding_h"] == 2.0


def test_summary_sharpe_sortino_on_forty_trades():
    rows = synthetic_rows(40)
    rs = [r["pnl_r"] for r in rows]
    mean, std = statistics.fmean(rs), statistics.stdev(rs)
    years = (39 * 3) / 365.25
    sharpe = mean / std
    sortino = mean / math.sqrt(statistics.fmean(min(v, 0.0) ** 2 for v in rs))
    s = an.summary(rows, 10000.0)["risk"]
    assert s["sharpe_r"] == round(sharpe, 2)
    assert s["sharpe_r_annual"] == round(sharpe * math.sqrt(40 / years), 2)
    assert s["sortino_r"] == round(sortino, 2)
    assert s["n_r"] == 40
    # 19 trades ou 40 trades sur 10 jours : null.
    assert an.summary(synthetic_rows(19), 1.0)["risk"]["sharpe_r"] is None
    short = synthetic_rows(40, step_days=0.25)
    assert an.summary(short, 1.0)["risk"]["sharpe_r"] is None
    # Écart-type nul : null, jamais une division par zéro.
    flat = an.normalize_rows([make_row(net=1.0, pnl_r=0.5, rid=i,
                                       close=f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}T10:00:00Z")
                              for i in range(40)], "ledger")
    assert an.summary(flat, 1.0)["risk"]["sharpe_r"] is None


# ── AN-T15 — streaks ────────────────────────────────────────────────────────
def test_streaks_zero_breaks_both_series():
    nets = [1, 1, 0, -1, -1, -1, 1]
    rows = an.normalize_rows([make_row(net=float(n), rid=i,
                                       close=f"2026-08-{i:02d}T10:00:00Z")
                              for i, n in enumerate(nets, start=1)], "ledger")
    assert an.streaks(rows) == {"max_win_streak": 2, "max_loss_streak": 3,
                                "current_streak": {"kind": "win", "len": 1}}
    assert an.streaks(rows[:3])["current_streak"] == {"kind": "none", "len": 0}
    assert an.streaks([]) == {"max_win_streak": 0, "max_loss_streak": 0,
                              "current_streak": {"kind": "none", "len": 0}}


# ── AN-T16 — drawdown partagé ───────────────────────────────────────────────
def test_drawdown_recovered_null_when_peak_regained_and_durations():
    raws = [make_row(net=100.0, rid=1, close="2026-08-01T10:00:00Z"),
            make_row(net=-60.0, rid=2, close="2026-08-03T10:00:00Z"),
            make_row(net=80.0, rid=3, close="2026-08-07T10:00:00Z")]
    k = an.kpi(an.normalize_rows(raws, "ledger"), 1000.0)
    assert k["max_drawdown"] == 60.0 and k["current_drawdown"] == 0.0
    assert k["recovered_pct"] is None                   # creux effacé
    assert k["dd_duration_days"] == 2.0 and k["recovery_days"] == 4.0
    assert k["max_dd_pct"] == pytest.approx(60 / 1100, abs=1e-4)
    # DD qui part de la base (aucun pic au-dessus de B_0) : durée depuis
    # le premier trade, pas de récupération.
    k2 = an.kpi(an.normalize_rows(raws[1:], "ledger"), 1000.0)
    assert k2["max_drawdown"] == 60.0 and k2["dd_duration_days"] == 0.0
    assert k2["recovered_pct"] is None and k2["recovery_days"] == 4.0


def test_kpi_max_drawdown_equals_curve_series_minimum():
    rows = synthetic_rows(40)
    c = an.curve(rows, 10000.0)
    k = an.kpi(rows, 10000.0)
    assert k["max_drawdown"] == -min(p[2] for p in c["points"])
    assert k["current_drawdown"] == -c["points"][-1][2]
    assert an.summary(rows, 10000.0)["risk"]["max_drawdown"] == k["max_drawdown"]


# ── AN-T17 — journal des trades ─────────────────────────────────────────────
def test_build_trades_page_pagination_sort_and_columns():
    src = FakeSources(ledger=j5_raw(edge_cost=1.5),
                      manifests={"S011": {"display_name": "Or", "magic": 130011}})
    page = an.build_trades_page({"page": "2", "limit": "2"}, sources=src)
    assert (page["total"], page["page"], page["limit"]) == (5, 2, 2)
    assert [r["close_time"] for r in page["rows"]] == ["2026-08-05T10:00:00Z",
                                                        "2026-08-04T10:00:00Z"]
    row = page["rows"][0]
    for key in ("pnl_r", "holding_h", "magic_ok", "arm", "source", "edge_cost_ccy",
                "source_ref"):
        assert key in row, key
    assert "meta_json" not in row
    assert row["holding_h"] == 2.0 and row["magic_ok"] is True
    assert row["edge_cost_ccy"] == 1.5 and row["pnl_r"] == 0.0
    assert set(an.ROW_KEYS) - {"meta_json"} <= set(row)
    last = an.build_trades_page({"page": "3", "limit": "2"}, sources=src)
    assert len(last["rows"]) == 1 and last["rows"][0]["net_pnl"] == 100.0
    beyond = an.build_trades_page({"page": "9"}, sources=src)
    assert beyond["rows"] == [] and beyond["total"] == 5
    assert "version" in page and "generated" in page


@pytest.mark.parametrize("args, name", [
    ({"limit": "5000"}, "limit=5000"), ({"limit": "0"}, "limit=0"),
    ({"page": "0"}, "page=0"), ({"page": "deux"}, "page=deux"),
])
def test_parse_paging_out_of_range_raises(args, name):
    with pytest.raises(ValueError) as e:
        an.parse_paging(args)
    assert str(e.value) == f"paramètre invalide : {name}"
    assert an.parse_paging({}) == (1, an.PAGE_LIMIT_DEFAULT)


# ── AN-T18 — positions ouvertes et /api/analytics/kpi ───────────────────────
def test_open_positions_listed_but_never_counted():
    open_ledger = [dict(make_row(net=0.0, close="2026-08-09T09:00:00Z", rid=50),
                        close_time=None, net_pnl=None, meta_json='{"arm": "PRIMARY"}',
                        open_time="2026-08-09T09:00:00Z")]
    open_journal = [dict(journal_row(trade_id="OPEN_1", net=0.0, mode="PAPER",
                                     strategy="S020", instance="S020.EUR-USD",
                                     symbol="EURUSD", arm="PRIMARY",
                                     close="2026-08-09T10:00:00Z"),
                         close_time=None, open_time="2026-08-09T10:00:00Z")]
    src = FakeSources(ledger=j5_raw(), open_ledger=open_ledger,
                      open_journals=open_journal)
    now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    out = an.build_analytics({}, sources=src, now=now)
    assert out["by_currency"]["CHF"]["kpi"]["total_trades"] == 5
    ops = out["open_positions"]
    assert [(p["source"], p["instance_id"], p["age_h"]) for p in ops] == [
        ("ledger", "S011.XAU-USD", 3.0), ("journal", "S020.EUR-USD", 2.0)]
    assert set(ops[0]) == {"source", "strategy_id", "instance_id", "mode",
                           "symbol", "side", "open_time", "open_price",
                           "stop_price", "target_price", "volume_lots",
                           "risk_amount", "arm", "age_h"}
    assert ops[0]["arm"] == "PRIMARY"
    only = an.build_analytics({"strategy": "S020"}, sources=src, now=now)
    assert [p["instance_id"] for p in only["open_positions"]] == ["S020.EUR-USD"]
    assert an.build_analytics({"mode": "LIVE"}, sources=src)["open_positions"] == []


def test_build_kpi_separates_paper_and_live_never_backtest():
    raws = j5_raw() + [
        make_row(net=40.0, rid=10, mode="LIVE", close="2026-08-10T10:00:00Z"),
        make_row(net=999.0, rid=11, mode="BACKTEST", close="2026-08-10T11:00:00Z"),
        make_row(net=-7.0, rid=12, mode="LIVE", currency="EUR",
                 close="2026-08-11T10:00:00Z")]
    out = an.build_kpi(sources=FakeSources(ledger=raws,
                                           capital={"S011.XAU-USD": 1000.0}))
    assert set(out) == {"generated", "version", "PAPER", "LIVE", "warnings"}
    assert out["PAPER"]["CHF"]["total_trades"] == 5
    assert out["PAPER"]["CHF"]["net_pnl"] == 60.0
    assert out["PAPER"]["CHF"]["max_dd_pct"] == pytest.approx(0.0455, abs=1e-4)
    assert out["LIVE"]["CHF"]["net_pnl"] == 40.0
    assert out["LIVE"]["EUR"]["net_pnl"] == -7.0
    empty = an.build_kpi(sources=FakeSources(ledger=None))
    assert empty["PAPER"] == {} and empty["LIVE"] == {}
    assert "ledger absent" in empty["warnings"]


# ── AN-T19 — SOLDE & COÛTS ──────────────────────────────────────────────────
def test_summary_balance_and_costs():
    rows = j5_rows(edge_cost=0.8, commission=0.5, swap=-0.1)
    b = an.summary(rows, J5_BASE)["balance"]
    assert b["base"] == 1000.0 and b["base_kind"] == "capital"
    assert b["final_balance"] == 1060.0
    assert b["total_edge_cost"] == 4.0
    assert b["total_commission"] == 2.5 and b["total_swap"] == -0.5
    b0 = an.summary(rows, None)["balance"]
    assert b0["base"] is None and b0["final_balance"] is None
    assert b0["base_kind"] == "zero" and b0["total_edge_cost"] == 4.0


# ── §3.3 — starting balance ─────────────────────────────────────────────────
def test_resolve_bases_resolution_order():
    raws = [make_row(net=1.0, rid=1, account_balance=500.0,
                     close="2026-08-03T10:00:00Z"),
            make_row(net=1.0, rid=2, account_balance=700.0, strategy="S013",
                     instance="S013.EUR-JPY", symbol="EURJPY",
                     close="2026-08-04T10:00:00Z"),
            make_row(net=1.0, rid=3, account_balance=None, strategy="S013",
                     instance="S013.AUD-CAD", symbol="AUDCAD",
                     close="2026-08-05T10:00:00Z"),
            make_row(net=1.0, rid=4, account_balance=900.0, strategy="S013",
                     instance="S013.EUR-JPY", symbol="EURJPY",
                     close="2026-08-06T10:00:00Z")]
    rows = an.normalize_rows(raws, "ledger")
    assert an.resolve_bases(rows, {"S011.XAU-USD": 10000.0}, None,
                            allocated={"S013": 5000.0}) == {
        "S011.XAU-USD": 10000.0, "S013.EUR-JPY": 5000.0, "S013.AUD-CAD": 5000.0}
    assert an.resolve_bases(rows, {}, None, allocated={}) == {
        "S011.XAU-USD": 500.0, "S013.EUR-JPY": 700.0, "S013.AUD-CAD": None}
    # Instance connue de l'adaptateur mais sans trade clos : base posée.
    assert an.resolve_bases([], {"S020.USD-JPY": 10000.0}, None,
                            allocated={}) == {"S020.USD-JPY": 10000.0}


def test_resolve_bases_first_trade_by_open_time_not_close_time():
    """§3.3 repli (3) : trade A ouvert le 1er clos le 5, trade B ouvert le
    2 clos le 3 — la base est l'account_balance de A (premier par
    open_time), même si B est clos avant."""
    raws = [make_row(net=1.0, rid=1, account_balance=500.0,
                     open_time="2026-08-01T10:00:00Z", close="2026-08-05T10:00:00Z"),
            make_row(net=1.0, rid=2, account_balance=700.0,
                     open_time="2026-08-02T10:00:00Z", close="2026-08-03T10:00:00Z")]
    rows = an.normalize_rows(raws, "ledger")
    assert an.resolve_bases(rows, {}, None, allocated={}) == {"S011.XAU-USD": 500.0}


def test_parse_filters_symbol_accepts_broker_suffixes():
    """Relecture tour 1 : ``XAUUSD+`` / ``EURUSD!`` / ``US30.cash`` sont
    proposés dans options.symbol et doivent rester filtrables (AN-4)."""
    f = an.parse_filters({"symbol": ["XAUUSD+", "EURUSD!", "US30.cash"]})
    assert f.symbol == ["XAUUSD+", "EURUSD!", "US30.cash"]
    with pytest.raises(ValueError):
        an.parse_filters({"symbol": "XAU USD"})
    with pytest.raises(ValueError):
        an.parse_filters({"strategy": "S011+"})     # le préfixe strict reste


def test_generated_utc_is_zulu_second_precision():
    g = an.generated_utc()
    assert g.endswith("Z") and len(g) == 20
    datetime.strptime(g, "%Y-%m-%dT%H:%M:%SZ")
    assert an._generated is an.generated_utc


def test_currency_base_sums_instances_or_falls_to_zero():
    rows = _two_by_two()
    bases = {"S011.XAU-USD": 10000.0, "S011.XAG-USD": 10000.0,
             "S013.EUR-JPY": 10000.0, "S013.AUD-CAD": 10000.0}
    assert an.currency_base(rows, bases, "auto") == (40000.0, "capital", [])
    partial = dict(bases, **{"S013.AUD-CAD": None})
    assert an.currency_base(rows, partial, "auto") == (None, "zero", [])
    base, kind, warns = an.currency_base(rows, partial, "capital")
    assert (base, kind) == (None, "zero")
    assert warns and "S013.AUD-CAD" in warns[0]
    assert an.currency_base(rows, bases, "zero") == (None, "zero", [])
    assert an.currency_base([], bases, "auto") == (None, "zero", [])
    # Une stratégie à N instances a pour base la SOMME (s13 : 10 000 par arm).
    s13 = [r for r in rows if r["strategy_id"] == "S013"]
    assert an.currency_base(s13, bases, "auto")[0] == 20000.0


def test_resolve_bases_reads_ledger_strategy_state(tmp_path):
    from core.ledger import Ledger
    ledger = Ledger(tmp_path / "ledger.db")
    try:
        with ledger._conn:
            ledger._conn.execute(
                "INSERT INTO strategy_state (strategy_id, allocated_capital) "
                "VALUES ('S013', 2500.0), ('S011', 0.0)")
        assert an._allocated_capital(ledger) == {"S013": 2500.0}
        rows = _two_by_two()
        bases = an.resolve_bases(rows, {}, ledger)
        assert bases["S013.EUR-JPY"] == 2500.0 and bases["S011.XAU-USD"] is None
    finally:
        ledger.close()


# ── §6.1 — forme du payload ─────────────────────────────────────────────────
def test_build_analytics_shape_and_empty_subset():
    out = an.build_analytics({}, sources=FakeSources(ledger=[]))
    assert set(out) == {"generated", "version", "filters", "source", "header",
                        "by_currency", "open_positions", "warnings"}
    assert out["by_currency"] == {} and out["header"]["n_trades"] == 0
    assert out["header"]["source_kind"] == "aucune" and out["warnings"] == []
    assert set(out["filters"]["options"]) == set(an.MULTI_PARAMS)
    assert out["filters"]["applied"]["mode"] == "PAPER"
    assert out["generated"].endswith("Z")

    full = an.build_analytics({"strategy": "S011", "curve_base": "capital"},
                              sources=FakeSources(
                                  ledger=j5_raw(), capital={"S011.XAU-USD": 1000.0},
                                  manifests={"S011": {"display_name": "Or",
                                                      "magic": 130011}}))
    blk = full["by_currency"]["CHF"]
    assert set(blk) == {"kpi", "curve", "heatmap", "by_month", "by_instance",
                        "by_symbol", "by_strategy", "by_weekday", "by_hour",
                        "distribution", "summary"}
    assert full["header"] == {"mode": "PAPER", "n_strategies": 1,
                              "n_instances": 1, "n_trades": 5,
                              "base": {"CHF": 1000.0}, "base_kind": "capital",
                              "source_kind": "ledger"}
    assert blk["kpi"]["max_dd_pct"] == pytest.approx(0.0455, abs=1e-4)
    assert blk["summary"]["balance"]["final_balance"] == 1060.0
    assert blk["by_strategy"][0]["display_name"] == "Or"
    assert full["filters"]["applied"]["strategy"] == ["S011"]
    assert full["source"]["ledger_rows"] == 5 and full["source"]["dedup"] == 0


def test_build_analytics_mixed_sources_and_zero_base_by_default():
    src = FakeSources(ledger=j5_raw(),
                      journals=[journal_row(trade_id="J1", net=5.0, strategy="S020",
                                            instance="S020.EUR-USD", symbol="EURUSD",
                                            study="s20_forward",
                                            close="2026-08-12T10:00:00Z")])
    out = an.build_analytics({}, sources=src)
    assert out["header"]["source_kind"] == "mixte"
    assert out["header"]["n_strategies"] == 2 and out["header"]["n_trades"] == 6
    # Base J5 = account_balance 1 000 mais S020 inconnue -> zéro pour la devise.
    assert out["header"]["base"] == {"CHF": None}
    assert out["header"]["base_kind"] == "zero"
    assert out["by_currency"]["CHF"]["curve"]["base_kind"] == "zero"
    assert out["by_currency"]["CHF"]["kpi"]["net_pnl"] == 65.0
    warned = an.build_analytics({"curve_base": "capital"}, sources=src)
    assert any("S020.EUR-USD" in w for w in warned["warnings"])


def test_bases_resolved_on_requested_mode_only():
    # Même instance en BACKTEST (account_balance 50 000, plus ancien) et en
    # PAPER (account_balance 1 000) : la base PAPER ne doit jamais venir du
    # trade BACKTEST (D-AN-5, §3.3 « premier trade clos de l'instance »).
    raws = [make_row(net=5.0, rid=1, mode="BACKTEST", account_balance=50000.0,
                     close="2026-07-01T10:00:00Z"),
            make_row(net=10.0, rid=2, mode="PAPER", account_balance=1000.0,
                     close="2026-08-03T10:00:00Z")]
    out = an.build_analytics({"mode": "PAPER"}, sources=FakeSources(ledger=raws))
    assert out["header"]["base"] == {"CHF": 1000.0}
    assert out["by_currency"]["CHF"]["curve"]["base"] == 1000.0
    bt = an.build_analytics({"mode": "BACKTEST"}, sources=FakeSources(ledger=raws))
    assert bt["header"]["base"] == {"CHF": 50000.0}
    # build_kpi : PAPER sur sa propre base, LIVE inconnue -> base zéro.
    raws.append(make_row(net=3.0, rid=3, mode="LIVE", close="2026-08-04T10:00:00Z"))
    k = an.build_kpi(sources=FakeSources(ledger=raws))
    assert k["PAPER"]["CHF"]["max_dd_pct"] == 0.0     # base connue, aucun DD
    assert k["LIVE"]["CHF"]["max_dd_pct"] is None      # base inconnue


def test_build_analytics_invalid_filter_raises_for_the_route():
    with pytest.raises(ValueError, match="paramètre invalide : mode=X"):
        an.build_analytics({"mode": "X"}, sources=FakeSources(ledger=[]))
    with pytest.raises(ValueError, match="paramètre invalide : limit=5000"):
        an.build_trades_page({"limit": "5000"}, sources=FakeSources(ledger=[]))
