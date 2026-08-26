"""
core/ledger/ledger.py — the ONE write/read path to the results ledger.
======================================================================

Implements SPEC_ledger.md v1.0.0 on top of the inherited schema.sql:
no strategy ever writes its own aggregates — every trade (BACKTEST,
PAPER, LIVE) lands here, and the dashboard, Telegram and the tax export
all read from here (LG-15).

Storage: SQLite in WAL mode. The file lives OUTSIDE the repo
(RULE_db-separation): resolution order is the ``TBOT_LEDGER_DB`` seam,
then ``db_dir()/"tradingbot.db"`` (default ``C:\\db\\tradingBot\\``).
The prototype path ``C:\\db\\tbot\\tbot.db`` mentioned in schema.sql's
header belongs to the system still in production and is NEVER used
(D-LG-1).

Schema versioning (D-LG-4): ``PRAGMA user_version`` + the ordered
``MIGRATIONS`` list.  v1 executes schema.sql (all CREATE IF NOT EXISTS,
hence idempotent), v2 adds the ``instance_id`` column to ``trades`` and
``equity_snapshots`` plus their indexes (D-LG-2).  Each step is guarded
so that a crash mid-migration simply re-runs cleanly at next open.

Conventions:
- ``strategy_id`` is the short canonical id ``S0NN`` (e.g. ``S013``),
  ``instance_id`` is ``S0NN.XXX-YYY`` (D-LG-3).
- Timestamps are stored ISO 8601 UTC with a ``Z`` suffix, second
  precision (D-LG-5).  Reporting converts to the LOCAL calendar at the
  edge (LG-11); the ``local_tz`` constructor argument is the
  deterministic-test seam (default: the machine's zone).
- Weeks are ISO weeks, computed Python-side via ``isocalendar()``
  (D-LG-6).
- Aggregates group per currency whenever several currencies coexist —
  never a silent cross-currency addition (LG-14).  Every aggregate row
  carries its ``currency``.
- Every write is a short auto-committed transaction (``with conn:``) —
  never a transaction held across calls (LG-9, WAL, several writers).

The ``strategy_state`` table is created by the schema but its piloting
stays out of scope here (LG-16 — future global risk layer, TCK-006).
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
from datetime import date, datetime, timezone, tzinfo
from typing import Any, Callable

from core.paths import db_dir

# ── Validated vocabularies (LG-3, LG-5, LG-8 — no silent default) ───────────
MODES = frozenset({"BACKTEST", "PAPER", "LIVE"})
SIDES = frozenset({"LONG", "SHORT"})            # schema contract: LONG | SHORT
EXIT_REASONS = frozenset({"SL", "TP", "TRAIL", "MANUAL", "HALT", "EOD"})
EVENT_TYPES = frozenset({"HALT", "RESUME", "SCALE_UP", "SCALE_DOWN",
                         "COOLDOWN", "DD_BREACH", "KILL_SWITCH"})

_SCHEMA_FILE = pathlib.Path(__file__).with_name("schema.sql")


# ── Small helpers ───────────────────────────────────────────────────────────
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_utc(value: datetime | str, field: str) -> str:
    """Normalize a caller timestamp to ISO 8601 UTC 'Z' (D-LG-5).

    Accepts a datetime (aware or naive — naive is taken as UTC) or an
    ISO 8601 string.  Anything else, or an unparseable string, raises
    ValueError: no silent default."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"{field}: not an ISO 8601 timestamp: {value!r}")
    else:
        raise ValueError(f"{field}: expected datetime or ISO string, "
                         f"got {type(value).__name__}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check(value: str, vocab: frozenset[str], field: str) -> str:
    if value not in vocab:
        raise ValueError(f"{field}={value!r} invalid — expected one of "
                         f"{sorted(vocab)}")
    return value


def _check_stop(stop_price: Any) -> float:
    """R3: never a trade without a stop — None and 0 both refused."""
    if stop_price is None or float(stop_price) == 0.0:
        raise ValueError("stop_price is mandatory and non-null (R3: "
                         "never a trade without a stop)")
    return float(stop_price)


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column
               for row in conn.execute(f"PRAGMA table_info({table})"))


def _as_local_date_str(value: str | date | None, field: str) -> str | None:
    """Normalize a local-date filter bound to 'YYYY-MM-DD'."""
    if value is None:
        return None
    if isinstance(value, datetime):        # datetime is a date subclass
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{field}: not a YYYY-MM-DD date: {value!r}")


# ── Migrations (D-LG-4) ─────────────────────────────────────────────────────
def _migrate_v1(conn: sqlite3.Connection) -> None:
    """v1 — the inherited schema.sql, read from the package.

    The script is 100% CREATE IF NOT EXISTS, so it is idempotent: a DB
    created by hand from schema.sql (user_version 0) passes through this
    step without loss (LG-T2)."""
    conn.executescript(_SCHEMA_FILE.read_text(encoding="utf-8"))


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """v2 — instance_id becomes first-class on trades and equity_snapshots
    (D-LG-2), plus the two indexes of LG-2.  Column adds are guarded so
    the step is idempotent (crash-safe re-run)."""
    if not _has_column(conn, "trades", "instance_id"):
        conn.execute("ALTER TABLE trades ADD COLUMN instance_id TEXT")
    if not _has_column(conn, "equity_snapshots", "instance_id"):
        conn.execute("ALTER TABLE equity_snapshots ADD COLUMN instance_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_instance "
                 "ON trades(instance_id, mode)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_equity_instance "
                 "ON equity_snapshots(instance_id, mode, timestamp)")


MIGRATIONS: list[Callable[[sqlite3.Connection], None]] = [
    _migrate_v1,   # -> user_version 1
    _migrate_v2,   # -> user_version 2
]

SCHEMA_VERSION = len(MIGRATIONS)


# ── The ledger ──────────────────────────────────────────────────────────────
class Ledger:
    """Held connection + short transactions (D-LG-5).

    ``db_path``: explicit path (tests), else ``TBOT_LEDGER_DB`` env seam,
    else ``db_dir()/"tradingbot.db"`` (LG-1).
    ``local_tz``: timezone used by the local-calendar reporting (LG-11);
    default None = the machine's local zone.  Injection seam for
    deterministic tests."""

    def __init__(self, db_path: pathlib.Path | str | None = None, *,
                 local_tz: tzinfo | None = None) -> None:
        if db_path is None:
            env = os.environ.get("TBOT_LEDGER_DB")
            db_path = pathlib.Path(env) if env else db_dir() / "tradingbot.db"
        self.db_path = pathlib.Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local_tz = local_tz
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._apply_migrations()

    # -- lifecycle ----------------------------------------------------------
    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Ledger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- schema (LG-2) ------------------------------------------------------
    def _apply_migrations(self) -> None:
        current = self._conn.execute("PRAGMA user_version").fetchone()[0]
        for version, migrate in enumerate(MIGRATIONS, start=1):
            if version <= current:
                continue
            migrate(self._conn)
            # PRAGMA does not accept bound parameters; version is an int
            # from enumerate, not user input.
            self._conn.execute(f"PRAGMA user_version = {version}")
            self._conn.commit()

    @property
    def user_version(self) -> int:
        return self._conn.execute("PRAGMA user_version").fetchone()[0]

    # -- writes (LG-4..LG-9) ------------------------------------------------
    def open_trade(self, *, strategy_id: str, instance_id: str,
                   strategy_version: str, magic_number: int, mode: str,
                   symbol: str, timeframe: str, side: str,
                   volume_lots: float, open_time: datetime | str,
                   open_price: float, stop_price: float,
                   target_price: float | None = None,
                   run_id: str | None = None, ticket: int | None = None,
                   signal_reason: str | None = None,
                   confidence: float | None = None,
                   risk_distance: float | None = None,
                   risk_amount: float | None = None,
                   account_balance: float | None = None,
                   currency: str = "CHF",
                   meta: dict | None = None) -> int:
        """LG-4 — insert an OPEN position; returns the ledger row id."""
        _check(mode, MODES, "mode")
        _check(side, SIDES, "side")
        stop = _check_stop(stop_price)
        with self._conn:
            cur = self._conn.execute(
                """INSERT INTO trades (strategy_id, instance_id,
                       strategy_version, magic_number, mode, run_id, symbol,
                       timeframe, ticket, side, volume_lots, open_time,
                       open_price, stop_price, target_price, signal_reason,
                       confidence, risk_distance, risk_amount,
                       account_balance, currency, meta_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (strategy_id, instance_id, strategy_version,
                 int(magic_number), mode, run_id, symbol, timeframe, ticket,
                 side, float(volume_lots), _iso_utc(open_time, "open_time"),
                 float(open_price), stop, target_price, signal_reason,
                 confidence, risk_distance, risk_amount, account_balance,
                 currency, json.dumps(meta) if meta is not None else None))
            return int(cur.lastrowid)

    def close_trade(self, trade_id: int, *, close_time: datetime | str,
                    close_price: float, exit_reason: str, gross_pnl: float,
                    commission: float = 0.0, swap: float = 0.0) -> None:
        """LG-5 — close an open trade; stores the gross/commission/swap/net
        decomposition (the net alone is not enough for the tax trail)."""
        _check(exit_reason, EXIT_REASONS, "exit_reason")
        net = float(gross_pnl) - float(commission) - float(swap)
        with self._conn:
            row = self._conn.execute(
                "SELECT close_time FROM trades WHERE id = ?",
                (trade_id,)).fetchone()
            if row is None:
                raise ValueError(f"trade {trade_id}: unknown id")
            if row["close_time"] is not None:
                raise ValueError(f"trade {trade_id}: already closed at "
                                 f"{row['close_time']}")
            self._conn.execute(
                """UPDATE trades SET close_time = ?, close_price = ?,
                       exit_reason = ?, gross_pnl = ?, commission = ?,
                       swap = ?, net_pnl = ?
                   WHERE id = ?""",
                (_iso_utc(close_time, "close_time"), float(close_price),
                 exit_reason, float(gross_pnl), float(commission),
                 float(swap), net, trade_id))

    def record_trade(self, *, close_time: datetime | str, close_price: float,
                     exit_reason: str, gross_pnl: float,
                     commission: float = 0.0, swap: float = 0.0,
                     **open_fields) -> int:
        """LG-6 — an already-closed trade in ONE call (backtest/bulk path).
        Same validations as open_trade + close_trade, single insert."""
        _check(open_fields.get("mode"), MODES, "mode")
        _check(open_fields.get("side"), SIDES, "side")
        _check(exit_reason, EXIT_REASONS, "exit_reason")
        _check_stop(open_fields.get("stop_price"))
        net = float(gross_pnl) - float(commission) - float(swap)
        meta = open_fields.pop("meta", None)
        with self._conn:
            cur = self._conn.execute(
                """INSERT INTO trades (strategy_id, instance_id,
                       strategy_version, magic_number, mode, run_id, symbol,
                       timeframe, ticket, side, volume_lots, open_time,
                       open_price, stop_price, target_price, signal_reason,
                       confidence, risk_distance, risk_amount,
                       account_balance, currency, meta_json,
                       close_time, close_price, exit_reason,
                       gross_pnl, commission, swap, net_pnl)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                           ?,?,?,?,?,?,?)""",
                (open_fields["strategy_id"], open_fields["instance_id"],
                 open_fields["strategy_version"],
                 int(open_fields["magic_number"]), open_fields["mode"],
                 open_fields.get("run_id"), open_fields["symbol"],
                 open_fields["timeframe"], open_fields.get("ticket"),
                 open_fields["side"], float(open_fields["volume_lots"]),
                 _iso_utc(open_fields["open_time"], "open_time"),
                 float(open_fields["open_price"]),
                 float(open_fields["stop_price"]),
                 open_fields.get("target_price"),
                 open_fields.get("signal_reason"),
                 open_fields.get("confidence"),
                 open_fields.get("risk_distance"),
                 open_fields.get("risk_amount"),
                 open_fields.get("account_balance"),
                 open_fields.get("currency", "CHF"),
                 json.dumps(meta) if meta is not None else None,
                 _iso_utc(close_time, "close_time"), float(close_price),
                 exit_reason, float(gross_pnl), float(commission),
                 float(swap), net))
            return int(cur.lastrowid)

    def record_equity_snapshot(self, *, strategy_id: str, instance_id: str,
                               mode: str, equity: float,
                               open_pnl: float = 0.0,
                               drawdown_pct: float | None = None,
                               timestamp: datetime | str | None = None
                               ) -> None:
        """LG-7 — one equity point; timestamp defaults to now UTC."""
        _check(mode, MODES, "mode")
        ts = _utc_now_iso() if timestamp is None else _iso_utc(timestamp,
                                                               "timestamp")
        with self._conn:
            self._conn.execute(
                """INSERT INTO equity_snapshots (timestamp, strategy_id,
                       instance_id, mode, equity, open_pnl, drawdown_pct)
                   VALUES (?,?,?,?,?,?,?)""",
                (ts, strategy_id, instance_id, mode, float(equity),
                 float(open_pnl), drawdown_pct))

    def record_risk_event(self, *, event_type: str, trigger: str,
                          strategy_id: str | None = None,
                          value_before: float | None = None,
                          value_after: float | None = None,
                          detail: dict | None = None) -> None:
        """LG-8 — trace of an automatic supervisor decision."""
        _check(event_type, EVENT_TYPES, "event_type")
        with self._conn:
            self._conn.execute(
                """INSERT INTO risk_events (timestamp, strategy_id,
                       event_type, trigger, value_before, value_after,
                       detail_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (_utc_now_iso(), strategy_id, event_type, trigger,
                 value_before, value_after,
                 json.dumps(detail) if detail is not None else None))

    # -- reads (LG-10..LG-13) -----------------------------------------------
    def _to_local(self, iso_utc: str) -> datetime:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self._local_tz)

    def closed_trades(self, *, strategy_id: str | None = None,
                      instance_id: str | None = None,
                      mode: str | None = None,
                      date_from: str | date | None = None,
                      date_to: str | date | None = None,
                      limit: int | None = None) -> list[dict]:
        """LG-10 — closed trades sorted by close_time, every column.

        ``date_from``/``date_to`` are LOCAL dates (YYYY-MM-DD, inclusive)
        — the same reader-calendar convention as the LG-11 aggregates."""
        sql = "SELECT * FROM trades WHERE close_time IS NOT NULL"
        args: list = []
        if strategy_id is not None:
            sql += " AND strategy_id = ?"
            args.append(strategy_id)
        if instance_id is not None:
            sql += " AND instance_id = ?"
            args.append(instance_id)
        if mode is not None:
            sql += " AND mode = ?"
            args.append(_check(mode, MODES, "mode"))
        sql += " ORDER BY close_time, id"
        rows = [dict(r) for r in self._conn.execute(sql, args)]
        d_from = _as_local_date_str(date_from, "date_from")
        d_to = _as_local_date_str(date_to, "date_to")
        if d_from or d_to:
            kept = []
            for r in rows:
                local_day = self._to_local(r["close_time"]).date().isoformat()
                if d_from and local_day < d_from:
                    continue
                if d_to and local_day > d_to:
                    continue
                kept.append(r)
            rows = kept
        if limit is not None:
            rows = rows[:int(limit)]
        return rows

    def _aggregate(self, key_of: Callable[[datetime], str], label: str,
                   date_from, date_to, strategy_id, instance_id,
                   mode) -> list[dict]:
        """LG-11/LG-14 — bucket closed trades by a LOCAL-calendar period.

        Buckets are per (period, currency): whenever several currencies
        coexist the rows split per currency — never a silent
        cross-currency addition.  Every row carries its currency."""
        trades = self.closed_trades(strategy_id=strategy_id,
                                    instance_id=instance_id, mode=mode,
                                    date_from=date_from, date_to=date_to)
        buckets: dict[tuple[str, str], dict] = {}
        for t in trades:
            key = key_of(self._to_local(t["close_time"]))
            cur = t["currency"]
            b = buckets.setdefault((key, cur), {
                label: key, "currency": cur, "n_trades": 0,
                "gross": 0.0, "commission": 0.0, "swap": 0.0, "net": 0.0})
            b["n_trades"] += 1
            b["gross"] += t["gross_pnl"] or 0.0
            b["commission"] += t["commission"] or 0.0
            b["swap"] += t["swap"] or 0.0
            b["net"] += t["net_pnl"] or 0.0
        out = []
        for (key, cur) in sorted(buckets):
            b = buckets[(key, cur)]
            for f in ("gross", "commission", "swap", "net"):
                b[f] = round(b[f], 2)
            out.append(b)
        return out

    def pnl_by_day(self, date_from=None, date_to=None, *,
                   strategy_id: str | None = None,
                   instance_id: str | None = None,
                   mode: str | None = None) -> list[dict]:
        return self._aggregate(lambda d: d.date().isoformat(), "day",
                               date_from, date_to, strategy_id, instance_id,
                               mode)

    def pnl_by_week(self, date_from=None, date_to=None, *,
                    strategy_id: str | None = None,
                    instance_id: str | None = None,
                    mode: str | None = None) -> list[dict]:
        """ISO week (D-LG-6): 'YYYY-Www', Monday-Sunday, computed via
        isocalendar() — the ISO year may differ from the calendar year at
        the year boundary, and that is the point."""
        def iso_week(d: datetime) -> str:
            y, w, _ = d.date().isocalendar()
            return f"{y}-W{w:02d}"
        return self._aggregate(iso_week, "week", date_from, date_to,
                               strategy_id, instance_id, mode)

    def pnl_by_month(self, date_from=None, date_to=None, *,
                     strategy_id: str | None = None,
                     instance_id: str | None = None,
                     mode: str | None = None) -> list[dict]:
        return self._aggregate(lambda d: d.date().isoformat()[:7], "month",
                               date_from, date_to, strategy_id, instance_id,
                               mode)

    def pnl_by_year(self, date_from=None, date_to=None, *,
                    strategy_id: str | None = None,
                    instance_id: str | None = None,
                    mode: str | None = None) -> list[dict]:
        return self._aggregate(lambda d: f"{d.year:04d}", "year",
                               date_from, date_to, strategy_id, instance_id,
                               mode)

    def day_trades(self, day: str | date, *,
                   strategy_id: str | None = None,
                   instance_id: str | None = None,
                   mode: str | None = None) -> list[dict]:
        """LG-11 — the LOCAL day's closed trades, Telegram-ready."""
        day_str = _as_local_date_str(day, "day")
        rows = self.closed_trades(strategy_id=strategy_id,
                                  instance_id=instance_id, mode=mode,
                                  date_from=day_str, date_to=day_str)
        return [{"close_time_local":
                 self._to_local(r["close_time"]).strftime("%H:%M"),
                 "instance_id": r["instance_id"],
                 "exit_reason": r["exit_reason"],
                 "net_pnl": r["net_pnl"]} for r in rows]

    def equity_curve(self, *, strategy_id: str,
                     instance_id: str | None = None,
                     mode: str | None = None,
                     limit: int = 2000) -> list[tuple[str, float]]:
        """LG-12 — the most recent ``limit`` points, chronological order."""
        sql = ("SELECT timestamp, equity FROM equity_snapshots "
               "WHERE strategy_id = ?")
        args: list = [strategy_id]
        if instance_id is not None:
            sql += " AND instance_id = ?"
            args.append(instance_id)
        if mode is not None:
            sql += " AND mode = ?"
            args.append(_check(mode, MODES, "mode"))
        sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        args.append(int(limit))
        rows = self._conn.execute(sql, args).fetchall()
        return [(r["timestamp"], r["equity"]) for r in reversed(rows)]

    def tax_detail(self, year: int | str) -> list[dict]:
        """LG-13 — plain SELECT of the inherited v_tax_detail view."""
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM v_tax_detail WHERE tax_year = ?", (str(year),))]

    def tax_summary(self, year: int | str) -> list[dict]:
        """LG-13 — plain SELECT of the inherited v_tax_summary view."""
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM v_tax_summary WHERE tax_year = ?", (str(year),))]


# ── Module-level convenience functions (D-LG-5) ─────────────────────────────
# One short-lived Ledger per call: for callers that write a single record
# and do not want to hold a connection.  ``db_path`` is the same seam as
# the constructor.
def open_trade(*, db_path=None, **kwargs) -> int:
    with Ledger(db_path) as ledger:
        return ledger.open_trade(**kwargs)


def close_trade(trade_id: int, *, db_path=None, **kwargs) -> None:
    with Ledger(db_path) as ledger:
        ledger.close_trade(trade_id, **kwargs)


def record_trade(*, db_path=None, **kwargs) -> int:
    with Ledger(db_path) as ledger:
        return ledger.record_trade(**kwargs)


def record_equity_snapshot(*, db_path=None, **kwargs) -> None:
    with Ledger(db_path) as ledger:
        ledger.record_equity_snapshot(**kwargs)


def record_risk_event(*, db_path=None, **kwargs) -> None:
    with Ledger(db_path) as ledger:
        ledger.record_risk_event(**kwargs)
