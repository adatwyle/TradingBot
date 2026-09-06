"""
Tests de S018 — or v2 (méthode Doud).

    python -m pytest strategies/S018_gold_doud_v2/test_strategy.py -q

Ce qui est vérifié, et pourquoi c'est ça :

  (a) LA CELLULE NEUTRE EST LA V1 — signal par signal, sur les barres réelles.
      C'est la propriété qui rend toute la grille lisible : si elle tombe, un
      écart mesuré peut venir d'une réécriture au lieu de l'hypothèse, et la
      comparaison v1/v2 ne vaut plus rien. Test sauté quand les barres ne sont
      pas disponibles (CI ubuntu sans MT5 ni cache).
  (b) CHAQUE COMMUTATEUR FAIT CE QU'IL DIT — long_only ne produit aucun short,
      la session ne laisse passer que ses heures, l'équilibre entre en repli et
      dans sa fenêtre. Sur barres synthétiques, donc exécuté partout.
  (c) LE BIAIS JOURNALIER EST CAUSAL — la porte d'un jour lit la veille close,
      jamais la journée en cours. C'est le point qui casse en silence si on
      retire le `shift(1)` : les signaux resteraient plausibles et le backtest
      deviendrait faux.
  (d) LES BORNES DE LA GRILLE — un commutateur inconnu lève, il ne dégrade pas
      silencieusement vers un défaut.
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

from core.contracts.strategy import Side                              # noqa: E402
from strategies.S018_gold_doud_v2.strategy import (                   # noqa: E402
    EQUILIBRIUM_RATIO, PULLBACK_MAX_BARS, SESSION_DOUD, Strategy, _daily_bias,
)

SEALED_CELL = {
    "donchian": 40, "adx_min": 20.0, "tp_m": 4.0, "sl_m": 1.5,
    "atr_vol_ratio": 0.8, "adx_rising_lookback": 5,
    "rsi_long_max": 75.0, "rsi_short_min": 25.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _synthetic_bars(n: int = 1200, seed: int = 20260906) -> pd.DataFrame:
    """Barres H1 synthétiques : segments de tendance alternés + bruit.

    Un pur bruit blanc ne franchit presque jamais la porte ADX-croissant, et les
    tests d'invariants seraient vides sans en avoir l'air. Les segments
    garantissent des cassures dans les deux sens.
    """
    rng = np.random.default_rng(seed)
    drift = np.concatenate([
        np.full(150, +0.9), np.full(80, 0.0), np.full(150, -0.9),
        np.full(80, 0.0), np.full(150, +0.6), np.full(80, 0.0),
        np.full(150, -0.6), np.full(80, 0.0),
    ])
    drift = np.resize(drift, n)
    close = 1800.0 + np.cumsum(drift + rng.normal(0.0, 2.2, n))
    high = close + np.abs(rng.normal(1.6, 0.9, n))
    low = close - np.abs(rng.normal(1.6, 0.9, n))
    opens = np.concatenate([[close[0]], close[:-1]])
    idx = pd.date_range("2024-01-01 00:00", periods=n, freq="h")
    return pd.DataFrame({"open": opens, "high": high, "low": low, "close": close,
                         "tick_volume": 100.0, "spread": 25.0}, index=idx)


def _signals(params: dict, df: pd.DataFrame | None = None):
    df = _synthetic_bars() if df is None else df
    strat = Strategy({**SEALED_CELL, **params})
    strat._symbol = "XAUUSD"
    data = strat.precompute(df, strat.params)
    return strat.generate_signals(data, strat.params, len(df)), data, df


def _real_bars():
    """Barres XAUUSD H1 réelles, ou skip. Sans MT5 ni cache (CI), `load_bars`
    lève sur l'import du module broker : c'est une absence de données, pas un
    échec de la stratégie."""
    try:
        from core.data.source import load_bars
        df = load_bars("XAUUSD", "H1")
    except Exception as e:                              # pragma: no cover — CI
        pytest.skip(f"barres XAUUSD indisponibles : {type(e).__name__}")
    if df is None or len(df) < 5000:                    # pragma: no cover — CI
        pytest.skip("barres XAUUSD indisponibles ou trop courtes")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# (a) La cellule neutre EST la v1
# ─────────────────────────────────────────────────────────────────────────────

def test_cellule_neutre_reproduit_la_v1():
    """Sur les barres réelles, la cellule neutre de S018 produit exactement les
    signaux de S011 aux paramètres scellés du forward or.

    Égalité EXACTE, pas approchée : S018 importe les indicateurs de S011 et
    applique la même arithmétique dans le même ordre. Un `pytest.approx` ici
    masquerait précisément le genre de dérive qu'on veut interdire.
    """
    df = _real_bars()
    from strategies.S011_legacy_breakout.strategy import Strategy as V1

    v1 = V1({**SEALED_CELL, "er_min": 0.0, "fr_max": 1.0})
    v1._symbol = "XAUUSD"
    s1 = v1.generate_signals(v1.precompute(df, v1.params), v1.params, len(df))

    s2, _, _ = _signals({"entry_mode": "breakout", "channel_source": "extremes",
                         "side_mode": "both", "session_filter": "off",
                         "htf_bias": "off"}, df)

    def key(s):
        return (pd.Timestamp(s.timestamp), s.side, s.entry, s.stop, s.target)

    assert len(s1) > 100, "témoin vide : le test ne prouverait rien"
    assert [key(s) for s in s2] == [key(s) for s in s1]


# ─────────────────────────────────────────────────────────────────────────────
# (b) Chaque commutateur fait ce qu'il dit
# ─────────────────────────────────────────────────────────────────────────────

def test_le_synthetique_produit_bien_des_signaux_des_deux_cotes():
    """Garde-fou des tests suivants : sans signaux, leurs invariants sont vides."""
    sigs, _, _ = _signals({})
    assert len(sigs) >= 5
    assert {s.side for s in sigs} == {Side.LONG, Side.SHORT}


def test_long_only_supprime_tous_les_shorts():
    ref, _, _ = _signals({"side_mode": "both"})
    lo, _, _ = _signals({"side_mode": "long_only"})
    assert any(s.side == Side.SHORT for s in ref)
    assert all(s.side == Side.LONG for s in lo)
    assert [s.timestamp for s in lo] == [s.timestamp for s in ref
                                         if s.side == Side.LONG]


def test_session_doud_ne_laisse_passer_que_ses_heures():
    ref, _, _ = _signals({"session_filter": "off"})
    doud, _, _ = _signals({"session_filter": "doud"})
    assert all(pd.Timestamp(s.timestamp).hour in SESSION_DOUD for s in doud)
    assert any(pd.Timestamp(s.timestamp).hour not in SESSION_DOUD for s in ref), \
        "le filtre ne retire rien : le test ne prouverait rien"
    assert len(doud) < len(ref)


def test_canal_sur_les_corps_est_plus_etroit_que_sur_les_meches():
    """« La structure, pas la mèche » : un canal de closes est contenu dans le
    canal d'extrêmes, donc cassé plus souvent."""
    _, d_ext, _ = _signals({"channel_source": "extremes"})
    _, d_bod, _ = _signals({"channel_source": "bodies"})
    ok = np.isfinite(d_ext["dh_prev"]) & np.isfinite(d_bod["dh_prev"])
    assert (d_bod["dh_prev"][ok] <= d_ext["dh_prev"][ok] + 1e-9).all()
    assert (d_bod["dl_prev"][ok] >= d_ext["dl_prev"][ok] - 1e-9).all()


def test_equilibre_entre_en_repli_et_dans_sa_fenetre():
    """Trois propriétés de D4, sur barres synthétiques :
       — l'entrée est plus favorable que le close de cassure (c'est tout
         l'intérêt : on ne court pas après le marché) ;
       — l'attente ne dépasse jamais la fenêtre de validité ;
       — l'équilibre tombe entre l'ancrage et l'extension de la jambe.
    """
    sigs, _, df = _signals({"entry_mode": "equilibrium"})
    assert len(sigs) >= 3, "pas assez de replis pour conclure"
    close = df["close"].to_numpy()
    for s in sigs:
        m = s.meta
        i = m["breakout_idx"]
        assert 1 <= m["bars_waited"] <= PULLBACK_MAX_BARS
        lo, hi = sorted((m["leg_anchor"], m["leg_extension"]))
        assert lo - 1e-9 <= m["equilibrium"] <= hi + 1e-9
        if s.side == Side.LONG:
            assert s.entry <= close[i] + 1e-9
        else:
            assert s.entry >= close[i] - 1e-9


def test_equilibre_et_cassure_ne_donnent_pas_les_memes_entrees():
    brk, _, _ = _signals({"entry_mode": "breakout"})
    eq, _, _ = _signals({"entry_mode": "equilibrium"})
    assert {pd.Timestamp(s.timestamp) for s in eq} != {pd.Timestamp(s.timestamp)
                                                       for s in brk}


def test_un_seul_setup_en_attente_a_la_fois():
    """Deux entrées d'équilibre ne peuvent pas naître de la même cassure, et
    une cassure survenue pendant l'attente est ignorée : sans cette règle une
    impulsion prolongée empilerait N setups quasi identiques."""
    sigs, _, _ = _signals({"entry_mode": "equilibrium"})
    origins = [s.meta["breakout_idx"] for s in sigs]
    assert len(origins) == len(set(origins))
    assert origins == sorted(origins)


# ─────────────────────────────────────────────────────────────────────────────
# (c) Le biais journalier est causal
# ─────────────────────────────────────────────────────────────────────────────

def test_biais_journalier_lit_la_veille_jamais_le_jour_courant():
    """La porte du jour J doit valoir le signe (close − EMA) du jour J−1.

    Vérification directe, sans passer par la stratégie : c'est une propriété du
    décalage, et c'est elle qui garantit qu'aucune barre du jour J n'entre dans
    sa propre autorisation d'entrée.
    """
    df = _synthetic_bars(n=24 * 60)
    bias = _daily_bias(df, ema_days=5)
    daily = df["close"].resample("1D").last().dropna()
    ema = daily.ewm(span=5, adjust=False).mean()
    expected = np.sign(daily - ema)

    days = pd.Series(bias, index=df.index).groupby(df.index.normalize()).first()
    checked = 0
    for day, value in days.items():
        pos = daily.index.get_indexer([day])[0]
        if pos <= 0:
            continue
        assert value == expected.iloc[pos - 1], f"biais du {day} lit le mauvais jour"
        checked += 1
    assert checked > 30


def test_biais_journalier_filtre_effectivement():
    ref, _, _ = _signals({"htf_bias": "off"})
    gated, _, _ = _signals({"htf_bias": "daily_ema"})
    assert len(gated) < len(ref)
    assert {pd.Timestamp(s.timestamp) for s in gated} <= {pd.Timestamp(s.timestamp)
                                                          for s in ref}


# ─────────────────────────────────────────────────────────────────────────────
# (d) Contrat et bornes
# ─────────────────────────────────────────────────────────────────────────────

def test_manifest_conforme_au_contrat():
    m = Strategy().manifest()
    assert m.magic_number == 130018
    assert m.strategy_id == "S018_gold_doud_v2"
    assert m.symbols == ["XAUUSD"] and m.timeframe == "H1"
    assert m.status == "RESEARCH"
    assert set(m.param_grid) == {"entry_mode", "channel_source", "side_mode",
                                 "session_filter", "htf_bias"}
    cells = int(np.prod([len(v) for v in m.param_grid.values()]))
    assert cells == 32
    # Les défauts DOIVENT être la cellule neutre : c'est ce qui fait qu'une
    # instanciation sans paramètre se comporte comme la v1.
    for k in m.param_grid:
        assert m.default_params[k] == m.param_grid[k][0]


def test_tout_signal_porte_un_stop_du_bon_cote():
    for mode in ("breakout", "equilibrium"):
        sigs, _, _ = _signals({"entry_mode": mode})
        for s in sigs:
            assert s.stop is not None and s.risk_distance > 0
            if s.side == Side.LONG:
                assert s.stop < s.entry < s.target
            else:
                assert s.target < s.entry < s.stop
            assert abs(s.rr - SEALED_CELL["tp_m"] / SEALED_CELL["sl_m"]) < 1e-9


@pytest.mark.parametrize("bad", [
    {"entry_mode": "retest"}, {"channel_source": "wicks"},
    {"side_mode": "short_only"}, {"session_filter": "london"},
    {"htf_bias": "weekly"},
])
def test_commutateur_inconnu_leve(bad):
    """Pas de dégradation silencieuse vers un défaut : une faute de frappe dans
    une grille doit casser, pas produire des chiffres de la cellule neutre."""
    with pytest.raises(ValueError):
        _signals(bad)


def test_troncature_ne_change_pas_les_signaux_passes():
    """Invariant R1, version rapide et synthétique. La version complète tourne
    sur données réelles via `backtests/run_checks.py` et son résultat est
    archivé dans `backtests/causality.txt`."""
    df = _synthetic_bars()
    for mode in ("breakout", "equilibrium"):
        params = {**SEALED_CELL, "entry_mode": mode, "channel_source": "extremes",
                  "side_mode": "both", "session_filter": "off", "htf_bias": "daily_ema"}
        strat = Strategy(params)
        strat._symbol = "XAUUSD"
        for frac in (0.7, 0.85):
            T = int(len(df) * frac)
            full = strat.generate_signals(strat.precompute(df, params), params, T)
            trunc_strat = Strategy(params)
            trunc_strat._symbol = "XAUUSD"
            trunc = trunc_strat.generate_signals(
                trunc_strat.precompute(df.iloc[:T].copy(), params), params, T)
            assert [(s.timestamp, s.side, s.entry, s.stop) for s in full] == \
                   [(s.timestamp, s.side, s.entry, s.stop) for s in trunc], \
                   f"fuite en mode {mode} à la coupe {frac}"


def test_on_bar_est_le_meme_code_que_le_backtest():
    """R5 : la barre live renvoie exactement la décision du chemin backtest."""
    from core.contracts.strategy import MarketContext

    df = _synthetic_bars()
    params = {**SEALED_CELL, "entry_mode": "breakout", "channel_source": "extremes",
              "side_mode": "both", "session_filter": "off", "htf_bias": "off"}
    strat = Strategy(params)
    strat._symbol = "XAUUSD"
    bt = {pd.Timestamp(s.timestamp): s
          for s in strat.generate_signals(strat.precompute(df, params), params, len(df))}

    checked = matched = 0
    for i in range(len(df) - 60, len(df)):
        ctx = MarketContext(symbol="XAUUSD", timeframe="H1", bars=df.iloc[:i + 1],
                            now=pd.Timestamp(df.index[i]).to_pydatetime(), spread=0.25)
        live = strat.on_bar(ctx)
        expected = bt.get(pd.Timestamp(df.index[i]))
        assert (live is None) == (expected is None)
        if live is not None:
            assert (live.side, live.entry, live.stop, live.target) == \
                   (expected.side, expected.entry, expected.stop, expected.target)
            matched += 1
        checked += 1
    assert checked == 60
