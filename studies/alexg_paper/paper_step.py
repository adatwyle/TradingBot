"""
ESSAI À BLANC « fxalexg ASSISTÉ PAR IA » — LE PAS DE MESURE (bibliothèque)
===========================================================================

Logique pure du pas horaire, séparée de l'accès MT5 et du CLI `claude` pour
être testable sur des barres synthétiques et un juge injecté
(`test_paper_step.py`). Le CLI est `run_paper.py`. Le motif (scellé, journal
chaîné, idempotence, conventions moteur) est REPRIS de
`studies/macd_ai_paper/paper_step.py`, lui-même repris de
`studies/gold_forward/forward_step.py` — une seule leçon, pas deux.

CE QUI EST MESURÉ ICI — voir PROTOCOL.md § 0
---------------------------------------------
Le détecteur v2 (importé de `strategies/s93_alexg_ai_judge/strategy.py`) est
réglé pour le RAPPEL : il attrape large, et son flux nu PERD (−0,2085 R/trade
sur 777 candidats, 26 paires, 2021-2026). La question n'est pas « la méthode
marche-t-elle » mais « le juge sait-il TRIER ce flux ». s93 a répondu non avec
une grille à cases (percentile 88,5 < 95) ; ici le juge DÉCIDE au lieu de
compter, et l'univers est enfin le vrai (26 paires, pas 6 dont 2 substituées).

LES QUATRE BRAS — journalisés à CHAQUE signal (PROTOCOL.md § 2)
----------------------------------------------------------------
    MECH  le détecteur nu : prend tout signal quand il est flat.
    AI    la session Claude Code headless décide (take/skip + taille 0..1).
          Panne du CLI -> décision « na » : le bras IA saute CE signal, les
          témoins continuent. Une panne d'IA ne fausse JAMAIS les témoins.
    RND   prise aléatoire au même taux historique que le bras IA (takes /
          décisions, recalculé à la volée), graine fixée, tirage déterministe
          par (graine, symbole, barre) — rejouable à l'identique.
    SHADOW (comptable, pas un compte) : chaque signal ouvre en plus une
          position contrefactuelle à configuration de base, SANS blocage de
          position ni cooldown. C'est elle qui fournit le R par signal dont
          F1 (sélection IA vs tirages aléatoires) et F2 (socle à coût nul)
          ont besoin, indépendamment de l'état des comptes.

MULTI-INSTRUMENTS
-----------------
26 flux H1 scellés (univers documenté de la source). Un curseur par
instrument, une position au plus par instrument et par bras, capital PARTAGÉ
par bras (pire cas : N stops touchés = N × le risque unitaire — déclaré).

TROIS INVARIANTS (hérités de gold_forward, mêmes raisons)
----------------------------------------------------------
1. SCELLÉ — SHA-256 de params.json vérifié avant toute action (exit 3 au CLI).
2. APPEND-ONLY — journal à chaîne de hachage ; réécriture/troncature/perte
   détectée -> refus de tourner sans rien écrire (exit 4 au CLI).
3. IDEMPOTENT — un curseur `last_bar_time` PAR instrument : seules les barres
   strictement postérieures sont traitées. Deux passages sur les mêmes données
   n'ajoutent rien — et ne rappellent PAS le juge IA.

CONVENTIONS D'EXÉCUTION — celles du moteur commun, répliquées à l'identique
----------------------------------------------------------------------------
Identiques ligne à ligne à `core/backtest/engine.py` : entrée au close de la
barre de signal + coût de bord ; stop UNILATÉRAL, gap payé à l'ouverture ; la
cible ne profite pas du gap ; SL prime sur TP dans la même barre ; coût de
bord aussi à la sortie ; une position par bras et par instrument, cooldown 2
barres, circuit breaker 3 pertes -> 24 barres (par instrument). Les quatre
bras utilisent le MÊME moteur : seule la décision d'entrée (et la taille pour
l'IA) diffère.

SIZING
------
1 % de risque de base par trade sur un capital virtuel initial de 10 000 par
bras, dimensionné par `core/risk/guards.py` (RiskLayer.evaluate — l'IA
propose, la couche risque dispose : défense en profondeur derrière le clamp).

AUCUN ORDRE N'EST ENVOYÉ AU BROKER. Le compte MT5 branché est un compte RÉEL
(Swissquote, trade_mode=2) : ce module lit des barres et simule. Rien d'autre.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from typing import Callable, Optional

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys  # noqa: E402
# Migration tbot : `core` vit dans app/ — les deux racines sont importables
# (studies/strategies a la racine, core sous app/ ; voir app/core/paths.py).
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.contracts.strategy import Side, Signal          # noqa: E402
from core.paths import db_dir                             # noqa: E402
from core.risk.guards import RiskLayer, RiskLimits        # noqa: E402

ARMS = ("MECH", "AI", "RND")

# Scellé — réplique de PROTOCOL.md § 1. Toute divergence = refus de tourner.
PARAMS_SHA256 = "14c7f31b66eb754d2f40e76955c677115d5e0a762e546263fce694ebd542e9d3"


class SealError(RuntimeError):
    """Le fichier de paramètres ne correspond pas au hash scellé."""


class JournalError(RuntimeError):
    """Le journal a été altéré (chaîne cassée, troncature, réécriture)."""


# Les données ne vivent JAMAIS dans l'arborescence de code (convention projet).
# Migration tbot : l'état vit sous C:\db\tradingBot\ (core.paths.db_dir, seam
# TBOT_DB_DIR) — plus jamais sous C:\db\tbot\ (prototype en exploitation,
# lecture seule absolue).
def default_data_dir() -> str:
    env = os.environ.get("ALEXG_PAPER_DIR")
    return env if env else os.path.join(str(db_dir()), "alexg_paper")


JOURNAL_COLUMNS = [
    "measured_at_utc",   # quand le script a tourné — l'horodatage de MESURE
    "event",             # DECISION | OPEN | CLOSE | SHADOW_OPEN | SHADOW_CLOSE
    "arm",               # MECH | AI | RND | SHADOW
    "symbol",
    "signal_id",         # symbole+barre du signal (partagé entre bras)
    "trade_id",
    "bar_time",          # la barre de l'événement (heure serveur MT5)
    "side",
    "entry_price",       # prix d'entrée coût de bord inclus
    "stop_price",
    "target_price",
    "size_lots",
    "risk_ccy",          # montant risqué si le stop est touché
    "exit_price",
    "exit_reason",       # SL | TP
    "pnl_r",             # R net (coûts payés) — vaut aussi pour SHADOW
    "pnl_r_nocost",      # R brut sans coût de bord (SHADOW seulement, F2)
    "pnl_ccy",
    "capital_after",
    "decision",          # DECISION : take | skip | na (IA) ; take | skip (RND)
    "size_frac",         # DECISION IA : taille 0..1 demandée (clampée)
    "sl_adjust",         # DECISION IA : facteur distance de stop (clampé à 1)
    "tp_adjust",         # DECISION IA : facteur distance de cible (clampé à 1)
    "reason",            # DECISION : raison une phrase (IA) / taux+tirage (RND)
    "chain",             # SHA-256 du fichier journal AVANT cette ligne
]


class Paths:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or default_data_dir()
        self.journal = os.path.join(self.data_dir, "journal.csv")
        self.state = os.path.join(self.data_dir, "state.json")
        self.status = os.path.join(self.data_dir, "status.json")

    def ensure(self):
        os.makedirs(self.data_dir, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Scellé — identique gold_forward
# ─────────────────────────────────────────────────────────────────────────────

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def load_sealed_params(path: str, expected_sha256: str = PARAMS_SHA256) -> dict:
    """Charge les paramètres figés. Refus net si le hash ne correspond pas :
    un essai dont la règle a bougé n'est plus un essai."""
    with open(path, "rb") as f:
        raw = f.read()
    got = sha256_bytes(raw)
    if got != expected_sha256:
        raise SealError(
            f"SCELLÉ VIOLÉ — {os.path.basename(path)} : SHA-256 attendu "
            f"{expected_sha256[:16]}…, obtenu {got[:16]}…. Toute modification "
            f"des paramètres invalide l'essai (PROTOCOL.md § 1). "
            f"Refus de tourner.")
    return json.loads(raw.decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Journal append-only à chaîne de hachage — identique gold_forward
# ─────────────────────────────────────────────────────────────────────────────

def _csv_line(values: list) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()


def init_journal(path: str) -> None:
    if os.path.exists(path):
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(_csv_line(JOURNAL_COLUMNS))


def verify_journal(path: str, state: Optional[dict]) -> None:
    """1. CHAÎNE INTERNE (chaque ligne porte le SHA-256 du fichier avant elle)
    2. EMPREINTE D'ÉTAT (taille + SHA-256 au dernier passage)."""
    if not os.path.exists(path):
        if state is not None and state.get("journal_bytes", 0) > 0:
            raise JournalError("journal.csv absent alors que l'état en "
                               "référence un — suppression détectée")
        return

    with open(path, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise JournalError("journal vide sans en-tête")
    running = lines[0] + "\n"
    for k, line in enumerate(lines[1:], start=2):
        cells = next(csv.reader(io.StringIO(line)))
        if len(cells) != len(JOURNAL_COLUMNS):
            raise JournalError(f"ligne {k} : {len(cells)} colonnes au lieu de "
                               f"{len(JOURNAL_COLUMNS)}")
        expected = sha256_bytes(running.encode("utf-8"))
        if cells[-1] != expected:
            raise JournalError(
                f"CHAÎNE CASSÉE à la ligne {k} — le journal a été modifié "
                f"après coup. Maillon attendu {expected[:16]}…, "
                f"lu {cells[-1][:16]}…")
        running += line + "\n"

    if state is not None:
        n = int(state.get("journal_bytes", 0))
        sha = state.get("journal_sha256", "")
        if n:
            if len(raw) < n:
                raise JournalError(
                    f"journal tronqué : {len(raw)} octets, "
                    f"{n} attendus au minimum")
            if sha and sha256_bytes(raw[:n]) != sha:
                raise JournalError(
                    "le préfixe du journal ne correspond plus à l'empreinte "
                    "du dernier passage — réécriture détectée")


def append_journal(path: str, rows: list[dict]) -> tuple[int, str]:
    with open(path, "rb") as f:
        raw = f.read()
    out = []
    for row in rows:
        row = dict(row)
        row["chain"] = sha256_bytes(raw + b"".join(out))
        line = _csv_line([row.get(c, "") for c in JOURNAL_COLUMNS]).encode("utf-8")
        out.append(line)
    with open(path, "ab") as f:
        for line in out:
            f.write(line)
    final = raw + b"".join(out)
    return len(final), sha256_bytes(final)


def read_journal(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────────────────────────────────────
# État
# ─────────────────────────────────────────────────────────────────────────────

def load_state(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    """Écriture atomique : un crash au milieu ne laisse jamais un état
    corrompu à côté d'un journal sain."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_arm_state(capital: float, symbols: list[str]) -> dict:
    return {"capital": capital, "n_closed": 0, "cum_r": 0.0,
            "by_symbol": {s: {"open_position": None, "cooldown_bars_left": 0,
                              "consecutive_losses": 0} for s in symbols}}


# ─────────────────────────────────────────────────────────────────────────────
# Exécution — conventions du moteur commun (identiques gold_forward)
# ─────────────────────────────────────────────────────────────────────────────

def edge_cost_of(spec: dict) -> float:
    """Demi-spread + slippage, payé à CHAQUE extrémité — engine.py ligne à ligne."""
    return (spec["spread_pips"] * spec["pip"] / 2.0
            + spec["slippage_pips"] * spec["pip"])


def check_exit(pos: dict, bar) -> Optional[tuple[float, str]]:
    """Unilatéral : stop franchi dès que la barre l'atteint ; une barre qui
    ouvre au-delà exécute à l'ouverture (le gap se paie). La cible n'a pas ce
    privilège. SL et TP dans la même barre -> SL."""
    long = pos["side"] == "LONG"
    hi, lo, op = float(bar["high"]), float(bar["low"]), float(bar["open"])
    stop = float(pos["stop_price"])
    target = pos.get("target_price")
    target = float(target) if target not in (None, "") else None

    if long:
        hit_sl = lo <= stop
        hit_tp = target is not None and hi >= target
        sl_fill = min(stop, op)
    else:
        hit_sl = hi >= stop
        hit_tp = target is not None and lo <= target
        sl_fill = max(stop, op)

    if hit_sl:
        return sl_fill, "SL"
    if hit_tp:
        return target, "TP"
    return None


def clamp_decision(dec: dict, bounds: dict) -> dict:
    """Ramène toute décision IA DANS les bornes du protocole. Défense en
    profondeur n°1. Rappel PROTOCOL.md § 0ter : sl_adjust et tp_adjust sont
    scellés à [1,0 ; 1,0] — la source est set-and-forget, l'IA ne retouche
    pas les niveaux. Le plombage reste en place pour que la V2 puisse les
    rouvrir sans changer la structure du journal."""
    def _f(v, lo, hi, dflt):
        try:
            x = float(v)
        except (TypeError, ValueError):
            return dflt
        return min(max(x, lo), hi)

    decision = str(dec.get("decision", "")).strip().lower()
    if decision not in ("take", "skip"):
        decision = "skip"                # décision illisible = pas de trade
    return {
        "decision": decision,
        "size": _f(dec.get("size"), bounds["size_min"], bounds["size_max"], 0.0),
        "sl_adjust": _f(dec.get("sl_adjust"), bounds["sl_adjust_min"],
                        bounds["sl_adjust_max"], 1.0),
        "tp_adjust": _f(dec.get("tp_adjust"), bounds["tp_adjust_min"],
                        bounds["tp_adjust_max"], 1.0),
        "reason": str(dec.get("reason", ""))[:300].replace("\n", " "),
    }


def _open_position(sig: Signal, bar_time: pd.Timestamp, spec: dict,
                   sizing: dict, capital: float, *, size_frac: float = 1.0,
                   sl_adjust: float = 1.0, tp_adjust: float = 1.0,
                   arm: str = "MECH") -> Optional[dict]:
    """Dimensionne et ouvre une position virtuelle via la couche de risque.

    Le prix d'entrée inclut le coût de bord et c'est CE prix qui sert au
    dimensionnement : le risque dimensionné est le risque payé.
    """
    cost = edge_cost_of(spec)
    long = sig.side == Side.LONG
    entry_exec = float(sig.entry) + (cost if long else -cost)

    base_stop_dist = abs(entry_exec - float(sig.stop))
    stop_dist = base_stop_dist * float(sl_adjust)
    if stop_dist <= 0:
        return None
    stop = entry_exec - stop_dist if long else entry_exec + stop_dist

    target = None
    if sig.target is not None:
        base_tgt_dist = abs(float(sig.target) - entry_exec)
        tgt_dist = base_tgt_dist * float(tp_adjust)
        target = entry_exec + tgt_dist if long else entry_exec - tgt_dist

    eff_risk_pct = sizing["risk_per_trade_pct"] * float(size_frac)
    if eff_risk_pct <= 0:
        return None                       # taille nulle = pas de position

    sized = Signal(
        timestamp=sig.timestamp, symbol=spec["symbol"], side=sig.side,
        entry=entry_exec, stop=stop,
        target=target, reason=sig.reason)

    limits = RiskLimits(
        max_position_pct=min(eff_risk_pct / 100.0, 0.01),
        max_open_positions=1)
    risk = RiskLayer(capital=capital, limits=limits)
    value_per_unit = spec["pip_value_per_lot"] / spec["pip"]
    d = risk.evaluate(sized, value_per_unit=value_per_unit)
    if not d:
        return None                       # refus tracé côté appelant

    return {
        "trade_id": (f"{arm}_{spec['symbol']}_{sig.side.name}_"
                     f"{bar_time.strftime('%Y%m%d%H%M')}"),
        "symbol": spec["symbol"],
        "side": sig.side.name,
        "entry_bar_time": bar_time.isoformat(),
        "entry_price": entry_exec,
        "stop_price": stop,
        "target_price": target,
        "risk_distance": abs(entry_exec - stop),
        "size_lots": d.size,
        "risk_ccy": d.risk_amount,
    }


def _close_pnl(pos: dict, exit_price: float, spec: dict) -> tuple[float, float]:
    """P&L de clôture — mêmes lignes que le moteur : coût de bord payé aussi
    à la sortie, R = brut / distance de risque."""
    long = pos["side"] == "LONG"
    gross = (exit_price - pos["entry_price"]) if long else (pos["entry_price"] - exit_price)
    gross -= edge_cost_of(spec)
    pnl_r = gross / pos["risk_distance"]
    pnl_ccy = pnl_r * pos["risk_ccy"]
    return pnl_r, pnl_ccy


# ─────────────────────────────────────────────────────────────────────────────
# Tirage déterministe du bras aléatoire
# ─────────────────────────────────────────────────────────────────────────────

def rnd_draw(seed: int, symbol: str, bar_time: pd.Timestamp) -> float:
    """Uniforme [0,1) déterministe par (graine, symbole, barre) : rejouable,
    et indépendant de l'ordre/du nombre de passages (idempotence)."""
    h = hashlib.sha256(f"{seed}|{symbol}|{bar_time.isoformat()}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64


# ─────────────────────────────────────────────────────────────────────────────
# Le dossier de décision
# ─────────────────────────────────────────────────────────────────────────────

def build_dossier(df: pd.DataFrame, ts: pd.Timestamp, sig: Signal,
                  params: dict, state: dict, *, n_bars: int = 40) -> dict:
    """Le dossier de décision : les confluences objectivées par le détecteur
    (Signal.meta['dossier']), le contexte de barres, l'état du compte IA, les
    bornes. Barres normalisées en % de l'entrée, PAS de ticker ni de date :
    même hygiène d'anonymisation que le rejeu à l'aveugle de s93 — le juge ne
    doit pas pouvoir raisonner sur « c'est du GBPJPY en 2026 »."""
    upto = df[df.index <= ts].tail(n_bars)
    entry = float(sig.entry)
    bars = [{
        "o": round(100 * (float(r["open"]) / entry - 1), 3),
        "h": round(100 * (float(r["high"]) / entry - 1), 3),
        "l": round(100 * (float(r["low"]) / entry - 1), 3),
        "c": round(100 * (float(r["close"]) / entry - 1), 3),
    } for _, r in upto.iterrows()]

    det = dict((sig.meta or {}).get("dossier") or {})
    ai = state["arms"]["AI"]
    return {
        "methode": {
            "id": params["strategy_id"],
            "resume": ("swing forex H1 : 2 timeframes consécutifs alignés, "
                       "retour dans une AOI (<=60 pips, >=3 touches en corps, "
                       "W ou D), shift de structure par body close, stop "
                       "structurel, R:R>=2, set and forget."),
        },
        "confluences_detectees": det,
        "market_bars_pct_of_entry": bars,
        "account": {
            "capital": round(ai["capital"], 2),
            "start_capital": params["sizing"]["capital_initial"],
            "base_risk_pct": params["sizing"]["risk_per_trade_pct"],
            "closed_trades": ai["n_closed"],
            "cum_r": round(ai["cum_r"], 3),
            "recent_trades_r": state.get("ai_recent", [])[-5:],
            "take_rate_so_far": (
                round(state["ai_stats"]["n_takes"]
                      / state["ai_stats"]["n_decisions"], 3)
                if state["ai_stats"]["n_decisions"] else None),
        },
        "bounds": params["ai"]["bounds"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Le pas de mesure
# ─────────────────────────────────────────────────────────────────────────────

# judge_fn(dossier) -> décision brute (dict) ou None (panne CLI = N/A).
JudgeFn = Callable[[dict], Optional[dict]]
# signal_fns[sym](df) -> {bar_time -> Signal}
SignalFn = Callable[[pd.DataFrame], dict]


def run_step(dfs: dict[str, pd.DataFrame], params: dict, paths: Paths,
             signal_fns: dict[str, SignalFn], judge_fn: JudgeFn,
             now: Optional[datetime] = None) -> dict:
    """Un passage de mesure sur les instruments scellés. Idempotent,
    append-only, sans effet si rien de neuf. `dfs[sym]` : barres CLÔTURÉES
    uniquement. Un instrument absent de `dfs` (MT5 partiel) est simplement
    sauté ce passage — son curseur ne bouge pas. Retourne un résumé."""
    paths.ensure()
    measured_at = _now_iso(now)
    state = load_state(paths.state)
    symbols = list(params["instruments"])

    # Intégrité AVANT toute écriture : un journal altéré arrête tout ici.
    verify_journal(paths.journal, state)

    if state is None:
        # PREMIER PASSAGE — pose du scellé. Aucun signal historique n'entre au
        # journal : l'essai est prospectif, il commence MAINTENANT.
        missing = [s for s in symbols if s not in dfs]
        if missing:
            raise ValueError(f"premier passage : instruments manquants "
                             f"{missing} — le scellé se pose sur tous les "
                             f"flux à la fois")
        init_journal(paths.journal)
        n_bytes, sha = os.path.getsize(paths.journal), sha256_file(paths.journal)
        cap0 = params["sizing"]["capital_initial"]
        state = {
            "schema": 1,
            "started_at": measured_at,
            "symbols": {s: {"seal_bar_time": dfs[s].index[-1].isoformat(),
                            "last_bar_time": dfs[s].index[-1].isoformat()}
                        for s in symbols},
            "arms": {a: _new_arm_state(cap0, symbols) for a in ARMS},
            "ai_stats": {"n_decisions": 0, "n_takes": 0, "n_na": 0},
            "ai_recent": [],
            "shadow_open": [],
            "shadow": {"n_closed": 0, "cum_r": 0.0, "cum_r_nocost": 0.0},
            "journal_bytes": n_bytes,
            "journal_sha256": sha,
        }
        save_state(paths.state, state)
        return _write_status(params, paths, state, measured_at,
                             opened=0, closed=0, first_pass=True)

    init_journal(paths.journal)
    rows: list[dict] = []
    counters = {"opened": 0, "closed": 0}

    for sym in symbols:
        if sym not in dfs or dfs[sym] is None or not len(dfs[sym]):
            continue
        _step_symbol(sym, dfs[sym], params, state, rows, counters,
                     signal_fns[sym], judge_fn, measured_at)

    if rows:
        n_bytes, sha = append_journal(paths.journal, rows)
        state["journal_bytes"] = n_bytes
        state["journal_sha256"] = sha

    save_state(paths.state, state)
    return _write_status(params, paths, state, measured_at,
                         opened=counters["opened"], closed=counters["closed"],
                         first_pass=False)


def _step_symbol(sym: str, df: pd.DataFrame, params: dict, state: dict,
                 rows: list[dict], counters: dict, signal_fn: SignalFn,
                 judge_fn: JudgeFn, measured_at: str) -> None:
    spec = params["specs"][sym]
    sizing = params["sizing"]
    bounds = params["ai"]["bounds"]
    last = pd.Timestamp(state["symbols"][sym]["last_bar_time"])
    new_bars = df[df.index > last]
    if not len(new_bars):
        return
    signals = signal_fn(df)

    def _row(event, arm, ts, signal_id, pos=None, **kw):
        r = {"measured_at_utc": measured_at, "event": event, "arm": arm,
             "symbol": sym, "signal_id": signal_id, "bar_time": ts.isoformat()}
        if pos is not None:
            r.update({
                "trade_id": pos["trade_id"], "side": pos["side"],
                "entry_price": f"{pos['entry_price']:.5f}",
                "stop_price": f"{pos['stop_price']:.5f}",
                "target_price": ("" if pos["target_price"] is None
                                 else f"{pos['target_price']:.5f}"),
                "size_lots": f"{pos['size_lots']:.4f}",
                "risk_ccy": f"{pos['risk_ccy']:.2f}",
            })
        r.update(kw)
        return r

    for ts, bar in new_bars.iterrows():

        # ── 1. sorties : les trois comptes, puis le shadow ─────────────────
        for arm in ARMS:
            st = state["arms"][arm]
            slot = st["by_symbol"][sym]
            pos = slot["open_position"]
            if pos is not None and ts > pd.Timestamp(pos["entry_bar_time"]):
                ex = check_exit(pos, bar)
                if ex is not None:
                    exit_price, reason = ex
                    pnl_r, pnl_ccy = _close_pnl(pos, exit_price, spec)
                    st["capital"] += pnl_ccy
                    st["n_closed"] += 1
                    st["cum_r"] += pnl_r
                    rows.append(_row("CLOSE", arm, ts, pos.get("signal_id", ""),
                                     pos,
                                     exit_price=f"{exit_price:.5f}",
                                     exit_reason=reason,
                                     pnl_r=f"{pnl_r:+.4f}",
                                     pnl_ccy=f"{pnl_ccy:+.2f}",
                                     capital_after=f"{st['capital']:.2f}"))
                    counters["closed"] += 1
                    if arm == "AI":
                        state["ai_recent"] = (state.get("ai_recent", [])
                                              + [round(pnl_r, 3)])[-10:]
                    slot["open_position"] = None
                    slot["cooldown_bars_left"] = params["engine"]["cooldown_bars"]
                    if pnl_r < 0:
                        slot["consecutive_losses"] += 1
                        if (params["engine"]["cb_losses"] > 0
                                and slot["consecutive_losses"]
                                >= params["engine"]["cb_losses"]):
                            slot["cooldown_bars_left"] = \
                                params["engine"]["cb_cooldown_bars"]
                            slot["consecutive_losses"] = 0
                    else:
                        slot["consecutive_losses"] = 0

        still_open = []
        for spos in state["shadow_open"]:
            if spos["symbol"] == sym and ts > pd.Timestamp(spos["entry_bar_time"]):
                ex = check_exit(spos, bar)
                if ex is not None:
                    exit_price, reason = ex
                    pnl_r, pnl_ccy = _close_pnl(spos, exit_price, spec)
                    long = spos["side"] == "LONG"
                    gross = ((exit_price - spos["entry_price"]) if long
                             else (spos["entry_price"] - exit_price))
                    # sans AUCUN coût : on ré-ajoute le coût d'entrée inclus
                    # dans entry_price et celui de sortie déjà déduit du net.
                    nocost = ((gross + 2 * edge_cost_of(spec))
                              / spos["risk_distance"])
                    state["shadow"]["n_closed"] += 1
                    state["shadow"]["cum_r"] += pnl_r
                    state["shadow"]["cum_r_nocost"] += nocost
                    rows.append(_row("SHADOW_CLOSE", "SHADOW", ts,
                                     spos["signal_id"], spos,
                                     exit_price=f"{exit_price:.5f}",
                                     exit_reason=reason,
                                     pnl_r=f"{pnl_r:+.4f}",
                                     pnl_r_nocost=f"{nocost:+.4f}",
                                     pnl_ccy=f"{pnl_ccy:+.2f}",
                                     capital_after=""))
                    continue
            still_open.append(spos)
        state["shadow_open"] = still_open

        # ── 2. nouveau signal sur cette barre ? ────────────────────────────
        sig = signals.get(ts)
        if sig is not None and spec["spread_pips"] <= spec["max_spread_pips"]:
            signal_id = f"{sym}_{ts.strftime('%Y%m%d%H%M')}"

            # 2a. SHADOW — contrefactuel systématique, config de base,
            #     jamais bloqué. C'est la matière première de F1/F2.
            spos = _open_position(sig, ts, spec, sizing,
                                  sizing["capital_initial"], arm="SHADOW")
            if spos is not None:
                spos["signal_id"] = signal_id
                state["shadow_open"].append(spos)
                rows.append(_row("SHADOW_OPEN", "SHADOW", ts, signal_id, spos,
                                 capital_after=""))

            # 2b. MECH — prend tout, aux règles du moteur.
            st = state["arms"]["MECH"]
            slot = st["by_symbol"][sym]
            if slot["open_position"] is None and slot["cooldown_bars_left"] == 0:
                pos = _open_position(sig, ts, spec, sizing, st["capital"],
                                     arm="MECH")
                if pos is not None:
                    pos["signal_id"] = signal_id
                    slot["open_position"] = pos
                    rows.append(_row("OPEN", "MECH", ts, signal_id, pos,
                                     capital_after=f"{st['capital']:.2f}"))
                    counters["opened"] += 1

            # 2c. AI — décision headless, seulement si le bras peut agir.
            st = state["arms"]["AI"]
            slot = st["by_symbol"][sym]
            if slot["open_position"] is None and slot["cooldown_bars_left"] == 0:
                dossier = build_dossier(df, ts, sig, params, state)
                raw = judge_fn(dossier)
                if raw is None:
                    # Panne CLI (après relance) : bras IA N/A pour CE signal.
                    # Ni décision comptée, ni trade — les témoins continuent.
                    state["ai_stats"]["n_na"] += 1
                    rows.append(_row("DECISION", "AI", ts, signal_id,
                                     decision="na",
                                     reason="claude CLI indisponible "
                                            "(timeout/erreur après relance)"))
                else:
                    dec = clamp_decision(raw, bounds)
                    state["ai_stats"]["n_decisions"] += 1
                    took = dec["decision"] == "take" and dec["size"] > 0
                    if took:
                        state["ai_stats"]["n_takes"] += 1
                    rows.append(_row("DECISION", "AI", ts, signal_id,
                                     decision="take" if took else "skip",
                                     size_frac=f"{dec['size']:.3f}",
                                     sl_adjust=f"{dec['sl_adjust']:.3f}",
                                     tp_adjust=f"{dec['tp_adjust']:.3f}",
                                     reason=dec["reason"]))
                    if took:
                        pos = _open_position(
                            sig, ts, spec, sizing, st["capital"],
                            size_frac=dec["size"],
                            sl_adjust=dec["sl_adjust"],
                            tp_adjust=dec["tp_adjust"], arm="AI")
                        if pos is not None:
                            pos["signal_id"] = signal_id
                            slot["open_position"] = pos
                            rows.append(_row("OPEN", "AI", ts, signal_id, pos,
                                             capital_after=f"{st['capital']:.2f}"))
                            counters["opened"] += 1

            # 2d. RND — même taux historique que l'IA, tirage déterministe.
            st = state["arms"]["RND"]
            slot = st["by_symbol"][sym]
            if slot["open_position"] is None and slot["cooldown_bars_left"] == 0:
                a = state["ai_stats"]
                rate = (a["n_takes"] / a["n_decisions"] if a["n_decisions"]
                        else params["random_arm"]["default_take_rate"])
                u = rnd_draw(params["random_arm"]["seed"], sym, ts)
                take = u < rate
                rows.append(_row("DECISION", "RND", ts, signal_id,
                                 decision="take" if take else "skip",
                                 reason=f"taux={rate:.3f} tirage={u:.3f}"))
                if take:
                    pos = _open_position(sig, ts, spec, sizing, st["capital"],
                                         arm="RND")
                    if pos is not None:
                        pos["signal_id"] = signal_id
                        slot["open_position"] = pos
                        rows.append(_row("OPEN", "RND", ts, signal_id, pos,
                                         capital_after=f"{st['capital']:.2f}"))
                        counters["opened"] += 1

        # cooldowns — décrémentés après la barre, comme le moteur.
        for arm in ARMS:
            slot = state["arms"][arm]["by_symbol"][sym]
            if slot["cooldown_bars_left"] > 0:
                slot["cooldown_bars_left"] -= 1

    state["symbols"][sym]["last_bar_time"] = df.index[-1].isoformat()


def _write_status(params: dict, paths: Paths, state: dict,
                  measured_at: str, *, opened: int, closed: int,
                  first_pass: bool) -> dict:
    """status.json — l'état contre les critères d'arrêt. Le percentile F1
    (coûteux) n'est PAS recalculé ici : c'est le rôle de report_paper.py."""
    rules = params["stop_rules"]
    started = datetime.strptime(state["started_at"], "%Y-%m-%dT%H:%M:%SZ")
    now_dt = datetime.strptime(measured_at, "%Y-%m-%dT%H:%M:%SZ")
    months = (now_dt - started).days / 30.44
    a = state["ai_stats"]

    arms = {}
    for arm in ARMS:
        st = state["arms"][arm]
        arms[arm] = {
            "capital": round(st["capital"], 2),
            "n_closed": st["n_closed"],
            "cum_r": round(st["cum_r"], 4),
            "open_positions": [
                slot["open_position"]["trade_id"]
                for slot in st["by_symbol"].values()
                if slot["open_position"] is not None],
        }

    status = {
        "generated_at_utc": measured_at,
        "study": params["study"],
        "first_pass": first_pass,
        "opened_this_pass": opened,
        "closed_this_pass": closed,
        "arms": arms,
        "ai_stats": dict(a),
        "shadow": dict(state["shadow"]),
        "months_elapsed": round(months, 2),
        "stop_criteria": {
            "fail_ai": (f"actif dès {rules['fail_ai']['min_decisions']} "
                        f"décisions IA (n = {a['n_decisions']}) ; ÉCHEC si "
                        f"percentile sélection < "
                        f"{rules['fail_ai']['percentile_fail_below']}, apport "
                        f"conclu seulement à >= "
                        f"{rules['fail_ai']['percentile_pass_at_or_above']} — "
                        f"voir report_paper.py"),
            "fail_base": (f"actif dès {rules['fail_base']['min_signals']} "
                          f"signaux shadow clos "
                          f"(n = {state['shadow']['n_closed']}) ; verdict si "
                          f"R cumulé SANS coût < "
                          f"{rules['fail_base']['cum_r_nocost_below']} "
                          f"(actuel {state['shadow']['cum_r_nocost']:+.2f})"),
            "time": (f"NON CONCLUSIF si < {rules['time']['min_decisions']} "
                     f"décisions IA après {rules['time']['months']} mois "
                     f"(écoulés : {months:.1f})"),
        },
    }
    tmp = paths.status + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    os.replace(tmp, paths.status)
    return status
