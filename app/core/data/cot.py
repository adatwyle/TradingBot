"""
COT — POSITIONNEMENT DES GROS OPÉRATEURS (CFTC), AVEC SA DATE DE PUBLICATION
=============================================================================

Le rapport *Commitments of Traders* de la CFTC dit qui est positionné, et
comment, sur les futures listés aux États-Unis. C'est la seule source de
positionnement gratuite qui possède un HISTORIQUE exploitable — donc la seule
qu'on puisse falsifier, donc la seule adoptable ici.

LE PIÈGE QUE CE MODULE EXISTE POUR RENDRE IMPOSSIBLE
-----------------------------------------------------
La photo est prise le MARDI à la clôture. Elle n'est publiée que le VENDREDI
à 15h30 heure de New York. Le jeu de données de la CFTC ne porte QUE la date
du mardi — la date de publication n'y figure nulle part.

Un backtest qui utilise la ligne du mardi à partir du mardi exploite donc
trois jours d'information future. Et ce n'est pas une petite fuite : Klitgaard
& Weir (Fed de New York, 2004) montrent que le positionnement explique 30 à
45 % du mouvement de change de LA MÊME SEMAINE — connaître les positions de la
semaine donne 75 % de chances de deviner la direction de cette semaine-là. Les
mêmes auteurs concluent que ces données **ne prédisent pas** la semaine
suivante.

Autrement dit : mal aligner les dates ne produit pas un petit biais, cela
fabrique un edge spectaculaire et entièrement faux. C'est pourquoi ce module
ne rend JAMAIS une observation sans sa date de publication, et fournit
`connu_au()` — la seule porte par laquelle un backtest devrait lire ces
données.

CE QU'IL NE FAUT PAS ATTENDRE DE CETTE DONNÉE
-----------------------------------------------
La littérature sérieuse (par opposition au marketing de brokers, abondant sur
ce sujet) attend un pouvoir prédictif faible ou nul. Si une étude scellée
ressort avec un signal fort, la première hypothèse à instruire est un défaut
d'alignement, pas une découverte.

DEUX AUTRES RÉSERVES, DÉCLARÉES ICI PLUTÔT QUE DÉCOUVERTES PLUS TARD
---------------------------------------------------------------------
· L'API sert la version RÉVISÉE des rapports. La CFTC corrige et republie
  (transferts de comptes, erreurs de déclarants). Un backtest voit donc une
  donnée plus propre que celle qui était visible le jour même. Seule parade :
  archiver nos propres instantanés à partir de maintenant.
· La publication a été SUSPENDUE du 30 septembre au 23 décembre 2025 (arrêt
  budgétaire fédéral), avec rattrapage jusqu'au 29 décembre. Les lignes
  existent dans l'historique mais n'étaient pas disponibles en temps réel :
  `connu_au()` en tient compte, et c'est aussi un risque opérationnel en live
  (le flux peut s'arrêter trois mois).

USAGE
-----
    from core.data import cot
    cot.rafraichir()                       # télécharge/complète le cache local
    df = cot.serie("088691")               # l'or, toutes colonnes
    df = cot.connu_au(df, "2026-08-18")    # ce qui était PUBLIC ce jour-là
"""
from __future__ import annotations

import os
import pathlib
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests

# Portail Socrata de la CFTC — aucune authentification requise (un app token
# ne sert qu'à obtenir un throttling plus généreux).
BASE = "https://publicreporting.cftc.gov/resource/{resource}.json"
RESOURCES = {
    # Legacy : Commercial / Non-Commercial / Non-Reportable. Historique 1986.
    "legacy": "6dca-aqww",
    # TFF : sépare Leveraged Funds (tactique) d'Asset Manager (structurel).
    # La littérature désigne les Leveraged Funds comme la sous-catégorie la
    # plus informative sur les devises — l'agrégat « non-commercial » l'est
    # peu. Historique 2006.
    "tff": "gpe5-46if",
}

from core.paths import db_dir as _db_dir  # noqa: E402

DB_DIR = _db_dir()
COT_DIR = pathlib.Path(os.environ.get("TBOT_COT_DIR") or (DB_DIR / "datasets" / "cot"))

HTTP_TIMEOUT = 60
PAGE = 5000

# Les contrats qui nous concernent. On joint par CODE, jamais par nom : les
# libellés changent d'époque (le S&P 500 existe en quatre variantes qui se
# chevauchent), et un backtest joint par nom fabrique des trous ou des
# doublons sans prévenir.
CONTRATS = {
    "088691": "GOLD",
    "099741": "EURO FX",
    "232741": "AUSTRALIAN DOLLAR",
    "092741": "SWISS FRANC",
    "090741": "CANADIAN DOLLAR",
    "097741": "JAPANESE YEN",
}

# Les paires de l'univers RobinBot qui n'ont PAS de contrat propre doivent
# être synthétisées depuis leurs jambes contre dollar. C'est une HYPOTHÈSE de
# décomposition, pas une donnée : l'essentiel du positionnement sur un cross
# se fait en spot et en CFD, jamais sur le CME. À falsifier séparément.
SYNTHETIQUES = {
    "AUDCHF": ("232741", "092741"),
    "AUDCAD": ("232741", "090741"),
    "EURJPY": ("099741", "097741"),
}

# Suspension pour arrêt budgétaire fédéral : aucune publication entre ces
# dates, puis rattrapage accéléré. Les lignes existent, elles n'étaient pas
# publiques.
GEL_2025 = (date(2025, 9, 30), date(2025, 12, 29))


# ─────────────────────────────────────────────────────────────────────────────
# La date de publication — le cœur du module
# ─────────────────────────────────────────────────────────────────────────────

def publication(snapshot: date) -> date:
    """Quand la photo du mardi `snapshot` est devenue PUBLIQUE.

    Règle : le vendredi qui suit, à 15h30 ET. On rend la date du vendredi ; un
    backtest prudent n'utilisera la donnée qu'à partir de la clôture de ce
    jour-là, voire du lundi suivant.

    Pendant le gel de 2025, la donnée n'est devenue publique qu'à la fin du
    rattrapage — la retenir à sa date théorique serait exactement la fuite que
    ce module combat.
    """
    jours_jusquau_vendredi = (4 - snapshot.weekday()) % 7
    if jours_jusquau_vendredi == 0:
        jours_jusquau_vendredi = 7          # un snapshot un vendredi : +1 sem.
    pub = snapshot + timedelta(days=jours_jusquau_vendredi)
    debut, fin = GEL_2025
    if debut <= pub <= fin:
        return fin
    return pub


def connu_au(df: pd.DataFrame, quand) -> pd.DataFrame:
    """Ne garde que les observations DÉJÀ PUBLIÉES à la date `quand`.

    C'est la seule porte par laquelle un backtest devrait lire ces données.
    Lire `df` directement, c'est lire l'avenir."""
    q = pd.Timestamp(quand).date()
    return df[df["publication"] <= q]


# ─────────────────────────────────────────────────────────────────────────────
# Récupération
# ─────────────────────────────────────────────────────────────────────────────

def _fetch(resource: str, code: str, depuis: Optional[str] = None) -> list[dict]:
    """Toutes les lignes d'un contrat, paginées. Une erreur réseau REMONTE :
    un collecteur silencieux qui rend une liste vide ferait croire à un
    contrat mort."""
    ou = f"cftc_contract_market_code='{code}'"
    if depuis:
        ou += f" AND report_date_as_yyyy_mm_dd > '{depuis}'"
    lignes: list[dict] = []
    offset = 0
    while True:
        r = requests.get(
            BASE.format(resource=resource),
            params={"$where": ou, "$order": "report_date_as_yyyy_mm_dd",
                    "$limit": PAGE, "$offset": offset},
            timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        lot = r.json()
        lignes.extend(lot)
        if len(lot) < PAGE:
            return lignes
        offset += PAGE


def _normaliser(lignes: list[dict], code: str) -> pd.DataFrame:
    """Colonnes utiles, typées, plus la date de publication calculée."""
    if not lignes:
        return pd.DataFrame()
    df = pd.DataFrame(lignes)
    df["snapshot"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.date
    df["publication"] = df["snapshot"].map(publication)
    df["code"] = code
    df["contrat"] = CONTRATS.get(code, code)

    # Positions nettes normalisées par l'open interest : une position nette de
    # 50 000 lots ne dit rien sans la taille du marché, et l'open interest a
    # été multiplié par dix en quarante ans.
    def num(col):
        """None si la colonne est absente — les rapports Legacy et TFF n'ont
        pas les mêmes. `pd.to_numeric(None)` rendrait un scalaire, pas rien."""
        if col not in df.columns:
            return None
        return pd.to_numeric(df[col], errors="coerce")

    df["oi"] = num("open_interest_all")
    for cat, (lg, ct) in {
        "noncomm": ("noncomm_positions_long_all", "noncomm_positions_short_all"),
        "comm": ("comm_positions_long_all", "comm_positions_short_all"),
        "petits": ("nonrept_positions_long_all", "nonrept_positions_short_all"),
        # TFF — présentes seulement dans ce rapport.
        "levfunds": ("lev_money_positions_long_all", "lev_money_positions_short_all"),
        "assetmgr": ("asset_mgr_positions_long", "asset_mgr_positions_short"),
    }.items():
        lo, sh = num(lg), num(ct)
        if lo is None or sh is None or lo.isna().all():
            continue
        df[f"net_{cat}"] = lo - sh
        df[f"pct_{cat}"] = (lo - sh) / df["oi"]

    garder = (["snapshot", "publication", "code", "contrat", "oi"]
              + [c for c in df.columns if c.startswith(("net_", "pct_"))])
    return df[garder].sort_values("snapshot").reset_index(drop=True)


def _fichier(rapport: str, code: str) -> pathlib.Path:
    return COT_DIR / f"{rapport}_{code}.parquet"


def rafraichir(rapport: str = "legacy",
               codes: Optional[list[str]] = None) -> dict[str, int]:
    """Complète le cache local. Rend {code: nombre de lignes ajoutées}.

    Incrémental : on ne redemande que ce qui suit la dernière photo connue.
    Les révisions de la CFTC ne sont donc PAS récupérées pour le passé déjà
    téléchargé — c'est voulu : notre copie devient un instantané daté, plus
    proche de ce qui était réellement visible qu'une base sans cesse réécrite.
    """
    COT_DIR.mkdir(parents=True, exist_ok=True)
    resource = RESOURCES[rapport]
    ajouts: dict[str, int] = {}
    for code in (codes or list(CONTRATS)):
        f = _fichier(rapport, code)
        ancien = pd.read_parquet(f) if f.exists() else pd.DataFrame()
        depuis = (str(ancien["snapshot"].max()) if len(ancien) else None)
        neuf = _normaliser(_fetch(resource, code, depuis), code)
        if len(neuf) == 0:
            ajouts[code] = 0
            continue
        fusion = (pd.concat([ancien, neuf], ignore_index=True)
                  if len(ancien) else neuf)
        fusion = (fusion.drop_duplicates(subset=["snapshot", "code"], keep="first")
                  .sort_values("snapshot").reset_index(drop=True))
        fusion.to_parquet(f, index=False)
        ajouts[code] = len(fusion) - len(ancien)
    return ajouts


def serie(code: str, rapport: str = "legacy") -> pd.DataFrame:
    f = _fichier(rapport, code)
    if not f.exists():
        raise FileNotFoundError(
            f"cache COT absent pour {code} ({rapport}) — lancer "
            f"core.data.cot.rafraichir() d'abord.")
    return pd.read_parquet(f)


def synthetique(paire: str, colonne: str = "pct_noncomm",
                rapport: str = "legacy") -> pd.DataFrame:
    """Positionnement d'un cross, reconstitué depuis ses deux jambes dollar.

    ATTENTION — ceci est une HYPOTHÈSE, pas une mesure : rien ne garantit que
    le positionnement sur AUDCHF se décompose proprement en (AUD/USD moins
    CHF/USD). L'essentiel du volume sur ces crosses se traite en spot et en
    CFD, hors du CME. Le proxy est donc structurellement plus bruité que le
    signal direct sur l'euro ou l'or, et doit être scellé dans une étude
    SÉPARÉE — sinon un résultat obtenu sur EURUSD contaminerait sa lecture.
    """
    if paire not in SYNTHETIQUES:
        raise KeyError(f"{paire} n'a pas de décomposition déclarée "
                       f"(connues : {', '.join(SYNTHETIQUES)})")
    base, contre = SYNTHETIQUES[paire]
    a = serie(base, rapport)[["snapshot", "publication", colonne]]
    b = serie(contre, rapport)[["snapshot", colonne]]
    m = a.merge(b, on="snapshot", suffixes=("_base", "_contre"))
    m[paire] = m[f"{colonne}_base"] - m[f"{colonne}_contre"]
    return m[["snapshot", "publication", paire]]
