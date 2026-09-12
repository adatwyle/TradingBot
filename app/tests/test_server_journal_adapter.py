"""
Tests de l'adaptateur journaux forward (SPEC_analytics-trades §3.2, AN-12,
AN-T1…AN-T4).

POURQUOI ce banc : l'adaptateur est la seule source réelle de trades tant que
le ledger est vide. Le banc fige : le mapping complet vers les 31 clés de
``Ledger.closed_trades()`` + ``instance_id`` + clés source (AN-T1), la
conversion heure serveur → UTC par la règle DST UE et le garde-fou
``measured_at_utc`` (AN-T2), l'intégrité (chaîne rompue servie avec alerte,
journal / params absents = étude ignorée, AUCUN fichier créé — AN-T3), les
journaux à bras et symboles (s13, alexg — AN-T4), et chaque fonction unitaire
(dernier dimanche, offset, coût de bord, raison de sortie, empreinte d'état).

    pytest app/tests/test_server_journal_adapter.py -q
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import date, datetime

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import journal_adapter as ja                  # noqa: E402


# ── fabrique de lignes de journal (format gold : sans arm ni symbol) ────────
def _open(trade_id, bar_time, *, side="SHORT", entry=4345.081, stop=4368.801,
          target=4282.286, lots=0.0422, risk=100.0, capital=10000.0,
          measured="2026-08-18T22:57:55Z", **extra):
    row = {"measured_at_utc": measured, "event": "OPEN", "trade_id": trade_id,
           "bar_time": bar_time, "side": side, "entry_price": entry,
           "stop_price": stop, "target_price": target, "size_lots": lots,
           "risk_ccy": risk, "capital_after": capital}
    row.update(extra)
    return row


def _close(trade_id, bar_time, *, side="SHORT", entry=4345.081, stop=4368.801,
           target=4282.286, lots=0.0422, risk=100.0, exit_price=4368.801,
           reason="SL", pnl_r=-1.0053, pnl=-100.53, capital=9899.47,
           measured="2026-08-19T13:59:42Z", **extra):
    row = {"measured_at_utc": measured, "event": "CLOSE", "trade_id": trade_id,
           "bar_time": bar_time, "side": side, "entry_price": entry,
           "stop_price": stop, "target_price": target, "size_lots": lots,
           "risk_ccy": risk, "exit_price": exit_price, "exit_reason": reason,
           "pnl_r": pnl_r, "pnl_ccy": pnl, "capital_after": capital}
    row.update(extra)
    return row


def _gold_rows():
    """2 trades clos + 1 OPEN seul (AN-T1)."""
    return [
        _open("SHORT_20260818_2100", "2026-08-18T21:00:00"),
        _close("SHORT_20260818_2100", "2026-08-19T12:00:00"),
        _open("LONG_20260821_0700", "2026-08-21T07:00:00", side="LONG",
              entry=4553.371, stop=4525.7285, target=4626.626, lots=0.0358,
              risk=98.99, capital=9899.47, measured="2026-08-21T08:12:34Z"),
        _close("LONG_20260821_0700", "2026-08-22T10:00:00", side="LONG",
               entry=4553.371, stop=4525.7285, target=4626.626, lots=0.0358,
               risk=98.99, exit_price=4626.626, reason="TP", pnl_r=2.6,
               pnl=257.4, capital=10156.87, measured="2026-08-22T11:00:00Z"),
        _open("SHORT_20260910_1400", "2026-09-10T14:00:00", capital=10156.87,
              measured="2026-09-10T15:34:53Z"),
    ]


def _snapshot(*roots):
    """Listing récursif (chemins + tailles) — preuve « aucun fichier créé »."""
    out = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            for name in dirnames:
                out.add(("d", os.path.join(dirpath, name)))
            for name in filenames:
                p = os.path.join(dirpath, name)
                out.add(("f", p, os.path.getsize(p)))
    return out


# ── fonctions unitaires ─────────────────────────────────────────────────────
def test_last_sunday_of_march_and_october():
    assert ja.last_sunday(2026, 3) == date(2026, 3, 29)
    assert ja.last_sunday(2026, 10) == date(2026, 10, 25)
    assert ja.last_sunday(2025, 3) == date(2025, 3, 30)
    assert ja.last_sunday(2024, 10) == date(2024, 10, 27)


def test_eu_dst_offset_hours_summer_winter_and_boundaries():
    assert ja.eu_dst_offset_hours(datetime(2026, 7, 1, 16, 0)) == 3
    assert ja.eu_dst_offset_hours(datetime(2026, 12, 1, 16, 0)) == 2
    # Dernier dimanche de mars 2026 : 01:00 UTC = 03:00 serveur (hiver
    # jusque-là, +2). Juste avant → 2, juste après → 3.
    assert ja.eu_dst_offset_hours(datetime(2026, 3, 29, 2, 59)) == 2
    assert ja.eu_dst_offset_hours(datetime(2026, 3, 29, 3, 0)) == 3
    # Dernier dimanche d'octobre 2026 : fin à 01:00 UTC = 03:00 serveur été.
    assert ja.eu_dst_offset_hours(datetime(2026, 10, 25, 2, 59)) == 3
    assert ja.eu_dst_offset_hours(datetime(2026, 10, 25, 3, 0)) == 2


def test_bar_time_to_utc_applies_rule_and_is_injectable():
    assert ja.iso_z(ja.bar_time_to_utc("2026-07-01T16:00:00")) == "2026-07-01T13:00:00Z"
    assert ja.iso_z(ja.bar_time_to_utc("2026-12-01T16:00:00")) == "2026-12-01T14:00:00Z"
    # Règle injectée : offset constant 0 → heure serveur = UTC.
    assert ja.iso_z(ja.bar_time_to_utc("2026-07-01T16:00:00",
                                       lambda dt: 0)) == "2026-07-01T16:00:00Z"
    # Déjà zoné : respecté ; vide / illisible : None.
    assert ja.iso_z(ja.bar_time_to_utc("2026-07-01T16:00:00Z")) == "2026-07-01T16:00:00Z"
    assert ja.bar_time_to_utc("") is None
    assert ja.bar_time_to_utc("pas une date") is None
    assert ja.bar_time_to_utc(None) is None


def test_server_offset_rule_constant_is_used_by_default(monkeypatch):
    monkeypatch.setattr(ja, "SERVER_OFFSET_RULE", lambda dt: 5)
    assert ja.iso_z(ja.bar_time_to_utc("2026-07-01T16:00:00")) == "2026-07-01T11:00:00Z"


def test_to_float_and_exit_reason_and_instance_id():
    assert ja.to_float("") is None
    assert ja.to_float(None) is None
    assert ja.to_float("abc") is None
    assert ja.to_float("-100.53") == -100.53
    assert ja.to_float(3) == 3.0
    assert ja.normalize_exit_reason("SL") == "SL"
    assert ja.normalize_exit_reason("tp") == "TP"
    assert ja.normalize_exit_reason("EOD") == "EOD"
    assert ja.normalize_exit_reason("TIME") == "MANUAL"
    assert ja.normalize_exit_reason("") == "MANUAL"
    assert ja.normalize_exit_reason(None) == "MANUAL"
    # Même règle que declared_instances (state.py) : paire FX vs mono-instrument.
    assert ja.instance_id_of("S011", "XAUUSD") == "S011.XAU-USD"
    assert ja.instance_id_of("S013", "EURJPY") == "S013.EUR-JPY"
    assert ja.instance_id_of("S012", "SP500") == "S012.SP500"


def test_edge_cost_ccy_formula_and_incomplete_spec():
    spec = {"pip": 0.01, "spread_pips": 25.0, "slippage_pips": 0.0}
    # edge = 25 × 0.01 / 2 = 0.125 ; payé deux fois ; × risk / distance.
    got = ja.edge_cost_ccy(spec, 100.0, 23.72)
    assert abs(got - 2 * 0.125 * 100.0 / 23.72) < 1e-12
    spec2 = {"pip": 0.0001, "spread_pips": 2.0, "slippage_pips": 0.5}
    got2 = ja.edge_cost_ccy(spec2, 100.0, 0.005)
    assert abs(got2 - 2 * (0.0001 + 0.00005) * 100.0 / 0.005) < 1e-12
    assert ja.edge_cost_ccy({"pip": 0.01}, 100.0, 1.0) is None
    assert ja.edge_cost_ccy(None, 100.0, 1.0) is None
    assert ja.edge_cost_ccy(spec, None, 1.0) is None
    assert ja.edge_cost_ccy(spec, 100.0, 0.0) is None
    assert ja.edge_cost_ccy(spec, 100.0, None) is None


def test_study_symbol_spec_for_and_capital_helpers():
    gold = {"instrument": "XAUUSD", "spec": {"symbol": "XAUUSD", "pip": 0.01},
            "sizing": {"capital_initial": 10000.0}}
    assert ja.study_symbol(gold) == "XAUUSD"
    assert ja.spec_for(gold, "XAUUSD")["pip"] == 0.01
    assert ja.spec_for(gold, "EURUSD") is None
    assert ja.capital_initial_of(gold) == 10000.0
    assert ja.capital_instances(gold) == ["XAUUSD"]

    s13 = {"primary_symbol": "AUDCAD",
           "instruments": {"AUDCAD": "PRIMARY", "EURJPY": "OBSERVATION"},
           "specs": {"EURJPY": {"pip": 0.01}}, "sizing": {"capital_initial": 10000}}
    assert ja.study_symbol(s13) == "AUDCAD"
    assert ja.spec_for(s13, "EURJPY") == {"pip": 0.01}
    assert ja.spec_for(s13, "AUDCAD") is None
    assert ja.capital_instances(s13) == ["AUDCAD", "EURJPY"]

    alexg = {"instruments": ["EURUSD", "GBPUSD"], "sizing": {}}
    assert ja.study_symbol(alexg) is None
    assert ja.capital_initial_of(alexg) is None
    assert ja.capital_instances(alexg) == []
    assert ja.capital_initial_of({}) is None


def test_verify_chain_accepts_valid_and_reports_break():
    header = "a,b,chain\n"
    l1 = "1,2," + hashlib.sha256(header.encode()).hexdigest() + "\n"
    l2 = "3,4," + hashlib.sha256((header + l1).encode()).hexdigest() + "\n"
    assert ja.verify_chain(header + l1 + l2) is None
    assert ja.verify_chain(header) is None                # en-tête seul
    assert "vide" in ja.verify_chain("")
    # Réécrire la ligne 2 casse le maillon de la ligne 3 (SHA du fichier
    # AVANT la ligne) ; falsifier le maillon lui-même casse la ligne 2.
    tampered = header + l1.replace("1,2,", "9,2,") + l2
    assert "ligne 3" in ja.verify_chain(tampered)
    forged = header + "1,2," + "0" * 64 + "\n" + l2
    assert "ligne 2" in ja.verify_chain(forged)
    assert "ligne 3" in ja.verify_chain(header + l1 + "3,4,5,6\n")
    assert "colonnes" in ja.verify_chain(header + "1,2\n")


def test_verify_state_fingerprint():
    raw = b"a,b,chain\n1,2,x\n"
    sha = hashlib.sha256(raw).hexdigest()
    assert ja.verify_state_fingerprint(raw, None) is None
    assert ja.verify_state_fingerprint(raw, {}) is None
    assert ja.verify_state_fingerprint(raw, {"journal_bytes": 0}) is None
    ok = {"journal_bytes": len(raw), "journal_sha256": sha}
    assert ja.verify_state_fingerprint(raw, ok) is None
    assert ja.verify_state_fingerprint(raw + b"3,4,y\n", ok) is None
    assert "tronqué" in ja.verify_state_fingerprint(raw[:-3], ok)
    assert "empreinte" in ja.verify_state_fingerprint(
        raw, {"journal_bytes": len(raw), "journal_sha256": "0" * 64})
    assert ja.verify_state_fingerprint(raw, {"journal_bytes": "x"}) is None


def test_parse_journal_text_splits_header_and_rows():
    header, rows = ja.parse_journal_text('a,b\n1,"x,y"\n')
    assert header == ["a", "b"] and rows == [["1", "x,y"]]
    assert ja.parse_journal_text("") == ([], [])


def test_studies_catalogue_is_fixed():
    assert dict(ja.STUDIES) == {"gold_forward": "S011", "s13_forward": "S013",
                                "s20_forward": "S020", "alexg_paper": "S093",
                                "macd_ai_paper": "S012"}
    assert "s14_sentiment" not in ja.STUDY_STRATEGY


# ── AN-T1 : journal gold → lignes §3.1 + position ouverte ───────────────────
def test_an_t1_gold_journal_maps_to_ledger_rows(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows(),
                         strategy_folder="S011_legacy_breakout")
    rows = ja.journal_closed_trades()
    assert len(rows) == 2
    for r in rows:
        assert set(r) == set(ja.LEDGER_KEYS) | set(ja.SOURCE_KEYS)
        assert r["instance_id"] == "S011.XAU-USD"
        assert r["mode"] == "PAPER" and r["currency"] == "CHF"
        assert r["strategy_id"] == "S011" and r["run_id"] == "gold_forward"
        assert r["symbol"] == "XAUUSD" and r["timeframe"] == "H1"
        assert r["source"] == "journal" and r["source_ref"] == r["meta_json"]["trade_id"]
        assert r["id"] is None and r["ticket"] is None
        assert r["commission"] == 0.0 and r["swap"] == 0.0
        assert r["gross_pnl"] == r["net_pnl"]
        assert r["magic_number"] == 130011 and r["strategy_version"] == "1.0.0"
        assert r["arm"] == "PRIMARY" and r["meta_json"]["arm"] == "PRIMARY"
        assert r["meta_json"]["chain_ok"] is True

    first, second = rows                      # tri close_time croissant
    assert first["source_ref"] == "SHORT_20260818_2100"
    assert first["account_balance"] == 10000.0        # capital_after de l'OPEN
    assert first["meta_json"]["capital_after"] == 9899.47
    assert first["pnl_r"] == -1.0053 and first["meta_json"]["pnl_r"] == -1.0053
    assert first["net_pnl"] == -100.53
    assert first["exit_reason"] == "SL" and first["side"] == "SHORT"
    assert first["open_price"] == 4345.081 and first["close_price"] == 4368.801
    assert first["stop_price"] == 4368.801 and first["target_price"] == 4282.286
    assert first["volume_lots"] == 0.0422 and first["risk_amount"] == 100.0
    assert abs(first["risk_distance"] - 23.72) < 1e-9
    # Été : +3 h.
    assert first["open_time"] == "2026-08-18T18:00:00Z"
    assert first["close_time"] == "2026-08-19T09:00:00Z"
    assert first["created_at"] == "2026-08-19T13:59:42Z"
    assert first["signal_reason"] is None and first["confidence"] is None
    # Coût de bord depuis params.spec : 2 × (25 × 0.01 / 2) × 100 / 23.72.
    expected_edge = 2 * 0.125 * 100.0 / 23.72
    assert abs(first["meta_json"]["edge_cost_ccy"] - expected_edge) < 1e-9
    assert first["meta_json"]["measured_at_utc_open"] == "2026-08-18T22:57:55Z"
    assert first["meta_json"]["measured_at_utc_close"] == "2026-08-19T13:59:42Z"

    assert second["source_ref"] == "LONG_20260821_0700"
    assert second["exit_reason"] == "TP" and second["pnl_r"] == 2.6
    assert second["account_balance"] == 9899.47

    opened = ja.journal_open_trades()
    assert len(opened) == 1
    pos = opened[0]
    assert set(pos) == {"source", "strategy_id", "instance_id", "mode",
                        "symbol", "side", "open_time", "open_price",
                        "stop_price", "target_price", "volume_lots",
                        "risk_amount", "arm", "age_h"}
    assert pos["instance_id"] == "S011.XAU-USD" and pos["mode"] == "PAPER"
    assert pos["open_time"] == "2026-09-10T11:00:00Z"
    assert pos["risk_amount"] == 100.0 and pos["arm"] == "PRIMARY"
    assert pos["age_h"] > 0
    assert "pnl" not in " ".join(pos)                 # jamais de P&L flottant

    assert ja.journal_capital_initial() == {"S011.XAU-USD": 10000.0}
    rep = ja.journal_report()
    # Les quatre autres études du catalogue signalent leur journal absent ;
    # gold elle-même est propre.
    assert not [w for w in rep["warnings"] if "gold_forward" in w]
    assert len(rep["warnings"]) == len(ja.STUDIES) - 1
    g = rep["studies"]["gold_forward"]
    assert g["strategy_id"] == "S011" and g["rows"] == 5
    assert g["closed"] == 2 and g["open"] == 1 and g["chain_ok"] is True
    assert g["path"].endswith("journal.csv")
    assert g["started_at"] == "2026-08-16T20:59:28Z"


def test_manifest_absent_falls_back_to_study_version_and_magic_0(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows(), strategy_folder=None)
    rows = ja.journal_closed_trades()
    assert len(rows) == 2
    assert rows[0]["strategy_version"] == "study"
    assert rows[0]["magic_number"] == 0


def test_studies_filter_and_unknown_study_warning(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows())
    ui_env.write_journal("s13_forward", _s13_rows())
    assert len(ja.journal_closed_trades()) == 3
    assert len(ja.journal_closed_trades(studies=["gold_forward"])) == 2
    assert [r["strategy_id"] for r in ja.journal_closed_trades(studies=["s13_forward"])] == ["S013"]
    rep = ja.journal_report(studies=["gold_forward", "inconnue"])
    assert list(rep["studies"]) == ["gold_forward"]
    assert any("inconnue" in w for w in rep["warnings"])


# ── AN-T2 : offset serveur → UTC + garde-fou measured_at ────────────────────
def test_an_t2_bar_time_summer_winter_and_measured_guard(ui_env):
    rows = [
        _open("A", "2026-07-01T16:00:00", measured="2026-07-01T14:05:00Z"),
        _close("A", "2026-07-01T18:00:00", measured="2026-07-01T16:05:00Z"),
        _open("B", "2026-12-01T16:00:00", measured="2026-12-01T14:05:00Z"),
        _close("B", "2026-12-01T18:00:00", measured="2026-12-01T16:05:00Z"),
        # C : bar_time postérieur à la mesure → warning, ligne conservée.
        _open("C", "2026-12-02T16:00:00", measured="2026-12-02T10:00:00Z"),
        _close("C", "2026-12-02T18:00:00", measured="2026-12-02T16:05:00Z"),
    ]
    ui_env.write_journal("gold_forward", rows)
    trades = {r["source_ref"]: r for r in ja.journal_closed_trades()}
    assert trades["A"]["open_time"] == "2026-07-01T13:00:00Z"
    assert trades["B"]["open_time"] == "2026-12-01T14:00:00Z"
    assert "C" in trades                                 # conservée
    warnings = ja.journal_report()["warnings"]
    assert any("postérieur" in w and "ligne 6" in w for w in warnings)
    assert not any("ligne 2" in w or "ligne 4" in w for w in warnings)


def test_an_t2_offset_rule_injected_per_call(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows())
    rows = ja.journal_closed_trades(offset_rule=lambda dt: 0)
    assert rows[0]["open_time"] == "2026-08-18T21:00:00Z"
    assert ja.journal_open_trades(offset_rule=lambda dt: 0)[0]["open_time"] \
        == "2026-09-10T14:00:00Z"


# ── AN-T3 : intégrité et absences, sans jamais rien créer ───────────────────
def test_an_t3_broken_chain_served_with_warning(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows(), chain=False)
    rows = ja.journal_closed_trades()
    assert len(rows) == 2                                # servies quand même
    assert all(r["meta_json"]["chain_ok"] is False for r in rows)
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["chain_ok"] is False
    assert any(w.startswith("journal altéré : gold_forward") for w in rep["warnings"])


def test_an_t3_state_fingerprint_mismatch_is_reported(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows(),
                         state={"started_at": "2026-08-16T20:59:28Z",
                                "journal_bytes": 10,
                                "journal_sha256": "0" * 64})
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["chain_ok"] is False
    assert any("journal altéré : gold_forward" in w and "empreinte" in w
               for w in rep["warnings"])
    assert len(ja.journal_closed_trades()) == 2


def test_an_t3_state_absent_or_corrupt_only_warns(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows(), state=None)
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["closed"] == 2
    assert rep["studies"]["gold_forward"]["started_at"] is None
    assert any("state.json absent : gold_forward" in w for w in rep["warnings"])
    (ui_env.db / "gold_forward" / "state.json").write_text("{pas", encoding="utf-8")
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["closed"] == 2
    assert any("state.json illisible" in w for w in rep["warnings"])


def test_an_t3_journal_absent_and_params_absent(ui_env):
    # Aucun journal : aucune étude dans le rapport, un warning par étude.
    rep = ja.journal_report()
    assert rep["studies"] == {}
    assert sorted(rep["warnings"]) == sorted(
        f"journal absent : {f}" for f, _ in ja.STUDIES)
    assert ja.journal_closed_trades() == []
    assert ja.journal_open_trades() == []
    assert ja.journal_capital_initial() == {}

    # params.json absent : étude ignorée (hors rapport, hors lignes).
    ui_env.write_journal("gold_forward", _gold_rows(), params=None)
    rep = ja.journal_report()
    assert "gold_forward" not in rep["studies"]
    assert any("params.json absent" in w and "gold_forward" in w
               for w in rep["warnings"])
    assert ja.journal_closed_trades() == []


def test_an_t3_unreadable_journal_bytes_or_empty(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows())
    (ui_env.db / "gold_forward" / "journal.csv").write_bytes(b"\xff\xfe\x00bad")
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["chain_ok"] is False
    assert any("journal illisible : gold_forward" in w for w in rep["warnings"])
    assert ja.journal_closed_trades() == []
    (ui_env.db / "gold_forward" / "journal.csv").write_bytes(b"")
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["rows"] == 0
    assert any("vide" in w for w in rep["warnings"])
    # Relecture tour 1 : un journal réduit à des sauts de ligne (première
    # ligne vide) ne doit plus lever StopIteration hors de read_study.
    for degenerate in (b"\n", b"\n\n", b"\r\n"):
        (ui_env.db / "gold_forward" / "journal.csv").write_bytes(degenerate)
        rep = ja.journal_report()
        assert rep["studies"]["gold_forward"]["rows"] == 0, degenerate
        assert any("vide" in w for w in rep["warnings"]), degenerate
        assert ja.journal_closed_trades() == []


def test_parse_and_verify_chain_on_newline_only_text():
    assert ja.parse_journal_text("\n") == ([], [])
    assert ja.parse_journal_text("\n\n") == ([], [])
    assert ja.parse_journal_text("") == ([], [])
    assert ja.verify_chain("\n") == "journal vide sans en-tête"
    assert ja.verify_chain("\n\n") == "journal vide sans en-tête"
    assert ja.verify_chain("") == "journal vide sans en-tête"
    # Un en-tête seul est une chaîne valide (aucune ligne à vérifier).
    assert ja.verify_chain("a,b,chain\n") is None
    assert ja.parse_journal_text("a,b,chain\n") == (["a", "b", "chain"], [])


def test_journal_missing_but_state_references_bytes_is_flagged_as_deletion(ui_env):
    """Relecture tour 1 : journal absent alors que state.json en mémorise
    la taille = suppression détectée (lecture de verify_journal)."""
    ui_env.write_journal("gold_forward", _gold_rows())
    (ui_env.db / "gold_forward" / "journal.csv").unlink()
    rep = ja.journal_report(studies=["gold_forward"])
    assert "gold_forward" not in rep["studies"]
    assert any("journal absent : gold_forward" in w and "suppression détectée" in w
               for w in rep["warnings"])
    # Sans state.json (ou taille 0) : simple « journal absent ».
    (ui_env.db / "gold_forward" / "state.json").unlink()
    rep = ja.journal_report(studies=["gold_forward"])
    assert "journal absent : gold_forward" in rep["warnings"]
    assert not any("suppression" in w for w in rep["warnings"])


def test_an_t3_no_file_created_under_db_dir_nor_project_root(ui_env):
    ui_env.write_journal("gold_forward", _gold_rows(), chain=False)
    ui_env.write_journal("s13_forward", _s13_rows(), params=None)
    before = _snapshot(ui_env.db, ui_env.root)
    ja.journal_closed_trades()
    ja.journal_open_trades()
    ja.journal_capital_initial()
    ja.journal_report()
    ja.journal_report(studies=["macd_ai_paper", "inconnue"])
    assert _snapshot(ui_env.db, ui_env.root) == before
    assert not (ui_env.db / "ledger.db").exists()


# ── AN-T4 : journaux à bras et symboles (s13, alexg) ────────────────────────
def _s13_rows():
    return [
        _open("EURJPY_LONG_20260904", "2026-09-04T00:00:00", side="LONG",
              entry=181.459, stop=179.97264, target=182.89936, lots=0.1004,
              risk=100.0, measured="2026-09-07T06:18:23Z",
              arm="OBSERVATION", symbol="EURJPY"),
        _close("EURJPY_LONG_20260904", "2026-09-07T00:00:00", side="LONG",
               entry=181.459, stop=179.97264, target=182.89936, lots=0.1004,
               risk=100.0, exit_price=179.97264, reason="SL", pnl_r=-1.0155,
               pnl=-101.55, capital=9898.45, measured="2026-09-08T06:27:06Z",
               arm="OBSERVATION", symbol="EURJPY"),
        _open("EURJPY_LONG_20260908", "2026-09-08T00:00:00", side="LONG",
              entry=178.914, stop=177.23264, target=180.54936, lots=0.087,
              risk=97.98, capital=9798.01, measured="2026-09-09T06:36:11Z",
              arm="OBSERVATION", symbol="EURJPY"),
    ]


def _alexg_rows():
    base = dict(signal_id="GBPUSD_202608251000", bar_time="2026-08-25T10:00:00",
                side="LONG", entry_price=1.36418, stop_price=1.36208,
                target_price=1.36847, size_lots=0.5923, risk_ccy=100.0,
                measured_at_utc="2026-08-26T19:36:18Z", symbol="GBPUSD")
    shadow_open = dict(base, event="SHADOW_OPEN", arm="SHADOW",
                       trade_id="SHADOW_GBPUSD_LONG_202608251000")
    mech_open = dict(base, event="OPEN", arm="MECH",
                     trade_id="MECH_GBPUSD_LONG_202608251000",
                     capital_after=10000.0)
    decision = {"measured_at_utc": "2026-08-26T19:36:18Z", "event": "DECISION",
                "arm": "AI", "symbol": "GBPUSD", "signal_id": base["signal_id"],
                "bar_time": base["bar_time"], "decision": "skip",
                "size_frac": 0.0, "sl_adjust": 1.0, "tp_adjust": 1.0,
                "reason": "Retrace de seulement 1% dans l'AOI, R:R 2.29."}
    close_common = dict(base, measured_at_utc="2026-08-27T19:36:18Z",
                        bar_time="2026-08-25T14:00:00", exit_price=1.36208,
                        exit_reason="SL", pnl_r=-1.05, pnl_ccy=-105.0)
    mech_close = dict(close_common, event="CLOSE", arm="MECH",
                      trade_id="MECH_GBPUSD_LONG_202608251000",
                      capital_after=9895.0, reason="stop structurel")
    shadow_close = dict(close_common, event="SHADOW_CLOSE", arm="SHADOW",
                        trade_id="SHADOW_GBPUSD_LONG_202608251000",
                        pnl_r_nocost=-0.8)
    return [shadow_open, mech_open, decision, mech_close, shadow_close]


def _alexg_params():
    return {"study": "alexg_paper", "timeframe": "H1",
            "instruments": ["EURUSD", "GBPUSD"],
            "specs": {"GBPUSD": {"symbol": "GBPUSD", "pip": 0.0001,
                                 "spread_pips": 2.3, "max_spread_pips": 6.5,
                                 "pip_value_per_lot": 8.01,
                                 "slippage_pips": 0.5}},
            "sizing": {"capital_initial": 10000.0, "risk_per_trade_pct": 1.0}}


def test_an_t4_s13_arm_and_symbol_columns(ui_env):
    ui_env.write_journal("s13_forward", _s13_rows(),
                         strategy_folder="S013_macd_fx")
    rows = ja.journal_closed_trades()
    assert len(rows) == 1
    r = rows[0]
    assert r["instance_id"] == "S013.EUR-JPY" and r["symbol"] == "EURJPY"
    assert r["arm"] == "OBSERVATION" and r["meta_json"]["arm"] == "OBSERVATION"
    assert r["strategy_id"] == "S013" and r["magic_number"] == 130013
    assert r["run_id"] == "s13_forward"
    assert r["open_time"] == "2026-09-03T21:00:00Z"
    assert r["net_pnl"] == -101.55 and r["pnl_r"] == -1.0155
    # Coût de bord depuis specs[EURJPY] (défaut helper : pip 1e-4, 2 pips, 0.5).
    edge = 2 * (2.0 * 0.0001 / 2 + 0.5 * 0.0001) * 100.0 / abs(181.459 - 179.97264)
    assert abs(r["meta_json"]["edge_cost_ccy"] - edge) < 1e-12
    opened = ja.journal_open_trades()
    assert len(opened) == 1 and opened[0]["instance_id"] == "S013.EUR-JPY"
    assert opened[0]["arm"] == "OBSERVATION"
    # Capital initial PAR bras, donc par instance (instruments = mapping).
    assert ja.journal_capital_initial() == {"S013.EUR-JPY": 10000.0}


def test_an_t4_alexg_ignores_shadow_and_decision_and_maps_reason(ui_env):
    ui_env.write_journal("alexg_paper", _alexg_rows(), params=_alexg_params(),
                         strategy_folder="S093_alexg_ai_judge")
    rep = ja.journal_report()
    a = rep["studies"]["alexg_paper"]
    assert a["rows"] == 5 and a["closed"] == 1 and a["open"] == 0
    assert a["chain_ok"] is True
    rows = ja.journal_closed_trades()
    assert len(rows) == 1
    r = rows[0]
    assert r["instance_id"] == "S093.GBP-USD" and r["strategy_id"] == "S093"
    assert r["arm"] == "MECH" and r["meta_json"]["arm"] == "MECH"
    assert r["source_ref"] == "MECH_GBPUSD_LONG_202608251000"
    assert r["signal_reason"] == "stop structurel"
    assert r["net_pnl"] == -105.0 and r["account_balance"] == 10000.0
    assert r["magic_number"] == 130093
    assert ja.journal_open_trades() == []
    # Capital par bras partagé entre symboles (liste d'instruments) : pas
    # attribuable par instance → inconnu (repli §3.3 côté analytics).
    assert ja.journal_capital_initial() == {}
    assert not [w for w in rep["warnings"] if "alexg" in w]


def test_pairing_on_trade_id_symbol_and_arm(ui_env):
    # Même trade_id sur deux bras : deux trades distincts, pas un doublon.
    rows = [
        _open("T1", "2026-09-04T00:00:00", arm="PRIMARY", symbol="EURUSD"),
        _open("T1", "2026-09-04T00:00:00", arm="OBSERVATION", symbol="EURUSD"),
        _close("T1", "2026-09-05T00:00:00", arm="PRIMARY", symbol="EURUSD",
               pnl=10.0),
        _close("T1", "2026-09-05T00:00:00", arm="OBSERVATION", symbol="EURUSD",
               pnl=-5.0),
    ]
    ui_env.write_journal("s20_forward", rows)
    got = ja.journal_closed_trades()
    assert sorted((r["arm"], r["net_pnl"]) for r in got) == [
        ("OBSERVATION", -5.0), ("PRIMARY", 10.0)]
    assert all(r["instance_id"] == "S020.EUR-USD" for r in got)


def test_close_without_open_and_duplicate_open_are_warned(ui_env):
    rows = [
        _close("ORPHAN", "2026-09-05T00:00:00"),
        _open("DUP", "2026-09-04T00:00:00", capital=1.0),
        _open("DUP", "2026-09-04T01:00:00", capital=2.0),
        _close("DUP", "2026-09-05T00:00:00"),
    ]
    ui_env.write_journal("gold_forward", rows)
    got = ja.journal_closed_trades()
    assert [r["source_ref"] for r in got] == ["DUP"]
    assert got[0]["account_balance"] == 2.0            # dernière occurrence
    warnings = ja.journal_report()["warnings"]
    assert any("CLOSE sans OPEN" in w and "ORPHAN" in w for w in warnings)
    assert any("en double" in w and "DUP" in w for w in warnings)


def test_rows_with_unreadable_bar_time_or_empty_trade_id_are_skipped(ui_env):
    rows = [
        _open("", "2026-09-04T00:00:00"),
        _open("X", "n'importe quoi"),
        _open("OK", "2026-09-04T00:00:00"),
        _close("OK", "2026-09-05T00:00:00"),
    ]
    ui_env.write_journal("gold_forward", rows)
    assert [r["source_ref"] for r in ja.journal_closed_trades()] == ["OK"]
    warnings = ja.journal_report()["warnings"]
    assert any("trade_id vide" in w for w in warnings)
    assert any("bar_time illisible" in w for w in warnings)


def test_symbol_unknown_when_no_column_and_no_params_symbol(ui_env):
    params = {"study": "gold_forward", "timeframe": "H1",
              "sizing": {"capital_initial": 10000.0}}
    ui_env.write_journal("gold_forward", _gold_rows(), params=params)
    assert ja.journal_closed_trades() == []
    warnings = ja.journal_report()["warnings"]
    assert any("symbole inconnu" in w for w in warnings)


def test_closed_rows_sorted_by_close_time_then_source_ref(ui_env):
    rows = [
        _open("B", "2026-09-01T00:00:00"), _close("B", "2026-09-03T00:00:00"),
        _open("A", "2026-09-01T00:00:00"), _close("A", "2026-09-03T00:00:00"),
        _open("C", "2026-09-01T00:00:00"), _close("C", "2026-09-02T00:00:00"),
    ]
    ui_env.write_journal("gold_forward", rows)
    assert [r["source_ref"] for r in ja.journal_closed_trades()] == ["C", "A", "B"]


def test_read_study_with_wrong_column_count_line_is_skipped_and_flagged(ui_env):
    path = ui_env.write_journal("gold_forward", _gold_rows())
    raw = path.read_bytes() + b"garbage,line\n"
    path.write_bytes(raw)
    rep = ja.journal_report()
    assert rep["studies"]["gold_forward"]["chain_ok"] is False
    assert rep["studies"]["gold_forward"]["closed"] == 2
    assert any("colonnes" in w for w in rep["warnings"])


def test_seed_ledger_helper_records_open_and_closed_trades(ui_env):
    """Le helper conftest ``seed_ledger`` (partagé avec test_server_analytics)
    accepte instances, modes, devises, zéros et positions ouvertes."""
    from core.ledger import Ledger
    path = ui_env.db / "ledger.db"
    ids = ui_env.seed_ledger(path, [
        {"net": 100.0},
        {"net": 0.0, "instance_id": "S013.EUR-JPY", "symbol": "EURJPY"},
        {"net": -20.0, "mode": "BACKTEST", "currency": "EUR"},
        {"close_time": None, "mode": "LIVE"},
    ])
    assert len(ids) == 4
    with Ledger(path) as lg:
        closed = lg.closed_trades()
        assert len(closed) == 3
        assert {r["net_pnl"] for r in closed} == {100.0, 0.0, -20.0}
        assert {r["currency"] for r in closed} == {"CHF", "EUR"}
        assert {r["mode"] for r in closed} == {"PAPER", "BACKTEST"}
        n_open = lg._conn.execute(
            "SELECT COUNT(*) FROM trades WHERE close_time IS NULL").fetchone()[0]
        assert n_open == 1
