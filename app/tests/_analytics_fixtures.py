"""
Fixtures du moteur d'analyse (SPEC_analytics-trades §8) — jeu J5 et
générateurs synthétiques, SANS conftest : les tests de ``analytics.py`` sont
purs (aucun disque, aucun seam), et conftest est édité par un autre acteur.

  - ``make_row(...)``      : une ligne brute au format Ledger.closed_trades()
  - ``j5_rows()``          : le jeu de référence J5 (§8), normalisé
  - ``synthetic_rows(n)``  : n trades à R connu, déterministes (Sharpe)
  - ``FakeSources``        : l'objet ``sources`` injectable de build_*
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server.analytics import normalize_rows  # noqa: E402

J5_BASE = 1000.0

# Août 2026 : le 3 est un lundi (3 lun, 4 mar, 5 mer, 8 sam, 9 dim — la spec
# dit « lun, mar, mer, lun, mar » pour les jours 3, 4, 5, 8, 9 : ce sont les
# mêmes trades, seul l'étiquetage calendaire diffère ; les tests jour de
# semaine posent leurs propres dates).
J5_NETS = (100.0, -50.0, 0.0, 30.0, -20.0)
J5_R = (2.0, -1.0, 0.0, 0.6, -0.4)
J5_DAYS = (3, 4, 5, 8, 9)
J5_SIDES = ("LONG", "SHORT", "LONG", "LONG", "SHORT")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_iso(value) -> str:
    return iso(value) if isinstance(value, datetime) else str(value)


def make_row(*, net: float, close, open_time=None, pnl_r="auto",
             strategy: str = "S011", instance: str | None = "S011.XAU-USD",
             symbol: str = "XAUUSD", side: str = "LONG", mode: str = "PAPER",
             currency: str = "CHF", exit_reason: str = "TP",
             magic: int = 130011, risk: float | None = 100.0,
             run_id: str | None = "gold_forward", ticket=None, rid=None,
             source_ref=None, arm: str | None = None, meta: dict | None = None,
             commission: float = 0.0, swap: float = 0.0,
             account_balance: float | None = None,
             edge_cost: float | None = None) -> dict:
    """Une ligne BRUTE (meta_json encodé en texte comme le ledger).
    ``pnl_r="auto"`` = laisse normalize_rows dériver net / risk_amount."""
    close_iso = _as_iso(close)
    if open_time is None:
        close_dt = datetime.fromisoformat(close_iso.replace("Z", "+00:00"))
        open_iso = iso(close_dt - timedelta(hours=2))
    else:
        open_iso = _as_iso(open_time)
    m = dict(meta or {})
    if pnl_r != "auto":
        m["pnl_r"] = pnl_r
    if arm is not None:
        m["arm"] = arm
    if edge_cost is not None:
        m["edge_cost_ccy"] = edge_cost
    row = {
        "id": rid, "strategy_id": strategy, "instance_id": instance,
        "strategy_version": "1.0", "magic_number": magic, "mode": mode,
        "run_id": run_id, "symbol": symbol, "timeframe": "H1",
        "ticket": ticket, "side": side, "volume_lots": 0.1,
        "open_time": open_iso, "open_price": 100.0, "close_time": close_iso,
        "close_price": 101.0, "stop_price": 99.0, "target_price": 102.0,
        "exit_reason": exit_reason, "gross_pnl": net + commission + swap,
        "commission": commission, "swap": swap, "net_pnl": net,
        "currency": currency, "signal_reason": None, "confidence": None,
        "risk_distance": 1.0, "risk_amount": risk,
        "account_balance": account_balance,
        "meta_json": json.dumps(m) if m else None,
        "created_at": "2026-08-01T00:00:00Z",
    }
    if source_ref is not None:
        row["source_ref"] = source_ref
    return row


def j5_raw(**over) -> list[dict]:
    """Les 5 lignes brutes de J5 (clôtures à 10:00Z les 3, 4, 5, 8, 9 août)."""
    rows = []
    for i, (net, r, day, side) in enumerate(zip(J5_NETS, J5_R, J5_DAYS,
                                                J5_SIDES), start=1):
        rows.append(make_row(net=net, pnl_r=r, side=side, rid=i, risk=50.0,
                             close=f"2026-08-{day:02d}T10:00:00Z",
                             account_balance=J5_BASE, **over))
    return rows


def j5_rows(**over) -> list[dict]:
    """J5 normalisé (§3.1) — prêt pour kpi / curve / summary."""
    return normalize_rows(j5_raw(**over), "ledger")


def synthetic_rows(n: int = 40, *, start="2026-01-05T10:00:00Z",
                   step_days: float = 3.0, **over) -> list[dict]:
    """n trades déterministes à R connu : R = +1,5 / −1 / +0,5 / −0,7 en
    boucle, net = 100 × R, un trade tous les ``step_days`` jours."""
    pattern = (1.5, -1.0, 0.5, -0.7)
    t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
    raws = []
    for i in range(n):
        r = pattern[i % len(pattern)]
        raws.append(make_row(net=100.0 * r, pnl_r=r, rid=i + 1,
                             close=t0 + timedelta(days=step_days * i), **over))
    return normalize_rows(raws, "ledger")


class FakeSources:
    """Sources injectables : listes brutes en entrée, rien sur disque.
    ``ledger=None`` simule un ledger absent."""

    def __init__(self, *, ledger=None, journals=(), open_ledger=(),
                 open_journals=(), capital=None, report=None, manifests=None,
                 allocated=None):
        self._ledger = ledger
        self._journals = list(journals)
        self._open_ledger = list(open_ledger)
        self._open_journals = list(open_journals)
        self._capital = dict(capital or {})
        self._report = report if report is not None else {"studies": {},
                                                          "warnings": []}
        self._manifests = dict(manifests or {})
        self._allocated = dict(allocated or {})
        self.calls: list[str] = []

    def closed_rows_ledger(self):
        self.calls.append("closed_rows_ledger")
        return None if self._ledger is None else list(self._ledger)

    def open_rows_ledger(self):
        self.calls.append("open_rows_ledger")
        return None if self._ledger is None else list(self._open_ledger)

    def closed_rows_journals(self):
        self.calls.append("closed_rows_journals")
        return list(self._journals)

    def open_rows_journals(self):
        self.calls.append("open_rows_journals")
        return list(self._open_journals)

    def capital_initial(self):
        self.calls.append("capital_initial")
        return dict(self._capital)

    def journal_report(self):
        self.calls.append("journal_report")
        return dict(self._report)

    def manifests(self):
        self.calls.append("manifests")
        return dict(self._manifests)

    def allocated_capital(self):
        self.calls.append("allocated_capital")
        return dict(self._allocated)


def journal_row(*, trade_id: str, study: str = "gold_forward", **over) -> dict:
    """Ligne telle que l'adaptateur la produirait (§3.2) — meta en dict."""
    row = make_row(run_id=study, source_ref=trade_id, **over)
    meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
    meta.setdefault("trade_id", trade_id)
    row["meta_json"] = meta
    row["source"] = "journal"
    return row
