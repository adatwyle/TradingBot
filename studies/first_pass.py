"""
studies/first_pass.py — garde commune « premier passage » des runners d'études.
================================================================================

POURQUOI : les 5 études scellées migrent leur journal VIVANT depuis le
prototype (C:\\db\\tbot\\) par bascule manuelle, étude par étude, sur GO
Adrian (studies/CUTOVER.md). Un runner lancé AVANT la bascule ne trouve pas de
journal et démarrerait un PREMIER PASSAGE : journal NEUF dans
C:\\db\\tradingBot\\, deux journaux parallèles pour la même étude — exactement
l'entrelacement que le protocole interdit.

Par défaut, un journal ABSENT est donc un REFUS : sortie 2 (ressource
indisponible — la factory réessaie sans crier, aucun incident). Une étude
réellement NEUVE s'autorise explicitement avec TBOT_ALLOW_FIRST_PASS=1 ;
une étude déjà basculée (journal présent) passe sans variable d'environnement.
"""
from __future__ import annotations

import os
import sys


def first_pass_refused(journal_path: str, etude: str) -> bool:
    """True si le passage doit être REFUSÉ (journal absent, pas d'autorisation
    explicite). Le message part sur stderr ; l'appelant sort en 2."""
    if os.path.exists(journal_path):
        return False
    if os.environ.get("TBOT_ALLOW_FIRST_PASS") == "1":
        return False
    print(f"[GUARD] {etude} : premier passage refusé — étude en attente de "
          f"bascule (studies/CUTOVER.md) ou TBOT_ALLOW_FIRST_PASS=1 pour une "
          f"étude neuve. Journal attendu : {journal_path}", file=sys.stderr)
    return True
