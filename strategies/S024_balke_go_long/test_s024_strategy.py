"""
Tests de S024 — « Go Long » : achat d'indice à heure fixe (René Balke).

    python -m pytest strategies/S024_balke_go_long -q

(a) la règle fait ce qu'elle dit : un achat par jour serveur, à la barre d'heure
    fixe, et pas ailleurs — y compris sur une séance DAX 08-21 ;
(b) les trous de calendrier (week-end, férié, barre orpheline du dimanche soir)
    ne produisent ni trade ni exception ;
(c) géométrie : garde catastrophe sous l'entrée, aucune cible, jamais de vente ;
(d) causalité : troncature invariante, on_bar = backtest ;
(e) manifeste et bornes : 130024, 6 cellules, défauts dans la grille, valeur
    hors bornes -> ValueError (pas de repli muet).
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

from core.contracts.strategy import MarketContext, Side                 # noqa: E402
from strategies.S024_balke_go_long.strategy import Strategy             # noqa: E402

BASE = {"start_hour": 0, "entry_hour_offset": 0, "guard_pct": 0.05}


# ─────────────────────────────────────────────────────────────────────────────
# Fabriques de barres — on construit le CALENDRIER, c'est lui que la règle lit.
# ─────────────────────────────────────────────────────────────────────────────
def _frame(stamps, seed: int = 7, price: float = 20000.0) -> pd.DataFrame:
    idx = pd.DatetimeIndex(stamps)
    rng = np.random.default_rng(seed)
    close = price + rng.normal(0, 25, len(idx)).cumsum()
    return pd.DataFrame(
        {"open": np.concatenate([[close[0]], close[:-1]]),
         "high": close + np.abs(rng.normal(20, 5, len(idx))),
         "low": close - np.abs(rng.normal(20, 5, len(idx))),
         "close": close, "tick_volume": 100.0, "spread": 12.0},
        index=idx)


def _us_session(days: int = 12, start="2024-01-01") -> pd.DataFrame:
    """Profil NASDAQ / US30 mesuré : 23 barres par jour, heures 0 -> 22."""
    stamps = []
    for d in pd.date_range(start, periods=days, freq="D"):
        stamps += [d + pd.Timedelta(hours=h) for h in range(23)]
    return _frame(stamps)


def _dax_session(days: int = 12, start="2024-01-01") -> pd.DataFrame:
    """Profil DAX mesuré : 14 barres par jour, heures 8 -> 21."""
    stamps = []
    for d in pd.date_range(start, periods=days, freq="D"):
        stamps += [d + pd.Timedelta(hours=h) for h in range(8, 22)]
    return _frame(stamps, seed=11)


def _run(df: pd.DataFrame, **over):
    p = {**BASE, **over}
    s = Strategy(p)
    s._symbol = "NASDAQ"
    data = s.precompute(df, p)
    return s.generate_signals(data, p, len(df)), data


# ─────────────────────────────────────────────────────────────────────────────
# (a) la règle
# ─────────────────────────────────────────────────────────────────────────────
def test_un_signal_par_jour_sur_la_premiere_barre():
    """« every single day it opens a buy position » [05:24] : un, et un seul."""
    df = _us_session(days=12)
    sigs, _ = _run(df)

    assert len(sigs) == 12, "il manque (ou il y a en trop) un jour de séance"
    jours = [pd.Timestamp(s.timestamp).normalize() for s in sigs]
    assert len(set(jours)) == 12, "deux signaux le même jour serveur"
    assert all(pd.Timestamp(s.timestamp).hour == 0 for s in sigs), \
        "le signal n'est pas sur la première barre du jour"
    # et c'est bien la PREMIÈRE barre du jour dans l'index, pas une autre
    for s in sigs:
        day = pd.Timestamp(s.timestamp).normalize()
        first = df.loc[df.index.normalize() == day].index[0]
        assert pd.Timestamp(s.timestamp) == first


def test_offset_1_prend_la_seconde_barre():
    """Son 01:05 tombe DANS la barre 01:00 : l'offset expose le ±1 h."""
    df = _us_session(days=10)
    s0, _ = _run(df, entry_hour_offset=0)
    s1, _ = _run(df, entry_hour_offset=1)

    assert len(s0) == len(s1) == 10
    assert all(pd.Timestamp(s.timestamp).hour == 1 for s in s1)
    # décalage d'exactement une barre, jour par jour
    for a, b in zip(s0, s1):
        assert pd.Timestamp(b.timestamp) - pd.Timestamp(a.timestamp) == pd.Timedelta(hours=1)


def test_seance_dax_08_21():
    """DE40 ouvre à 09:05 chez lui : chez nous, première barre de séance = 08:00."""
    df = _dax_session(days=10)

    # start_hour=8 : un signal par jour, sur la barre 08:00
    sigs, _ = _run(df, start_hour=8)
    assert len(sigs) == 10
    assert all(pd.Timestamp(s.timestamp).hour == 8 for s in sigs)

    # start_hour=0 (réglage des indices US) sur une séance DAX : aucune barre à
    # 00:00 -> aucun trade. Le harnais DOIT passer start_hour=8, et si jamais il
    # l'oublie la stratégie ne fabrique rien en silence.
    vide, _ = _run(df, start_hour=0)
    assert vide == []

    # offset 1 -> barre 09:00
    s1, _ = _run(df, start_hour=8, entry_hour_offset=1)
    assert all(pd.Timestamp(s.timestamp).hour == 9 for s in s1)


# ─────────────────────────────────────────────────────────────────────────────
# (b) les trous de calendrier
# ─────────────────────────────────────────────────────────────────────────────
def test_weekend_ferie_et_barre_orpheline():
    """Pas de barre à l'heure d'entrée -> pas de trade, et surtout pas d'exception.

    Reproduit trois anomalies réellement présentes dans le cache mesuré :
    le week-end (aucune barre), un férié tronqué (séance qui démarre à 08:00 au
    lieu de 00:00), et la barre orpheline du dimanche 23:00 (18 occurrences sur
    1331 jours pour NASDAQ et US30).
    """
    stamps = []
    # lundi + mardi complets
    for d in ("2024-01-01", "2024-01-02"):
        stamps += [pd.Timestamp(d) + pd.Timedelta(hours=h) for h in range(23)]
    # mercredi férié tronqué : la séance ne démarre qu'à 08:00
    stamps += [pd.Timestamp("2024-01-03") + pd.Timedelta(hours=h) for h in range(8, 23)]
    # (jeudi et vendredi absents = trou de calendrier)
    # dimanche : une seule barre à 23:00
    stamps += [pd.Timestamp("2024-01-07") + pd.Timedelta(hours=23)]
    # lundi suivant complet
    stamps += [pd.Timestamp("2024-01-08") + pd.Timedelta(hours=h) for h in range(23)]

    df = _frame(stamps)
    sigs, _ = _run(df)                      # ne doit pas lever

    jours = sorted({str(pd.Timestamp(s.timestamp).date()) for s in sigs})
    assert jours == ["2024-01-01", "2024-01-02", "2024-01-08"], \
        "un jour sans barre à l'heure d'entrée a produit un trade"
    assert all(pd.Timestamp(s.timestamp).hour == 0 for s in sigs)


def test_frame_vide_ou_minuscule_ne_casse_pas():
    df = _frame([pd.Timestamp("2024-01-01")])
    sigs, _ = _run(df)
    assert len(sigs) == 1          # une barre à 00:00 = un signal, le moteur le refusera
    vide = _frame([pd.Timestamp("2024-01-01T05:00")])
    assert _run(vide)[0] == []


# ─────────────────────────────────────────────────────────────────────────────
# (c) géométrie
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("guard", [0.03, 0.05, 0.10])
def test_garde_catastrophe_geometrie(guard):
    """R3 impose un stop ; lui n'en a pas. La garde est sous l'entrée, la cible absente."""
    df = _us_session(days=8)
    sigs, data = _run(df, guard_pct=guard)

    assert sigs, "aucun signal à vérifier"
    for s in sigs:
        assert s.side == Side.LONG
        assert s.target is None, "« there is no take profit » [05:24]"
        assert s.stop == pytest.approx(s.entry * (1.0 - guard), rel=1e-12)
        assert s.stop < s.entry
        assert s.risk_distance == pytest.approx(s.entry * guard, rel=1e-12)
        # l'entrée est bien le close de la barre de signal
        assert s.entry == pytest.approx(float(data.loc[pd.Timestamp(s.timestamp), "close"]))


def test_long_seulement_jamais_de_vente():
    """« The Go Long EA only opens long (buy) positions » (guide de l'EA).

    Sur une série franchement baissière, la règle achète quand même : c'est le
    pari assumé de l'auteur, pas un bug.
    """
    stamps = []
    for d in pd.date_range("2024-01-01", periods=15, freq="D"):
        stamps += [d + pd.Timedelta(hours=h) for h in range(23)]
    idx = pd.DatetimeIndex(stamps)
    close = np.linspace(20000.0, 12000.0, len(idx))          # -40 %
    df = pd.DataFrame({"open": close, "high": close + 5, "low": close - 5,
                       "close": close, "tick_volume": 100.0, "spread": 12.0}, index=idx)
    sigs, _ = _run(df)

    assert len(sigs) == 15
    assert {s.side for s in sigs} == {Side.LONG}


# ─────────────────────────────────────────────────────────────────────────────
# (d) causalité
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("frac", [0.35, 0.6, 0.85])
def test_invariance_par_troncature(frac):
    """generate_signals(precompute(df), p, T) == generate_signals(precompute(df[:T]), p, T)."""
    df = _us_session(days=20)
    p = dict(BASE)
    T = int(len(df) * frac)

    s = Strategy(p); s._symbol = "NASDAQ"
    plein = s.generate_signals(s.precompute(df, p), p, T)
    tronq = s.generate_signals(s.precompute(df.iloc[:T].copy(), p), p, T)

    assert len(plein) == len(tronq)
    for a, b in zip(plein, tronq):
        assert pd.Timestamp(a.timestamp) == pd.Timestamp(b.timestamp)
        assert a.entry == pytest.approx(b.entry)
        assert a.stop == pytest.approx(b.stop)
        assert a.side == b.side


def test_on_bar_egale_backtest():
    """R5 : le chemin live et le chemin backtest décident la même chose."""
    df = _us_session(days=9)
    p = dict(BASE)
    s = Strategy(p); s._symbol = "NASDAQ"
    attendus = {pd.Timestamp(x.timestamp): x
                for x in s.generate_signals(s.precompute(df, p), p, len(df))}

    vus = 0
    for i in range(len(df)):
        ctx = MarketContext(symbol="NASDAQ", timeframe="H1", bars=df.iloc[:i + 1],
                            now=pd.Timestamp(df.index[i]).to_pydatetime(), spread=0.0)
        live = s.on_bar(ctx)
        bt = attendus.get(pd.Timestamp(df.index[i]))
        if bt is None:
            assert live is None, f"on_bar invente un signal à {df.index[i]}"
        else:
            assert live is not None, f"on_bar rate le signal de {df.index[i]}"
            assert live.side == bt.side
            assert live.entry == pytest.approx(bt.entry)
            assert live.stop == pytest.approx(bt.stop)
            assert live.target is None and bt.target is None
            vus += 1
    assert vus == 9


# ─────────────────────────────────────────────────────────────────────────────
# (e) manifeste et bornes
# ─────────────────────────────────────────────────────────────────────────────
def test_manifeste():
    m = Strategy().manifest()
    assert m.magic_number == 130024
    assert Strategy.MAGIC_NUMBER == 130024
    assert m.strategy_id == "S024_balke_go_long" == Strategy.STRATEGY_ID
    assert m.timeframe == "H1"
    assert set(m.symbols) == {"DAX", "NASDAQ", "US30"}

    # 6 cellules exactement
    grid = m.param_grid
    n = 1
    for v in grid.values():
        n *= len(v)
    assert n == 6, f"la grille doit valoir 6 cellules, pas {n}"
    assert grid["guard_pct"] == [0.03, 0.05, 0.10]
    assert grid["entry_hour_offset"] == [0, 1]

    # les défauts (cellule de fidélité) appartiennent à la grille
    for k, vals in grid.items():
        assert m.default_params[k] in vals, f"défaut {k} hors grille"
    assert m.default_params["guard_pct"] == 0.05
    assert m.default_params["entry_hour_offset"] == 0
    assert m.status in ("RESEARCH", "BACKTESTED")     # jamais promu ici (R10)


@pytest.mark.parametrize("bad", [
    {"guard_pct": 0.0}, {"guard_pct": -0.05}, {"guard_pct": 1.0}, {"guard_pct": 2.5},
    {"entry_hour_offset": 2}, {"entry_hour_offset": -1}, {"entry_hour_offset": 0.5},
    {"start_hour": 24}, {"start_hour": -1}, {"start_hour": "0"},
    {"start_hour": 23, "entry_hour_offset": 1},
])
def test_parametres_hors_bornes_levent(bad):
    with pytest.raises(ValueError):
        Strategy({**BASE, **bad})


def test_parametre_inconnu_leve():
    with pytest.raises(ValueError):
        Strategy({**BASE, "trailing_stop": True})


def test_precompute_ne_retombe_pas_en_silence_sur_lheure_zero():
    """Un appel partiel hérite du start_hour de l'instance, il ne le perd pas.

    Piège réel : `precompute(df, {"guard_pct": 0.03})` sur une instance réglée
    sur la séance du DAX renvoyait une colonne vide (aucune barre à 00:00) au
    lieu de marquer les barres 08:00 — zéro trade, zéro erreur.
    """
    df = _dax_session(days=6)
    s = Strategy({**BASE, "start_hour": 8})
    data = s.precompute(df, {"guard_pct": 0.03})          # params partiels
    assert data["entry_bar"].sum() == 6
    assert set(df.index[data["entry_bar"] > 0.5].hour) == {8}


def test_heure_dupliquee_changement_dheure_ne_donne_quun_signal():
    """Passage à l'heure d'hiver : l'heure d'entrée apparaît DEUX fois le même jour.

    Le cache réel contient 71 journées NASDAQ/US30 hors profil type en mars et
    octobre-novembre (décalage d'heure d'été américain contre européen). La règle
    doit acheter UNE fois, sur la PREMIÈRE occurrence — pas deux, pas la seconde.
    """
    stamps = [pd.Timestamp("2024-01-01") + pd.Timedelta(hours=h) for h in range(23)]
    # la barre 00:00 du lendemain est doublée (heure rejouée)
    stamps += [pd.Timestamp("2024-01-02T00:00"), pd.Timestamp("2024-01-02T00:00")]
    stamps += [pd.Timestamp("2024-01-02") + pd.Timedelta(hours=h) for h in range(1, 23)]

    df = _frame(stamps)
    sigs, data = _run(df)

    assert len(sigs) == 2, "l'heure dupliquée a produit un second achat le même jour"
    j2 = [s for s in sigs if pd.Timestamp(s.timestamp).date() == pd.Timestamp("2024-01-02").date()]
    assert len(j2) == 1
    # marquée sur la PREMIÈRE des deux barres 00:00 (position 23, pas 24)
    marked = np.flatnonzero(data["entry_bar"].to_numpy() > 0.5)
    assert marked.tolist() == [0, 23]


def test_barre_orpheline_du_dimanche_a_lheure_dentree():
    """Dimanche réduit à une seule barre, TOMBANT sur l'heure d'entrée.

    Dans le cache réel la barre orpheline du dimanche est à 23:00 et n'est donc
    jamais prise (cf. test_weekend_ferie_et_barre_orpheline). Si le courtier
    décalait son ouverture, elle tomberait sur l'heure d'entrée. Comportement
    voulu et épinglé ici : la règle achète — « every single day » — et c'est le
    MOTEUR qui portera la position jusqu'au lendemain. Aucune exception, aucun
    filtre implicite ; le harnais rend la chose visible par son compteur de
    sorties le lendemain.
    """
    stamps = [pd.Timestamp("2024-01-05") + pd.Timedelta(hours=h) for h in range(23)]
    stamps += [pd.Timestamp("2024-01-07T00:00")]              # dimanche, une seule barre
    stamps += [pd.Timestamp("2024-01-08") + pd.Timedelta(hours=h) for h in range(23)]

    df = _frame(stamps)
    sigs, _ = _run(df)

    jours = sorted({str(pd.Timestamp(s.timestamp).date()) for s in sigs})
    assert jours == ["2024-01-05", "2024-01-07", "2024-01-08"]
    assert all(pd.Timestamp(s.timestamp).hour == 0 for s in sigs)


def test_manifest_yaml_est_coherent_avec_manifest():
    """R7 — le manifeste est la source unique de vérité : les deux doivent coïncider.

    Deux fichiers qui décrivent la même stratégie finissent toujours par diverger
    si rien ne les compare. Ici la divergence casse un test.
    """
    import yaml

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.yaml")
    with open(path, encoding="utf-8") as f:
        y = yaml.safe_load(f)
    m = Strategy().manifest()

    assert y["strategy_id"] == m.strategy_id
    assert y["magic_number"] == m.magic_number == 130024
    assert y["status"] == m.status
    assert y["version"] == m.version
    assert y["display_name"] == m.display_name
    assert y["timeframe"] == m.timeframe
    assert y["warmup_bars"] == m.warmup_bars
    assert list(y["symbols"]) == list(m.symbols)
    assert y["param_grid"] == m.param_grid
    assert y["default_params"] == m.default_params
