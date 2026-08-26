"""
Tests du pas de mesure — barres synthétiques, juge injecté, sans MT5 ni CLI.

    python -m pytest studies/macd_ai_paper/test_paper_step.py -q

Ce qui est vérifié, et pourquoi :

  (a) IDEMPOTENCE — deux passages sur les mêmes données n'ajoutent rien ET ne
      rappellent pas le juge (un juge rappelé = décisions dupliquées + coût).
  (b) APPEND-ONLY — réécriture/troncature détectée, refus sans écriture.
  (c) SCELLÉ — hash faux refusé ; le hash du dépôt correspond à la constante.
  (d) PANNE CLAUDE — juge à None : bras IA N/A, MECH et RND ouvrent quand
      même. Une panne d'IA ne fausse jamais les témoins.
  (e) CONVENTIONS MOTEUR — gap payé à l'ouverture, SL prime sur TP.
  (f) COMPTES — taille IA fractionnée (0,5 -> 50 risqués), SL/TP resserrés
      appliqués, capital ajusté à chaque sortie, clamp des bornes.
  (g) RND — tirage déterministe, taux = takes/décisions recalculé.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.contracts.strategy import Side, Signal                  # noqa: E402
from studies.macd_ai_paper.ai_judge import extract_json_object    # noqa: E402
from studies.macd_ai_paper.paper_step import (                    # noqa: E402
    JournalError, Paths, SealError, clamp_decision, load_sealed_params,
    read_journal, rnd_draw, run_step, sha256_file,
)

SPREAD_PIPS = 20.0
PIP = 0.01
EDGE = SPREAD_PIPS * PIP / 2.0          # 0.10 par extrémité

PARAMS = {
    "strategy_id": "s12_prt_macd_meanrev",
    "instruments": ["IDX"],
    "specs": {"IDX": {"symbol": "IDX", "pip": PIP, "spread_pips": SPREAD_PIPS,
                      "max_spread_pips": 60.0, "pip_value_per_lot": 1.0,
                      "slippage_pips": 0.0}},
    "engine": {"max_positions": 1, "cooldown_bars": 2, "cb_losses": 3,
               "cb_cooldown_bars": 24, "max_hold_bars": None},
    "sizing": {"capital_initial": 10000.0, "risk_per_trade_pct": 1.0},
    "ai": {"timeout_s": 5, "retries": 1,
           "bounds": {"size_min": 0.0, "size_max": 1.0,
                      "sl_adjust_min": 0.5, "sl_adjust_max": 1.0,
                      "tp_adjust_min": 0.5, "tp_adjust_max": 1.0}},
    "random_arm": {"seed": 20260816, "default_take_rate": 1.0},
    "control": {"draws": 200, "seed": 20260816},
    "stop_rules": {"fail_ai": {"min_decisions": 40, "percentile_below": 80},
                   "fail_base": {"min_signals": 40, "cum_r_nocost_below": 0.0},
                   "time": {"months": 12, "min_decisions": 40}},
}

TAKE_ALL = {"decision": "take", "size": 1.0, "sl_adjust": 1.0,
            "tp_adjust": 1.0, "reason": "test take"}
SKIP_ALL = {"decision": "skip", "size": 0.0, "sl_adjust": 1.0,
            "tp_adjust": 1.0, "reason": "test skip"}


def bars(rows, start="2026-08-17"):
    idx = pd.date_range(start, periods=len(rows), freq="1D")
    a = np.asarray(rows, dtype=float)
    return pd.DataFrame(
        {"open": a[:, 0], "high": a[:, 1], "low": a[:, 2], "close": a[:, 3]},
        index=idx)


def flat(n, price=100.0, start="2026-08-17"):
    return bars([(price, price + 0.2, price - 0.2, price)] * n, start)


def sig_at(df, i, sl=1.5, tp=6.0):
    entry = float(df["close"].iloc[i])
    return {df.index[i]: Signal(timestamp=df.index[i], symbol="IDX",
                                side=Side.LONG, entry=entry,
                                stop=entry - sl, target=entry + tp,
                                reason="test")}


def no_signals(df):
    return {}


class CountingJudge:
    def __init__(self, decision):
        self.decision = decision
        self.calls = 0

    def __call__(self, dossier):
        self.calls += 1
        return self.decision


@pytest.fixture
def paths(tmp_path):
    return Paths(str(tmp_path))


def seal_then_extend(paths, df_seal, df_full, signal_fn, judge):
    s0 = run_step({"IDX": df_seal}, PARAMS, paths, {"IDX": no_signals},
                  judge)
    assert s0["first_pass"]
    return run_step({"IDX": df_full}, PARAMS, paths, {"IDX": signal_fn},
                    judge)


# ── (a) idempotence, y compris du juge ───────────────────────────────────────

def test_idempotence_et_juge_jamais_rappele(paths):
    df_seal = flat(10)
    df_full = flat(15)
    sigs = sig_at(df_full, 11)
    judge = CountingJudge(TAKE_ALL)

    st1 = seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)
    assert st1["opened_this_pass"] == 3          # MECH + AI + RND
    assert judge.calls == 1
    n_lines = len(read_journal(paths.journal))
    sha1 = sha256_file(paths.journal)

    st2 = run_step({"IDX": df_full}, PARAMS, paths,
                   {"IDX": lambda d: sigs}, judge)
    assert st2["opened_this_pass"] == 0 and st2["closed_this_pass"] == 0
    assert judge.calls == 1                      # PAS de rappel du juge
    assert len(read_journal(paths.journal)) == n_lines
    assert sha256_file(paths.journal) == sha1


def test_premier_passage_ne_consomme_aucun_signal_historique(paths):
    df = flat(12)
    sigs = sig_at(df, 5)
    judge = CountingJudge(TAKE_ALL)
    run_step({"IDX": df}, PARAMS, paths, {"IDX": lambda d: sigs}, judge)
    st2 = run_step({"IDX": df}, PARAMS, paths, {"IDX": lambda d: sigs}, judge)
    assert st2["opened_this_pass"] == 0
    assert judge.calls == 0
    assert [r for r in read_journal(paths.journal)
            if r["event"] == "OPEN"] == []


# ── (b) append-only ──────────────────────────────────────────────────────────

def test_reecriture_du_journal_detectee_et_refus(paths):
    df_seal, df_full = flat(10), flat(15)
    sigs = sig_at(df_full, 11)
    judge = CountingJudge(TAKE_ALL)
    seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)

    with open(paths.journal, "r", encoding="utf-8") as f:
        txt = f.read()
    assert "OPEN" in txt
    with open(paths.journal, "w", encoding="utf-8") as f:
        f.write(txt.replace("OPEN", "0PEN", 1))

    before = sha256_file(paths.journal)
    with pytest.raises(JournalError):
        run_step({"IDX": flat(20)}, PARAMS, paths,
                 {"IDX": lambda d: sigs}, judge)
    assert sha256_file(paths.journal) == before   # refus SANS écriture


def test_troncature_et_suppression_detectees(paths):
    df_seal, df_full = flat(10), flat(15)
    sigs = sig_at(df_full, 11)
    judge = CountingJudge(TAKE_ALL)
    seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)

    with open(paths.journal, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(paths.journal, "w", encoding="utf-8") as f:
        f.writelines(lines[:-1])
    with pytest.raises(JournalError):
        run_step({"IDX": flat(20)}, PARAMS, paths,
                 {"IDX": lambda d: sigs}, judge)

    os.remove(paths.journal)
    with pytest.raises(JournalError):
        run_step({"IDX": flat(20)}, PARAMS, paths,
                 {"IDX": lambda d: sigs}, judge)


# ── (c) scellé ───────────────────────────────────────────────────────────────

def test_hash_correct_charge_hash_faux_refuse(tmp_path):
    p = tmp_path / "params.json"
    p.write_text(json.dumps(PARAMS), encoding="utf-8")
    good = sha256_file(str(p))
    loaded = load_sealed_params(str(p), good)
    assert loaded["sizing"]["capital_initial"] == 10000.0

    tampered = dict(PARAMS)
    tampered["sizing"] = {"capital_initial": 10000.0, "risk_per_trade_pct": 2.0}
    p.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(SealError):
        load_sealed_params(str(p), good)


def test_hash_du_vrai_fichier_scelle_correspond():
    """params.json ↔ constante de run_paper.py. Si ce test casse, quelqu'un a
    touché l'un sans l'autre — l'événement que le dispositif rend visible."""
    from studies.macd_ai_paper.run_paper import PARAMS_PATH, PARAMS_SHA256
    load_sealed_params(PARAMS_PATH, PARAMS_SHA256)   # ne lève pas


# ── (d) panne claude : bras IA N/A, témoins intacts ─────────────────────────

def test_panne_claude_ia_na_temoins_continuent(paths):
    df_seal, df_full = flat(10), flat(15)
    sigs = sig_at(df_full, 11)
    judge = CountingJudge(None)                  # panne simulée

    st = seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)
    assert st["opened_this_pass"] == 2           # MECH + RND, pas d'IA
    j = read_journal(paths.journal)
    opens = {r["arm"] for r in j if r["event"] == "OPEN"}
    assert opens == {"MECH", "RND"}
    na = [r for r in j if r["event"] == "DECISION" and r["arm"] == "AI"]
    assert len(na) == 1 and na[0]["decision"] == "na"
    assert st["ai_stats"] == {"n_decisions": 0, "n_takes": 0, "n_na": 1}
    # le taux RND n'est pas contaminé par la panne (défaut 1.0 -> take)
    rnd = [r for r in j if r["event"] == "DECISION" and r["arm"] == "RND"]
    assert rnd[0]["decision"] == "take"


def test_skip_ia_pas_de_position_shadow_vit(paths):
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL (IA skip)
        (100.0, 100.4, 98.0, 99.0),           # 12 : SL du shadow touché
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11)
    judge = CountingJudge(SKIP_ALL)

    st = seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)
    j = read_journal(paths.journal)
    assert not [r for r in j if r["event"] == "OPEN" and r["arm"] == "AI"]
    assert st["ai_stats"]["n_decisions"] == 1
    assert st["ai_stats"]["n_takes"] == 0
    shadow = [r for r in j if r["event"] == "SHADOW_CLOSE"]
    assert len(shadow) == 1                      # le contrefactuel existe
    assert st["shadow"]["n_closed"] == 1


# ── (e) conventions moteur ───────────────────────────────────────────────────

def test_stop_saute_par_gap_execute_a_l_ouverture(paths):
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL, entrée 100
        (97.0, 97.5, 96.0, 96.5),             # 12 : gap sous le stop 98.5
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, sl=1.5, tp=6.0)
    judge = CountingJudge(TAKE_ALL)

    st = seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)
    assert st["closed_this_pass"] == 3           # MECH + AI + RND
    for arm in ("MECH", "AI", "RND"):
        row = [r for r in read_journal(paths.journal)
               if r["event"] == "CLOSE" and r["arm"] == arm][0]
        assert row["exit_reason"] == "SL"
        assert float(row["exit_price"]) == pytest.approx(97.0)   # l'ouverture

        entry = 100.0 + EDGE
        risk = entry - 98.5
        expected_r = ((97.0 - entry) - EDGE) / risk
        assert float(row["pnl_r"]) == pytest.approx(expected_r, abs=1e-4)
        assert expected_r < -1.0                 # le gap coûte PLUS qu'un R


def test_sl_et_tp_meme_barre_le_stop_l_emporte(paths):
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL
        (100.0, 106.5, 98.4, 102.0),          # 12 : traverse SL ET TP
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, sl=1.5, tp=6.0)
    judge = CountingJudge(TAKE_ALL)

    seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)
    row = [r for r in read_journal(paths.journal)
           if r["event"] == "CLOSE" and r["arm"] == "MECH"][0]
    assert row["exit_reason"] == "SL"
    assert float(row["exit_price"]) == pytest.approx(98.5)   # pas de gap


# ── (f) comptes : taille fractionnée, niveaux resserrés, clamp ──────────────

def test_taille_ia_fractionnee_et_niveaux_resserres(paths):
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL entrée 100
        (100.5, 103.2, 100.2, 102.5),         # 12 : le TP IA resserré (103.1)
    ]                                          #      est touché, TP base 106 non
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, sl=1.5, tp=6.0)
    half = {"decision": "take", "size": 0.5, "sl_adjust": 0.8,
            "tp_adjust": 0.5, "reason": "test demi-taille"}
    judge = CountingJudge(half)

    st = seal_then_extend(paths, df_seal, df_full, lambda d: sigs, judge)
    j = read_journal(paths.journal)
    ai_open = [r for r in j if r["event"] == "OPEN" and r["arm"] == "AI"][0]
    # risque monétaire = 0,5 % de 10 000 = 50 (RiskLayer, base 1 %)
    assert float(ai_open["risk_ccy"]) == pytest.approx(50.0, rel=1e-6)
    entry = 100.0 + EDGE
    # distances mesurées depuis l'entrée EXÉCUTÉE (conv. moteur, adjust=1 ->
    # niveaux stratégie tels quels)
    assert float(ai_open["stop_price"]) == pytest.approx(
        entry - (entry - 98.5) * 0.8)
    assert float(ai_open["target_price"]) == pytest.approx(
        entry + (106.0 - entry) * 0.5)

    ai_close = [r for r in j if r["event"] == "CLOSE" and r["arm"] == "AI"][0]
    assert ai_close["exit_reason"] == "TP"
    # capital IA ajusté du P&L ; MECH toujours en position (TP 106 pas touché)
    assert st["arms"]["AI"]["capital"] == pytest.approx(
        10000.0 + float(ai_close["pnl_ccy"]), abs=0.01)
    assert st["arms"]["MECH"]["open_positions"]


def test_clamp_des_bornes():
    b = PARAMS["ai"]["bounds"]
    d = clamp_decision({"decision": "TAKE", "size": 7, "sl_adjust": 0.1,
                        "tp_adjust": 2.0, "reason": "x" * 500}, b)
    assert d == {"decision": "take", "size": 1.0, "sl_adjust": 0.5,
                 "tp_adjust": 1.0, "reason": "x" * 300}
    d2 = clamp_decision({"decision": "nonsense", "size": "abc"}, b)
    assert d2["decision"] == "skip" and d2["size"] == 0.0
    assert d2["sl_adjust"] == 1.0 and d2["tp_adjust"] == 1.0


def test_extract_json_object_tolere_texte_autour():
    txt = 'Voici :\n```json\n{"decision":"take","size":0.7}\n``` merci'
    assert extract_json_object(txt) == {"decision": "take", "size": 0.7}
    assert extract_json_object("aucun json ici") is None


# ── (g) bras aléatoire ───────────────────────────────────────────────────────

def test_rnd_deterministe_et_taux_recalcule(paths):
    ts = pd.Timestamp("2026-08-20")
    assert rnd_draw(20260816, "IDX", ts) == rnd_draw(20260816, "IDX", ts)
    assert rnd_draw(20260816, "IDX", ts) != rnd_draw(20260816, "OTH", ts)

    # Après 1 décision IA skip, le taux RND doit passer à 0 -> RND skip aussi.
    df_seal = flat(10)
    df_a = flat(15)
    sigs_a = sig_at(df_a, 11)
    judge = CountingJudge(SKIP_ALL)
    seal_then_extend(paths, df_seal, df_a, lambda d: sigs_a, judge)

    df_b = flat(20)
    sigs_b = {}
    sigs_b.update(sig_at(df_b, 16))
    run_step({"IDX": df_b}, PARAMS, paths, {"IDX": lambda d: sigs_b}, judge)
    j = read_journal(paths.journal)
    rnd = [r for r in j if r["event"] == "DECISION" and r["arm"] == "RND"]
    assert rnd[1]["decision"] == "skip"          # taux 0/1 = 0
    assert "taux=0.000" in rnd[1]["reason"]
