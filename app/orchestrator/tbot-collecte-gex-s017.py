#!/usr/bin/env python3
"""
tbot-collecte-gex-s017.py — WRAPPER DE FENÊTRE HORAIRE DU COLLECTEUR GEX S017
==============================================================================

Worker `py:` de la tbot factory (app/orchestrator/tbot-factory.py). Il décide
en Python pur — ZÉRO token — si le snapshot GEX pré-market S017 doit partir,
puis délègue le travail réel à l'outil de la stratégie :

    strategies/S017_ireland_gex/research/daily_snapshot.py

TROIS CONDITIONS, TOUTES REQUISES (sinon : exit 0, no-op SILENCIEUX)
---------------------------------------------------------------------
    1. jour ouvré US (lundi-vendredi — les jours fériés US ne sont pas
       exclus : un snapshot un jour férié est inoffensif, la chaîne CBOE
       existe et phase_a ne verra simplement pas de barres ; on ne tire pas
       un calendrier de bourse pour éviter ça) ;
    2. heure locale (Suisse) >= 14:55 — le pré-market US commence à 15:30 CH,
       on collecte juste avant. RATTRAPAGE INCLUS : la condition est « après
       14:55 », pas « à 14:55 » — une console démarrée à 19 h collecte à 19 h
       (daily_snapshot garde lui-même ses fichiers canoniques write-once) ;
    3. le snapshot CANONIQUE du jour est ABSENT
       (C:/db/tradingBot/S017/gex/SPY_gex_YYYY-MM-DD.csv) — s'il existe,
       le travail du jour est fait, on ne repasse pas.

La cadence (900 s au catalogue) fait le reste : entre 14:55 et le premier
succès, chaque tick tente ; après le succès, chaque tick est un no-op gratuit.

CODES DE SORTIE (contrat de la factory)
----------------------------------------
    0  passage effectué (y compris no-op « pas la fenêtre / déjà fait »)
    2  la collecte a échoué (réseau CBOE/yfinance, dépendance absente)
       — ressource externe indisponible, réessai au tick suivant
    (jamais 3/4 : ce wrapper ne touche à aucun scellé)

USAGE
-----
    python app/orchestrator/tbot-collecte-gex-s017.py            # un passage
    python app/orchestrator/tbot-collecte-gex-s017.py --dry-run  # décide, ne lance rien
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from core.paths import db_dir, project_root  # noqa: E402

# Le snapshot appartient à la STRATÉGIE (cloisonnement) : ce wrapper ne fait
# que décider QUAND l'appeler. Le script cible garde ses propres défauts
# (--db-dir C:/db/tradingBot/S017) et sa propre protection write-once.
SNAPSHOT = project_root() / "strategies" / "S017_ireland_gex" / "research" / "daily_snapshot.py"

# Fenêtre horaire, surchargée par l'environnement pour les tests.
AFTER_LOCAL = os.environ.get("TBF_GEX_AFTER") or "14:55"
SNAPSHOT_TIMEOUT_S = int(os.environ.get("TBF_GEX_TIMEOUT") or 600)


def gex_dir() -> pathlib.Path:
    """Résolu à l'appel (testable via TBOT_DB_DIR sans toucher au code)."""
    return db_dir() / "S017" / "gex"


def should_collect(now: datetime, gdir: pathlib.Path,
                   after: str = AFTER_LOCAL) -> tuple[bool, str]:
    """La décision, pure et testable : (collecter ?, raison).

    POURQUOI une fonction pure : la fenêtre horaire est LA logique de ce
    wrapper — la tester ne doit exiger ni mock de datetime.now ni disque réel,
    juste un `datetime` et un dossier fabriqués."""
    if now.weekday() >= 5:                       # samedi=5, dimanche=6
        return False, "week-end — marché US fermé"
    try:
        hh, mm = (int(x) for x in after.split(":"))
    except ValueError:
        hh, mm = 14, 55                          # garde-fou : fenêtre par défaut
    if (now.hour, now.minute) < (hh, mm):
        return False, f"avant {after} heure locale — le pré-market US attendra"
    canonical = gdir / f"SPY_gex_{now.strftime('%Y-%m-%d')}.csv"
    if canonical.exists():
        return False, f"snapshot canonique du jour déjà présent ({canonical.name})"
    return True, "jour ouvré US, fenêtre atteinte, snapshot du jour absent"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fenêtre horaire du snapshot GEX S017 — délègue à daily_snapshot.py.")
    ap.add_argument("--dry-run", action="store_true",
                    help="décide et affiche, ne lance pas la collecte")
    a = ap.parse_args()

    go, raison = should_collect(datetime.now(), gex_dir())
    if not go:
        # No-op SILENCIEUX voulu (contrat du ticket TCK-005) : à 96 ticks/jour,
        # le moindre print noierait la console de la factory sous du rien.
        if a.dry_run:
            print(f"[dry-run] pas de collecte : {raison}")
        return 0

    if a.dry_run:
        print(f"[dry-run] collecte DUE ({raison}) — lancerait : {SNAPSHOT}")
        return 0

    if not SNAPSHOT.exists():
        print(f"daily_snapshot.py INTROUVABLE : {SNAPSHOT}", file=sys.stderr)
        return 2

    print(f"collecte GEX S017 ({raison})")
    try:
        cp = subprocess.run([sys.executable, str(SNAPSHOT)],
                            cwd=str(SNAPSHOT.parent),
                            timeout=SNAPSHOT_TIMEOUT_S, check=False)
    except subprocess.TimeoutExpired:
        print(f"snapshot : timeout après {SNAPSHOT_TIMEOUT_S}s — réessai au "
              f"prochain tick", file=sys.stderr)
        return 2
    except OSError as e:  # noqa: BLE001
        print(f"snapshot : lancement impossible ({type(e).__name__})", file=sys.stderr)
        return 2

    if cp.returncode != 0:
        # La cause précise (CBOE injoignable, yfinance vide, lib absente) est
        # dans la sortie du snapshot lui-même, déjà dans le log du tick.
        print(f"snapshot : sortie {cp.returncode} — ressource externe "
              f"indisponible, réessai au prochain tick", file=sys.stderr)
        return 2
    print("snapshot GEX S017 : OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
