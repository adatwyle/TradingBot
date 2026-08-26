"""
Tests du collecteur COT — AUCUN réseau (les réponses CFTC sont injectées).

POURQUOI ce banc porte presque entièrement sur les DATES : la corrélation du
positionnement avec le prix est contemporaine (Klitgaard & Weir, Fed de New
York, 2004 : 30-45 % du mouvement de la même semaine expliqué, aucune valeur
prédictive sur la suivante). Se tromper de trois jours dans l'alignement ne
produit donc pas un petit biais — cela fabrique un edge spectaculaire et
entièrement faux. C'est CE défaut-là qu'on épingle ici.

    python -m pytest tests/test_cot.py -q
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data import cot  # noqa: E402


# == LA DATE DE PUBLICATION ====================================================
def test_photo_du_mardi_publiee_le_vendredi():
    """Trois jours d'écart : c'est toute la fuite possible."""
    mardi = date(2026, 8, 11)
    assert mardi.weekday() == 1
    pub = cot.publication(mardi)
    assert pub == date(2026, 8, 14) and pub.weekday() == 4


@pytest.mark.parametrize("jour", [
    date(2026, 8, 10),   # lundi
    date(2026, 8, 11),   # mardi (le cas réel)
    date(2026, 8, 12),   # mercredi
    date(2026, 8, 13),   # jeudi
])
def test_publication_toujours_posterieure_au_snapshot(jour):
    assert cot.publication(jour) > jour
    assert cot.publication(jour).weekday() == 4


def test_snapshot_un_vendredi_attend_la_semaine_suivante():
    """Sinon la donnée serait 'publiée' le jour même de sa photo."""
    vendredi = date(2026, 8, 14)
    assert cot.publication(vendredi) == date(2026, 8, 21)


def test_gel_budgetaire_2025_repousse_la_publication():
    """Du 30 septembre au 29 décembre 2025, la CFTC n'a rien publié. Les
    lignes existent dans l'historique mais n'étaient pas publiques : les
    dater à leur vendredi théorique rendrait un backtest de ce trimestre
    structurellement faux."""
    pendant = date(2025, 10, 21)              # un mardi du gel
    assert cot.publication(pendant) == cot.GEL_2025[1]
    apres = date(2026, 1, 6)
    assert cot.publication(apres) == date(2026, 1, 9)   # régime normal repris


# == LA PORTE D'ACCÈS ==========================================================
def _serie_test() -> pd.DataFrame:
    snaps = [date(2026, 8, 4), date(2026, 8, 11), date(2026, 8, 18)]
    return pd.DataFrame({
        "snapshot": snaps,
        "publication": [cot.publication(s) for s in snaps],
        "pct_noncomm": [0.10, 0.20, 0.30],
    })


def test_connu_au_cache_ce_qui_n_est_pas_encore_publie():
    df = _serie_test()
    # Le mercredi 12 août, la photo du 11 existe mais n'est PAS publique.
    vu = cot.connu_au(df, "2026-08-12")
    assert list(vu["snapshot"]) == [date(2026, 8, 4)]
    assert 0.20 not in list(vu["pct_noncomm"])


def test_connu_au_le_jour_de_publication_inclut_la_ligne():
    vu = cot.connu_au(_serie_test(), "2026-08-14")
    assert date(2026, 8, 11) in list(vu["snapshot"])


def test_lire_sans_la_porte_c_est_lire_l_avenir():
    """Démonstration du piège : la série brute contient, au 12 août, une
    observation qui ne sera publique que le 14."""
    df = _serie_test()
    brut = df[df["snapshot"] <= date(2026, 8, 12)]
    honnete = cot.connu_au(df, "2026-08-12")
    assert len(brut) == 2 and len(honnete) == 1     # 3 jours de fuite


# == NORMALISATION =============================================================
def _ligne(snapshot="2026-08-11", oi="1000", lg="600", sh="400"):
    return {"report_date_as_yyyy_mm_dd": snapshot, "open_interest_all": oi,
            "noncomm_positions_long_all": lg, "noncomm_positions_short_all": sh,
            "comm_positions_long_all": "300", "comm_positions_short_all": "500"}


def test_normalisation_calcule_le_net_et_la_part():
    df = cot._normaliser([_ligne()], "088691")
    assert df.loc[0, "contrat"] == "GOLD"
    assert df.loc[0, "net_noncomm"] == 200
    assert df.loc[0, "pct_noncomm"] == pytest.approx(0.2)
    assert df.loc[0, "publication"] == date(2026, 8, 14)


def test_part_normalisee_par_open_interest():
    """Une position nette de 50 000 lots ne dit rien sans la taille du
    marché — l'open interest a été multiplié par dix en quarante ans."""
    petit = cot._normaliser([_ligne(oi="1000", lg="600", sh="400")], "088691")
    gros = cot._normaliser([_ligne(oi="10000", lg="6000", sh="4000")], "088691")
    assert petit.loc[0, "net_noncomm"] * 10 == gros.loc[0, "net_noncomm"]
    assert petit.loc[0, "pct_noncomm"] == gros.loc[0, "pct_noncomm"]


def test_colonnes_absentes_ignorees_sans_crash():
    """Le rapport Legacy n'a pas les colonnes TFF, et réciproquement."""
    df = cot._normaliser([_ligne()], "088691")
    assert "pct_levfunds" not in df.columns
    assert "pct_noncomm" in df.columns


def test_reponse_vide_rend_un_cadre_vide():
    assert cot._normaliser([], "088691").empty


# == LES SYNTHÉTIQUES ==========================================================
def test_synthetique_declare_ses_jambes():
    assert cot.SYNTHETIQUES["AUDCHF"] == ("232741", "092741")
    assert cot.SYNTHETIQUES["AUDCAD"] == ("232741", "090741")


def test_paire_sans_decomposition_refusee():
    with pytest.raises(KeyError):
        cot.synthetique("USDNOK")


def test_synthetique_soustrait_les_jambes(monkeypatch):
    snaps = [date(2026, 8, 4), date(2026, 8, 11)]
    aud = pd.DataFrame({"snapshot": snaps,
                        "publication": [cot.publication(s) for s in snaps],
                        "pct_noncomm": [0.30, 0.40]})
    chf = pd.DataFrame({"snapshot": snaps,
                        "publication": [cot.publication(s) for s in snaps],
                        "pct_noncomm": [0.10, 0.05]})
    monkeypatch.setattr(cot, "serie",
                        lambda code, rapport="legacy":
                        aud if code == "232741" else chf)
    s = cot.synthetique("AUDCHF")
    assert list(s["AUDCHF"]) == pytest.approx([0.20, 0.35])
    # La date de publication survit à la synthèse : sinon le proxy
    # rouvrirait la fuite que la série d'origine ferme.
    assert "publication" in s.columns


# == LE CACHE ==================================================================
def test_dax_et_ftse_ne_sont_pas_declares():
    """La CFTC ne couvre que les bourses américaines : DAX (Eurex) et FTSE
    (ICE Europe) n'ont AUCUN rapport COT. Les déclarer donnerait à croire
    qu'on peut les couvrir."""
    noms = " ".join(cot.CONTRATS.values()).upper()
    assert "DAX" not in noms and "FTSE" not in noms


def test_serie_absente_dit_quoi_faire(tmp_path, monkeypatch):
    monkeypatch.setattr(cot, "COT_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="rafraichir"):
        cot.serie("088691")


def test_rafraichir_est_incremental(tmp_path, monkeypatch):
    monkeypatch.setattr(cot, "COT_DIR", tmp_path)
    appels = []

    def faux_fetch(resource, code, depuis=None):
        appels.append(depuis)
        if depuis is None:
            return [_ligne("2026-08-04"), _ligne("2026-08-11")]
        return [_ligne("2026-08-18")]

    monkeypatch.setattr(cot, "_fetch", faux_fetch)
    assert cot.rafraichir(codes=["088691"])["088691"] == 2
    assert cot.rafraichir(codes=["088691"])["088691"] == 1
    assert appels == [None, "2026-08-11"]          # 2e appel borné
    assert len(cot.serie("088691")) == 3


def test_pas_de_doublon_si_la_cftc_republie(tmp_path, monkeypatch):
    """La CFTC révise et republie. Notre copie garde la PREMIÈRE version
    reçue : elle est plus proche de ce qui était réellement visible le jour
    même qu'une base sans cesse réécrite."""
    monkeypatch.setattr(cot, "COT_DIR", tmp_path)
    monkeypatch.setattr(cot, "_fetch",
                        lambda r, c, depuis=None: [_ligne("2026-08-11", lg="600")])
    cot.rafraichir(codes=["088691"])
    monkeypatch.setattr(cot, "_fetch",
                        lambda r, c, depuis=None: [_ligne("2026-08-11", lg="999")])
    cot.rafraichir(codes=["088691"])
    df = cot.serie("088691")
    assert len(df) == 1
    assert df.loc[0, "net_noncomm"] == 200         # la version d'origine
