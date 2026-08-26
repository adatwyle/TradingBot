#!/usr/bin/env python3
"""
robinbot-gateway.py — LE RÉPONDEUR TELEGRAM DE ROBINBOT
========================================================

Chaque message d'Adrian sur Telegram déclenche une session Claude Code
HEADLESS qui lui répond. L'usine devient dynamique : on interroge le bot
depuis un téléphone, sans qu'aucune session Claude ne soit ouverte sur le PC.

POURQUOI UN WORKER ET PAS LE CANAL DE SESSION
----------------------------------------------
Le plugin Telegram de Claude Code route les entrants vers la session ouverte —
donc vers personne quand il n'y en a pas, et vers une session occupée quand
elle travaille (message accusé, jamais traité : constaté le 2026-08-17). Un
worker de la factory, lui, tourne tant que la console tourne. C'est le même
déplacement que pour les études : l'état vit dans les fichiers, pas dans un
processus vivant qu'il faut avoir pensé à lancer.

UN BOT DÉDIÉ, PAS CELUI DES SESSIONS
-------------------------------------
L'API Telegram n'autorise qu'UN SEUL lecteur par bot (`getUpdates` est
exclusif). Si ce worker lisait le bot des sessions Claude Code, les deux se
voleraient les messages à tour de rôle — le bug qu'on vient précisément de
constater. D'où un bot séparé : @BotFather -> token -> le fichier nommé par
TOKEN_FILE ci-dessous. Sans ce token le worker sort en 2 et ne gêne personne.

CE QUE LA SESSION HEADLESS A LE DROIT DE FAIRE
------------------------------------------------
Lecture seule : `--allowedTools Read,Grep,Glob`. Un téléphone devient ainsi
une fenêtre sur l'usine, JAMAIS une télécommande : pas de Bash, pas d'Edit,
pas de Write, donc aucun ordre, aucune écriture dans un journal scellé,
aucune modification du panneau. Un message qui demanderait d'acheter, de
lancer un runner ou de « réparer » un scellé obtiendra une explication, pas
une exécution. C'est volontaire et non négociable : le canal est ouvert vers
l'extérieur, il doit être inoffensif par construction.

L'ALLOWLIST EST UN FILTRE, PAS UNE POLITESSE
----------------------------------------------
Seul le `chat_id` déclaré en configuration est servi. Tout autre expéditeur
est ignoré en silence (et son message consommé, pour ne pas boucler dessus).

CODES DE SORTIE (contrat commun de la factory)
-----------------------------------------------
    0  passage effectué (y compris « aucun message »)
    2  token/config absents, ou Telegram injoignable — réessai au prochain tick
    1  erreur inattendue (loggée, retentée)
Jamais 3/4 : ce worker ne touche à aucun scellé.

USAGE
-----
    python app/orchestrator/robinbot-gateway.py            # un passage
    python app/orchestrator/robinbot-gateway.py --dry-run  # montre, n'appelle rien
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.paths import db_dir, project_root  # noqa: E402

# RBF_ROOT est lu DANS project_root() (un seul seam canonique).
ROOT = project_root()

GATEWAY_DIR = pathlib.Path(os.environ.get("ROBINBOT_GATEWAY_DIR")
                           or (db_dir() / "gateway"))
STATE_FILE = GATEWAY_DIR / "state.json"
CONFIG_FILE = GATEWAY_DIR / "config.json"
# Le token du bot DÉDIÉ. Fichier hors dépôt (C:\db\), jamais commité.
TOKEN_FILE = pathlib.Path(os.environ.get("ROBINBOT_GATEWAY_TOKEN_FILE")
                          or (GATEWAY_DIR / "gateway_token.txt"))

API = "https://api.telegram.org/bot{token}/{method}"
HTTP_TIMEOUT = 20
# Plafond d'une réponse : au-delà, Claude tourne en rond ou la question
# demandait un travail de session, pas de répondeur.
CLAUDE_TIMEOUT_S = int(os.environ.get("ROBINBOT_GATEWAY_CLAUDE_TIMEOUT") or 300)
CLAUDE_MAX_TURNS = int(os.environ.get("ROBINBOT_GATEWAY_MAX_TURNS") or 24)
# Lecture seule — cf. l'en-tête. Toute extension de cette liste est une
# décision de sécurité, pas un réglage de confort.
ALLOWED_TOOLS = "Read,Grep,Glob"
TELEGRAM_LIMIT = 4000          # 4096 réel, marge pour les entêtes

CONSIGNE = (
    "Tu réponds à Adrian par Telegram, depuis le dépôt RobinBot "
    "(TradingBot). Réponds en français, court et factuel : un écran de "
    "téléphone, pas un rapport. Tu es en LECTURE SEULE — tu ne peux ni écrire, "
    "ni lancer un runner, ni passer un ordre ; si on te le demande, dis "
    "simplement ce qu'il faudrait faire et qui doit le faire. Les chiffres "
    "viennent des fichiers (journaux C:/db/tradingBot/, status.json, TODO.md, "
    "app/orchestrator/logs/factory.log), jamais de mémoire. Pour un état de "
    "situation, suis .claude/skills/robinbot-etat/SKILL.md."
)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[{_ts()}] {msg}", file=sys.stderr, flush=True)


# == ÉTAT ET CONFIGURATION =====================================================
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"offset": 0, "n_served": 0}


def save_state(state: dict) -> None:
    GATEWAY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def load_config() -> dict | None:
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not str(cfg.get("chat_id", "")).strip():
        return None
    return cfg


def load_token() -> str:
    tok = os.environ.get("ROBINBOT_GATEWAY_TOKEN", "").strip()
    if tok:
        return tok
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# == TELEGRAM ==================================================================
def _post(token: str, method: str, payload: dict) -> dict | None:
    """Rend le champ `result`, ou None si le tour a échoué.

    Le token ne doit JAMAIS atterrir dans un log : le repr des exceptions
    requests contient l'URL complète, donc le token. On ne journalise que le
    type de la panne (leçon payée sur le notifier)."""
    try:
        r = requests.post(API.format(token=token, method=method),
                          json=payload, timeout=HTTP_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        err(f"Telegram injoignable ({method}) : {type(e).__name__}")
        return None
    if not r.ok:
        err(f"Telegram a refusé {method} : HTTP {r.status_code}")
        return None
    try:
        body = r.json()
    except ValueError:
        err(f"Telegram : réponse illisible sur {method}")
        return None
    if not body.get("ok"):
        err(f"Telegram : {method} rejeté ({str(body.get('description'))[:120]})")
        return None
    return body.get("result")


def fetch_updates(token: str, offset: int) -> list | None:
    return _post(token, "getUpdates",
                 {"offset": offset, "timeout": 0, "allowed_updates": ["message"]})


def send(token: str, chat_id: str, text: str) -> bool:
    """Découpe si nécessaire : Telegram refuse au-delà de ~4096 caractères, et
    un refus silencieux serait pire qu'une réponse en deux morceaux."""
    morceaux = [text[i:i + TELEGRAM_LIMIT]
                for i in range(0, len(text), TELEGRAM_LIMIT)] or [""]
    for m in morceaux:
        if _post(token, "sendMessage", {"chat_id": chat_id, "text": m}) is None:
            return False
    return True


# == LA SESSION HEADLESS =======================================================
def _clean_env() -> dict:
    """Le CLI enfant ne doit pas hériter du contexte d'une session Claude Code
    parente (base URL de proxy, marqueurs de session)."""
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("CLAUDE_", "CLAUDECODE")) or k == "ANTHROPIC_BASE_URL":
            env.pop(k, None)
    return env


def ask_claude(question: str) -> str | None:
    """Une question -> une réponse texte, ou None si la session a échoué.

    Le prompt passe par STDIN : sous Windows la ligne de commande plafonne à
    ~32 767 caractères et un `claude -p "<texte>"` mal quoté se fait tronquer
    en silence (leçon du juge macd_ai_paper)."""
    exe = shutil.which("claude")
    if exe is None:
        err("claude CLI introuvable dans le PATH")
        return None
    cmd = ["cmd", "/c", exe, "-p", "--output-format", "json",
           "--max-turns", str(CLAUDE_MAX_TURNS),
           "--allowedTools", ALLOWED_TOOLS,
           "--append-system-prompt", CONSIGNE]
    try:
        cp = subprocess.run(cmd, input=question, cwd=str(ROOT),
                            capture_output=True, text=True, encoding="utf-8",
                            timeout=CLAUDE_TIMEOUT_S, env=_clean_env())
    except subprocess.TimeoutExpired:
        err(f"session headless : timeout après {CLAUDE_TIMEOUT_S} s")
        return None
    except OSError as e:  # noqa: BLE001
        err(f"session headless : échec de lancement ({type(e).__name__})")
        return None

    if cp.returncode != 0 and not cp.stdout.strip():
        err(f"session headless : exit {cp.returncode} — {cp.stderr[:200]}")
        return None
    try:
        env = json.loads(cp.stdout)
    except ValueError:
        # Selon la version du CLI, --output-format json peut rendre du texte
        # brut : mieux vaut le relayer que déclarer la panne.
        txt = cp.stdout.strip()
        return txt or None
    if env.get("is_error"):
        err(f"session headless en erreur : {str(env.get('result'))[:200]}")
        return None
    res = str(env.get("result", "")).strip()
    return res or None



# == LE MENU DES COMMANDES =====================================================
# Telegram affiche un menu quand on tape « / ». On y publie les SKILLS DU
# PROJET — celles de `.claude/skills/`, pas les skills globales d'Adrian : ce
# bot répond de RobinBot, pas de tout l'écosystème.
SKILLS_DIR = ROOT / ".claude" / "skills"
# Contraintes Telegram : 1-32 caractères, minuscules, chiffres, underscores.
_AUTORISES = "abcdefghijklmnopqrstuvwxyz0123456789_"


def _nom_telegram(slug: str) -> str:
    """`robinbot-etat` -> `etat`.

    On retire le préfixe `robinbot` : à l'intérieur du bot RobinBot, il est
    redondant, et il coûte huit caractères sur chaque commande qu'Adrian tape
    au pouce."""
    n = slug.lower().replace("-", "_")
    for prefixe in ("robinbot_", "robin_"):
        if n.startswith(prefixe) and len(n) > len(prefixe):
            n = n[len(prefixe):]
            break
    n = "".join(c for c in n if c in _AUTORISES)
    return n[:32]


def _frontmatter(texte: str) -> dict:
    """Lecture minimale du frontmatter : `name` et `description`, y compris en
    forme repliée (`description: >`). On ne tire pas une dépendance YAML pour
    deux champs."""
    if not texte.startswith("---"):
        return {}
    fin = texte.find("\n---", 3)
    if fin == -1:
        return {}
    champs, cle = {}, None
    for ligne in texte[3:fin].splitlines():
        if not ligne.strip():
            continue
        if ligne[:1] not in " 	" and ":" in ligne:
            cle, _, valeur = ligne.partition(":")
            cle = cle.strip()
            champs[cle] = valeur.strip().lstrip(">|").strip()
        elif cle:
            champs[cle] = (champs.get(cle, "") + " " + ligne.strip()).strip()
    return champs


def decouvrir_commandes() -> list[dict]:
    """[{command, description, skill, dossier}] — les skills du projet.

    Une skill sans `name` exploitable est ignorée en silence : mieux vaut un
    menu incomplet qu'un menu que Telegram refuse en bloc."""
    out = []
    if not SKILLS_DIR.is_dir():
        return out
    for d in sorted(SKILLS_DIR.iterdir()):
        f = d / "SKILL.md"
        if not f.is_file():
            continue
        try:
            fm = _frontmatter(f.read_text(encoding="utf-8"))
        except OSError:
            continue
        nom = _nom_telegram(fm.get("name") or d.name)
        if not nom:
            continue
        # Telegram plafonne la description à 256 caractères ; la première
        # phrase suffit à choisir dans un menu.
        desc = (fm.get("description") or d.name).split(".")[0].strip()[:256]
        out.append({"command": nom, "description": desc or d.name,
                    "skill": fm.get("name") or d.name, "dossier": str(d)})
    return out


def synchroniser_commandes(token: str, state: dict, cmds: list[dict]) -> None:
    """Publie le menu — SEULEMENT s'il a changé.

    POURQUOI comparer d'abord : ce worker tourne toutes les 30 s ; republier un
    menu identique 2 880 fois par jour serait du bruit pur sur l'API de
    Telegram."""
    signature = json.dumps([(c["command"], c["description"]) for c in cmds],
                           ensure_ascii=False, sort_keys=True)
    if state.get("menu") == signature:
        return
    charge = [{"command": c["command"], "description": c["description"]}
              for c in cmds]
    if _post(token, "setMyCommands", {"commands": charge}) is None:
        return                      # on réessaiera : la signature n'est pas notée
    state["menu"] = signature
    save_state(state)
    log(f"menu Telegram publié : {', '.join('/' + c['command'] for c in cmds) or '(vide)'}")


def resoudre_commande(texte: str, cmds: list[dict]) -> tuple[str, Optional[dict]]:
    """Une commande `/etat blabla` -> (question pour Claude, skill visée).

    Le texte libre qui suit la commande est CONSERVÉ : « /etat et l'or ? » doit
    pouvoir orienter la réponse."""
    if not texte.startswith("/"):
        return texte, None
    mot, _, reste = texte[1:].partition(" ")
    mot = mot.split("@")[0].lower()          # Telegram suffixe parfois @lebot
    for c in cmds:
        if c["command"] == mot:
            question = (f"Applique la skill « {c['skill']} » du projet "
                        f"(voir {c['dossier']}/SKILL.md) et rends son "
                        f"résultat.")
            if reste.strip():
                question += f"\n\nPrécision d'Adrian : {reste.strip()}"
            return question, c
    dispo = ", ".join("/" + c["command"] for c in cmds) or "(aucune)"
    return (f"Adrian a envoyé la commande inconnue « /{mot} ». Dis-le-lui "
            f"brièvement et rappelle les commandes disponibles : {dispo}."), None


# == LE PASSAGE ================================================================
def handle(token: str, chat_id: str, updates: list, state: dict,
           cmds: list[dict], dry: bool) -> int:
    """Traite les messages du chat autorisé. Rend le nombre de questions
    servies ; l'état est sauvé au fil de l'eau.

    TROIS SIGNAUX PAR QUESTION — parce qu'un système qui met une minute à
    répondre sans rien dire donne à croire qu'il est mort :
        1. l'accusé de réception, émis par le TERMINAL dès que le message est
           relevé — il prouve que l'usine tourne, avant même que Claude entre
           en jeu ;
        2. l'annonce du démarrage de la session headless — la réflexion
           commence, et elle prend le temps qu'elle prend ;
        3. la réponse, avec sa durée.

    ORDRE DE CONSOMMATION — la leçon coûteuse de s14. Le message est consommé
    (curseur avancé, état sauvé) AVANT l'appel payé, pas après. Consommer
    après voudrait dire qu'une panne de Telegram au moment de la remise ferait
    REJOUER la session headless au tick suivant : Telegram indisponible une
    heure, c'est soixante réflexions facturées pour une seule question. On paie
    donc UNE fois, et l'on s'acharne ensuite sur la remise, qui est gratuite.
    """
    servis = 0
    for up in updates:
        suivant = int(up.get("update_id", 0)) + 1
        msg = up.get("message") or {}
        texte = (msg.get("text") or "").strip()
        exp = str((msg.get("chat") or {}).get("id", ""))

        if exp != str(chat_id):
            # Consommé sans réponse : ignorer sans avancer le curseur ferait
            # boucler l'usine sur un intrus à chaque tick.
            log(f"message d'un expéditeur non autorisé ({exp}) — ignoré")
            _consommer(state, suivant, dry)
            continue
        if not texte:
            _consommer(state, suivant, dry)
            continue

        question, skill = resoudre_commande(texte, cmds)
        log(f"question reçue ({len(texte)} caractères)"
            + (f" — commande /{skill['command']}" if skill else ""))
        if dry:
            log(f"DRY-RUN : aucune session lancée pour « {texte[:60]} »")
            continue

        # ── SIGNAL 1 : l'accusé de réception, par le terminal ───────────────
        # S'il ne part pas, on ne consomme rien : le message reviendra au tick
        # suivant. Ne rien avoir payé encore rend ce rejeu inoffensif.
        if not send(token, chat_id,
                    f"📨 Reçu par le terminal RobinBot à {_hhmm()}."):
            log("accusé de réception non remis — le message sera rejoué")
            return servis

        # Le message est à nous : plus jamais rejoué, donc jamais repayé.
        _consommer(state, suivant, dry)

        # ── SIGNAL 2 : la réflexion démarre ─────────────────────────────────
        detail = f" · skill {skill['skill']}" if skill else ""
        send(token, chat_id,
             f"🧠 Session Claude Code headless démarrée (lecture seule){detail} — réflexion en cours…")

        quoi = f"skill {skill['skill']}" if skill else "question libre"
        log(f"session Claude headless — LANCEMENT ({quoi}, "
            f"outils {ALLOWED_TOOLS}, plafond {CLAUDE_TIMEOUT_S}s)")
        debut = time.monotonic()
        reponse = ask_claude(question)
        duree = time.monotonic() - debut
        issue = f"{len(reponse)} caractères" if reponse else "AUCUNE RÉPONSE"
        log(f"session Claude headless — FIN en {duree:.1f}s ({issue})")

        # ── SIGNAL 3 : la réponse ──────────────────────────────────────────
        if reponse is None:
            corps = ("⚠️ La session headless n'a pas abouti "
                     f"(après {duree:.0f} s). L'usine, elle, tourne — "
                     "reformule ou réessaie dans un moment.")
        else:
            corps = f"{reponse}\n\n— Claude Code headless · {duree:.0f} s"

        if not _remettre(token, chat_id, corps):
            # La réflexion est perdue, mais elle n'a été payée qu'une fois et
            # Adrian sait que sa question a été reçue (signal 1).
            err("réponse produite mais NON REMISE après plusieurs tentatives "
                "— la question ne sera pas rejouée (déjà payée).")
        servis += 1
    return servis


def _hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def _consommer(state: dict, offset: int, dry: bool) -> None:
    """Avance le curseur et le PERSISTE tout de suite : ce qui est consommé ne
    doit plus jamais revenir, même si le processus meurt à la ligne suivante."""
    if dry:
        return
    if offset > int(state.get("offset", 0)):
        state["offset"] = offset
        state["last_seen_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        save_state(state)


def _remettre(token: str, chat_id: str, texte: str, essais: int = 3) -> bool:
    """La remise est GRATUITE : on insiste, contrairement à la réflexion."""
    for i in range(essais):
        if send(token, chat_id, texte):
            return True
        if i < essais - 1:
            time.sleep(2 * (i + 1))
    return False


def tick(dry: bool = False) -> int:
    cfg = load_config()
    if cfg is None:
        err(f"configuration absente ou sans chat_id : {CONFIG_FILE} — "
            f"attendu {{\"chat_id\": \"<ton id Telegram>\"}}")
        return 2
    token = load_token()
    if not token:
        err(f"token absent : crée un bot dédié via @BotFather et dépose son "
            f"token dans {TOKEN_FILE} (un seul lecteur par bot — ne réutilise "
            f"pas celui des sessions Claude Code).")
        return 2

    state = load_state()
    # Le menu est publié AVANT de relever les messages : si Adrian vient
    # d'ajouter une skill au projet, elle doit apparaître dans son menu
    # sans qu'il ait à écrire quoi que ce soit.
    cmds = decouvrir_commandes()
    if not dry:
        synchroniser_commandes(token, state, cmds)
    updates = fetch_updates(token, int(state.get("offset", 0)))
    if updates is None:
        return 2
    if not updates:
        # Le dire plutôt que sortir en silence : c'est cette ligne que la
        # console remonte, et « rien à faire » est une information — elle
        # distingue une boîte vide d'une session en cours.
        log("boîte vide — aucune session lancée, aucun token dépensé")
        return 0

    servis = handle(token, str(cfg["chat_id"]), updates, state, cmds, dry)
    if servis and not dry:
        state["n_served"] = int(state.get("n_served", 0)) + servis
        save_state(state)
    log(f"{servis} question(s) servie(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Répondeur Telegram RobinBot — une session headless par message.")
    ap.add_argument("--dry-run", action="store_true",
                    help="montre les messages en attente, ne lance aucune session")
    a = ap.parse_args()
    try:
        return tick(dry=a.dry_run)
    except Exception as e:  # noqa: BLE001 — un répondeur ne tue jamais l'usine
        err(f"erreur inattendue : {type(e).__name__} — {str(e)[:200]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
