"""
Tests de S023 — Turnaround Tuesday (achat du lundi sous la SMA journalière).

    python -m pytest strategies/S023_balke_turnaround_tuesday -q

(a) la règle fait ce qu'elle dit : lundi seulement, achat seulement, un par jour ;
(b) la SMA est journalière, SIMPLE, sur les jours COMPLETS — modifier les barres
    du lundi lui-même ne peut pas changer la SMA qu'il utilise ;
(c) les deux modèles d'entrée choisissent la barre qu'ils annoncent ;
(d) la séance du DAX (08:00-21:00, sans dimanche) est traitée comme un jour ;
(e) la garde catastrophe est à la bonne distance, du bon côté, sans cible ;
(f) causalité : troncature invariante, on_bar = backtest ;
(g) le manifeste est la source de vérité (magic, 18 cellules, défauts dans la grille) ;
(h) bornes : paramètre inconnu ou hors bornes lève.
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

from core.contracts.strategy import MarketContext, Side                        # noqa: E402
from strategies.S023_balke_turnaround_tuesday.strategy import Strategy         # noqa: E402

BASE = {"sma_period": 9, "entry_mode": "first_bar", "guard_pct": 0.05, "open_dow": 0}


# ── fabriques de barres ─────────────────────────────────────────────────────
def _bars_24(days: int = 120, seed: int = 3, price: float = 20000.0,
             start: str = "2024-01-01") -> pd.DataFrame:
    """Indice US : 24 barres par jour civil, lundi → vendredi (pas de week-end)."""
    idx = pd.date_range(start, periods=days * 24, freq="h")
    idx = idx[idx.dayofweek < 5]
    rng = np.random.default_rng(seed)
    close = price + rng.normal(0, 25, len(idx)).cumsum()
    return _ohlc(close, idx, rng)


def _bars_dax(days: int = 160, seed: int = 5, price: float = 18000.0) -> pd.DataFrame:
    """DAX : séance 08:00-21:00 (14 barres), jamais le week-end."""
    idx = pd.date_range("2024-01-01", periods=days * 24, freq="h")
    idx = idx[(idx.dayofweek < 5) & (idx.hour >= 8) & (idx.hour <= 21)]
    rng = np.random.default_rng(seed)
    close = price + rng.normal(0, 20, len(idx)).cumsum()
    return _ohlc(close, idx, rng)


def _ohlc(close, idx, rng) -> pd.DataFrame:
    high = close + np.abs(rng.normal(20, 5, len(idx)))
    low = close - np.abs(rng.normal(20, 5, len(idx)))
    opens = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": opens, "high": high, "low": low, "close": close,
                         "tick_volume": 100.0, "spread": 120.0}, index=idx)


def _run(df, **over):
    p = {**BASE, **over}
    s = Strategy(p)
    s._symbol = "US30"
    data = s.precompute(df, p)
    return s.generate_signals(data, p, len(df)), data


# ── (a) la règle ────────────────────────────────────────────────────────────
def test_lundi_seulement_et_achat_seulement():
    """Le jour d'ouverture est le lundi, le sens est l'achat, sans exception."""
    df = _bars_24()
    sigs, _ = _run(df)
    assert sigs, "aucun signal : la fabrique de barres ne produit pas de lundi qualifiant"
    assert all(pd.Timestamp(s.timestamp).dayofweek == 0 for s in sigs)
    assert all(s.side is Side.LONG for s in sigs)
    assert all(s.target is None for s in sigs), "la source n'a pas de take profit"


def test_un_seul_signal_par_lundi_en_any_bar():
    """« any_bar » relit la condition à chaque barre mais n'entre qu'UNE fois."""
    df = _bars_24()
    sigs, _ = _run(df, entry_mode="any_bar")
    days = [pd.Timestamp(s.timestamp).normalize() for s in sigs]
    assert len(days) == len(set(days))


# ── (b) la SMA journalière ──────────────────────────────────────────────────
def test_sma_est_la_moyenne_simple_des_n_derniers_jours_complets():
    """Valeur recalculée à la main : moyenne des N clôtures journalières
    strictement antérieures au jour de la barre."""
    df = _bars_24()
    _, data = _run(df, sma_period=9)
    dclose = df["close"].groupby(df.index.normalize()).last()
    for i in (900, 1400, len(df) - 5):
        d = df.index[i].normalize()
        prior = dclose.index[dclose.index < d]
        attendu = float(dclose.loc[prior[-9:]].mean())
        assert data["prev_day_sma"].iloc[i] == pytest.approx(attendu, rel=1e-12)
        assert data["prev_day_close"].iloc[i] == pytest.approx(float(dclose.loc[prior[-1]]), rel=1e-12)


def test_modifier_le_lundi_ne_change_pas_la_sma_qu_il_utilise():
    """Causalité du filtre : la SMA d'un lundi ne porte que sur des jours
    ANTÉRIEURS. Déformer toutes les barres de ce lundi ne doit rien y changer."""
    df = _bars_24()
    sigs, data = _run(df)
    assert sigs
    ts = pd.Timestamp(sigs[len(sigs) // 2].timestamp)
    jour = ts.normalize()

    df2 = df.copy()
    m = df2.index.normalize() == jour
    for c in ("open", "high", "low", "close"):
        df2.loc[m, c] = df2.loc[m, c] * 1.25
    _, data2 = _run(df2)

    i = df.index.get_loc(ts)
    assert data2["prev_day_sma"].iloc[i] == pytest.approx(float(data["prev_day_sma"].iloc[i]), rel=1e-12)
    assert data2["prev_day_close"].iloc[i] == pytest.approx(float(data["prev_day_close"].iloc[i]), rel=1e-12)


def test_filtre_desactive_prend_tous_les_lundis():
    """sma_period=0 = cellule de RÉFÉRENCE : chaque lundi, sans condition."""
    df = _bars_24()
    ref, _ = _run(df, sma_period=0)
    filtre, _ = _run(df, sma_period=9)
    lundis = {d for d in df.index.normalize().unique() if d.dayofweek == 0}
    # tous les lundis sauf le premier (aucun jour complet antérieur)
    assert len(ref) >= len(lundis) - 1
    assert len(filtre) < len(ref), "le filtre doit retirer des lundis, pas tous les garder"
    assert {pd.Timestamp(s.timestamp) for s in filtre} <= {pd.Timestamp(s.timestamp) for s in ref}


# ── (c) les deux modèles d'entrée ───────────────────────────────────────────
def _frame(jours: list[tuple[str, list[float]]]) -> pd.DataFrame:
    """Barres H1 FABRIQUÉES À LA MAIN : une liste de (date, clôtures horaires).

    Les fixtures en marche aléatoire sont trop lisses pour séparer `first_bar` de
    `any_bar` — un mutant qui rabattrait `any_bar` sur `first_bar` y passerait
    inaperçu. Ici, le chemin intrajournalier du lundi est posé au pouce près.
    """
    idx, close = [], []
    for d, cl in jours:
        base = pd.Timestamp(d)
        for h, c in enumerate(cl):
            idx.append(base + pd.Timedelta(hours=h))
            close.append(float(c))
    idx = pd.DatetimeIndex(idx)
    close = np.array(close)
    opens = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame({"open": opens, "high": np.maximum(opens, close) + 0.2,
                         "low": np.minimum(opens, close) - 0.2, "close": close,
                         "tick_volume": 100.0, "spread": 10.0}, index=idx)


# 2023-12-27 mercredi · 12-28 jeudi · 12-29 vendredi · 2024-01-01 LUNDI
# SMA3 au lundi = moyenne des clôtures mer/jeu/ven = 100.0 dans les deux cas.
def test_divergence_lundi_ouvre_AU_DESSUS_puis_passe_SOUS_la_sma():
    """Vendredi clôture à 101 (au-dessus de la SMA 100) : `first_bar` ne prend
    rien. Le lundi ouvre au-dessus puis passe sous 100 en séance : `any_bar`
    entre à la barre du franchissement, et à celle-là seulement."""
    df = _frame([("2023-12-27", [99.0] * 3), ("2023-12-28", [100.0] * 3),
                 ("2023-12-29", [101.0] * 3),
                 ("2024-01-01", [101.0, 100.5, 99.0, 99.5, 102.0])])
    _, data = _run(df, sma_period=3)
    lundi0 = pd.Timestamp("2024-01-01 00:00")
    i0 = df.index.get_loc(lundi0)
    assert data["prev_day_sma"].iloc[i0] == pytest.approx(100.0)
    assert data["prev_day_close"].iloc[i0] == pytest.approx(101.0)

    sigs_f, _ = _run(df, sma_period=3, entry_mode="first_bar")
    assert sigs_f == [], "first_bar compare la clôture de vendredi (101 ≥ 100) : rien à prendre"

    sigs_a, _ = _run(df, sma_period=3, entry_mode="any_bar")
    assert len(sigs_a) == 1
    assert pd.Timestamp(sigs_a[0].timestamp) == pd.Timestamp("2024-01-01 02:00")
    assert sigs_a[0].entry == pytest.approx(99.0)


def test_divergence_miroir_lundi_ouvre_SOUS_mais_remonte_AU_DESSUS():
    """Cas miroir : vendredi clôture à 99 (sous la SMA 100) → `first_bar` entre à
    la première barre. Mais le lundi cote au-dessus de 100 toute la séance :
    `any_bar` ne trouve aucune barre qualifiante et ne prend RIEN."""
    df = _frame([("2023-12-27", [101.0] * 3), ("2023-12-28", [100.0] * 3),
                 ("2023-12-29", [99.0] * 3),
                 ("2024-01-01", [101.0, 102.0, 103.0, 102.5, 104.0])])
    _, data = _run(df, sma_period=3)
    i0 = df.index.get_loc(pd.Timestamp("2024-01-01 00:00"))
    assert data["prev_day_sma"].iloc[i0] == pytest.approx(100.0)
    assert data["prev_day_close"].iloc[i0] == pytest.approx(99.0)

    sigs_f, _ = _run(df, sma_period=3, entry_mode="first_bar")
    assert len(sigs_f) == 1
    assert pd.Timestamp(sigs_f[0].timestamp) == pd.Timestamp("2024-01-01 00:00")
    assert sigs_f[0].entry == pytest.approx(101.0)

    sigs_a, _ = _run(df, sma_period=3, entry_mode="any_bar")
    assert sigs_a == [], "aucune barre du lundi ne clôture sous la SMA : any_bar reste flat"


def test_first_bar_entre_a_la_premiere_barre_du_jour_serveur():
    df = _bars_24()
    sigs, _ = _run(df, entry_mode="first_bar")
    assert sigs
    for s in sigs:
        ts = pd.Timestamp(s.timestamp)
        meme_jour = df.index[df.index.normalize() == ts.normalize()]
        assert ts == meme_jour[0]


def test_first_bar_compare_la_cloture_de_vendredi_any_bar_le_prix_courant():
    """Les deux lectures du « check constantly » ne comparent pas la même chose —
    et chacune compare ce qu'elle annonce."""
    df = _bars_24()
    sigs_f, data = _run(df, entry_mode="first_bar")
    sigs_a, _ = _run(df, entry_mode="any_bar")
    for s in sigs_f:
        i = df.index.get_loc(pd.Timestamp(s.timestamp))
        assert data["prev_day_close"].iloc[i] < data["prev_day_sma"].iloc[i]
    for s in sigs_a:
        i = df.index.get_loc(pd.Timestamp(s.timestamp))
        assert data["close"].iloc[i] < data["prev_day_sma"].iloc[i]
    # la première barre qualifiante du jour, pas une autre
    for s in sigs_a:
        ts = pd.Timestamp(s.timestamp)
        i = df.index.get_loc(ts)
        jour = df.index.normalize() == ts.normalize()
        avant = np.flatnonzero(jour & (np.arange(len(df)) < i))
        assert not any(data["close"].iloc[k] < data["prev_day_sma"].iloc[k] for k in avant)


# ── (d) la séance du DAX ────────────────────────────────────────────────────
def test_dax_session_08_21_premiere_barre_a_8h():
    """Le DAX ne cote pas 24/24 : « première barre du lundi » vaut 08:00,
    et la clôture journalière est celle de 21:00."""
    df = _bars_dax()
    sigs, data = _run(df, sma_period=40)
    assert sigs
    assert all(pd.Timestamp(s.timestamp).hour == 8 for s in sigs)
    dclose = df["close"].groupby(df.index.normalize()).last()
    assert all(h == 21 for h in df.groupby(df.index.normalize()).apply(lambda g: g.index[-1].hour))
    i = df.index.get_loc(pd.Timestamp(sigs[-1].timestamp))
    d = df.index[i].normalize()
    prior = dclose.index[dclose.index < d]
    assert data["prev_day_sma"].iloc[i] == pytest.approx(float(dclose.loc[prior[-40:]].mean()), rel=1e-12)


# ── (e) la garde catastrophe ────────────────────────────────────────────────
@pytest.mark.parametrize("guard", [0.03, 0.05, 0.10])
def test_geometrie_de_la_garde(guard):
    df = _bars_24()
    sigs, _ = _run(df, guard_pct=guard)
    assert sigs
    for s in sigs:
        assert s.stop == pytest.approx(s.entry * (1 - guard), rel=1e-12)
        assert s.stop < s.entry
        assert s.target is None
        assert s.risk_distance == pytest.approx(s.entry * guard, rel=1e-12)


# ── (f) causalité et conformance ────────────────────────────────────────────
@pytest.mark.parametrize("mode", ["first_bar", "any_bar"])
def test_invariance_par_troncature(mode):
    """generate_signals(precompute(df), p, T) == generate_signals(precompute(df[:T]), p, T)."""
    df = _bars_24()
    p = {**BASE, "entry_mode": mode}
    s = Strategy(p)
    full = s.precompute(df, p)
    for frac in (0.6, 0.75, 0.9):
        T = int(len(df) * frac)
        a = s.generate_signals(full, p, T)
        b = s.generate_signals(s.precompute(df.iloc[:T].copy(), p), p, T)
        assert len(a) == len(b)
        for x, y in zip(a, b):
            assert pd.Timestamp(x.timestamp) == pd.Timestamp(y.timestamp)
            assert x.entry == pytest.approx(y.entry) and x.stop == pytest.approx(y.stop)


def test_on_bar_est_le_meme_code_que_le_backtest():
    """R5 : garantie structurelle (on_bar délègue), vérifiée sur les 80
    dernières barres."""
    df = _bars_24()
    p = dict(BASE)
    s = Strategy(p)
    s._symbol = "US30"
    attendus = {pd.Timestamp(x.timestamp) for x in s.generate_signals(s.precompute(df, p), p, len(df))}
    for i in range(len(df) - 80, len(df)):
        ctx = MarketContext(symbol="US30", timeframe="H1", bars=df.iloc[:i + 1],
                            now=df.index[i].to_pydatetime(), spread=12.0)
        got = s.on_bar(ctx)
        assert (got is not None) == (df.index[i] in attendus), f"divergence à {df.index[i]}"


# ── (g) le manifeste ────────────────────────────────────────────────────────
def test_manifeste_source_de_verite():
    m = Strategy().manifest()
    assert m.magic_number == 130023
    assert m.strategy_id == "S023_balke_turnaround_tuesday"
    assert m.symbols == ["DAX", "NASDAQ", "US30"] and m.timeframe == "H1"
    assert m.status == "BACKTESTED"           # mesuré ; « mesuré, pas validé » (R10)
    g = m.param_grid
    assert len(g["sma_period"]) * len(g["entry_mode"]) * len(g["guard_pct"]) == 18
    assert {9, 25, 40} == set(g["sma_period"])     # ses trois périodes live
    for k, v in m.default_params.items():          # les défauts sont DANS la grille
        if k in g:
            assert v in g[k], f"défaut {k}={v} hors grille"


# ── (h) bornes ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("bad", [
    {"entry_mode": "every_bar"},
    {"guard_pct": 0.0},
    {"guard_pct": 1.0},
    {"guard_pct": -0.05},
    {"sma_period": -1},
    {"open_dow": 7},
])
def test_parametre_hors_bornes_leve(bad):
    with pytest.raises(ValueError):
        Strategy({**BASE, **bad})


def test_parametre_inconnu_leve():
    with pytest.raises(ValueError):
        Strategy({**BASE, "take_profit_pct": 0.02})
