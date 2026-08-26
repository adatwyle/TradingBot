"""
ÉTUDE SCELLÉE s14 « SENTIMENT DES NEWS FOREX » — CLI du worker
===============================================================

    python -m studies.s14_sentiment.run_sentiment [--dry-run] [--test-judge]

UN PASSAGE = COLLECTE PUIS JUGEMENT, dans cet ordre (PROTOCOL.md § 2.1) :
vérification du scellé et de la chaîne du journal AVANT toute écriture,
collecte Finnhub dédupliquée, puis jugement des lots en attente — juge Claude
d'abord, témoin FinBERT ensuite, curseurs indépendants. Idempotent : relancer
plus souvent que nécessaire est sans effet et sans risque. Aucun ordre, aucun
compte virtuel, aucun R : cette étude ne trade pas (§ 0).

CODES DE SORTIE (§ 7)
---------------------
    0  passage effectué — y compris « rien de neuf » (aucune news, aucun lot
       en attente : no-op silencieux, c'est le « moment opportun ») ET y
       compris juge en panne (verdicts `na` journalisés : un juge muet n'est
       pas une panne d'étude)
    2  collecte indisponible — clé Finnhub absente ou API injoignable. Le
       jugement du passage a QUAND MÊME eu lieu ; journal intact ; réessai au
       passage suivant
    3  scellé violé (hash de params.json) — NE PAS « réparer » : toute
       modification des paramètres invalide l'étude (§ 5, invariance).
       INCIDENT, la factory met le worker OFF
    4  journal altéré (chaîne cassée, troncature, réécriture) — enquête
       requise avant tout nouveau passage. INCIDENT, worker OFF

Aucun autre code n'est rendu volontairement. Une exception non rattrapée
(invariant de la bibliothèque violé, ex. lot désynchronisé) sort en 1 avec sa
trace : c'est un BUG, il doit être bruyant, pas absorbé dans un code de
contrat.

EXIT 2 — LA RÈGLE EXACTE, TRANCHÉE ICI
---------------------------------------
**Toute collecte en panne rend 2, que le jugement du passage ait eu lieu ou
non.** C'est la lettre du protocole (§ 2.2 « Clé absente ou service
injoignable -> exit 2 (§ 2.1 — le jugement du passage a quand même lieu) » et
§ 7 « panne de la collecte -> exit 2, journal intact, jugement du passage
quand même effectué »). Le 2 qualifie donc la COLLECTE, jamais le jugement :
il n'est pas un retour anticipé, c'est le code rendu à la FIN d'un passage
dont la phase de jugement s'est déroulée normalement.

POURQUOI ne pas rendre 0 quand le backlog a pu être jugé (lecture alternative
envisagée) : le 2 est le seul signal qui distingue « le collecteur est aveugle
depuis N passages » de « il ne se passe rien ». Le masquer dès qu'un lot
traîne rendrait une clé expirée invisible tant qu'il reste du backlog — et
l'on ne s'en apercevrait qu'une fois le corpus tari, des heures plus tard. Le
coût de ce choix est nul : la factory traite le 2 comme bénin (retry au tick
suivant, worker laissé ON) ; seuls 3 et 4 coupent le worker.

LE SCELLÉ N'EST JAMAIS POSÉ SUR UNE COLLECTE EN PANNE
------------------------------------------------------
Une exception, et une seule, à « `ingest_news` est appelé à chaque passage » :
si la collecte échoue ALORS QUE L'ÉTUDE N'A JAMAIS TOURNÉ (ni état ni
journal), on sort en 2 sans rien créer. POURQUOI : le premier passage POSE le
scellé (§ 7) — il fige `started_at`, qui fait courir les 60 jours de F1, et
marque le flux courant comme « histoire » pour interdire le backfill. Poser ce
scellé sans avoir vu le flux ferait courir F1 sur des jours où rien n'est
collecté, et laisserait ensuite entrer au corpus des news publiées avant le
démarrage. Rien n'est perdu côté intégrité : sans journal ni état, la
vérification de `ingest_news` n'a rien à vérifier.

OPTIONS
-------
`--once`       : un passage, et c'est le DÉFAUT (sans option, le runner fait
                 exactement un passage puis rend la main). Le worker est un
                 processus éphémère relancé par la factory toutes les 1800 s
                 (§ 8) — jamais une boucle qui vit sa vie.
`--dry-run`    : montre ce que le passage ferait — clé présente ou non, juges
                 allumés, effectifs, lots estimés — et n'écrit RIEN, n'appelle
                 ni Finnhub ni aucun juge (aucun token, aucun réseau).
`--test-judge` : envoie un lot synthétique marqué TEST au juge Claude et
                 affiche sa réponse. Ne touche NI journal NI état : c'est la
                 validation de bout en bout du maillon CLI. 0 s'il répond,
                 2 sinon.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    # stderr AUSSI : le message « où déposer la clé » y sort, et c'est
    # exactement celui que l'opérateur doit pouvoir lire — dans la console
    # comme dans le log de la factory, qui capture les deux flux.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from core import secrets                                 # noqa: E402
from studies.s14_sentiment.sentiment_step import (      # noqa: E402
    PARAMS_PATH, PARAMS_SHA256, JournalError, Paths, SealError, _write_status,
    ingest_news, judge_is_on, load_sealed_params, load_state, next_batch,
    read_journal, read_judges, record_verdicts,
)

# Le scellé N'EST PAS redéfini ici : `PARAMS_SHA256` est importé de la
# bibliothèque, qui le porte une seule fois (triple consignation : protocole,
# constante, test — § 1.1). Deux copies du hash, c'est déjà une divergence
# possible.

HTTP_TIMEOUT_S = 20          # borne dure : un passage ne pend jamais sur HTTP
ISO = "%Y-%m-%dT%H:%M:%SZ"


# ─────────────────────────────────────────────────────────────────────────────
# Collecte Finnhub — jamais de crash, jamais de silence
# ─────────────────────────────────────────────────────────────────────────────

def read_api_key(paths: Paths) -> tuple[str, str]:
    """-> (clé, erreur). Délègue à `core.secrets` : la clé appartient au
    COMPTE, pas à l'étude — d'autres stratégies consommeront la même.

    L'emplacement documenté par le protocole scellé (§ 2.2,
    `<data_dir>/finnhub_key.txt`) reste accepté en dernier recours : un
    document scellé ne doit pas devenir un mensonge. Mais l'emplacement
    canonique est désormais partagé, et c'est lui que le message d'absence
    indique.

    La source est journalisée, jamais la clé — sans quoi une vieille clé
    oubliée dans l'ancien emplacement prendrait silencieusement le pas sur la
    bonne, et l'on chercherait longtemps la cause d'un 401.
    """
    key, source, err = secrets.read_api_key(
        "finnhub", chemins_herites=(paths.finnhub_key,))
    if err:
        return "", err
    if "hérité" in source:
        print(f"[CLÉ] finnhub lue depuis {source} — pense à la déplacer vers "
              f"{secrets.secret_path('finnhub')} (partagée par toutes les "
              f"études).", file=sys.stderr)
    return key, ""


def _sans_cle(msg: str, key: str) -> str:
    """Masque la clé dans un message destiné à un log (cf. core.secrets)."""
    return secrets.masquer(msg, key)


def collect_finnhub(paths: Paths, params: dict,
                    timeout_s: int = HTTP_TIMEOUT_S) -> tuple[list, str]:
    """-> (items bruts Finnhub, erreur). Erreur non vide = collecte
    indisponible (exit 2) ; les items rendus sont alors vides.

    Les items partent TELS QUELS à `ingest_news` : la sanitisation, la
    troncature et le dedup sont le travail de la bibliothèque, pas du
    transport. Toute anomalie de transport (HTTP != 200, corps non-JSON,
    JSON d'une forme inattendue) est un échec de collecte — jamais une
    exception qui tuerait le passage et donc le jugement.
    """
    key, err = read_api_key(paths)
    if err:
        return [], err
    url = params["collect"]["endpoint"]
    try:
        import requests
        resp = requests.get(url,
                            params={"category": params["collect"]["category"],
                                    "token": key},
                            timeout=timeout_s)
    except Exception as e:                       # noqa: BLE001 — réseau
        # La clé voyage en QUERY STRING : le repr d'une exception requests
        # embarque l'URL complète, donc le secret. Ce message part sur stderr
        # et atterrit dans un log conservé des mois — on masque avant, jamais
        # après. (Même piège que le token du notifier, en pire : ici c'est
        # l'URL elle-même qui porte la clé.)
        return [], _sans_cle(f"Finnhub injoignable : "
                             f"{type(e).__name__}: {e}", key)
    if resp.status_code != 200:
        corps = resp.text[:200] if resp.text else "(corps vide)"
        return [], _sans_cle(f"Finnhub HTTP {resp.status_code} : {corps}", key)
    try:
        data = resp.json()
    except ValueError as e:
        return [], f"Finnhub : corps non-JSON ({e})"
    if not isinstance(data, list):
        return [], (f"Finnhub : JSON inattendu — liste attendue, "
                    f"{type(data).__name__} reçu")
    return [it for it in data if isinstance(it, dict)], ""


# ─────────────────────────────────────────────────────────────────────────────
# Les juges du passage — Claude d'abord, témoin ensuite (§ 7)
# ─────────────────────────────────────────────────────────────────────────────

def default_judges(params: dict) -> list[tuple[str, object]]:
    """[(nom, fn)] dans l'ordre du protocole. Les imports sont locaux : le
    témoin ne doit pas coûter le chargement de `transformers` quand il est
    coupé au fichier juges — la paresse commence ici."""
    from studies.s14_sentiment.ai_judge import make_judge
    from studies.s14_sentiment.finbert_witness import make_witness
    return [(params["judge"]["name"], make_judge(params)),
            (params["witness"]["name"], make_witness(params))]


# ─────────────────────────────────────────────────────────────────────────────
# Le passage
# ─────────────────────────────────────────────────────────────────────────────

def _log_line(paths: Paths, line: str) -> None:
    """`run.log` — la trace locale des passages (§ 3). Best-effort : un log
    qui rate ne doit JAMAIS faire échouer un passage, et n'écrit rien tant
    que le dossier de données n'existe pas (pas de scellé, pas de trace)."""
    if not os.path.isdir(paths.data_dir):
        return
    try:
        with open(os.path.join(paths.data_dir, "run.log"), "a",
                  encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run_pass(paths: Paths, params: dict, *, collect=None, judges=None,
             now=None) -> int:
    """UN passage complet. Rend le code de sortie du § 7.

    `collect` et `judges` sont injectables — c'est la seule façon de tester un
    passage complet sans réseau, sans CLI claude et sans FinBERT.
    """
    collect = collect or collect_finnhub
    now = now or datetime.now(timezone.utc)
    measured_at = now.strftime(ISO)

    state = load_state(paths.state)
    first_pass = state is None

    items, collect_err = collect(paths, params)
    if collect_err:
        print(f"[COLLECTE] {collect_err}", file=sys.stderr)

    # Le scellé n'est jamais posé sur une collecte en panne (voir l'en-tête).
    if collect_err and state is None and not os.path.exists(paths.journal):
        print("[SCELLÉ] non posé : le premier passage doit voir le flux "
              "courant (§ 7 — aucun backfill, et `started_at` fait courir les "
              "60 jours de F1). Aucun fichier créé, nouvel essai au passage "
              "suivant.", file=sys.stderr)
        return 2

    # PREMIER ACTE : intégrité (scellé + chaîne + empreinte) AVANT toute
    # écriture — appelé même avec items=[] (§ 7). C'est le seul endroit qui
    # vérifie ; les primitives suivantes supposent le journal déjà vérifié.
    try:
        state, n_new = ingest_news(paths, state, items, now=now)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        print("[JOURNAL] aucun passage tant que l'altération n'est pas "
              "expliquée — voir PROTOCOL.md § 3, intégrité.", file=sys.stderr)
        return 4

    # ── Jugement : chaque juge allumé, curseur propre, lot vide = no-op ─────
    switches = read_judges(paths)
    # Les lignes NEWS sont invariantes pendant la phase de jugement (seules
    # des lignes VERDICT/STALE s'ajoutent, et `next_batch` ne lit que les
    # NEWS) : une seule lecture du journal suffit pour les deux juges.
    rows = read_journal(paths.journal)

    # PRÉ-VOL : le journal est-il inscriptible ? On le vérifie AVANT de payer
    # quoi que ce soit. POURQUOI : le juge est appelé (et facturé) avant
    # `record_verdicts` ; si l'append échoue, le curseur n'avance pas et le
    # MÊME lot est rejugé — donc repayé — à chaque tick, indéfiniment et sans
    # alarme. Le déclencheur le plus banal est un verrou de lecture-écriture
    # posé par Excel quand on ouvre journal.csv pour regarder son corpus.
    try:
        with open(paths.journal, "ab"):
            pass
    except OSError as e:
        print(f"[JOURNAL] non inscriptible ({type(e).__name__}) : "
              f"{paths.journal}. Aucun juge n'est appelé — un verdict qu'on ne "
              f"peut pas journaliser est un verdict payé pour rien. Ferme ce "
              f"qui tient le fichier (Excel ?) et laisse le prochain tick "
              f"reprendre.", file=sys.stderr)
        return 4

    resume: list[str] = []
    try:
        for name, fn in (judges if judges is not None else default_judges(params)):
            if not judge_is_on(switches, name):
                resume.append(f"    {name:<12} OFF (judges.txt)")
                continue
            batch = next_batch(paths, state, rows, name, now)
            if not batch:
                resume.append(f"    {name:<12} rien à juger")
                continue
            raw = fn(batch)
            state = record_verdicts(
                paths, state, name, batch, raw, now=now,
                na_reason=(getattr(fn, "last_error", "") if raw is None else ""))
            js = state["judges"][name]
            last = js["last_batch"]
            resume.append(
                f"    {name:<12} lot {len(batch)} news [{last['news_id']}] · "
                f"{last['n_na']} na · curseur {js['cursor']}/"
                f"{state['n_news_total']}")
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        return 4
    except OSError as e:
        # Le journal est devenu inaccessible entre le pré-vol et l'écriture
        # (disque plein, verrou tardif). C'est un INCIDENT, pas un aléa : sans
        # ce filet, l'exception sortirait en 1, la factory laisserait le worker
        # ON, et le lot déjà payé serait rejugé à chaque tick.
        print(f"[JOURNAL] écriture impossible ({type(e).__name__}) : {e}. "
              f"Un lot a peut-être été jugé sans être journalisé — il sera "
              f"rejugé au prochain passage. Worker coupé pour éviter d'y "
              f"revenir en boucle.", file=sys.stderr)
        return 4

    _write_status(paths, state, measured_at, first_pass=first_pass)

    tag = "PREMIER PASSAGE — scellé posé" if first_pass else "passage"
    # On affiche REÇUES et RETENUES, pas seulement les nouvelles. POURQUOI : si
    # Finnhub renomme un champ (`id`, `datetime`), les items sont écartés à
    # l'ingestion et le passage rendrait « 0 nouvelle » pour toujours, exit 0,
    # sans un mot — une collecte morte ressemblerait à un flux calme.
    # « 40 reçue(s) / 0 nouvelle(s) » saute aux yeux dans run.log.
    etat_collecte = ("INDISPONIBLE" if collect_err
                     else f"{len(items)} reçue(s) / {n_new} nouvelle(s)")
    entete = (f"[{measured_at}] {tag} · collecte "
              f"{etat_collecte} · corpus {state['n_news_total']} news")
    print(entete)
    for line in resume:
        print(line)
    _log_line(paths, " | ".join([entete] + [s.strip() for s in resume]))
    return 2 if collect_err else 0


# ─────────────────────────────────────────────────────────────────────────────
# --dry-run — lecture seule, zéro écriture, zéro réseau, zéro token
# ─────────────────────────────────────────────────────────────────────────────

def _preview(news_rows: list[dict], cursor: int, params: dict,
             now: datetime) -> tuple[int, int]:
    """(news périmées en tête, taille du lot) qu'un passage produirait —
    JUMEAU EN LECTURE SEULE de `next_batch`, dont il n'a AUCUN effet de bord
    (pas de ligne STALE, pas de curseur avancé, pas d'état sauvé). Affichage
    seulement : la mesure passe toujours par la bibliothèque."""
    max_age = timedelta(hours=float(params["collect"]["max_news_age_h"]))
    batch_max = int(params["judge"]["batch_max_news"])

    def stale(row: dict) -> bool:
        try:
            pub = datetime.strptime(row["published_at_utc"],
                                    ISO).replace(tzinfo=timezone.utc)
        except (KeyError, TypeError, ValueError):
            return False
        return (now - pub) > max_age

    j = cursor
    while j < len(news_rows) and stale(news_rows[j]):
        j += 1
    k, n = j, 0
    while k < len(news_rows) and n < batch_max and not stale(news_rows[k]):
        k += 1
        n += 1
    return j - cursor, n


def dry_run(paths: Paths, params: dict, now=None) -> int:
    """Ce que le passage FERAIT. N'écrit rien — pas même le dossier."""
    now = now or datetime.now(timezone.utc)
    print("=" * 78)
    print("s14_sentiment — DRY-RUN (aucune écriture, aucun réseau, aucun token)")
    print("=" * 78)
    print(f"données   : {paths.data_dir}")

    key, err = read_api_key(paths)
    print(f"clé API   : {'présente' if key else 'ABSENTE'}")
    if err:
        print(f"            {err}")

    state = load_state(paths.state)
    if state is None:
        print("état      : ABSENT — le prochain passage POSERAIT le scellé "
              "(journal en-tête seule, flux courant marqué comme histoire).")
        if not key:
            print("            …sauf que la collecte est indisponible : le "
                  "scellé ne serait PAS posé, exit 2, aucun fichier créé.")
        return 0

    rows = read_journal(paths.journal)
    news = [r for r in rows if r.get("event") == "NEWS"]
    switches = read_judges(paths)
    print(f"état      : scellé le {state['started_at']} · corpus "
          f"{state['n_news_total']} news · journal {len(rows)} lignes")
    print(f"collecte  : {'appel Finnhub, dedup par id' if key else 'IMPOSSIBLE (exit 2)'}"
          f" — le jugement ci-dessous aurait lieu dans tous les cas (§ 7)")
    for name in (params["judge"]["name"], params["witness"]["name"]):
        js = state["judges"].get(name)
        if js is None:
            print(f"    {name:<12} jamais vu (curseur 0 à son arrivée)")
            continue
        if not judge_is_on(switches, name):
            print(f"    {name:<12} OFF (judges.txt) — aucun lot, aucun token")
            continue
        n_stale, n_batch = _preview(news, int(js["cursor"]), params, now)
        detail = []
        if n_stale:
            detail.append(f"{n_stale} périmée(s) -> STALE")
        detail.append(f"lot de {n_batch} news" if n_batch else "rien à juger")
        print(f"    {name:<12} curseur {js['cursor']}/{state['n_news_total']} · "
              + " · ".join(detail))
    print("-" * 78)
    print("Rien n'a été écrit.")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# --test-judge — un appel réel au juge, rien de journalisé
# ─────────────────────────────────────────────────────────────────────────────

def test_judge(params: dict, now=None) -> int:
    """Lot synthétique marqué TEST -> un appel headless réel. Rien n'est
    journalisé : c'est un contrôle de chaîne, pas une mesure."""
    from studies.s14_sentiment.ai_judge import build_prompt, make_judge
    # Respecter judges.txt ICI AUSSI : on coupe un juge parce qu'il coûte, et
    # une sonde qui passe outre dépense exactement ce qu'on voulait éviter.
    paths = Paths()
    nom_juge = params["judge"]["name"]
    if not judge_is_on(read_judges(paths), nom_juge):
        print(f"[JUDGE] {nom_juge} est coupé dans {paths.judges} — sonde "
              f"annulée (elle coûterait un appel). Rallume-le pour tester.",
              file=sys.stderr)
        return 2
    now = now or datetime.now(timezone.utc)
    batch = [
        {"news_id": "TEST-1",
         "published_at_utc": (now - timedelta(hours=1)).strftime(ISO),
         "source": "TEST", "headline": "Fed officials signal patience as US "
                                       "inflation cools faster than expected"},
        {"news_id": "TEST-2",
         "published_at_utc": (now - timedelta(minutes=40)).strftime(ISO),
         "source": "TEST", "headline": "ECB hawks push back on early rate "
                                       "cuts, euro firms"},
        {"news_id": "TEST-3",
         "published_at_utc": (now - timedelta(minutes=10)).strftime(ISO),
         "source": "TEST", "headline": "Gold steadies near record as real "
                                       "yields drift lower"},
    ]
    judge = make_judge(params)
    print("[TEST-JUDGE] lot synthétique de 3 titres marqués TEST — aucune "
          "écriture, aucun curseur touché.")
    print(f"[TEST-JUDGE] modèle épinglé : {judge.model}")
    print(f"[TEST-JUDGE] prompt : {len(build_prompt(batch, params['universe'], now))} chars")
    raw = judge(batch)
    if raw is None:
        print(f"[TEST-JUDGE] ÉCHEC — le CLI claude n'a rendu aucun verdict "
              f"({judge.last_error}). Le runner journaliserait 5 lignes `na` "
              f"et le témoin FinBERT jugerait quand même.")
        return 2
    print("[TEST-JUDGE] verdicts bruts :",
          json.dumps(raw, ensure_ascii=False)[:1500])
    return 0


# ─────────────────────────────────────────────────────────────────────────────

USAGE = ("usage : run_sentiment.py [--dry-run | --test-judge]\n"
         "        (sans argument : un passage réel — collecte puis jugement)")


def main(argv: list[str]) -> int:
    # Liste blanche AVANT toute E/S. POURQUOI : sans elle, `--dry-runn` ou
    # `-dry-run` ne matchent rien, tombent dans la branche par défaut et
    # lancent un passage RÉEL — vraie collecte, vrais appels payés, vraies
    # écritures dans le scellé. Une faute de frappe ne doit pas coûter de
    # l'argent.
    connus = {"--dry-run", "--test-judge", "--once"}
    inconnus = [a for a in argv if a not in connus]
    if inconnus:
        print(f"argument inconnu : {' '.join(inconnus)}\n{USAGE}",
              file=sys.stderr)
        return 1

    try:
        params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"[SEAL] params.json ILLISIBLE (pas invalide) : "
              f"{type(e).__name__} — {e}. Le scellé n'est pas en cause : "
              f"vérifie les droits, un verrou antivirus, ou le chemin. Ne "
              f"touche PAS au contenu du fichier.", file=sys.stderr)
        return 3

    paths = Paths()
    if "--test-judge" in argv:
        return test_judge(params)
    if "--dry-run" in argv:
        return dry_run(paths, params)
    return run_pass(paths, params)              # --once est le défaut


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
