#!/usr/bin/env python3
"""
robinbot-mesureur.py — CELUI QUI FAIT AVANCER LE TRAVAIL EN COURS
==================================================================

Toutes les deux heures, ce worker lit `orchestrator/mesureur-mandat.txt`. S'il
y trouve un mandat, il ouvre une session Claude Code headless qui applique la
skill `robinbot-mesureur` : UN pas mécanique sur l'étude en cours, testé, puis
un rapport dans `orchestrator/mesureur-rapport.md`.

LE MANDAT EST UN FICHIER, PAS UNE INTENTION
--------------------------------------------
Adrian écrit une ligne dans `mesureur-mandat.txt` et le travail avance tout
seul jusqu'à la prochaine porte fermée. Il vide le fichier et le worker se tait.
C'est un interrupteur lisible, versionnable, et qui survit à la fermeture de
toutes les sessions — la même raison qui a fait quitter les tâches planifiées
Windows pour une console qu'on voit tourner.

LA VEILLE EST EN PYTHON, DONC GRATUITE
---------------------------------------
Fichier absent, vide, ou ne portant que des commentaires `#` : sortie 0
immédiate, aucune session, aucun token. C'est le cas NORMAL — l'usine passe
l'essentiel de son temps sans mandat en cours.

LE WORKER LE PLUS PUISSANT DU DÉPÔT
------------------------------------
`--allowedTools Read,Grep,Glob,Edit,Write,Bash` : il écrit du code de portage et
lance `pytest`. Aucune liste d'outils ne peut rendre ça inoffensif, et prétendre
le contraire serait se mentir. Sa sûreté tient à trois choses, et à elles
seules :

  1. LES SCELLÉS SONT VÉRIFIÉS, PAS PROMIS. Les SHA-256 des
     `studies/*/params.json` sont relevés AVANT et APRÈS la session. La moindre
     divergence — contenu changé, fichier disparu, fichier apparu — sort en 1,
     crie en première ligne de stderr et s'inscrit dans le rapport. Un scellé
     modifié détruit une étude de façon irréparable par conception.
  2. RIEN N'ENTRE DANS L'HISTOIRE SANS RELECTURE. `git rev-parse HEAD` est
     comparé avant/après : si un commit est apparu, c'est un incident. Le
     travail du mesureur reste dans l'arbre de travail, donc tout ce qu'il
     ferait de travers se défait d'un `git checkout`.
  3. IL NE DÉCIDE RIEN. Sceller, armer, promouvoir, trancher un recadrage sont
     des actes d'Adrian. La skill lui impose de s'arrêter à chaque porte et
     d'écrire ce qui manque.

CODES DE SORTIE (contrat commun de la factory)
-----------------------------------------------
    0  passage effectué (y compris « aucun mandat », le cas le plus fréquent)
    2  session headless indisponible — on réessaiera, l'usine n'en souffre pas
    1  erreur inattendue, ou INCIDENT de garde-fou (scellé touché, commit créé)
Jamais 3/4 : ces deux codes appartiennent aux runners scellés.

USAGE
-----
    python app/orchestrator/robinbot-mesureur.py             # un passage
    python app/orchestrator/robinbot-mesureur.py --dry-run   # montre, n'appelle rien
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
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
_HERE = pathlib.Path(__file__).resolve().parent           # app/orchestrator
sys.path.insert(0, str(_HERE.parent))
from core.paths import db_dir, project_root  # noqa: E402

ROOT = pathlib.Path(os.environ.get("RBF_ROOT") or project_root())
# Le mandat et le rapport vivent À CÔTÉ du script (app/orchestrator/) : ce sont
# des fichiers de travail versionnés, pas de l'état vivant.
MANDAT_FILE = pathlib.Path(os.environ.get("ROBINBOT_MESUREUR_MANDAT")
                           or (_HERE / "mesureur-mandat.txt"))
RAPPORT_FILE = pathlib.Path(os.environ.get("ROBINBOT_MESUREUR_RAPPORT")
                            or (_HERE / "mesureur-rapport.md"))
MESUREUR_DIR = pathlib.Path(os.environ.get("ROBINBOT_MESUREUR_DIR")
                            or (db_dir() / "mesureur"))
STATE_FILE = MESUREUR_DIR / "state.json"

SKILL = "robinbot-mesureur"
# Le worker le plus puissant du dépôt — cf. l'en-tête : ce sont les garde-fous
# mécaniques qui le tiennent, pas cette liste.
ALLOWED_TOOLS = "Read,Grep,Glob,Edit,Write,Bash"
# Généreux : il fait du vrai travail (écrire du code, lancer pytest). Reste
# sous le plafond de tick de la factory (1200 s), qui tuerait l'arbre sinon.
CLAUDE_TIMEOUT_S = int(os.environ.get("ROBINBOT_MESUREUR_TIMEOUT") or 900)
CLAUDE_MAX_TURNS = int(os.environ.get("ROBINBOT_MESUREUR_MAX_TURNS") or 120)

CONSIGNE = (
    "Tu es le mesureur de RobinBot (dépôt TradingBot). Tu fais avancer "
    "UN seul mandat, celui d'app/orchestrator/mesureur-mandat.txt, et seulement si "
    "son objet est EN COURS dans FILE_ETUDES.md. Tu fais UN pas mécanique, "
    "complet et testé — pas dix entamés — puis tu rends la main. Tu prépares et "
    "tu rends compte, tu ne décides pas : sceller, armer, promouvoir, trancher "
    "un recadrage sont des actes d'Adrian ; devant l'une de ces portes tu "
    "t'arrêtes, tu écris ce qui est prêt et ce qui manque, et tu sors. Tu ne "
    "touches à AUCUN scellé (studies/*/params.json, PROTOCOL.md d'études "
    "armées, constantes PARAMS_SHA256) — ils sont vérifiés par hash à ta "
    "sortie. Tu ne commites pas, tu ne pousses pas, tu ne modifies pas le "
    "panneau, tu ne passes aucun ordre. pytest doit être vert avant que tu "
    "rendes la main. Respecte core/contracts/STRATEGY_RULES.md (R1 causalité, "
    "R3 stop obligatoire, R5 même code backtest et live, R9 backtester commun). "
    "Écris ton rapport dans app/orchestrator/mesureur-rapport.md au format imposé "
    "par la skill. Français sobre, aucun enthousiasme : un chiffre sans son "
    "effectif ne veut rien dire."
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
    MESUREUR_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, STATE_FILE)


# == LA VEILLE (Python pur, ZÉRO token) ========================================
def lire_mandat() -> str:
    """Le mandat, commentaires retirés. Chaîne vide = rien à faire.

    Les lignes `#` permettent de garder le gabarit dans le fichier et de le
    laisser en place entre deux mandats — ce qui évite d'avoir à se rappeler du
    format le jour où l'on veut relancer le travail."""
    try:
        brut = MANDAT_FILE.read_text(encoding="utf-8-sig")
    except OSError:
        return ""
    utiles = [l.rstrip() for l in brut.splitlines()
              if l.strip() and not l.strip().startswith("#")]
    return "\n".join(utiles).strip()


# == GARDE-FOUS MÉCANIQUES =====================================================
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
    """Ce qui a bougé entre les deux relevés — changé, disparu, ou apparu.
    Un scellé qui APPARAÎT compte : créer un params.json, c'est sceller."""
    faits: list[str] = []
    for cle in sorted(set(avant) | set(apres)):
        a, b = avant.get(cle), apres.get(cle)
        if a == b:
            continue
        if a is None:
            faits.append(f"{cle} : scellé APPARU (sceller est un acte d'Adrian)")
        elif b is None:
            faits.append(f"{cle} : scellé DISPARU")
        else:
            faits.append(f"{cle} : hash modifié ({a[:12]}… → {b[:12]}…)")
    return faits


def git_head() -> str | None:
    """Le commit courant, ou None si git est indisponible ici. None des deux
    côtés = contrôle impossible, pas contrôle réussi : on le dit dans le log
    plutôt que de laisser croire à une vérification qui n'a pas eu lieu."""
    exe = shutil.which("git")
    if exe is None:
        return None
    try:
        cp = subprocess.run([exe, "rev-parse", "HEAD"], cwd=str(ROOT),
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if cp.returncode != 0:
        return None
    return (cp.stdout or "").strip() or None


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
    l'ARBRE (`taskkill /T /F`), comme la factory le fait pour ses ticks. Ça
    compte doublement ici : ce worker-là a le droit d'écrire.

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


def question_mesureur(mandat: str) -> str:
    """Le prompt nomme la skill et son chemin — comme le fait le gateway quand
    Adrian tape une commande depuis son téléphone. Le mandat est recopié : la
    session doit pouvoir travailler même si le fichier bouge sous ses pieds."""
    return (f"Applique la skill « {SKILL} » du projet "
            f"(voir {_chemin_skill()}) et rends son résultat.\n\n"
            f"Mandat en cours ({MANDAT_FILE}) :\n{mandat}\n\n"
            f"Vérifie d'abord que son objet est EN COURS dans FILE_ETUDES.md, "
            f"fais UN pas, teste-le, et écris ton rapport dans "
            f"{RAPPORT_FILE}.")


def _porte_du_rapport() -> str:
    """La ligne « BLOQUÉ » du rapport, pour que la console dise à quoi le
    passage s'est arrêté sans qu'on ouvre le fichier."""
    try:
        for ligne in RAPPORT_FILE.read_text(encoding="utf-8",
                                            errors="replace").splitlines():
            if ligne.strip().upper().startswith(("BLOQUÉ", "BLOQUE")):
                return ligne.strip()[:120]
    except OSError:
        pass
    return ""


def _inscrire_incident(faits: list[str]) -> None:
    """Le rapport DOIT porter l'incident : c'est lui qu'un humain relit, et la
    session qui vient de déraper est le dernier témoin à croire sur parole."""
    bloc = ("\n\n---\n"
            f"## INCIDENT — garde-fou du worker, {_ts()}\n"
            "Le worker a constaté, hors de la session, que le passage a "
            "franchi une limite qui lui est interdite :\n"
            + "\n".join(f"- {f}" for f in faits)
            + "\nNe 'répare' rien : lis `git status` / `git diff` d'abord.\n")
    try:
        RAPPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RAPPORT_FILE, "a", encoding="utf-8") as f:
            f.write(bloc)
    except OSError as e:  # noqa: BLE001
        err(f"incident non inscrit au rapport ({type(e).__name__}) — il reste "
            f"dans ce log.")


# == LE PASSAGE ================================================================
def tick(dry: bool = False) -> int:
    mandat = lire_mandat()
    if not mandat:
        log(f"aucun mandat ({MANDAT_FILE.name} absent, vide ou commenté) — "
            f"rien à faire, aucune session lancée, zéro token")
        return 0

    premiere = mandat.splitlines()[0][:120]
    log(f"mandat en cours : {premiere}")
    if dry:
        log("DRY-RUN : session non lancée, rien écrit")
        return 0

    scelles_avant = scelles()
    head_avant = git_head()
    if head_avant is None:
        log("git indisponible ici — le contrôle « aucun commit créé » ne sera "
            "pas concluant ce passage")

    log(f"session Claude headless — LANCEMENT (skill {SKILL}, "
        f"outils {ALLOWED_TOOLS}, plafond {CLAUDE_TIMEOUT_S}s)")
    debut = time.monotonic()
    rendu = lancer_session(question_mesureur(mandat))
    duree = time.monotonic() - debut
    issue = f"{len(rendu)} caractères" if rendu else "AUCUNE RÉPONSE"
    log(f"session Claude headless — FIN en {duree:.1f}s ({issue})")

    # Les contrôles ont lieu même si la session a échoué : un timeout tue une
    # session EN COURS d'écriture, il ne prouve pas qu'elle n'a rien fait.
    faits = divergences(scelles_avant, scelles())
    head_apres = git_head()
    if head_avant and head_apres and head_apres != head_avant:
        faits.append(f"git HEAD a bougé ({head_avant[:12]}… → {head_apres[:12]}…) "
                     f"— le mesureur ne commite pas, son travail est relu avant "
                     f"d'entrer dans l'histoire")

    if faits:
        # Première ligne de stderr : l'alerte, avant tout le reste.
        err("INCIDENT — le mesureur a franchi une limite qui lui est interdite :")
        for f in faits:
            err("  " + f)
        err("Un scellé modifié détruit l'étude de façon irréparable. "
            "Ne 'répare' pas params.json : lis `git status`, `git diff`, puis "
            "le PROTOCOL.md concerné.")
        _inscrire_incident(faits)
        log(f"passage terminé : INCIDENT garde-fou ({len(faits)}) — voir "
            f"{RAPPORT_FILE.name}")
        return 1

    if rendu is None:
        log("passage terminé : session indisponible, mandat inchangé, scellés "
            "intacts")
        return 2

    etat = load_state()
    etat["last_run_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    etat["n_sessions"] = int(etat.get("n_sessions", 0)) + 1
    etat["dernier_mandat"] = premiere
    etat["derniere_duree_s"] = round(duree, 1)
    save_state(etat)

    porte = _porte_du_rapport()
    resume = porte or rendu.replace("\n", " ")[:110]
    log(f"passage terminé : un pas en {duree:.0f}s, scellés intacts, aucun "
        f"commit · {resume}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Mesureur RobinBot — fait avancer d'un pas le mandat en cours.")
    ap.add_argument("--dry-run", action="store_true",
                    help="montre le mandat, ne lance aucune session, n'écrit rien")
    a = ap.parse_args()
    try:
        return tick(dry=a.dry_run)
    except Exception as e:  # noqa: BLE001 — un worker ne tue jamais l'usine
        err(f"erreur inattendue : {type(e).__name__} — {str(e)[:200]}")
        log("passage terminé : erreur inattendue")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
