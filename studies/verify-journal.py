"""
VÉRIFICATION D'INTÉGRITÉ D'UN JOURNAL CHAÎNÉ — outil de bascule (TCK-009/T10)
==============================================================================

    python studies/verify-journal.py <étude> [--dir <chemin>]

Vérifie la chaîne de hachage d'un journal d'étude scellée, AVANT et APRÈS le
déplacement `C:/db/tbot/<étude>/` -> `C:/db/tradingBot/<étude>/` (runbook :
studies/CUTOVER.md). STRICTEMENT LECTURE SEULE — aucun fichier n'est créé,
modifié ni déplacé, quel que soit le résultat.

RÉUTILISATION, PAS RÉINVENTION : la vérification est déléguée à la fonction
`verify_journal` de l'étude elle-même (module *_step migré du prototype) —
la même que le pas de mesure exécute avant chaque écriture. Deux contrôles :
  1. chaîne interne  — chaque ligne porte le SHA-256 du fichier AVANT elle ;
  2. empreinte d'état — state.json mémorise (taille, SHA-256) du dernier
     passage, attrape une reconstruction complète du fichier.
La chaîne ne hache QUE le contenu du fichier (octets), jamais son chemin :
un journal déplacé intact se vérifie à l'identique au nouvel emplacement.

CODES DE SORTIE
---------------
    0  journal intact (chaîne + empreinte d'état cohérentes)
    2  journal/dossier introuvable (rien à vérifier — pas une altération)
    4  JOURNAL ALTÉRÉ (chaîne cassée, troncature, réécriture) — enquête
       requise, AUCUNE bascule tant que l'altération n'est pas expliquée

`--dir` : dossier de données à vérifier (défaut : l'emplacement cible de
l'étude sous C:/db/tradingBot/). Pour vérifier le journal du prototype AVANT
déplacement : `--dir C:/db/tbot/<étude>` (lecture seule, sans danger).
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `core` vit dans app/ — les deux racines sont importables (cf. app/core/paths.py).
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# étude -> module qui porte Paths / load_state / verify_journal / read_journal.
# La mécanique de chaîne est identique dans les 5 études (héritage prototype) ;
# chaque module connaît SES colonnes — on délègue, on ne réimplémente pas.
STEP_MODULES = {
    "gold_forward":  "studies.gold_forward.forward_step",
    "s13_forward":   "studies.s13_forward.forward_step",
    "s14_sentiment": "studies.s14_sentiment.sentiment_step",
    "macd_ai_paper": "studies.macd_ai_paper.paper_step",
    "alexg_paper":   "studies.alexg_paper.paper_step",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Vérifie la chaîne de hachage du journal d'une étude "
                    "scellée (lecture seule).")
    ap.add_argument("etude", choices=sorted(STEP_MODULES),
                    help="l'étude dont on vérifie le journal")
    ap.add_argument("--dir", dest="data_dir", default=None,
                    help="dossier de données (défaut : emplacement cible de "
                         "l'étude ; pour le prototype : C:/db/tbot/<étude>)")
    args = ap.parse_args(argv)

    step = importlib.import_module(STEP_MODULES[args.etude])
    paths = step.Paths(args.data_dir) if args.data_dir else step.Paths()

    if not os.path.isdir(paths.data_dir):
        print(f"[VERIFY] dossier introuvable : {paths.data_dir}", file=sys.stderr)
        return 2
    if not os.path.exists(paths.journal):
        print(f"[VERIFY] journal absent : {paths.journal}", file=sys.stderr)
        return 2

    state = step.load_state(paths.state)
    if state is None:
        print(f"[VERIFY] state.json absent ({paths.state}) — vérification de "
              f"la chaîne interne seule (l'empreinte du dernier passage ne "
              f"peut pas être contrôlée).", file=sys.stderr)

    try:
        step.verify_journal(paths.journal, state)
    except step.JournalError as e:
        print(f"[JOURNAL] ALTÉRÉ — {e}", file=sys.stderr)
        print("[JOURNAL] AUCUNE bascule tant que l'altération n'est pas "
              "expliquée — voir PROTOCOL.md § intégrité.", file=sys.stderr)
        return 4

    rows = step.read_journal(paths.journal)
    n_bytes = os.path.getsize(paths.journal)
    print(f"[VERIFY] OK — {args.etude} : journal intact "
          f"({len(rows)} lignes, {n_bytes} octets) · {paths.journal}")
    if state is not None:
        print(f"[VERIFY] empreinte d'état cohérente "
              f"(journal_bytes={state.get('journal_bytes')}, "
              f"sha256={str(state.get('journal_sha256', ''))[:16]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
