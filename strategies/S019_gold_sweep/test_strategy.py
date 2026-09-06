"""
Tests de S019 — balayage de liquidité et réintégration.

    python -m pytest strategies/S019_gold_sweep/test_strategy.py -q

Ce qui est vérifié, et pourquoi c'est ça :

  (a) LA RÈGLE FAIT CE QU'ELLE DIT — sur un scénario construit à la main où le
      balayage et la réintégration sont placés à des barres connues, le signal
      tombe exactement à la barre de réintégration, pas à celle du perçage.
      C'est la distinction « impulsion » / « structure » de la source ; si elle
      se perd, la stratégie n'est plus la sienne.
  (b) LE STOP EST STRUCTUREL, ET PLANCHONNÉ — sous le plus-bas balayé quand
      celui-ci est assez loin, ramené au plancher quand il est trop près. Le
      plancher n'est pas cosmétique : un stop de 34 pips face à 52 pips de
      spread perd de l'argent par construction.
  (c) LA CAUSALITÉ — l'invariant de troncature, et la porte journalière qui lit
      la veille close et jamais le jour courant.
  (d) LES BORNES — un commutateur inconnu lève au lieu de retomber en silence
      sur un défaut.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.contracts.strategy import MarketContext, Side          # noqa: E402
from strategies.S019_gold_sweep.strategy import (                # noqa: E402
    SESSION_DOUD, WARMUP_BARS, Strategy, _htf_trend,
)

BASE = {"sweep_lookback": 60, "sweep_window": 5, "stop_buffer_atr": 0.10,
        "min_stop_atr": 0.5, "tp_r": 2.0, "htf_bias": "off",
        "session_filter": "off", "side_mode": "both", "htf_ema_days": 20,
        "cooldown_bars": 3}


def _flat(n: int, price: float = 4000.0, wiggle: float = 2.0, seed: int = 1) -> pd.DataFrame:
    """Fond de marché calme : assez de bruit pour que l'ATR existe, pas assez
    pour percer quoi que ce soit."""
    rng = np.random.default_rng(seed)
    close = price + rng.normal(0, wiggle, n).cumsum() * 0.05
    high = close + np.abs(rng.normal(wiggle, 0.4, n))
    low = close - np.abs(rng.normal(wiggle, 0.4, n))
    opens = np.concatenate([[close[0]], close[:-1]])
    idx = pd.date_range("2025-01-01 00:00", periods=n, freq="15min")
    return pd.DataFrame({"open": opens, "high": high, "low": low, "close": close,
                         "tick_volume": 100.0, "spread": 52.0}, index=idx)


def _signals(df: pd.DataFrame, **over):
    p = {**BASE, **over}
    s = Strategy(p)
    s._symbol = "XAUUSD"
    data = s.precompute(df, p)
    return s.generate_signals(data, p, len(df)), data


# ─────────────────────────────────────────────────────────────────────────────
# (a) La règle fait ce qu'elle dit
# ─────────────────────────────────────────────────────────────────────────────

def test_scenario_construit_le_signal_tombe_a_la_reintegration():
    """Balayage à la barre 400, réintégration à la 402 : le signal doit être
    daté de 402. Une entrée datée de 400 signifierait qu'on prend la mèche —
    exactement ce que la source dit de ne pas faire."""
    df = _flat(500).copy()
    ref = float(df["low"].iloc[340:400].min())

    # barre 400 : la mèche perce nettement sous la poche, mais clôture dessous
    df.iloc[400, df.columns.get_loc("low")] = ref - 6.0
    df.iloc[400, df.columns.get_loc("close")] = ref - 1.0
    df.iloc[400, df.columns.get_loc("high")] = ref + 0.5
    # barres 401-402 : réintégration, la clôture repasse au-dessus du niveau
    for k, c in ((401, ref + 0.5), (402, ref + 3.0)):
        df.iloc[k, df.columns.get_loc("close")] = c
        df.iloc[k, df.columns.get_loc("high")] = c + 1.0
        df.iloc[k, df.columns.get_loc("low")] = c - 1.0

    sigs, _ = _signals(df)
    matched = [s for s in sigs if s.meta.get("sweep_idx") == 400]
    assert matched, "le balayage construit n'a produit aucun signal"
    s = matched[0]
    assert s.side == Side.LONG
    assert pd.Timestamp(s.timestamp) == df.index[401], \
        "le signal doit tomber à la RÉINTÉGRATION (401), pas à la mèche (400)"
    assert s.meta["bars_to_reentry"] == 1
    assert s.meta["depth_pips"] > 500       # 6,0 en prix = 600 pips


def test_pas_de_signal_sans_reintegration():
    """Le prix perce et reste dessous : le setup meurt, aucune entrée."""
    df = _flat(500).copy()
    ref = float(df["low"].iloc[340:400].min())
    for k in range(400, 410):               # au-delà de sweep_window
        df.iloc[k, df.columns.get_loc("low")] = ref - 6.0 - k * 0.1
        df.iloc[k, df.columns.get_loc("close")] = ref - 4.0 - k * 0.1
        df.iloc[k, df.columns.get_loc("high")] = ref - 2.0
    sigs, _ = _signals(df)
    assert not [s for s in sigs if s.meta.get("sweep_idx") == 400]


def test_la_reintegration_se_juge_sur_la_cloture_pas_sur_la_meche():
    """Une mèche qui repasse au-dessus du niveau ne vaut rien si la clôture
    reste dessous — « il a cassé en impulsion mais pas en structure »."""
    df = _flat(500).copy()
    ref = float(df["low"].iloc[340:400].min())
    df.iloc[400, df.columns.get_loc("low")] = ref - 6.0
    df.iloc[400, df.columns.get_loc("close")] = ref - 1.0
    for k in range(401, 406):
        df.iloc[k, df.columns.get_loc("high")] = ref + 5.0    # la mèche repasse
        df.iloc[k, df.columns.get_loc("close")] = ref - 1.0   # la clôture, non
        df.iloc[k, df.columns.get_loc("low")] = ref - 3.0
    sigs, _ = _signals(df)
    assert not [s for s in sigs if s.meta.get("sweep_idx") == 400]


# ─────────────────────────────────────────────────────────────────────────────
# (b) Le stop est structurel, et planchonné
# ─────────────────────────────────────────────────────────────────────────────

def test_stop_structurel_quand_le_balayage_est_profond():
    df = _flat(500).copy()
    ref = float(df["low"].iloc[340:400].min())
    df.iloc[400, df.columns.get_loc("low")] = ref - 12.0     # balayage profond
    df.iloc[400, df.columns.get_loc("close")] = ref - 1.0
    df.iloc[401, df.columns.get_loc("close")] = ref + 3.0
    df.iloc[401, df.columns.get_loc("high")] = ref + 4.0
    df.iloc[401, df.columns.get_loc("low")] = ref + 1.0
    sigs, _ = _signals(df)
    s = [x for x in sigs if x.meta.get("sweep_idx") == 400][0]
    assert s.meta["stop_structurel"] is True
    assert s.stop < ref - 12.0 + 1e-6, "le stop doit passer SOUS le plus-bas balayé"


def test_plancher_de_stop_quand_le_balayage_est_trop_serre():
    """Un balayage minuscule donnerait un stop plus petit que le spread : le
    plancher doit reprendre la main. C'est une condition de survie économique,
    pas un raffinement."""
    df = _flat(500).copy()
    ref = float(df["low"].iloc[340:400].min())
    df.iloc[400, df.columns.get_loc("low")] = ref - 0.05     # perçage minuscule
    df.iloc[400, df.columns.get_loc("close")] = ref - 0.02
    df.iloc[401, df.columns.get_loc("close")] = ref + 2.0
    df.iloc[401, df.columns.get_loc("high")] = ref + 2.5
    df.iloc[401, df.columns.get_loc("low")] = ref + 1.0
    sigs, data = _signals(df, min_stop_atr=1.0)
    s = [x for x in sigs if x.meta.get("sweep_idx") == 400][0]
    assert s.meta["stop_structurel"] is False, "le plancher aurait dû s'appliquer"
    atr = float(data["atr"].iloc[401])
    assert abs(s.risk_distance - 1.0 * atr) < 1e-6


def test_geometrie_du_signal_conforme_au_contrat():
    df = _flat(1500, seed=7)
    sigs, _ = _signals(df)
    assert sigs, "le fond synthétique doit produire des signaux"
    for s in sigs:
        assert s.stop is not None and s.risk_distance > 0
        if s.side == Side.LONG:
            assert s.stop < s.entry < s.target
        else:
            assert s.target < s.entry < s.stop
        assert abs(s.rr - BASE["tp_r"]) < 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# (c) Causalité
# ─────────────────────────────────────────────────────────────────────────────

def test_troncature_ne_change_pas_les_signaux_passes():
    df = _flat(1500, seed=11)
    for htf in ("off", "daily_ema"):
        p = {**BASE, "htf_bias": htf}
        for frac in (0.7, 0.85):
            T = int(len(df) * frac)
            a = Strategy(p); a._symbol = "XAUUSD"
            full = a.generate_signals(a.precompute(df, p), p, T)
            b = Strategy(p); b._symbol = "XAUUSD"
            trunc = b.generate_signals(b.precompute(df.iloc[:T].copy(), p), p, T)
            k = lambda xs: [(x.timestamp, x.side, x.entry, x.stop) for x in xs]
            assert k(full) == k(trunc), f"fuite avec htf={htf} à la coupe {frac}"


def test_porte_journaliere_lit_la_veille_close():
    df = _flat(24 * 4 * 60, seed=3)
    bias = _htf_trend(df, 5)
    daily = df["close"].resample("1D").last().dropna()
    expected = np.sign(daily - daily.ewm(span=5, adjust=False).mean())
    first = pd.Series(bias, index=df.index).groupby(df.index.normalize()).first()
    checked = 0
    for day, val in first.items():
        pos = daily.index.get_indexer([day])[0]
        if pos <= 0:
            continue
        assert val == expected.iloc[pos - 1], f"la porte du {day} lit le mauvais jour"
        checked += 1
    assert checked > 20


def test_on_bar_est_le_meme_code_que_le_backtest():
    df = _flat(1200, seed=5)
    p = dict(BASE)
    strat = Strategy(p); strat._symbol = "XAUUSD"
    bt = {pd.Timestamp(s.timestamp): s
          for s in strat.generate_signals(strat.precompute(df, p), p, len(df))}
    for i in range(len(df) - 40, len(df)):
        ctx = MarketContext(symbol="XAUUSD", timeframe="M15", bars=df.iloc[:i + 1],
                            now=pd.Timestamp(df.index[i]).to_pydatetime(), spread=0.52)
        live = strat.on_bar(ctx)
        exp = bt.get(pd.Timestamp(df.index[i]))
        assert (live is None) == (exp is None)
        if live is not None:
            assert (live.side, live.entry, live.stop) == (exp.side, exp.entry, exp.stop)


# ─────────────────────────────────────────────────────────────────────────────
# (d) Commutateurs et bornes
# ─────────────────────────────────────────────────────────────────────────────

def test_long_only_supprime_les_shorts():
    df = _flat(1500, seed=13)
    ref, _ = _signals(df)
    lo, _ = _signals(df, side_mode="long_only")
    assert any(s.side == Side.SHORT for s in ref)
    assert all(s.side == Side.LONG for s in lo)


def test_session_doud_restreint_aux_heures_declarees():
    df = _flat(2000, seed=17)
    ref, _ = _signals(df)
    doud, _ = _signals(df, session_filter="doud")
    assert all(pd.Timestamp(s.timestamp).hour in SESSION_DOUD for s in doud)
    assert len(doud) < len(ref)


def test_manifest_conforme():
    m = Strategy().manifest()
    assert m.magic_number == 130019
    assert m.strategy_id == "S019_gold_sweep"
    assert m.symbols == ["XAUUSD"] and m.status == "RESEARCH"
    cells = int(np.prod([len(v) for v in m.param_grid.values()]))
    assert cells == 16
    for k in m.param_grid:
        assert m.default_params[k] == m.param_grid[k][0]


@pytest.mark.parametrize("bad", [{"side_mode": "short_only"},
                                 {"session_filter": "londres"},
                                 {"htf_bias": "weekly"}])
def test_commutateur_inconnu_leve(bad):
    with pytest.raises(ValueError):
        _signals(_flat(500), **bad)
