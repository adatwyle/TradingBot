#!/usr/bin/env python3
"""
tbot-factory.py — LA CONSOLE 24/7 DE TRADINGBOT (« tbot factory »)
===================================================================

RÈGLE D'OR : si cette console ne tourne pas, RIEN ne se passe.

Adaptation FIDÈLE de robinbot-factory.py (décision D1, ticket TCK-005) : mêmes
mécanismes éprouvés — ticks éphémères, panneau à chaud hors dépôt, contrat de
codes de sortie 0/2/3/4 avec AUTO-OFF, verrou single-instance, arrêt propre
par Ctrl-C ou `.stop`, timeout par tick, échelonnement des départs, veille en
Python pur gratuite / session Claude Code seulement quand il y a MATIÈRE.
Aucune tâche planifiée Windows : la console qu'on démarre à la main est
l'interrupteur physique unique du système (la collecte GEX posée en Task
Scheduler le 2026-08-26 est transitoire et sera retirée dès cette factory
validée).

CE QU'EST UN WORKER : UN TICK, PAS UN AGENT VIVANT
--------------------------------------------------
La factory lance un processus NEUF et ÉPHÉMÈRE, redirige sa sortie vers un
log, et l'oublie. Le processus lit l'état sur disque, produit, écrit, sort.
Un worker « sorti » est le cas NORMAL, pas une panne. L'état vit dans les
FICHIERS (C:/db/tradingBot/, tickets/, snapshots S017) — un tick tué laisse
l'état exactement où il est, le tick suivant reprend.

LES DEUX FAMILLES DE SPECS
---------------------------
  spec "py:<chemin> [args]"  : commande Python pure, ZÉRO token. Le cas normal.
  spec "claude:<clé>"        : session Claude Code HEADLESS. La <clé> désigne
        une GARDE enregistrée dans CLAUDE_GUARDS : du Python pur qui décide
        gratuitement s'il y a MATIÈRE (ticket ouvert, nouveaux snapshots…) et
        construit le prompt. Pas de matière = no-op, AUCUN processus, AUCUN
        token. Matière = session `claude -p` ; le prompt passe par STDIN
        (sous Windows la ligne de commande plafonne à ~32k caractères et se
        tronque en silence — leçon du gateway), les flags sont ceux du
        prototype (`--output-format json --max-turns N`).
        Une clé inconnue de CLAUDE_GUARDS est traitée comme un PROMPT LITTÉRAL
        (la forme du prototype robinbot reste disponible).

CHAUD vs FROID — CE QUI SE CHANGE SANS REDÉMARRER
--------------------------------------------------
  À CHAUD (relu à CHAQUE cycle, effet au tick suivant) :
      le PANNEAU DE CONTRÔLE `C:/db/tradingBot/tbot-panel.txt`
      (HORS du dépôt : un panneau = un poste. Gabarit versionné :
       `app/orchestrator/tbot-panel.exemple.txt`)
        · `worker = on` / `worker = off`
        · cadence par worker : `worker = on:1800` (secondes)
      + le MANDAT de cc_S017 : `strategies/S017_ireland_gex/mandat-cc.txt`
        (relu à chaque tick avec matière — éditer le mandat ne demande rien)

  À FROID (fermer et rouvrir la console) :
      · le CATALOGUE des workers (ajouter/retirer) — voir WORKERS
      · les constantes : TICK_TIMEOUT_SEC, STAGGER_SEC, POLL_SEC, chemins
      · les variables d'environnement TBF_*

LE PANNEAU EST UNE SURFACE DE CONTRÔLE, PAS UN RECENSEMENT
-----------------------------------------------------------
Un worker ABSENT du panneau est OFF. Jamais l'inverse. Un panneau tronqué ou
à moitié écrit doit TAIRE l'usine, jamais l'ouvrir en grand.

CODES DE SORTIE DES TICKS (contrat commun, hérité du prototype)
----------------------------------------------------------------
    0  passage effectué (y compris « rien de neuf » / « pas de matière »)  → OK
    2  ressource externe indisponible (réseau, token Telegram absent…)     → réessai
    3  scellé violé (hash des paramètres)                                  → INCIDENT, worker OFF
    4  journal altéré (chaîne de hachage cassée)                           → INCIDENT, worker OFF
Tout autre code non nul = erreur inattendue (on log, on continue).
3 et 4 sont des alarmes de falsification : la factory met le worker OFF dans
le panneau elle-même (AUTO-OFF) et crie, pour qu'un humain LISE avant de
rallumer. Aucun worker v1 n'émet 3/4 (les journaux scellés arrivent avec la
famille paper_S0NN) — le mécanisme est gréé et prêt.

GARDE-FOU R4 — LA FACTORY N'ARME JAMAIS UN TRADE RÉEL
------------------------------------------------------
Une assertion à l'import (assert_no_live_markers) refuse tout catalogue dont
une spec porte un marqueur de trading réel, et l'environnement transmis aux
ticks est purgé des variables d'armement (R4_FORBIDDEN_ENV). Passer en LIVE
n'est PAS un réglage de la factory : c'est une décision d'Adrian, hors de
cette surface (héritage R10/R4 du prototype).

USAGE
-----
    python app/orchestrator/tbot-factory.py            # la console
    python app/orchestrator/tbot-factory.py --once     # un seul cycle (sonde)
    python app/orchestrator/tbot-factory.py --dry-run  # n'exécute rien, montre
    ou double-clic sur app/orchestrator/run-tbot-factory.bat

Arrêt : Ctrl-C, ou créer le fichier `app/orchestrator/.stop`. Les deux sont
PROPRES — on cesse de lancer, on laisse finir ce qui vole, puis on sort.

QUI DOIT LANCER CETTE CONSOLE — et surtout, qui ne doit PAS
------------------------------------------------------------
Double-clic sur `run-tbot-factory.bat`, ou commande DÉTACHÉE. JAMAIS depuis
une session Claude Code : le processus deviendrait descendant de
l'application et retiendrait ses fichiers (constaté le 2026-08-21 sur le
prototype — mise à jour Claude Desktop bloquée par la filiation).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows propre (accents)
except Exception:  # noqa: BLE001
    pass


# == CHEMINS ET CONSTANTES (FROID — redémarrage requis) ========================
# Tout est surchargeable par l'environnement TBF_* : c'est ce qui rend ce
# fichier testable (les tests montent une usine jetable dans un tmp_path) sans
# la moindre branche « if TEST » dans le code de production.
HERE = pathlib.Path(__file__).resolve().parent           # app/orchestrator
# `core` vit dans app/ ; ce script est lancé en direct (pas en module), on rend
# donc app/ importable AVANT l'import de core.paths.
sys.path.insert(0, str(HERE.parent))
from core.paths import db_dir, project_root  # noqa: E402

# TBF_ROOT est le seam de test de CETTE factory ; à défaut, la résolution
# canonique du dépôt (core.paths.project_root — RBF_ROOT/TBOT_PROJECT_ROOT).
ROOT = pathlib.Path(os.environ.get("TBF_ROOT") or project_root())

# LE PANNEAU VIT HORS DU DÉPÔT — un panneau, un poste (leçon robinbot
# 2026-08-21 : un panneau versionné devient un conflit de merge multi-postes).
# C'est le panneau de la TBOT factory : fichier distinct de celui du prototype
# (robinbot-panel.txt) — deux consoles, deux surfaces de contrôle.
PANEL_FILE = pathlib.Path(os.environ.get("TBF_PANEL") or (db_dir() / "tbot-panel.txt"))
PANEL_TEMPLATE = HERE / "tbot-panel.exemple.txt"
LOG_DIR    = pathlib.Path(os.environ.get("TBF_LOG_DIR") or (HERE / "logs"))
FACTORY_LOG = LOG_DIR / "tbot-factory.log"
LOCK_FILE  = pathlib.Path(os.environ.get("TBF_LOCK") or (HERE / ".tbot-factory.lock"))
# `.stop` est PARTAGÉ avec le prototype robinbot par choix : UN interrupteur
# d'arrêt par dépôt. Les deux consoles ne cohabitent pas sur ce repo (le
# prototype en production tourne depuis SON dossier, pas d'ici).
STOP_FILE  = pathlib.Path(os.environ.get("TBF_STOP") or (HERE / ".stop"))

# Le verrou est RETOUCHÉ à chaque cycle. « Périmé » = plus vieux que ce délai,
# donc laissé par une factory morte brutalement : on peut passer outre.
LOCK_STALE_SEC = int(os.environ.get("TBF_LOCK_STALE") or 180)

POLL_SEC    = int(os.environ.get("TBF_POLL") or 30)      # rythme du superviseur
STAGGER_SEC = int(os.environ.get("TBF_STAGGER") or 5)    # délai entre 2 départs
# Plafond par tick. DIVERGENCE ASSUMÉE vs prototype (1200 s) : ici le tick
# long NORMAL est une session Claude de développement (cc_app_queue sur un
# ticket costaud), pas un pas de mesure MT5. 1 h de plafond protège du tick
# MORT sans tuer le travail légitime.
TICK_TIMEOUT_SEC = int(os.environ.get("TBF_TIMEOUT") or 3600)
SERVICE_RESTART_BACKOFF_SEC = int(os.environ.get("TBF_SERVICE_BACKOFF") or 60)
FACTORY_LOG_MAX_BYTES = 2 * 1024 * 1024
# La console n'imprime le tableau d'état QUE s'il s'est passé quelque chose,
# plus un battement périodique.
HEARTBEAT_SEC = int(os.environ.get("TBF_HEARTBEAT") or 300)

CLAUDE_BIN = os.environ.get("TBF_CLAUDE_BIN") or "claude"
CLAUDE_MAX_TURNS = int(os.environ.get("TBF_MAX_TURNS") or 40)
PYTHON = sys.executable or "python"

# Garde matière cc_S017 : nombre minimal de NOUVEAUX jours de snapshots GEX
# depuis le dernier run pour justifier une session (tokens).
S017_MIN_NEW_DAYS = int(os.environ.get("TBF_S017_MIN_NEW_DAYS") or 3)
# Un ticket dont la session a déjà été tentée n'est pas rejoué avant ce délai :
# une session qui échoue à flipper `status:` ferait sinon repayer la même
# réflexion à CHAQUE cadence (48 sessions/jour sur le même ticket). Doctrine
# gateway : on paie une fois, on ne s'acharne que sur ce qui est gratuit.
TICKET_COOLDOWN_SEC = int(os.environ.get("TBF_TICKET_COOLDOWN") or 21600)   # 6 h
BLOCKING_COOLDOWN_SEC = int(os.environ.get("TBF_BLOCKING_COOLDOWN") or 3600)  # 1 h


def state_dir() -> pathlib.Path:
    """Le dossier d'état PROPRE à la factory (marqueurs de matière). Résolu à
    l'appel — testable via TBF_STATE_DIR / TBOT_DB_DIR sans recharger."""
    return pathlib.Path(os.environ.get("TBF_STATE_DIR") or (db_dir() / "tbot-factory"))


def s017_gex_dir() -> pathlib.Path:
    return db_dir() / "S017" / "gex"


def mandat_s017_file() -> pathlib.Path:
    return ROOT / "strategies" / "S017_ireland_gex" / "mandat-cc.txt"


def tickets_dir() -> pathlib.Path:
    return ROOT / "tickets"


# == GARDE-FOU R4 (la factory ne peut JAMAIS armer un trade réel) ==============
# Marqueurs interdits dans une spec de worker : leur seule présence au
# catalogue fait REFUSER le démarrage. La liste est volontairement large —
# rater un vrai marqueur coûte un trade réel, attraper un faux positif coûte
# un renommage.
R4_FORBIDDEN_SPEC_MARKERS = (
    "--live", "--real", "live=1", "real=1", "trade_live", "live_trading",
    "tbot_live", "mt5_live", "go-live",
)
# Variables d'environnement purgées de TOUT tick lancé : même posées par
# erreur dans l'environnement de la console, elles n'atteignent aucun enfant.
R4_FORBIDDEN_ENV = ("TBOT_LIVE", "MT5_LIVE", "TBOT_REAL_TRADING", "LIVE_TRADING")


def assert_no_live_markers(workers: list[tuple]) -> None:
    """R4 : promotion LIVE = décision Adrian, JAMAIS un réglage de la factory."""
    for name, _cwd, spec, _interval, _kind in workers:
        low = spec.lower()
        for marker in R4_FORBIDDEN_SPEC_MARKERS:
            if marker in low:
                raise AssertionError(
                    f"R4 VIOLÉ : la spec du worker '{name}' porte le marqueur de "
                    f"trading réel {marker!r}. La factory n'arme JAMAIS un trade "
                    f"live — retire le marqueur ou passe par la décision Adrian "
                    f"hors factory (R4/R10).")


def _child_env(claude_tick: bool = False) -> dict:
    """L'environnement transmis à un tick : purgé des variables d'armement R4 ;
    pour un tick claude, purgé aussi du contexte d'une éventuelle session
    Claude Code parente (leçon gateway : base URL de proxy, marqueurs)."""
    env = dict(os.environ)
    for k in R4_FORBIDDEN_ENV:
        env.pop(k, None)
    if claude_tick:
        for k in list(env):
            if k.startswith(("CLAUDE_", "CLAUDECODE")) or k == "ANTHROPIC_BASE_URL":
                env.pop(k, None)
    return env


# == TICKETS (parsing minimal du frontmatter — pas de dépendance YAML) =========
def ticket_fields(path: pathlib.Path) -> dict:
    """Frontmatter `---` ... `---` -> {clé: valeur} en minuscules côté clé.
    Un fichier illisible ou sans frontmatter rend {} : il est simplement
    ignoré par les gardes (fail-closed, comme le panneau)."""
    try:
        texte = path.read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    if not texte.startswith("---"):
        return {}
    fin = texte.find("\n---", 3)
    if fin == -1:
        return {}
    champs: dict = {}
    for ligne in texte[3:fin].splitlines():
        if ":" not in ligne:
            continue
        cle, _, val = ligne.partition(":")
        champs[cle.strip().lower()] = val.strip()
    return champs


def _attempts_file() -> pathlib.Path:
    return state_dir() / "ticket_attempts.json"


def _load_attempts() -> dict:
    try:
        return json.loads(_attempts_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _note_attempt(ticket_id: str) -> None:
    """Consommer AVANT de payer (doctrine gateway) : la tentative est notée au
    lancement, pas au succès — une session ratée ne rejoue qu'après cooldown."""
    data = _load_attempts()
    data[ticket_id] = time.time()
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        tmp = _attempts_file().with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, _attempts_file())
    except OSError:
        pass    # un marqueur qui rate ne bloque pas l'usine — on risque un rejeu


def find_ticket(to: str | None = None, blocking: bool = False,
                cooldown_sec: int | None = None) -> Optional[pathlib.Path]:
    """Le PREMIER ticket ouvert qui matche (ordre alphabétique = ordre TCK-NNN).
    Un seul ticket par tick — c'est le contrat du catalogue."""
    tdir = tickets_dir()
    if not tdir.is_dir():
        return None
    attempts = _load_attempts()
    now = time.time()
    cd = TICKET_COOLDOWN_SEC if cooldown_sec is None else cooldown_sec
    for f in sorted(tdir.glob("TCK-*.md")):
        ch = ticket_fields(f)
        if ch.get("status", "").lower() != "open":
            continue
        if to is not None and ch.get("to", "").lower() != to:
            continue
        if blocking and ch.get("blocking", "").lower() != "true":
            continue
        tid = ch.get("id") or f.stem
        if (now - float(attempts.get(tid, 0.0))) < cd:
            continue        # déjà tenté récemment — on ne repaie pas en boucle
        return f
    return None


# == GARDES « MATIÈRE » DES WORKERS claude: ====================================
# Une garde est du Python pur, GRATUIT, exécuté par la factory elle-même à
# chaque tick dû. Elle rend None (pas de matière → no-op, aucun processus) ou
# (prompt, consommer) où `consommer` est appelé JUSTE AVANT le lancement payé
# (jamais en dry-run) — c'est le « consomme avant de payer » du gateway.
Matiere = tuple[str, Optional[Callable[[], None]]]


def _s017_seen_file() -> pathlib.Path:
    return state_dir() / "cc_S017_seen.json"


def _s017_snapshot_days() -> set[str]:
    """Les jours (YYYY-MM-DD) présents dans C:/db/tradingBot/S017/gex/ —
    canoniques ET intraday confondus : un jour de données est un jour."""
    gdir = s017_gex_dir()
    if not gdir.is_dir():
        return set()
    jours = set()
    for f in gdir.glob("SPY_gex_*.csv"):
        m = re.match(r"SPY_gex_(\d{4}-\d{2}-\d{2})", f.name)
        if m:
            jours.add(m.group(1))
    return jours


def guard_cc_s017() -> Optional[Matiere]:
    """Matière = au moins S017_MIN_NEW_DAYS nouveaux jours de snapshots depuis
    le dernier run (marqueur fichier). Le mandat est relu À CHAQUE lancement :
    l'éditer est une commande à chaud, comme le panneau."""
    jours = _s017_snapshot_days()
    try:
        vus = set(json.loads(_s017_seen_file().read_text(encoding="utf-8")).get("seen", []))
    except (OSError, ValueError):
        vus = set()
    nouveaux = sorted(jours - vus)
    if len(nouveaux) < S017_MIN_NEW_DAYS:
        return None
    mandat_f = mandat_s017_file()
    try:
        mandat = mandat_f.read_text(encoding="utf-8-sig").strip()
    except OSError:
        log(f"cc_S017 : matière présente ({len(nouveaux)} nouveaux jours) mais "
            f"MANDAT INTROUVABLE ({mandat_f}) — aucune session sans mandat.")
        return None
    prompt = (
        f"Tu es cc-S017, le Claude Code dédié à la stratégie S017 ireland_gex "
        f"(lis CLAUDE.md du dossier courant).\n"
        f"Matière : {len(nouveaux)} nouveau(x) jour(s) de snapshots GEX depuis "
        f"ton dernier passage ({', '.join(nouveaux)}).\n\n"
        f"Ton mandat (strategies/S017_ireland_gex/mandat-cc.txt, éditable à "
        f"chaud par Adrian) :\n\n{mandat}\n")

    def consommer() -> None:
        try:
            state_dir().mkdir(parents=True, exist_ok=True)
            tmp = _s017_seen_file().with_suffix(".json.tmp")
            tmp.write_text(json.dumps({"seen": sorted(jours),
                                       "at": _ts()}, indent=2), encoding="utf-8")
            os.replace(tmp, _s017_seen_file())
        except OSError:
            pass

    return prompt, consommer


def _prompt_queue(role: str, perimetre: str, ticket: pathlib.Path, tid: str) -> str:
    rel = ticket.relative_to(ROOT) if ticket.is_relative_to(ROOT) else ticket
    return (
        f"Tu es {role} du projet TradingBot (lis le CLAUDE.md racine du dépôt "
        f"et celui de ton dossier s'il existe).\n"
        f"Traite UNIQUEMENT le ticket {rel} ({tid}) :\n"
        f"1. Lis le ticket en entier et réalise la demande, strictement dans "
        f"ton périmètre ({perimetre}).\n"
        f"2. Réponds dans la section `## Réponse` du ticket et passe "
        f"`status: answered` dans son frontmatter.\n"
        f"3. `git add` + `git commit` sur la branche dev de TES fichiers "
        f"uniquement — jamais ceux modifiés par d'autres acteurs. Pas de push.\n"
        f"Règles : contrats R1-R10 du projet, aucun trade réel, promotion "
        f"PAPER/LIVE = décision Adrian uniquement. Un seul ticket : celui-ci.\n")


def guard_cc_app_queue() -> Optional[Matiere]:
    t = find_ticket(to="cc-app")
    if t is None:
        return None
    tid = ticket_fields(t).get("id") or t.stem
    return (_prompt_queue("cc-app", "app/ — services communs, tests obligatoires (R3)", t, tid),
            lambda: _note_attempt(tid))


def guard_cc_spec_queue() -> Optional[Matiere]:
    t = find_ticket(to="cc-spec")
    if t is None:
        return None
    tid = ticket_fields(t).get("id") or t.stem
    return (_prompt_queue("cc-spec", "spec/ — spécifications de l'application "
                          "(specification-app/), jamais d'implémentation", t, tid),
            lambda: _note_attempt(tid))


def guard_cc_support_block() -> Optional[Matiere]:
    t = find_ticket(blocking=True, cooldown_sec=BLOCKING_COOLDOWN_SEC)
    if t is None:
        return None
    tid = ticket_fields(t).get("id") or t.stem
    rel = t.relative_to(ROOT) if t.is_relative_to(ROOT) else t
    prompt = (
        f"Tu es cc-support du projet TradingBot (lis support/CLAUDE.md).\n"
        f"Le ticket {rel} ({tid}) est OUVERT et BLOQUANT. Applique tes règles "
        f"de déblocage :\n"
        f"- réponse évidente → réponds seul IMMÉDIATEMENT : section "
        f"`## Réponse` avec préconisation d'abord, puis `status: answered` ;\n"
        f"- sinon → prépare la QA Adrian avec préconisation pré-sélectionnée "
        f"(canal Telegram ou hook) et documente l'état dans le ticket.\n"
        f"Interdits : coder l'app, écrire des specs, développer une stratégie, "
        f"décider une promotion PAPER/LIVE.\n"
        f"`git add` + `git commit` sur dev de TES fichiers uniquement. Pas de push.\n")
    return prompt, (lambda: _note_attempt(tid))


CLAUDE_GUARDS: dict[str, Callable[[], Optional[Matiere]]] = {
    "cc_S017": guard_cc_s017,
    "cc_app_queue": guard_cc_app_queue,
    "cc_spec_queue": guard_cc_spec_queue,
    "cc_support_block": guard_cc_support_block,
}


# == CATALOGUE DES WORKERS (FROID — redémarrage requis) ========================
# (nom, cwd, spec, intervalle_sec, nature)
#   nature "tick"    : processus éphémère — sortir est NORMAL.
#   nature "service" : processus persistant, relancé s'il meurt (aucun en v1 ;
#                      le serveur web de supervision arrivera ici).
#
# FAMILLE paper_S0NN — PRÉVUE, AUCUN WORKER ACTIF (aucune stratégie au statut
# PAPER dans strategies/*/manifest.yaml — le registre est affiché au
# démarrage). Le jour où Adrian promeut une stratégie en PAPER (décision R10),
# on dérive son worker ICI, à froid, sur le modèle :
#     ("paper_S013", ROOT / "strategies" / "S013_macd_fx",
#      "py:strategies/S013_macd_fx/run_paper.py", 3600, "tick"),
# c'est-à-dire un runner `py:` scellé propre à la stratégie (journal chaîné
# dans C:/db/tradingBot/S013/, codes 0/2/3/4), JAMAIS un flag de la factory —
# le garde-fou R4 ci-dessus refuse tout marqueur live au catalogue.
WORKERS: list[tuple[str, pathlib.Path, str, int, str]] = [
    # Collecteur GEX S017 : py pur, fenêtre horaire + rattrapage DANS le
    # wrapper (pas ici) — la factory cadence, le wrapper décide.
    ("gex_S017",  ROOT, "py:app/orchestrator/tbot-collecte-gex-s017.py", 900, "tick"),
    # cc-S017 : session de développement/amélioration continue de la
    # stratégie. Garde : >= N nouveaux jours de snapshots. Mandat à chaud.
    ("cc_S017",   ROOT / "strategies" / "S017_ireland_gex", "claude:cc_S017", 3600, "tick"),
    # Constructeurs d'application : la file tickets/ anime cc-app et cc-spec.
    # Un tick = UN ticket. File vide = veille gratuite.
    ("cc_app_queue",  ROOT / "app",  "claude:cc_app_queue",  1800, "tick"),
    ("cc_spec_queue", ROOT / "spec", "claude:cc_spec_queue", 1800, "tick"),
    # Débloqueur : un ticket bloquant ouvert → session cc-support immédiate.
    ("cc_support_block", ROOT / "support", "claude:cc_support_block", 300, "tick"),
    # Canal Telegram : mécanique du prototype REPRISE TELLE QUELLE (les
    # scripts robinbot-* sont réutilisés, pas réécrits). Sans secrets
    # (C:/db/tradingBot/gateway/, notifier/), chaque tick sort en 2
    # « ressource externe indisponible » — vérifié dans leur code, la factory
    # réessaie sans crier. Le gabarit du panneau les livre OFF tant que les
    # tokens ne sont pas posés (TCK-004).
    ("gateway",   ROOT, "py:app/orchestrator/robinbot-gateway.py", 30, "tick"),
    ("notify",    ROOT, "py:app/orchestrator/robinbot-notify.py",  300, "tick"),
    # Études scellées en vol, migrées du prototype (TCK-009/T10) : py pur,
    # cadences IDENTIQUES à robinbot. Codes 0/2/3/4 contractuels (AUTO-OFF
    # sur 3/4). OFF par défaut au panneau : chaque bascule d'étude = GO
    # Adrian explicite après déplacement du journal (studies/CUTOVER.md) —
    # JAMAIS deux factories sur le même journal (entrelacement = fausse
    # alarme d'altération). État : C:/db/tradingBot/<étude>/ via core.paths.
    ("gold_forward",  ROOT, "py:studies/gold_forward/run_forward.py",    3600, "tick"),
    ("s13_forward",   ROOT, "py:studies/s13_forward/run_forward.py",     3600, "tick"),
    ("macd_ai_paper", ROOT, "py:studies/macd_ai_paper/run_paper.py",     3600, "tick"),
    ("s14_sentiment", ROOT, "py:studies/s14_sentiment/run_sentiment.py", 1800, "tick"),
    ("alexg_paper",   ROOT, "py:studies/alexg_paper/run_paper.py",       3600, "tick"),
]

# SEAM DE TEST (et uniquement ça) : un catalogue JSON injecté par
# l'environnement remplace celui ci-dessus — les tests montent des workers
# factices sans jamais lancer les vrais. Lu à l'import → donnée FROIDE.
_CAT_ENV = os.environ.get("TBF_CATALOGUE")
if _CAT_ENV:
    WORKERS = [(w["name"], pathlib.Path(w.get("cwd") or ROOT), w["spec"],
                int(w.get("interval", 60)), w.get("kind", "tick"))
               for w in json.loads(_CAT_ENV)]

# R4 : le catalogue — injecté ou non — est refusé s'il porte un marqueur live.
assert_no_live_markers(WORKERS)

WORKER_NAMES = [w[0] for w in WORKERS]
WORKER_BY_NAME = {w[0]: w for w in WORKERS}

# Défauts du panneau GÉNÉRÉ quand le gabarit versionné manque : seul le
# collecteur (py pur, zéro token) naît allumé. Tout worker à tokens ou à
# secrets naît éteint — Adrian allume à chaud, en conscience.
DEFAULT_ON = {"gex_S017"}


# == ÉTAT INTERNE (vivant, jamais la source de vérité) =========================
_running: dict[str, subprocess.Popen] = {}
_started_at: dict[str, float] = {}
_last_run: dict[str, float] = {}          # worker -> t du dernier LANCEMENT
_last_result: dict[str, dict] = {}        # worker -> {code, label, duree, fin}
_stop = threading.Event()
_services_coupes: set = set()
_events = threading.Event()               # « il s'est passé quelque chose »
_lock_console = threading.Lock()

EXIT_LABELS = {
    0: "OK",
    2: "ressource externe indisponible (réessai au prochain tick)",
    3: "SCELLÉ VIOLÉ",
    4: "JOURNAL ALTÉRÉ",
}
INCIDENT_CODES = (3, 4)     # les deux alarmes de falsification


# == JOURNAL ET CONSOLE ========================================================
def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _rotate_if_needed() -> None:
    try:
        if FACTORY_LOG.exists() and FACTORY_LOG.stat().st_size > FACTORY_LOG_MAX_BYTES:
            backup = FACTORY_LOG.with_suffix(".log.1")
            backup.unlink(missing_ok=True)
            FACTORY_LOG.rename(backup)
    except OSError:
        pass        # un log qui rate ne doit JAMAIS tuer la boucle


def log(msg: str) -> None:
    """Écrit à l'écran ET sur disque (le doublage ici, pas par un `| tee`)."""
    line = f"[{_ts()}] {msg}"
    with _lock_console:
        print(line, flush=True)
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            _rotate_if_needed()
            with open(FACTORY_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def alerte(msg: str) -> None:
    """Un incident doit être IMPOSSIBLE à rater dans un flux de lignes grises."""
    bandeau = "!" * 74
    log(bandeau)
    for ligne in msg.splitlines():
        log("!! " + ligne)
    log(bandeau)


# == VERROU SINGLE-INSTANCE ====================================================
def lock_is_fresh() -> bool:
    """True si une AUTRE tbot factory semble vivante sur ce poste. Deux usines
    = deux ticks concurrents sur les mêmes fichiers d'état. Une seule, point."""
    if not LOCK_FILE.exists():
        return False
    try:
        return (time.time() - LOCK_FILE.stat().st_mtime) < LOCK_STALE_SEC
    except OSError:
        return False


def write_lock() -> None:
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(f"pid {os.getpid()} :: {_ts()}\n", encoding="utf-8")
    except OSError:
        pass


def clear_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# == PANNEAU DE CONTRÔLE (CHAUD — relu à chaque cycle) =========================
PANEL_HEADER = """\
# ═══════════════════════════════════════════════════════════════════════════
# PANNEAU DE CONTRÔLE tbot factory — relu à CHAQUE cycle
# ═══════════════════════════════════════════════════════════════════════════
# Modifier ce fichier prend effet AU TICK SUIVANT. Aucun redémarrage.
#
#   worker = on           actif, cadence du catalogue
#   worker = on:1800      actif, cadence forcée à 1800 s
#   worker = off          éteint
#
# Un worker ABSENT de ce fichier est OFF : ce panneau est une surface de
# CONTRÔLE, pas un recensement. Ce qui n'est pas explicitement allumé est
# éteint — un panneau à moitié écrit doit taire l'usine, jamais l'ouvrir.
#
# AJOUTER ou RETIRER un worker se fait dans le CATALOGUE
# (app/orchestrator/tbot-factory.py, section WORKERS) et exige un redémarrage.
# ═══════════════════════════════════════════════════════════════════════════
"""


def ensure_panel() -> None:
    """Crée le panneau s'il manque. Machine neuve : copie du GABARIT versionné
    (tbot-panel.exemple.txt — défauts économes en tokens). Sans gabarit : seul
    DEFAULT_ON naît allumé — un worker à tokens ne s'allume jamais tout seul."""
    if PANEL_FILE.exists():
        return
    try:
        PANEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        if PANEL_TEMPLATE.exists():
            PANEL_FILE.write_text(
                PANEL_TEMPLATE.read_text(encoding="utf-8-sig"),
                encoding="utf-8")
            log(f"panneau créé depuis le gabarit : {PANEL_FILE}")
            return
        lignes = [PANEL_HEADER]
        for name, _cwd, _spec, interval, kind in WORKERS:
            etat = "on " if name in DEFAULT_ON else "off"
            nature = "service persistant" if kind == "service" else f"tick toutes les {interval}s"
            lignes.append(f"{name} = {etat}          # {nature}")
        PANEL_FILE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
        log(f"panneau créé : {PANEL_FILE} (défauts économes : ON={sorted(DEFAULT_ON)})")
    except OSError as e:  # noqa: BLE001
        log(f"ATTENTION : création du panneau impossible ({e!r}) — tous les workers restent OFF.")


_panel_cache: dict[str, tuple[bool, int | None]] = {}


def read_panel() -> dict[str, tuple[bool, int | None]]:
    """-> {worker: (allumé, cadence forcée ou None)}. Tolérant par
    construction : ligne illisible ignorée, fichier illisible → DERNIER
    panneau valide connu, fichier ABSENT → tout OFF (fail-closed)."""
    global _panel_cache
    if not PANEL_FILE.exists():
        log(f"PANNEAU INTROUVABLE ({PANEL_FILE.name}) → tous les workers OFF.")
        _panel_cache = {}
        return {}
    out: dict[str, tuple[bool, int | None]] = {}
    try:
        for raw in PANEL_FILE.read_text(encoding="utf-8-sig").splitlines():
            ligne = raw.split("#", 1)[0].strip()
            if not ligne or "=" not in ligne:
                continue
            nom, val = ligne.split("=", 1)
            nom, val = nom.strip(), val.strip().lower()
            if not nom:
                continue
            cadence: int | None = None
            if ":" in val:
                val, _, brut = val.partition(":")
                val = val.strip()
                try:
                    cadence = max(1, int(brut.strip()))
                except ValueError:
                    log(f"panneau : cadence illisible pour '{nom}' ({brut!r}) — "
                        f"cadence du catalogue conservée.")
            out[nom] = (val in ("on", "true", "1", "yes", "oui"), cadence)
    except OSError as e:  # noqa: BLE001
        log(f"ATTENTION : lecture du panneau impossible ({e!r}) — on garde le précédent.")
        return dict(_panel_cache)
    _panel_cache = out
    return out


def panel_set_off(worker: str, raison: str) -> None:
    """Éteint un worker DANS le panneau (AUTO-OFF sur incident 3/4), en place,
    trace de la raison en commentaire pour celui qui rallumera."""
    try:
        lignes = PANEL_FILE.read_text(encoding="utf-8-sig").splitlines() if PANEL_FILE.exists() else []
        trouve = False
        for i, raw in enumerate(lignes):
            code = raw.split("#", 1)[0]
            if "=" in code and code.split("=", 1)[0].strip() == worker:
                lignes[i] = f"{worker} = off          # AUTO-OFF {_ts()} — {raison}"
                trouve = True
                break
        if not trouve:
            lignes.append(f"{worker} = off          # AUTO-OFF {_ts()} — {raison}")
        PANEL_FILE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    except OSError as e:  # noqa: BLE001
        log(f"ATTENTION : impossible d'éteindre '{worker}' dans le panneau ({e!r}) — "
            f"FAIS-LE À LA MAIN, l'incident risque de se répéter à chaque cycle.")


# == REGISTRE DES STRATÉGIES (affiché au démarrage) ============================
def scan_strategies() -> list[dict]:
    """strategies/*/manifest.yaml -> [{id, name, status, magic}]. Parsing
    ligne-à-ligne des clés de premier niveau (pas de dépendance YAML pour
    quatre champs). Un manifest illisible est signalé, jamais fatal."""
    out = []
    sdir = ROOT / "strategies"
    if not sdir.is_dir():
        return out
    for d in sorted(sdir.iterdir()):
        mf = d / "manifest.yaml"
        if not mf.is_file():
            continue
        champs = {}
        try:
            for ligne in mf.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r"^(strategy_id|name|status|magic)\s*:\s*([^#]*)", ligne)
                if m:
                    champs[m.group(1)] = m.group(2).strip()
        except OSError:
            champs = {}
        out.append({"id": champs.get("strategy_id", d.name),
                    "name": champs.get("name", ""),
                    "status": champs.get("status", "?"),
                    "magic": champs.get("magic", "?"),
                    "dir": d.name})
    return out


# == CONSTRUCTION DES COMMANDES ================================================
def _dotted_module(rel: str) -> str | None:
    """'x/y/run.py' -> 'x.y.run' si et seulement si TOUS les dossiers traversés
    sont de vrais packages (forme -m des .bat d'origine) — sinon script."""
    p = pathlib.Path(rel)
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if len(parts) < 2:
        return None
    dossier = ROOT
    for seg in parts[:-1]:
        dossier = dossier / seg
        if not (dossier / "__init__.py").exists():
            return None       # pas un package -> lancement en script
    return ".".join(parts)


def build_cmd(spec: str) -> list[str]:
    """spec -> argv. Deux familles seulement, volontairement.

      py:<chemin> [args]   commande Python pure — ZÉRO token, le cas normal
      claude:<clé>         session Claude headless — le PROMPT ne figure PAS
                           dans l'argv : il passe par STDIN (plafond ~32k de
                           la ligne de commande Windows, troncature silencieuse
                           — leçon gateway). Flags identiques au prototype.
    """
    if spec.startswith("py:"):
        toks = spec[3:].split()
        if not toks:
            raise ValueError(f"spec py: vide ({spec!r})")
        cible, args = toks[0], toks[1:]
        mod = _dotted_module(cible)
        if mod:
            return [PYTHON, "-m", mod, *args]
        return [PYTHON, str((ROOT / cible)), *args]

    if spec.startswith("claude:"):
        # Sous Windows `claude` est un shim npm .cmd, pas un .exe : CreateProcess
        # ne résout pas un ["claude", ...] nu. On passe par cmd.exe qui applique
        # PATHEXT. (Leçon héritée du prototype — deux heures payées chez DURIAN.)
        return ["cmd", "/c", CLAUDE_BIN, "-p",
                "--output-format", "json",
                "--max-turns", str(CLAUDE_MAX_TURNS)]

    raise ValueError(f"spec inconnue : {spec!r} (attendu 'py:...' ou 'claude:...')")


# == LANCEMENT ET RÉCOLTE ======================================================
def _tick_log_path(name: str) -> pathlib.Path:
    d = LOG_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"


def _feed_stdin(proc: subprocess.Popen, texte: str) -> None:
    """Nourrit le prompt au CLI claude puis FERME stdin (sans fermeture, claude
    attend la fin d'entrée pour toujours). Dans un thread : un prompt plus gros
    que le tampon du pipe bloquerait sinon la boucle de la factory."""
    try:
        proc.stdin.write(texte)
        proc.stdin.close()
    except OSError:
        pass    # le processus est peut-être déjà mort — le reaper le dira


def launch(name: str, dry: bool = False) -> None:
    """Lance UN tick. Ne bloque pas : la récolte se fait dans un thread.
    Pour un worker claude:, la GARDE décide d'abord — pas de matière, pas de
    processus, pas de token."""
    _name, cwd, spec, _interval, kind = WORKER_BY_NAME[name]

    prompt: str | None = None
    consommer: Callable[[], None] | None = None

    if spec.startswith("py:"):
        # FICHIER INTROUVABLE ≠ « ressource externe indisponible ». On crie une
        # fois par cadence, et on ne lance rien (boucle silencieuse interdite).
        toks = spec[3:].split()
        cible = toks[0] if toks else ""
        if cible and not (ROOT / cible).exists():
            _last_run[name] = time.time()
            alerte(
                f"[{name}] fichier INTROUVABLE : {ROOT / cible}\n"
                f"Faute de frappe au CATALOGUE, ou fichier pas encore livré.\n"
                f"Éteins le worker au panneau, ou corrige le catalogue (à froid)."
            )
            return

    elif spec.startswith("claude:"):
        cle = spec[7:].strip()
        garde = CLAUDE_GUARDS.get(cle)
        if garde is not None:
            try:
                matiere = garde()
            except Exception as e:  # noqa: BLE001 — une garde cassée ne tue pas l'usine
                _last_run[name] = time.time()
                log(f"ERREUR [{name}] garde matière en échec : {type(e).__name__} "
                    f"— {str(e)[:150]} (réessai à la prochaine cadence)")
                return
            if matiere is None:
                _last_run[name] = time.time()
                log(f"veille [{name}] : pas de matière — aucun processus, aucun token")
                return
            prompt, consommer = matiere
        else:
            # Clé inconnue = prompt LITTÉRAL (forme du prototype robinbot).
            prompt = cle
        if not cwd.is_dir():
            _last_run[name] = time.time()
            alerte(f"[{name}] cwd INTROUVABLE : {cwd}\n"
                   f"Corrige le catalogue (à froid) ou éteins le worker au panneau.")
            return

    try:
        cmd = build_cmd(spec)
    except ValueError as e:  # noqa: BLE001
        log(f"ERREUR [{name}] : {e} — worker ignoré (corrige le CATALOGUE, à froid).")
        return

    if dry:
        detail = f" [prompt {len(prompt)} chars via STDIN]" if prompt is not None else ""
        log(f"DRY-RUN [{name}] (cwd={cwd}) :: {' '.join(cmd)}{detail}")
        _last_run[name] = time.time()
        return

    # Consommer AVANT de payer (doctrine gateway) : marqueurs de matière notés
    # maintenant — une session qui plante ne rejouera pas en boucle facturée.
    if consommer is not None:
        consommer()

    logf = _tick_log_path(name)
    est_claude = spec.startswith("claude:")
    try:
        with open(logf, "a", encoding="utf-8") as lf:
            lf.write(f"===== {_ts()} TICK {name} :: {' '.join(cmd)} =====\n")
            if prompt is not None:
                lf.write(f"----- prompt ({len(prompt)} chars) -----\n{prompt}\n----- fin prompt -----\n")
            lf.flush()
            proc = subprocess.Popen(
                cmd, cwd=str(cwd),
                stdout=lf, stderr=subprocess.STDOUT,
                stdin=(subprocess.PIPE if prompt is not None else subprocess.DEVNULL),
                text=True, encoding="utf-8",
                env=_child_env(claude_tick=est_claude),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except FileNotFoundError as e:  # noqa: BLE001
        log(f"ERREUR [{name}] : exécutable introuvable ({e}).")
        return
    except Exception as e:  # noqa: BLE001 — un lancement raté ne tue pas l'usine
        log(f"ERREUR [{name}] lancement impossible : {e!r}")
        return

    if prompt is not None:
        threading.Thread(target=_feed_stdin, args=(proc, prompt), daemon=True).start()

    _running[name] = proc
    _started_at[name] = time.time()
    _last_run[name] = time.time()
    log(f"lance [{name}] {'(service)' if kind == 'service' else ''}"
        f"{' (session claude)' if est_claude else ''} → {logf.name}")
    _events.set()
    threading.Thread(target=_reap, args=(name, proc, kind, logf),
                     daemon=True).start()


def _resume_du_worker(logf: pathlib.Path) -> str:
    """La dernière ligne parlante qu'a écrite le worker — remontée en console,
    parce qu'une réflexion de quarante secondes et une boîte vide se
    ressemblent sinon (deux lignes OK, l'une longue, l'autre courte)."""
    try:
        lignes = [l.strip() for l in logf.read_text(encoding="utf-8",
                                                    errors="replace").splitlines()]
    except OSError:
        return ""
    for ligne in reversed(lignes):
        if not ligne or ligne.startswith("=====") or ligne.startswith("-----"):
            continue
        if ligne.startswith("[") and "] " in ligne:
            ligne = ligne.split("] ", 1)[1]
        return ligne[:150]
    return ""


def _reap(name: str, proc: subprocess.Popen, kind: str,
          logf: Optional[pathlib.Path] = None) -> None:
    """Attend la fin du tick, traduit son code de sortie, agit sur incident."""
    debut = _started_at.get(name, time.time())
    timeout = None if kind == "service" else TICK_TIMEOUT_SEC
    try:
        code = proc.wait(timeout=timeout)
        duree = time.time() - debut
        label = EXIT_LABELS.get(code, f"code inattendu {code}")
        _last_result[name] = {"code": code, "label": label, "duree": duree, "fin": time.time()}

        resume = _resume_du_worker(logf) if logf else ""
        suffixe = f" — {resume}" if resume else ""
        if code == 0:
            log(f"fini  [{name}] OK en {duree:.1f}s{suffixe}")
        elif code == 2:
            # PAS une erreur : secrets Telegram pas posés, CBOE injoignable une
            # minute. La cause précise est dans le log DU WORKER.
            log(f"info  [{name}] ressource externe indisponible ({duree:.1f}s)"
                f"{suffixe or f' — cause dans {LOG_DIR / name}'}")
        elif code in INCIDENT_CODES:
            quoi = ("le SCELLÉ (hash des paramètres) est violé"
                    if code == 3 else "le JOURNAL est altéré (chaîne de hachage cassée)")
            panel_set_off(name, f"sortie {code} — {EXIT_LABELS[code]}")
            alerte(
                f"INCIDENT [{name}] — sortie {code} : {quoi}.\n"
                f"Le worker vient d'être mis OFF dans le panneau : le relancer ne "
                f"réparerait rien, ça ne ferait qu'une deuxième trace de la violation.\n"
                f"À FAIRE, dans l'ordre : lire {LOG_DIR / name}, puis la doc "
                f"d'intégrité du worker, puis `git log` sur ses paramètres.\n"
                f"NE PAS 'réparer' les paramètres : toute modification invalide le test."
            )
        elif kind == "service" and name in _services_coupes:
            log(f"fini  [{name}] service arrêté sur demande, après {duree:.0f}s")
        elif kind == "service":
            log(f"ATTENTION [{name}] le service persistant s'est ARRÊTÉ (code {code}) "
                f"après {duree:.0f}s — relance dans {SERVICE_RESTART_BACKOFF_SEC}s.")
        else:
            log(f"ERREUR [{name}] sortie inattendue {code} en {duree:.1f}s — "
                f"voir {LOG_DIR / name}{suffixe}")

    except subprocess.TimeoutExpired:
        # On tue TOUT L'ARBRE : tuer le seul parent orphelinerait l'enfant réel
        # (python.exe, ou claude.exe sous un cmd /c) qui continuerait à écrire.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)
        duree = time.time() - debut
        _last_result[name] = {"code": "TIMEOUT", "label": f"tué après {TICK_TIMEOUT_SEC}s",
                              "duree": duree, "fin": time.time()}
        log(f"TIMEOUT [{name}] arbre tué après {TICK_TIMEOUT_SEC}s. "
            f"L'état sur disque est intact — le prochain tick reprend.")
    finally:
        _running.pop(name, None)
        _started_at.pop(name, None)
        _events.set()


# == TABLEAU D'ÉTAT ============================================================
def _humain(sec: float) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m{sec % 60:02d}"
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}"


def status_lines(panel: dict[str, tuple[bool, int | None]], now: float) -> list[str]:
    """Une ligne par worker : nom · état · dernier tick · code · durée · prochain."""
    out = [f"{'WORKER':<17} {'ÉTAT':<10} {'DERNIER TICK':<14} {'RÉSULTAT':<34} PROCHAIN"]
    for name, _cwd, _spec, interval, kind in WORKERS:
        on, cadence = panel.get(name, (False, None))
        periode = cadence or interval

        if name in _running:
            etat = "EN VOL"
        elif not on:
            etat = "off"
        else:
            etat = "service" if kind == "service" else "armé"

        res = _last_result.get(name)
        if res is None:
            dernier, resultat = "—", "(aucun depuis le démarrage)"
        else:
            dernier = _humain(now - res["fin"]) + " ago"
            resultat = f"{res['code']} · {res['label']} · {res['duree']:.1f}s"

        if name in _running:
            prochain = f"en cours ({_humain(now - _started_at.get(name, now))})"
        elif not on:
            prochain = "—"
        elif kind == "service":
            prochain = "relance si mort"
        else:
            reste = periode - (now - _last_run.get(name, 0.0))
            prochain = "maintenant" if reste <= 0 else f"dans {_humain(reste)}"

        out.append(f"{name:<17} {etat:<10} {dernier:<14} {resultat:<34} {prochain}")
    return out


def print_status(panel, now: float) -> None:
    for ligne in status_lines(panel, now):
        log("  " + ligne)


def print_header(dry: bool) -> None:
    log("=" * 78)
    log(f"tbot factory — LA console TradingBot. Si elle s'arrête, RIEN ne tourne."
        f"{'  [DRY-RUN]' if dry else ''}")
    log(f"racine   : {ROOT}")
    log(f"panneau  : {PANEL_FILE}  (À CHAUD — relu à chaque cycle)")
    log(f"logs     : {LOG_DIR}")
    log(f"arrêt    : Ctrl-C, ou créer {STOP_FILE.name}")
    log(f"réglages : poll {POLL_SEC}s · stagger {STAGGER_SEC}s · timeout tick "
        f"{TICK_TIMEOUT_SEC}s   (À FROID — redémarrage requis)")
    log("-" * 78)
    log("CATALOGUE (à froid) :")
    for name, cwd, spec, interval, kind in WORKERS:
        nature = "SERVICE persistant" if kind == "service" else f"tick / {interval}s"
        log(f"  {name:<17} {nature:<20} {spec}   (cwd={cwd})")
    log("-" * 78)
    # REGISTRE DES STRATÉGIES : affiché pour situer la famille paper_S0NN
    # (aucun worker paper tant qu'aucune stratégie n'est au statut PAPER —
    # la dérivation est documentée au CATALOGUE, la promotion est à Adrian).
    strategies = scan_strategies()
    if strategies:
        log("REGISTRE STRATÉGIES (strategies/*/manifest.yaml) :")
        for s in strategies:
            log(f"  {s['id']:<26} {s['name']:<22} {s['status']:<12} magic {s['magic']}")
        en_paper = [s["id"] for s in strategies if s["status"].upper() == "PAPER"]
        if en_paper:
            log(f"  → stratégies PAPER sans worker au catalogue : {', '.join(en_paper)} "
                f"— dérive leur worker paper_S0NN (à froid, voir CATALOGUE).")
        else:
            log("  → aucune stratégie PAPER : famille paper_S0NN sans worker actif (normal).")
    log("-" * 78)


# == LE CYCLE ==================================================================
def due(name: str, panel: dict, now: float) -> bool:
    """Trois refus, dans l'ordre : déjà en vol, éteint au panneau (y compris
    par absence de ligne), pas encore l'heure."""
    if name in _running:
        return False
    on, cadence = panel.get(name, (False, None))
    if not on:
        return False
    _n, _cwd, _spec, interval, kind = WORKER_BY_NAME[name]
    return (now - _last_run.get(name, 0.0)) >= (cadence or interval)


def run_cycle(panel: dict, dry: bool = False, now: float | None = None) -> list[str]:
    """Une ronde : lance tout ce qui est dû, échelonné. Rend les noms lancés."""
    now = time.time() if now is None else now
    lances: list[str] = []
    for name in WORKER_NAMES:
        if _stop.is_set():
            break
        if not due(name, panel, now):
            continue
        if lances and STAGGER_SEC > 0:
            _stop.wait(STAGGER_SEC)
        launch(name, dry=dry)
        lances.append(name)
    return lances


def stop_requested() -> bool:
    return STOP_FILE.exists()


def _ticks_en_vol() -> list[str]:
    """Les workers ÉPHÉMÈRES encore en cours (un service ne finit jamais)."""
    return [n for n in list(_running) if WORKER_BY_NAME[n][4] != "service"]


def arreter_services() -> None:
    """Coupe les services persistants : un service ne mesure rien, il SERT —
    le couper ne perd que la page de quelqu'un qui la rechargera."""
    for name in list(_running):
        if WORKER_BY_NAME[name][4] != "service":
            continue
        proc = _running.get(name)
        if proc is None:
            continue
        log(f"arrêt du service [{name}] (pid {proc.pid}) — il ne finit jamais de lui-même.")
        _services_coupes.add(name)
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)


def run(dry: bool = False, once: bool = False) -> int:
    if not dry and lock_is_fresh():
        detenteur = LOCK_FILE.read_text(encoding="utf-8").strip() if LOCK_FILE.exists() else "?"
        log(f"REFUS DE DÉMARRER : une autre tbot factory semble vivante "
            f"({LOCK_FILE.name}, {detenteur}, touché il y a moins de {LOCK_STALE_SEC}s).\n"
            f"        Deux usines = deux ticks concurrents sur les mêmes fichiers d'état.\n"
            f"        Si tu es SÛR qu'aucune ne tourne : supprime {LOCK_FILE} et relance.")
        return 1

    if stop_requested():
        log(f"REFUS DE DÉMARRER : {STOP_FILE.name} est présent (arrêt demandé). "
            f"Supprime-le pour relancer.")
        return 1

    ensure_panel()
    print_header(dry)
    if not dry:
        write_lock()

    dernier_panneau: dict | None = None
    dernier_battement = 0.0
    drainage = ""
    code_retour = 0

    try:
        while not _stop.is_set():
            now = time.time()
            if not dry:
                write_lock()        # battement : garde le verrou frais

            panel = read_panel()
            if panel != dernier_panneau:
                allumes = [n for n in WORKER_NAMES if panel.get(n, (False, None))[0]]
                eteints = [n for n in WORKER_NAMES if not panel.get(n, (False, None))[0]]
                log(f"panneau : ON={', '.join(allumes) or '(aucun)'} · "
                    f"OFF={', '.join(eteints) or '(aucun)'}")
                inconnus = [n for n in panel if n not in WORKER_BY_NAME]
                if inconnus:
                    log(f"panneau : lignes sans worker au catalogue, ignorées → "
                        f"{', '.join(inconnus)} (faute de frappe ? ajout à froid oublié ?)")
                dernier_panneau = panel
                _events.set()

            # ---- ARRÊT PROPRE : on cesse de LANCER, on laisse finir. ----------
            if not drainage and stop_requested():
                drainage = STOP_FILE.name
            if drainage:
                arreter_services()
                if not _ticks_en_vol():
                    log(f"arrêt propre ({drainage}) terminé : zéro tick en vol, zéro perte. "
                        f"Verrou libéré.")
                    break
                log(f"arrêt propre ({drainage}) : plus rien ne démarre, on attend "
                    f"{', '.join(_ticks_en_vol())}. Aucun tick ne sera tué.")
                time.sleep(min(POLL_SEC, 5))
                continue

            lances = run_cycle(panel, dry=dry, now=now)

            if lances or _events.is_set() or (time.time() - dernier_battement) > HEARTBEAT_SEC:
                _events.clear()
                print_status(panel, time.time())
                dernier_battement = time.time()

            if once:
                if _ticks_en_vol() and not dry:
                    log("--once : on attend la fin des ticks lancés…")
                    while _ticks_en_vol() and not _stop.is_set():
                        time.sleep(0.5)
                    print_status(panel, time.time())
                elif not lances:
                    log("--once : rien n'était dû ce cycle → sortie.")
                break

            _stop.wait(POLL_SEC)

    except KeyboardInterrupt:
        log("Ctrl-C reçu — arrêt propre : plus rien ne démarre, on laisse finir.")
        arreter_services()
        try:
            while _ticks_en_vol():
                time.sleep(0.5)
        except KeyboardInterrupt:
            log("second Ctrl-C — on n'attend plus (les ticks en vol restent orphelins, "
                "l'état sur disque reste intact).")
            code_retour = 130
    finally:
        _stop.set()
        if not dry:
            clear_lock()
        log("tbot factory arrêtée. Plus rien ne tourne — c'est la règle d'or.")
    return code_retour


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="tbot factory — la console 24/7 TradingBot. Si elle ne tourne pas, rien ne se passe.")
    ap.add_argument("--once", action="store_true", help="un seul cycle puis sortie (sonde)")
    ap.add_argument("--dry-run", action="store_true", help="montre ce qui serait lancé, n'exécute rien")
    a = ap.parse_args(argv)
    return run(dry=a.dry_run, once=a.once)


if __name__ == "__main__":
    raise SystemExit(main())
