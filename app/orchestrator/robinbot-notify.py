#!/usr/bin/env python3
"""
robinbot-notify.py — LE NOTIFIER TELEGRAM DE LA FACTORY
========================================================

Worker « tick » de la factory (orchestrator/robinbot-factory.py) : lit les
journaux des études forward, détecte les nouveautés, pousse UN message
Telegram par passage. LECTURE SEULE stricte sur C:/db/tbot/<étude>/ — ce
worker n'écrit QUE dans son propre dossier C:/db/tbot/notifier/.

POURQUOI un watcher séparé plutôt qu'une notification dans les runners : les
runners sont SCELLÉS (hash des paramètres, journaux chaînés). Y greffer un
canal de sortie toucherait aux scellés. Le notifier observe les mêmes
fichiers que n'importe quel humain — aucun privilège, donc aucune capacité
de nuire aux études.

LES CURSEURS N'AVANCENT QU'APRÈS UN ENVOI RÉUSSI
-------------------------------------------------
L'état (state.json) mémorise par journal les octets couverts et le nombre de
lignes vues. Si Telegram est injoignable, l'état n'est PAS sauvé : le tick
suivant relit les mêmes lignes et retente. On préfère risquer un doublon
(fenêtre de quelques millisecondes entre envoi et sauvegarde) que perdre un
trade — une notification manquée ne se rejoue jamais, un doublon se lit en
deux secondes.

CE QU'ON NOTIFIE, CE QU'ON TAIT
--------------------------------
    OPEN / SHADOW_OPEN     → une ligne par trade ouvert, immédiate
    CLOSE / SHADOW_CLOSE   → une ligne par trade clos (R, monnaie, raison)
    VERDICT (futur s14)    → JAMAIS par ligne (trop bavard) — le digest suffit
    AUTO-OFF au panneau    → alerte immédiate, une seule fois par ligne — une
                             alarme de falsification doit réveiller un humain
    digest QUOTIDIEN       → au premier tick après l'heure locale configurée
                             (config.json, défaut 20 h), une fois par jour :
                             l'état par étude + les trades du jour. Le
                             VENDREDI, le même digest porte une section
                             « — Semaine — » (bilan de l'ISO-semaine). Un
                             seul message, jamais deux.

Tout ce qu'un même tick récolte part en UN SEUL message, sections séparées
par des lignes vides — pas de rafale.

PREMIER PASSAGE : les curseurs se posent à la FIN des journaux existants —
l'historique n'est pas re-notifié, la surveillance est prospective, comme
les études elles-mêmes. Un unique message d'armement prouve la boucle
complète (token → API Telegram → téléphone).

CODES DE SORTIE (contrat de la factory)
----------------------------------------
    0  passage effectué (y compris « rien de neuf » et journaux absents)
    1  erreur inattendue (loggée, retentée au tick suivant — jamais d'AUTO-OFF)
    2  token/config absents, ou Telegram injoignable — réessai au tick suivant
    (jamais 3/4 : réservés aux scellés — ce worker n'en porte aucun)

USAGE
-----
    python orchestrator/robinbot-notify.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Optional

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))


# == SOURCES (une ligne par étude — extensible) ================================
# (nom, variable d'environnement, dossier par défaut). La variable d'env est
# celle des études elles-mêmes (motif Paths/default_data_dir) : les tests
# montent des études jetables dans un tmp_path sans toucher au code.
ETUDES: list[tuple[str, str, str]] = [
    ("gold_forward",  "GOLD_FORWARD_DIR",  r"C:\db\tbot\gold_forward"),
    ("s13_forward",   "S13_FORWARD_DIR",   r"C:\db\tbot\s13_forward"),
    ("macd_ai_paper", "MACD_AI_PAPER_DIR", r"C:\db\tbot\macd_ai_paper"),
    ("s14_sentiment", "S14_SENTIMENT_DIR", r"C:\db\tbot\s14_sentiment"),
]

# gold_forward ne journalise pas de colonne symbol : l'instrument est unique.
IMPLICIT_SYMBOL = {"gold_forward": "XAUUSD"}

TELEGRAM_TIMEOUT_SEC = 15
DIGEST_HOUR_DEFAULT = 20
FRIDAY = 4                       # weekday() Python — section « Semaine »


# == RÉSOLUTION DES CHEMINS (à l'appel, pas à l'import — testable) =============
def notify_dir() -> str:
    return os.environ.get("ROBINBOT_NOTIFY_DIR", r"C:\db\tbot\notifier")


def etude_dirs() -> list[tuple[str, str]]:
    return [(name, os.environ.get(env, default)) for name, env, default in ETUDES]


def panel_path() -> str:
    # Même variable que la factory (RBF_PANEL) : le notifier lit la même
    # surface de contrôle que celle que la factory écrit sur incident.
    return os.environ.get("RBF_PANEL", os.path.join(HERE, "robinbot-panel.txt"))


def telegram_env_path() -> str:
    return os.environ.get(
        "ROBINBOT_TELEGRAM_ENV",
        os.path.join(os.path.expanduser("~"), ".claude", "channels",
                     "telegram", ".env"))


# == PETITS OUTILS =============================================================
def err(msg: str) -> None:
    print(f"[NOTIFY] {msg}", file=sys.stderr)


def load_json_quiet(path: str) -> Optional[dict]:
    """None si absent OU illisible — le notifier n'a pas le droit de crasher
    sur un fichier d'étude en cours d'écriture."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_state(path: str, state: dict) -> None:
    """Écriture atomique (tmp + os.replace) — motif du repo."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_token(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


# == LECTURE DES JOURNAUX ======================================================
def parse_journal(jpath: str) -> tuple[list[dict], int, int]:
    """-> (lignes complètes via DictReader, octets couverts, octets totaux).

    POURQUOI le découpage au dernier saut de ligne : un runner peut être en
    train d'écrire sa ligne au moment où on lit. On ne compte que les lignes
    COMPLÈTES ; les octets « couverts » s'arrêtent là. La ligne en cours sera
    vue entière au tick suivant. Le schéma vient de l'en-tête réelle du
    fichier — 16, 18 ou 25 colonnes, peu importe : on lit des noms de champs,
    pas des positions.
    """
    with open(jpath, "rb") as f:
        raw = f.read()
    total = len(raw)
    cut = raw.rfind(b"\n")
    parsed = raw[:cut + 1] if cut >= 0 else b""
    text = parsed.decode("utf-8", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    return rows, len(parsed), total


def format_row(etude: str, row: dict) -> Optional[str]:
    """Une ligne de journal -> un message, ou None (événement non notifié).

    VERDICT, DECISION et tout événement inconnu rendent None : la ligne est
    comptée (le curseur avance) mais rien ne part — c'est le filtre
    anti-bavardage. Une ligne dont les chiffres sont illisibles lève : la
    boucle appelante loggue et continue.
    """
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
    # Le bras figure aussi sur CLOSE : sur s13/macd (2-3 bras), savoir QUEL
    # bras a encaissé est l'information utile — un CLOSE anonyme serait ambigu.
    return (f"{emoji} [{etude}] {pfx}CLOSE {symbol} {pnl_r:+.2f} R "
            f"({pnl_ccy:+.0f} CHF) {reason} — capital {cap}{suffixe_bras}")


# == PANNEAU : DÉTECTION AUTO-OFF ==============================================
def scan_autooff(seen: set[str]) -> list[tuple[str, str]]:
    """-> [(empreinte, message)] pour chaque ligne AUTO-OFF jamais vue.

    L'empreinte est le hash de la ligne entière : la factory horodate chaque
    AUTO-OFF, donc un nouvel incident sur le même worker produit une ligne
    différente — et une nouvelle alerte. Rallumer puis retomber ne passe pas
    inaperçu.
    """
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


# == DIGEST QUOTIDIEN (section semaine le vendredi) ============================
def _measured_local_date(row: dict) -> Optional[date]:
    """Date LOCALE de la mesure (measured_at_utc converti au fuseau du poste)
    — le digest parle le calendrier de celui qui le lit."""
    ts = (row.get("measured_at_utc") or "").strip()
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return dt.astimezone().date()


def _fmt_passage(generated: str) -> str:
    """'2026-08-17T20:25:22Z' -> '17.08 20:25 UTC' — lisible en un clin d'œil,
    la date reste (un passage d'avant-hier ne doit pas se déguiser en frais)."""
    try:
        dt = datetime.strptime(generated, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return str(generated)
    return dt.strftime("%d.%m %H:%M UTC")


def _s14_verdicts(status: dict) -> Optional[int]:
    """Somme des `judges.*.n_verdicts_total` du status s14 — les compteurs y
    sont nichés PAR JUGE, pas à la racine. None si la forme n'est pas là
    (dégradation propre : la ligne s'affiche alors sans compteur)."""
    judges = status.get("judges")
    if not isinstance(judges, dict):
        return None
    total, seen = 0, False
    for j in judges.values():
        if isinstance(j, dict) and isinstance(j.get("n_verdicts_total"), (int, float)):
            total += int(j["n_verdicts_total"])
            seen = True
    return total if seen else None


def _digest_arm_line(prefix: str, st) -> str:
    """Une ligne d'état : n clos · R cumulé · capital · position. Toute forme
    inattendue rend « n/d » plutôt qu'un crash — les status évoluent avec
    leurs études, le digest doit survivre à tous."""
    if not isinstance(st, dict):
        return prefix + "n/d"
    n = st.get("n_closed_total", st.get("n_closed"))
    n_txt = str(n) if isinstance(n, (int, float)) else "n/d"
    cum = st.get("cum_r")
    cum_txt = f"{cum:+.2f} R" if isinstance(cum, (int, float)) else "n/d"
    cap = st.get("capital")
    cap_txt = f"{cap:.2f}" if isinstance(cap, (int, float)) else "n/d"
    if "open_position" in st:
        pos_txt = "position ouverte" if st["open_position"] else "flat"
    elif "open_positions" in st:
        ps = st["open_positions"]
        pos_txt = (f"{len(ps)} position(s) ouverte(s)"
                   if isinstance(ps, list) and ps else "flat")
    else:
        pos_txt = "n/d"
    return f"{prefix}{n_txt} clos · {cum_txt} · capital {cap_txt} · {pos_txt}"


def build_digest(now_local: datetime) -> str:
    """Le digest de 20 h — pensé pour se lire en 15 secondes.

    1. L'état par étude depuis status.json — deux formes gérées : plate
       (gold_forward) et nichée sous `arms` (s13 par symbole, macd_ai_paper
       par bras MECH/AI/RND). s14 n'a une ligne que si son status existe.
    2. Les trades CLOS du JOUR (depuis les journaux) — seulement s'il y en a.
    3. Le VENDREDI : « — Semaine — », bilan de l'ISO-semaine par étude
       (n clos, R, variation de capital) — depuis les journaux aussi, pas
       les status : la semaine est une fenêtre, pas un cumul depuis le scellé.
    """
    lines = [f"📊 RobinBot — digest du {now_local.strftime('%d.%m.%Y')}"]

    # -- 1. état par étude ----------------------------------------------------
    for name, ddir in etude_dirs():
        status = load_json_quiet(os.path.join(ddir, "status.json"))
        if name == "s14_sentiment":
            if status is None:
                continue                      # étude pas encore en route
            gen = _fmt_passage(status.get("generated_at_utc", "n/d"))
            n_verd = _s14_verdicts(status)
            extra = f" · {n_verd} verdicts" if n_verd is not None else ""
            lines.append(f"{name} — passage {gen}{extra}")
            continue
        if status is None:
            lines.append(f"{name} : n/d")
            continue
        gen = _fmt_passage(status.get("generated_at_utc", "n/d"))
        arms = status.get("arms")
        if isinstance(arms, dict) and arms:
            lines.append(f"{name} — passage {gen}")
            for key, st in arms.items():
                lines.append("  " + _digest_arm_line(f"{key} : ", st))
        else:
            lines.append(f"{name} — {_digest_arm_line('', status)} · passage {gen}")

    # -- 2. et 3. fenêtres jour/semaine depuis les journaux --------------------
    today = now_local.date()
    iso_week = today.isocalendar()[:2]
    day_lines: list[str] = []
    week_stats: dict[str, list] = {}          # étude -> [n, somme R, somme CHF]

    for name, ddir in etude_dirs():
        jpath = os.path.join(ddir, "journal.csv")
        if not os.path.exists(jpath):
            continue
        try:
            rows, _covered, _total = parse_journal(jpath)
        except OSError:
            continue
        for row in rows:
            if (row.get("event") or "").strip().upper() != "CLOSE":
                continue                      # shadow et verdicts hors bilan
            d = _measured_local_date(row)
            if d is None:
                continue
            try:
                pnl_r = float(row.get("pnl_r") or "")
                pnl_ccy = float(row.get("pnl_ccy") or "")
            except ValueError:
                continue
            if d == today:
                sym = ((row.get("symbol") or "").strip()
                       or IMPLICIT_SYMBOL.get(name, "?"))
                arm = (row.get("arm") or "").strip()
                bras = f", bras {arm}" if arm else ""
                reason = (row.get("exit_reason") or "").strip() or "?"
                day_lines.append(f"  {name} {sym} {pnl_r:+.2f} R ({reason}){bras}")
            if d.isocalendar()[:2] == iso_week:
                st = week_stats.setdefault(name, [0, 0.0, 0.0])
                st[0] += 1
                st[1] += pnl_r
                st[2] += pnl_ccy

    if day_lines:                             # rien clos aujourd'hui = pas de bruit
        lines.append("Aujourd'hui :")
        lines.extend(day_lines)

    if now_local.weekday() == FRIDAY:
        lines.append("— Semaine —")
        if week_stats:
            for name, (n, cum_r, cum_ccy) in week_stats.items():
                lines.append(f"  {name} : {n} clos · {cum_r:+.2f} R · "
                             f"{cum_ccy:+.0f} CHF")
        else:
            lines.append("  rien de clos cette semaine")

    return "\n".join(lines)


# == ENVOI =====================================================================
def send_telegram(token: str, chat_id: str, text: str) -> bool:
    """POST sendMessage. False sur tout échec — l'appelant décide (exit 2,
    curseurs inchangés). Remplacée par un stub dans les tests : AUCUN réseau."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text},
                          timeout=TELEGRAM_TIMEOUT_SEC)
    except Exception as e:  # noqa: BLE001
        # POURQUOI on ne loggue que le TYPE : le repr des exceptions requests
        # contient l'URL — donc le TOKEN — et stderr finit dans les logs de
        # la factory. Un token dans un fichier de log est un token grillé.
        err(f"Telegram injoignable : {type(e).__name__}")
        return False
    if not r.ok:
        detail = r.text[:200].replace(token, "<token>")
        err(f"Telegram a refusé l'envoi (HTTP {r.status_code}) : {detail}")
        return False
    return True


# == LE PASSAGE ================================================================
def tick(now_local: Optional[datetime] = None) -> int:
    """Un passage complet. Idempotent : deux ticks sans nouveauté = zéro
    message. L'état n'est sauvé qu'en fin de passage, et JAMAIS si l'envoi a
    échoué — c'est la garantie « aucun trade perdu »."""
    now_local = now_local or datetime.now()
    ndir = notify_dir()

    config = load_json_quiet(os.path.join(ndir, "config.json"))
    if config is None or not str(config.get("chat_id") or "").strip():
        err(f"config.json absent ou sans chat_id ({os.path.join(ndir, 'config.json')}) "
            f"— rien ne part, réessai au prochain tick.")
        return 2
    token = load_token(telegram_env_path())
    if not token:
        err(f"TELEGRAM_BOT_TOKEN introuvable ({telegram_env_path()}) "
            f"— réessai au prochain tick.")
        return 2

    chat_id = str(config["chat_id"])
    try:
        digest_hour = int(config.get("digest_hour_local", DIGEST_HOUR_DEFAULT))
    except (TypeError, ValueError):
        digest_hour = DIGEST_HOUR_DEFAULT

    state_path = os.path.join(ndir, "state.json")
    state = load_json_quiet(state_path)
    dirty = False
    incidents: list[str] = []
    trades: list[str] = []
    tail: list[str] = []

    if state is None:
        # PREMIER PASSAGE — armement. Curseurs posés à la FIN des journaux
        # existants (rien de l'historique ne part), empreintes AUTO-OFF déjà
        # présentes mémorisées SANS alerte (vieilles nouvelles). Un état
        # perdu/corrompu repasse par ici : re-seed silencieux, pas de rafale.
        state = {
            "schema": 1,
            "armed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cursors": {},
            "autooff_seen": [],
            "last_digest_date": None,
        }
        n = 0
        for name, ddir in etude_dirs():
            jpath = os.path.join(ddir, "journal.csv")
            if not os.path.exists(jpath):
                continue                      # étude pas encore en route
            try:
                rows, covered, _total = parse_journal(jpath)
            except OSError as e:
                # Journal PRÉSENT mais illisible : on n'arme PAS. Poser un
                # état sans ce curseur ferait rejouer tout son historique au
                # tick suivant (curseur absent = tout est « nouveau »). On
                # annule l'armement entier et on réessaie au prochain tick.
                err(f"[{name}] journal illisible à l'armement ({e!r}) — "
                    f"armement annulé, aucun état posé, réessai au prochain tick.")
                return 2
            state["cursors"][name] = {"bytes": covered, "lines": len(rows)}
            n += 1
        for fp, _msg in scan_autooff(set()):
            state["autooff_seen"].append(fp)
        trades.append(f"🔔 Notifier RobinBot armé — {n} études surveillées")
        dirty = True
    else:
        state.setdefault("cursors", {})
        state.setdefault("autooff_seen", [])

        # -- incidents AUTO-OFF (en tête de message : c'est l'urgence) --------
        for fp, msg in scan_autooff(set(state["autooff_seen"])):
            incidents.append(msg)
            state["autooff_seen"].append(fp)
            dirty = True

        # -- journaux des études ---------------------------------------------
        for name, ddir in etude_dirs():
            jpath = os.path.join(ddir, "journal.csv")
            if not os.path.exists(jpath):
                continue                      # absent = pas encore en route
            cur = state["cursors"].get(name) or {"bytes": 0, "lines": 0}
            try:
                rows, covered, total = parse_journal(jpath)
            except OSError as e:
                err(f"[{name}] journal illisible ({e!r}) — sauté ce tick.")
                continue

            if total < int(cur.get("bytes", 0)):
                # Journal TRONQUÉ/reconstruit : re-seed silencieux en fin de
                # fichier — on ne re-notifie pas un historique réécrit, et on
                # ne crie qu'une ligne stderr (le journal chaîné, lui, hurlera
                # par la voie 4 de son étude).
                state["cursors"][name] = {"bytes": covered, "lines": len(rows)}
                dirty = True
                err(f"[{name}] journal tronqué/reconstruit ({total} octets < "
                    f"curseur {cur.get('bytes')}) — curseur re-posé en fin de "
                    f"fichier, historique non re-notifié.")
                continue

            for row in rows[int(cur.get("lines", 0)):]:
                try:
                    msg = format_row(name, row)
                except Exception as e:  # noqa: BLE001 — jamais de crash sur une ligne
                    err(f"[{name}] ligne malformée ignorée : {e!r}")
                    msg = None
                if msg:
                    trades.append(msg)
            newcur = {"bytes": covered, "lines": len(rows)}
            if newcur != cur:
                state["cursors"][name] = newcur
                dirty = True

        # -- digest quotidien (une fois par date locale) ----------------------
        today = now_local.strftime("%Y-%m-%d")
        if now_local.hour >= digest_hour and state.get("last_digest_date") != today:
            tail.append(build_digest(now_local))
            state["last_digest_date"] = today
            dirty = True

    sections = incidents + trades + tail
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
