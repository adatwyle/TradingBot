"""
Scaffolding — crée un dossier de stratégie complet depuis le gabarit.

    python tools/new_strategy.py --id s03_foo --name "Foo" --trader "X" \
        --source "https://..." --magic 130003

Génère l'arborescence, le CLAUDE.md du Claude dédié, le manifest et un
strategy.py qui refuse de tourner tant qu'il n'est pas implémenté (pour qu'une
stratégie vide ne puisse jamais être confondue avec une stratégie neutre).
"""
import argparse
import os
import re
import sys
from datetime import date

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/
# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
sys.path.insert(0, APP_DIR)
from core.paths import project_root  # noqa: E402

# Les stratégies vivent à la RACINE PROJET, pas dans app/ (résolution unique
# core/paths.py, seam TBOT_PROJECT_ROOT).
ROOT = str(project_root())
TEMPLATE = os.path.join(ROOT, "strategies", "_TEMPLATE", "CLAUDE.md")


MANIFEST = """# Manifest — {name}
# Lu par la plateforme (dashboard, orchestrateur, backtester).
# R7 : ce fichier est la seule source de vérité sur cette stratégie.

strategy_id: {sid}
display_name: "{name}"
version: "0.1.0"
magic_number: {magic}
author: "claude:{sid}"
source: "{source}"
trader: "{trader}"

status: RESEARCH        # RESEARCH | BACKTESTED | PAPER | LIVE | RETIRED

symbols: []             # à remplir après l'analyse — quels instruments ?
timeframe: ""           # H1 | H4 | M5 | D1
warmup_bars: 0

default_params: {{}}
param_grid: {{}}

created: {today}
notes: |
  À remplir par le Claude dédié après la Phase 1.
"""


STRATEGY_STUB = '''"""
{name} — stratégie {sid}

Source : {source}
Trader : {trader}

STATUT : NON IMPLÉMENTÉE. Voir CLAUDE.md, Phase 1 avant d'écrire du code.
"""
from typing import Optional

import pandas as pd

from core.contracts.strategy import (
    StrategyModule, StrategyManifest, Signal, MarketContext,
)


class Strategy(StrategyModule):
    STRATEGY_ID = "{sid}"
    MAGIC_NUMBER = {magic}

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="{name}",
            version="0.1.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:{sid}",
            source="{source}",
            symbols=[],          # Phase 1
            timeframe="",        # Phase 1
            warmup_bars=0,
            param_grid={{}},
            default_params={{}},
            status="RESEARCH",
        )

    def precompute(self, df: pd.DataFrame, params: dict):
        raise NotImplementedError(
            "{sid} n'est pas implémentée. Fais la Phase 1 (research/ANALYSIS.md) "
            "avant d'écrire du code."
        )

    def generate_signals(self, data, params: dict, end_idx: int) -> list[Signal]:
        raise NotImplementedError("{sid} : voir CLAUDE.md Phase 2")

    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        raise NotImplementedError("{sid} : voir CLAUDE.md Phase 2")
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--trader", default="—")
    ap.add_argument("--source", default="—")
    ap.add_argument("--magic", required=True, type=int)
    a = ap.parse_args()

    if not re.fullmatch(r"s\d{2}_[a-z0-9_]+", a.id):
        raise SystemExit(f"id invalide '{a.id}' — attendu sNN_slug_minuscules")

    d = os.path.join(ROOT, "strategies", a.id)
    if os.path.exists(d):
        raise SystemExit(f"{d} existe déjà")

    for sub in ("", "research", "backtests"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)

    with open(TEMPLATE, encoding="utf-8") as f:
        claude_md = f.read()
    claude_md = (claude_md
                 .replace("{{STRATEGY_ID}}", a.id)
                 .replace("{{SOURCE}}", a.source)
                 .replace("{{TRADER}}", a.trader))

    files = {
        "CLAUDE.md": claude_md,
        "manifest.yaml": MANIFEST.format(sid=a.id, name=a.name, magic=a.magic,
                                         source=a.source, trader=a.trader,
                                         today=date.today().isoformat()),
        "strategy.py": STRATEGY_STUB.format(sid=a.id, name=a.name,
                                            source=a.source, trader=a.trader,
                                            magic=a.magic),
        "research/ANALYSIS.md": f"# Analyse — {a.name}\n\n"
                                f"Source : {a.source}\nTrader : {a.trader}\n\n"
                                "> À rédiger en Phase 1. Voir CLAUDE.md.\n",
        "__init__.py": "",
    }
    for rel, content in files.items():
        with open(os.path.join(d, rel), "w", encoding="utf-8") as f:
            f.write(content)

    print(f"[OK] {a.id} créée : {d}")
    print(f"     magic {a.magic} — pense à l'inscrire dans core/contracts/MAGIC_REGISTRY.md")


if __name__ == "__main__":
    main()
