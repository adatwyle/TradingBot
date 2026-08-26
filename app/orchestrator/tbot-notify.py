#!/usr/bin/env python3
"""
tbot-notify.py — LE NOTIFIER TELEGRAM DE TRADINGBOT (bot dédié, sortant)
=========================================================================

Worker « tick » de la tbot factory (SPEC_telegram-reporting.md §3) : la source
des trades est le LEDGER (core/ledger — modes PAPER et LIVE uniquement, jamais
BACKTEST), les formats sont EXACTEMENT ceux d'Adrian (chapitre 07) :

    10:53 S001.CHF-USD SL -100chf          ← ligne live à la clôture (TG-3)
    📒 TradingBot — 26.08.2026             ← récap quotidien (TG-4)
    — Semaine 35 (24.08–28.08) —           ← section hebdo le vendredi (TG-5)
    📒 Mois d'août 2026                    ← récap mensuel + 12 mois (TG-6)
    📒 Année 2026                          ← récap annuel (TG-7)

Nouveau canal : bot Telegram DÉDIÉ TradingBot (les bots du prototype ne sont
pas réutilisés). Token brut dans C:/db/tradingBot/tbot-notify/token.txt,
chat_id dans config.json — absents, le worker est INERTE : sortie 2 SANS
BRUIT (TCK-007), la factory réessaie sans crier. L'état vit dans un dossier
PROPRE à ce worker (`tbot-notify/`, seam TBOT_NOTIFY_DIR) : AUCUN partage
avec les dossiers ni les variables d'environnement du prototype robinbot
(`ROBINBOT_*`, `notifier/`) — deux bots, deux curseurs.

LES CURSEURS N'AVANCENT QU'APRÈS UN ENVOI RÉUSSI (héritage robinbot-notify)
----------------------------------------------------------------------------
Curseur des trades notifiés = tuple (close_time, id) dans state.json (D-TG-6).
Le close est un UPDATE : l'ordre des id ne suit PAS l'ordre des clôtures — un
trade ouvert tôt (petit id) qui clôt tard est rattrapé par son close_time
frais. Règle héritée : un doublon est toléré, un trade manqué est INTERDIT.
Si Telegram est injoignable, l'état n'est PAS sauvé : le tick suivant relit
et retente (TG-9).

CE QU'ON NOTIFIE
-----------------
    clôture ledger          → une ligne par trade, immédiate (flag live_lines,
                              défaut true — D-TG-2)
    récap QUOTIDIEN         → au premier tick après digest_hour locale
                              (config.json, défaut 22), une fois par jour ;
                              reprend TOUS les trades du jour (filet si un
                              envoi live a échoué). Le VENDREDI, une section
                              « — Semaine — » (D-TG-3). Premier créneau du
                              mois suivant : le récap MENSUEL (D-TG-4).
                              Premier créneau de janvier : le récap ANNUEL.
    AUTO-OFF au panneau     → alerte immédiate, une fois par ligne (TG-10)
    études scellées (E6)    → sources héritées CONSERVÉES mais inertes tant
                              que leurs dossiers n'existent pas (TG-10)

Tout ce qu'un même tick récolte part en UN SEUL message, sections séparées
par des lignes vides, découpé à 4000 caractères sur une frontière de ligne
(TG-8). Le token n'apparaît JAMAIS dans un log (TG-11).

CODES DE SORTIE (contrat de la factory — TG-12)
------------------------------------------------
    0  passage effectué (y compris « rien de neuf »)
    2  token/config absents (sortie SILENCIEUSE) ou Telegram injoignable
    1  erreur inattendue (loggée, retentée au tick suivant)
    (jamais 3/4 : réservés aux scellés — ce worker n'en porte aucun)

USAGE
-----
    python app/orchestrator/tbot-notify.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Optional

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))        # app/orchestrator
# `core` vit dans app/ ; script lancé en direct -> app/ importable d'abord.
sys.path.insert(0, os.path.dirname(HERE))
from core import paths as _paths          # noqa: E402
from core.ledger import Ledger            # noqa: E402


# == CONSTANTES ================================================================
TELEGRAM_TIMEOUT_SEC = 15
TELEGRAM_LIMIT = 4000            # 4096 réel, marge héritée (TG-8)
DIGEST_HOUR_DEFAULT = 22         # config.json `digest_hour` (TG-1)
FRIDAY = 4                       # weekday() Python — section « Semaine »
LEDGER_MODES = ("PAPER", "LIVE")  # jamais BACKTEST (TG-2)

# Fuseau du REPORTING (heure de clôture locale, calendrier local). None = le
# fuseau du poste. Seam de test : les tests golden posent timezone.utc ici.
LOCAL_TZ: tzinfo | None = None

MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]
JOURS_FR = ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"]


# == SOURCES ÉTUDES (héritées — inertes tant que les dossiers n'existent pas) ==
# (nom, variable d'environnement). Dossier par défaut <db>/<nom>. Les études
# scellées migrent vers C:/db/tradingBot/<étude>/ en E6 (studies/CUTOVER.md) ;
# d'ici là ces sources rendent « rien » sans bruit (TG-10).
ETUDES: list[tuple[str, str]] = [
    ("gold_forward",  "GOLD_FORWARD_DIR"),
    ("s13_forward",   "S13_FORWARD_DIR"),
    ("macd_ai_paper", "MACD_AI_PAPER_DIR"),
    ("s14_sentiment", "S14_SENTIMENT_DIR"),
    ("alexg_paper",   "ALEXG_PAPER_DIR"),
]

# gold_forward ne journalise pas de colonne symbol : l'instrument est unique.
IMPLICIT_SYMBOL = {"gold_forward": "XAUUSD"}


# == RÉSOLUTION DES CHEMINS (à l'appel, pas à l'import — testable) =============
def notify_dir() -> str:
    # Dossier PROPRE à ce worker — jamais `notifier/` (curseurs robinbot).
    return os.environ.get("TBOT_NOTIFY_DIR") or str(_paths.db_dir() / "tbot-notify")


def etude_dirs() -> list[tuple[str, str]]:
    return [(name, os.environ.get(env) or str(_paths.db_dir() / name))
            for name, env in ETUDES]


def panel_path() -> str:
    # Le panneau de la TBOT factory (tbot-factory.py écrit ses AUTO-OFF là),
    # PAS celui du prototype robinbot. Résolution UNIQUE : core.paths (F9).
    return str(_paths.tbot_panel_file())


# == PETITS OUTILS =============================================================
def err(msg: str) -> None:
    print(f"[TBOT-NOTIFY] {msg}", file=sys.stderr)


def load_json_quiet(path: str) -> Optional[dict]:
    """None si absent OU illisible — le notifier n'a pas le droit de crasher
    sur un fichier en cours d'écriture."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_state(path: str, state: dict) -> None:
    """Écriture atomique (tmp + os.replace) — motif du repo (TG-9)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_token(path: str) -> Optional[str]:
    """Token BRUT, une ligne, BOM toléré (D-TG-1) — pas le format .env du
    prototype : un bot dédié, un fichier dédié, une seule ligne."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return None


def _to_local(iso_utc: str) -> datetime:
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def money(amount: float, currency: str = "CHF") -> str:
    """Montant -> forme exacte d'Adrian : arrondi entier, signé, suffixe
    devise collé en minuscules (D-TG-5) : -100chf, +210chf, +0chf, +50eur.
    Arrondi « half away from zero » (déterministe — pas le banquier de
    round()), jamais de « -0chf »."""
    suffix = (currency or "CHF").lower()
    n = int(math.floor(abs(float(amount)) + 0.5))
    if amount < 0 and n > 0:
        return f"-{n}{suffix}"
    return f"+{n}{suffix}"


def chf(amount: float) -> str:
    """Forme historique CHF (les golden TG-4..TG-7 en CHF pur)."""
    return money(amount, "CHF")


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Découpe à `limit` caractères max, sur une frontière de ligne (TG-8).
    Une ligne monstre (> limit) est coupée dure — mieux vaut deux morceaux
    qu'un refus Telegram silencieux."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    cur = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if not cur:
            cur = line
        elif len(cur) + 1 + len(line) <= limit:
            cur += "\n" + line
        else:
            chunks.append(cur)
            cur = line
    if cur:
        chunks.append(cur)
    return chunks


# == LEDGER : SÉLECTION DES TRADES =============================================
def _closed_trades(ledger: Ledger, date_from=None, date_to=None) -> list[dict]:
    """Trades clos PAPER + LIVE (jamais BACKTEST — TG-2), triés
    (close_time, id) — l'ordre du curseur D-TG-6."""
    rows: list[dict] = []
    for mode in LEDGER_MODES:
        rows.extend(ledger.closed_trades(mode=mode, date_from=date_from,
                                         date_to=date_to))
    rows.sort(key=lambda r: (r["close_time"], r["id"]))
    return rows


def _cursor_tuple(state: dict) -> tuple[str, int]:
    cur = state.get("trade_cursor")
    if not isinstance(cur, dict):
        return ("", 0)
    return (str(cur.get("close_time") or ""), int(cur.get("id") or 0))


def new_closed_trades(ledger: Ledger, cursor: tuple[str, int]) -> list[dict]:
    """Les trades clos jamais notifiés : tuple (close_time, id) > curseur.
    POURQUOI close_time en clé primaire : le close est un UPDATE, un trade
    ouvert tôt (petit id) peut clore APRÈS un trade au grand id — un curseur
    par id le perdrait, le close_time frais le rattrape (D-TG-6)."""
    return [r for r in _closed_trades(ledger)
            if (r["close_time"], r["id"]) > cursor]


def format_trade_line(row: dict) -> str:
    """Le format exact d'une ligne de trade (TG-3, au caractère près) :
    `10:53 S001.CHF-USD SL -100chf` — heure de clôture LOCALE, instance,
    motif tel que stocké, net arrondi CHF entier signé."""
    hhmm = _to_local(row["close_time"]).strftime("%H:%M")
    return (f"{hhmm} {row['instance_id']} {row['exit_reason']} "
            f"{chf(row['net_pnl'] or 0.0)}")


def _merged_pnl(ledger: Ledger, method: str, label: str,
                date_from, date_to) -> dict[str, dict[str, float]]:
    """Agrégat ledger fusionné PAPER + LIVE -> {période: {devise: net}}.
    Les agrégats du ledger séparent les devises (LG-14) ; le reporting
    CONSERVE la séparation — une ligne par devise, JAMAIS une addition
    inter-devises muette (F10)."""
    out: dict[str, dict[str, float]] = {}
    for mode in LEDGER_MODES:
        for row in getattr(ledger, method)(date_from, date_to, mode=mode):
            per = out.setdefault(row[label], {})
            cur = row.get("currency") or "CHF"
            per[cur] = per.get(cur, 0.0) + (row["net"] or 0.0)
    return out


def _sum_per_ccy(periods) -> dict[str, float]:
    """Totaux par devise sur un itérable de {devise: net} — même règle F10 :
    on additionne DANS une devise, jamais entre devises."""
    totals: dict[str, float] = {}
    for per in periods:
        for cur, net in per.items():
            totals[cur] = totals.get(cur, 0.0) + net
    return totals


def _amount_lines(prefix: str, per_ccy: dict[str, float]) -> list[str]:
    """Une ligne PAR DEVISE (F10), devises triées pour un rendu déterministe.
    Période sans trade -> la ligne +0chf historique (le défaut du reporting).
    Une seule devise CHF -> rendu golden inchangé (TG-4..TG-7)."""
    if not per_ccy:
        return [f"{prefix} +0chf"]
    return [f"{prefix} {money(net, cur)}"
            for cur, net in sorted(per_ccy.items())]


# == LES SECTIONS DU DIGEST (formats golden — TG-4 à TG-7) =====================
def build_daily_section(ledger: Ledger, today: date) -> str:
    """TG-4 — les trades du JOUR local + total. Aucun trade → le dire : le
    silence total est indistinguable d'une panne."""
    lines = [f"📒 TradingBot — {today.strftime('%d.%m.%Y')}"]
    rows = _closed_trades(ledger, date_from=today, date_to=today)
    if not rows:
        lines.append("Aucun trade aujourd'hui.")
    else:
        for r in rows:
            lines.append(format_trade_line(r))
        total = sum((r["net_pnl"] or 0.0) for r in rows)
        lines.append(f"Total jour : {chf(total)}")
    return "\n".join(lines)


def build_weekly_section(ledger: Ledger, today: date) -> str:
    """TG-5 — le vendredi : gains/pertes par jour Lu-Ve puis total, source
    pnl_by_day sur la semaine ISO. Un jour sans trade affiche +0chf (semaine
    FX = lundi-vendredi) ; un trade de week-end, exceptionnel, a sa ligne —
    jamais d'argent perdu entre les lignes."""
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    per_day = _merged_pnl(ledger, "pnl_by_day", "day",
                          monday, monday + timedelta(days=6))
    week_no = today.isocalendar()[1]
    lines = [f"— Semaine {week_no} ({monday.strftime('%d.%m')}"
             f"–{friday.strftime('%d.%m')}) —"]
    for i in range(7):
        d = monday + timedelta(days=i)
        per = per_day.get(d.isoformat(), {})
        if i >= 5 and not any(abs(net) >= 0.005 for net in per.values()):
            continue                        # week-end sans trade : pas de ligne
        lines.extend(_amount_lines(JOURS_FR[i], per))
    lines.extend(_amount_lines("Total semaine :", _sum_per_ccy(per_day.values())))
    return "\n".join(lines)


def _titre_mois(year: int, month: int) -> str:
    nom = MOIS_FR[month - 1]
    liaison = "d'" if nom[0] in "aeiouâàéèêëîïôöûü" else "de "
    return f"📒 Mois {liaison}{nom} {year}"


def build_monthly_section(ledger: Ledger, year: int, month: int) -> str:
    """TG-6 — par semaine ISO puis total, puis rétrospective 12 mois (tous
    les mois affichés, +0chf pour un mois vide — une rétrospective à trous
    ne se lit pas)."""
    first = date(year, month, 1)
    last = (date(year + 1, 1, 1) if month == 12
            else date(year, month + 1, 1)) - timedelta(days=1)
    weeks = _merged_pnl(ledger, "pnl_by_week", "week", first, last)
    lines = [_titre_mois(year, month)]
    for wk in sorted(weeks):                # 'YYYY-Www' — l'ordre lexical suit
        lines.extend(_amount_lines(f"S{int(wk.split('-W')[1]):02d}", weeks[wk]))
    lines.extend(_amount_lines("Total mois :", _sum_per_ccy(weeks.values())))
    lines.append("")
    lines.append("— 12 derniers mois —")
    start_y, start_m = (year, month + 1) if month < 12 else (year + 1, 1)
    start = date(start_y - 1, start_m, 1)   # 12 mois finissant au mois clos
    months = _merged_pnl(ledger, "pnl_by_month", "month", start, last)
    y, m = start.year, start.month
    for _ in range(12):
        lines.extend(_amount_lines(f"{m:02d}.{y:04d}",
                                   months.get(f"{y:04d}-{m:02d}", {})))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return "\n".join(lines)


def build_annual_section(ledger: Ledger, year: int) -> str:
    """TG-7 — par mois puis total, les 12 mois affichés."""
    months = _merged_pnl(ledger, "pnl_by_month", "month",
                         date(year, 1, 1), date(year, 12, 31))
    lines = [f"📒 Année {year}"]
    for m in range(1, 13):
        lines.extend(_amount_lines(f"{m:02d}",
                                   months.get(f"{year:04d}-{m:02d}", {})))
    lines.extend(_amount_lines("Total année :", _sum_per_ccy(months.values())))
    return "\n".join(lines)


def _prev_month_key(d: date) -> str:
    prev = d.replace(day=1) - timedelta(days=1)
    return f"{prev.year:04d}-{prev.month:02d}"


# == SOURCES HÉRITÉES : JOURNAUX D'ÉTUDES + PANNEAU (TG-10) ====================
def parse_journal(jpath: str) -> tuple[list[dict], int, int]:
    """-> (lignes complètes via DictReader, octets couverts, octets totaux).
    Découpage au dernier saut de ligne : un runner peut être en train
    d'écrire — la ligne en cours sera vue entière au tick suivant."""
    with open(jpath, "rb") as f:
        raw = f.read()
    total = len(raw)
    cut = raw.rfind(b"\n")
    parsed = raw[:cut + 1] if cut >= 0 else b""
    text = parsed.decode("utf-8", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    return rows, len(parsed), total


def format_row(etude: str, row: dict) -> Optional[str]:
    """Une ligne de journal d'étude -> un message, ou None (non notifié).
    Mécanique héritée telle quelle du notifier robinbot éprouvé."""
    event = (row.get("event") or "").strip().upper()
    shadow = event.startswith("SHADOW_")
    base = event[len("SHADOW_"):] if shadow else event
    if base not in ("OPEN", "CLOSE"):
        return None

    symbol = (row.get("symbol") or "").strip() or IMPLICIT_SYMBOL.get(etude, "?")
    arm = (row.get("arm") or "").strip()
    pfx = "(shadow) " if shadow else ""
    suffixe_bras = f", bras {arm}" if arm else ""

    if base == "OPEN":
        side = (row.get("side") or "").strip()
        entry = (row.get("entry_price") or "").strip() or "?"
        stop = (row.get("stop_price") or "").strip() or "—"
        target = (row.get("target_price") or "").strip() or "—"
        return (f"📈 [{etude}] {pfx}OPEN {symbol} {side} @ {entry} "
                f"(SL {stop}, TP {target}){suffixe_bras}")

    pnl_r = float(row.get("pnl_r") or "")        # ValueError -> ligne ignorée
    pnl_ccy = float(row.get("pnl_ccy") or "")
    emoji = "💰" if pnl_r >= 0 else "🔻"
    reason = (row.get("exit_reason") or "").strip() or "?"
    cap = (row.get("capital_after") or "").strip() or "n/d"
    return (f"{emoji} [{etude}] {pfx}CLOSE {symbol} {pnl_r:+.2f} R "
            f"({pnl_ccy:+.0f} CHF) {reason} — capital {cap}{suffixe_bras}")


def scan_autooff(seen: set[str]) -> list[tuple[str, str]]:
    """-> [(empreinte, message)] pour chaque ligne AUTO-OFF du panneau tbot
    jamais vue. L'empreinte est le hash de la ligne entière : la factory
    horodate, donc un nouvel incident produit une nouvelle alerte."""
    p = panel_path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            raw_lines = f.read().splitlines()
    except OSError:
        return []
    out: list[tuple[str, str]] = []
    for raw in raw_lines:
        if "AUTO-OFF" not in raw:
            continue
        fp = hashlib.sha256(raw.strip().encode("utf-8")).hexdigest()[:16]
        if fp in seen:
            continue
        code = raw.split("#", 1)[0]
        worker = code.split("=", 1)[0].strip() if "=" in code else "?"
        raison = raw.split("AUTO-OFF", 1)[1].strip() or "raison inconnue"
        out.append((fp, f"🚨 [{worker}] AUTO-OFF : {raison}"))
    return out


# == ENVOI (TG-8, TG-9, TG-11) =================================================
def send_telegram(token: str, chat_id: str, text: str) -> bool:
    """POST sendMessage, découpé sur frontière de ligne. False sur tout échec
    — l'appelant décide (exit 2, curseurs inchangés). Succès = HTTP 200 ET
    ok:true (TG-9). Le token n'atteint JAMAIS un log : le repr des exceptions
    requests contient l'URL, donc le token — on ne loggue que le TYPE, et les
    corps de refus sont masqués (TG-11)."""
    for chunk in split_message(text):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            r = requests.post(url, json={"chat_id": chat_id, "text": chunk},
                              timeout=TELEGRAM_TIMEOUT_SEC)
        except Exception as e:  # noqa: BLE001
            err(f"Telegram injoignable : {type(e).__name__}")
            return False
        if not r.ok:
            detail = r.text[:200].replace(token, "<token>")
            err(f"Telegram a refusé l'envoi (HTTP {r.status_code}) : {detail}")
            return False
        try:
            body = r.json()
        except ValueError:
            err("Telegram : réponse illisible sur sendMessage")
            return False
        if not body.get("ok"):
            err(f"Telegram : sendMessage rejeté "
                f"({str(body.get('description'))[:120].replace(token, '<token>')})")
            return False
    return True


# == LE PASSAGE ================================================================
def tick(now_local: Optional[datetime] = None) -> int:
    """Un passage complet. Idempotent : deux ticks sans nouveauté = zéro
    message. L'état n'est sauvé qu'en fin de passage, et JAMAIS si l'envoi a
    échoué — c'est la garantie « aucun trade perdu » (TG-9)."""
    now_local = now_local or datetime.now(LOCAL_TZ).replace(tzinfo=None)
    ndir = notify_dir()

    # -- inertie TCK-007 : token OU chat_id absents -> sortie 2 SANS BRUIT ----
    token = load_token(os.path.join(ndir, "token.txt"))
    config = load_json_quiet(os.path.join(ndir, "config.json"))
    if not token or config is None or not str(config.get("chat_id") or "").strip():
        return 2

    chat_id = str(config["chat_id"])
    try:
        digest_hour = int(config.get("digest_hour", DIGEST_HOUR_DEFAULT))
    except (TypeError, ValueError):
        digest_hour = DIGEST_HOUR_DEFAULT
    live_lines_enabled = bool(config.get("live_lines", True))

    state_path = os.path.join(ndir, "state.json")
    state = load_json_quiet(state_path)
    today = now_local.date()
    dirty = False
    incidents: list[str] = []
    sections_trades: list[str] = []
    tail: list[str] = []

    ledger = Ledger(local_tz=LOCAL_TZ)
    try:
        if state is None:
            # PREMIER PASSAGE — armement. Curseur trade posé sur le DERNIER
            # trade clos existant (l'historique n'est pas re-notifié — la
            # surveillance est prospective), curseurs d'études en fin de
            # journaux, empreintes AUTO-OFF mémorisées sans alerte, marqueurs
            # mensuel/annuel posés sur les périodes déjà écoulées (pas de
            # récap rétroactif à l'armement).
            state = {
                "schema": 1,
                "armed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "trade_cursor": None,
                "etude_cursors": {},
                "autooff_seen": [],
                "last_digest_date": None,
                "last_monthly": _prev_month_key(today),
                "last_annual": str(today.year - 1),
            }
            existing = _closed_trades(ledger)
            if existing:
                last = existing[-1]
                state["trade_cursor"] = {"close_time": last["close_time"],
                                         "id": last["id"]}
            n = 0
            for name, ddir in etude_dirs():
                jpath = os.path.join(ddir, "journal.csv")
                if not os.path.exists(jpath):
                    continue
                try:
                    rows, covered, _total = parse_journal(jpath)
                except OSError as e:
                    # Journal PRÉSENT mais illisible : on n'arme PAS — un état
                    # sans ce curseur rejouerait tout son historique.
                    err(f"[{name}] journal illisible à l'armement ({e!r}) — "
                        f"armement annulé, réessai au prochain tick.")
                    return 2
                state["etude_cursors"][name] = {"bytes": covered,
                                                "lines": len(rows)}
                n += 1
            for fp, _msg in scan_autooff(set()):
                state["autooff_seen"].append(fp)
            sections_trades.append(
                f"🔔 Notifier TradingBot armé — ledger surveillé, "
                f"{n} étude(s) en journal")
            dirty = True
        else:
            state.setdefault("etude_cursors", {})
            state.setdefault("autooff_seen", [])
            # Schéma qui évolue : des marqueurs absents se posent sur les
            # périodes écoulées — jamais de rafale de récaps de rattrapage.
            state.setdefault("last_monthly", _prev_month_key(today))
            state.setdefault("last_annual", str(today.year - 1))

            # -- incidents AUTO-OFF (en tête : c'est l'urgence) ---------------
            for fp, msg in scan_autooff(set(state["autooff_seen"])):
                incidents.append(msg)
                state["autooff_seen"].append(fp)
                dirty = True

            # -- journaux des études (hérités, inertes tant que absents) ------
            for name, ddir in etude_dirs():
                jpath = os.path.join(ddir, "journal.csv")
                if not os.path.exists(jpath):
                    continue
                cur = state["etude_cursors"].get(name) or {"bytes": 0, "lines": 0}
                try:
                    rows, covered, total = parse_journal(jpath)
                except OSError as e:
                    err(f"[{name}] journal illisible ({e!r}) — sauté ce tick.")
                    continue
                if total < int(cur.get("bytes", 0)):
                    state["etude_cursors"][name] = {"bytes": covered,
                                                    "lines": len(rows)}
                    dirty = True
                    err(f"[{name}] journal tronqué/reconstruit — curseur "
                        f"re-posé en fin de fichier, historique non re-notifié.")
                    continue
                for row in rows[int(cur.get("lines", 0)):]:
                    try:
                        msg = format_row(name, row)
                    except Exception as e:  # noqa: BLE001
                        err(f"[{name}] ligne malformée ignorée : {e!r}")
                        msg = None
                    if msg:
                        sections_trades.append(msg)
                newcur = {"bytes": covered, "lines": len(rows)}
                if newcur != cur:
                    state["etude_cursors"][name] = newcur
                    dirty = True

            # -- lignes de trade live depuis le LEDGER (TG-2, TG-3) -----------
            nouveaux = new_closed_trades(ledger, _cursor_tuple(state))
            if nouveaux:
                if live_lines_enabled:
                    sections_trades.append(
                        "\n".join(format_trade_line(r) for r in nouveaux))
                last = nouveaux[-1]
                state["trade_cursor"] = {"close_time": last["close_time"],
                                         "id": last["id"]}
                dirty = True

            # -- digest quotidien (une fois par date locale — TG-4..TG-7) -----
            today_str = today.isoformat()
            if (now_local.hour >= digest_hour
                    and state.get("last_digest_date") != today_str):
                tail.append(build_daily_section(ledger, today))
                if today.weekday() == FRIDAY:
                    tail.append(build_weekly_section(ledger, today))
                pm = _prev_month_key(today)
                if state.get("last_monthly") != pm:
                    y, m = int(pm[:4]), int(pm[5:7])
                    tail.append(build_monthly_section(ledger, y, m))
                    state["last_monthly"] = pm
                prev_year = today.year - 1
                if state.get("last_annual") != str(prev_year):
                    tail.append(build_annual_section(ledger, prev_year))
                    state["last_annual"] = str(prev_year)
                state["last_digest_date"] = today_str
                dirty = True
    finally:
        ledger.close()

    sections = incidents + sections_trades + tail
    if sections:
        if not send_telegram(token, chat_id, "\n\n".join(sections)):
            err("envoi Telegram en échec — état NON sauvé, tout sera retenté "
                "au prochain tick.")
            return 2
    if dirty:
        save_state(state_path, state)
    return 0


def main() -> int:
    try:
        return tick()
    except Exception as e:  # noqa: BLE001 — jamais 3/4, jamais de traceback nu
        err(f"erreur inattendue : {e!r}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
