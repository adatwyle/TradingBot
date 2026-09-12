"""
server/analytics.py — moteur d'analyse des trades (SPEC_analytics-trades v1.0.0).
=================================================================================

Parité Trade Buddy : tout sous-ensemble de trades clos (mode × stratégie ×
instance × symbole × sens × jour × raison de sortie × période) est rejoué à
CHAQUE requête (D-AN-2, UI-1 : pas de cache) en KPI, courbe de solde /
drawdown, heatmap mensuelle, répartitions, distribution et bloc de synthèse.

Principes :
  - toutes les fonctions de calcul sont PURES : elles consomment une
    ``list[dict]`` au format ``Ledger.closed_trades()`` (§3.1 : 31 colonnes +
    ``instance_id``, plus ``source``, ``source_ref``, ``pnl_r``, ``arm`` posés
    par :func:`normalize_rows`) et rendent des dicts JSON-sérialisables ;
  - une seule série de solde / drawdown (D-AN-9) partagée par le KPI, la
    courbe et le SUMMARY : :func:`_balance_series` + :func:`_drawdown_stats` ;
  - jamais d'addition entre devises, entre modes, ni entre le clôturé et
    l'ouvert (§3.5) ; les arrondis n'interviennent qu'à la sortie ;
  - calendrier LOCAL pour les dates de filtre et les buckets (LG-10 /
    ``Ledger._to_local``) : le seam est le même — un ``tzinfo`` injectable,
    ``None`` = fuseau de la machine ;
  - serveur en lecture seule (UI-7, AN-12) : le ledger n'est ouvert que s'il
    existe déjà (``state.open_ledger``), les journaux sont lus par
    ``server.journal_adapter`` (importé paresseusement), rien n'est écrit ;
  - jamais de 500 (D-AN-16) : source absente ou altérée ⇒ résultat vide +
    ``warnings[]`` explicites ; la seule exception est ``ValueError`` levée
    par :func:`parse_filters` sur un paramètre hors domaine (la route la
    traduit en 400).

Les sources de données sont injectables (``sources=``) pour les tests : un
objet exposant ``closed_rows_ledger()``, ``closed_rows_journals()``,
``open_rows_ledger()``, ``open_rows_journals()``, ``capital_initial()``,
``journal_report()``, ``manifests()`` et, optionnellement,
``allocated_capital()``.  :class:`DefaultSources` est la fabrique réelle.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone, tzinfo

from core.version import read_version
from server import state as state_mod

# ── domaines des filtres (AN-4) ─────────────────────────────────────────────
MODES = ("BACKTEST", "PAPER", "LIVE")
SIDES = ("LONG", "SHORT")
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
EXIT_REASONS = ("SL", "TP", "TRAIL", "MANUAL", "HALT", "EOD")
ARMS = ("PRIMARY", "OBSERVATION", "MECH", "SHADOW", "none")
SOURCE_MODES = ("auto", "ledger", "journals")
CURVE_BASES = ("auto", "zero", "capital")
WEEKDAY_KEYS = ("open", "close")
DIST_UNITS = ("r", "ccy")

# Paramètres multi-valeurs (repeated keys) et leur ordre de présentation dans
# ``filters.options`` (AN-7) — domaine ordonné ou tri alphabétique/numérique.
MULTI_PARAMS = ("strategy", "instance", "symbol", "side", "weekday",
                "exit_reason", "arm", "magic")

# Caractères admis dans un symbole en plus des alphanumériques : les
# suffixes broker (``XAUUSD+``, ``EURUSD!``, ``US30.cash``) restent filtrables.
SYMBOL_EXTRA_CHARS = ".-_#+!$"

# Groupe des trades dont le magic diverge du manifeste (AN-22, F20).
MAGIC_DIVERGENT = "magic divergent"

# Au-delà de ce nombre de points, la courbe est décimée (AN-17).
CURVE_MAX_POINTS = 2000

# Sharpe / Sortino (AN-26) : nuls sous ces seuils.
SHARPE_MIN_TRADES = 20
SHARPE_MIN_DAYS = 30

# Journal des trades (AN-28).
PAGE_LIMIT_DEFAULT = 200
PAGE_LIMIT_MAX = 1000

# Bins fixes de la distribution en R (D-AN-12) : [-3, 5) par pas de 0,5.
R_BIN_LO, R_BIN_HI, R_BIN_STEP = -3.0, 5.0, 0.5
CCY_BINS = 16

# Les 31 colonnes de Ledger.closed_trades() (schema.sql + instance_id v2).
ROW_KEYS = (
    "id", "strategy_id", "instance_id", "strategy_version", "magic_number",
    "mode", "run_id", "symbol", "timeframe", "ticket", "side", "volume_lots",
    "open_time", "open_price", "close_time", "close_price", "stop_price",
    "target_price", "exit_reason", "gross_pnl", "commission", "swap",
    "net_pnl", "currency", "signal_reason", "confidence", "risk_distance",
    "risk_amount", "account_balance", "meta_json", "created_at",
)

VERSION_UNREADABLE = "VERSION illisible"


# ── petits helpers ──────────────────────────────────────────────────────────
def _version() -> str:
    """Même contrat que app._version (UI-6) — jamais une exception."""
    try:
        return read_version()
    except (OSError, ValueError):
        return VERSION_UNREADABLE


def generated_utc() -> str:
    """Horodatage ``generated`` des payloads analytics : UTC suffixé ``Z``
    (forme de l'exemple §6.1) — partagé avec les replis d'app.py pour que
    la réponse dégradée porte le même format que la nominale."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_generated = generated_utc


def to_local(iso_utc: str, local_tz: tzinfo | None = None) -> datetime | None:
    """ISO 8601 UTC -> datetime dans le calendrier local (même règle que
    ``Ledger._to_local`` : ``local_tz`` None = fuseau de la machine)."""
    dt = state_mod.parse_utc(iso_utc)
    return dt.astimezone(local_tz) if dt is not None else None


def _f(value, default: float = 0.0) -> float:
    """float tolérant : None / texte non numérique -> ``default``."""
    if value is None:
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return default if math.isnan(out) else out


def _opt_f(value) -> float | None:
    """float ou None (jamais NaN) — pour les champs facultatifs."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) else out


def _money(v) -> float | None:
    return None if v is None else round(float(v), 2)


def _ratio(v) -> float | None:
    return None if v is None else round(float(v), 2)


def _pct(v) -> float | None:
    # Fractions (0,0455 = 4,55 %) : 4 décimales = 2 décimales en pour-cent.
    return None if v is None else round(float(v), 4)


def _div(num: float, den: float) -> float | None:
    return None if den == 0 else num / den


def _net(row: dict) -> float:
    return _f(row.get("net_pnl"))


def instance_key(row: dict) -> str:
    """Clé d'instance d'une ligne : ``instance_id``, repli ``symbol`` (AN-21)."""
    return str(row.get("instance_id") or row.get("symbol") or "?")


def _decode_meta(raw) -> dict:
    """``meta_json`` -> dict ; ``{}`` si NULL, invalide ou pas un objet."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


# ── §3.1 — normalisation des lignes ─────────────────────────────────────────
def normalize_rows(rows: list[dict], source: str,
                   warnings: list[str] | None = None) -> list[dict]:
    """Lignes brutes (ledger ou adaptateur) -> format unique §3.1.

    Pose les 31 clés (None si absentes), décode ``meta_json`` en dict,
    calcule ``pnl_r`` (meta puis net/risk_amount), ``arm`` (meta) et
    ``source_ref`` (déjà porté par la ligne, sinon ``ticket`` puis ``id``).
    Une ligne sans ``close_time`` exploitable est écartée avec un warning :
    elle n'est pas un trade clos."""
    out: list[dict] = []
    for raw in rows:
        row = {k: raw.get(k) for k in ROW_KEYS}
        if state_mod.parse_utc(row.get("close_time")) is None:
            if warnings is not None:
                warnings.append(
                    f"ligne ignorée ({source}) : close_time invalide "
                    f"{row.get('close_time')!r}")
            continue
        meta = _decode_meta(raw.get("meta_json"))
        row["meta_json"] = meta
        row["source"] = source
        ref = raw.get("source_ref")
        if ref is None:
            ref = raw.get("ticket")
        if ref is None:
            ref = raw.get("id")
        row["source_ref"] = None if ref is None else str(ref)
        pnl_r = _opt_f(meta.get("pnl_r"))
        if pnl_r is None:
            risk = _opt_f(row.get("risk_amount"))
            if risk is not None and risk > 0:
                pnl_r = _net(row) / risk
        row["pnl_r"] = pnl_r
        arm = meta.get("arm")
        row["arm"] = str(arm) if arm not in (None, "") else None
        out.append(row)
    return sort_rows(out)


def _id_key(row: dict) -> tuple:
    """Départage d'un tri : ``id`` numérique d'abord (ordre du ledger,
    ``ORDER BY close_time, id``), sinon texte (``source_ref`` des journaux)
    — jamais lexical sur un entier ('10' < '9')."""
    ident = row.get("id")
    if ident is None:
        ident = row.get("source_ref")
    try:
        return (0, int(ident), "")
    except (TypeError, ValueError):
        return (1, 0, str(ident or ""))


def sort_rows(rows: list[dict]) -> list[dict]:
    """Tri de référence (§3.5) : ``close_time`` croissant puis id/source_ref."""
    return sorted(rows, key=lambda r: (str(r.get("close_time") or ""), _id_key(r)))


# ── AN-4 — filtres ──────────────────────────────────────────────────────────
@dataclass
class Filters:
    """Les paramètres de GET /api/analytics (AN-4), validés."""
    mode: str = "PAPER"
    strategy: list[str] = field(default_factory=list)
    instance: list[str] = field(default_factory=list)
    symbol: list[str] = field(default_factory=list)
    side: list[str] = field(default_factory=list)
    weekday: list[str] = field(default_factory=list)
    exit_reason: list[str] = field(default_factory=list)
    arm: list[str] = field(default_factory=list)
    magic: list[int] = field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    source: str = "auto"
    curve_base: str = "auto"
    weekday_key: str = "open"
    dist_unit: str = "r"

    def applied(self) -> dict:
        """La forme ``filters.applied`` de §6.1."""
        return {
            "mode": self.mode, "strategy": list(self.strategy),
            "instance": list(self.instance), "symbol": list(self.symbol),
            "side": list(self.side), "weekday": list(self.weekday),
            "exit_reason": list(self.exit_reason), "arm": list(self.arm),
            "magic": list(self.magic), "from": self.date_from,
            "to": self.date_to, "source": self.source,
            "curve_base": self.curve_base, "weekday_key": self.weekday_key,
            "dist_unit": self.dist_unit,
        }


def _invalid(name: str, value) -> ValueError:
    return ValueError(f"paramètre invalide : {name}={value}")


def _values(args, name: str) -> list[str]:
    """Toutes les valeurs d'un paramètre (repeated keys), chaînes vides
    ignorées (un ``<input type=date>`` vide envoie ``""``).  Accepte un
    MultiDict Flask (``getlist``) ou un dict de str / list."""
    if hasattr(args, "getlist"):
        raw = args.getlist(name)
    else:
        v = args.get(name) if hasattr(args, "get") else None
        raw = list(v) if isinstance(v, (list, tuple)) else ([] if v is None else [v])
    return [str(x).strip() for x in raw if str(x).strip() != ""]


def _single(args, name: str, domain: tuple[str, ...] | None,
            default: str | None) -> str | None:
    vals = _values(args, name)
    if not vals:
        return default
    if len(vals) > 1:
        raise _invalid(name, ",".join(vals))
    if domain is not None and vals[0] not in domain:
        raise _invalid(name, vals[0])
    return vals[0]


def _multi(args, name: str, domain: tuple[str, ...] | None) -> list[str]:
    vals = _values(args, name)
    for v in vals:
        if domain is not None and v not in domain:
            raise _invalid(name, v)
    return list(dict.fromkeys(vals))


def _date(args, name: str) -> str | None:
    val = _single(args, name, None, None)
    if val is None:
        return None
    try:
        return date.fromisoformat(val).isoformat()
    except ValueError:
        raise _invalid(name, val) from None


def _ident(value: str, name: str, *, prefix: str = "",
           extra: str = ".-_#") -> str:
    """Identifiants (stratégie, instance, symbole) : lettres, chiffres et
    ``.-_#`` seulement — une valeur farfelue est une URL fausse (400).
    ``extra`` élargit le jeu (symboles broker suffixés ``XAUUSD+``)."""
    ok = value and all(c.isalnum() or c in extra for c in value)
    if not ok or not value.startswith(prefix):
        raise _invalid(name, value)
    return value


def parse_filters(args) -> Filters:
    """Query string -> :class:`Filters`.  Lève ``ValueError`` « paramètre
    invalide : <nom>=<valeur> » sur toute valeur hors domaine (AN-4)."""
    f = Filters()
    f.mode = _single(args, "mode", MODES, "PAPER")
    f.strategy = [_ident(v, "strategy", prefix="S")
                  for v in _multi(args, "strategy", None)]
    for v in f.strategy:
        if not (len(v) == 4 and v[1:].isdigit()):
            raise _invalid("strategy", v)
    f.instance = [_ident(v, "instance", prefix="S")
                  for v in _multi(args, "instance", None)]
    for v in f.instance:
        if "." not in v or not v[1:4].isdigit():
            raise _invalid("instance", v)
    f.symbol = [_ident(v, "symbol", extra=SYMBOL_EXTRA_CHARS)
                for v in _multi(args, "symbol", None)]
    f.side = _multi(args, "side", SIDES)
    f.weekday = _multi(args, "weekday", WEEKDAYS)
    f.exit_reason = _multi(args, "exit_reason", EXIT_REASONS)
    f.arm = _multi(args, "arm", ARMS)
    magics: list[int] = []
    for v in _values(args, "magic"):
        try:
            magics.append(int(v))
        except ValueError:
            raise _invalid("magic", v) from None
    f.magic = list(dict.fromkeys(magics))
    f.date_from = _date(args, "from")
    f.date_to = _date(args, "to")
    if f.date_from and f.date_to and f.date_from > f.date_to:
        raise _invalid("to", f.date_to)
    f.source = _single(args, "source", SOURCE_MODES, "auto")
    f.curve_base = _single(args, "curve_base", CURVE_BASES, "auto")
    f.weekday_key = _single(args, "weekday_key", WEEKDAY_KEYS, "open")
    f.dist_unit = _single(args, "dist_unit", DIST_UNITS, "r")
    return f


def parse_paging(args) -> tuple[int, int]:
    """``page`` (≥ 1, défaut 1) et ``limit`` (1…1000, défaut 200) — AN-28."""
    page_s = _single(args, "page", None, None)
    limit_s = _single(args, "limit", None, None)
    try:
        page = 1 if page_s is None else int(page_s)
    except ValueError:
        raise _invalid("page", page_s) from None
    if page < 1:
        raise _invalid("page", page_s)
    try:
        limit = PAGE_LIMIT_DEFAULT if limit_s is None else int(limit_s)
    except ValueError:
        raise _invalid("limit", limit_s) from None
    if not 1 <= limit <= PAGE_LIMIT_MAX:
        raise _invalid("limit", limit_s)
    return page, limit


# ── AN-5 / AN-6 — prédicat ──────────────────────────────────────────────────
def weekday_of(row: dict, weekday_key: str = "open",
               local_tz: tzinfo | None = None) -> str | None:
    """``mon``…``sun`` du jour LOCAL d'entrée (``open``) ou de sortie (``close``)."""
    key = "close_time" if weekday_key == "close" else "open_time"
    dt = to_local(row.get(key), local_tz)
    return WEEKDAYS[dt.weekday()] if dt is not None else None


def _local_close_date(row: dict, local_tz: tzinfo | None) -> str | None:
    dt = to_local(row.get("close_time"), local_tz)
    return dt.date().isoformat() if dt is not None else None


def _matches(row: dict, f: Filters, local_tz: tzinfo | None) -> bool:
    if row.get("mode") != f.mode:
        return False
    if f.strategy and row.get("strategy_id") not in f.strategy:
        return False
    if f.instance and row.get("instance_id") not in f.instance:
        return False
    if f.symbol and row.get("symbol") not in f.symbol:
        return False
    if f.side and row.get("side") not in f.side:
        return False
    if f.exit_reason and row.get("exit_reason") not in f.exit_reason:
        return False
    if f.arm:
        arm = row.get("arm") or "none"
        if arm not in f.arm:
            return False
    if f.magic:
        try:
            magic = int(row.get("magic_number"))
        except (TypeError, ValueError):
            return False
        if magic not in f.magic:
            return False
    if f.weekday and weekday_of(row, f.weekday_key, local_tz) not in f.weekday:
        return False
    if f.date_from or f.date_to:
        day = _local_close_date(row, local_tz)
        if day is None:
            return False
        if f.date_from and day < f.date_from:
            return False
        if f.date_to and day > f.date_to:
            return False
    return True


def filter_rows(rows: list[dict], filters: Filters,
                local_tz: tzinfo | None = None) -> list[dict]:
    """AND entre paramètres, OR à l'intérieur (AN-5) ; liste vide = « All »."""
    return [r for r in rows if _matches(r, filters, local_tz)]


# ── AN-7 — listes dépendantes ───────────────────────────────────────────────
def options(rows: list[dict], filters: Filters, *,
            local_tz: tzinfo | None = None,
            manifests: dict[str, dict] | None = None) -> dict:
    """``filters.options`` : pour chaque paramètre multi, les valeurs
    distinctes du sous-ensemble filtré par TOUS LES AUTRES paramètres."""
    manifests = manifests or {}
    out: dict = {}
    for name in MULTI_PARAMS:
        others = replace(filters, **{name: []})
        subset = filter_rows(rows, others, local_tz)
        if name == "strategy":
            ids = sorted({str(r.get("strategy_id")) for r in subset
                          if r.get("strategy_id")})
            out[name] = [{
                "id": sid,
                "display_name": str((manifests.get(sid) or {}).get(
                    "display_name") or sid),
                "retired": bool((manifests.get(sid) or {}).get("retired")),
            } for sid in ids]
        elif name in ("instance", "symbol"):
            col = "instance_id" if name == "instance" else "symbol"
            out[name] = sorted({str(r.get(col)) for r in subset if r.get(col)})
        elif name == "side":
            present = {r.get("side") for r in subset}
            out[name] = [s for s in SIDES if s in present]
        elif name == "weekday":
            present = {weekday_of(r, filters.weekday_key, local_tz)
                       for r in subset}
            out[name] = [w for w in WEEKDAYS if w in present]
        elif name == "exit_reason":
            present = {r.get("exit_reason") for r in subset}
            out[name] = [e for e in EXIT_REASONS if e in present]
        elif name == "arm":
            present = {r.get("arm") or "none" for r in subset}
            out[name] = [a for a in ARMS if a in present]
        elif name == "magic":
            magics: set[int] = set()
            for r in subset:
                try:
                    magics.add(int(r.get("magic_number")))
                except (TypeError, ValueError):
                    continue
            out[name] = sorted(magics)
    return out


# ── AN-14 — LA série de solde / drawdown (D-AN-9) ──────────────────────────
def _balance_series(rows: list[dict], base: float | None) -> list[dict]:
    """``B_0 = base`` (0 si inconnue), ``B_k = B_{k-1} + net_k``,
    ``P_k = max(B_0..B_k)``, ``dd_k = B_k − P_k``, ``dd_pct_k = dd_k / P_k``
    (null en base zéro : pas de pic significatif)."""
    known = base is not None and base > 0
    bal = float(base) if known else 0.0
    peak = bal
    out = []
    for r in rows:
        bal += _net(r)
        peak = max(peak, bal)
        dd = bal - peak
        out.append({"t": r.get("close_time"), "balance": bal, "peak": peak,
                    "dd": dd, "dd_pct": (dd / peak if known and peak > 0
                                         else None)})
    return out


def _days_between(iso_a, iso_b) -> float | None:
    a, b = state_mod.parse_utc(iso_a), state_mod.parse_utc(iso_b)
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 86400.0


def _drawdown_stats(series: list[dict], base: float | None) -> dict:
    """max / courant / récupéré / durées sur la série AN-14 (valeurs brutes)."""
    empty = {"max_drawdown": 0.0, "max_dd_pct": None, "current_drawdown": 0.0,
             "recovered_pct": None, "dd_duration_days": 0.0,
             "recovery_days": None}
    if not series:
        return empty
    known = base is not None and base > 0
    max_dd, k_star = 0.0, -1
    for k, s in enumerate(series):
        d = s["peak"] - s["balance"]
        if d > max_dd:
            max_dd, k_star = d, k
    last = series[-1]
    current = last["peak"] - last["balance"]
    out = dict(empty, current_drawdown=current)
    if k_star < 0:
        # Aucun creux : 0 % en base connue, « — » (null) en base zéro.
        out["max_dd_pct"] = 0.0 if known else None
        return out
    peak_star = series[k_star]["peak"]
    out["max_drawdown"] = max_dd
    out["max_dd_pct"] = (max_dd / peak_star
                         if known and peak_star > 0 else None)
    # Creux effacé = le pic du DD max a été retrouvé après le creux.
    erased_at = next((j for j in range(k_star + 1, len(series))
                      if series[j]["balance"] >= peak_star), None)
    if erased_at is None:
        out["recovered_pct"] = 1.0 - current / max_dd
        out["recovery_days"] = None
    else:
        out["recovered_pct"] = None
        out["recovery_days"] = _days_between(series[k_star]["t"],
                                             series[erased_at]["t"])
    # Pic : dernier point ≤ k* où le solde vaut le pic ; si le pic est B_0
    # (la base), le DD commence au premier trade.
    peak_at = next((i for i in range(k_star, -1, -1)
                    if series[i]["balance"] >= peak_star), 0)
    out["dd_duration_days"] = _days_between(series[peak_at]["t"],
                                            series[k_star]["t"]) or 0.0
    return out


# ── AN-13 — KPI ─────────────────────────────────────────────────────────────
def _counts(rows: list[dict]) -> dict:
    nets = [_net(r) for r in rows]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x < 0]
    rs = [r["pnl_r"] for r in rows if r.get("pnl_r") is not None]
    return {
        "n": len(rows), "wins": len(wins), "losses": len(losses),
        "zeros": len(nets) - len(wins) - len(losses),
        "net": sum(nets), "gross_profit": sum(wins), "gross_loss": sum(losses),
        "rs": rs, "sum_r": sum(rs),
        "long": sum(1 for r in rows if r.get("side") == "LONG"),
        "short": sum(1 for r in rows if r.get("side") == "SHORT"),
    }


def kpi(rows: list[dict], base: float | None = None) -> dict:
    """Les 9 tuiles (AN-13) + la partie drawdown (AN-14) — jamais de division
    par zéro : N = 0 ⇒ 0 / null partout."""
    c = _counts(rows)
    n = c["n"]
    dd = _drawdown_stats(_balance_series(rows, base), base)
    return {
        "total_trades": n, "long": c["long"], "short": c["short"],
        "wins": c["wins"], "losses": c["losses"], "zeros": c["zeros"],
        "win_rate": _pct(c["wins"] / n if n else 0.0),
        "net_pnl": _money(c["net"]),
        "avg_per_trade": _money(c["net"] / n if n else 0.0),
        "gross_profit": _money(c["gross_profit"]),
        "gross_loss": _money(c["gross_loss"]),
        "profit_factor": _ratio(_div(c["gross_profit"], abs(c["gross_loss"]))),
        "avg_win": _money(_div(c["gross_profit"], c["wins"])),
        "avg_loss": _money(_div(c["gross_loss"], c["losses"])),
        "expectancy": _money(c["net"] / n if n else 0.0),
        "n_r": len(c["rs"]),
        "avg_r": _ratio(_div(c["sum_r"], len(c["rs"]))),
        "sum_r": _ratio(c["sum_r"]),
        "max_drawdown": _money(dd["max_drawdown"]),
        "max_dd_pct": _pct(dd["max_dd_pct"]),
        "recovery_factor": _ratio(_div(c["net"], dd["max_drawdown"])),
        "current_drawdown": _money(dd["current_drawdown"]),
        "recovered_pct": _pct(dd["recovered_pct"]),
        "dd_duration_days": _ratio(dd["dd_duration_days"]),
        "recovery_days": _ratio(dd["recovery_days"]),
    }


# ── AN-15…AN-18 — courbe ────────────────────────────────────────────────────
def curve(rows: list[dict], base: float | None = None, *,
          local_tz: tzinfo | None = None) -> dict:
    """``{base, base_kind, points: [[iso_utc, balance, drawdown, dd_pct]],
    decimated}`` — un point par trade clos ; au-delà de 2 000 points,
    « dernier solde du jour » (jour local) PLUS, quand il en diffère, le
    creux du jour (pire drawdown) : la courbe décimée porte toujours le
    max drawdown du KPI (D-AN-9, une seule série) et son dernier point
    reste le solde final (drawdown courant)."""
    known = base is not None and base > 0
    series = _balance_series(rows, base)
    decimated = False
    if len(series) > CURVE_MAX_POINTS:
        series = _decimate_by_day(series, local_tz)
        decimated = True
    return {
        "base": _money(base if known else 0.0),
        "base_kind": "capital" if known else "zero",
        "decimated": decimated,
        "points": [[s["t"], _money(s["balance"]), _money(s["dd"]),
                    _pct(s["dd_pct"])] for s in series],
    }


def _decimate_by_day(series: list[dict], local_tz: tzinfo | None) -> list[dict]:
    """Par jour local : le point de solde final et, s'il est antérieur, le
    point du creux (dd minimal, dernier en cas d'égalité) — tous deux sont
    de vrais points de la série AN-14, jamais une valeur recomposée."""
    days: dict[str, tuple[dict, dict]] = {}   # jour -> (creux, dernier)
    for s in series:
        dt = to_local(s["t"], local_tz)
        day = dt.date().isoformat() if dt else str(s["t"])
        low, _last = days.get(day, (s, s))
        days[day] = (s if s["dd"] <= low["dd"] else low, s)
    out: list[dict] = []
    for low, last in days.values():
        if low is not last:
            out.append(low)
        out.append(last)
    return out


# ── AN-19 / AN-20 — heatmap et P&L par mois ─────────────────────────────────
def _month_cells(rows: list[dict], local_tz: tzinfo | None) -> dict[str, dict]:
    cells: dict[str, dict] = {}
    for r in rows:
        dt = to_local(r.get("close_time"), local_tz)
        if dt is None:
            continue
        key = f"{dt.year:04d}-{dt.month:02d}"
        c = cells.setdefault(key, {"net": 0.0, "n_trades": 0, "sum_r": 0.0})
        c["net"] += _net(r)
        c["n_trades"] += 1
        c["sum_r"] += r.get("pnl_r") or 0.0
    return cells


def _cell_out(c: dict, base: float | None) -> dict:
    known = base is not None and base > 0
    return {"net": _money(c["net"]), "n_trades": c["n_trades"],
            "sum_r": _ratio(c["sum_r"]),
            "pct": _pct(c["net"] / base) if known else None}


def heatmap(rows: list[dict], base: float | None = None, *,
            local_tz: tzinfo | None = None) -> dict:
    """Années × mois (+ TOTAL ligne, colonne et global) sur le calendrier
    local ; ``pct = net / base`` non composé, null en base zéro."""
    cells = _month_cells(rows, local_tz)
    years: dict[str, dict] = {}
    months: dict[str, dict] = {}
    total = {"net": 0.0, "n_trades": 0, "sum_r": 0.0}
    for key, c in cells.items():
        y, m = key.split("-")
        for bucket in (years.setdefault(y, {"net": 0.0, "n_trades": 0,
                                            "sum_r": 0.0}),
                       months.setdefault(m, {"net": 0.0, "n_trades": 0,
                                             "sum_r": 0.0}),
                       total):
            bucket["net"] += c["net"]
            bucket["n_trades"] += c["n_trades"]
            bucket["sum_r"] += c["sum_r"]
    return {
        "years": sorted(int(y) for y in years),
        "cells": {k: _cell_out(cells[k], base) for k in sorted(cells)},
        "year_totals": {y: _cell_out(years[y], base) for y in sorted(years)},
        "month_totals": {m: _cell_out(months[m], base) for m in sorted(months)},
        "total": _cell_out(total, base),
    }


def by_month(rows: list[dict], base: float | None = None, *,
             local_tz: tzinfo | None = None) -> list[dict]:
    """Une entrée par mois calendaire de la plage (mois vides inclus)."""
    cells = _month_cells(rows, local_tz)
    if not cells:
        return []
    keys = sorted(cells)
    y, m = (int(x) for x in keys[0].split("-"))
    y_end, m_end = (int(x) for x in keys[-1].split("-"))
    out = []
    while (y, m) <= (y_end, m_end):
        key = f"{y:04d}-{m:02d}"
        c = cells.get(key, {"net": 0.0, "n_trades": 0, "sum_r": 0.0})
        out.append({"month": key, **_cell_out(c, base)})
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


# ── AN-21…AN-23 — répartitions ──────────────────────────────────────────────
def _raw_net(rows: list[dict]) -> float:
    """Net brut d'un groupe (clé de tri : jamais la valeur arrondie, qui
    crée des égalités artificielles sous 0,005)."""
    return sum(_net(r) for r in rows)


def _group_stats(rows: list[dict]) -> dict:
    c = _counts(rows)
    return {
        "n_trades": c["n"],
        "win_rate": _pct(c["wins"] / c["n"] if c["n"] else 0.0),
        "net": _money(c["net"]),
        "profit_factor": _ratio(_div(c["gross_profit"], abs(c["gross_loss"]))),
        "sum_r": _ratio(c["sum_r"]),
    }


def magic_ok(row: dict, manifests: dict[str, dict] | None) -> bool:
    """``False`` si le manifeste de la stratégie porte un magic connu (≠ 0)
    différent de celui du trade ; ``True`` sinon (rien à confronter)."""
    if not manifests:
        return True
    expected = (manifests.get(str(row.get("strategy_id"))) or {}).get("magic")
    try:
        expected = int(expected or 0)
        actual = int(row.get("magic_number") or 0)
    except (TypeError, ValueError):
        return True
    return expected == 0 or expected == actual


def _group_by(rows: list[dict], key_of) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(key_of(r), []).append(r)
    return groups


def _by_instance(rows: list[dict], bases: dict[str, float | None]) -> list[dict]:
    out = []
    for inst, sub in _group_by(rows, instance_key).items():
        b = bases.get(inst)
        dd = _drawdown_stats(_balance_series(sub, b), b)
        out.append((-_raw_net(sub), inst,
                    {"instance": inst,
                     "symbol": next((r.get("symbol") for r in sub), None),
                     **_group_stats(sub),
                     "max_drawdown": _money(dd["max_drawdown"])}))
    return [e for _n, _k, e in sorted(out, key=lambda t: t[:2])]


def _by_symbol(rows: list[dict], bases: dict[str, float | None]) -> list[dict]:
    out = []
    for sym, sub in _group_by(rows, lambda r: str(r.get("symbol") or "?")).items():
        insts = {instance_key(r) for r in sub}
        known = all(bases.get(i) for i in insts)
        b = sum(bases[i] for i in insts) if known else None
        dd = _drawdown_stats(_balance_series(sub, b), b)
        out.append((-_raw_net(sub), sym,
                    {"symbol": sym, "n_instances": len(insts),
                     **_group_stats(sub),
                     "max_drawdown": _money(dd["max_drawdown"])}))
    return [e for _n, _k, e in sorted(out, key=lambda t: t[:2])]


def _by_strategy(rows: list[dict], bases: dict[str, float | None],
                 manifests: dict[str, dict]) -> list[dict]:
    regular = [r for r in rows if magic_ok(r, manifests)]
    divergent = [r for r in rows if not magic_ok(r, manifests)]
    out = []
    for sid, sub in _group_by(regular, lambda r: str(r.get("strategy_id") or "?")).items():
        mf = manifests.get(sid) or {}
        out.append((-_raw_net(sub), sid,
                    {"strategy_id": sid,
                     "display_name": str(mf.get("display_name") or sid),
                     "retired": bool(mf.get("retired")),
                     **_group_stats(sub),
                     "instances": _by_instance(sub, bases)}))
    out = [e for _n, _k, e in sorted(out, key=lambda t: t[:2])]
    if divergent:
        out.append({"strategy_id": MAGIC_DIVERGENT,
                    "display_name": MAGIC_DIVERGENT, "retired": False,
                    **_group_stats(divergent),
                    "instances": _by_instance(divergent, bases)})
    return out


def _by_weekday(rows: list[dict], weekday_key: str,
                local_tz: tzinfo | None) -> list[dict]:
    groups = _group_by(rows, lambda r: weekday_of(r, weekday_key, local_tz) or "?")
    return [{"weekday": w, **_group_stats(groups.get(w, []))} for w in WEEKDAYS]


def _by_hour(rows: list[dict], local_tz: tzinfo | None) -> list[dict]:
    def hour_of(r):
        dt = to_local(r.get("open_time"), local_tz)
        return dt.hour if dt is not None else -1
    groups = _group_by(rows, hour_of)
    return [{"hour": h, **_group_stats(groups.get(h, []))} for h in range(24)]


def by_key(rows: list[dict], key: str, *,
           bases: dict[str, float | None] | None = None,
           manifests: dict[str, dict] | None = None,
           weekday_key: str = "open", base: float | None = None,
           local_tz: tzinfo | None = None) -> list[dict]:
    """Répartition selon ``key`` ∈ instance / symbol / strategy / weekday /
    hour / month.  ``bases`` = starting balance par instance (§3.3),
    ``manifests`` = ``{S0NN: {display_name, retired, magic}}``."""
    bases = bases or {}
    manifests = manifests or {}
    if key == "instance":
        return _by_instance(rows, bases)
    if key == "symbol":
        return _by_symbol(rows, bases)
    if key == "strategy":
        return _by_strategy(rows, bases, manifests)
    if key == "weekday":
        return _by_weekday(rows, weekday_key, local_tz)
    if key == "hour":
        return _by_hour(rows, local_tz)
    if key == "month":
        return by_month(rows, base, local_tz=local_tz)
    raise ValueError(f"clé de répartition inconnue : {key}")


# ── AN-24 — distribution ────────────────────────────────────────────────────
def distribution(rows: list[dict], unit: str = "r") -> dict:
    """``r`` : bins fixes de 0,5 R sur [−3, 5) + ``< −3`` + ``≥ 5`` ;
    ``ccy`` : 16 bins équirépartis sur [min, max] du net (1 bin si égaux)."""
    n_without_r = sum(1 for r in rows if r.get("pnl_r") is None)
    if unit == "ccy":
        vals = [_net(r) for r in rows]
        if not vals:
            return {"unit": "ccy", "bins": [], "n_without_r": n_without_r}
        lo, hi = min(vals), max(vals)
        if lo == hi:
            return {"unit": "ccy", "n_without_r": n_without_r,
                    "bins": [{"lo": _money(lo), "hi": _money(hi), "n": len(vals)}]}
        width = (hi - lo) / CCY_BINS
        counts = [0] * CCY_BINS
        for v in vals:
            idx = min(int((v - lo) / width), CCY_BINS - 1)
            counts[idx] += 1
        return {"unit": "ccy", "n_without_r": n_without_r,
                "bins": [{"lo": _money(lo + i * width),
                          "hi": _money(lo + (i + 1) * width), "n": counts[i]}
                         for i in range(CCY_BINS)]}
    rs = [r["pnl_r"] for r in rows if r.get("pnl_r") is not None]
    n_bins = int(round((R_BIN_HI - R_BIN_LO) / R_BIN_STEP))
    edges = [R_BIN_LO + i * R_BIN_STEP for i in range(n_bins + 1)]
    below = sum(1 for v in rs if v < R_BIN_LO)
    above = sum(1 for v in rs if v >= R_BIN_HI)
    bins = [{"lo": None, "hi": R_BIN_LO, "n": below}]
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        bins.append({"lo": lo, "hi": hi, "n": sum(1 for v in rs if lo <= v < hi)})
    bins.append({"lo": R_BIN_HI, "hi": None, "n": above})
    return {"unit": "r", "bins": bins, "n_without_r": n_without_r}


# ── AN-25 (SÉRIES) — streaks ────────────────────────────────────────────────
def streaks(rows: list[dict]) -> dict:
    """Séries de gains / pertes sur T trié ; un net = 0 casse les deux
    (DF-16) et laisse la série courante à ``{none, 0}``."""
    max_win = max_loss = 0
    kind, length = "none", 0
    for r in rows:
        net = _net(r)
        if net > 0:
            kind, length = "win", (length + 1 if kind == "win" else 1)
            max_win = max(max_win, length)
        elif net < 0:
            kind, length = "loss", (length + 1 if kind == "loss" else 1)
            max_loss = max(max_loss, length)
        else:
            kind, length = "none", 0
    return {"max_win_streak": max_win, "max_loss_streak": max_loss,
            "current_streak": {"kind": kind, "len": length}}


def holding_hours(row: dict) -> float | None:
    """``close_time − open_time`` en heures décimales, None si inexploitable."""
    a = state_mod.parse_utc(row.get("open_time"))
    b = state_mod.parse_utc(row.get("close_time"))
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 3600.0


# ── AN-26 — Sharpe / Sortino sur le R ───────────────────────────────────────
def sharpe_sortino(rows: list[dict]) -> dict:
    """``{sharpe_r, sharpe_r_annual, sortino_r, n_r, years}`` sur les R
    connus ; null sous 20 trades, sous 30 jours ou à dénominateur nul."""
    rs = [r["pnl_r"] for r in rows if r.get("pnl_r") is not None]
    out = {"sharpe_r": None, "sharpe_r_annual": None, "sortino_r": None,
           "n_r": len(rs), "years": None}
    if len(rs) < SHARPE_MIN_TRADES:
        return out
    with_r = [r for r in rows if r.get("pnl_r") is not None]
    span_days = _days_between(with_r[0]["close_time"], with_r[-1]["close_time"])
    years = span_days / 365.25 if span_days is not None else None
    out["years"] = years
    if years is None or years < SHARPE_MIN_DAYS / 365.25:
        return out
    mean = statistics.fmean(rs)
    std = statistics.stdev(rs)
    if std > 0:
        out["sharpe_r"] = mean / std
        out["sharpe_r_annual"] = out["sharpe_r"] * math.sqrt(len(rs) / years)
    down = math.sqrt(statistics.fmean(min(v, 0.0) ** 2 for v in rs))
    if down > 0:
        out["sortino_r"] = mean / down
    return out


# ── AN-25 — SUMMARY complet ─────────────────────────────────────────────────
def summary(rows: list[dict], base: float | None = None) -> dict:
    """Les 5 colonnes VOLUME / P&L / RISQUE / SÉRIES & DURÉE / SOLDE & COÛTS."""
    c = _counts(rows)
    n = c["n"]
    known = base is not None and base > 0
    longs = [r for r in rows if r.get("side") == "LONG"]
    shorts = [r for r in rows if r.get("side") == "SHORT"]
    nets = [_net(r) for r in rows]
    rs = c["rs"]
    dd = _drawdown_stats(_balance_series(rows, base), base)
    sh = sharpe_sortino(rows)
    holds = [h for h in (holding_hours(r) for r in rows) if h is not None]
    st = streaks(rows)

    def wr(sub):
        w = sum(1 for r in sub if _net(r) > 0)
        return _pct(_div(w, len(sub)))

    return {
        "volume": {
            "total": n, "long": c["long"], "short": c["short"],
            "wins": c["wins"], "losses": c["losses"], "zeros": c["zeros"],
            "win_rate": _pct(c["wins"] / n if n else 0.0),
            "long_win_rate": wr(longs), "short_win_rate": wr(shorts),
        },
        "pnl": {
            "net": _money(c["net"]),
            "gross_profit": _money(c["gross_profit"]),
            "gross_loss": _money(c["gross_loss"]),
            "avg_win": _money(_div(c["gross_profit"], c["wins"])),
            "avg_loss": _money(_div(c["gross_loss"], c["losses"])),
            "expectancy": _money(c["net"] / n if n else 0.0),
            "profit_factor": _ratio(_div(c["gross_profit"], abs(c["gross_loss"]))),
            "best_trade": _money(max(nets)) if nets else None,
            "worst_trade": _money(min(nets)) if nets else None,
            "best_r": _ratio(max(rs)) if rs else None,
            "worst_r": _ratio(min(rs)) if rs else None,
            "sum_r": _ratio(c["sum_r"]),
            "avg_r": _ratio(_div(c["sum_r"], len(rs))),
            "pct_trades_ge_1r": _pct(_div(sum(1 for v in rs if v >= 1.0), len(rs))),
            "sum_risk": _money(sum(_f(r.get("risk_amount")) for r in rows)),
        },
        "risk": {
            "max_drawdown": _money(dd["max_drawdown"]),
            "max_dd_pct": _pct(dd["max_dd_pct"]),
            "recovery_factor": _ratio(_div(c["net"], dd["max_drawdown"])),
            "current_drawdown": _money(dd["current_drawdown"]),
            "recovered_pct": _pct(dd["recovered_pct"]),
            "dd_duration_days": _ratio(dd["dd_duration_days"]),
            "recovery_days": _ratio(dd["recovery_days"]),
            "sharpe_r": _ratio(sh["sharpe_r"]),
            "sharpe_r_annual": _ratio(sh["sharpe_r_annual"]),
            "sortino_r": _ratio(sh["sortino_r"]),
            "n_r": sh["n_r"],
            "trades_per_year": _ratio(_div(sh["n_r"], sh["years"])
                                      if sh["years"] else None),
        },
        "streaks": {
            **st,
            "avg_holding_h": _ratio(statistics.fmean(holds)) if holds else None,
            "median_holding_h": _ratio(statistics.median(holds)) if holds else None,
            "max_holding_h": _ratio(max(holds)) if holds else None,
        },
        "balance": {
            "base": _money(base) if known else None,
            "base_kind": "capital" if known else "zero",
            "final_balance": _money(base + c["net"]) if known else None,
            "total_commission": _money(sum(_f(r.get("commission")) for r in rows)),
            "total_swap": _money(sum(_f(r.get("swap")) for r in rows)),
            "total_edge_cost": _money(sum(
                _f((r.get("meta_json") or {}).get("edge_cost_ccy")) for r in rows)),
        },
    }


# ── §3.3 — starting balance ─────────────────────────────────────────────────
def _allocated_capital(ledger) -> dict[str, float]:
    """``strategy_state.allocated_capital`` non nul par stratégie — SELECT
    seul, sur la connexion déjà ouverte du ledger (aucune écriture)."""
    if ledger is None:
        return {}
    out: dict[str, float] = {}
    for row in ledger._conn.execute(  # noqa: SLF001 — lecture pure
            "SELECT strategy_id, allocated_capital FROM strategy_state"):
        cap = _opt_f(row["allocated_capital"])
        if cap:
            out[str(row["strategy_id"])] = cap
    return out


def resolve_bases(rows: list[dict], capital_initial: dict[str, float] | None,
                  ledger=None, *, allocated: dict[str, float] | None = None
                  ) -> dict[str, float | None]:
    """Base par instance, dans l'ordre : (1) ``capital_initial`` de
    l'adaptateur ; (2) ``allocated_capital`` du ledger (par stratégie) ;
    (3) ``account_balance`` du premier trade clos de l'instance ; (4) None."""
    capital_initial = capital_initial or {}
    if allocated is None:
        allocated = _allocated_capital(ledger)
    bases: dict[str, float | None] = {}
    # Repli (3) : « premier trade clos » au sens de §3.3 = ordre open_time
    # (deux trades d'une instance peuvent se chevaucher).
    by_open = sorted(rows, key=lambda r: (str(r.get("open_time") or ""),
                                          str(r.get("close_time") or ""),
                                          _id_key(r)))
    for r in by_open:
        inst = instance_key(r)
        if inst in bases:
            continue
        cap = _opt_f(capital_initial.get(inst))
        if not cap:
            cap = _opt_f(allocated.get(str(r.get("strategy_id"))))
        if not cap:
            cap = _opt_f(r.get("account_balance"))
        bases[inst] = cap if cap else None
    for inst, cap in capital_initial.items():
        bases.setdefault(inst, _opt_f(cap) or None)
    return bases


def currency_base(rows: list[dict], bases: dict[str, float | None],
                  curve_base: str = "auto") -> tuple[float | None, str, list[str]]:
    """Base d'un sous-ensemble (une devise) : somme des bases de ses
    instances si TOUTES sont connues (D-AN-8), sinon zéro.  Rend
    ``(base, base_kind, warnings)``."""
    insts = sorted({instance_key(r) for r in rows})
    unknown = [i for i in insts if not bases.get(i)]
    total = sum(bases[i] for i in insts if bases.get(i))
    if curve_base == "zero" or not insts:
        return None, "zero", []
    if unknown:
        warn = ([f"capital initial inconnu : {', '.join(unknown)} — courbe en base zéro"]
                if curve_base == "capital" else [])
        return None, "zero", warn
    return total, "capital", []


# ── sources de données ──────────────────────────────────────────────────────
class DefaultSources:
    """La fabrique réelle : ledger via ``state.open_ledger()`` (None = absent,
    jamais de création), journaux via ``server.journal_adapter`` importé
    paresseusement (module injectable), manifestes via ``state``."""

    def __init__(self, journal_mod=None) -> None:
        self._journal_mod = journal_mod
        self._journal_error: str | None = None

    # -- ledger ---------------------------------------------------------------
    def closed_rows_ledger(self) -> list[dict] | None:
        ledger = state_mod.open_ledger()
        if ledger is None:
            return None
        try:
            return ledger.closed_trades()
        finally:
            ledger.close()

    def open_rows_ledger(self) -> list[dict] | None:
        ledger = state_mod.open_ledger()
        if ledger is None:
            return None
        try:
            return [dict(r) for r in ledger._conn.execute(  # noqa: SLF001
                "SELECT * FROM trades WHERE close_time IS NULL "
                "ORDER BY open_time, id")]
        finally:
            ledger.close()

    def allocated_capital(self) -> dict[str, float]:
        ledger = state_mod.open_ledger()
        if ledger is None:
            return {}
        try:
            return _allocated_capital(ledger)
        finally:
            ledger.close()

    # -- journaux (adaptateur, lecture seule) ---------------------------------
    def _journal(self):
        if self._journal_mod is None and self._journal_error is None:
            try:
                from server import journal_adapter  # import paresseux
            except ImportError as e:
                self._journal_error = f"adaptateur journaux indisponible : {e}"
            else:
                self._journal_mod = journal_adapter
        if self._journal_mod is None:
            raise RuntimeError(self._journal_error)
        return self._journal_mod

    def closed_rows_journals(self) -> list[dict]:
        return list(self._journal().journal_closed_trades())

    def open_rows_journals(self) -> list[dict]:
        return list(self._journal().journal_open_trades())

    def capital_initial(self) -> dict[str, float]:
        return dict(self._journal().journal_capital_initial())

    def journal_report(self) -> dict:
        return dict(self._journal().journal_report())

    # -- manifestes -----------------------------------------------------------
    def manifests(self) -> dict[str, dict]:
        return read_manifests()


def read_manifests() -> dict[str, dict]:
    """``{S0NN: {display_name, retired, magic, folder}}`` depuis les
    manifestes (mêmes lecteurs que state.py) — un manifeste illisible ne
    fait pas tomber la page : identité repliée sur le dossier."""
    out: dict[str, dict] = {}
    for folder in state_mod.scan_strategy_folders():
        short = state_mod.short_id(folder)
        manifest, _err = state_mod.load_manifest(state_mod.strategies_root() / folder)
        magic = 0
        name, retired = folder, False
        if manifest:
            name = str(manifest.get("display_name") or folder)
            retired = str(manifest.get("status") or "").upper() == "RETIRED"
            try:
                magic = int(manifest.get("magic_number") or 0)
            except (TypeError, ValueError):
                magic = 0
        out[short] = {"display_name": name, "retired": retired,
                      "magic": magic, "folder": folder}
    return out


def _call(sources, name: str, warnings: list[str], default):
    """Appelle ``sources.<name>()`` ; une source qui casse devient un warning
    explicite et un résultat vide (D-AN-16), jamais un 500."""
    fn = getattr(sources, name, None)
    if fn is None:
        return default
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — converti en warning explicite
        warnings.append(f"source {name} illisible : {str(e)[:160]}")
        return default


def collect_rows(filters: Filters, *, sources=None) -> dict:
    """AN-10 / AN-11 — union ledger ∪ journaux dédoublonnée sur
    ``(run_id, source_ref)`` (la ligne ledger prime).  Rend
    ``{rows, open_rows, source, warnings}`` ; ``rows`` = lignes §3.1 de
    TOUS les modes (le filtre s'applique ensuite)."""
    sources = sources if sources is not None else DefaultSources()
    warnings: list[str] = []
    use_ledger = filters.source in ("auto", "ledger")
    use_journals = filters.source in ("auto", "journals")

    ledger_rows: list[dict] = []
    open_rows: list[dict] = []
    ledger_present = False
    if use_ledger:
        raw = _call(sources, "closed_rows_ledger", warnings, None)
        if raw is None:
            warnings.append("ledger absent")
        else:
            ledger_present = True
            ledger_rows = normalize_rows(raw, "ledger", warnings)
            raw_open = _call(sources, "open_rows_ledger", warnings, None) or []
            open_rows.extend(_normalize_open(raw_open, "ledger"))

    journal_rows: list[dict] = []
    studies: dict = {}
    if use_journals:
        raw = _call(sources, "closed_rows_journals", warnings, [])
        journal_rows = normalize_rows(raw, "journal", warnings)
        raw_open = _call(sources, "open_rows_journals", warnings, [])
        open_rows.extend(_normalize_open(raw_open, "journal"))
        report = _call(sources, "journal_report", warnings, {}) or {}
        studies = dict(report.get("studies") or {})
        for w in report.get("warnings") or []:
            if w not in warnings:
                warnings.append(str(w))

    seen = {(r.get("run_id"), r.get("source_ref")) for r in ledger_rows
            if r.get("source_ref") is not None}
    dedup = 0
    kept_journal = []
    for r in journal_rows:
        if (r.get("run_id"), r.get("source_ref")) in seen:
            dedup += 1
            continue
        kept_journal.append(r)

    return {
        "rows": sort_rows(ledger_rows + kept_journal),
        "open_rows": open_rows,
        "source": {"ledger_rows": len(ledger_rows),
                   "journal_rows": len(kept_journal), "dedup": dedup,
                   "ledger_present": ledger_present, "studies": studies},
        "warnings": warnings,
    }


# ── §3.4 — positions ouvertes ───────────────────────────────────────────────
def _normalize_open(rows: list[dict], source: str) -> list[dict]:
    out = []
    for raw in rows:
        meta = _decode_meta(raw.get("meta_json"))
        arm = raw.get("arm") if raw.get("arm") is not None else meta.get("arm")
        out.append({
            "source": source,
            "strategy_id": raw.get("strategy_id"),
            "instance_id": raw.get("instance_id"),
            "mode": raw.get("mode"),
            "symbol": raw.get("symbol"),
            "side": raw.get("side"),
            "open_time": raw.get("open_time"),
            "open_price": raw.get("open_price"),
            "stop_price": raw.get("stop_price"),
            "target_price": raw.get("target_price"),
            "volume_lots": raw.get("volume_lots"),
            "risk_amount": _opt_f(raw.get("risk_amount")),
            "arm": str(arm) if arm not in (None, "") else None,
        })
    return out


def open_positions(open_rows: list[dict], filters: Filters, *,
                   now: datetime | None = None) -> list[dict]:
    """AN-30 — filtrées par mode / stratégie / instance / symbole / arm
    seulement ; ``age_h`` depuis ``open_time`` ; jamais de P&L flottant."""
    now = now or datetime.now(timezone.utc)
    out = []
    for p in open_rows:
        if p.get("mode") != filters.mode:
            continue
        if filters.strategy and p.get("strategy_id") not in filters.strategy:
            continue
        if filters.instance and p.get("instance_id") not in filters.instance:
            continue
        if filters.symbol and p.get("symbol") not in filters.symbol:
            continue
        if filters.arm and (p.get("arm") or "none") not in filters.arm:
            continue
        opened = state_mod.parse_utc(p.get("open_time"))
        age = ((now - opened).total_seconds() / 3600.0
               if opened is not None else None)
        out.append({**p, "risk_amount": _money(p.get("risk_amount")),
                    "age_h": _ratio(age)})
    return sorted(out, key=lambda p: (str(p.get("open_time") or ""),
                                      str(p.get("instance_id") or "")))


# ── assemblage — GET /api/analytics ─────────────────────────────────────────
def _source_kind(rows: list[dict]) -> str:
    kinds = {r.get("source") for r in rows}
    if not kinds:
        return "aucune"
    if kinds == {"ledger"}:
        return "ledger"
    if kinds == {"journal"}:
        return "journaux"
    return "mixte"


def _currency_block(rows: list[dict], base: float | None, filters: Filters,
                    bases: dict, manifests: dict, local_tz) -> dict:
    return {
        "kpi": kpi(rows, base),
        "curve": curve(rows, base, local_tz=local_tz),
        "heatmap": heatmap(rows, base, local_tz=local_tz),
        "by_month": by_month(rows, base, local_tz=local_tz),
        "by_instance": by_key(rows, "instance", bases=bases),
        "by_symbol": by_key(rows, "symbol", bases=bases),
        "by_strategy": by_key(rows, "strategy", bases=bases, manifests=manifests),
        "by_weekday": by_key(rows, "weekday", weekday_key=filters.weekday_key,
                             local_tz=local_tz),
        "by_hour": by_key(rows, "hour", local_tz=local_tz),
        "distribution": distribution(rows, filters.dist_unit),
        "summary": summary(rows, base),
    }


def build_analytics(args, *, sources=None, local_tz: tzinfo | None = None,
                    now: datetime | None = None) -> dict:
    """Le payload complet §6.1.  ``ValueError`` (filtre hors domaine) remonte
    à la route ; tout le reste dégrade en warnings."""
    filters = parse_filters(args)
    sources = sources if sources is not None else DefaultSources()
    collected = collect_rows(filters, sources=sources)
    warnings = list(collected["warnings"])
    all_rows = collected["rows"]
    manifests = _call(sources, "manifests", warnings, {}) or {}
    rows = filter_rows(all_rows, filters, local_tz)

    capital_initial = (_call(sources, "capital_initial", warnings, {}) or {}
                       if filters.source != "ledger" else {})
    allocated = (_call(sources, "allocated_capital", warnings, {}) or {}
                 if filters.source != "journals" else {})
    # Bases résolues sur les lignes du MODE demandé seulement (D-AN-5) : le
    # premier account_balance d'une instance BACKTEST ne sert jamais de base
    # à sa courbe PAPER.
    mode_rows = [r for r in all_rows if r.get("mode") == filters.mode]
    bases = resolve_bases(mode_rows, capital_initial, None, allocated=allocated)

    by_ccy: dict[str, dict] = {}
    header_base: dict[str, float | None] = {}
    kinds: list[str] = []
    for ccy in sorted({str(r.get("currency") or "CHF") for r in rows}):
        sub = [r for r in rows if str(r.get("currency") or "CHF") == ccy]
        base, kind, warns = currency_base(sub, bases, filters.curve_base)
        warnings.extend(warns)
        header_base[ccy] = _money(base) if kind == "capital" else None
        kinds.append(kind)
        by_ccy[ccy] = _currency_block(sub, base, filters, bases, manifests,
                                      local_tz)

    header = {
        "mode": filters.mode,
        "n_strategies": len({r.get("strategy_id") for r in rows}),
        "n_instances": len({instance_key(r) for r in rows}),
        "n_trades": len(rows),
        "base": header_base,
        "base_kind": "capital" if kinds and all(k == "capital" for k in kinds)
        else "zero",
        "source_kind": _source_kind(rows),
    }
    return {
        "generated": _generated(),
        "version": _version(),
        "filters": {"applied": filters.applied(),
                    "options": options(all_rows, filters, local_tz=local_tz,
                                       manifests=manifests)},
        "source": collected["source"],
        "header": header,
        "by_currency": by_ccy,
        "open_positions": open_positions(collected["open_rows"], filters,
                                         now=now),
        "warnings": warnings,
    }


# ── AN-28 — journal des trades ──────────────────────────────────────────────
def trade_row_out(row: dict, manifests: dict[str, dict] | None) -> dict:
    """Ligne §3.1 sans ``meta_json`` brut, avec ``pnl_r``, ``arm``,
    ``source``, ``holding_h``, ``edge_cost_ccy``, ``magic_ok``."""
    out = {k: row.get(k) for k in ROW_KEYS if k != "meta_json"}
    meta = row.get("meta_json") or {}
    for k in ("gross_pnl", "commission", "swap", "net_pnl", "risk_amount",
              "account_balance"):
        out[k] = _money(_opt_f(row.get(k)))
    out["source"] = row.get("source")
    out["source_ref"] = row.get("source_ref")
    out["pnl_r"] = _ratio(row.get("pnl_r"))
    out["arm"] = row.get("arm")
    out["holding_h"] = _ratio(holding_hours(row))
    out["edge_cost_ccy"] = _money(_opt_f(meta.get("edge_cost_ccy")))
    out["magic_ok"] = magic_ok(row, manifests)
    return out


def build_trades_page(args, *, sources=None, local_tz: tzinfo | None = None
                      ) -> dict:
    """``{generated, version, total, page, limit, rows, warnings}`` — mêmes
    filtres qu'AN-4, tri serveur ``close_time desc`` fixe, pagination."""
    filters = parse_filters(args)
    page, limit = parse_paging(args)
    sources = sources if sources is not None else DefaultSources()
    collected = collect_rows(filters, sources=sources)
    warnings = list(collected["warnings"])
    manifests = _call(sources, "manifests", warnings, {}) or {}
    rows = list(reversed(filter_rows(collected["rows"], filters, local_tz)))
    start = (page - 1) * limit
    return {
        "generated": _generated(),
        "version": _version(),
        "total": len(rows),
        "page": page,
        "limit": limit,
        "rows": [trade_row_out(r, manifests) for r in rows[start:start + limit]],
        "warnings": warnings,
    }


# ── AN-31 — bandeau KPI de la vue d'ensemble ────────────────────────────────
def build_kpi(*, sources=None) -> dict:
    """``{generated, version, PAPER: {ccy: kpi}, LIVE: {ccy: kpi}, warnings}``
    — sans filtre, source ``auto`` ; jamais BACKTEST, jamais de fusion."""
    sources = sources if sources is not None else DefaultSources()
    filters = Filters()
    collected = collect_rows(filters, sources=sources)
    warnings = list(collected["warnings"])
    capital_initial = _call(sources, "capital_initial", warnings, {}) or {}
    allocated = _call(sources, "allocated_capital", warnings, {}) or {}
    out: dict = {"generated": _generated(), "version": _version()}
    for mode in ("PAPER", "LIVE"):
        block: dict[str, dict] = {}
        rows = [r for r in collected["rows"] if r.get("mode") == mode]
        # Bases par mode (D-AN-5), comme dans build_analytics.
        bases = resolve_bases(rows, capital_initial, None, allocated=allocated)
        for ccy in sorted({str(r.get("currency") or "CHF") for r in rows}):
            sub = [r for r in rows if str(r.get("currency") or "CHF") == ccy]
            base, _kind, _w = currency_base(sub, bases, "auto")
            block[ccy] = kpi(sub, base)
        out[mode] = block
    out["warnings"] = warnings
    return out
