"""
Tests de S020 — MACD cross + filtre zéro, SL/TP en %.

    python -m pytest strategies/S020_balke_macd_cross/test_s020_strategy.py -q

(a) la règle fait ce qu'elle dit : signal à la barre du croisement, pas avant ;
(b) le filtre zéro coupe exactement les croisements du mauvais côté ;
(c) la géométrie en % est celle de la vidéo, du bon côté de l'entrée ;
(d) causalité : troncature invariante, on_bar = backtest ;
(e) bornes : commutateur inconnu lève.
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

from core.contracts.strategy import MarketContext, Side                    # noqa: E402
from strategies.S020_balke_macd_cross.strategy import (                    # noqa: E402
    MACD_FAST, MACD_SIGNAL, MACD_SLOW, WARMUP_BARS, Strategy,
)

BASE = {"zero_filter": True, "sl_pct": 0.02, "tp_pct": 0.02, "side_mode": "both"}


def _bars(n: int, seed: int = 1, price: float = 20000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = price + rng.normal(0, 40, n).cumsum()
    high = close + np.abs(rng.normal(30, 8, n))
    low = close - np.abs(rng.normal(30, 8, n))
    opens = np.concatenate([[close[0]], close[:-1]])
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame({"open": opens, "high": high, "low": low, "close": close,
                         "tick_volume": 100.0, "spread": 20.0}, index=idx)


def _run(df, **over):
    p = {**BASE, **over}
    s = Strategy(p)
    s._symbol = "NASDAQ"
    data = s.precompute(df, p)
    return s.generate_signals(data, p, len(df)), data


def _macd(close: pd.Series):
    ef = close.ewm(span=MACD_FAST, adjust=False).mean()
    es = close.ewm(span=MACD_SLOW, adjust=False).mean()
    m = ef - es
    return m, m.ewm(span=MACD_SIGNAL, adjust=False).mean()


# (a) la règle
def test_signal_tombe_a_la_barre_du_croisement():
    df = _bars(800)
    sigs, data = _run(df, zero_filter=False)
    assert sigs
    m, s = _macd(df["close"])
    d = (m - s).to_numpy()
    for sg in sigs:
        i = df.index.get_loc(pd.Timestamp(sg.timestamp))
        assert i >= WARMUP_BARS
        if sg.side == Side.LONG:
            assert d[i - 1] <= 0 < d[i], "achat sans croisement haussier à cette barre"
        else:
            assert d[i - 1] >= 0 > d[i], "vente sans croisement baissier à cette barre"


def test_un_seul_signal_par_croisement():
    df = _bars(800)
    sigs, _ = _run(df, zero_filter=False)
    m, s = _macd(df["close"])
    d = (m - s).to_numpy()
    n_cross = int(np.sum((d[:-1] <= 0) & (d[1:] > 0)) + np.sum((d[:-1] >= 0) & (d[1:] < 0)))
    n_cross_after_warmup = sum(
        1 for i in range(WARMUP_BARS, len(d))
        if (d[i - 1] <= 0 < d[i]) or (d[i - 1] >= 0 > d[i]))
    assert len(sigs) == n_cross_after_warmup
    assert n_cross_after_warmup <= n_cross


# (b) le filtre zéro
def test_filtre_zero_ne_garde_que_le_bon_cote():
    df = _bars(1500, seed=3)
    sans, data = _run(df, zero_filter=False)
    avec, _ = _run(df, zero_filter=True)
    assert 0 < len(avec) < len(sans)
    for sg in avec:
        assert (sg.meta["macd"] < 0) if sg.side == Side.LONG else (sg.meta["macd"] > 0)
    kept = {(s.timestamp, s.side) for s in avec}
    for sg in sans:
        ok = (sg.meta["macd"] < 0) if sg.side == Side.LONG else (sg.meta["macd"] > 0)
        assert ((sg.timestamp, sg.side) in kept) == ok


# (c) géométrie en %
def test_stop_et_cible_en_pourcent_du_prix():
    df = _bars(800, seed=5)
    sigs, _ = _run(df, zero_filter=False, sl_pct=0.01, tp_pct=0.03)
    for sg in sigs:
        if sg.side == Side.LONG:
            assert abs(sg.stop - sg.entry * 0.99) < 1e-6
            assert abs(sg.target - sg.entry * 1.03) < 1e-6
            assert sg.stop < sg.entry < sg.target
        else:
            assert abs(sg.stop - sg.entry * 1.01) < 1e-6
            assert abs(sg.target - sg.entry * 0.97) < 1e-6
            assert sg.target < sg.entry < sg.stop
        assert abs(sg.rr - 3.0) < 1e-9


# (d) causalité
def test_troncature_ne_change_pas_les_signaux_passes():
    df = _bars(1500, seed=7)
    for zf in (False, True):
        p = {**BASE, "zero_filter": zf}
        for frac in (0.6, 0.8):
            T = int(len(df) * frac)
            a = Strategy(p); a._symbol = "NASDAQ"
            full = a.generate_signals(a.precompute(df, p), p, T)
            b = Strategy(p); b._symbol = "NASDAQ"
            trunc = b.generate_signals(b.precompute(df.iloc[:T].copy(), p), p, T)
            k = lambda xs: [(x.timestamp, x.side, x.entry, x.stop, x.target) for x in xs]
            assert k(full) == k(trunc)


def test_on_bar_est_le_meme_code_que_le_backtest():
    df = _bars(1200, seed=9)
    p = dict(BASE, zero_filter=False)
    strat = Strategy(p); strat._symbol = "NASDAQ"
    bt = {pd.Timestamp(s.timestamp): s
          for s in strat.generate_signals(strat.precompute(df, p), p, len(df))}
    hits = 0
    for i in range(len(df) - 60, len(df)):
        ctx = MarketContext(symbol="NASDAQ", timeframe="H1", bars=df.iloc[:i + 1],
                            now=pd.Timestamp(df.index[i]).to_pydatetime(), spread=2.0)
        live = strat.on_bar(ctx)
        exp = bt.get(pd.Timestamp(df.index[i]))
        assert (live is None) == (exp is None)
        if live is not None:
            hits += 1
            assert (live.side, live.entry, live.stop, live.target) == \
                   (exp.side, exp.entry, exp.stop, exp.target)
    assert hits >= 1


# (e) bornes et manifeste
def test_manifest_conforme():
    m = Strategy().manifest()
    assert m.magic_number == 130020
    assert m.strategy_id == "S020_balke_macd_cross"
    assert m.status == "RESEARCH"
    assert int(np.prod([len(v) for v in m.param_grid.values()])) == 18
    for k in m.param_grid:
        assert m.default_params[k] in m.param_grid[k]


@pytest.mark.parametrize("bad", [{"side_mode": "flat"}, {"sl_pct": 0.0}, {"tp_pct": -0.01}])
def test_parametre_invalide_leve(bad):
    with pytest.raises(ValueError):
        _run(_bars(300), **bad)


def test_long_only_supprime_les_ventes():
    df = _bars(1500, seed=11)
    ref, _ = _run(df, zero_filter=False)
    lo, _ = _run(df, zero_filter=False, side_mode="long_only")
    assert any(s.side == Side.SHORT for s in ref)
    assert lo and all(s.side == Side.LONG for s in lo)
