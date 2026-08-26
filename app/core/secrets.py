"""
LES CLÉS D'API VIVENT AU NIVEAU DU COMPTE, PAS DE L'ÉTUDE
==========================================================

Une clé Finnhub, OpenAI ou autre appartient à l'ABONNEMENT d'Adrian. Elle est
donc partagée par toutes les études et stratégies qui en ont besoin, et elle
n'a rien à faire dans le dossier de données d'une étude scellée.

POURQUOI CE MODULE EXISTE (l'erreur qu'il corrige)
---------------------------------------------------
La clé Finnhub avait d'abord été logée dans `C:\\db\\tbot\\s14_sentiment\\`.
Trois conséquences, toutes mauvaises :
  · une deuxième étude consommant Finnhub aurait exigé une COPIE de la clé,
    donc deux endroits à mettre à jour le jour où elle tourne ;
  · archiver ou déplacer l'étude aurait emporté la clé avec elle ;
  · le dossier d'une étude scellée contient des MESURES — y mêler un secret
    brouille ce qui est auditable et ce qui doit rester confidentiel.

ORDRE DE RECHERCHE, ET POURQUOI CELUI-LÀ
-----------------------------------------
  1. variable d'environnement `<NOM>_API_KEY`  — override ponctuel, tests, CI
  2. `C:\\db\\tbot\\secrets\\<nom>_key.txt`     — L'EMPLACEMENT CANONIQUE
  3. chemins hérités passés par l'appelant     — compatibilité

Le point 3 existe pour une raison précise : le protocole SCELLÉ de s14 nomme
`C:\\db\\tbot\\s14_sentiment\\finnhub_key.txt`. Un document scellé ne doit pas
devenir un mensonge — on ÉTEND donc la recherche, on ne la remplace pas. Ce
qui y était déposé continue de fonctionner.

La FONCTION REND AUSSI LA SOURCE UTILISÉE. Sans cela, une vieille clé oubliée
dans un emplacement hérité prendrait silencieusement le pas sur la bonne, et
l'on chercherait longtemps pourquoi l'API répond 401 alors qu'« on vient de
mettre la clé à jour ».

RIEN N'EST JAMAIS AFFICHÉ NI JOURNALISÉ
----------------------------------------
La valeur ne sort pas d'ici. `C:\\db\\` est hors dépôt par construction (la
convention du projet sépare code et données), donc aucun risque git ; le
risque restant est le log, et il se traite là où le message est fabriqué —
voir `masquer()`.
"""
from __future__ import annotations

import os
import pathlib

# Racine des données du projet (convention : le code ne contient jamais de
# données). Surchargeable pour les tests.
DB_DIR = pathlib.Path(os.environ.get("TBOT_DB_DIR") or r"C:\db\tbot")
SECRETS_DIR = pathlib.Path(os.environ.get("TBOT_SECRETS_DIR")
                           or (DB_DIR / "secrets"))


def secret_path(nom: str) -> pathlib.Path:
    """L'emplacement canonique d'une clé — celui qu'on documente et qu'on
    indique à l'opérateur quand elle manque."""
    return SECRETS_DIR / f"{nom.lower()}_key.txt"


def env_var(nom: str) -> str:
    return f"{nom.upper()}_API_KEY"


def _lire(chemin: pathlib.Path) -> str:
    try:
        # utf-8-sig : un fichier créé au Bloc-notes commence par un BOM, qui
        # partirait sinon dans l'en-tête HTTP et ferait un 401 incompréhensible.
        return chemin.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return ""


def read_api_key(nom: str,
                 chemins_herites: tuple[pathlib.Path | str, ...] = ()
                 ) -> tuple[str, str, str]:
    """-> (clé, source, erreur).

    `source` nomme l'endroit d'où la clé vient (« environnement », un chemin) :
    l'appelant doit pouvoir le journaliser, jamais la clé elle-même.
    `erreur` est non vide UNIQUEMENT si aucune clé n'a été trouvée ; le message
    dit alors où la déposer, ce qui est la seule information utile à ce
    moment-là.
    """
    depuis_env = os.environ.get(env_var(nom), "").strip()
    if depuis_env:
        return depuis_env, "environnement", ""

    canonique = secret_path(nom)
    cle = _lire(canonique)
    if cle:
        return cle, str(canonique), ""

    for herite in chemins_herites:
        chemin = pathlib.Path(herite)
        cle = _lire(chemin)
        if cle:
            return cle, f"{chemin} (emplacement hérité)", ""

    return "", "", (
        f"clé {nom} absente — déposer la clé (une ligne, la clé seule) dans "
        f"{canonique}, ou définir la variable d'environnement {env_var(nom)}. "
        f"Cet emplacement est partagé par toutes les études : une seule clé à "
        f"maintenir. Le dossier vit hors du dépôt, rien n'est jamais commité.")


def masquer(message: str, cle: str) -> str:
    """Retire une clé d'un message destiné à un log.

    POURQUOI ce n'est pas de la paranoïa : la clé Finnhub voyage en QUERY
    STRING, et le repr d'une exception `requests` embarque l'URL complète.
    Sans ce masquage, chaque coupure réseau déposait le secret en clair dans
    un fichier conservé des mois — celui-là même qu'on ouvre et qu'on
    copie-colle pendant un incident.

    Une clé de moins de 8 caractères n'est pas masquée : caviarder un
    fragment aussi court reviendrait à mutiler le message pour rien.
    """
    if cle and len(cle) >= 8:
        return message.replace(cle, "<clé masquée>")
    return message
