"""
LE TÉMOIN FINBERT — s14_sentiment (ProsusAI/finbert, local, zéro token)
=======================================================================

Le corollaire falsifiable de l'étude (PROTOCOL.md § 0) : FinBERT est gratuit.
Si le juge payant ne le bat pas sur le même corpus (F3), les tokens ne sont
pas justifiés. Le témoin doit donc être « la méthode de la vidéo » et pas une
variante flatteuse — l'agrégation est répliquée à l'identique du MLTradingBot
source (§ 2.4) :

    tokens = tokenizer(news, return_tensors="pt", padding=True)
    logits = model(input_ids, attention_mask)["logits"]
    result = softmax(sum(logits, 0), dim=-1)      # somme des logits du LOT
    (probabilité, label) = (max(result), labels[argmax(result)])

L'ordre des étiquettes `["positive", "negative", "neutral"]` est celui du
MLTradingBot source ET celui de la tête de classification ProsusAI/finbert :
c'est lui qui donne son sens à `argmax`.

DEUX PROPRIÉTÉS NON NÉGOCIABLES
-------------------------------
1. IMPORT PARESSEUX de `transformers`/`torch` — À L'INTÉRIEUR de la fonction.
   Le worker tourne toutes les 1800 s et le témoin peut être coupé au fichier
   juges (§ 8) : payer le chargement d'un modèle de 400 Mo à chaque passage,
   y compris quand FinBERT est OFF ou qu'aucun lot n'attend, serait absurde.
   Le modèle chargé est mis en cache module — un seul chargement par processus.
2. JAMAIS DE CRASH. Bibliothèque absente, modèle non téléchargé, réseau HF
   coupé, tenseur inattendu : on rend `None`, le runner journalise des `na`,
   l'étude continue (§ 2.4). Une panne du témoin ne fausse jamais le juge.

ANGLE MORT DÉCLARÉ (§ 2.4) : FinBERT ne connaît pas les paires. Le verdict du
lot est appliqué UNIFORMÉMENT aux cinq instruments — le témoin mesure le
sentiment du FLUX, pas celui d'un instrument. C'est une différence assumée
avec Claude (qui peut différencier), inscrite au protocole avant la première
mesure, et rappelée dans chaque `reason` journalisée.
"""
from __future__ import annotations

import sys
from typing import Optional

WITNESS_MODEL = "ProsusAI/finbert"

# L'ordre FAIT LA MESURE (index d'argmax) — ne pas trier, ne pas « ranger ».
LABELS = ["positive", "negative", "neutral"]

# (tokenizer, model, torch) — un seul chargement par processus.
_CACHE: Optional[tuple] = None
_LAST_ERROR = ""


def last_error() -> str:
    """La cause courte du dernier échec du témoin (vide si aucun)."""
    return _LAST_ERROR


def _load(model_name: str):
    """Chargement PARESSEUX et mis en cache. Lève — l'appelant traduit en
    `None` : c'est le seul endroit qui a le droit d'échouer bruyamment."""
    global _CACHE
    if _CACHE is None:
        from transformers import (AutoModelForSequenceClassification,
                                  AutoTokenizer)
        import torch
        # `local_files_only` : on refuse de TÉLÉCHARGER ici. Le modèle pèse
        # ~440 Mo et le tick est plafonné à 20 minutes par la factory — un
        # premier chargement sur une ligne lente ferait tuer l'arbre en plein
        # vol, tick après tick, pendant que le curseur du témoin resterait
        # figé et que ses news partiraient en STALE : le bras témoin se
        # viderait en silence, et F3 (« les tokens sont-ils justifiés ? »)
        # deviendrait non évaluable. Le téléchargement est un geste
        # d'armement, une fois, hors de l'usine (voir PROTOCOL § armement).
        tokenizer = AutoTokenizer.from_pretrained(model_name,
                                                 local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name, local_files_only=True)
        model.eval()
        _CACHE = (tokenizer, model, torch)
    return _CACHE


def estimate_sentiment(headlines: list[str],
                       model_name: str = WITNESS_MODEL
                       ) -> Optional[tuple[float, str]]:
    """-> (probabilité de la classe majoritaire, label) ou None si indisponible.

    Agrégation du lot par softmax de la SOMME des logits — motif exact du
    MLTradingBot (§ 2.4). Aucune variante, aucune moyenne « améliorée » : le
    témoin ne vaut que s'il est celui qu'on prétend battre.
    """
    global _LAST_ERROR
    _LAST_ERROR = ""
    news = [h for h in (headlines or []) if str(h).strip()]
    if not news:
        _LAST_ERROR = "aucun headline exploitable"
        return None
    try:
        tokenizer, model, torch = _load(model_name)
    except Exception as e:                       # noqa: BLE001 — jamais de crash
        _LAST_ERROR = "modèle indisponible"
        print(f"[FINBERT] chargement impossible ({model_name}) : {e!r} — "
              f"verdicts na, l'étude continue.", file=sys.stderr)
        return None
    try:
        tokens = tokenizer(news, return_tensors="pt", padding=True)
        # `no_grad` ne change AUCUNE valeur (il coupe seulement la
        # construction du graphe d'autograd) — la mesure reste celle du
        # MLTradingBot, sans garder un graphe inutile en mémoire.
        with torch.no_grad():
            logits = model(tokens["input_ids"],
                           attention_mask=tokens["attention_mask"])["logits"]
        result = torch.nn.functional.softmax(torch.sum(logits, 0), dim=-1)
        idx = int(torch.argmax(result))
        return float(result[idx]), LABELS[idx]
    except Exception as e:                       # noqa: BLE001 — jamais de crash
        _LAST_ERROR = "inférence en échec"
        print(f"[FINBERT] inférence en échec : {e!r} — verdicts na.",
              file=sys.stderr)
        return None


def make_witness(params: dict):
    """-> `witness(batch) -> verdicts bruts | None`, portant
    `witness.last_error` (cause courte du dernier échec).

    Sortie de la MÊME forme que celle du juge Claude : la bibliothèque
    (`record_verdicts`) ne connaît qu'un seul format, clampé de la même façon.
    """
    universe = list(params["universe"])
    model_name = params["witness"]["model"]

    def witness(batch: list[dict]) -> Optional[dict]:
        witness.last_error = ""
        headlines = [b.get("headline", "") for b in (batch or [])]
        out = estimate_sentiment(headlines, model_name)
        if out is None:
            witness.last_error = f"[{model_name}] {last_error() or 'témoin indisponible'}"
            return None
        probability, label = out
        n = len([h for h in headlines if str(h).strip()])
        reason = (f"[{model_name}] softmax de la somme des logits sur {n} "
                  f"headlines — verdict de lot appliqué uniformément aux "
                  f"{len(universe)} instruments (angle mort déclaré § 2.4)")
        return {"verdicts": [{"symbol": s, "sentiment": label,
                              "confidence": probability, "reason": reason}
                             for s in universe]}

    witness.last_error = ""
    witness.model = model_name
    return witness
