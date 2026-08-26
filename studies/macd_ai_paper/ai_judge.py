"""
LE JUGE HEADLESS — invocation `claude -p … --output-format json`
=================================================================

Une seule responsabilité : transformer un dossier de décision (dict factuel,
construit par `paper_step.build_dossier`) en décision brute {decision, size,
sl_adjust, tp_adjust, reason} — ou None si le CLI est en panne (timeout,
erreur, JSON illisible) APRÈS la relance unique autorisée.

Le prompt est PARTAGÉ avec le rejeu à l'aveugle accéléré (`replay_*`) : même
rôle, même sortie, mêmes bornes — pour que le rejeu mesure bien ce que le
runner temps réel exécutera.

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
`is_error: true` (ex. 401 OAuth expiré) = panne. Le texte du modèle doit
contenir un objet JSON — extrait par équilibrage d'accolades, pas par regex
fragile.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Optional

PROMPT_TEMPLATE = """Tu es le gestionnaire de risque d'un compte de trading \
virtuel qui exécute UNE stratégie précise, décrite dans le dossier JSON \
ci-dessous. La stratégie mécanique vient de produire un signal d'entrée. Ta \
seule mission : décider si CE trade mérite d'être pris, et à quelle taille.

Règles impératives :
- Tu réponds UNIQUEMENT avec un objet JSON strict, sans texte autour, sans \
markdown, sans backticks :
  {{"decision":"take"|"skip","size":<0..1>,"sl_adjust":<0.5..1.0>,\
"tp_adjust":<0.5..1.0>,"reason":"<une phrase>"}}
- "size" : fraction du risque de base (1 % du capital). 0 = ne pas prendre.
- "sl_adjust"/"tp_adjust" : facteur appliqué à la distance stop/cible. 1.0 = \
niveaux de la stratégie ; < 1.0 = resserré. INTERDICTION de sortir des bornes \
données dans "bounds" (elles seront de toute façon appliquées par une couche \
de risque que tu ne contrôles pas).
- Décide sur les FAITS du dossier (structure des barres, position dans le \
range, distance du stop, R:R, état du compte). Pas de considérations que le \
dossier ne contient pas.
- Sois sélectif si les faits le justifient, pas par principe : un skip \
systématique est aussi peu informatif qu'un take systématique.

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
        # Le prompt passe par STDIN, jamais par argv : sous Windows la ligne
        # de commande est plafonnee a ~32 767 caracteres et un dossier avec
        # ses barres depasse ce plafond -- le prompt arrivait TRONQUE et le
        # juge repondait, de bonne foi, "le dossier JSON n'apparait pas".
        # Constate au premier test-judge reel apres le re-login d'Adrian.
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
        print(f"[JUDGE] exit {cp.returncode} : {cp.stderr[:300]}",
              file=sys.stderr)
        return None
    try:
        envelope = json.loads(cp.stdout)
    except json.JSONDecodeError:
        # Selon la version du CLI, --output-format json peut rendre du texte
        # brut. On tente d'extraire la decision directement du texte avant de
        # declarer la panne : la robustesse du parseur ne doit pas dependre de
        # la version d'un outil externe.
        dec = extract_json_object(cp.stdout)
        if dec is not None and "decision" in dec:
            return dec
        print(f"[JUDGE] enveloppe illisible : {cp.stdout[:200]}",
              file=sys.stderr)
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
