"""
LE JUGE CLAUDE HEADLESS — s14_sentiment (`claude -p … --output-format json`)
============================================================================

Une seule responsabilité : transformer UN LOT de headlines forex en verdicts
bruts `{"verdicts": [{symbol, sentiment, confidence, reason}, …]}` — un par
instrument de l'univers scellé — ou `None` si le CLI est en panne (absent,
timeout, erreur, JSON illisible) APRÈS la relance unique autorisée
(PROTOCOL.md § 2.3). `None` n'est jamais une exception : le runner journalise
alors des `na` et le témoin FinBERT juge quand même — les curseurs des juges
sont indépendants.

Motif REPRIS de `studies/macd_ai_paper/ai_judge.py` (prompt par STDIN, env
nettoyé, extraction par équilibrage d'accolades, une relance). Une seule
leçon, pas deux.

LE MODÈLE EST ÉPINGLÉ — et journalisé
--------------------------------------
`JUDGE_MODEL` fige le cerveau du juge : sans `--model`, le CLI suit son
défaut, qui bouge à chaque mise à jour. Un juge scellé qui change de modèle en
cours d'étude mesurerait deux choses différentes sous un seul nom, et le
corpus deviendrait illisible a posteriori.

Le protocole fige DOUZE colonnes de journal (§ 3) : on n'en ajoute pas une
treizième pour l'identifiant du modèle. Tranché ici, et documenté :
**l'identifiant est préfixé au champ `reason` de chaque ligne VERDICT**, sous
la forme `[claude-sonnet-4-5] <phrase>`.

POURQUOI `reason` et pas le nom du juge : la colonne `judge` est la CLÉ des
curseurs (`state["judges"]`), de l'appariement F3/F4 et du vocabulaire fixé
par le § 3 (`claude-cli` | `finbert`). La suffixer d'un modèle créerait un
juge nouveau à chaque montée de version — curseur neuf, backlog reparti en
STALE, compteur F1 remis à zéro : le contraire de ce qu'on cherche. `reason`
est au contraire un champ libre, borné à 300 chars, qu'aucune lecture
(§ 4-§ 5) n'interprète — la lecture ne lit que `sentiment`, `confidence`,
`judge`, `symbol` et les horodatages. Le tag y est donc de la traçabilité
pure, ligne à ligne, sans effet de mesure. Il est également porté par les
lignes `na` (via `na_reason`), pour qu'une panne soit imputable au modèle qui
l'a subie.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

# LE CERVEAU DU JUGE, FIGÉ. Ne change qu'avec une entrée datée en annexe du
# protocole (§ 2.5, même frontière qu'un juge ajouté) — jamais en silence.
JUDGE_MODEL = "claude-sonnet-4-5"

PROMPT_TEMPLATE = """Tu es analyste de sentiment sur le marché des changes. \
Tu reçois les titres de presse forex publiés dans les dernières heures. Ta \
seule mission : dire, pour CHACUN des instruments listés, l'effet ATTENDU de \
ces nouvelles sur son cours.

Règles impératives :
- Tu réponds UNIQUEMENT avec un objet JSON strict, sans texte autour, sans \
markdown, sans backticks :
  {{"verdicts":[{{"symbol":"<code>","sentiment":"positive"|"negative"|\
"neutral","confidence":<0..1>,"reason":"<une phrase>"}}]}}
- Un objet par instrument, pour les {n_symbols} instruments suivants, et \
aucun autre : {symbols}
- "sentiment" est l'effet attendu sur la PAIRE, pas l'humeur du titre : une \
nouvelle qui renforce le dollar rend EURUSD "negative" (le dollar est au \
dénominateur), et une nouvelle qui renforce l'euro le rend "positive". \
Raisonne devise par devise, dans le sens de la cotation.
- "neutral" est une réponse légitime et ATTENDUE : la plupart des titres ne \
concernent pas la plupart des paires. Un juge qui trouve une direction \
partout n'informe sur rien.
- "confidence" est ta probabilité subjective HONNÊTE que la direction \
annoncée soit la bonne, pas un score d'enthousiasme : 0,5 = pile ou face, \
0,9 = tu paierais pour parier dessus. Ne gonfle jamais pour "faire un avis".
- N'invente rien au-delà des titres fournis : pas de chiffre, pas \
d'événement, pas de niveau de prix qui n'y figure pas. Aucune donnée de \
marché ne t'est donnée, et c'est voulu.
- "reason" : UNE phrase courte, factuelle, adossée aux titres.

TITRES ({n_news}, du plus ancien au plus récent) :
{headlines}"""


def _age_txt(published_at_utc: str, now: datetime) -> str:
    """L'âge RELATIF d'un titre. Le prompt ne porte aucune date absolue : un
    juge qui saurait « on est le 12 mars 2026 » pourrait raisonner sur ce
    qu'il a appris du marché à cette date-là plutôt que sur les titres."""
    try:
        pub = datetime.strptime(published_at_utc,
                                "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return "âge inconnu"
    minutes = max(0, int((now - pub).total_seconds() // 60))
    if minutes < 60:
        return f"il y a {minutes} min"
    return f"il y a {minutes // 60} h {minutes % 60:02d}"


def build_prompt(batch: list[dict], universe: list[str],
                 now: Optional[datetime] = None) -> str:
    """Le prompt d'UN LOT. Figé au premier passage de mesure (§ 2.3) :
    le modifier ensuite invalide l'étude (§ 5, invariance)."""
    now = now or datetime.now(timezone.utc)
    lignes = []
    for i, b in enumerate(batch, start=1):
        src = str(b.get("source", "")).strip() or "source inconnue"
        lignes.append(f"[{i}] ({_age_txt(b.get('published_at_utc', ''), now)}) "
                      f"{src} — {b.get('headline', '')}")
    return PROMPT_TEMPLATE.format(
        n_symbols=len(universe), symbols=", ".join(universe),
        n_news=len(batch), headlines="\n".join(lignes))


def extract_json_object(text: str) -> Optional[dict]:
    """Premier objet JSON équilibré du texte — tolère du texte autour.

    Scanner à équilibrage d'accolades, PAS de regex : une regex sur du JSON
    imbriqué s'arrête à la première accolade fermante et rend un fragment
    invalide (leçon de macd_ai_paper).
    """
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def _clean_env() -> dict:
    """Le CLI enfant ne doit pas hériter du contexte d'une éventuelle session
    Claude Code parente (base URL proxy, marqueurs de session)."""
    env = dict(os.environ)
    for k in list(env):
        if k.startswith(("CLAUDE_", "CLAUDECODE")) or k == "ANTHROPIC_BASE_URL":
            env.pop(k, None)
    return env


def invoke_claude_once(prompt: str, timeout_s: int,
                       model: str = JUDGE_MODEL) -> tuple[Optional[dict], str]:
    """Un appel. -> (verdicts bruts, cause courte). Verdicts None = panne.

    La cause est celle qui partira au journal si la relance échoue aussi
    (§ 3 : une ligne `na` porte la cause, pas la prose).
    """
    exe = shutil.which("claude")
    if exe is None:
        print("[JUDGE] claude CLI introuvable dans le PATH", file=sys.stderr)
        return None, "cli introuvable"
    try:
        # Le prompt passe par STDIN, jamais par argv : sous Windows la ligne
        # de commande est plafonnée à ~32 767 caractères et un lot de 40
        # headlines la dépasse — le prompt arriverait TRONQUÉ et le juge
        # répondrait, de bonne foi, sur ce qu'il en resterait (leçon payée
        # par studies/macd_ai_paper).
        # `subprocess.run(timeout=...)` NE SUFFIT PAS ici. Sous Windows,
        # `claude` est un shim npm .CMD : le vrai travailleur est un node.exe
        # PETIT-FILS. Au timeout, run() tue le fils direct puis appelle
        # communicate() SANS timeout — le petit-fils garde les descripteurs
        # d'écriture des tuyaux, et l'attente ne rend jamais la main. Le tick
        # pendrait alors jusqu'au taskkill de la factory (20 min), après avoir
        # payé. On tue donc l'ARBRE nous-mêmes, exactement comme la factory a
        # appris à le faire.
        # `errors="replace"` : un seul octet UTF-8 invalide ferait échouer le
        # décodage DANS le thread lecteur — run() ne lèverait pas, il rendrait
        # un stdout VIDE. On conclurait « réponse illisible », on écrirait 5
        # `na`, et le curseur avancerait : un appel payé transformé en trou
        # définitif du corpus, pour un accent mal encodé.
        proc = subprocess.Popen(
            [exe, "-p", "--output-format", "json", "--model", model],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", env=_clean_env())
        try:
            sortie, erreur = proc.communicate(prompt, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, check=False)
            try:
                sortie, erreur = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                sortie, erreur = "", ""
            raise
        cp = subprocess.CompletedProcess(proc.args, proc.returncode,
                                         sortie, erreur)
    except subprocess.TimeoutExpired:
        print(f"[JUDGE] timeout après {timeout_s} s — arbre du processus tué",
              file=sys.stderr)
        return None, "timeout"
    except OSError as e:
        print(f"[JUDGE] échec de lancement : {type(e).__name__}", file=sys.stderr)
        return None, "lancement impossible"
    if cp.returncode != 0 and not cp.stdout.strip():
        print(f"[JUDGE] exit {cp.returncode} : {cp.stderr[:300]}",
              file=sys.stderr)
        return None, f"exit {cp.returncode}"
    try:
        envelope = json.loads(cp.stdout)
    except json.JSONDecodeError:
        # Selon la version du CLI, --output-format json peut rendre du texte
        # brut. On tente d'extraire les verdicts directement du texte avant
        # de déclarer la panne : la robustesse du parseur ne doit pas dépendre
        # de la version d'un outil externe.
        raw = extract_json_object(cp.stdout)
        if raw is not None and "verdicts" in raw:
            return raw, ""
        print(f"[JUDGE] enveloppe illisible : {cp.stdout[:200]}",
              file=sys.stderr)
        return None, "enveloppe illisible"
    if envelope.get("is_error"):
        print(f"[JUDGE] CLI en erreur : {str(envelope.get('result'))[:200]}",
              file=sys.stderr)
        return None, "cli en erreur"
    raw = extract_json_object(str(envelope.get("result", "")))
    if raw is None or "verdicts" not in raw:
        print(f"[JUDGE] pas de verdicts JSON dans la réponse : "
              f"{str(envelope.get('result'))[:200]}", file=sys.stderr)
        return None, "json illisible"
    return raw, ""


def tag_model(raw: dict, model: str = JUDGE_MODEL) -> dict:
    """Préfixe l'identifiant du modèle à chaque `reason` — la traçabilité du
    cerveau, SANS colonne nouvelle (voir l'en-tête du module). La troncature à
    `judge.max_reason_chars` est faite par la bibliothèque, à l'écriture."""
    entries = raw.get("verdicts")
    if not isinstance(entries, list):
        return raw
    for e in entries:
        if isinstance(e, dict):
            e["reason"] = f"[{model}] {str(e.get('reason', '')).strip()}".strip()
    return raw


def na_reason(cause: str, model: str = JUDGE_MODEL) -> str:
    """La cause courte d'un lot `na`, elle aussi tagguée du modèle : une panne
    doit être imputable au cerveau qui l'a subie."""
    return f"[{model}] {cause or 'juge indisponible'}"


def make_judge(params: dict, model: str = JUDGE_MODEL):
    """-> `judge(batch) -> verdicts bruts | None`, portant `judge.last_error`
    (cause courte du dernier échec, vide sinon — le runner la journalise).

    UNE relance en cas d'échec, puis `na` : une panne du juge payant ne doit
    jamais bloquer le témoin gratuit (§ 2.3).
    """
    timeout_s = int(params["judge"]["timeout_s"])
    retries = int(params["judge"]["retries"])
    universe = list(params["universe"])

    def judge(batch: list[dict]) -> Optional[dict]:
        judge.last_error = ""
        if not batch:
            judge.last_error = na_reason("lot vide", model)
            return None
        prompt = build_prompt(batch, universe)
        cause = "juge indisponible"
        for _ in range(1 + retries):
            raw, cause = invoke_claude_once(prompt, timeout_s, model)
            if raw is not None:
                return tag_model(raw, model)
        judge.last_error = na_reason(cause, model)
        return None

    judge.last_error = ""
    judge.model = model
    return judge
