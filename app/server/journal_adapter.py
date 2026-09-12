"""
server/journal_adapter.py — les journaux forward lus comme des trades ledger.
============================================================================

Le ledger est vide (0 ligne) alors que la seule donnée réelle de la
plateforme vit dans les journaux CSV des études scellées
(``db_dir()/<étude>/journal.csv``). Ce module les rend consommables par
``server/analytics.py`` en produisant, EN MÉMOIRE, des lignes au format exact
de ``Ledger.closed_trades()`` (31 clés + ``instance_id``) enrichies de
``source`` / ``source_ref`` / ``pnl_r`` / ``arm`` (SPEC_analytics-trades §3.1,
§3.2). Il n'écrit JAMAIS rien : ni ledger, ni journal, ni dossier (UI-7,
AN-12, D-AN-3).

Entrées lues (jamais créées) :
  - ``db_dir()/<étude>/journal.csv``  — les événements OPEN / CLOSE chaînés
    SHA-256 (les SHADOW_* et DECISION d'alexg sont ignorés) ;
  - ``db_dir()/<étude>/state.json``   — ``started_at`` + empreinte du journal
    au dernier passage (second contrôle d'intégrité) ;
  - ``project_root()/studies/<étude>/params.json`` — ``sizing.capital_initial``,
    ``timeframe``, ``spec`` / ``specs`` (symbole, pip, spread, slippage) ;
  - ``project_root()/strategies/S0NN_*/manifest.yaml`` — ``version``,
    ``magic_number`` (via ``server.state``, jamais recopié).

Journal absent, ``params.json`` absent, fichier illisible ou chaîne altérée
⇒ jamais d'exception : résultat réduit + ``warnings[]`` explicites
(D-AN-16). La chaîne SHA-256 est vérifiée par le MÊME algorithme que
``verify_journal`` des études, réimplémenté ici : le serveur de supervision
n'importe jamais le code d'une étude (AN-12).

Horodatage : ``bar_time`` est naïf en heure serveur MT5 (≈ UTC+2/+3, cf.
``core/data/source.py``). La conversion en UTC applique la règle DST UE
(``SERVER_OFFSET_RULE``, injectable pour les tests) ; ``measured_at_utc``
sert de garde-fou (une barre ne peut pas être postérieure à sa mesure).
"""
from __future__ import annotations

import csv
import hashlib
import io
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from core.paths import db_dir, project_root
from server import state as state_mod
from server.state import STUDIES, declared_instances, load_json_quiet, parse_utc

# Catalogue fixe (dossier étude sous db_dir(), stratégie instanciée) — §3.2 :
# ``server.state.STUDIES`` (source unique, s14_sentiment exclue : pas de journal).
STUDY_STRATEGY: dict[str, str] = dict(STUDIES)

# Constantes d'étude : les journaux ne nomment ni la devise ni le mode
# (D-AN-5 / D-AN-6, DF-9).
JOURNAL_CURRENCY = "CHF"
JOURNAL_MODE = "PAPER"
# Un journal sans colonne ``arm`` (gold) ne porte qu'un bras : le principal.
DEFAULT_ARM = "PRIMARY"
# Valeur de repli quand le manifeste ne donne pas de version.
STUDY_VERSION = "study"

# Raisons de sortie admises par le ledger ; tout le reste devient MANUAL.
EXIT_REASONS = frozenset({"SL", "TP", "TRAIL", "MANUAL", "HALT", "EOD"})

# Les 31 clés de ``Ledger.closed_trades()`` (30 colonnes + instance_id),
# dans l'ordre du SELECT * — le contrat §3.1.
LEDGER_KEYS: tuple[str, ...] = (
    "id", "strategy_id", "strategy_version", "magic_number", "mode",
    "run_id", "symbol", "timeframe", "ticket", "side", "volume_lots",
    "open_time", "open_price", "close_time", "close_price", "stop_price",
    "target_price", "exit_reason", "gross_pnl", "commission", "swap",
    "net_pnl", "currency", "signal_reason", "confidence", "risk_distance",
    "risk_amount", "account_balance", "meta_json", "created_at",
    "instance_id",
)
# Les clés ajoutées par la couche source (§3.1).
SOURCE_KEYS: tuple[str, ...] = ("source", "source_ref", "pnl_r", "arm")

OPEN_EVENT = "OPEN"
CLOSE_EVENT = "CLOSE"


# ── fuseau serveur MT5 → UTC (§3.2, DF-8) ───────────────────────────────────
def last_sunday(year: int, month: int) -> date:
    """Dernier dimanche d'un mois (bascules DST UE : mars et octobre)."""
    last = date(year, month, 1) + timedelta(days=31)
    last = last.replace(day=1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def eu_dst_offset_hours(bar_time: datetime) -> int:
    """Offset (heures) serveur MT5 − UTC pour une barre en heure serveur
    naïve : +3 en heure d'été européenne, +2 sinon. La fenêtre d'été va du
    dernier dimanche de mars 01:00 UTC au dernier dimanche d'octobre
    01:00 UTC ; la barre est ramenée en UTC avec l'offset d'hiver pour
    situer la bascule (l'heure ambiguë de la bascule est négligée)."""
    guess_utc = bar_time - timedelta(hours=2)
    year = guess_utc.year
    start = datetime.combine(last_sunday(year, 3), datetime.min.time()) \
        + timedelta(hours=1)
    end = datetime.combine(last_sunday(year, 10), datetime.min.time()) \
        + timedelta(hours=1)
    return 3 if start <= guess_utc < end else 2


# Règle injectable : ``callable(bar_time naïf) -> offset heures``. Les tests
# la remplacent (monkeypatch) ou passent ``offset_rule=`` explicitement.
SERVER_OFFSET_RULE: Callable[[datetime], int] = eu_dst_offset_hours


def bar_time_to_utc(value, offset_rule: Callable[[datetime], int] | None = None
                    ) -> datetime | None:
    """``bar_time`` du journal (ISO naïf, heure serveur) → datetime UTC
    aware ; None si vide ou illisible. Une valeur déjà zonée est respectée."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    rule = offset_rule or SERVER_OFFSET_RULE
    return (dt - timedelta(hours=int(rule(dt)))).replace(tzinfo=timezone.utc)


def iso_z(dt: datetime | None) -> str | None:
    """Datetime UTC → ``YYYY-MM-DDTHH:MM:SSZ`` (convention ledger D-LG-5)."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── petites conversions défensives ──────────────────────────────────────────
def to_float(value) -> float | None:
    """Cellule CSV → float, None si vide ou non numérique (jamais d'exception)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_exit_reason(value) -> str:
    """``SL`` / ``TP`` (et le reste du domaine ledger) conservés, sinon
    ``MANUAL`` — le domaine du ledger est le contrat §3.1."""
    text = str(value or "").strip().upper()
    return text if text in EXIT_REASONS else "MANUAL"


def instance_id_of(strategy_id: str, symbol: str) -> str:
    """``instance_id`` par la RÈGLE de ``declared_instances`` (state.py) :
    paire FX 6 lettres → ``S0NN.XXX-YYY``, sinon ``S0NN.<SYMBOL>``."""
    ids = declared_instances(strategy_id, {"symbols": [symbol]})
    return ids[0] if ids else f"{strategy_id}.{symbol}"


def edge_cost_ccy(spec: dict | None, risk_ccy: float | None,
                  risk_distance: float | None) -> float | None:
    """Coût de bord en devise d'un trade : demi-spread + slippage payés aux
    DEUX extrémités (formule ``edge_cost_of`` des études), convertis en
    devise via le ratio risque / distance de stop. None si la spec est
    incomplète ou le ratio indéfini."""
    if not isinstance(spec, dict):
        return None
    try:
        edge = (float(spec["spread_pips"]) * float(spec["pip"]) / 2.0
                + float(spec["slippage_pips"]) * float(spec["pip"]))
    except (KeyError, TypeError, ValueError):
        return None
    if risk_ccy is None or not risk_distance:
        return None
    return 2.0 * edge * risk_ccy / risk_distance


# ── chaîne SHA-256 (réimplémentation de verify_journal, AN-12) ──────────────
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_journal_text(text: str) -> tuple[list[str], list[list[str]]]:
    """Texte du journal → (colonnes d'en-tête, lignes de cellules). Une ligne
    par enregistrement, comme l'écrit ``append_journal`` (jamais de retour à
    la ligne embarqué) — le découpage est celui de ``verify_journal``."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        return [], []
    # ``next(..., [])`` : un journal réduit à des sauts de ligne a une
    # première ligne vide — csv.reader n'y rend rien, jamais de
    # StopIteration hors de la fonction.
    header = next(csv.reader(io.StringIO(lines[0])), [])
    if not header:
        return [], []
    rows = [next(csv.reader(io.StringIO(line)), []) if line else []
            for line in lines[1:]]
    return header, rows


def verify_chain(text: str) -> str | None:
    """Contrôle interne : chaque ligne porte le SHA-256 du fichier tel qu'il
    était AVANT elle. Retourne None si la chaîne tient, sinon le motif."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        return "journal vide sans en-tête"
    n_cols = len(next(csv.reader(io.StringIO(lines[0])), []))
    if n_cols == 0:
        return "journal vide sans en-tête"
    running = lines[0] + "\n"
    for k, line in enumerate(lines[1:], start=2):
        cells = next(csv.reader(io.StringIO(line)), []) if line else []
        if len(cells) != n_cols:
            return f"ligne {k} : {len(cells)} colonnes au lieu de {n_cols}"
        expected = sha256_bytes(running.encode("utf-8"))
        if cells[-1] != expected:
            return (f"chaîne cassée à la ligne {k} (maillon attendu "
                    f"{expected[:16]}…, lu {cells[-1][:16]}…)")
        running += line + "\n"
    return None


def verify_state_fingerprint(raw: bytes, state: dict | None) -> str | None:
    """Second contrôle : ``state.json`` mémorise (taille, SHA-256) du journal
    au dernier passage — un journal reconstruit à chaîne cohérente mais
    contenu différent est attrapé ici. None si cohérent ou sans empreinte."""
    if not isinstance(state, dict):
        return None
    try:
        n = int(state.get("journal_bytes") or 0)
    except (TypeError, ValueError):
        return None
    sha = state.get("journal_sha256") or ""
    if n <= 0:
        return None
    if len(raw) < n:
        return f"journal tronqué : {len(raw)} octets, {n} attendus au minimum"
    if sha and sha256_bytes(raw[:n]) != sha:
        return ("le préfixe du journal ne correspond plus à l'empreinte du "
                "dernier passage")
    return None


# ── params.json : symbole, spec, capital ────────────────────────────────────
def study_symbol(params: dict) -> str | None:
    """Symbole constant d'une étude mono-instrument (journal sans colonne
    ``symbol``) : ``instrument``, sinon ``spec.symbol``, sinon
    ``primary_symbol``."""
    if isinstance(params.get("instrument"), str) and params["instrument"]:
        return params["instrument"]
    spec = params.get("spec")
    if isinstance(spec, dict) and isinstance(spec.get("symbol"), str):
        return spec["symbol"]
    if isinstance(params.get("primary_symbol"), str):
        return params["primary_symbol"]
    return None


def spec_for(params: dict, symbol: str | None) -> dict | None:
    """La spec de coûts d'un symbole : ``specs[symbol]`` (multi-instruments)
    ou ``spec`` (mono-instrument)."""
    specs = params.get("specs")
    if isinstance(specs, dict) and symbol in specs \
            and isinstance(specs[symbol], dict):
        return specs[symbol]
    spec = params.get("spec")
    if isinstance(spec, dict):
        declared = spec.get("symbol")
        if declared is None or symbol is None or declared == symbol:
            return spec
    return None


def capital_initial_of(params: dict) -> float | None:
    sizing = params.get("sizing")
    if not isinstance(sizing, dict):
        return None
    return to_float(sizing.get("capital_initial"))


def capital_instances(params: dict) -> list[str]:
    """Symboles dont le capital initial est propre à l'instance : l'unique
    instrument (gold) ou les entrées d'``instruments`` en mapping
    symbole → bras (s13/s20 : 10 000 PAR bras). Une liste d'instruments
    (alexg, macd_ai) partage un capital par bras entre tous ses symboles :
    il n'est pas attribuable par instance et reste inconnu (§3.3 repli)."""
    instruments = params.get("instruments")
    if isinstance(instruments, dict):
        return [str(s) for s in instruments]
    single = study_symbol(params)
    return [single] if single else []


# ── lecture d'une étude ─────────────────────────────────────────────────────
class _StudyRead:
    """Résultat de lecture d'une étude : lignes clos / ouvertes, entrée de
    rapport, capital par instance, warnings. Objet interne, jamais servi."""

    def __init__(self, folder: str, strategy_id: str) -> None:
        self.folder = folder
        self.strategy_id = strategy_id
        self.closed: list[dict] = []
        self.open: list[dict] = []
        self.capital: dict[str, float] = {}
        self.warnings: list[str] = []
        self.report: dict | None = None


def _manifest_of(strategy_id: str) -> dict | None:
    """Manifeste de la stratégie instanciée (résolution state.py) — None si
    aucun dossier ``S0NN_*`` ou manifeste illisible (repli version/magic)."""
    folder = state_mod.resolve_folder(strategy_id)
    if folder is None:
        return None
    manifest, _err = state_mod.load_manifest(state_mod.strategies_root() / folder)
    return manifest


def _first_float(closed: dict, opened: dict, column: str) -> float | None:
    """Valeur numérique portée par le CLOSE, sinon par l'OPEN (les deux
    lignes répètent les champs d'entrée ; le CLOSE fait foi)."""
    value = to_float(closed.get(column))
    return value if value is not None else to_float(opened.get(column))


def _build_closed(study: _StudyRead, key: tuple, opened: dict, closed: dict,
                  params: dict, manifest: dict | None, chain_ok: bool) -> dict:
    """Une ligne §3.1 depuis la paire OPEN / CLOSE d'un même trade."""
    trade_id, symbol, arm = key
    strategy_id = study.strategy_id
    entry = _first_float(closed, opened, "entry_price")
    stop = _first_float(closed, opened, "stop_price")
    risk_ccy = _first_float(closed, opened, "risk_ccy")
    risk_distance = (abs(entry - stop) if entry is not None and stop is not None
                     else None)
    pnl = to_float(closed.get("pnl_ccy"))
    version = STUDY_VERSION
    magic = 0
    if manifest:
        if manifest.get("version") not in (None, ""):
            version = str(manifest["version"])
        try:
            magic = int(manifest.get("magic_number") or 0)
        except (TypeError, ValueError):
            magic = 0
    meta = {
        "arm": arm,
        "trade_id": trade_id,
        "pnl_r": to_float(closed.get("pnl_r")),
        "capital_after": to_float(closed.get("capital_after")),
        "measured_at_utc_open": opened.get("measured_at_utc") or None,
        "measured_at_utc_close": closed.get("measured_at_utc") or None,
        "edge_cost_ccy": edge_cost_ccy(spec_for(params, symbol), risk_ccy,
                                       risk_distance),
        "chain_ok": chain_ok,
    }
    reason = (closed.get("reason") or opened.get("reason") or "").strip()
    return {
        "id": None,
        "strategy_id": strategy_id,
        "strategy_version": version,
        "magic_number": magic,
        "mode": JOURNAL_MODE,
        "run_id": study.folder,
        "symbol": symbol,
        "timeframe": params.get("timeframe"),
        "ticket": None,
        "side": (closed.get("side") or opened.get("side") or "").strip().upper()
        or None,
        "volume_lots": _first_float(closed, opened, "size_lots"),
        "open_time": opened["_utc"],
        "open_price": entry,
        "close_time": closed["_utc"],
        "close_price": to_float(closed.get("exit_price")),
        "stop_price": stop,
        "target_price": _first_float(closed, opened, "target_price"),
        "exit_reason": normalize_exit_reason(closed.get("exit_reason")),
        "gross_pnl": pnl,
        "commission": 0.0,
        "swap": 0.0,
        "net_pnl": pnl,
        "currency": JOURNAL_CURRENCY,
        "signal_reason": reason or None,
        "confidence": None,
        "risk_distance": risk_distance,
        "risk_amount": risk_ccy,
        "account_balance": to_float(opened.get("capital_after")),
        "meta_json": meta,
        "created_at": closed.get("measured_at_utc") or None,
        "instance_id": instance_id_of(strategy_id, symbol),
        "source": "journal",
        "source_ref": trade_id,
        "pnl_r": meta["pnl_r"],
        "arm": arm,
    }


def _build_open(study: _StudyRead, key: tuple, opened: dict,
                now: datetime) -> dict:
    """Une position ouverte §3.4 depuis un OPEN sans CLOSE (jamais de P&L
    flottant : le status.json de l'instance reste la source du vivant)."""
    trade_id, symbol, arm = key
    open_utc = parse_utc(opened["_utc"])
    age_h = ((now - open_utc).total_seconds() / 3600.0
             if open_utc is not None else None)
    return {
        "source": "journal",
        "strategy_id": study.strategy_id,
        "instance_id": instance_id_of(study.strategy_id, symbol),
        "mode": JOURNAL_MODE,
        "symbol": symbol,
        "side": (opened.get("side") or "").strip().upper() or None,
        "open_time": opened["_utc"],
        "open_price": to_float(opened.get("entry_price")),
        "stop_price": to_float(opened.get("stop_price")),
        "target_price": to_float(opened.get("target_price")),
        "volume_lots": to_float(opened.get("size_lots")),
        "risk_amount": to_float(opened.get("risk_ccy")),
        "arm": arm,
        "age_h": age_h,
    }


def read_study(folder: str, strategy_id: str, *,
               offset_rule: Callable[[datetime], int] | None = None,
               now: datetime | None = None) -> _StudyRead:
    """Lecture complète d'une étude — jamais d'exception, jamais d'écriture.

    Journal ou params.json absent ⇒ ``report`` None (étude hors rapport) +
    warning. Journal illisible ou chaîne altérée ⇒ signalé, les lignes
    lisibles sont servies quand même avec ``chain_ok = False`` (§3.2)."""
    study = _StudyRead(folder, strategy_id)
    now = now or state_mod.utc_now()
    journal_path = db_dir() / folder / "journal.csv"
    params_path = project_root() / "studies" / folder / "params.json"
    state_path = db_dir() / folder / "state.json"

    if not journal_path.is_file():
        # state.json mémorise la taille du journal au dernier passage : un
        # journal absent alors qu'il pesait > 0 octet est une suppression
        # (même lecture que verify_journal des études).
        prior = load_json_quiet(state_path) if state_path.is_file() else None
        prior_bytes = to_float(prior.get("journal_bytes")) if isinstance(prior, dict) else None
        if prior_bytes:
            study.warnings.append(
                f"journal absent : {folder} — suppression détectée "
                f"(state.json en référençait {int(prior_bytes)} octets)")
        else:
            study.warnings.append(f"journal absent : {folder}")
        return study
    params = load_json_quiet(params_path)
    if params is None:
        study.warnings.append(f"params.json absent ou illisible : {folder}")
        return study

    report = {"strategy_id": strategy_id, "rows": 0, "closed": 0, "open": 0,
              "chain_ok": True, "path": str(journal_path),
              "started_at": None, "capital_initial": capital_initial_of(params)}
    study.report = report

    capital = capital_initial_of(params)
    if capital is not None:
        for symbol in capital_instances(params):
            study.capital[instance_id_of(strategy_id, symbol)] = capital

    state = None
    if state_path.is_file():
        state = load_json_quiet(state_path)
        if state is None:
            study.warnings.append(f"state.json illisible : {folder}")
        else:
            report["started_at"] = state.get("started_at")
    else:
        study.warnings.append(f"state.json absent : {folder}")

    try:
        raw = journal_path.read_bytes()
    except OSError as e:
        report["chain_ok"] = False
        study.warnings.append(f"journal illisible : {folder} ({e.__class__.__name__})")
        return study
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        report["chain_ok"] = False
        study.warnings.append(f"journal illisible : {folder} (encodage non UTF-8)")
        return study

    problem = verify_chain(text) or verify_state_fingerprint(raw, state)
    if problem is not None:
        report["chain_ok"] = False
        study.warnings.append(f"journal altéré : {folder} — {problem}")
    chain_ok = report["chain_ok"]

    header, rows = parse_journal_text(text)
    report["rows"] = len(rows)
    if not header:
        study.warnings.append(f"journal vide sans en-tête : {folder}")
        return study

    default_symbol = study_symbol(params)
    manifest = _manifest_of(strategy_id)
    opens: dict[tuple, dict] = {}
    closes: dict[tuple, dict] = {}
    for k, cells in enumerate(rows, start=2):
        if len(cells) != len(header):
            # Déjà signalé par la chaîne ; la ligne n'est pas exploitable.
            continue
        row = dict(zip(header, cells))
        event = (row.get("event") or "").strip().upper()
        if event not in (OPEN_EVENT, CLOSE_EVENT):
            continue
        symbol = (row.get("symbol") or "").strip() or default_symbol
        if not symbol:
            study.warnings.append(
                f"{folder} ligne {k} : symbole inconnu (ni colonne ni params.json)")
            continue
        arm = (row.get("arm") or "").strip().upper() or DEFAULT_ARM
        trade_id = (row.get("trade_id") or "").strip()
        if not trade_id:
            study.warnings.append(f"{folder} ligne {k} : trade_id vide")
            continue
        bar_utc = bar_time_to_utc(row.get("bar_time"), offset_rule)
        if bar_utc is None:
            study.warnings.append(
                f"{folder} ligne {k} : bar_time illisible ({row.get('bar_time')!r})")
            continue
        measured = parse_utc(row.get("measured_at_utc"))
        if measured is not None and bar_utc > measured:
            study.warnings.append(
                f"{folder} ligne {k} : bar_time {iso_z(bar_utc)} postérieur à "
                f"measured_at_utc {iso_z(measured)} — offset serveur suspect")
        row["_utc"] = iso_z(bar_utc)
        key = (trade_id, symbol, arm)
        bucket = opens if event == OPEN_EVENT else closes
        if key in bucket:
            study.warnings.append(
                f"{folder} ligne {k} : {event} en double pour {trade_id} "
                f"({symbol}/{arm}) — dernière occurrence retenue")
        bucket[key] = row

    for key, closed in closes.items():
        opened = opens.get(key)
        if opened is None:
            study.warnings.append(
                f"{folder} : CLOSE sans OPEN pour {key[0]} ({key[1]}/{key[2]}) — ignoré")
            continue
        study.closed.append(_build_closed(study, key, opened, closed, params,
                                          manifest, chain_ok))
    for key, opened in opens.items():
        if key not in closes:
            study.open.append(_build_open(study, key, opened, now))

    report["closed"] = len(study.closed)
    report["open"] = len(study.open)
    return study


# ── API publique (§3.2) ─────────────────────────────────────────────────────
def _selected(studies) -> tuple[list[tuple[str, str]], list[str]]:
    """Catalogue restreint à ``studies`` (dossiers) ; inconnu ⇒ warning."""
    if studies is None:
        return list(STUDIES), []
    wanted = [str(s) for s in studies]
    warnings = [f"étude inconnue du catalogue : {s}"
                for s in wanted if s not in STUDY_STRATEGY]
    return [(f, sid) for f, sid in STUDIES if f in wanted], warnings


def _read_all(studies=None, *, offset_rule=None, now=None) -> dict:
    """Lecture de tout le catalogue (ou d'un sous-ensemble) à l'appel —
    aucun cache (UI-1)."""
    selected, warnings = _selected(studies)
    closed: list[dict] = []
    opened: list[dict] = []
    capital: dict[str, float] = {}
    report: dict[str, dict] = {}
    for folder, sid in selected:
        st = read_study(folder, sid, offset_rule=offset_rule, now=now)
        warnings.extend(st.warnings)
        closed.extend(st.closed)
        opened.extend(st.open)
        capital.update(st.capital)
        if st.report is not None:
            report[folder] = st.report
    closed.sort(key=lambda r: (r["close_time"] or "", r["source_ref"] or ""))
    opened.sort(key=lambda r: (r["open_time"] or "", r["instance_id"] or ""))
    return {"closed": closed, "open": opened, "capital": capital,
            "studies": report, "warnings": warnings}


def journal_closed_trades(*, studies=None, offset_rule=None) -> list[dict]:
    """Trades clos des journaux au format §3.1, triés ``close_time`` puis
    ``source_ref`` (§3.5). Liste vide sans journal — jamais d'exception."""
    return _read_all(studies, offset_rule=offset_rule)["closed"]


def journal_open_trades(*, studies=None, offset_rule=None, now=None) -> list[dict]:
    """Positions ouvertes §3.4 (OPEN sans CLOSE), hors de toute statistique."""
    return _read_all(studies, offset_rule=offset_rule, now=now)["open"]


def journal_capital_initial(*, studies=None) -> dict[str, float]:
    """``{instance_id: capital_initial}`` depuis ``params.json.sizing`` —
    par bras, donc par instance (gold, s13, s20)."""
    return _read_all(studies)["capital"]


def journal_report(*, studies=None, offset_rule=None) -> dict:
    """``{studies: {<étude>: {strategy_id, rows, closed, open, chain_ok,
    path, started_at, capital_initial}}, warnings: [...]}`` — les études
    sans journal ou sans params.json sont absentes de ``studies`` et
    présentes dans ``warnings``."""
    data = _read_all(studies, offset_rule=offset_rule)
    return {"studies": data["studies"], "warnings": data["warnings"]}
