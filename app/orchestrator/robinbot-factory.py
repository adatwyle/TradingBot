#!/usr/bin/env python3
"""
robinbot-factory.py — LE SUPERVISEUR CONSOLE DE ROBINBOT
========================================================

RÈGLE D'OR : si cette console ne tourne pas, RIEN ne se passe.

Il n'y a plus de tâche planifiée Windows (supprimées le 2026-08-17, décision
Adrian). Ce fichier les remplace, et le remplacement est VOULU différent : une
tâche planifiée est invisible, tourne sans qu'on la voie, échoue sans qu'on le
sache, et survit à l'oubli de celui qui l'a posée. Une console qu'on démarre à
la main est un interrupteur physique : on la voit vivre, et quand elle est
fermée le système est ARRÊTÉ — pas « peut-être en train de tourner quelque part ».

CE QU'EST UN WORKER : UN TICK, PAS UN AGENT VIVANT
--------------------------------------------------
La factory lance un processus NEUF et ÉPHÉMÈRE, redirige sa sortie vers un log,
et l'oublie. Le processus lit l'état sur disque, produit, écrit, sort. Un worker
« sorti » est le cas NORMAL, pas une panne. La seule question de vivacité est :
*la factory tourne-t-elle, et des ticks partent-ils ?*

L'ÉTAT VIT DANS LES FICHIERS, JAMAIS DANS UN PROCESSUS
-------------------------------------------------------
Ici l'état, ce sont les journaux scellés `C:/db/tradingBot/<étude>/journal.csv` et
`status.json` — append-only, chaînés par hachage. Conséquence directe : un tick
tué (timeout, Ctrl-C, coupure de courant) laisse l'état exactement où il est, et
le tick suivant reprend. C'est ce qui autorise la factory à être brutale avec un
tick bloqué : elle ne peut rien corrompre qui ne soit déjà protégé en amont.

CHAUD vs FROID — CE QUI SE CHANGE SANS REDÉMARRER
--------------------------------------------------
  À CHAUD (relu à CHAQUE cycle, effet au tick suivant, aucun redémarrage) :
      le PANNEAU DE CONTRÔLE `C:/db/tradingBot/robinbot-panel.txt`
      (HORS du dépôt : un panneau = un poste. Gabarit versionné :
       `app/orchestrator/robinbot-panel.exemple.txt`)
        · `worker = on` / `worker = off`
        · cadence par worker : `worker = on:1800` (secondes)

  À FROID (exige de fermer et rouvrir la console) :
      · le CATALOGUE des workers (ajouter/retirer un worker) — voir WORKERS
      · les constantes : TICK_TIMEOUT_SEC, STAGGER_SEC, POLL_SEC, chemins
      · les variables d'environnement RBF_*

  POURQUOI cette frontière : le panneau est ce qu'on touche en situation (« coupe
  le juge IA, il brûle des tokens »), donc il doit agir tout de suite. Le
  catalogue est une décision d'architecture — la relire à chaud voudrait dire
  gérer l'apparition/disparition de workers en vol, pour un besoin qui survient
  trois fois par an. On paie le redémarrage, il coûte deux secondes.

LE PANNEAU EST UNE SURFACE DE CONTRÔLE, PAS UN RECENSEMENT
-----------------------------------------------------------
Un worker ABSENT du panneau est OFF. Jamais l'inverse. Un panneau tronqué, mal
orthographié ou à moitié écrit doit TAIRE l'usine, jamais l'ouvrir en grand :
c'est l'erreur la plus coûteuse qu'un fichier de contrôle puisse commettre.

CODES DE SORTIE DES RUNNERS (contrat commun aux trois études scellées)
-----------------------------------------------------------------------
    0  passage effectué (y compris « rien de neuf »)          → OK
    2  MT5 / données indisponibles                            → INFO, on réessaie
    3  scellé violé (hash des paramètres)                     → INCIDENT, worker OFF
    4  journal altéré (chaîne de hachage cassée)              → INCIDENT, worker OFF
Tout autre code non nul = erreur inattendue (on log, on continue).

3 et 4 ne sont PAS des erreurs de fonctionnement : ce sont des alarmes de
falsification. Relancer le worker après un 3 ne « répare » rien — ça produirait
juste une deuxième trace de la violation. La factory le met donc OFF elle-même
dans le panneau et crie, pour qu'un humain vienne LIRE avant de rallumer.

USAGE
-----
    python app/orchestrator/robinbot-factory.py            # la console
    python app/orchestrator/robinbot-factory.py --once     # un seul cycle (sonde)
    python app/orchestrator/robinbot-factory.py --dry-run  # n'exécute rien, montre
    ou double-clic sur app/orchestrator/run-factory.bat

Arrêt : Ctrl-C, ou créer le fichier `app/orchestrator/.stop`. Les deux sont PROPRES —
on cesse de lancer, on laisse finir ce qui vole, puis on sort.

QUI DOIT LANCER CETTE CONSOLE — et surtout, qui ne doit PAS
------------------------------------------------------------
Elle se lance par DOUBLE-CLIC sur `run-factory.bat`, ou par une commande
DÉTACHÉE. Jamais depuis une session Claude Code : le processus deviendrait
descendant de l'application, et comme la factory ne s'arrête jamais, l'arbre de
processus de l'application ne se libérerait plus.

Constaté le 2026-08-21 : Adrian ne pouvait plus ouvrir Claude Desktop
(« Another program is currently using this file » sur le paquet 1.34493.0.0).
La mise à jour MSIX exigeait l'ancien paquet libre ; la factory, lancée depuis
une session, en était descendante et le retenait. Tuer la factory a débloqué.
Filiation relevée : factory <- claude.exe (runtime) <- claude.exe (paquet
WindowsApps) <- sihost.exe.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows propre (accents)
except Exception:  # noqa: BLE001
    pass


# == CHEMINS ET CONSTANTES (FROID — redémarrage requis) ========================
# Tout est surchargeable par l'environnement RBF_* : c'est ce qui rend ce
# fichier testable (les tests montent une usine jetable dans un tmp_path) sans
# la moindre branche « if TEST » dans le code de production.
HERE = pathlib.Path(__file__).resolve().parent           # app/orchestrator
# `core` vit dans app/ ; ce script est lancé en direct (pas en module), on rend
# donc app/ importable AVANT l'import de core.paths — la résolution de racine
# unique du dépôt (code dans app/, strategies/ et studies/ à la racine projet).
sys.path.insert(0, str(HERE.parent))
from core.paths import panel_file, project_root  # noqa: E402

ROOT = pathlib.Path(os.environ.get("RBF_ROOT") or project_root())

# LE PANNEAU VIT HORS DU DÉPÔT — un panneau, un poste.
#
# Il était versionné jusqu'au 2026-08-21. C'était une bombe à retardement : le
# jour où une seconde machine cloner ait le dépôt, les deux postes partageraient
# la même surface de contrôle, et le `panel_set_off` d'un incident sur l'une
# deviendrait un conflit de merge chez l'autre. Le panneau répond à « qu'est-ce
# que J'ALLUME SUR CE POSTE » — c'est une décision locale, comme les données.
# (Règle reprise de la codeFactory DURIAN §5, qui l'a payée avant nous.)
#
# Le dépôt garde un GABARIT versionné ; la factory en tire le panneau réel au
# premier démarrage sur une machine neuve.
#
# La résolution vit dans core/paths.py (panel_file) : factory, notify et pilot
# doivent résoudre LE MÊME fichier par défaut. Le prototype divergeait ici
# (factory écrivait dans <db>, notify/pilot lisaient à côté du script) — défaut
# documenté, corrigé par la centralisation.
PANEL_FILE = panel_file()
PANEL_TEMPLATE = HERE / "robinbot-panel.exemple.txt"
LOG_DIR    = pathlib.Path(os.environ.get("RBF_LOG_DIR") or (HERE / "logs"))
FACTORY_LOG = LOG_DIR / "factory.log"
LOCK_FILE  = pathlib.Path(os.environ.get("RBF_LOCK") or (HERE / ".robinbot-factory.lock"))
STOP_FILE  = pathlib.Path(os.environ.get("RBF_STOP") or (HERE / ".stop"))

# Le verrou est RETOUCHÉ à chaque cycle. « Périmé » = plus vieux que ce délai,
# donc laissé par une factory morte brutalement (coupure, BSOD) : on peut passer
# outre. Il doit rester nettement supérieur à POLL_SEC, sinon une factory bien
# vivante mais lente à un cycle se ferait doubler par une seconde instance.
LOCK_STALE_SEC = int(os.environ.get("RBF_LOCK_STALE") or 180)

POLL_SEC    = int(os.environ.get("RBF_POLL") or 30)      # rythme du superviseur
STAGGER_SEC = int(os.environ.get("RBF_STAGGER") or 5)    # délai entre 2 départs
# Plafond par tick. Il protège d'un tick MORT (MT5 qui ne répond jamais, juge IA
# parti en boucle), pas d'un tick lent. 20 min : un pas de mesure prend quelques
# secondes, un pas avec juge IA quelques minutes ; au-delà, quelque chose pend.
TICK_TIMEOUT_SEC = int(os.environ.get("RBF_TIMEOUT") or 1200)
# Un service (serveur Flask) qui meurt n'est pas relancé instantanément : sinon
# un serveur qui crashe au démarrage (port déjà pris) fait tourner la factory en
# boucle de relance à plein régime. On respire.
SERVICE_RESTART_BACKOFF_SEC = int(os.environ.get("RBF_SERVICE_BACKOFF") or 60)
# Rotation naïve du journal de la factory : au-delà, on décale vers .1 et on
# repart. Pas de logrotate, pas de dépendance — un seul fichier de secours suffit
# pour une console qu'on lit en direct.
FACTORY_LOG_MAX_BYTES = 2 * 1024 * 1024
# La console n'imprime le tableau d'état QUE s'il s'est passé quelque chose,
# plus un battement périodique. Sinon, à 30 s de cycle, elle noierait l'incident
# du jour sous 2880 tableaux identiques.
HEARTBEAT_SEC = int(os.environ.get("RBF_HEARTBEAT") or 300)

CLAUDE_BIN = os.environ.get("RBF_CLAUDE_BIN") or "claude"
CLAUDE_MAX_TURNS = int(os.environ.get("RBF_MAX_TURNS") or 40)
PYTHON = sys.executable or "python"


# == CATALOGUE DES WORKERS (FROID — redémarrage requis) ========================
# (nom, cwd, spec, intervalle_sec, nature)
#
#   nature "tick"    : processus éphémère. On lance, on log, on oublie. Sortir
#                      est NORMAL. Relancé toutes les `intervalle_sec`.
#   nature "service" : processus PERSISTANT (le serveur Flask). Lancé une fois,
#                      relancé seulement s'il meurt. `intervalle_sec` sert alors
#                      de délai minimal entre deux relances.
#
#   spec "py:<chemin> [args]"  : commande Python pure, ZÉRO token.
#         Le chemin est résolu depuis la racine du dépôt. S'il désigne un module
#         d'un vrai package (chaîne de `__init__.py` complète), on lance en
#         `-m paquet.module` — la forme qu'utilisaient les .bat des études, et la
#         seule qui garantisse les imports absolus `from core...` / `from
#         studies...`. Sinon on lance le script tel quel.
#   spec "claude:<prompt>"     : tick IA headless (`claude -p ... --output-format
#         json`). Aucun n'est actif aujourd'hui — voir README « ajouter un
#         worker » : la mécanique est gréée et dormante, une ligne suffit.
#
# CADENCES : les trois runners sont SCELLÉS et IDEMPOTENTS (hash des paramètres,
# journal à chaîne de hachage, sans effet si aucune barre nouvelle). Les relancer
# plus souvent que nécessaire est sans effet et sans risque — vérifié dans
# studies/gold_forward/run_forward.py. On prend donc 1 h pour tout le monde, y
# compris les études D1 : un passage horaire sur une bougie quotidienne ne fait
# rien 23 fois sur 24, et fait le travail dès que la bougie est là — sans
# dépendre d'une heure de rendez-vous que MT5 pourrait manquer.
# NOTE MIGRATION (E2) : les workers d'études référencent `studies/*/run_*.py`
# à la RACINE PROJET — les études scellées ne sont PAS encore migrées (elles
# tournent dans le prototype jusqu'à E6). Les workers restent DÉCLARABLES mais
# INERTES : le gabarit du panneau les livre `off`, et le panneau fail-closed
# couvre le reste (absent = OFF). Les rallumer sans les fichiers d'études ne
# produit qu'un tick en sortie 2 (ressource indisponible), jamais un incident.
WORKERS: list[tuple[str, pathlib.Path, str, int, str]] = [
    ("gold_forward",  ROOT, "py:studies/gold_forward/run_forward.py", 3600, "tick"),
    ("s13_forward",   ROOT, "py:studies/s13_forward/run_forward.py",  3600, "tick"),
    ("macd_ai_paper", ROOT, "py:studies/macd_ai_paper/run_paper.py",  3600, "tick"),
    # s14 : UN worker séquentiel (collecte PUIS jugement). Deux workers sur le
    # même journal chaîné produiraient un entrelacement, donc une fausse alarme
    # d'altération irréparable — le protocole l'interdit explicitement.
    # Cadence 1800 s : le jugement n'a lieu que s'il existe des news fraîches
    # non jugées (sinon no-op silencieux, zéro token).
    ("s14_sentiment", ROOT, "py:studies/s14_sentiment/run_sentiment.py", 1800, "tick"),
    # alexg_paper : essai a blanc fxalexg + juge IA headless sur 26 paires H1
    # (studies/alexg_paper/PROTOCOL.md, scelle 2026-08-22). Cadence horaire =
    # la barre H1. Le passage coute ~15 s et ne rappelle JAMAIS le juge sur un
    # signal deja traite (curseur par paire) : un tick sans barre neuve est
    # gratuit en tokens comme en temps.
    ("alexg_paper",   ROOT, "py:studies/alexg_paper/run_paper.py", 3600, "tick"),
    # Porte ENTRANTE : chaque message Telegram d'Adrian déclenche une session
    # Claude headless en lecture seule. 60 s = le délai de réponse ressenti
    # depuis un téléphone ; le tick ne coûte rien quand la boîte est vide.
    ("gateway",       ROOT, "py:app/orchestrator/robinbot-gateway.py", 30, "tick"),
    # Le pilote regarde chaque heure mais ne PARLE qu'une fois par jour, et
    # seulement s'il s'est passé quelque chose : la veille est en Python pur,
    # la session Claude n'est appelée qu'une fois la matière constatée.
    ("pilot",         ROOT, "py:app/orchestrator/robinbot-pilot.py", 3600, "tick"),
    # Le PORTIER trie les idees neuves avant qu'elles ne deviennent des
    # etudes : deja testee ? assez de donnees ? quel effectif ? Il annote,
    # Adrian tranche. ENTREE vide = no-op gratuit, le cas normal.
    ("portier",       ROOT, "py:app/orchestrator/robinbot-portier.py", 3600, "tick"),
    # Le MESUREUR fait avancer UN mandat et s'arrete a toute porte qui
    # demande une decision. Pas de mandat = il dort et ne coute rien.
    ("mesureur",      ROOT, "py:app/orchestrator/robinbot-mesureur.py", 7200, "tick"),
    ("notify",        ROOT, "py:app/orchestrator/robinbot-notify.py",      300, "tick"),
    ("supervision",   ROOT, "py:app/server/app.py",  SERVICE_RESTART_BACKOFF_SEC, "service"),
]

# SEAM DE TEST (et uniquement ça) : un catalogue JSON injecté par l'environnement
# remplace celui ci-dessus. Les tests montent ainsi des workers factices sans
# jamais lancer les vrais runners scellés. Lu à l'import → reste une donnée
# FROIDE, cohérent avec la règle chaud/froid.
_CAT_ENV = os.environ.get("RBF_CATALOGUE")
if _CAT_ENV:
    WORKERS = [(w["name"], pathlib.Path(w.get("cwd") or ROOT), w["spec"],
                int(w.get("interval", 60)), w.get("kind", "tick"))
               for w in json.loads(_CAT_ENV)]

WORKER_NAMES = [w[0] for w in WORKERS]
WORKER_BY_NAME = {w[0]: w for w in WORKERS}


# == ÉTAT INTERNE (vivant, jamais la source de vérité) =========================
# Ce dictionnaire sert à AFFICHER, pas à décider : la vérité est sur disque
# (journaux des études, panneau, verrou). Perdre cet état au redémarrage ne
# perd rien — c'est le principe même de l'architecture.
_running: dict[str, subprocess.Popen] = {}
_started_at: dict[str, float] = {}
_last_run: dict[str, float] = {}          # worker -> t du dernier LANCEMENT
_last_result: dict[str, dict] = {}        # worker -> {code, label, duree, fin}
_stop = threading.Event()
# Services coupés VOLONTAIREMENT par l'arrêt propre : leur mort est le
# résultat attendu, pas un incident. Sans cette distinction, la console crie
# « ATTENTION, le service s'est ARRÊTÉ » juste après l'avoir arrêté elle-même
# — et une alerte qui se déclenche sur une action délibérée apprend à ignorer
# les alertes.
_services_coupes: set = set()
_events = threading.Event()               # « il s'est passé quelque chose »
_lock_console = threading.Lock()

EXIT_LABELS = {
    0: "OK",
    # Le 2 dit « la ressource extérieure dont j'ai besoin n'est pas là » — MT5
    # pour les études, mais aussi la clé Finnhub, le token du bot, Telegram.
    # Nommer MT5 ici envoyait chercher au mauvais endroit : le worker, lui,
    # écrit la vraie cause dans son propre log.
    2: "ressource externe indisponible (réessai au prochain tick)",
    3: "SCELLÉ VIOLÉ",
    4: "JOURNAL ALTÉRÉ",
}
INCIDENT_CODES = (3, 4)     # les deux alarmes de falsification


# == JOURNAL ET CONSOLE ========================================================
def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _rotate_if_needed() -> None:
    """Rotation naïve : un seul fichier de secours. POURQUOI si simple — ce log
    se lit en direct pendant un incident ; une politique de rotation savante
    déplacerait la ligne qu'on cherche dans un fichier qu'on n'a pas ouvert."""
    try:
        if FACTORY_LOG.exists() and FACTORY_LOG.stat().st_size > FACTORY_LOG_MAX_BYTES:
            backup = FACTORY_LOG.with_suffix(".log.1")
            backup.unlink(missing_ok=True)
            FACTORY_LOG.rename(backup)
    except OSError:
        pass        # un log qui rate ne doit JAMAIS tuer la boucle


def log(msg: str) -> None:
    """Écrit à l'écran ET sur disque. Le doublage se fait ICI et non par un
    `| tee` côté .bat : un pipe fait perdre le tty, et une console redirigée
    perd son intérêt de console."""
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
    """True si une AUTRE factory semble vivante sur ce poste.

    Deux factories = deux ticks simultanés sur le même journal scellé. Les
    journaux résisteraient (append-only chaîné), mais le second tick verrait un
    curseur déplacé sous ses pieds et sortirait en 4 — on fabriquerait de fausses
    alarmes de falsification. Une seule usine par poste, point."""
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
# PANNEAU DE CONTRÔLE RobinBot — relu à CHAQUE cycle de la factory
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
# En revanche AJOUTER ou RETIRER un worker se fait dans le CATALOGUE
# (app/orchestrator/robinbot-factory.py, section WORKERS) et exige un redémarrage.
# ═══════════════════════════════════════════════════════════════════════════
"""


def ensure_panel() -> None:
    """Crée le panneau s'il manque, avec TOUS les workers du catalogue sur ON.

    POURQUOI ON à la création et OFF à l'absence de ligne : ce sont deux
    situations différentes. Pas de fichier du tout = première utilisation, on
    fournit un panneau complet et lisible. Fichier présent mais sans la ligne =
    quelqu'un l'a retirée, et son intention est de ne pas faire tourner ce
    worker."""
    if PANEL_FILE.exists():
        return
    lignes = [PANEL_HEADER]
    for name, _cwd, _spec, interval, kind in WORKERS:
        nature = "service persistant" if kind == "service" else f"tick toutes les {interval}s"
        lignes.append(f"{name} = on          # {nature}")
    try:
        PANEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Machine neuve : on part du gabarit versionne s'il existe, pour
        # que le panneau local naisse deja renseigne.
        if PANEL_TEMPLATE.exists():
            PANEL_FILE.write_text(
                PANEL_TEMPLATE.read_text(encoding='utf-8-sig'),
                encoding='utf-8')
            log(f'panneau cree depuis le gabarit : {PANEL_FILE}')
            return
        PANEL_FILE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
        log(f"panneau créé : {PANEL_FILE} (tous les workers ON)")
    except OSError as e:  # noqa: BLE001
        log(f"ATTENTION : création du panneau impossible ({e!r}) — tous les workers restent OFF.")


_panel_cache: dict[str, tuple[bool, int | None]] = {}


def read_panel() -> dict[str, tuple[bool, int | None]]:
    """-> {worker: (allumé, cadence forcée ou None)}.

    Tolérant par construction : une ligne illisible est ignorée, un fichier
    illisible rend le DERNIER panneau valide connu (et pas un panneau vide, qui
    éteindrait l'usine sur un simple verrou de fichier transitoire pendant qu'on
    l'édite au bloc-notes)."""
    global _panel_cache
    if not PANEL_FILE.exists():
        # Absent alors qu'on l'a créé au démarrage = quelqu'un l'a supprimé
        # en vol. FAIL-CLOSED : on éteint tout plutôt que de deviner.
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
    """Éteint un worker DANS le panneau, en place, en gardant le reste intact.

    C'est la factory qui écrit dans la surface de contrôle de l'humain : elle ne
    le fait QUE sur incident (code 3/4), et elle laisse la trace de la raison en
    commentaire pour que celui qui rallume sache ce qu'il rallume."""
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


# == CONSTRUCTION DES COMMANDES ================================================
def _dotted_module(rel: str) -> str | None:
    """'studies/gold_forward/run_forward.py' -> 'studies.gold_forward.run_forward'
    si et seulement si TOUS les dossiers traversés sont de vrais packages.

    POURQUOI ce détour : les runners scellés font `from core.data.source import
    ...`. Lancés en `-m` depuis la racine, l'import fonctionne (c'est la forme
    des .bat d'origine). Lancés comme simple script, ils s'en sortent aussi (ils
    insèrent ROOT dans sys.path eux-mêmes), mais on reste sur la forme éprouvée
    quand elle est disponible — on ne change pas la façon d'appeler un scellé."""
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

      py:<chemin> [args]   commande Python pure — ZÉRO token, c'est le cas normal
      claude:<prompt>      tick IA headless — coûte des tokens, donc explicite
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
        prompt = spec[7:].strip()
        # Sous Windows `claude` est un shim npm .cmd, pas un .exe : CreateProcess
        # ne résout pas un ["claude", ...] nu. On passe par cmd.exe qui applique
        # PATHEXT. (Leçon reprise de la codeFactory DURIAN — deux heures perdues.)
        return ["cmd", "/c", CLAUDE_BIN, "-p", prompt,
                "--output-format", "json",
                "--max-turns", str(CLAUDE_MAX_TURNS)]

    raise ValueError(f"spec inconnue : {spec!r} (attendu 'py:...' ou 'claude:...')")


# == LANCEMENT ET RÉCOLTE ======================================================
def _tick_log_path(name: str) -> pathlib.Path:
    d = LOG_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"


def launch(name: str, dry: bool = False) -> None:
    """Lance UN tick. Ne bloque pas : la récolte se fait dans un thread."""
    _name, cwd, spec, _interval, kind = WORKER_BY_NAME[name]
    try:
        cmd = build_cmd(spec)
    except ValueError as e:  # noqa: BLE001
        log(f"ERREUR [{name}] : {e} — worker ignoré (corrige le CATALOGUE, à froid).")
        return

    if dry:
        log(f"DRY-RUN [{name}] (cwd={cwd}) :: {' '.join(cmd)}")
        _last_run[name] = time.time()
        return

    logf = _tick_log_path(name)
    try:
        with open(logf, "a", encoding="utf-8") as lf:
            lf.write(f"===== {_ts()} TICK {name} :: {' '.join(cmd)} =====\n")
            lf.flush()
            proc = subprocess.Popen(
                cmd, cwd=str(cwd),
                stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except FileNotFoundError as e:  # noqa: BLE001
        log(f"ERREUR [{name}] : exécutable introuvable ({e}).")
        return
    except Exception as e:  # noqa: BLE001 — un lancement raté ne tue pas l'usine
        log(f"ERREUR [{name}] lancement impossible : {e!r}")
        return

    _running[name] = proc
    _started_at[name] = time.time()
    _last_run[name] = time.time()
    log(f"lance [{name}] {'(service)' if kind == 'service' else ''} → {logf.name}")
    _events.set()
    threading.Thread(target=_reap, args=(name, proc, kind, logf),
                     daemon=True).start()



def _resume_du_worker(logf: pathlib.Path) -> str:
    """La dernière ligne parlante qu'a écrite le worker, pour la remonter dans
    la console.

    POURQUOI : la factory ne voit d'un tick que son code de sortie et sa durée.
    Or certains workers font le vrai travail à l'INTÉRIEUR d'eux-mêmes — le
    gateway et le pilote lancent une session Claude headless que le tableau
    d'état ne montre pas. Sans ce résumé, une réflexion de quarante secondes et
    une boîte vide se ressemblent : deux lignes « OK », l'une longue, l'autre
    courte. On remonte donc ce que le worker a dit de lui-même."""
    try:
        lignes = [l.strip() for l in logf.read_text(encoding="utf-8",
                                                    errors="replace").splitlines()]
    except OSError:
        return ""
    for ligne in reversed(lignes):
        if not ligne or ligne.startswith("====="):
            continue
        # On retire l'horodatage du worker : la console met déjà le sien.
        if ligne.startswith("[") and "] " in ligne:
            ligne = ligne.split("] ", 1)[1]
        return ligne[:150]
    return ""


def _reap(name: str, proc: subprocess.Popen, kind: str,
          logf: Optional[pathlib.Path] = None) -> None:
    """Attend la fin du tick, traduit son code de sortie, agit sur incident."""
    debut = _started_at.get(name, time.time())
    # Un SERVICE n'a pas de plafond : il est censé vivre. Un TICK, si.
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
            # PAS une erreur : MT5 fermé le week-end (nominal 2j/7), une clé
            # pas encore déposée, Telegram injoignable une minute. La cause
            # précise est dans le log DU WORKER — on ne la devine pas ici.
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
                f"À FAIRE, dans l'ordre : lire {LOG_DIR / name}, puis le PROTOCOL.md de "
                f"l'étude (§ intégrité), puis `git log` sur params.json.\n"
                f"NE PAS 'réparer' params.json : toute modification invalide le test."
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
        # (python.exe, ou claude.exe sous un cmd /c), qui continuerait à écrire
        # pendant que la place se libère — et le cycle suivant lancerait un
        # SECOND tick concurrent sur le même journal.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)
        duree = time.time() - debut
        _last_result[name] = {"code": "TIMEOUT", "label": f"tué après {TICK_TIMEOUT_SEC}s",
                              "duree": duree, "fin": time.time()}
        log(f"TIMEOUT [{name}] arbre tué après {TICK_TIMEOUT_SEC}s. "
            f"L'état sur disque est intact (append-only) — le prochain tick reprend.")
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
    out = [f"{'WORKER':<14} {'ÉTAT':<10} {'DERNIER TICK':<14} {'RÉSULTAT':<34} PROCHAIN"]
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

        out.append(f"{name:<14} {etat:<10} {dernier:<14} {resultat:<34} {prochain}")
    return out


def print_status(panel, now: float) -> None:
    for ligne in status_lines(panel, now):
        log("  " + ligne)


def print_header(dry: bool) -> None:
    log("=" * 78)
    log(f"RobinBot factory — LE superviseur. Si cette console s'arrête, RIEN ne tourne."
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
        log(f"  {name:<14} {nature:<20} {spec}   (cwd={cwd})")
    log("-" * 78)


# == LE CYCLE ==================================================================
def due(name: str, panel: dict, now: float) -> bool:
    """Ce worker doit-il partir MAINTENANT ?

    Trois refus, dans l'ordre : déjà en vol (jamais deux ticks du même worker sur
    le même journal), éteint au panneau (y compris par absence de ligne), pas
    encore l'heure. Le dernier point est ce qui rend deux cycles rapprochés
    inoffensifs : c'est l'idempotence côté factory, en plus de celle des runners."""
    if name in _running:
        return False
    on, cadence = panel.get(name, (False, None))
    if not on:
        return False
    _n, _cwd, _spec, interval, kind = WORKER_BY_NAME[name]
    if kind == "service":
        # Un service absent de _running est soit jamais lancé, soit mort.
        # Le backoff évite la boucle de relance à plein régime.
        return (now - _last_run.get(name, 0.0)) >= (cadence or interval)
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
            # ÉCHELONNEMENT : trois runners qui attaquent MT5 à la même
            # milliseconde au réveil de la factory, c'est trois chargements de
            # barres concurrents sur un terminal qui n'aime pas ça. On respire
            # entre deux départs — le coût est nul, la cadence est horaire.
            _stop.wait(STAGGER_SEC)
        launch(name, dry=dry)
        lances.append(name)
    return lances


def stop_requested() -> bool:
    return STOP_FILE.exists()


def _ticks_en_vol() -> list[str]:
    """Les workers ÉPHÉMÈRES encore en cours. Un service n'y figure jamais :
    il ne finit pas, donc l'attendre serait attendre pour toujours."""
    return [n for n in list(_running) if WORKER_BY_NAME[n][4] != "service"]


def arreter_services() -> None:
    """Coupe les services persistants (le serveur de supervision).

    POURQUOI les tuer alors qu'on laisse finir les ticks : un tick MESURE —
    l'interrompre gaspille un appel MT5 et, pour un tick à juge IA, des tokens
    déjà payés. Un service ne mesure rien, il SERT ; le couper ne perd que la
    page de quelqu'un qui la rechargera. Et la règle d'or exige qu'après la
    fermeture de cette console, plus rien ne tourne — un serveur orphelin
    tiendrait son port et ferait échouer le prochain démarrage."""
    for name in list(_running):
        if WORKER_BY_NAME[name][4] != "service":
            continue
        proc = _running.get(name)
        if proc is None:
            continue
        log(f"arrêt du service [{name}] (pid {proc.pid}) — il ne finit jamais de "
            f"lui-même.")
        _services_coupes.add(name)
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)


def run(dry: bool = False, once: bool = False) -> int:
    if not dry and lock_is_fresh():
        detenteur = LOCK_FILE.read_text(encoding="utf-8").strip() if LOCK_FILE.exists() else "?"
        log(f"REFUS DE DÉMARRER : une autre factory semble vivante "
            f"({LOCK_FILE.name}, {detenteur}, touché il y a moins de {LOCK_STALE_SEC}s).\n"
            f"        Deux usines = deux ticks concurrents sur le même journal scellé, "
            f"donc de fausses alarmes d'altération.\n"
            f"        Si tu es SÛR qu'aucune ne tourne : supprime {LOCK_FILE} et relance.")
        return 1

    if stop_requested():
        # Un `.stop` oublié est le piège classique : la console démarre, ne lance
        # rien, et on cherche pourquoi pendant dix minutes. On le dit tout haut.
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
            # (Le Ctrl-C, lui, remonte en exception et se traite dans le except.)
            if not drainage and stop_requested():
                drainage = STOP_FILE.name
            if drainage:
                # Un SERVICE ne finit jamais — c'est sa définition. L'attendre
                # ferait de l'arrêt propre une attente infinie (constaté le
                # 2026-08-18 : le `.stop` restait bloqué sur `supervision`).
                # On le coupe donc : « si la console s'arrête, RIEN ne tourne »
                # vaut d'abord pour lui. Les TICKS, eux, sont laissés finir —
                # ils mesurent, et une mesure interrompue est un appel MT5
                # gaspillé.
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

            # La console n'imprime le tableau que s'il s'est passé quelque chose,
            # plus un battement périodique : sinon l'incident du jour se noierait
            # sous des centaines de tableaux identiques.
            if lances or _events.is_set() or (time.time() - dernier_battement) > HEARTBEAT_SEC:
                _events.clear()
                print_status(panel, time.time())
                dernier_battement = time.time()

            if once:
                # On n'attend que les TICKS (cf. _ticks_en_vol) : un service
                # persistant ne finit jamais, l'attendre ferait de `--once` une
                # boucle infinie — exactement ce que la sonde doit éviter.
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
        # Ctrl-C = arrêt PROPRE, pas un massacre : on laisse finir ce qui vole.
        # Tuer un tick en vol ne corromprait rien (append-only), mais gaspillerait
        # un appel MT5 — et pour un tick à juge IA, des tokens déjà payés.
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
        log("factory arrêtée. Plus rien ne tourne — c'est la règle d'or.")
    return code_retour


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Superviseur console RobinBot — si elle ne tourne pas, rien ne se passe.")
    ap.add_argument("--once", action="store_true", help="un seul cycle puis sortie (sonde)")
    ap.add_argument("--dry-run", action="store_true", help="montre ce qui serait lancé, n'exécute rien")
    a = ap.parse_args(argv)
    return run(dry=a.dry_run, once=a.once)


if __name__ == "__main__":
    raise SystemExit(main())
