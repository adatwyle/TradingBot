"""
Tests du pas de mesure s13 — sur barres synthétiques, sans MT5.

    python -m pytest studies/s13_forward/test_forward_step.py -q

Ce qui est vérifié, et pourquoi c'est ça et pas autre chose :

  (a) IDEMPOTENCE — deux passages sur les mêmes données n'ajoutent rien.
      Sans elle, une exécution quotidienne fabriquerait des trades dupliqués
      et le journal ne compterait plus rien.
  (b) APPEND-ONLY — une réécriture du journal est détectée et le pas refuse de
      tourner sans rien écrire. C'est la propriété qui rend le test opposable.
  (c) SCELLÉ — un fichier de paramètres dont le hash ne correspond pas est
      refusé. Critère d du protocole : aucun paramètre ne bouge en route.
  (d) GAP — un stop sauté par un gap est exécuté à l'OUVERTURE de la barre
      (pire que le stop), comme le moteur commun (correctif 66668d1).
  (e) DEUX BRAS — indépendance des curseurs et des capitaux : un flux absent
      ne bloque pas l'autre et n'avance pas son curseur ; un trade
      d'OBSERVATION ne touche jamais la comptabilité du bras PRINCIPAL.

Plus les contrôles de conformité moteur : préséance SL sur TP dans la même
barre, concordance R/monnaie (coût de bord payé deux fois), et ré-entrée
même barre autorisée avec cooldown 0 (les engine_kwargs de l'étude s13).
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
from studies.s13_forward.forward_step import (                     # noqa: E402
    JournalError, Paths, SealError, load_sealed_params, load_state,
    read_journal, run_step, sha256_file,
)

SPREAD_PIPS = 20.0
PIP = 0.01
EDGE = SPREAD_PIPS * PIP / 2.0          # 0.10 par extrémité (slippage 0 en test)

SPEC = {"pip": PIP, "spread_pips": SPREAD_PIPS, "max_spread_pips": 60.0,
        "pip_value_per_lot": 1.0, "slippage_pips": 0.0}

PARAMS = {
    "primary_symbol": "AUDCAD",
    "instruments": {"AUDCAD": "PRIMARY", "EURJPY": "OBSERVATION"},
    "specs": {"AUDCAD": {"symbol": "AUDCAD", **SPEC},
              "EURJPY": {"symbol": "EURJPY", **SPEC}},
    # Les engine_kwargs de l'ÉTUDE s13 : cooldown 0, circuit breaker désarmé.
    "engine": {"max_positions": 1, "cooldown_bars": 0, "cb_losses": 999,
               "cb_cooldown_bars": 0, "max_hold_bars": None},
    "sizing": {"capital_initial": 10000.0, "risk_per_trade_pct": 1.0},
    "stop_rules": {"fail": {"min_trades": 20, "percentile_below": 20},
                   "success": {"min_trades": 40, "percentile_at_least": 95},
                   "time": {"months": 36, "min_trades": 12},
                   "horizon": {"months": 72}},
}


def bars(rows, start="2026-08-17"):
    """rows = [(open, high, low, close), ...] -> DataFrame D1."""
    idx = pd.date_range(start, periods=len(rows), freq="1D")
    a = np.asarray(rows, dtype=float)
    return pd.DataFrame(
        {"open": a[:, 0], "high": a[:, 1], "low": a[:, 2], "close": a[:, 3]},
        index=idx)


def flat(n, price=100.0, start="2026-08-17"):
    return bars([(price, price + 0.2, price - 0.2, price)] * n, start)


def sig_at(df, i, symbol="AUDCAD", side=Side.LONG, sl=1.5, tp=6.0):
    """Un signal injecté à la barre i : entrée au close, stop/cible en prix."""
    entry = float(df["close"].iloc[i])
    if side == Side.LONG:
        stop, target = entry - sl, entry + tp
    else:
        stop, target = entry + sl, entry - tp
    return {df.index[i]: Signal(timestamp=df.index[i], symbol=symbol,
                                side=side, entry=entry, stop=stop,
                                target=target, reason="test")}


def no_signals(df):
    return {}


NO_SIG = {"AUDCAD": no_signals, "EURJPY": no_signals}


def fns(aud=None, eur=None):
    return {"AUDCAD": (lambda d: aud) if aud is not None else no_signals,
            "EURJPY": (lambda d: eur) if eur is not None else no_signals}


@pytest.fixture
def paths(tmp_path):
    return Paths(str(tmp_path))


def seal_then_extend(paths, df_seal, dfs_full, signal_fns):
    """Premier passage (pose du scellé sur les deux flux, aucun trade), puis
    passage sur les données étendues — le schéma de tout test ci-dessous."""
    s0 = run_step({"AUDCAD": df_seal, "EURJPY": df_seal}, PARAMS, paths, NO_SIG)
    assert s0["first_pass"]
    assert all(a["n_closed_total"] == 0 for a in s0["arms"].values())
    return run_step(dfs_full, PARAMS, paths, signal_fns)


# ─────────────────────────────────────────────────────────────────────────────
# (a) idempotence
# ─────────────────────────────────────────────────────────────────────────────

def test_idempotence_meme_donnees_aucun_ajout(paths):
    df_seal = flat(10)
    df_full = flat(15)                       # 5 barres nouvelles, dont 1 signal
    sigs = sig_at(df_full, 11)
    both = {"AUDCAD": df_full, "EURJPY": df_full}

    st1 = seal_then_extend(paths, df_seal, both, fns(aud=sigs))
    assert st1["opened_this_pass"] == 1
    n_lines = len(read_journal(paths.journal))
    sha1 = sha256_file(paths.journal)

    # Deuxième passage, mêmes données : rien ne doit bouger.
    st2 = run_step(both, PARAMS, paths, fns(aud=sigs))
    assert st2["opened_this_pass"] == 0 and st2["closed_this_pass"] == 0
    assert len(read_journal(paths.journal)) == n_lines
    assert sha256_file(paths.journal) == sha1

    # Troisième passage, toujours identique.
    st3 = run_step(both, PARAMS, paths, fns(aud=sigs))
    assert st3["opened_this_pass"] == 0
    assert sha256_file(paths.journal) == sha1


def test_premier_passage_ne_consomme_aucun_signal_historique(paths):
    """Le scellé est prospectif : un signal ANTÉRIEUR au premier passage ne
    doit jamais entrer au journal."""
    df = flat(12)
    sigs = sig_at(df, 5)                      # signal dans le passé
    both = {"AUDCAD": df, "EURJPY": df}
    st = run_step(both, PARAMS, paths, fns(aud=sigs))
    assert st["first_pass"]
    st2 = run_step(both, PARAMS, paths, fns(aud=sigs))
    assert st2["opened_this_pass"] == 0
    assert [r for r in read_journal(paths.journal) if r["event"] == "OPEN"] == []


def test_premier_passage_exige_les_deux_flux(paths):
    """Le scellé se pose sur les DEUX flux à la fois — pas de bras qui démarre
    en retard (motif macd_ai_paper)."""
    with pytest.raises(ValueError):
        run_step({"AUDCAD": flat(10)}, PARAMS, paths, NO_SIG)
    assert load_state(paths.state) is None    # rien n'a été posé


# ─────────────────────────────────────────────────────────────────────────────
# (b) append-only
# ─────────────────────────────────────────────────────────────────────────────

def _sealed_with_one_trade(paths):
    df_seal = flat(10)
    df_full = flat(15)
    sigs = sig_at(df_full, 11)
    both = {"AUDCAD": df_full, "EURJPY": df_full}
    seal_then_extend(paths, df_seal, both, fns(aud=sigs))
    return sigs


def test_reecriture_du_journal_detectee_et_refus(paths):
    sigs = _sealed_with_one_trade(paths)

    # Falsification : on améliore un chiffre dans une ligne passée.
    with open(paths.journal, "r", encoding="utf-8") as f:
        txt = f.read()
    assert "OPEN" in txt
    with open(paths.journal, "w", encoding="utf-8") as f:
        f.write(txt.replace("OPEN", "OPEN".replace("O", "0"), 1))

    before = sha256_file(paths.journal)
    both = {"AUDCAD": flat(20), "EURJPY": flat(20)}
    with pytest.raises(JournalError):
        run_step(both, PARAMS, paths, fns(aud=sigs))
    # Refus SANS écriture : le fichier falsifié est resté tel quel (preuve).
    assert sha256_file(paths.journal) == before


def test_troncature_du_journal_detectee(paths):
    sigs = _sealed_with_one_trade(paths)
    with open(paths.journal, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(paths.journal, "w", encoding="utf-8") as f:
        f.writelines(lines[:-1])              # on efface le dernier trade
    both = {"AUDCAD": flat(20), "EURJPY": flat(20)}
    with pytest.raises(JournalError):
        run_step(both, PARAMS, paths, fns(aud=sigs))


def test_suppression_du_journal_detectee(paths):
    sigs = _sealed_with_one_trade(paths)
    os.remove(paths.journal)
    both = {"AUDCAD": flat(20), "EURJPY": flat(20)}
    with pytest.raises(JournalError):
        run_step(both, PARAMS, paths, fns(aud=sigs))


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
    from studies.s13_forward.run_forward import PARAMS_PATH, PARAMS_SHA256
    load_sealed_params(PARAMS_PATH, PARAMS_SHA256)   # ne lève pas


# ─────────────────────────────────────────────────────────────────────────────
# (d) stop sauté par gap — conventions moteur
# ─────────────────────────────────────────────────────────────────────────────

def test_stop_saute_par_gap_execute_a_l_ouverture(paths):
    """LONG entré à 100, stop 98.5. La barre suivante OUVRE à 97 : le stop est
    sauté, l'exécution se fait à l'ouverture (97), pas au stop. Le gap se
    paie — même règle que le moteur commun (correctif 66668d1). Sur D1 les
    gaps de week-end sont fréquents : ce cas N'EST PAS théorique."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 10 + [
        (100.0, 100.2, 99.8, 100.0),          # barre 10 : rien
        (100.0, 100.3, 99.9, 100.0),          # barre 11 : SIGNAL, entrée 100
        (97.0, 97.5, 96.0, 96.5),             # barre 12 : gap sous le stop
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, side=Side.LONG, sl=1.5, tp=6.0)
    both = {"AUDCAD": df_full, "EURJPY": df_full}

    st = seal_then_extend(paths, df_seal, both, fns(aud=sigs))
    assert st["closed_this_pass"] == 1

    close_row = [r for r in read_journal(paths.journal) if r["event"] == "CLOSE"][0]
    assert close_row["symbol"] == "AUDCAD" and close_row["arm"] == "PRIMARY"
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
    both = {"AUDCAD": df_full, "EURJPY": df_full}

    seal_then_extend(paths, df_seal, both, fns(aud=sigs))
    close_row = [r for r in read_journal(paths.journal) if r["event"] == "CLOSE"][0]
    assert close_row["exit_reason"] == "SL"
    assert float(close_row["exit_price"]) == pytest.approx(98.5)   # pas de gap


def test_take_profit_et_monnaie_coherente(paths):
    """Une cible atteinte proprement : le R et la monnaie racontent le même
    trade (pnl_ccy = pnl_r × risque dimensionné à 1 % du capital DU BRAS)."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # barre 11 : SIGNAL
        (100.5, 103.0, 100.2, 102.5),         # barre 12 : monte
        (103.0, 106.2, 102.8, 106.0),         # barre 13 : TP 106 touché
    ]
    df_full = bars(rows)
    sigs = sig_at(df_full, 11, side=Side.LONG, sl=1.5, tp=6.0)
    both = {"AUDCAD": df_full, "EURJPY": df_full}

    st = seal_then_extend(paths, df_seal, both, fns(aud=sigs))
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
    aud = st["arms"]["AUDCAD"]
    assert aud["capital"] == pytest.approx(10000.0 + expected_r * risk_ccy,
                                           abs=0.01)
    # Le bras d'observation n'a pas bougé d'un centime.
    assert st["arms"]["EURJPY"]["capital"] == pytest.approx(10000.0)


def test_position_unique_et_reentree_meme_barre_cooldown_zero(paths):
    """Une position à la fois PAR BRAS ; avec cooldown 0 (engine_kwargs de
    l'étude s13), un signal sur la barre de SORTIE ré-entre le jour même —
    même sémantique que le moteur (`i < cooldown_until` faux)."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL 1 (ouvre)
        (100.0, 100.3, 99.9, 100.0),          # 12 : SIGNAL 2 (bloqué : ouvert)
        (100.0, 100.4, 98.4, 99.0),           # 13 : SL touché + SIGNAL 3
                                              #      (ré-entrée même barre)
        (99.0, 99.3, 98.8, 99.0),             # 14 : rien
    ]
    df_full = bars(rows)
    sigs = {}
    for i in (11, 12, 13):
        sigs.update(sig_at(df_full, i))
    both = {"AUDCAD": df_full, "EURJPY": df_full}

    seal_then_extend(paths, df_seal, both, fns(aud=sigs))
    opens = [r for r in read_journal(paths.journal) if r["event"] == "OPEN"]
    assert len(opens) == 2
    assert opens[0]["bar_time"] == df_full.index[11].isoformat()
    assert opens[1]["bar_time"] == df_full.index[13].isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# (e) deux bras — indépendance
# ─────────────────────────────────────────────────────────────────────────────

def test_flux_absent_curseur_intact_l_autre_avance(paths):
    """MT5 partiel : un instrument absent d'un passage est sauté (curseur
    intact), l'autre avance. Au passage suivant, le retardataire rattrape ses
    barres manquées — aucun signal perdu."""
    df_seal = flat(10)
    df_full = flat(15)
    sig_eur = sig_at(df_full, 11, symbol="EURJPY")

    run_step({"AUDCAD": df_seal, "EURJPY": df_seal}, PARAMS, paths, NO_SIG)

    # Passage avec EURJPY absent : AUDCAD avance, EURJPY reste au scellé.
    st = run_step({"AUDCAD": df_full}, PARAMS, paths, fns(eur=sig_eur))
    assert st["arms"]["AUDCAD"]["last_bar_time"] == df_full.index[-1].isoformat()
    assert st["arms"]["EURJPY"]["last_bar_time"] == df_seal.index[-1].isoformat()
    assert st["opened_this_pass"] == 0

    # EURJPY revient : ses barres manquées sont rejouées, le signal est pris.
    st2 = run_step({"AUDCAD": df_full, "EURJPY": df_full}, PARAMS, paths,
                   fns(eur=sig_eur))
    assert st2["opened_this_pass"] == 1
    opens = [r for r in read_journal(paths.journal) if r["event"] == "OPEN"]
    assert len(opens) == 1
    assert opens[0]["symbol"] == "EURJPY" and opens[0]["arm"] == "OBSERVATION"


def test_observation_n_entre_pas_dans_la_comptabilite_du_principal(paths):
    """Un trade EURJPY (OBSERVATION) est journalisé à l'identique mais ne
    touche NI le n_closed NI le capital du bras PRINCIPAL — c'est ce qui rend
    les critères d'arrêt insensibles à l'observation."""
    df_seal = flat(10)
    rows = [(100.0, 100.2, 99.8, 100.0)] * 11 + [
        (100.0, 100.3, 99.9, 100.0),          # 11 : SIGNAL EURJPY
        (100.0, 100.4, 98.4, 99.0),           # 12 : SL touché
    ]
    df_full = bars(rows)
    sig_eur = sig_at(df_full, 11, symbol="EURJPY")
    both = {"AUDCAD": df_full, "EURJPY": df_full}

    st = seal_then_extend(paths, df_seal, both, fns(eur=sig_eur))
    assert st["arms"]["EURJPY"]["n_closed_total"] == 1
    assert st["arms"]["EURJPY"]["capital"] < 10000.0
    assert st["arms"]["AUDCAD"]["n_closed_total"] == 0
    assert st["arms"]["AUDCAD"]["capital"] == pytest.approx(10000.0)

    rows_j = read_journal(paths.journal)
    assert all(r["arm"] == "OBSERVATION" for r in rows_j)
