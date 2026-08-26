"""
core/ledger — single source of truth for results (SPEC_ledger.md).

Public API: the ``Ledger`` class (held connection, short transactions)
plus module-level convenience functions for one-shot writes.  No module
opens the SQLite file directly — everything goes through this package
(LG-15).
"""
from core.ledger.ledger import (
    EVENT_TYPES,
    EXIT_REASONS,
    Ledger,
    MODES,
    SCHEMA_VERSION,
    SIDES,
    close_trade,
    open_trade,
    record_equity_snapshot,
    record_risk_event,
    record_trade,
)

__all__ = [
    "Ledger",
    "MODES",
    "SIDES",
    "EXIT_REASONS",
    "EVENT_TYPES",
    "SCHEMA_VERSION",
    "open_trade",
    "close_trade",
    "record_trade",
    "record_equity_snapshot",
    "record_risk_event",
]
