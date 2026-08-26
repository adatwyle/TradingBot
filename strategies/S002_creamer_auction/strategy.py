"""
Creamer Auction/Orderflow — stratégie s02_creamer_auction

Source : https://www.youtube.com/watch?v=PL7LKUsCgIQ
Trader : Chris Creamer - Robbins World Cup 2026

STATUT : NON IMPLÉMENTÉE. Voir CLAUDE.md, Phase 1 avant d'écrire du code.
"""
from typing import Optional

import pandas as pd

from core.contracts.strategy import (
    StrategyModule, StrategyManifest, Signal, MarketContext,
)


class Strategy(StrategyModule):
    STRATEGY_ID = "s02_creamer_auction"
    MAGIC_NUMBER = 130002

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Creamer Auction/Orderflow",
            version="0.1.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s02_creamer_auction",
            source="https://www.youtube.com/watch?v=PL7LKUsCgIQ",
            symbols=[],          # Phase 1
            timeframe="",        # Phase 1
            warmup_bars=0,
            param_grid={},
            default_params={},
            status="RESEARCH",
        )

    def precompute(self, df: pd.DataFrame, params: dict):
        raise NotImplementedError(
            "s02_creamer_auction n'est pas implémentée. Fais la Phase 1 (research/ANALYSIS.md) "
            "avant d'écrire du code."
        )

    def generate_signals(self, data, params: dict, end_idx: int) -> list[Signal]:
        raise NotImplementedError("s02_creamer_auction : voir CLAUDE.md Phase 2")

    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        raise NotImplementedError("s02_creamer_auction : voir CLAUDE.md Phase 2")
