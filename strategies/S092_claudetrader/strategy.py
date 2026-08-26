"""
ClaudeTrader - agent headless cyclique — stratégie s92_claudetrader

Source : https://www.youtube.com/watch?v=lIMu8ysJW68
Trader : AI Pathways (concept Hermes) / adaptation Claude Code

STATUT : NON IMPLÉMENTÉE. Voir CLAUDE.md, Phase 1 avant d'écrire du code.
"""
from typing import Optional

import pandas as pd

from core.contracts.strategy import (
    StrategyModule, StrategyManifest, Signal, MarketContext,
)


class Strategy(StrategyModule):
    STRATEGY_ID = "s92_claudetrader"
    MAGIC_NUMBER = 130092

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="ClaudeTrader - agent headless cyclique",
            version="0.1.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s92_claudetrader",
            source="https://www.youtube.com/watch?v=lIMu8ysJW68",
            symbols=[],          # Phase 1
            timeframe="",        # Phase 1
            warmup_bars=0,
            param_grid={},
            default_params={},
            status="RESEARCH",
        )

    def precompute(self, df: pd.DataFrame, params: dict):
        raise NotImplementedError(
            "s92_claudetrader n'est pas implémentée. Fais la Phase 1 (research/ANALYSIS.md) "
            "avant d'écrire du code."
        )

    def generate_signals(self, data, params: dict, end_idx: int) -> list[Signal]:
        raise NotImplementedError("s92_claudetrader : voir CLAUDE.md Phase 2")

    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        raise NotImplementedError("s92_claudetrader : voir CLAUDE.md Phase 2")
