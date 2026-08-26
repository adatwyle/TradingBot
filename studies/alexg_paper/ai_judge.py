"""
LE JUGE HEADLESS — invocation `claude -p … --output-format json`
=================================================================

Une seule responsabilité : transformer un dossier de décision (dict factuel,
construit par `paper_step.build_dossier`) en décision brute
{decision, size, reason} — ou None si le CLI est en panne (timeout, erreur,
JSON illisible) APRÈS la relance unique autorisée.

La mécanique d'invocation (STDIN, enveloppe JSON, extraction par équilibrage
d'accolades, nettoyage d'environnement) est REPRISE ligne à ligne de
`studies/macd_ai_paper/ai_judge.py` — une seule leçon, pas deux. Seul le
PROMPT change : ici l'analyste juge un setup de swing forex selon la méthode
de la source, là-bas un signal de mean-reversion sur indice.

CE QUE CE JUGE N'EST PAS
-------------------------
Ce n'est PAS la grille à cases de s93 (compter des confluences, ×10 %, seuiller
le total). Cette grille est mesurée non discriminante : sa distribution
observée plafonne à 60 % et monter le seuil DÉGRADE le résultat
(s93/research/VERDICT.md, F3). Le juge décide ; il ne compte pas.

DÉFENSE EN PROFONDEUR (trois couches, dans l'ordre)
----------------------------------------------------
1. le prompt INTERDIT de sortir des bornes ;
2. `paper_step.clamp_decision` ramène toute valeur dans les bornes ;
3. `RiskLayer.evaluate` borne le risque monétaire quoi qu'il arrive.
Une IA qui « négocie » ses bornes ne peut donc au pire que choisir take/skip.

FORMAT DE L'ENVELOPPE CLI (vérifié sur claude 2.1.152, 2026-08-16)
-------------------------------------------------------------------
`--output-format json` rend UN objet JSON : {"type":"result",
"subtype":"success", "is_error": bool, "result": "<texte du modèle>", …}.
`is_error: true` (ex. 401 OAuth expiré) = panne.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Optional

PROMPT_TEMPLATE = """Tu es l'analyste d'un compte de trading virtuel qui \
exécute UNE méthode de swing forex précise. Le détecteur mécanique vient de \
produire un candidat d'entrée. Ta seule mission : décider si CE candidat \
mérite d'être pris, et à quelle taille.

LA MÉTHODE QUE TU JUGES (spec publique 2025 de la source, reproduite par le \
détecteur) :
- tendance : au moins 2 timeframes CONSÉCUTIFS alignés (W+D ou D+H4), \
structure lue sur les CORPS de bougie, jamais sur les mèches ;
- zone d'intérêt (AOI) : zone de <= 60 pips, >= 3 touches en corps, repérée \
sur W ou D ; on entre sur le RETOUR dans la zone, jamais sur la cassure ;
- déclencheur : shift de structure par body close sur H1, idéalement \
head & shoulders avec cassure PUIS retest de la neckline, confirmé par une \
bougie engulfing ;
- stop structurel derrière le pivot, cible avant le prochain point de \
structure, R:R >= 2 ; set and forget (ni breakeven, ni trailing) ;
- la source prend environ 1 candidat identifié sur 4 : la sélectivité fait \
partie de la méthode.

CE QUE TU DOIS SAVOIR SUR CE FLUX (mesuré, pas supposé) :
- le détecteur est réglé pour le RAPPEL, pas pour la précision : il attrape \
large et le tri est TON travail ;
- pris tel quel, ce flux perd : -0,21 R par trade sur 777 candidats \
historiques. Approuver systématiquement est donc mesuré perdant ;
- refuser systématiquement n'apprend rien non plus. On mesure ta capacité à \
SÉPARER, pas ta prudence.

Règles impératives :
- Tu réponds UNIQUEMENT avec un objet JSON strict, sans texte autour, sans \
markdown, sans backticks :
  {{"decision":"take"|"skip","size":<0..1>,"reason":"<une phrase>"}}
- "size" : fraction du risque de base (1 % du capital). 0 = ne pas prendre. \
Module-la selon ta conviction, elle est mesurée contre le résultat.
- INTERDICTION de sortir des bornes données dans "bounds" (elles seront de \
toute façon appliquées par une couche de risque que tu ne contrôles pas).
- Décide sur les FAITS du dossier : qualité de la zone (largeur, touches, \
présence sur les deux timeframes), alignement des timeframes, netteté du \
shift, présence de l'engulfing et du break+retest, distance à l'EMA et au \
niveau rond, R:R, profondeur du retracement, session, et l'allure des barres \
fournies. N'invoque RIEN que le dossier ne contient pas — ni actualité, ni \
niveau que tu croirais connaître, ni le nom de l'instrument (il n'y est pas).
- Une phrase de raison, factuelle, citant les éléments qui ont fait pencher.

DOSSIER :
{dossier}"""


def build_prompt(dossier: dict) -> str:
    return PROMPT_TEMPLATE.format(
        dossier=json.dumps(dossier, ensure_ascii=False, separators=(",", ":")))


def extract_json_object(text: str) -> Optional[dict]:
    """Premier objet JSON équilibré du texte — tolère du texte autour."""
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


def invoke_claude_once(prompt: str, timeout_s: int) -> Optional[dict]:
    """Un appel. None = panne (CLI absent, timeout, erreur, JSON illisible)."""
    exe = shutil.which("claude")
    if exe is None:
        print("[JUDGE] claude CLI introuvable dans le PATH", file=sys.stderr)
        return None
    try:
        # Le prompt passe par STDIN, jamais par argv : sous Windows la ligne de
        # commande est plafonnee a ~32 767 caracteres et un dossier avec ses
        # barres depasse ce plafond -- le prompt arriverait TRONQUE (panne
        # constatee sur macd_ai_paper).
        cp = subprocess.run(
            [exe, "-p", "--output-format", "json"],
            input=prompt,
            capture_output=True, text=True, encoding="utf-8",
            timeout=timeout_s, env=_clean_env())
    except subprocess.TimeoutExpired:
        print(f"[JUDGE] timeout après {timeout_s} s", file=sys.stderr)
        return None
    except OSError as e:
        print(f"[JUDGE] échec de lancement : {e}", file=sys.stderr)
        return None
    if cp.returncode != 0 and not cp.stdout.strip():
        print(f"[JUDGE] exit {cp.returncode} : {cp.stderr[:300]}", file=sys.stderr)
        return None
    try:
        envelope = json.loads(cp.stdout)
    except json.JSONDecodeError:
        # Selon la version du CLI, --output-format json peut rendre du texte
        # brut. On tente d'extraire la decision avant de declarer la panne.
        dec = extract_json_object(cp.stdout)
        if dec is not None and "decision" in dec:
            return dec
        print(f"[JUDGE] enveloppe illisible : {cp.stdout[:200]}", file=sys.stderr)
        return None
    if envelope.get("is_error"):
        print(f"[JUDGE] CLI en erreur : {str(envelope.get('result'))[:200]}",
              file=sys.stderr)
        return None
    dec = extract_json_object(str(envelope.get("result", "")))
    if dec is None or "decision" not in dec:
        print(f"[JUDGE] pas de décision JSON dans la réponse : "
              f"{str(envelope.get('result'))[:200]}", file=sys.stderr)
        return None
    return dec


def make_judge(params: dict):
    """judge_fn(dossier) -> décision brute ou None. UNE relance en cas
    d'échec, puis N/A : une panne d'IA ne doit jamais fausser les témoins
    (paper_step gère le N/A sans toucher MECH/RND)."""
    timeout_s = int(params["ai"]["timeout_s"])
    retries = int(params["ai"]["retries"])

    def judge(dossier: dict) -> Optional[dict]:
        prompt = build_prompt(dossier)
        for _ in range(1 + retries):
            dec = invoke_claude_once(prompt, timeout_s)
            if dec is not None:
                return dec
        return None

    return judge
