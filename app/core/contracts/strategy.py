"""
TBOT — STRATEGY MODULE CONTRACT
================================

Every strategy in `strategies/` MUST subclass `StrategyModule`. This contract is
what makes a strategy pluggable into the common backtester, the live
orchestrator, the risk layer, the ledger and the dashboard — without any of
those components knowing anything about the strategy's internals.

DESIGN PRINCIPLE — SEPARATION OF CONCERNS
------------------------------------------
    strategy  ->  decides DIRECTION and LEVELS  (signal, stop, target)
    risk      ->  decides SIZE                  (lots, exposure, kill-switch)
    broker    ->  decides EXECUTION             (order type, retries, slippage)
    ledger    ->  records EVERYTHING            (tax, audit, dashboard)

A strategy NEVER computes its own position size, NEVER reads the account
balance, NEVER decides whether it is allowed to trade. It answers one question:
"given this market state, do I want to be long or short, where is my
invalidation, and where is my objective?" Everything else belongs to the
platform.

This separation is what allows the dashboard to change a strategy's capital
allocation, or the supervisor to halt it, without touching strategy code.

WHY "SAME CODE BACKTEST AND LIVE"
----------------------------------
`generate_signals()` (vectorised, for the backtester) and `on_bar()` (live) must
produce IDENTICAL decisions for the same market state. The platform provides a
conformance test that runs both paths over historical data and asserts they
agree. A strategy whose live and backtest logic diverge is not admissible —
that divergence is the single most common source of "it worked in backtest".
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Value objects
# ─────────────────────────────────────────────────────────────────────────────

class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Mode(str, Enum):
    """Execution mode. The ledger records this so tax reporting can separate
    real activity from research activity."""
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"      # demo account, real-time
    LIVE = "LIVE"        # real money


@dataclass(frozen=True)
class Signal:
    """A strategy's decision at one bar.

    The strategy expresses intent in PRICE terms only. No lot size, no risk
    percentage, no account reference — the risk layer converts this into an
    executable order.
    """
    timestamp: datetime
    symbol: str
    side: Side
    entry: float              # intended entry price (usually current close)
    stop: float               # invalidation level — MANDATORY, never None
    target: Optional[float]   # objective; None = managed by trailing/exit rules
    reason: str               # human-readable, shown in the dashboard + journal
    confidence: float = 1.0   # 0..1, may modulate risk if the strategy supports it
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.stop is None:
            raise ValueError("Signal.stop is mandatory — set & forget is a platform rule")
        if self.side == Side.LONG and self.stop >= self.entry:
            raise ValueError(f"LONG stop {self.stop} must be below entry {self.entry}")
        if self.side == Side.SHORT and self.stop <= self.entry:
            raise ValueError(f"SHORT stop {self.stop} must be above entry {self.entry}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0, 1]")

    @property
    def risk_distance(self) -> float:
        """Absolute price distance to invalidation. The risk layer sizes on this."""
        return abs(self.entry - self.stop)

    @property
    def rr(self) -> Optional[float]:
        if self.target is None:
            return None
        return abs(self.target - self.entry) / self.risk_distance if self.risk_distance else None


@dataclass
class MarketContext:
    """What the platform hands a strategy on each live bar.

    NOTE the deliberate omissions: no balance, no equity, no open positions of
    OTHER strategies, no permission flag. A strategy cannot see, and therefore
    cannot react to, the portfolio around it. That isolation is what makes
    strategies independently testable.
    """
    symbol: str
    timeframe: str
    bars: pd.DataFrame          # OHLC(V) history up to and INCLUDING current closed bar
    now: datetime
    spread: float               # current spread in price units
    own_position: Optional[dict] = None   # this strategy's own open position, if any


@dataclass
class StrategyManifest:
    """Declarative metadata. The dashboard, orchestrator and backtester read
    this instead of hardcoding anything about the strategy."""
    strategy_id: str            # unique slug, must match folder name
    display_name: str
    version: str
    magic_number: int           # unique per strategy — MT5 position isolation
    author: str                 # "claude:s02_creamer_auction" | "adrian" | ...
    source: str                 # provenance: youtube URL, paper, "from scratch"
    symbols: list[str]          # instruments this strategy targets
    timeframe: str              # "H1", "H4", "M5", "D1"
    warmup_bars: int            # bars needed before first valid signal
    param_grid: dict[str, list] # search space for the common grid-search
    default_params: dict[str, Any]
    status: str = "RESEARCH"    # RESEARCH | BACKTESTED | PAPER | LIVE | RETIRED
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# The contract
# ─────────────────────────────────────────────────────────────────────────────

class StrategyModule(abc.ABC):
    """Base class every strategy must implement.

    Lifecycle:
        manifest()          -> platform discovers the strategy
        precompute(df, p)   -> heavy indicator work, done ONCE per (symbol, params)
        generate_signals()  -> backtest path (vectorised over history)
        on_bar(ctx)         -> live path (one decision per closed bar)

    See STRATEGY_RULES.md for the compatibility rules and the mandatory
    conformance tests.
    """

    # ── Identity (must be overridden) ────────────────────────────────────────
    STRATEGY_ID: str = ""
    MAGIC_NUMBER: int = 0

    def __init__(self, params: Optional[dict] = None):
        if not self.STRATEGY_ID:
            raise ValueError(f"{type(self).__name__} must define STRATEGY_ID")
        if not self.MAGIC_NUMBER:
            raise ValueError(f"{type(self).__name__} must define MAGIC_NUMBER")
        self.params = dict(self.manifest().default_params)
        if params:
            unknown = set(params) - set(self.params)
            if unknown:
                raise ValueError(f"unknown params for {self.STRATEGY_ID}: {sorted(unknown)}")
            self.params.update(params)

    # ── Declaration ──────────────────────────────────────────────────────────
    @abc.abstractmethod
    def manifest(self) -> StrategyManifest:
        """Static description of this strategy. Must be pure — no I/O, no state."""

    # ── Backtest path ────────────────────────────────────────────────────────
    @abc.abstractmethod
    def precompute(self, df: pd.DataFrame, params: dict) -> Any:
        """Compute every indicator the strategy needs, ONCE.

        Returns an opaque object handed back to `generate_signals`. The common
        backtester caches this per (symbol, params-that-affect-indicators), so
        expensive work (S/R levels, swing detection) is not repeated per grid cell.

        MUST be causal: value at index i may only depend on data at indices <= i.
        """

    @abc.abstractmethod
    def generate_signals(self, data: Any, params: dict, end_idx: int) -> list[Signal]:
        """Produce every signal the strategy would have taken over [0, end_idx).

        CRITICAL — the `end_idx` contract:
            Nothing at index >= end_idx may influence the output. Not the last
            close, not a residual position marked to the final price, nothing.

            The platform enforces this with the truncation invariant:

                generate_signals(precompute(df),      p, T)
                    ==
                generate_signals(precompute(df[:T]),  p, T)

            This exact bug (a residual trade closed at `closes[-1]` instead of
            `closes[n-1]`) silently contaminated months of this project's
            walk-forward results. The invariant test is mandatory, not optional.
        """

    # ── Live path ────────────────────────────────────────────────────────────
    @abc.abstractmethod
    def on_bar(self, ctx: MarketContext) -> Optional[Signal]:
        """One decision on one freshly-closed bar. Return None to stay flat.

        Must be a pure function of `ctx` and `self.params`. No hidden state
        between calls beyond what is reconstructible from `ctx` — the
        orchestrator may restart the process at any time and the strategy must
        behave identically.
        """

    # ── Optional hooks ───────────────────────────────────────────────────────
    def on_position_closed(self, trade: dict) -> None:
        """Notification only. May update internal counters (e.g. consecutive
        losses for the strategy's own cooldown). MUST NOT place orders."""
        return None

    def health(self) -> dict:
        """Optional diagnostics surfaced on the dashboard."""
        return {}
