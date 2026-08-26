#!/usr/bin/env python3
"""
robinbot-portier.py — LE TRI DE L'ENTRÉE
=========================================

Une fois par heure, ce worker regarde la section ENTRÉE de `FILE_ETUDES.md`.
S'il y trouve une idée que personne n'a encore annotée, il ouvre une session
Claude Code headless qui applique la skill `robinbot-portier` : trois questions
vérifiées par idée — déjà instruite ? la donnée peut-elle répondre ? quel
effectif espérer ? — chacune avec le fichier qui la prouve.

POURQUOI CE WORKER EXISTE
--------------------------
Deux fois de suite, le dépôt a payé en journées ce qu'une heure de
vérification aurait coûté : la checklist Alex G avait déjà été instruite sous
un autre nom, et l'étude COT a reçu un protocole complet avant qu'on mesure
que sa donnée ne pouvait pas répondre à la question. Le portier interpose cette
heure de vérification entre l'idée et le travail — automatiquement, sans qu'il
faille y penser.

LA VEILLE EST EN PYTHON, DONC GRATUITE
---------------------------------------
La section ENTRÉE est vide la plupart du temps : c'est le cas NORMAL. Ce script
lit donc le fichier, repère les idées non annotées, et sort en 0 sans avoir rien
appelé quand il n'y a rien à trier. Aucun token n'est dépensé pour constater
qu'une file est vide. La session headless ne démarre qu'une fois la matière
constatée — même discipline que le pilote, et que les runners scellés
(« sans effet si aucune barre nouvelle »).

CE QUE LA SESSION A LE DROIT DE FAIRE
--------------------------------------
`--allowedTools Read,Grep,Glob,Edit`. Edit est nécessaire — le portier écrit
son annotation SOUS l'idée, dans `FILE_ETUDES.md`. Rien d'autre n'est accordé :
pas de Write (il ne crée aucun fichier), pas de Bash (il n'exécute rien, ni
runner, ni backtest, ni ordre).

LE GARDE-FOU EST MÉCANIQUE, PAS MORAL
--------------------------------------
La skill lui interdit de toucher un scellé. On ne s'en remet pas à cette
interdiction : les SHA-256 des `studies/*/params.json` sont relevés AVANT et
APRÈS la session, et la moindre divergence — contenu changé, fichier disparu,
fichier apparu — sort en 1 avec un incident sur stderr. Un scellé modifié
détruit une étude de façon irréparable ; ça se vérifie, ça ne s'espère pas.

LA LIMITE D'ENCOURS SE COMPTE ICI AUSSI
----------------------------------------
`FILE_ETUDES.md` plafonne l'encours à deux études. Le compte se fait en Python,
à chaque passage, même quand ENTRÉE est vide : un dépassement est signalé dans
le log sans coûter un token.

CODES DE SORTIE (contrat commun de la factory)
-----------------------------------------------
    0  passage effectué (y compris « rien à trier », le cas le plus fréquent)
    2  session headless indisponible, ou file des études illisible (elle peut
       être verrouillée une seconde pendant qu'Adrian l'édite) — on réessaiera
    1  erreur inattendue, ou INCIDENT de garde-fou (scellé touché)
Jamais 3/4 : ces deux codes appartiennent aux runners scellés.

USAGE
-----
    python orchestrator/robinbot-portier.py             # un passage
    python orchestrator/robinbot-portier.py --dry-run   # montre, n'appelle rien
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = pathlib.Path(os.environ.get("RBF_ROOT")
                    or pathlib.Path(__file__).resolve().parent.parent)
FILE_ETUDES = pathlib.Path(os.environ.get("ROBINBOT_FILE_ETUDES")
                           or (ROOT / "FILE_ETUDES.md"))
PORTIER_DIR = pathlib.Path(os.environ.get("ROBINBOT_PORTIER_DIR")
                           or r"C:\db\tbot\portier")
STATE_FILE = PORTIER_DIR / "state.json"

SKILL = "robinbot-portier"
# Lecture + Edit, et rien de plus. Toute extension de cette liste est une
# décision de sécurité, pas un réglage de confort (cf. l'en-tête).
ALLOWED_TOOLS = "Read,Grep,Glob,Edit"
CLAUDE_TIMEOUT_S = int(os.environ.get("ROBINBOT_PORTIER_TIMEOUT") or 600)
CLAUDE_MAX_TURNS = int(os.environ.get("ROBINBOT_PORTIER_MAX_TURNS") or 40)
LIMITE_ENCOURS = int(os.environ.get("ROBINBOT_LIMITE_ENCOURS") or 2)

CONSIGNE = (
    "Tu es le portier de la file des études de RobinBot (dépôt "
    "TradingBot_9.0.0.x). Tu annotes les idées brutes de la section ENTRÉE de "
    "FILE_ETUDES.md, et tu n'écris nulle part ailleurs. Pour chaque idée : "
    "a-t-elle déjà été instruite (cite le fichier exact et le verdict), la "
    "donnée peut-elle répondre (source, fréquence, profondeur mesurée sur le "
    "disque), quel effectif indépendant espérer face au plancher usuel du "
    "dépôt. Tu ne supprimes rien, tu ne déplaces rien d'une section à l'autre, "
    "tu ne promeus ni ne clos aucune idée : tu vérifies, Adrian décide. Tu ne "
    "touches à aucun scellé (studies/*/params.json, PROTOCOL.md), à aucun "
    "journal, et tu n'exécutes rien. Français sobre, phrases complètes, aucun "
    "enthousiasme : un « DOUBLON » sans le fichier qui le prouve ne vaut rien."
)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[{_ts()}] {msg}", file=sys.stderr, flush=True)


# == ÉTAT ======================================================================
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    """Écriture atomique : un état à moitié écrit vaut moins qu'un état absent."""
    PORTIER_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, STATE_FILE)


# == LA VEILLE (Python pur, ZÉRO token) ========================================
def _pli(txt: str) -> str:
    """Sans accents, en majuscules — pour que « ENTRÉE » et « ENTREE » soient le
    même titre. La file est écrite à la main : elle doit tolérer les deux."""
    sans = unicodedata.normalize("NFD", txt)
    return "".join(c for c in sans if not unicodedata.combining(c)).upper().strip()


def _section(texte: str, titre: str) -> list[str]:
    """Les lignes de la section « ## <titre> », titre exclu, jusqu'au prochain
    titre de niveau 2. Les « ### » restent DEDANS : ce sont les entrées."""
    cible = _pli(titre)
    out: list[str] = []
    dedans = False
    for ligne in texte.splitlines():
        if ligne.startswith("## "):
            dedans = _pli(ligne[3:]).startswith(cible)
            continue
        if dedans:
            out.append(ligne)
    return out


def _paragraphes(lignes: list[str]) -> list[list[str]]:
    """Groupes de lignes séparés par du vide. Une idée est un paragraphe ; son
    annotation aussi. Raisonner par paragraphe évite de compter deux fois une
    idée écrite sur deux lignes."""
    out: list[list[str]] = []
    courant: list[str] = []
    for ligne in lignes:
        if ligne.strip():
            courant.append(ligne)
        elif courant:
            out.append(courant)
            courant = []
    if courant:
        out.append(courant)
    return out


def _est_annotation(ligne: str) -> bool:
    """« → PORTIER 2026-08-21 » et ses variantes de flèche."""
    t = ligne.strip().lstrip("→>-–—*+ ").upper()
    return t.startswith("PORTIER")


def _est_ignorable(para: list[str]) -> bool:
    """Ce qui n'est ni une idée ni une annotation : la consigne en blockquote,
    le marqueur « _(vide)_ », une règle horizontale."""
    if not para:
        return True
    prem = para[0].strip()
    if not prem or prem.startswith(">"):
        return True
    if set(prem) <= set("-*=_ "):
        return True
    return _pli(prem.strip("_*() ")) == "VIDE"


def _titre(para: list[str]) -> str:
    """De quoi reconnaître l'idée dans un log, sans recopier son paragraphe.

    La file écrit ses idées « **Titre.** puis la description » : quand le gras
    balise un titre complet, on s'en sert et on laisse la description dehors."""
    brut = para[0].strip().lstrip("#-*+ ").strip()
    if para[0].strip().startswith("**") and "**" in brut:
        brut = brut.split("**", 1)[0].strip() or brut
    return brut[:110]


def idees_de_l_entree(texte: str) -> list[dict]:
    """[{titre, annotee}] pour la section ENTRÉE.

    Une idée est ANNOTÉE si un bloc « → PORTIER » la suit avant l'idée suivante
    — que ce bloc soit séparé par une ligne vide ou collé dessous."""
    idees: list[dict] = []
    for para in _paragraphes(_section(texte, "ENTREE")):
        coupe = next((i for i, l in enumerate(para) if _est_annotation(l)), None)
        if coupe is None:
            if not _est_ignorable(para):
                idees.append({"titre": _titre(para), "annotee": False})
            continue
        corps = para[:coupe]
        if corps and not _est_ignorable(corps):
            idees.append({"titre": _titre(corps), "annotee": True})
        elif idees:
            idees[-1]["annotee"] = True
    return idees


def compter_encours(texte: str) -> int:
    """Le nombre d'études qui occupent un créneau. Les entrées sont écrites en
    « ### » ; sans aucune, on retombe sur le compte des paragraphes utiles
    plutôt que d'annoncer un encours nul sur une section pleine."""
    lignes = _section(texte, "EN COURS")
    n = sum(1 for l in lignes if l.startswith("###"))
    if n:
        return n
    return sum(1 for p in _paragraphes(lignes) if not _est_ignorable(p))


# == GARDE-FOU : LES SCELLÉS ===================================================
def scelles() -> dict[str, str]:
    """{chemin relatif: sha256} des params.json d'études. Un fichier illisible
    est noté comme tel : disparaître est aussi une divergence."""
    out: dict[str, str] = {}
    for p in sorted((ROOT / "studies").glob("*/params.json")):
        try:
            cle = str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            cle = str(p)
        try:
            out[cle] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            out[cle] = "ILLISIBLE"
    return out


def divergences(avant: dict[str, str], apres: dict[str, str]) -> list[str]:
    """Ce qui a bougé entre les deux relevés — changé, disparu, ou apparu."""
    faits: list[str] = []
    for cle in sorted(set(avant) | set(apres)):
        a, b = avant.get(cle), apres.get(cle)
        if a == b:
            continue
        if a is None:
            faits.append(f"{cle} : scellé APPARU (aucun scellé ne se crée ici)")
        elif b is None:
            faits.append(f"{cle} : scellé DISPARU")
        else:
            faits.append(f"{cle} : hash modifié ({a[:12]}… → {b[:12]}…)")
    return faits


# == LA SESSION HEADLESS =======================================================
def _clean_env() -> dict:
    """Le CLI enfant ne doit pas hériter du contexte d'une session Claude Code
    parente (base URL de proxy, marqueurs de session)."""
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("CLAUDE_", "CLAUDECODE")) or k == "ANTHROPIC_BASE_URL":
            env.pop(k, None)
    return env


def _chemin_skill() -> pathlib.Path:
    return ROOT / ".claude" / "skills" / SKILL / "SKILL.md"


def lancer_session(question: str) -> str | None:
    """Une question -> le texte rendu, ou None si la session a échoué.

    POPEN ET NON subprocess.run : sous Windows `claude` est un shim .CMD lancé
    par cmd.exe, et le vrai travailleur est un node.exe PETIT-FILS. Le timeout
    de `subprocess.run` ne tue que le parent — le petit-fils continuerait
    d'écrire, et le tick pendrait jusqu'au plafond de la factory. On tue donc
    l'ARBRE (`taskkill /T /F`), comme la factory le fait pour ses ticks.

    Le prompt passe par STDIN : la ligne de commande Windows plafonne à ~32 767
    caractères et un `claude -p "<texte>"` mal quoté se fait tronquer en silence.

    `errors="replace"` au décodage : un seul octet UTF-8 invalide rendrait un
    stdout VIDE sans lever, donc une panne muette."""
    exe = shutil.which("claude")
    if exe is None:
        err("claude CLI introuvable dans le PATH")
        return None
    cmd = ["cmd", "/c", exe, "-p", "--output-format", "json",
           "--max-turns", str(CLAUDE_MAX_TURNS),
           "--allowedTools", ALLOWED_TOOLS,
           "--append-system-prompt", CONSIGNE]
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=_clean_env())
    except OSError as e:  # noqa: BLE001
        err(f"session headless : échec de lancement ({type(e).__name__})")
        return None
    try:
        sortie, erreurs = proc.communicate(question, timeout=CLAUDE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)
        try:
            proc.communicate(timeout=15)
        except Exception:  # noqa: BLE001 — on a déjà tué, on ne s'acharne pas
            pass
        err(f"session headless : timeout après {CLAUDE_TIMEOUT_S} s — arbre tué")
        return None

    sortie = sortie or ""
    if proc.returncode != 0 and not sortie.strip():
        err(f"session headless : exit {proc.returncode} — {(erreurs or '')[:200]}")
        return None
    try:
        enveloppe = json.loads(sortie)
    except ValueError:
        # Selon la version du CLI, --output-format json peut rendre du texte
        # brut : mieux vaut le relayer que déclarer la panne.
        return sortie.strip() or None
    if enveloppe.get("is_error"):
        err(f"session headless en erreur : {str(enveloppe.get('result'))[:200]}")
        return None
    return str(enveloppe.get("result", "")).strip() or None


def question_portier(neuves: list[dict], encours: int) -> str:
    """Le prompt nomme la skill et son chemin — comme le fait le gateway quand
    Adrian tape une commande depuis son téléphone."""
    liste = "\n".join(f"- {i['titre']}" for i in neuves)
    q = (f"Applique la skill « {SKILL} » du projet "
         f"(voir {_chemin_skill()}) et rends son résultat.\n\n"
         f"La veille Python a repéré {len(neuves)} idée(s) NON ENCORE ANNOTÉE(S) "
         f"dans la section ENTRÉE de {FILE_ETUDES} :\n{liste}\n\n"
         f"Annote chacune sur place, sans rien supprimer ni déplacer.")
    if encours > LIMITE_ENCOURS:
        q += (f"\n\nLa section EN COURS compte {encours} entrées pour une limite "
              f"de {LIMITE_ENCOURS} : signale-le en tête de fichier, comme le "
              f"demande la skill.")
    return q


# == LE PASSAGE ================================================================
def tick(dry: bool = False) -> int:
    try:
        texte = FILE_ETUDES.read_text(encoding="utf-8-sig")
    except OSError as e:  # noqa: BLE001
        err(f"file des études illisible ({FILE_ETUDES}) : {type(e).__name__}")
        log("passage terminé : file illisible, aucune session lancée")
        return 2

    encours = compter_encours(texte)
    idees = idees_de_l_entree(texte)
    neuves = [i for i in idees if not i["annotee"]]

    # Le compte d'encours se fait à CHAQUE passage, y compris quand ENTRÉE est
    # vide : c'est gratuit, et un dépassement silencieux est exactement ce que
    # la limite est censée empêcher.
    depasse = encours > LIMITE_ENCOURS
    if depasse:
        err(f"file : {encours} études EN COURS pour une limite de "
            f"{LIMITE_ENCOURS} — la limite d'encours n'est pas indicative.")
    marge = f"encours {encours}/{LIMITE_ENCOURS}" + (" DÉPASSÉ" if depasse else "")

    if not neuves:
        etat_entree = (f"{len(idees)} idée(s), toutes annotées" if idees
                       else "ENTRÉE vide")
        log(f"rien à trier — {etat_entree} · {marge} · aucune session lancée, "
            f"zéro token")
        return 0

    log(f"{len(neuves)} idée(s) non annotée(s) : "
        + " | ".join(i["titre"] for i in neuves)[:200])
    if dry:
        log(f"DRY-RUN : session non lancée, rien écrit · {marge}")
        return 0

    avant = scelles()
    log(f"session Claude headless — LANCEMENT (skill {SKILL}, "
        f"outils {ALLOWED_TOOLS}, plafond {CLAUDE_TIMEOUT_S}s)")
    debut = time.monotonic()
    rendu = lancer_session(question_portier(neuves, encours))
    duree = time.monotonic() - debut
    issue = f"{len(rendu)} caractères" if rendu else "AUCUNE RÉPONSE"
    log(f"session Claude headless — FIN en {duree:.1f}s ({issue})")

    # Le contrôle des scellés a lieu même si la session a échoué : un timeout
    # tue la session EN COURS d'écriture, il ne prouve pas qu'elle n'a rien fait.
    bouges = divergences(avant, scelles())
    if bouges:
        err("INCIDENT — le portier a touché un scellé, ce qu'il n'a JAMAIS le "
            "droit de faire :")
        for f in bouges:
            err("  " + f)
        err("Ne 'répare' pas params.json : toute modification invalide l'étude. "
            "Lis `git diff` puis le PROTOCOL.md concerné avant quoi que ce soit.")
        log(f"passage terminé : INCIDENT scellé ({len(bouges)}) · {marge}")
        return 1

    if rendu is None:
        log(f"passage terminé : session indisponible, rien annoté · {marge}")
        return 2

    etat = load_state()
    etat["last_run_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    etat["n_sessions"] = int(etat.get("n_sessions", 0)) + 1
    etat["dernieres_idees"] = [i["titre"] for i in neuves]
    etat["encours"] = encours
    save_state(etat)

    resume = rendu.replace("\n", " ")[:110]
    log(f"passage terminé : {len(neuves)} idée(s) soumise(s) au portier en "
        f"{duree:.0f}s, scellés intacts · {marge} · {resume}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Portier RobinBot — trie la section ENTRÉE de la file des études.")
    ap.add_argument("--dry-run", action="store_true",
                    help="montre les idées à trier, ne lance aucune session, n'écrit rien")
    a = ap.parse_args()
    try:
        return tick(dry=a.dry_run)
    except Exception as e:  # noqa: BLE001 — un worker ne tue jamais l'usine
        err(f"erreur inattendue : {type(e).__name__} — {str(e)[:200]}")
        log("passage terminé : erreur inattendue")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
