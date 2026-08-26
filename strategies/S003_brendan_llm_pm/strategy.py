"""
Brendan - Claude comme gerant de portefeuille — stratégie s03_brendan_llm_pm

Source : https://www.youtube.com/watch?v=RetsRS5u-8Q
Trader : Brendan (AI trading, ex-Raymond James)

STATUT : NON IMPLÉMENTÉE. Voir CLAUDE.md, Phase 1 avant d'écrire du code.
"""
from typing import Optional

import pandas as pd

from core.contracts.strategy import (
    StrategyModule, StrategyManifest, Signal, MarketContext,
)


class Strategy(StrategyModule):
    STRATEGY_ID = "s03_brendan_llm_pm"
    MAGIC_NUMBER = 130003

    def manifest(self) -> StrategyManifest:
        return StrategyManifest(
            strategy_id=self.STRATEGY_ID,
            display_name="Brendan - Claude comme gerant de portefeuille",
            version="0.1.0",
            magic_number=self.MAGIC_NUMBER,
            author="claude:s03_brendan_llm_pm",
            source="https://www.youtube.com/watch?v=RetsRS5u-8Q",
            symbols=[],          # Phase 1
            timeframe="",        # Phase 1
            warmup_bars=0,
            param_grid={},
            default_params={},
            status="RESEARCH",
        )

    def precompute(self, df: pd.DataFrame, params: dict):
        raise NotImplementedError(
            "s03_brendan_llm_pm n'est pas implémentée. Fais la Phase 1 (research/ANALYSIS.md) "
            "avant d'écrire du code."
        )

    def generate_signals(self, data, params: dict, end_idx: int) -> list[Signal]:
        raise NotImplementedError("s03_brendan_llm_pm : voir CLAUDE.md Phase 2")

    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        raise NotImplementedError("s03_brendan_llm_pm : voir CLAUDE.md Phase 2")
