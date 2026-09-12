"""
Tests de S022 — ATR Candle Breakout (grosse bougie fermant sur son extrême).

    python -m pytest strategies/S022_balke_atr_candle/test_s022_strategy.py -q

(a) la règle ne se déclenche que sur une bougie qualifiante : assez grande ET
    fermant près de son extrême — une grosse bougie fermant au milieu ne donne rien ;
(b) la proximité est une borne inclusive, exactement à la frontière ;
(c) le sens suit la bougie ;
(d) l'ATR de référence ignore la bougie jugée (décalage 1) — vérifié numériquement
    ET par son effet : sans décalage, le signal disparaîtrait ;
(e) géométrie en % du prix d'entrée, des deux côtés ;
(f) causalité : troncature invariante, on_bar = backtest ;
(g) bornes : paramètre invalide → ValueError ; manifeste conforme.

Les barres sont construites à la main : un fond parfaitement régulier (True Range
constant, donc ATR connu exactement) dans lequel on injecte des bougies choisies.
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
from strategies.S022_balke_atr_candle.strategy import (                    # noqa: E402
    ATR_PERIOD, WARMUP_BARS, WARMUP_MARGIN, Strategy,
)

# Période courte pour des tests lisibles : le fond fait 1,0 de True Range, donc
# ATR = 1,0 exactement, et le seuil « grosse bougie » vaut atr_mult.
P = 10
BASE = {"atr_period": P, "atr_mult": 2.5, "proximity": 0.25, "tp_pct": 0.02,
        "sl_pct": 0.005, "min_body_ratio": 0.0, "atr_mode": "sma", "side_mode": "both"}
PRICE = 2000.0


def _flat(n: int, price: float = PRICE) -> pd.DataFrame:
    """Fond régulier : chaque barre ouvre et ferme à `price`, amplitude 1,0.
    Le close précédent valant aussi `price`, le True Range vaut 1,0 partout."""
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame({"open": price, "high": price + 0.5, "low": price - 0.5,
                         "close": price, "tick_volume": 100.0, "spread": 900.0},
                        index=idx)


def _put(df: pd.DataFrame, i: int, o: float, h: float, l: float, c: float) -> pd.DataFrame:
    df = df.copy()
    df.iloc[i, df.columns.get_indexer(["open", "high", "low", "close"])] = [o, h, l, c]
    return df


def _run(df: pd.DataFrame, **over):
    p = {**BASE, **over}
    s = Strategy(p)
    s._symbol = "XAUUSD"
    return s.generate_signals(s.precompute(df, p), p, len(df)), s.precompute(df, p)


def _at(df: pd.DataFrame, i: int) -> pd.Timestamp:
    return pd.Timestamp(df.index[i])


K = 60          # indice de la bougie injectée : > warmup (P + 10 = 20)


# ── (a) la règle ────────────────────────────────────────────────────────────
def test_une_grosse_bougie_fermant_sur_son_haut_donne_exactement_un_achat():
    # amplitude 4,0 = 4 × ATR (> 2,5) ; close à 0,1 du haut = 2,5 % de l'amplitude
    df = _put(_flat(200), K, o=1999.0, h=2003.0, l=1999.0, c=2002.9)
    sigs, _ = _run(df)
    assert len(sigs) == 1
    assert sigs[0].side == Side.LONG
    assert pd.Timestamp(sigs[0].timestamp) == _at(df, K)
    assert sigs[0].entry == pytest.approx(2002.9)


def test_grosse_bougie_fermant_au_milieu_ne_donne_rien():
    # même amplitude, mais close au centre : (haut − close) = 50 % > 25 %
    df = _put(_flat(200), K, o=1999.2, h=2003.0, l=1999.0, c=2001.0)
    sigs, _ = _run(df)
    assert sigs == []


def test_petite_bougie_fermant_sur_son_haut_ne_donne_rien():
    # ferme pile sur son haut, mais amplitude 2,0 < 2,5 × ATR → pas un outlier
    df = _put(_flat(200), K, o=1999.0, h=2001.0, l=1999.0, c=2001.0)
    sigs, _ = _run(df)
    assert sigs == []
    # la même bougie passe dès que le seuil descend sous son amplitude
    sigs2, _ = _run(df, atr_mult=1.5)
    assert len(sigs2) == 1 and pd.Timestamp(sigs2[0].timestamp) == _at(df, K)


def test_seules_les_bougies_injectees_declenchent():
    df = _flat(400)
    for i in (40, 120, 300):
        df = _put(df, i, o=1999.0, h=2003.0, l=1999.0, c=2002.95)
    sigs, _ = _run(df)
    assert [pd.Timestamp(s.timestamp) for s in sigs] == [_at(df, i) for i in (40, 120, 300)]


# ── (b) la frontière de proximité ───────────────────────────────────────────
def test_proximite_est_une_borne_inclusive():
    # amplitude 4,0 ; close à exactement 25 % du haut → accepté (≤)
    df = _put(_flat(200), K, o=1999.5, h=2003.0, l=1999.0, c=2002.0)
    assert len(_run(df, proximity=0.25)[0]) == 1
    # un cheveu plus strict → refusé
    assert _run(df, proximity=0.249)[0] == []


# ── (c) le sens suit la bougie ──────────────────────────────────────────────
def test_bougie_baissiere_fermant_sur_son_bas_donne_une_vente():
    df = _put(_flat(200), K, o=2003.0, h=2003.0, l=1999.0, c=1999.1)
    sigs, _ = _run(df)
    assert len(sigs) == 1 and sigs[0].side == Side.SHORT
    assert sigs[0].entry == pytest.approx(1999.1)


def test_side_mode_long_only_supprime_les_ventes():
    df = _flat(400)
    df = _put(df, 60, o=1999.0, h=2003.0, l=1999.0, c=2002.9)      # achat
    df = _put(df, 200, o=2003.0, h=2003.0, l=1999.0, c=1999.1)     # vente
    ref, _ = _run(df)
    assert {s.side for s in ref} == {Side.LONG, Side.SHORT}
    lo, _ = _run(df, side_mode="long_only")
    assert lo and all(s.side == Side.LONG for s in lo)
    so, _ = _run(df, side_mode="short_only")
    assert so and all(s.side == Side.SHORT for s in so)


def test_filtre_de_corps_ecarte_les_grandes_meches():
    # amplitude 4,0, corps 0,4 (10 %) : longue mèche basse, close sur le haut
    df = _put(_flat(200), K, o=2002.5, h=2003.0, l=1999.0, c=2002.9)
    assert len(_run(df, min_body_ratio=0.0)[0]) == 1      # filtre désactivé (réglage live)
    assert _run(df, min_body_ratio=0.5)[0] == []          # filtre actif → écartée


# ── (d) causalité de l'ATR ──────────────────────────────────────────────────
def test_atr_de_reference_ignore_la_bougie_jugee():
    df = _put(_flat(200), K, o=1999.0, h=2003.0, l=1999.0, c=2002.9)
    _, data = _run(df)
    high, low, close = df["high"], df["low"], df["close"]
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    # la référence à la barre i est la moyenne des P True Range QUI PRÉCÈDENT i
    for i in (K, K + 1, 150):
        attendu = float(tr.iloc[i - P:i].mean())
        assert data["atr_ref"].iloc[i] == pytest.approx(attendu, rel=1e-12)
    assert data["atr_ref"].iloc[K] == pytest.approx(1.0)   # fond régulier intact


def test_true_range_tient_compte_du_close_precedent():
    """Épingle la DÉFINITION du True Range, valeurs écrites à la main.

    Une barre qui s'écarte du close précédent sans être ample par elle-même (gap)
    a un True Range grand et une amplitude petite. Une mise en œuvre qui
    confondrait True Range et (haut − bas) donnerait ici des ATR deux à trois fois
    trop faibles — et survivrait à tous les autres tests. Les valeurs attendues
    sont posées EN DUR, pas recalculées avec l'expression du module."""
    G = 60
    # fond régulier (TR = 1,0) ; une seule barre s'installe à 2010, puis retour à 2000
    df = _put(_flat(200), G, o=2010.0, h=2010.4, l=2009.8, c=2010.2)
    _, data = _run(df)
    a = data["atr_ref"]
    # TR[G]   = max(0,6 ; |2010,4 − 2000| ; |2009,8 − 2000|) = 10,4   (et non 0,6)
    # TR[G+1] = max(1,0 ; |2000,5 − 2010,2| ; |1999,5 − 2010,2|) = 10,7
    assert a.iloc[G] == pytest.approx(1.0)        # fond seul : la barre de gap est décalée
    assert a.iloc[G + 1] == pytest.approx(1.94)   # (9 × 1,0 + 10,4) / 10
    assert a.iloc[G + 2] == pytest.approx(2.91)   # (8 × 1,0 + 10,4 + 10,7) / 10
    assert a.iloc[G + 11] == pytest.approx(1.97)  # (9 × 1,0 + 10,7) / 10
    # une définition « haut − bas » donnerait 0,96 : l'écart n'est pas marginal
    assert a.iloc[G + 1] > 1.5


def test_atr_mode_wilder_suit_la_recurrence_annoncee():
    """`atr_mode="wilder"` existe comme OUTIL DE DIAGNOSTIC (hors grille, jamais
    dans le manifeste ni dans la mesure). Son comportement est épinglé ici pour
    qu'il ne dérive pas en silence.

    Récurrence α = 1/P amorcée sur TR[0] (`ewm(adjust=False)`) — différence
    transitoire assumée avec l'amorce par moyenne simple du Wilder canonique,
    déclarée dans le docstring de `strategy.py` et les notes du manifeste.
    Valeurs attendues calculées à la main."""
    K = 60
    df = _put(_flat(200), K, o=1999.0, h=2003.0, l=1999.0, c=2002.9)
    _, data = _run(df, atr_mode="wilder")
    a = data["atr_ref"]
    # TR = 1,0 partout, sauf TR[K] = 4,0 et
    # TR[K+1] = max(1,0 ; |2000,5 − 2002,9| = 2,4 ; |1999,5 − 2002,9| = 3,4) = 3,4.
    # α = 0,1 ; le fond vaut 1,0 depuis la barre 0, donc :
    #   atr[K]   = 0,9 × 1,0  + 0,1 × 4,0 = 1,3
    #   atr[K+1] = 0,9 × 1,3  + 0,1 × 3,4 = 1,51
    #   atr[K+2] = 0,9 × 1,51 + 0,1 × 1,0 = 1,459
    assert a.iloc[K] == pytest.approx(1.0)
    assert a.iloc[K + 1] == pytest.approx(1.3)
    assert a.iloc[K + 2] == pytest.approx(1.51)
    assert a.iloc[K + 3] == pytest.approx(1.459)
    # la moyenne simple (défaut fidèle, iATR de MT5) donne autre chose
    _, sma = _run(df)
    assert sma["atr_ref"].iloc[K + 2] == pytest.approx(1.54)   # (8 × 1,0 + 4,0 + 3,4) / 10
    assert abs(float(sma["atr_ref"].iloc[K + 2]) - float(a.iloc[K + 2])) > 1e-6


def test_sans_decalage_le_signal_disparaitrait():
    """Garde-fou de comportement : une bougie de 2,8 × ATR passe le seuil 2,5 avec
    l'ATR décalé (1,0) ; si l'ATR incluait la bougie elle-même il vaudrait 1,18 et
    le seuil monterait à 2,95 — au-dessus de l'amplitude. Le signal doit exister."""
    df = _put(_flat(200), K, o=1999.0, h=2001.8, l=1999.0, c=2001.75)
    sigs, data = _run(df)
    assert len(sigs) == 1
    rng = float(df["high"].iloc[K] - df["low"].iloc[K])
    assert rng == pytest.approx(2.8)
    atr_inclusif = float(pd.Series([1.0] * (P - 1) + [rng]).mean())
    assert rng < 2.5 * atr_inclusif          # aurait été rejetée sans décalage
    assert rng > 2.5 * float(data["atr_ref"].iloc[K])


def test_troncature_ne_change_pas_les_signaux_passes():
    rng = np.random.default_rng(3)
    df = _flat(1200)
    # dispersion de grosses bougies aléatoires dans le fond régulier
    for i in rng.choice(np.arange(40, 1150), size=60, replace=False):
        amp = float(rng.uniform(3.5, 8.0))
        up = bool(rng.integers(0, 2))
        lo_, hi_ = PRICE - amp / 2, PRICE + amp / 2
        c = hi_ - amp * float(rng.uniform(0.0, 0.2)) if up else lo_ + amp * float(rng.uniform(0.0, 0.2))
        o = lo_ if up else hi_
        df = _put(df, int(i), o=o, h=hi_, l=lo_, c=c)
    for over in ({}, {"atr_mult": 2.0, "proximity": 0.35, "sl_pct": 0.01}):
        p = {**BASE, **over}
        for frac in (0.6, 0.8):
            T = int(len(df) * frac)
            a = Strategy(p); a._symbol = "XAUUSD"
            full = a.generate_signals(a.precompute(df, p), p, T)
            b = Strategy(p); b._symbol = "XAUUSD"
            trunc = b.generate_signals(b.precompute(df.iloc[:T].copy(), p), p, T)
            k = lambda xs: [(x.timestamp, x.side, x.entry, x.stop, x.target) for x in xs]
            assert k(full) == k(trunc)
            assert full, "l'échantillon de test doit contenir des signaux"


def test_on_bar_est_le_meme_code_que_le_backtest():
    df = _flat(400)
    for i in (350, 360, 370, 380):
        up = i % 20 == 0
        df = _put(df, i, o=1999.0 if up else 2003.0, h=2003.0, l=1999.0,
                  c=2002.9 if up else 1999.1)
    p = dict(BASE)
    strat = Strategy(p); strat._symbol = "XAUUSD"
    bt = {pd.Timestamp(s.timestamp): s
          for s in strat.generate_signals(strat.precompute(df, p), p, len(df))}
    hits = 0
    for i in range(len(df) - 80, len(df)):
        ctx = MarketContext(symbol="XAUUSD", timeframe="H1", bars=df.iloc[:i + 1],
                            now=pd.Timestamp(df.index[i]).to_pydatetime(), spread=0.9)
        live = strat.on_bar(ctx)
        exp = bt.get(pd.Timestamp(df.index[i]))
        assert (live is None) == (exp is None)
        if live is not None:
            hits += 1
            assert (live.side, live.entry, live.stop, live.target) == \
                   (exp.side, exp.entry, exp.stop, exp.target)
    assert hits >= 3


# ── (e) géométrie ───────────────────────────────────────────────────────────
def test_stop_et_cible_en_pourcent_du_prix_dentree():
    df = _flat(400)
    df = _put(df, 60, o=1999.0, h=2003.0, l=1999.0, c=2002.9)      # achat
    df = _put(df, 200, o=2003.0, h=2003.0, l=1999.0, c=1999.1)     # vente
    sigs, _ = _run(df, sl_pct=0.005, tp_pct=0.02)
    assert len(sigs) == 2
    for sg in sigs:
        if sg.side == Side.LONG:
            assert sg.stop == pytest.approx(sg.entry * 0.995)
            assert sg.target == pytest.approx(sg.entry * 1.02)
            assert sg.stop < sg.entry < sg.target
        else:
            assert sg.stop == pytest.approx(sg.entry * 1.005)
            assert sg.target == pytest.approx(sg.entry * 0.98)
            assert sg.target < sg.entry < sg.stop
        assert sg.rr == pytest.approx(4.0)      # RR 4 de ses réglages live


# ── (g) manifeste et bornes ─────────────────────────────────────────────────
def test_manifest_conforme():
    m = Strategy().manifest()
    assert m.magic_number == 130022
    assert m.strategy_id == "S022_balke_atr_candle"
    assert m.status == "BACKTESTED"        # mesuré le 2026-09-12 — mesuré ≠ validé (R10)
    assert m.symbols == ["XAUUSD"] and m.timeframe == "H1"
    assert int(np.prod([len(v) for v in m.param_grid.values()])) == 12
    for k in m.param_grid:
        assert m.default_params[k] in m.param_grid[k], f"défaut hors grille : {k}"
    # les réglages live de l'auteur, tels quels
    assert m.default_params["atr_period"] == ATR_PERIOD == 200
    assert m.default_params["atr_mult"] == 2.5
    assert m.default_params["proximity"] == 0.25
    assert (m.default_params["tp_pct"], m.default_params["sl_pct"]) == (0.02, 0.005)
    assert m.default_params["min_body_ratio"] == 0.0
    assert m.warmup_bars >= m.default_params["atr_period"] + WARMUP_MARGIN == WARMUP_BARS


@pytest.mark.parametrize("bad", [
    {"side_mode": "flat"}, {"atr_mode": "ema"}, {"sl_pct": 0.0}, {"tp_pct": -0.01},
    {"proximity": 0.0}, {"proximity": 1.5}, {"atr_mult": 0.0},
    {"atr_period": 1}, {"min_body_ratio": 1.5},
])
def test_parametre_invalide_leve(bad):
    with pytest.raises(ValueError):
        _run(_flat(200), **bad)


def test_parametre_inconnu_refuse():
    with pytest.raises(ValueError):
        Strategy({"trailing_pct": 0.01})
