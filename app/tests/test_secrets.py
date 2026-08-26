"""
Tests des clés d'API partagées — aucun secret réel, aucun réseau.

POURQUOI ce banc : une clé mal résolue ne casse rien bruyamment, elle rend un
401 des heures plus tard. On épingle donc l'ORDRE de recherche, le fait que la
source soit toujours nommée, et surtout que la clé ne ressorte jamais dans un
message destiné à un log.

    python -m pytest tests/test_secrets.py -q
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import secrets  # noqa: E402


@pytest.fixture
def coffre(tmp_path, monkeypatch):
    """Un dossier de secrets jetable — jamais C:\\db."""
    monkeypatch.setenv("TBOT_SECRETS_DIR", str(tmp_path / "secrets"))
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    importlib.reload(secrets)
    yield tmp_path
    importlib.reload(secrets)


def _ecrire(chemin, contenu):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(contenu, encoding="utf-8")


# == L'ORDRE DE RECHERCHE ======================================================
def test_environnement_gagne(coffre, monkeypatch):
    _ecrire(secrets.secret_path("finnhub"), "CLE_DU_FICHIER_123")
    monkeypatch.setenv("FINNHUB_API_KEY", "CLE_ENV_456")
    cle, source, err = secrets.read_api_key("finnhub")
    assert (cle, source, err) == ("CLE_ENV_456", "environnement", "")


def test_emplacement_canonique(coffre):
    _ecrire(secrets.secret_path("finnhub"), "CLE_PARTAGEE_789\n")
    cle, source, err = secrets.read_api_key("finnhub")
    assert cle == "CLE_PARTAGEE_789" and err == ""
    assert "secrets" in source                 # la source est NOMMÉE


def test_chemin_herite_accepte_mais_signale(coffre):
    """Le protocole scellé de s14 nomme un chemin dans le dossier de l'étude :
    il doit continuer de fonctionner, sinon le scellé deviendrait un mensonge."""
    vieux = coffre / "s14_sentiment" / "finnhub_key.txt"
    _ecrire(vieux, "VIEILLE_CLE_000")
    cle, source, err = secrets.read_api_key("finnhub", chemins_herites=(vieux,))
    assert cle == "VIEILLE_CLE_000" and err == ""
    assert "hérité" in source                  # pour que l'appelant le dise


def test_le_partage_prime_sur_l_herite(coffre):
    """Une clé déplacée au bon endroit doit gagner : sinon un fichier oublié
    dans l'ancien emplacement continuerait de servir en silence."""
    vieux = coffre / "s14_sentiment" / "finnhub_key.txt"
    _ecrire(vieux, "VIEILLE_CLE_000")
    _ecrire(secrets.secret_path("finnhub"), "NOUVELLE_CLE_111")
    cle, source, _ = secrets.read_api_key("finnhub", chemins_herites=(vieux,))
    assert cle == "NOUVELLE_CLE_111" and "hérité" not in source


def test_bom_du_bloc_notes_retire(coffre):
    """Un fichier créé au Bloc-notes commence par un BOM : parti dans l'URL,
    il produirait un 401 incompréhensible."""
    secrets.secret_path("finnhub").parent.mkdir(parents=True, exist_ok=True)
    secrets.secret_path("finnhub").write_bytes(b"\xef\xbb\xbfCLE_AVEC_BOM_222\n")
    cle, _, _ = secrets.read_api_key("finnhub")
    assert cle == "CLE_AVEC_BOM_222"


# == L'ABSENCE =================================================================
def test_absence_indique_ou_deposer(coffre):
    cle, source, err = secrets.read_api_key("finnhub")
    assert cle == "" and source == ""
    assert str(secrets.secret_path("finnhub")) in err
    assert "FINNHUB_API_KEY" in err
    assert "partagé" in err                    # on explique le POURQUOI


def test_fichier_vide_vaut_absence(coffre):
    _ecrire(secrets.secret_path("finnhub"), "   \n")
    cle, _, err = secrets.read_api_key("finnhub")
    assert cle == "" and err


# == LE MASQUAGE ===============================================================
def test_masquage_dans_un_message_de_log():
    """La clé Finnhub voyage en query string : le repr d'une exception
    requests porte l'URL entière, donc le secret."""
    cle = "CLE_ULTRA_SECRETE_333"
    msg = (f"Max retries exceeded with url: "
           f"/api/v1/news?category=forex&token={cle}")
    masque = secrets.masquer(msg, cle)
    assert cle not in masque and "<clé masquée>" in masque


def test_masquage_ignore_les_fragments_trop_courts():
    """Caviarder « abc » mutilerait le message pour rien."""
    assert secrets.masquer("erreur abc quelque part", "abc") == \
        "erreur abc quelque part"
