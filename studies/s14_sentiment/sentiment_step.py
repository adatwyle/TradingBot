"""
ÉTUDE SCELLÉE s14 « SENTIMENT DES NEWS FOREX » — LE PAS DE MESURE (bibliothèque)
=================================================================================

Logique pure du passage de mesure, séparée de l'accès réseau (Finnhub), du CLI
`claude` headless et du témoin FinBERT pour être testable sur des news
synthétiques (`test_sentiment_step.py`). Le CLI est `run_sentiment.py`. Le
motif (scellé, journal chaîné, idempotence) est REPRIS de
`studies/gold_forward/forward_step.py` — une seule leçon, pas deux ; le clamp
des sorties du juge reprend celui de `studies/macd_ai_paper/paper_step.py`.

CE QUE CETTE ÉTUDE FAIT — ET NE FAIT PAS (PROTOCOL.md § 0)
-----------------------------------------------------------
Elle constitue un corpus de verdicts de sentiment horodatés, scellé au fil de
l'eau. **Aucun ordre, aucun compte virtuel, aucun R** : la mesure de valeur
(hit-rate contre la barre D1 cible) est le rôle de `report_sentiment.py`,
jamais avant F1.

TROIS INVARIANTS (hérités de gold_forward, mêmes raisons)
----------------------------------------------------------
1. SCELLÉ — SHA-256 de params.json vérifié avant tout usage (exit 3 au CLI).
   La constante `PARAMS_SHA256` vit ICI : les CLIs l'importent, le test
   l'épingle contre le fichier réel — triple consignation (PROTOCOL.md § 1.1).
2. APPEND-ONLY — journal à chaîne de hachage ; réécriture/troncature/perte
   détectée -> refus de tourner sans rien écrire (exit 4 au CLI).
3. IDEMPOTENT — dedup des news par id Finnhub À VIE (une news = au plus une
   ligne NEWS), et un CURSEUR PAR JUGE sur la suite des lignes NEWS du
   journal : un lot consommé ne l'est qu'une fois, on ne rappelle JAMAIS un
   juge sur les mêmes news. Deux passages sur le même flux n'ajoutent rien.

LE CURSEUR PAR JUGE — la pièce maîtresse
-----------------------------------------
Chaque juge (claude-cli, finbert, futurs `gpt-*` — § 2.5) avance seul sur la
suite ordonnée des lignes NEWS du journal. Chaque ligne NEWS est consommée
soit dans un lot jugé (VERDICT), soit dans un segment périmé (STALE) — le
curseur ne SAUTE jamais de ligne : sa position est reconstructible depuis le
journal seul, et un trou dans les jugements est impossible par construction.

PAS DE VÉRIFICATION D'INTÉGRITÉ RÉPÉTÉE PAR PRIMITIVE
------------------------------------------------------
Le protocole (§ 7) exige UNE vérification du scellé et de la chaîne par
passage, AVANT toute écriture. Elle vit dans `ingest_news` (premier acte de
chaque passage — collecte vide comprise : `ingest_news(paths, state, [])`
vérifie puis no-op). `next_batch` et `record_verdicts` supposent un journal
déjà vérifié dans le même passage — les revérifier à chaque lot serait du
théâtre, pas de la rigueur.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Le scellé — hash consigné (PROTOCOL.md § 1.1), constante importée par les CLIs
# ─────────────────────────────────────────────────────────────────────────────

PARAMS_SHA256 = "31023cf9ab977374bf9de539a908cd0cfdedce46a3acad42c4adfc19ff20bfab"
PARAMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "params.json")


class SealError(RuntimeError):
    """Le fichier de paramètres ne correspond pas au hash scellé."""


class JournalError(RuntimeError):
    """Le journal a été altéré (chaîne cassée, troncature, réécriture)."""


# Les données ne vivent JAMAIS dans l'arborescence de code (convention projet).
# Migration tbot : l'état vit sous C:\db\tradingBot\ (core.paths.db_dir, seam
# TBOT_DB_DIR) — plus jamais sous C:\db\tbot\ (prototype en exploitation,
# lecture seule absolue). Import paresseux : cette bibliothèque ne pose pas
# sys.path elle-même, les CLIs et tests le font avant de l'importer.
def default_data_dir() -> str:
    env = os.environ.get("S14_SENTIMENT_DIR")
    if env:
        return env
    from core.paths import db_dir
    return os.path.join(str(db_dir()), "s14_sentiment")


JOURNAL_COLUMNS = [
    "measured_at_utc",    # quand le passage a tourné — l'horodatage de MESURE
    "event",              # NEWS | VERDICT | STALE
    "news_id",            # NEWS : id Finnhub ; VERDICT/STALE : plage "a..b"
    "published_at_utc",   # NEWS seulement — horodatage de contenu
    "source",             # NEWS seulement
    "headline",           # NEWS seulement, sanitisé (≤ 300 chars, sans \n)
    "judge",              # VERDICT/STALE : claude-cli | finbert | gpt-* futurs
    "symbol",             # VERDICT : instrument de l'univers
    "sentiment",          # VERDICT : positive | negative | neutral | na
    "confidence",         # VERDICT : [0;1], vide si na
    "reason",             # VERDICT : une phrase sanitisée (≤ 300 chars)
    "chain",              # SHA-256 du fichier journal AVANT cette ligne
]


class Paths:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or default_data_dir()
        self.journal = os.path.join(self.data_dir, "journal.csv")
        self.state = os.path.join(self.data_dir, "state.json")
        self.status = os.path.join(self.data_dir, "status.json")
        self.judges = os.path.join(self.data_dir, "judges.txt")
        self.finnhub_key = os.path.join(self.data_dir, "finnhub_key.txt")

    def ensure(self):
        os.makedirs(self.data_dir, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Scellé — identique gold_forward
# ─────────────────────────────────────────────────────────────────────────────

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def load_sealed_params(path: str, expected_sha256: str) -> dict:
    """Charge les paramètres figés. Refus net si le hash ne correspond pas :
    une étude dont la règle a bougé n'est plus une étude."""
    with open(path, "rb") as f:
        raw = f.read()
    got = sha256_bytes(raw)
    if got != expected_sha256:
        raise SealError(
            f"SCELLÉ VIOLÉ — {os.path.basename(path)} : SHA-256 attendu "
            f"{expected_sha256[:16]}…, obtenu {got[:16]}…. Toute modification "
            f"des paramètres invalide l'étude (PROTOCOL.md, § invariance). "
            f"Refus de tourner.")
    return json.loads(raw.decode("utf-8"))


_PARAMS_CACHE: Optional[dict] = None


def sealed_params() -> dict:
    """Les paramètres scellés, hash vérifié au premier usage puis mis en cache.

    POURQUOI un cache module : chaque primitive dépend du scellé (univers,
    seuils, bornes). Le vérifier à la première lecture garantit qu'AUCUNE
    écriture n'est possible avec un scellé violé, sans re-hasher le fichier à
    chaque lot ; et les signatures des primitives restent celles du protocole
    (pas de `params` à trimballer). Le fichier est immuable par définition —
    le cache ne peut pas devenir stale sans violation du scellé.
    """
    global _PARAMS_CACHE
    if _PARAMS_CACHE is None:
        _PARAMS_CACHE = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    return _PARAMS_CACHE


# ─────────────────────────────────────────────────────────────────────────────
# Journal append-only à chaîne de hachage — identique gold_forward
# ─────────────────────────────────────────────────────────────────────────────

def _csv_line(values: list) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()


def init_journal(path: str) -> None:
    if os.path.exists(path):
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(_csv_line(JOURNAL_COLUMNS))


def verify_journal(path: str, state: Optional[dict]) -> None:
    """1. CHAÎNE INTERNE (chaque ligne porte le SHA-256 du fichier avant elle)
    2. EMPREINTE D'ÉTAT (taille + SHA-256 au dernier passage). Voir
    gold_forward/forward_step.py pour l'argumentaire complet."""
    if not os.path.exists(path):
        if state is not None and state.get("journal_bytes", 0) > 0:
            raise JournalError("journal.csv absent alors que l'état en "
                               "référence un — suppression détectée")
        return

    with open(path, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise JournalError("journal vide sans en-tête")
    running = lines[0] + "\n"
    for k, line in enumerate(lines[1:], start=2):
        cells = next(csv.reader(io.StringIO(line)))
        if len(cells) != len(JOURNAL_COLUMNS):
            raise JournalError(f"ligne {k} : {len(cells)} colonnes au lieu de "
                               f"{len(JOURNAL_COLUMNS)}")
        expected = sha256_bytes(running.encode("utf-8"))
        if cells[-1] != expected:
            raise JournalError(
                f"CHAÎNE CASSÉE à la ligne {k} — le journal a été modifié "
                f"après coup. Maillon attendu {expected[:16]}…, "
                f"lu {cells[-1][:16]}…")
        running += line + "\n"

    if state is not None:
        n = int(state.get("journal_bytes", 0))
        sha = state.get("journal_sha256", "")
        if n:
            if len(raw) < n:
                raise JournalError(
                    f"journal tronqué : {len(raw)} octets, "
                    f"{n} attendus au minimum")
            if sha and sha256_bytes(raw[:n]) != sha:
                raise JournalError(
                    "le préfixe du journal ne correspond plus à l'empreinte "
                    "du dernier passage — réécriture détectée")


def append_journal(path: str, rows: list[dict]) -> tuple[int, str]:
    """Ajoute des lignes en fin de fichier, chaînées. Retourne l'empreinte
    (octets, SHA-256) du fichier après écriture — à consigner dans l'état."""
    with open(path, "rb") as f:
        raw = f.read()
    out = []
    for row in rows:
        row = dict(row)
        row["chain"] = sha256_bytes(raw + b"".join(out))
        line = _csv_line([row.get(c, "") for c in JOURNAL_COLUMNS]).encode("utf-8")
        out.append(line)
    with open(path, "ab") as f:
        for line in out:
            f.write(line)
    final = raw + b"".join(out)
    return len(final), sha256_bytes(final)


def read_journal(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────────────────────────────────────
# État — identique gold_forward
# ─────────────────────────────────────────────────────────────────────────────

def load_state(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    """Écriture atomique : un crash au milieu ne laisse jamais un état
    corrompu à côté d'un journal sain."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _to_utc(t) -> datetime:
    """Accepte un ISO du journal ou un datetime (naïf = réputé UTC)."""
    if isinstance(t, str):
        return _parse_iso(t)
    if t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Sanitisation — la chaîne du journal repose sur le découpage par lignes
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize(text, max_chars: Optional[int] = None) -> str:
    """Retours à la ligne remplacés par un espace, puis troncature.

    POURQUOI c'est vital et pas cosmétique : `verify_journal` découpe le
    fichier par `split("\\n")` — un retour à la ligne dans un champ (même
    proprement quoté par csv) casserait la vérification d'un journal pourtant
    honnête. Aucun champ écrit au journal ne doit en contenir. `splitlines`
    couvre \\n, \\r\\n, \\r et les séparateurs Unicode exotiques d'un titre
    de presse copié-collé.
    """
    flat = " ".join(str(text).splitlines())
    if max_chars is not None:
        flat = flat[:max_chars]
    return flat


def _clamp_float(v, lo, hi, dflt) -> float:
    """Motif clamp de macd_ai_paper (`clamp_decision`) : une valeur illisible
    prend le défaut, une valeur lisible est RAMENÉE dans les bornes. Le prompt
    du juge n'est jamais la seule barrière (PROTOCOL.md § 2.3)."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return float(dflt)
    if x != x:  # NaN : "lisible" mais sans ordre — traité comme illisible
        return float(dflt)
    return min(max(x, float(lo)), float(hi))


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion — dedup à vie, sanitisation, pose du scellé au premier passage
# ─────────────────────────────────────────────────────────────────────────────

def _fresh_judge_state() -> dict:
    return {"cursor": 0, "n_verdicts_total": 0, "n_na": 0,
            "n_stale_news": 0, "last_batch": None}


def _judge_state(state: dict, judge: str) -> dict:
    """Le sous-état d'un juge, créé paresseusement au premier contact.

    POURQUOI paresseux : le § 2.5 du protocole réserve des juges futurs
    (`gpt-*`) — un juge ajouté démarre curseur à zéro, et son backlog
    antérieur sera consommé en STALE par la péremption : son compteur F1
    démarre de fait à son arrivée, sans toucher au scellé.
    """
    return state["judges"].setdefault(judge, _fresh_judge_state())


def ingest_news(paths: Paths, state: Optional[dict], items: list,
                now: Optional[datetime] = None) -> tuple[dict, int]:
    """Phase collecte d'un passage : dedup par id Finnhub, sanitisation,
    append des lignes NEWS. Retourne (état, nombre de lignes ajoutées).

    C'est le PREMIER ACTE de chaque passage : l'intégrité (chaîne + empreinte)
    est vérifiée ici, avant toute écriture (§ 7). Collecte en panne ->
    l'appelant passe `items=[]` : la vérification a lieu, rien n'est écrit.

    PREMIER PASSAGE = POSE DU SCELLÉ (§ 7) : le journal est initialisé
    EN-TÊTE SEULE et les ids du flux courant sont marqués vus SANS être
    journalisés — ils sont l'histoire, comme la dernière barre close de
    gold_forward. « Un corpus prospectif ne se constitue pas
    rétroactivement » : seules les news apparues APRÈS le scellement entrent
    au corpus. Curseurs des deux juges à zéro.

    `items` : dicts Finnhub {id, datetime (epoch s), headline, source}.
    Items défectueux : APRÈS le scellé, un item sans id (pas de dedup
    possible) ou sans horodatage lisible (pas de péremption possible) n'est
    ni journalisé ni marqué vu — il est compté dans
    `n_rejected_items_total` (une dérive du schéma Finnhub doit rester
    distinguable d'un flux calme). AU scellé, tout id présent est marqué vu
    — c'est de l'histoire, l'horodatage n'y joue aucun rôle.
    """
    paths.ensure()
    measured_at = _now_iso(now)
    params = sealed_params()
    max_chars = int(params["collect"]["max_headline_chars"])

    verify_journal(paths.journal, state)

    if state is None:
        # ANTI-RE-SCELLEMENT : un journal déjà nourri SANS état à côté n'est
        # jamais un premier passage — c'est un état perdu ou supprimé (la
        # chaîne interne, elle, se vérifie sans état et passerait). Re-sceller
        # par-dessus remettrait les curseurs à zéro et rejugerait l'histoire :
        # refus net, on vient ENQUÊTER avant de relancer.
        if os.path.exists(paths.journal):
            with open(paths.journal, "rb") as f:
                raw = f.read()
            header = _csv_line(JOURNAL_COLUMNS).encode("utf-8")
            if raw not in (b"", header):
                raise JournalError(
                    "état absent alors qu'un journal non vide existe — "
                    "re-scellement refusé, enquête requise")
            if raw == b"":
                # Fichier vide (crash avant l'en-tête) : on repose l'en-tête
                # — init_journal ne réécrit pas un fichier existant.
                with open(paths.journal, "wb") as f:
                    f.write(header)
        init_journal(paths.journal)
        n_bytes, sha = os.path.getsize(paths.journal), sha256_file(paths.journal)
        seen = []
        n_rejected = 0
        for it in items or []:
            if isinstance(it, dict) and it.get("id") is not None:
                seen.append(str(it["id"]))
            else:
                n_rejected += 1
        state = {
            "schema": 1,
            "study": params["study"],
            "started_at": measured_at,
            "seen_ids": seen,
            "n_news_total": 0,
            "n_rejected_items_total": n_rejected,
            "judges": {
                params["judge"]["name"]: _fresh_judge_state(),
                params["witness"]["name"]: _fresh_judge_state(),
            },
            "journal_bytes": n_bytes,
            "journal_sha256": sha,
        }
        save_state(paths.state, state)
        return state, 0

    init_journal(paths.journal)
    seen = set(state["seen_ids"])
    rows: list[dict] = []
    new_ids: list[str] = []
    for it in items or []:
        if not isinstance(it, dict) or it.get("id") is None:
            continue
        nid = str(it["id"])
        if nid in seen:
            continue
        try:
            published = datetime.fromtimestamp(int(it.get("datetime")),
                                               tz=timezone.utc)
        except (TypeError, ValueError, OSError, OverflowError):
            continue
        rows.append({
            "measured_at_utc": measured_at,
            "event": "NEWS",
            "news_id": nid,
            "published_at_utc": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
            # `source` n'est pas plafonné : le protocole ne fixe de longueur
            # que pour `headline` (collect.max_headline_chars). Seuls les
            # retours à la ligne sont retirés — la chaîne repose sur split.
            "source": _sanitize(it.get("source", "")),
            "headline": _sanitize(it.get("headline", ""), max_chars),
        })
        seen.add(nid)
        new_ids.append(nid)

    if rows:
        n_bytes, sha = append_journal(paths.journal, rows)
        state["journal_bytes"] = n_bytes
        state["journal_sha256"] = sha
        state["seen_ids"].extend(new_ids)
        state["n_news_total"] += len(rows)
    save_state(paths.state, state)
    return state, len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Lots par juge — curseur, péremption STALE, contiguïté (§ 2.3 et § 3)
# ─────────────────────────────────────────────────────────────────────────────

def _news_rows(journal_rows: list[dict]) -> list[dict]:
    """Les lignes NEWS dans l'ordre du journal — le référentiel des curseurs."""
    return [r for r in journal_rows if r.get("event") == "NEWS"]


def next_batch(paths: Paths, state: dict, journal_rows: list[dict],
               judge: str, now_utc) -> list[dict]:
    """Le lot du juge : segment CONTIGU de news fraîches depuis son curseur,
    au plus `batch_max_news`, dans l'ordre du journal.

    Effet de bord unique : un run de news périmées (âge contre
    `published_at_utc` > max_news_age_h) EN TÊTE de curseur est consommé ICI,
    en UNE ligne STALE par juge et par segment contigu (plage d'ids), curseur
    avancé, état sauvé. POURQUOI journaliser la péremption : sans trace, un
    trou dans les jugements serait indistinguable d'une perte de données —
    le curseur doit rester reconstructible depuis le journal seul (§ 3).

    Une news périmée au MILIEU du backlog COUPE le lot : le lot s'arrête
    avant elle et le segment périmé, alors en tête de curseur, sera consommé
    en STALE au passage suivant. Le curseur ne saute JAMAIS de ligne : chaque
    ligne NEWS finit soit dans un lot (VERDICT), soit dans un STALE.

    Le curseur n'avance pour le lot rendu QUE dans `record_verdicts` — rendre
    un lot sans le journaliser ne consomme rien.
    """
    params = sealed_params()
    max_age = timedelta(hours=float(params["collect"]["max_news_age_h"]))
    batch_max = int(params["judge"]["batch_max_news"])
    now = _to_utc(now_utc)

    news = _news_rows(journal_rows)
    js = _judge_state(state, judge)
    cur = int(js["cursor"])

    def _stale(row: dict) -> bool:
        return (now - _parse_iso(row["published_at_utc"])) > max_age

    # 1 — le run périmé en tête de curseur, consommé en UNE ligne STALE.
    j = cur
    while j < len(news) and _stale(news[j]):
        j += 1
    if j > cur:
        rng = f"{news[cur]['news_id']}..{news[j - 1]['news_id']}"
        n_bytes, sha = append_journal(paths.journal, [{
            "measured_at_utc": _now_iso(now),
            "event": "STALE",
            "news_id": rng,
            "judge": judge,
        }])
        state["journal_bytes"] = n_bytes
        state["journal_sha256"] = sha
        js["n_stale_news"] += j - cur
        js["cursor"] = j
        save_state(paths.state, state)
        cur = j

    # 2 — le lot : fraîches, contiguës, coupé par la première périmée.
    batch: list[dict] = []
    k = cur
    while k < len(news) and len(batch) < batch_max and not _stale(news[k]):
        r = news[k]
        batch.append({
            "index": k,
            "news_id": r["news_id"],
            "published_at_utc": r["published_at_utc"],
            "source": r["source"],
            "headline": r["headline"],
        })
        k += 1
    return batch


# ─────────────────────────────────────────────────────────────────────────────
# Verdicts — clamp (motif macd_ai_paper), une ligne par instrument (§ 3)
# ─────────────────────────────────────────────────────────────────────────────

def record_verdicts(paths: Paths, state: dict, judge: str, batch: list[dict],
                    verdicts_raw, now: Optional[datetime] = None,
                    na_reason: str = "") -> dict:
    """Journalise UNE ligne VERDICT par instrument de l'univers pour ce lot,
    puis avance le curseur du juge — y compris si tout est `na` : « na
    consomme le lot » (§ 3), rejuger des heures plus tard mesurerait le prix
    déjà réalisé, pas le sentiment.

    `verdicts_raw` : la sortie brute du juge — dict {"verdicts": [...]},
    liste directe, ou None (panne CLI/modèle après relance : tout `na`,
    cause courte dans `na_reason`). Clamp, jamais confiance aveugle :
    sentiment hors vocabulaire -> `na` ; confidence illisible -> défaut 0.0,
    lisible -> ramenée dans les bornes ; reason sans retour à la ligne,
    tronquée ; symbole manquant -> `na` ; symbole hors univers -> ignoré.
    `confidence` reste vide si `na` (§ 3).

    Garde-fou d'idempotence : le lot DOIT démarrer au curseur du juge — un
    lot déjà consommé (ou désynchronisé) est refusé, on ne rappelle jamais un
    juge sur les mêmes news et on ne les journalise jamais deux fois.
    """
    if not batch:
        raise ValueError("lot vide — rien à journaliser")
    params = sealed_params()
    universe = list(params["universe"])
    labels = set(params["sentiment_labels"])
    bounds = params["judge"]["bounds"]
    max_reason = int(params["judge"]["max_reason_chars"])
    measured_at = _now_iso(now)

    js = _judge_state(state, judge)
    if int(js["cursor"]) != int(batch[0]["index"]):
        raise ValueError(
            f"lot désynchronisé pour {judge} : curseur {js['cursor']}, lot "
            f"démarrant à l'index {batch[0]['index']} — un lot ne se "
            f"journalise qu'une fois")
    # Contiguïté : le curseur avance de len(batch), donc un lot troué ferait
    # sauter des news SANS trace (ni VERDICT ni STALE). next_batch ne produit
    # que du contigu — on le rend structurel plutôt que promis.
    if int(batch[-1]["index"]) - int(batch[0]["index"]) + 1 != len(batch):
        raise ValueError(
            f"lot non contigu pour {judge} : indices "
            f"{batch[0]['index']}..{batch[-1]['index']} pour {len(batch)} "
            f"news — le curseur sauterait des lignes sans les consommer")

    # Déballage tolérant de la sortie du juge.
    if verdicts_raw is None:
        entries: list = []
        default_reason = _sanitize(na_reason or "juge indisponible", max_reason)
    else:
        v = (verdicts_raw.get("verdicts")
             if isinstance(verdicts_raw, dict) else verdicts_raw)
        if isinstance(v, list):
            entries = v
            default_reason = _sanitize(
                na_reason or "symbole absent de la réponse du juge", max_reason)
        else:
            entries = []
            default_reason = "sortie du juge illisible"

    by_symbol: dict[str, dict] = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        sym = str(e.get("symbol", "")).strip().upper()
        if sym and sym not in by_symbol:
            by_symbol[sym] = e          # hors univers : jamais consulté

    rng = f"{batch[0]['news_id']}..{batch[-1]['news_id']}"
    rows: list[dict] = []
    n_na = 0
    for sym in universe:
        e = by_symbol.get(sym)
        if e is None:
            sentiment, conf_txt, reason = "na", "", default_reason
        else:
            sentiment = str(e.get("sentiment", "")).strip().lower()
            reason = _sanitize(e.get("reason", ""), max_reason)
            if sentiment not in labels:
                # § 3 : une ligne `na` porte la CAUSE, pas la prose d'un
                # verdict qu'on vient d'écarter — sinon le journal donne à
                # lire une opinion qui n'a jamais été retenue.
                sentiment = "na"
                reason = "sentiment hors vocabulaire"
            conf_txt = ""
            if sentiment != "na":
                conf = _clamp_float(e.get("confidence"),
                                    bounds["confidence_min"],
                                    bounds["confidence_max"], 0.0)
                conf_txt = f"{conf:.3f}"
        if sentiment == "na":
            n_na += 1
        rows.append({
            "measured_at_utc": measured_at,
            "event": "VERDICT",
            "news_id": rng,
            "judge": judge,
            "symbol": sym,
            "sentiment": sentiment,
            "confidence": conf_txt,
            "reason": reason,
        })

    n_bytes, sha = append_journal(paths.journal, rows)
    state["journal_bytes"] = n_bytes
    state["journal_sha256"] = sha
    js["cursor"] = int(batch[-1]["index"]) + 1
    js["n_verdicts_total"] += len(rows)
    js["n_na"] += n_na
    js["last_batch"] = {"news_id": rng, "n_news": len(batch),
                        "measured_at_utc": measured_at, "n_na": n_na}
    save_state(paths.state, state)
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Mapping barre cible — définitions figées du § 4, appliquées telles quelles
# ─────────────────────────────────────────────────────────────────────────────

def _nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    first_sunday = first + timedelta(days=(6 - first.weekday()) % 7)
    return first_sunday + timedelta(days=7 * (n - 1))


def server_utc_offset(d: date) -> int:
    """Décalage serveur Swissquote pour un jour nominal donné — règle DST US
    figée (§ 4) : été du 2e dimanche de mars (inclus) au 1er dimanche de
    novembre (exclu), offsets ancrés dans params.json (`bar_mapping`)."""
    bm = sealed_params()["bar_mapping"]
    # La règle DST est codée en dur ci-dessous : on refuse net si le scellé
    # décrivait une autre règle, plutôt que de mesurer avec un mapping qui ne
    # serait plus celui du protocole.
    if bm.get("dst_rule") != "US":
        raise SealError(
            f"règle DST inattendue dans le scellé : {bm.get('dst_rule')!r} — "
            f"le mapping codé ici suit la règle US (§ 4). Refus de mesurer.")
    dst_start = _nth_sunday(d.year, 3, 2)
    dst_end = _nth_sunday(d.year, 11, 1)
    if dst_start <= d < dst_end:
        return int(bm["server_utc_offset_summer"])
    return int(bm["server_utc_offset_winter"])


def bar_open_utc(nominal_date: date) -> datetime:
    """Ouverture UTC de la barre D1 du jour nominal : 00:00 heure serveur du
    jour de la barre, converti via la table DST. La barre du lundi ouvre
    dimanche 22:00 UTC (hiver US) ou 21:00 UTC (été US). C'est le timestamp
    NOMINAL qui fait foi, pas le premier tick (§ 4, ambiguïté XAUUSD)."""
    off = server_utc_offset(nominal_date)
    midnight = datetime(nominal_date.year, nominal_date.month,
                        nominal_date.day, tzinfo=timezone.utc)
    return midnight - timedelta(hours=off)


def target_bar_for(measured_at_utc) -> date:
    """Le jour nominal (Lun-Ven) de la PREMIÈRE barre D1 dont l'ouverture UTC
    est STRICTEMENT postérieure au verdict — zéro lookahead, même le dimanche
    soir (§ 4). Un verdict émis dimanche AVANT l'ouverture serveur vise le
    lundi ; APRÈS, le mardi."""
    m = _to_utc(measured_at_utc)
    d0 = m.date()
    for k in range(0, 9):       # 9 jours couvrent tout week-end + DST
        d = d0 + timedelta(days=k)
        if d.weekday() >= 5:    # jours nominaux Lun-Ven seulement
            continue
        if bar_open_utc(d) > m:
            return d
    raise RuntimeError("aucune barre cible sous 9 jours — impossible par "
                       "construction, données d'entrée corrompues")


# ─────────────────────────────────────────────────────────────────────────────
# judges.txt — interrupteur opérateur par juge (§ 8, motif panneau factory)
# ─────────────────────────────────────────────────────────────────────────────

def read_judges(paths: Paths) -> dict[str, bool]:
    """-> {juge: allumé}. Grammaire du panneau factory : `nom = on|off`,
    commentaires `#`, lignes illisibles ignorées.

    POURQUOI fail-OPEN ici (contrairement au panneau, fail-closed) : le
    protocole (§ 8) dit « fichier absent ou juge non listé = ON » — couper un
    juge est un acte opérationnel EXPLICITE (« coupe Claude, il brûle des
    tokens »), jamais un accident de fichier. L'appelant lit l'état d'un juge
    via `judge_is_on` (défaut ON).
    """
    out: dict[str, bool] = {}
    try:
        with open(paths.judges, "r", encoding="utf-8-sig") as f:
            raw = f.read()
    except OSError:
        return out
    for line in raw.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        name, val = line.split("=", 1)
        name, val = name.strip(), val.strip().lower()
        if not name:
            continue
        out[name] = val in ("on", "true", "1", "yes", "oui")
    return out


def judge_is_on(judges: dict[str, bool], judge: str) -> bool:
    """Absent ou non listé = ON (§ 8)."""
    return judges.get(judge, True)


# ─────────────────────────────────────────────────────────────────────────────
# status.json — effectifs et distance à F1, JAMAIS de hit-rate (§ 9)
# ─────────────────────────────────────────────────────────────────────────────

def _write_status(paths: Paths, state: dict, measured_at: str, *,
                  first_pass: bool) -> dict:
    """status.json — la dernière photographie du dispositif.

    Avant F1, seuls les effectifs et la distance à F1 sont exposés — les
    hit-rates ne sont PAS calculés ici (« on ne regarde pas la casserole »,
    § 9) : la lecture de valeur est le rôle exclusif de `report_sentiment.py`.
    """
    params = sealed_params()
    fals = params["falsification"]
    stop = params["stop"]
    started = _parse_iso(state["started_at"])
    now_dt = _parse_iso(measured_at)
    days = (now_dt - started).days
    months = days / 30.44

    judges = {}
    total_stale = 0
    for name, js in state["judges"].items():
        total_stale += js["n_stale_news"]
        judges[name] = {
            "cursor": js["cursor"],
            "backlog_news": state["n_news_total"] - js["cursor"],
            "n_verdicts_total": js["n_verdicts_total"],
            "n_na": js["n_na"],
            "n_stale_news": js["n_stale_news"],
            "last_batch": js["last_batch"],
        }

    status = {
        "generated_at_utc": measured_at,
        "first_pass": first_pass,
        "started_at": state["started_at"],
        "n_news_total": state["n_news_total"],
        "n_stale": total_stale,
        "judges": judges,
        "days_elapsed": days,
        "months_elapsed": round(months, 2),
        "stop_criteria": {
            "f1": (f"aucune lecture de valeur avant N >= "
                   f"{fals['n_min_verdicts']} verdicts comptables ET >= "
                   f"{fals['min_days']} jours par juge (écoulés : {days}) — "
                   f"les comptables se calculent dans report_sentiment.py, "
                   f"jamais ici"),
            "time": (f"NON CONCLUSIF à {stop['max_months']} mois si F1 "
                     f"jamais atteint (écoulés : {months:.1f})"),
        },
    }
    tmp = paths.status + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    os.replace(tmp, paths.status)
    return status
