"""
Tests du pas de mesure de l'essai fxalexg+IA.

Ils protègent trois choses, dans cet ordre d'importance :
  1. le SCELLÉ (le hash du vrai params.json committé) ;
  2. l'INTÉGRITÉ du journal (toute retouche doit être détectée) ;
  3. l'IDEMPOTENCE (un second passage n'ajoute rien et ne rappelle pas le juge)
     — c'est elle qui rend la cadence horaire de l'usine inoffensive.

Aucun test n'appelle le CLI `claude` : le juge est injecté.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.contracts.strategy import Side, Signal          # noqa: E402
from studies.alexg_paper import paper_step as ps          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# Le scellé
# ─────────────────────────────────────────────────────────────────────────────

def test_hash_du_vrai_fichier_scelle_correspond():
    """Si ce test casse, params.json a bougé : l'essai n'est plus le même.
    Ne PAS mettre à jour le hash pour faire passer le test — c'est
    exactement ce que le scellé interdit (PROTOCOL.md § 1)."""
    got = ps.sha256_file(os.path.join(HERE, "params.json"))
    assert got == ps.PARAMS_SHA256


def test_params_scelles_chargeables_et_coherents():
    p = ps.load_sealed_params(os.path.join(HERE, "params.json"))
    assert p["timeframe"] == "H1"
    assert len(p["instruments"]) == 26
    # toute paire déclarée doit avoir sa spec figée
    assert set(p["specs"]) == set(p["instruments"])
    # set-and-forget : les niveaux sont plombés à 1.0 (PROTOCOL.md § 0ter)
    b = p["ai"]["bounds"]
    assert b["sl_adjust_min"] == b["sl_adjust_max"] == 1.0
    assert b["tp_adjust_min"] == b["tp_adjust_max"] == 1.0


def test_scelle_viole_leve():
    with pytest.raises(ps.SealError):
        ps.load_sealed_params(os.path.join(HERE, "params.json"), "0" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Bornes et conventions d'exécution
# ─────────────────────────────────────────────────────────────────────────────

BOUNDS = {"size_min": 0.0, "size_max": 1.0, "sl_adjust_min": 1.0,
          "sl_adjust_max": 1.0, "tp_adjust_min": 1.0, "tp_adjust_max": 1.0}


def test_clamp_ramene_dans_les_bornes():
    d = ps.clamp_decision(
        {"decision": "take", "size": 4.2, "sl_adjust": 0.1, "tp_adjust": 9.0,
         "reason": "x"}, BOUNDS)
    assert d["size"] == 1.0
    assert d["sl_adjust"] == 1.0 and d["tp_adjust"] == 1.0


def test_decision_illisible_vaut_skip():
    """Une IA qui répond n'importe quoi ne doit jamais ouvrir de position."""
    for raw in ({"decision": "peut-être"}, {"decision": None}, {}):
        assert ps.clamp_decision(raw, BOUNDS)["decision"] == "skip"


def test_taille_non_numerique_vaut_zero():
    d = ps.clamp_decision({"decision": "take", "size": "beaucoup"}, BOUNDS)
    assert d["size"] == 0.0


def test_sortie_stop_prime_sur_cible_dans_la_meme_barre():
    pos = {"side": "LONG", "stop_price": 99.0, "target_price": 101.0}
    bar = {"open": 100.0, "high": 101.5, "low": 98.5, "close": 100.0}
    price, reason = ps.check_exit(pos, bar)
    assert reason == "SL" and price == 99.0


def test_gap_est_paye_a_l_ouverture():
    """Une barre qui ouvre sous le stop exécute à l'ouverture, pas au stop."""
    pos = {"side": "LONG", "stop_price": 99.0, "target_price": 101.0}
    bar = {"open": 97.0, "high": 97.5, "low": 96.0, "close": 96.5}
    price, reason = ps.check_exit(pos, bar)
    assert reason == "SL" and price == 97.0


def test_la_cible_ne_profite_pas_du_gap():
    pos = {"side": "LONG", "stop_price": 99.0, "target_price": 101.0}
    bar = {"open": 103.0, "high": 103.5, "low": 102.5, "close": 103.0}
    price, reason = ps.check_exit(pos, bar)
    assert reason == "TP" and price == 101.0


def test_tirage_aleatoire_deterministe():
    t = pd.Timestamp("2026-08-22 10:00")
    a = ps.rnd_draw(20260822, "GBPJPY", t)
    b = ps.rnd_draw(20260822, "GBPJPY", t)
    c = ps.rnd_draw(20260822, "EURUSD", t)
    assert a == b and a != c and 0.0 <= a < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Journal à chaîne de hachage
# ─────────────────────────────────────────────────────────────────────────────

def test_journal_retouche_est_detecte(tmp_path):
    j = str(tmp_path / "journal.csv")
    ps.init_journal(j)
    ps.append_journal(j, [{"event": "DECISION", "arm": "AI", "symbol": "EURUSD",
                           "decision": "take", "reason": "r1"}])
    n, sha = ps.append_journal(j, [{"event": "DECISION", "arm": "AI",
                                    "symbol": "EURUSD", "decision": "skip",
                                    "reason": "r2"}])
    ps.verify_journal(j, {"journal_bytes": n, "journal_sha256": sha})  # sain

    txt = open(j, encoding="utf-8").read().replace("take", "skip")
    open(j, "w", encoding="utf-8", newline="").write(txt)
    with pytest.raises(ps.JournalError):
        ps.verify_journal(j, {"journal_bytes": n, "journal_sha256": sha})


def test_journal_tronque_est_detecte(tmp_path):
    j = str(tmp_path / "journal.csv")
    ps.init_journal(j)
    n, sha = ps.append_journal(j, [{"event": "OPEN", "arm": "MECH",
                                    "symbol": "EURUSD"}])
    with open(j, "rb") as f:
        raw = f.read()
    with open(j, "wb") as f:
        f.write(raw[: len(raw) // 2])
    with pytest.raises(ps.JournalError):
        ps.verify_journal(j, {"journal_bytes": n, "journal_sha256": sha})


def test_journal_supprime_est_detecte(tmp_path):
    j = str(tmp_path / "journal.csv")
    with pytest.raises(ps.JournalError):
        ps.verify_journal(j, {"journal_bytes": 512, "journal_sha256": "x"})


# ─────────────────────────────────────────────────────────────────────────────
# Le pas complet, sur barres synthétiques et juge injecté
# ─────────────────────────────────────────────────────────────────────────────

SYM = "EURUSD"


def _params(tmp_path):
    p = ps.load_sealed_params(os.path.join(HERE, "params.json"))
    p = json.loads(json.dumps(p))          # copie profonde
    p["instruments"] = [SYM]
    p["specs"] = {SYM: p["specs"][SYM]}
    return p


def _bars(n=60, start="2026-08-01 00:00", drift=-0.0002):
    idx = pd.date_range(start, periods=n, freq="h")
    base = [1.1000 + i * drift for i in range(n)]
    return pd.DataFrame({"open": base,
                         "high": [b + 0.0010 for b in base],
                         "low": [b - 0.0010 for b in base],
                         "close": [b - 0.0001 for b in base]}, index=idx)


def _signal_at(df, k, side=Side.SHORT):
    """Un signal unique sur la barre k, niveaux cohérents avec le contrat."""
    ts = df.index[k]
    entry = float(df["close"].iloc[k])
    if side == Side.SHORT:
        stop, target = entry + 0.0030, entry - 0.0060
    else:
        stop, target = entry - 0.0030, entry + 0.0060
    return {ts: Signal(timestamp=ts, symbol=SYM, side=side, entry=entry,
                       stop=stop, target=target, reason="test")}


def test_premier_passage_pose_le_scelle_sans_journaliser_l_historique(tmp_path):
    """L'essai est PROSPECTIF : le premier passage ne rejoue rien."""
    params = _params(tmp_path)
    paths = ps.Paths(str(tmp_path))
    df = _bars()
    st = ps.run_step({SYM: df}, params, paths,
                     {SYM: lambda d: _signal_at(d, 10)}, lambda dossier: None)
    assert st["first_pass"] is True
    assert st["opened_this_pass"] == 0
    assert len(ps.read_journal(paths.journal)) == 0


def test_second_passage_traite_le_signal_et_ouvre_les_bras(tmp_path):
    params = _params(tmp_path)
    paths = ps.Paths(str(tmp_path))
    df = _bars()
    ps.run_step({SYM: df}, params, paths, {SYM: lambda d: {}},
                lambda dossier: None)

    df2 = _bars(n=70)
    sig = _signal_at(df2, 62)
    calls = []

    def judge(dossier):
        calls.append(dossier)
        return {"decision": "take", "size": 0.5, "reason": "ok"}

    st = ps.run_step({SYM: df2}, params, paths, {SYM: lambda d: sig}, judge)
    rows = ps.read_journal(paths.journal)
    events = {(r["event"], r["arm"]) for r in rows}
    assert ("SHADOW_OPEN", "SHADOW") in events
    assert ("OPEN", "MECH") in events
    assert ("DECISION", "AI") in events
    assert ("OPEN", "AI") in events
    assert ("DECISION", "RND") in events
    assert len(calls) == 1
    assert st["ai_stats"]["n_takes"] == 1
    # le dossier soumis au juge ne doit pas trahir l'instrument
    assert SYM not in json.dumps(calls[0])


def test_idempotence_le_juge_n_est_pas_rappele(tmp_path):
    """Deux passages sur les mêmes données : rien ne s'ajoute, et surtout
    aucun nouvel appel au juge (c'est ce qui rend la cadence horaire de
    l'usine gratuite)."""
    params = _params(tmp_path)
    paths = ps.Paths(str(tmp_path))
    ps.run_step({SYM: _bars()}, params, paths, {SYM: lambda d: {}},
                lambda dossier: None)

    df2 = _bars(n=70)
    sig = _signal_at(df2, 62)
    calls = []

    def judge(dossier):
        calls.append(1)
        return {"decision": "take", "size": 1.0, "reason": "ok"}

    ps.run_step({SYM: df2}, params, paths, {SYM: lambda d: sig}, judge)
    n_rows = len(ps.read_journal(paths.journal))
    n_calls = len(calls)

    ps.run_step({SYM: df2}, params, paths, {SYM: lambda d: sig}, judge)
    assert len(ps.read_journal(paths.journal)) == n_rows
    assert len(calls) == n_calls


def test_panne_du_juge_n_affecte_pas_les_temoins(tmp_path):
    """Le juge tombe : bras IA en N/A, MECH et RND continuent."""
    params = _params(tmp_path)
    paths = ps.Paths(str(tmp_path))
    ps.run_step({SYM: _bars()}, params, paths, {SYM: lambda d: {}},
                lambda dossier: None)

    df2 = _bars(n=70)
    sig = _signal_at(df2, 62)
    st = ps.run_step({SYM: df2}, params, paths, {SYM: lambda d: sig},
                     lambda dossier: None)
    rows = ps.read_journal(paths.journal)
    ai_dec = [r for r in rows if r["event"] == "DECISION" and r["arm"] == "AI"]
    assert ai_dec and ai_dec[0]["decision"] == "na"
    assert st["ai_stats"]["n_na"] == 1
    assert st["ai_stats"]["n_decisions"] == 0
    assert not [r for r in rows if r["event"] == "OPEN" and r["arm"] == "AI"]
    assert [r for r in rows if r["event"] == "OPEN" and r["arm"] == "MECH"]


def test_instrument_absent_ne_bouge_pas_son_curseur(tmp_path):
    """MT5 partiel : la paire manquante est sautée, pas avancée."""
    params = _params(tmp_path)
    paths = ps.Paths(str(tmp_path))
    ps.run_step({SYM: _bars()}, params, paths, {SYM: lambda d: {}},
                lambda dossier: None)
    before = ps.load_state(paths.state)["symbols"][SYM]["last_bar_time"]
    ps.run_step({}, params, paths, {SYM: lambda d: {}}, lambda dossier: None)
    after = ps.load_state(paths.state)["symbols"][SYM]["last_bar_time"]
    assert before == after


def test_journal_altere_bloque_tout_nouveau_passage(tmp_path):
    """Après retouche, le pas refuse de tourner — et n'écrit rien."""
    params = _params(tmp_path)
    paths = ps.Paths(str(tmp_path))
    ps.run_step({SYM: _bars()}, params, paths, {SYM: lambda d: {}},
                lambda dossier: None)
    df2 = _bars(n=70)
    ps.run_step({SYM: df2}, params, paths, {SYM: lambda d: _signal_at(d, 62)},
                lambda dossier: {"decision": "skip", "size": 0.0})

    txt = open(paths.journal, encoding="utf-8").read().replace("skip", "take")
    open(paths.journal, "w", encoding="utf-8", newline="").write(txt)
    with pytest.raises(ps.JournalError):
        ps.run_step({SYM: _bars(n=80)}, params, paths,
                    {SYM: lambda d: {}}, lambda dossier: None)
