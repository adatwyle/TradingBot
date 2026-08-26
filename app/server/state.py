"""
server/state.py — strategy discovery + performance contract (SPEC_ui-dynamique).
================================================================================

Everything here is resolved AT REQUEST TIME (UI-1: no startup cache) through
core.paths exclusively (UI-10) — the TBOT_PROJECT_ROOT / TBOT_DB_DIR seams make
the whole module testable against a throwaway tmp layout.

Data contract (§3 of the spec):
  - ``strategies/S0NN_*/manifest.yaml``  -> declared level (R7, single source
    of truth), display name, magic number, declared instances.
  - ``db_dir()/<S0NN>/<instance>/status.json`` -> live per-instance metrics,
    written by the strategy, NEVER by this server.  Absent = the instance
    never ran (a legitimate state, not an error); unreadable = shown as such,
    never a 500 (UI-T2).
  - The ledger (core.ledger) -> closed trades, aggregates and equity curves.
    The ledger file is opened ONLY if it already exists: a read-only
    supervision server must not create databases on disk.

The declared level is CONFRONTED with reality (D-UI-4): a manifest that says
PAPER without a living instance is a divergence, displayed, never asleep.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from datetime import datetime, timezone

import yaml

from core.ledger import Ledger
from core.paths import db_dir, project_root

# An instance is « alive » if its status.json is fresher than this (§3.2).
FRESH_SEC = 24 * 3600

# Points embedded in the overview sparklines (UI-3) — the full curve stays
# available on /api/equity/<S0NN>/<instance>.
SPARK_POINTS = 60

# Statuses the manifest may declare (R7) and their level buckets (UI-2).
LEVEL_OF_STATUS = {
    "LIVE": "prod",
    "PAPER": "paper",
    "RESEARCH": "dev",
    "BACKTESTED": "dev",
    "RETIRED": "retired",
}

# Inherited sealed studies (UI-9): they instantiate strategies and stay
# visible in /services until E6 migrates them to the paper_S0NN family.
# (data folder under db_dir(), instantiated strategy S0NN or None, label)
LEGACY_STUDIES = [
    ("gold_forward",  "S011", "Or — XAUUSD H1"),
    ("s13_forward",   "S013", "AUDCAD ext-MACD D1"),
    ("macd_ai_paper", "S012", "MACD-IA — indices D1"),
    ("s14_sentiment", None,   "Sentiment des news (étude)"),
]

_PAIR_RE = re.compile(r"^[A-Z]{6}$")


# ── small helpers ───────────────────────────────────────────────────────────
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value) -> datetime | None:
    """ISO 8601 (Z accepted) -> aware UTC datetime, None if unparseable."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def short_id(folder_name: str) -> str:
    """'S013_macd_fx' -> 'S013' (D-UI-5 identity prefix)."""
    return folder_name.split("_", 1)[0]


def strategies_root() -> pathlib.Path:
    return project_root() / "strategies"


def ledger_db_path() -> pathlib.Path:
    """Same resolution as core.ledger.Ledger (TBOT_LEDGER_DB seam first)."""
    env = os.environ.get("TBOT_LEDGER_DB")
    return pathlib.Path(env) if env else db_dir() / "tradingbot.db"


def open_ledger() -> Ledger | None:
    """The ledger, ONLY if the file already exists — a read-only server
    never creates a database as a side effect of a GET."""
    path = ledger_db_path()
    if not path.is_file():
        return None
    try:
        return Ledger(path)
    except Exception:  # noqa: BLE001 — a corrupt db must not 500 the UI
        return None


def load_json_quiet(path: pathlib.Path) -> dict | None:
    """dict if readable, None otherwise (absent OR corrupt — the caller
    distinguishes via path.exists() when it matters)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# ── manifest ────────────────────────────────────────────────────────────────
def load_manifest(sdir: pathlib.Path) -> tuple[dict | None, str | None]:
    """(manifest dict, error message).  Never raises: an unreadable manifest
    yields an explicit error so the card shows « manifest invalide » instead
    of silently disappearing (UI-1)."""
    mf = sdir / "manifest.yaml"
    if not mf.is_file():
        return None, "manifest.yaml absent"
    try:
        data = yaml.safe_load(mf.read_text(encoding="utf-8-sig"))
    except (OSError, yaml.YAMLError) as e:
        return None, f"manifest invalide : {str(e)[:120]}"
    if not isinstance(data, dict):
        return None, "manifest invalide : pas un mapping YAML"
    return data, None


def declared_instances(short: str, manifest: dict | None) -> list[str]:
    """Instance ids declared by the manifest (D-UI-5).

    An explicit ``instances:`` list wins; otherwise instances derive from
    ``symbols:`` — a 6-letter FX pair becomes ``S0NN.XXX-YYY``, anything
    else the mono-instrument form ``S0NN.<SYMBOL>``."""
    if not manifest:
        return []
    raw = manifest.get("instances")
    if isinstance(raw, list) and all(isinstance(x, str) for x in raw):
        return list(raw)
    out = []
    symbols = manifest.get("symbols")
    if isinstance(symbols, list):
        for sym in symbols:
            s = str(sym).strip()
            if not s:
                continue
            if _PAIR_RE.match(s):
                out.append(f"{short}.{s[:3]}-{s[3:]}")
            else:
                out.append(f"{short}.{s}")
    return out


# ── per-instance status.json (§3.1) ─────────────────────────────────────────
def instance_status(short: str, instance: str) -> dict:
    """The §3.1 contract, defensively read.

    state: 'ok' (readable), 'never' (file absent — the instance never ran),
    'unreadable' (present but corrupt).  Extra fields in the file are
    tolerated and ignored (§3.1 extensibility)."""
    path = db_dir() / short / instance / "status.json"
    if not path.is_file():
        return {"instance": instance, "state": "never", "alive": False}
    st = load_json_quiet(path)
    if st is None:
        return {"instance": instance, "state": "unreadable", "alive": False,
                "error": "status.json illisible"}
    ts = parse_utc(st.get("generated_at_utc"))
    age = (utc_now() - ts).total_seconds() if ts else None
    return {
        "instance": instance,
        "state": "ok",
        "mode": st.get("mode"),
        "generated_at_utc": st.get("generated_at_utc"),
        "last_bar_time": st.get("last_bar_time"),
        "n_closed_total": st.get("n_closed_total", 0),
        "cum_r": st.get("cum_r", 0.0),
        "pnl_chf": st.get("pnl_chf", 0.0),
        "capital": st.get("capital"),
        "open_position": st.get("open_position"),
        "error": st.get("error"),
        "age_sec": age,
        "alive": age is not None and age < FRESH_SEC,
    }


def discovered_instances(short: str) -> list[str]:
    """Instances that EXIST on disk (db_dir()/<S0NN>/<inst>/status.json) —
    merged with the declared ones: a running instance the manifest forgot
    must still show up."""
    root = db_dir() / short
    if not root.is_dir():
        return []
    out = []
    try:
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and (entry / "status.json").is_file():
                out.append(entry.name)
    except OSError:
        return []
    return out


# ── equity curves (ledger + fallback, §3.2) ─────────────────────────────────
def equity_points(short: str, instance: str | None = None,
                  limit: int = 2000) -> list[list]:
    """[[iso_utc, equity], …] — ledger equity_snapshots first, fallback on
    the cumulative net_pnl of closed trades (§3.2).  Empty list without a
    ledger: never an exception."""
    ledger = open_ledger()
    if ledger is None:
        return []
    try:
        pts = ledger.equity_curve(strategy_id=short, instance_id=instance,
                                  limit=limit)
        if pts:
            return [[ts, eq] for ts, eq in pts]
        trades = ledger.closed_trades(strategy_id=short, instance_id=instance)
        cum, out = 0.0, []
        for t in trades[-limit:]:
            cum += t.get("net_pnl") or 0.0
            out.append([t["close_time"], round(cum, 2)])
        return out
    except Exception:  # noqa: BLE001 — supervision never 500s on read
        return []
    finally:
        ledger.close()


# ── strategy cards (UI-3) ───────────────────────────────────────────────────
def build_card(folder: str, *, spark: bool = True) -> dict:
    """One overview card: manifest identity + per-instance §3.1 metrics +
    sparkline data."""
    sdir = strategies_root() / folder
    short = short_id(folder)
    manifest, error = load_manifest(sdir)

    names = list(dict.fromkeys(declared_instances(short, manifest)
                               + discovered_instances(short)))
    instances = []
    for inst in names:
        st = instance_status(short, inst)
        if spark:
            st["equity"] = equity_points(short, inst, limit=SPARK_POINTS)
        instances.append(st)

    declared = "RESEARCH"
    name = folder
    magic = 0
    if manifest:
        declared = str(manifest.get("status") or "RESEARCH").upper()
        name = str(manifest.get("display_name") or folder)
        try:
            magic = int(manifest.get("magic_number") or 0)
        except (TypeError, ValueError):
            magic = 0

    return {
        "id": folder,
        "short": short,
        "name": name,
        "magic": magic,
        "declared": declared,
        "manifest_error": error,
        "alive": any(i["alive"] for i in instances),
        "instances": instances,
    }


def scan_strategy_folders() -> list[str]:
    """strategies/ scanned AT CALL TIME (UI-1) — ``_*`` folders ignored,
    missing root = empty list (clean empty state)."""
    root = strategies_root()
    if not root.is_dir():
        return []
    out = []
    try:
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and not entry.name.startswith("_"):
                out.append(entry.name)
    except OSError:
        return []
    return out


# ── legacy sealed studies (UI-9) ────────────────────────────────────────────
def study_state(folder: str) -> dict:
    """The real state of an inherited study — what the disk says (ported
    from the legacy server, freshness added per D-UI-4)."""
    path = db_dir() / folder / "status.json"
    if not path.is_file():
        return {"vivante": False, "mesure": "jamais"}
    st = load_json_quiet(path)
    if st is None:
        return {"vivante": False, "erreur": "status.json illisible",
                "mesure": "jamais"}
    ts = parse_utc(st.get("generated_at_utc"))
    if ts is None:
        try:
            age = utc_now().timestamp() - path.stat().st_mtime
        except OSError:
            age = None
    else:
        age = (utc_now() - ts).total_seconds()
    judges = st.get("judges") or {}
    return {
        "vivante": age is not None and age < FRESH_SEC,
        "trades": st.get("n_closed_total", 0),
        "cum_r": st.get("cum_r", 0.0),
        "capital": st.get("capital"),
        "position": bool(st.get("open_position")),
        "mesure": st.get("generated_at_utc") or "jamais",
        "news": st.get("n_news_total"),
        "verdicts": (sum(int(j.get("n_verdicts_total", 0))
                         for j in judges.values()) if judges else None),
        "arret": st.get("stop_criteria") or {},
    }


def living_study_strategies() -> set[str]:
    """S0NN ids instantiated by a LIVING legacy study — they count as real
    paper activity in the declared-vs-real confrontation."""
    out = set()
    for folder, strat, _label in LEGACY_STUDIES:
        if strat and study_state(folder).get("vivante"):
            out.add(strat)
    return out


# ── declared vs real (D-UI-4, kept from the legacy build_niveaux) ───────────
def build_niveaux(cards: list[dict]) -> dict:
    """{prod, paper, dev, retired: [folder ids], divergences: [messages]}.

    Placement follows the DECLARED status (R7 single source of truth) except
    the inherited rule: real paper activity pulls a dev card up to PAPER,
    with the divergence displayed."""
    study_paper = living_study_strategies()
    niveaux = {"prod": [], "paper": [], "dev": [], "retired": [],
               "divergences": []}
    for card in cards:
        declared = card["declared"]
        short = card["short"]
        living = [i for i in card["instances"] if i["alive"]]
        living_modes = {i.get("mode") for i in living}
        has_real_paper = bool(living) or short in study_paper

        if declared == "LIVE":
            niveaux["prod"].append(card["id"])
            if "LIVE" not in living_modes:
                niveaux["divergences"].append(
                    f"{short} : le manifeste déclare LIVE mais aucune "
                    f"instance vivante en mode LIVE")
        elif declared == "PAPER" or has_real_paper:
            niveaux["paper"].append(card["id"])
            if declared != "PAPER":
                niveaux["divergences"].append(
                    f"{short} : activité vivante (instance ou étude) mais le "
                    f"manifeste déclare {declared} (attendu PAPER)")
            elif not has_real_paper:
                niveaux["divergences"].append(
                    f"{short} : le manifeste déclare PAPER mais aucune "
                    f"instance vivante ne l'instancie")
        elif declared == "RETIRED":
            niveaux["retired"].append(card["id"])
        else:
            niveaux["dev"].append(card["id"])
    return niveaux


# ── top-level builders consumed by the routes ───────────────────────────────
def build_state() -> dict:
    """The /api/state payload (UI-7)."""
    cards = [build_card(folder) for folder in scan_strategy_folders()]
    return {"niveaux": build_niveaux(cards), "strategies": cards}


def resolve_folder(sid: str) -> str | None:
    """'S013' or 'S013_macd_fx' -> the folder name, None if unknown."""
    folders = scan_strategy_folders()
    if sid in folders:
        return sid
    for folder in folders:
        if short_id(folder).lower() == sid.lower():
            return folder
    return None


def build_strategy_detail(folder: str) -> dict:
    """The /api/strategy/<S0NN> payload (UI-4): full manifest, per-instance
    metrics, equity curves (per instance + strategy-cumulated), ledger
    aggregates, last 50 closed trades, recent errors."""
    card = build_card(folder)
    short = card["short"]
    manifest, _err = load_manifest(strategies_root() / folder)

    equity = {"cumulative": equity_points(short)}
    for inst in card["instances"]:
        equity[inst["instance"]] = equity_points(short, inst["instance"])

    aggregates = {"day": [], "week": [], "month": [], "year": []}
    trades: list[dict] = []
    ledger = open_ledger()
    if ledger is not None:
        try:
            aggregates = {
                "day": ledger.pnl_by_day(strategy_id=short)[-30:],
                "week": ledger.pnl_by_week(strategy_id=short)[-26:],
                "month": ledger.pnl_by_month(strategy_id=short)[-24:],
                "year": ledger.pnl_by_year(strategy_id=short),
            }
            rows = ledger.closed_trades(strategy_id=short)
            trades = list(reversed(rows[-50:]))
        except Exception:  # noqa: BLE001 — read-only UI never 500s
            pass
        finally:
            ledger.close()

    errors = []
    if card["manifest_error"]:
        errors.append({"source": "manifest", "error": card["manifest_error"]})
    for inst in card["instances"]:
        if inst.get("error"):
            errors.append({"source": inst["instance"], "error": inst["error"],
                           "generated_at_utc": inst.get("generated_at_utc")})

    return {
        "card": card,
        "manifest": manifest,
        "manifest_error": card["manifest_error"],
        "equity": equity,
        "aggregates": aggregates,
        "trades": trades,
        "errors": errors,
    }
