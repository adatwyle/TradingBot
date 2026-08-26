#!/usr/bin/env python3
"""
robinbot-pilot.py — L'ŒIL QUI RAISONNE
=======================================

Une fois par jour, une session Claude Code headless LIT l'usine et en fait
une lecture — pas un tableau de chiffres, une interprétation : ce qui a bougé,
ce que ça vaut, ce qui mérite l'attention d'Adrian.

CE QUI LE DISTINGUE DU NOTIFIER
--------------------------------
Le notifier (`robinbot-notify.py`) est mécanique et gratuit : il recopie des
événements. Le pilote pense, donc il coûte des tokens. Les deux coexistent
parce que leurs pannes sont indépendantes : si le CLI Claude est indisponible,
les chiffres continuent d'arriver.

IL NE PARLE QUE S'IL A QUELQUE CHOSE À DIRE
--------------------------------------------
Un pilote qui commente quotidiennement une usine au repos écrirait « rien de
neuf » trois cents fois par an, en payant chaque phrase. Ce script vérifie
donc D'ABORD, en Python et sans le moindre token, s'il s'est passé quelque
chose depuis sa dernière parole : trades, incidents, franchissement d'un
palier de collecte, worker éteint, panne de mesure. Sans événement, il sort
en 0 sans avoir rien appelé. C'est la même discipline que les runners scellés
(« sans effet si aucune barre nouvelle »), appliquée à la dépense.

LECTURE SEULE, COMME LE RESTE
------------------------------
`--allowedTools Read,Grep,Glob`. Le pilote observe et écrit à Adrian ; il ne
touche ni aux journaux scellés, ni au panneau, ni à un ordre. C'est Python qui
envoie le message — Claude ne dispose d'aucun moyen d'émettre quoi que ce soit
par lui-même.

CODES DE SORTIE (contrat commun de la factory)
-----------------------------------------------
    0  passage effectué (y compris « rien à dire », le cas le plus fréquent)
    2  configuration/token absents, Telegram injoignable, ou session headless
       indisponible — on réessaiera, l'usine n'en souffre pas
    1  erreur inattendue
Jamais 3/4 : aucun scellé n'est touché.

USAGE
-----
    python app/orchestrator/robinbot-pilot.py             # un passage
    python app/orchestrator/robinbot-pilot.py --force     # parle même sans événement
    python app/orchestrator/robinbot-pilot.py --dry-run   # montre, n'appelle rien
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from datetime import datetime

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.paths import db_dir, panel_file, project_root  # noqa: E402

ROOT = pathlib.Path(os.environ.get("RBF_ROOT") or project_root())
PILOT_DIR = pathlib.Path(os.environ.get("ROBINBOT_PILOT_DIR")
                         or (db_dir() / "pilot"))
STATE_FILE = PILOT_DIR / "state.json"
# Le pilote emprunte le canal du notifier : même destinataire, même bot.
NOTIFY_DIR = pathlib.Path(os.environ.get("ROBINBOT_NOTIFY_DIR")
                          or (db_dir() / "notifier"))
TELEGRAM_ENV = pathlib.Path(os.environ.get("ROBINBOT_TELEGRAM_ENV")
                            or (pathlib.Path.home() / ".claude" / "channels"
                                / "telegram" / ".env"))
# Même résolution que la factory (core.paths.panel_file) : le pilote lit la
# surface de contrôle que la factory écrit. Le prototype divergeait ici
# (lecture à côté du script) — défaut corrigé par la centralisation.
PANEL_FILE = panel_file()

ETUDES = [
    ("gold_forward", os.environ.get("GOLD_FORWARD_DIR") or str(db_dir() / "gold_forward")),
    ("s13_forward", os.environ.get("S13_FORWARD_DIR") or str(db_dir() / "s13_forward")),
    ("macd_ai_paper", os.environ.get("MACD_AI_PAPER_DIR") or str(db_dir() / "macd_ai_paper")),
    ("s14_sentiment", os.environ.get("S14_SENTIMENT_DIR") or str(db_dir() / "s14_sentiment")),
]

API = "https://api.telegram.org/bot{token}/sendMessage"
HTTP_TIMEOUT = 15
CLAUDE_TIMEOUT_S = int(os.environ.get("ROBINBOT_PILOT_TIMEOUT") or 420)
CLAUDE_MAX_TURNS = int(os.environ.get("ROBINBOT_PILOT_MAX_TURNS") or 30)
ALLOWED_TOOLS = "Read,Grep,Glob"
HEURE_PAROLE = int(os.environ.get("ROBINBOT_PILOT_HOUR") or 8)   # locale
TELEGRAM_LIMIT = 4000
# Paliers de collecte s14 : on ne parle pas à chaque news, mais franchir un
# palier est une nouvelle (F1 exige 150 verdicts).
PALIERS_VERDICTS = (10, 50, 100, 150, 300, 600)

CONSIGNE = (
    "Tu es le pilote de RobinBot, l'usine de forward-tests scellés du dépôt "
    "TradingBot. Tu écris à Adrian par Telegram, une fois par jour au "
    "plus. Lis l'état réel dans les fichiers (journaux et status.json sous "
    "C:/db/tradingBot/, app/orchestrator/logs/factory.log, TODO.md, les "
    "PROTOCOL.md des "
    "études) et rends une LECTURE, pas un tableau : ce qui a changé, ce que "
    "ça vaut, ce qui mérite son attention. Sois bref (10 lignes maximum, "
    "phrases complètes, pas de markdown lourd — c'est un écran de téléphone). "
    "Discipline du projet : aucun hit-rate ni verdict avant l'effectif "
    "pré-enregistré du protocole concerné ; quelques trades ne prouvent rien "
    "et tu le dis plutôt que de féliciter ; un incident (sortie 3 ou 4) passe "
    "en première ligne. Tu es en lecture seule : si une action s'impose, tu "
    "dis laquelle et à qui elle revient, tu ne la fais pas."
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
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, STATE_FILE)


# == LA VEILLE (Python pur, ZÉRO token) ========================================
def _json(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _n_lignes_journal(p: pathlib.Path) -> int:
    try:
        with open(p, newline="", encoding="utf-8") as f:
            return max(0, sum(1 for _ in csv.reader(f)) - 1)
    except OSError:
        return 0


def observer() -> dict:
    """Photo chiffrée de l'usine — la matière de la comparaison, pas du
    commentaire."""
    photo: dict = {"etudes": {}, "autooff": [], "workers_off": []}
    for nom, ddir in ETUDES:
        d = pathlib.Path(ddir)
        st = _json(d / "status.json")
        judges = st.get("judges") or {}
        photo["etudes"][nom] = {
            "existe": (d / "status.json").exists(),
            "lignes": _n_lignes_journal(d / "journal.csv"),
            "n_trades": st.get("n_closed_total", 0),
            "n_verdicts": sum(int(j.get("n_verdicts_total", 0))
                              for j in judges.values()) if judges else 0,
            "mesure": st.get("generated_at_utc") or "",
        }
    try:
        for brute in PANEL_FILE.read_text(encoding="utf-8-sig").splitlines():
            if "AUTO-OFF" in brute:
                photo["autooff"].append(brute.strip())
            code = brute.split("#", 1)[0]
            if "=" in code:
                nom, val = code.split("=", 1)
                if val.strip().lower() not in ("on", "true", "1", "yes", "oui") \
                        and nom.strip():
                    photo["workers_off"].append(nom.strip())
    except OSError:
        pass
    return photo


def _palier(n: int) -> int:
    """Le plus haut palier franchi — comparer les paliers plutôt que les
    compteurs évite de parler à chaque news collectée."""
    return max([p for p in PALIERS_VERDICTS if n >= p], default=0)


def evenements(avant: dict, apres: dict) -> list[str]:
    """Ce qui mérite qu'on dépense des tokens. Vide = on se tait."""
    faits: list[str] = []
    va = (avant or {}).get("etudes", {})
    for nom, a in apres["etudes"].items():
        b = va.get(nom, {})
        if not b:
            if a["existe"]:
                faits.append(f"{nom} : première mesure déposée")
            continue
        d_trades = int(a["n_trades"]) - int(b.get("n_trades", 0))
        if d_trades:
            faits.append(f"{nom} : {d_trades:+d} trade(s) clos "
                         f"(total {a['n_trades']})")
        if _palier(int(a["n_verdicts"])) > _palier(int(b.get("n_verdicts", 0))):
            faits.append(f"{nom} : palier de {_palier(int(a['n_verdicts']))} "
                         f"verdicts franchi")
        if b.get("mesure") and a["mesure"] == b["mesure"]:
            faits.append(f"{nom} : aucune mesure nouvelle depuis la dernière "
                         f"lecture — vérifier que le worker tourne")

    nouveaux = [l for l in apres["autooff"] if l not in (avant or {}).get("autooff", [])]
    if nouveaux:
        faits.insert(0, f"INCIDENT : {len(nouveaux)} worker(s) mis AUTO-OFF")
    off_neufs = [w for w in apres["workers_off"]
                 if w not in (avant or {}).get("workers_off", [])]
    if off_neufs:
        faits.append(f"worker(s) éteints au panneau : {', '.join(off_neufs)}")
    return faits


# == TELEGRAM ET SESSION HEADLESS ==============================================
def load_token() -> str:
    tok = os.environ.get("ROBINBOT_TELEGRAM_TOKEN", "").strip()
    if tok:
        return tok
    try:
        for ligne in TELEGRAM_ENV.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("TELEGRAM_BOT_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def send(token: str, chat_id: str, text: str) -> bool:
    for i in range(0, max(1, len(text)), TELEGRAM_LIMIT):
        try:
            r = requests.post(API.format(token=token),
                              json={"chat_id": chat_id,
                                    "text": text[i:i + TELEGRAM_LIMIT]},
                              timeout=HTTP_TIMEOUT)
        except Exception as e:  # noqa: BLE001 — le repr porterait le token
            err(f"Telegram injoignable : {type(e).__name__}")
            return False
        if not r.ok:
            err(f"Telegram a refusé l'envoi : HTTP {r.status_code}")
            return False
    return True


def _clean_env() -> dict:
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("CLAUDE_", "CLAUDECODE")) or k == "ANTHROPIC_BASE_URL":
            env.pop(k, None)
    return env


def analyser(faits: list[str]) -> str | None:
    """La session headless : elle reçoit les faits repérés et rend la lecture."""
    exe = shutil.which("claude")
    if exe is None:
        err("claude CLI introuvable dans le PATH")
        return None
    question = ("Voici ce qui a changé depuis ta dernière lecture :\n- "
                + "\n- ".join(faits)
                + "\n\nVérifie ces faits dans les fichiers, replace-les dans "
                  "l'état des études et de leurs critères d'arrêt, et écris à "
                  "Adrian ta lecture du jour.")
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
        return cp.stdout.strip() or None
    if env.get("is_error"):
        err(f"session headless en erreur : {str(env.get('result'))[:200]}")
        return None
    return str(env.get("result", "")).strip() or None


# == LE PASSAGE ================================================================
def tick(now_local: datetime | None = None, force: bool = False,
         dry: bool = False) -> int:
    now = now_local or datetime.now()
    state = load_state()
    photo = observer()

    # L'heure de parole : une seule fois par jour, et pas la nuit.
    aujourdhui = now.strftime("%Y-%m-%d")
    if not force:
        if state.get("last_spoke_date") == aujourdhui:
            return 0
        if now.hour < HEURE_PAROLE:
            return 0

    # AMORÇAGE : au tout premier passage il n'y a pas de « avant », donc tout
    # paraît nouveau. On pose la photo de référence et on se tait — annoncer
    # « première mesure déposée » pour des études qui tournent depuis des
    # semaines serait une fausse nouvelle. Même principe que l'armement du
    # notifier.
    if "photo" not in state:
        state["photo"] = photo
        state["last_check_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if not dry:
            save_state(state)
        log("amorçage : photo de référence posée, aucune parole")
        return 0

    faits = evenements(state.get("photo") or {}, photo)
    if not faits and not force:
        # Rien ne s'est passé : on met la photo à jour et on se tait. Aucun
        # token dépensé — c'est le cas normal d'une usine qui mesure.
        state["photo"] = photo
        state["last_check_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if not dry:
            save_state(state)
        log("rien de neuf — le pilote se tait (zéro token)")
        return 0

    log(f"{len(faits)} fait(s) à instruire : {' | '.join(faits)[:200]}")
    if dry:
        log("DRY-RUN : session headless non lancée, rien envoyé, rien sauvé")
        return 0

    cfg = _json(NOTIFY_DIR / "config.json")
    token = load_token()
    if not str(cfg.get("chat_id", "")).strip() or not token:
        err("configuration ou token Telegram absents — lecture non envoyée")
        return 2

    log(f"session Claude headless — LANCEMENT (lecture du jour, "
        f"outils {ALLOWED_TOOLS}, plafond {CLAUDE_TIMEOUT_S}s)")
    debut = time.monotonic()
    lecture = analyser(faits)
    duree = time.monotonic() - debut
    log(f"session Claude headless — FIN en {duree:.1f}s "
        f"({len(lecture)} caractères)" if lecture else
        f"session Claude headless — FIN en {duree:.1f}s (AUCUNE RÉPONSE)")
    if lecture is None:
        return 2                     # on retentera : ni photo ni date sauvées
    if not send(token, str(cfg["chat_id"]), "🧭 RobinBot — lecture du jour\n\n"
                + lecture):
        return 2

    state["photo"] = photo
    state["last_spoke_date"] = aujourdhui
    state["last_check_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    save_state(state)
    log("lecture envoyée")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Pilote RobinBot — une lecture raisonnée par jour, quand il y a matière.")
    ap.add_argument("--force", action="store_true",
                    help="parle même sans événement et hors heure de parole")
    ap.add_argument("--dry-run", action="store_true",
                    help="montre les faits repérés, n'appelle ni Claude ni Telegram")
    a = ap.parse_args()
    try:
        return tick(force=a.force, dry=a.dry_run)
    except Exception as e:  # noqa: BLE001
        err(f"erreur inattendue : {type(e).__name__} — {str(e)[:200]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
