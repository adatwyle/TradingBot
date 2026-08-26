"""
Tests du pas de mesure — sur barres synthétiques, sans MT5.

    python -m pytest studies/gold_forward/test_forward_step.py -q

Ce qui est vérifié, et pourquoi c'est ça et pas autre chose :

  (a) IDEMPOTENCE — deux passages sur les mêmes données n'ajoutent rien.
      Sans elle, une exécution horaire fabriquerait des trades dupliqués et le
      journal ne compterait plus rien.
  (b) APPEND-ONLY — une réécriture du journal est détectée et le pas refuse de
      tourner sans rien écrire. C'est la propriété qui rend le test opposable.
  (c) SCELLÉ — un fichier de paramètres dont le hash ne correspond pas est
      refusé. Critère d du protocole : aucun paramètre ne bouge en route.
  (d) GAP — un stop sauté par un gap est exécuté à l'OUVERTURE de la barre
      (pire que le stop), comme le moteur commun. C'est le correctif 66668d1
      qui a changé la lecture de s11 : le forward doit payer les gaps pareil.

Plus deux contrôles de conformité moteur : préséance SL sur TP dans la même
barre, et concordance du P&L avec le coût de bord payé deux fois.
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
from studies.gold_forward.forward_step import (                    # noqa: E402
    JournalError, Paths, SealError, load_sealed_params,
    read_journal, run_step, sha256_file,
)

SPREAD_PIPS = 20.0
PIP = 0.01
EDGE = SPREAD_PIPS * PIP / 2.0          # 0.10 par extrémité

PARAMS = {
    "instrument": "XAUUSD",
    "spec": {"symbol": "XAUUSD", "pip": PIP, "spread_pips": SPREAD_PIPS,
             "max_spread_pips": 60.0, "pip_value_per_lot": 1.0,
             "slippage_pips": 0.0},
    "engine": {"max_positions": 1, "cooldown_bars": 2, "cb_losses": 3,
               "cb_cooldown_bars": 24, "max_hold_bars": None},
    "sizing": {"capital_initial": 10000.0, "risk_per_trade_pct": 1.0},
    "stop_rules": {"fail": {"min_trades": 40, "percentile_below": 20},
                   "success": {"min_trades": 100, "percentile_at_least": 95},
                   "time": {"months": 12, "min_trades": 40}},
}


def bars(rows, start="2026-08-17 00:00"):
    """rows = [(open, high, low, close), ...] -> DataFrame H1."""
    idx = pd.date_range(start, periods=len(rows), freq="1h")
    a = np.asarray(rows, dtype=float)
    return pd.DataFrame(
        {"open": a[:, 0], "high": a[:, 1], "low": a[:, 2], "close": a[:, 3]},
        index=idx)


def flat(n, price=100.0, start="2026-08-17 00:00"):
    return bars([(price, price + 0.2, price - 0.2, price)] * n, start)


def sig_at(df, i, side=Side.LONG, sl=1.5, tp=6.0):
    """Un signal injecté à la barre i : entrée au close, stop/cible en prix."""
    entry = float(df["close"].iloc[i])
    if side == Side.LONG:
        stop, target = entry - sl, entry + tp
    else:
        stop, target = entry + sl, entry - tp
    return {df.index[i]: Signal(timestamp=df.index[i], symbol="XAUUSD",
                                side=side, entry=entry, stop=stop,
                                target=target, reason="test")}


def no_signals(df):
    return {}


@pytest.fixture
def paths(tmp_path):
    return Paths(str(tmp_path))


def seal_then_extend(paths, df_seal, df_full, signal_fn):
    """Premier passage (pose du scellé, aucun trade), puis passage sur les
    données étendues — le schéma de tout test ci-dessous."""
    s0 = run_step(df_seal, PARAMS, paths, no_signals)
    assert s0["first_pass"] and s0["n_closed_total"] == 0
    return run_step(df_full, PARAMS, paths, signal_fn)


# ─────────────────────────────────────────────────────────────────────────────
# (a) idempotence
# ─────────────────────────────────────────────────────────────────────────────

def test_idempotence_meme_donnees_aucun_ajout(paths):
    df_seal = flat(10)
    df_full = flat(15)                       # 5 barres nouvelles, dont 1 signal
    sigs = sig_at(df_full, 11)
    fn = lambda df: sigs                     # noqa: E731

    st1 = seal_then_extend(paths, df_seal, df_full, fn)
    assert st1["opened_this_pass"] == 1
    n_lines = len(read_journal(paths.journal))
    sha1 = sha256_file(paths.journal)

    # Deuxième passage, mêmes données : rien ne doit bouger.
    st2 = run_step(df_full, PARAMS, paths, fn)
    assert st2["opened_this_pass"] == 0 and st2["closed_this_pass"] == 0
    assert len(read_journal(paths.journal)) == n_lines
    assert sha256_file(paths.journal) == sha1

    # Troisième passage, toujours identique.
    st3 = run_step(df_full, PARAMS, paths, fn)
    assert st3["opened_this_pass"] == 0
    assert sha256_file(paths.journal) == sha1


def test_premier_passage_ne_consomme_aucun_signal_historique(paths):
    """Le scellé est prospectif : un signal ANTÉRIEUR au premier passage ne
    doit jamais entrer au journal."""
    df = flat(12)
    sigs = sig_at(df, 5)                      # signal dans le passé
    st = run_step(df, PARAMS, paths, lambda d: sigs)
    assert st["first_pass"]
    st2 = run_step(df, PARAMS, paths, lambda d: sigs)
    assert st2["opened_this_pass"] == 0
    assert [r for r in read_journal(paths.journal) if r["event"] == "OPEN"] == []


# ─────────────────────────────────────────────────────────────────────────────
# (b) append-only
# ─────────────────────────────────────────────────────────────────────────────

def test_reecriture_du_journal_detectee_et_refus(paths):
    df_seal = flat(10)
    df_full = flat(15)
    sigs = sig_at(df_full, 11)
    seal_then_extend(paths, df_seal, df_full, lambda d: sigs)

    # Falsification : on améliore un chiffre dans une ligne passée.
    with open(paths.journal, "r", encoding="utf-8") as f:
        txt = f.read()
    assert "OPEN" in txt
    with open(paths.journal, "w", encoding="utf-8") as f:
        f.write(txt.replace("OPEN", "OPEN".replace("O", "0"), 1))

    before = sha256_file(paths.journal)
    with pytest.raises(JournalError):
        run_step(flat(20), PARAMS, paths, lambda d: sigs)
    # Refus SANS écriture : le fichier falsifié est resté tel quel (preuve).
    assert sha256_file(paths.journal) == before


def test_troncature_du_journal_detectee(paths):
    df_seal = flat(10)
    df_full = flat(15)
    sigs = sig_at(df_full, 11)
    seal_then_extend(paths, df_seal, df_full, lambda d: sigs)

    with open(paths.journal, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(paths.journal, "w", encoding="utf-8") as f:
        f.writelines(lines[:-1])              # on efface le dernier trade

    with pytest.raises(JournalError):
        run_step(flat(20), PARAMS, paths, lambda d: sigs)


def test_suppression_du_journal_detectee(paths):
    df_seal = flat(10)
    df_full = flat(15)
    sigs = sig_at(df_full, 11)
    seal_then_extend(paths, df_seal, df_full, lambda d: sigs)
    os.remove(paths.journal)
    with pytest.raises(JournalError):
        run_step(flat(20), PARAMS, paths, lambda d: sigs)


# ─────────────────────────────────────────────────────────────────────────────
# (c) scellé des paramètres
# ─────────────────────────────────────────────────────────────────────────────

def test_hash_correct_charge_hash_faux_refuse(tmp_path):
    p = tmp_path / "params.json"
    p.write_text(json.dumps(PARAMS), encoding="utf-8")
    good = sha256_file(str(p))

    loaded = load_sealed_params(str(p), good)
    assert loaded["sizing"]["capital_initial"] == 10000.0

    # Modification d'un paramètre -> hash caduc -> refus.
    tampered = dict(PARAMS)
    tampered["sizing"] = {"capital_initial": 10000.0, "risk_per_trade_pct": 2.0}
    p.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(SealError):
        load_sealed_params(str(p), good)


def test_hash_du_vrai_fichier_scelle_correspond():
    """Le scellé du dépôt est cohérent : params.json ↔ constante de
    run_forward.py. Si ce test casse, quelqu'un a touché l'un sans l'autre —
    c'est précisément l'événement que le dispositif doit rendre visible."""
    from studies.gold_forward.run_forward import PARAMS_PATH, PARAMS_SHA256
    load_sealed_params(PARAMS_PATH, PARAMS_SHA256)   # ne lève pas


# ─────────────────────────────────────────────────────────────────────────────
# (d) stop sauté par gap — conventions moteur
# ─────────────────────────────────────────────────────────────────────────────

def test_stop_saute_par_gap_execute_a_l_ouverture(paths):
    """LONG entré à 100, stop 98.5. La barre suivante OUVRE à 97 : le stop est
    sauté, l'exécution se fait à l'ouverture (97), pas au stop. Le gap se
    paie — même règle que le moteur commun (correctif 66668d1)."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 10 + [
        (100.0, 100.2, 99.8, 100.0),          # barre 10 : rien
        (100.0, 100.3, 99.9, 100.0),          # barre 11 : SIGNAL, entrée 100
        (97.0, 97.5, 96.0, 96.5),             # barre 12 : gap sous le stop
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, side=Side.LONG, sl=1.5, tp=6.0)

    st = seal_then_extend(paths, df_seal, df_full, lambda d: sigs)
    assert st["closed_this_pass"] == 1

    close_row = [r for r in read_journal(paths.journal) if r["event"] == "CLOSE"][0]
    assert close_row["exit_reason"] == "SL"
    assert float(close_row["exit_price"]) == pytest.approx(97.0)   # l'ouverture

    # P&L conforme moteur : entrée 100 + EDGE, sortie 97, coût payé en sortie.
    entry = 100.0 + EDGE
    risk = entry - 98.5
    expected_r = ((97.0 - entry) - EDGE) / risk
    assert float(close_row["pnl_r"]) == pytest.approx(expected_r, abs=1e-4)
    assert expected_r < -1.0               # le gap coûte PLUS qu'un R


def test_sl_et_tp_meme_barre_le_stop_l_emporte(paths):
    """Ordre de visite inconnu dans la barre -> hypothèse défavorable, comme
    le moteur."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # barre 11 : SIGNAL
        (100.0, 106.5, 98.4, 102.0),          # barre 12 : traverse SL ET TP
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, side=Side.LONG, sl=1.5, tp=6.0)

    seal_then_extend(paths, df_seal, df_full, lambda d: sigs)
    close_row = [r for r in read_journal(paths.journal) if r["event"] == "CLOSE"][0]
    assert close_row["exit_reason"] == "SL"
    assert float(close_row["exit_price"]) == pytest.approx(98.5)   # pas de gap


def test_take_profit_et_monnaie_coherente(paths):
    """Une cible atteinte proprement : le R et la monnaie racontent le même
    trade (pnl_ccy = pnl_r × risque dimensionné à 1 %)."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # barre 11 : SIGNAL
        (100.5, 103.0, 100.2, 102.5),         # barre 12 : monte
        (103.0, 106.2, 102.8, 106.0),         # barre 13 : TP 106 touché
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, side=Side.LONG, sl=1.5, tp=6.0)

    st = seal_then_extend(paths, df_seal, df_full, lambda d: sigs)
    close_row = [r for r in read_journal(paths.journal) if r["event"] == "CLOSE"][0]
    assert close_row["exit_reason"] == "TP"

    entry = 100.0 + EDGE
    risk = entry - 98.5
    expected_r = ((106.0 - entry) - EDGE) / risk
    assert float(close_row["pnl_r"]) == pytest.approx(expected_r, abs=1e-4)

    risk_ccy = float(close_row["risk_ccy"])
    assert risk_ccy == pytest.approx(100.0, rel=1e-6)      # 1 % de 10 000
    assert float(close_row["pnl_ccy"]) == pytest.approx(expected_r * risk_ccy,
                                                        abs=0.01)
    assert st["capital"] == pytest.approx(10000.0 + expected_r * risk_ccy,
                                          abs=0.01)


def test_position_unique_et_cooldown(paths):
    """Une position à la fois ; après clôture, 2 barres de cooldown bloquent
    tout nouveau signal — sémantique du moteur commun."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL 1 (ouvre)
        (100.0, 100.3, 99.9, 100.0),          # 12 : SIGNAL 2 (bloqué : ouvert)
        (100.0, 100.4, 98.4, 99.0),           # 13 : SL touché (clôture)
        (99.0, 99.3, 98.8, 99.0),             # 14 : SIGNAL 3 (bloqué : cooldown)
        (99.0, 99.3, 98.8, 99.0),             # 15 : rien (cooldown)
        (99.0, 99.3, 98.8, 99.0),             # 16 : SIGNAL 4 (autorisé)
    ]
    df_full = bars(rows)
    sigs = {}
    for i in (11, 12, 14, 16):
        sigs.update(sig_at(df_full, i))

    seal_then_extend(paths, df_seal, df_full, lambda d: sigs)
    opens = [r for r in read_journal(paths.journal) if r["event"] == "OPEN"]
    assert len(opens) == 2
    assert opens[0]["bar_time"] == df_full.index[11].isoformat()
    assert opens[1]["bar_time"] == df_full.index[16].isoformat()
