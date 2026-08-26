"""
FORWARD-TEST SCELLÉ s13 — LE PAS DE MESURE (bibliothèque)
==========================================================

Logique pure du pas de mesure, séparée de l'accès MT5 pour être testable sur
des barres synthétiques (`test_forward_step.py`). Le CLI est `run_forward.py`.
Réplique du motif `studies/gold_forward/forward_step.py`, étendu à DEUX
instruments : AUDCAD (bras PRINCIPAL — seul comptable dans les critères
d'arrêt) et EURJPY (bras d'OBSERVATION — journalisé à l'identique, jamais
dans les critères ; sa jumelle n'a pas battu son beta au hold-out, elle est
là pour apprendre, pas pour compter).

TROIS INVARIANTS, ET POURQUOI ILS SONT LÀ
------------------------------------------
1. SCELLÉ — les paramètres viennent d'un fichier dont le SHA-256 est vérifié
   avant toute action. Un hash qui ne correspond pas = refus de tourner. La
   valeur entière du forward-test tient à l'impossibilité de changer la règle
   en cours de route (PROTOCOL.md, critère d).

2. APPEND-ONLY — le journal n'est jamais réécrit. Chaque ligne contient un
   maillon de chaîne (`chain` = SHA-256 du fichier AVANT la ligne) : modifier
   ou supprimer une ligne passée casse tous les maillons suivants, et le pas
   suivant refuse de tourner. Chaque ligne porte en plus l'horodatage de
   MESURE (`measured_at_utc`, quand le script a tourné) à côté de l'horodatage
   de barre : un trade « mesuré » avant sa barre, ou des mesures non
   monotones, sont un antidatage visible.

3. IDEMPOTENT — l'état (`state.json`) porte un curseur `last_bar_time` PAR
   INSTRUMENT : seules les barres strictement postérieures sont traitées.
   Deux passages sur les mêmes données n'ajoutent rien. Un instrument absent
   d'un passage (MT5 partiel) est simplement sauté — son curseur ne bouge pas.

CONVENTIONS D'EXÉCUTION — celles du moteur commun, répliquées à l'identique
----------------------------------------------------------------------------
Ce module NE recode PAS un backtest (R9) : il rejoue, barre par barre au fil de
l'eau, exactement les règles de `core/backtest/engine.py`, avec les
`engine_kwargs` DE L'ÉTUDE s13 (cooldown 0, circuit breaker désarmé — les
mêmes que `strategies/s13_macd_fx/backtests/run_holdout.py`) :

    * entrée au close de la barre de signal, coût de bord payé à l'entrée
      (demi-spread + slippage, défavorable) ;
    * stop testé UNILATÉRALEMENT : franchi dès que la barre l'atteint ou le
      dépasse. Une barre qui OUVRE au-delà du stop exécute à l'ouverture — le
      gap se paie (`min(stop, open)` en long, `max(stop, open)` en short) ;
    * la cible ne profite PAS du gap (asymétrie pessimiste du moteur) ;
    * stop ET cible dans la même barre -> le stop l'emporte ;
    * coût de bord payé aussi à la sortie ;
    * une position à la fois PAR INSTRUMENT ; avec cooldown 0, un signal sur
      la barre de sortie ré-entre le jour même — même sémantique que le
      moteur (`i < cooldown_until` faux quand cooldown_bars = 0).

La divergence de tout chiffre produit ici avec `core.backtest.engine.run` sur
les mêmes barres serait un bug — c'est ce que vérifie `test_forward_step.py`
sur les cas limites (gap, préséance SL/TP, ré-entrée même barre).

SIZING VIRTUEL
--------------
1 % de risque par trade sur un capital fictif initial de 10 000 PAR BRAS,
dimensionné par `core/risk/guards.py` (RiskLayer.evaluate) : le journal parle
en R ET en monnaie. Le R reste la mesure de vérité ; la monnaie est une
lecture. Les deux bras ont chacun leur capital — l'observation ne contamine
jamais la comptabilité du bras principal.
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


class SealError(RuntimeError):
    """Le fichier de paramètres ne correspond pas au hash scellé."""


class JournalError(RuntimeError):
    """Le journal a été altéré (chaîne cassée, troncature, réécriture)."""


# Les données ne vivent JAMAIS dans l'arborescence de code (convention projet).
# Migration tbot : l'état vit sous C:\db\tradingBot\ (core.paths.db_dir, seam
# TBOT_DB_DIR) — plus jamais sous C:\db\tbot\ (prototype en exploitation,
# lecture seule absolue).
def default_data_dir() -> str:
    env = os.environ.get("S13_FORWARD_DIR")
    return env if env else os.path.join(str(db_dir()), "s13_forward")


JOURNAL_COLUMNS = [
    "measured_at_utc",   # quand le script a tourné — l'horodatage de MESURE
    "event",             # OPEN | CLOSE
    "arm",               # PRIMARY (AUDCAD) | OBSERVATION (EURJPY)
    "symbol",
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
    "pnl_r",
    "pnl_ccy",
    "capital_after",
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


def load_sealed_params(path: str, expected_sha256: str) -> dict:
    """Charge les paramètres figés. Refus net si le hash ne correspond pas :
    un forward-test dont la règle a bougé n'est plus un forward-test."""
    with open(path, "rb") as f:
        raw = f.read()
    got = sha256_bytes(raw)
    if got != expected_sha256:
        raise SealError(
            f"SCELLÉ VIOLÉ — {os.path.basename(path)} : SHA-256 attendu "
            f"{expected_sha256[:16]}…, obtenu {got[:16]}…. Toute modification "
            f"des paramètres invalide le test (PROTOCOL.md, critère d). "
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
    """Deux contrôles, du plus local au plus global.

    1. CHAÎNE INTERNE — chaque ligne porte le SHA-256 du fichier tel qu'il
       était avant elle. Réécrire, insérer ou supprimer une ligne passée casse
       tous les maillons suivants. Le fichier se vérifie SEUL, sans état.
    2. EMPREINTE D'ÉTAT — `state.json` mémorise (taille, SHA-256) du journal au
       dernier passage. Une reconstruction complète du fichier (chaîne interne
       cohérente mais contenu différent) est attrapée ici.

    Ni l'un ni l'autre n'arrête un falsificateur qui réécrit TOUT (journal +
    état) : cette couche-là est le dépôt git et les horodatages de mesure —
    voir PROTOCOL.md § intégrité.
    """
    if not os.path.exists(path):
        if state is not None and state.get("journal_bytes", 0) > 0:
            raise JournalError("journal.csv absent alors que l'état en "
                               "référence un — suppression détectée")
        return

    with open(path, "rb") as f:
        raw = f.read()

    # 1. chaîne interne
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

    # 2. empreinte du dernier passage
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
    """Ajoute des lignes en fin de fichier, chaînées. Retourne l'empreinte
    (octets, SHA-256) du fichier après écriture — à consigner dans l'état."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Exécution — conventions du moteur commun
# ─────────────────────────────────────────────────────────────────────────────

def edge_cost_of(spec: dict) -> float:
    """Demi-spread + slippage, payé à CHAQUE extrémité — engine.py ligne à ligne."""
    return (spec["spread_pips"] * spec["pip"] / 2.0
            + spec["slippage_pips"] * spec["pip"])


def check_exit(pos: dict, bar) -> Optional[tuple[float, str]]:
    """Le test de sortie du moteur commun, sur UNE barre.

    Unilatéral : le stop est franchi dès que la barre l'atteint ou le dépasse ;
    une barre qui ouvre au-delà exécute à l'ouverture (le gap se paie). La
    cible n'a pas ce privilège. SL et TP dans la même barre -> SL.
    """
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


def _open_position(sig: Signal, bar_time: pd.Timestamp, spec: dict,
                   sizing: dict, capital: float) -> Optional[dict]:
    """Dimensionne et ouvre une position virtuelle via la couche de risque.

    Le prix d'entrée inclut le coût de bord (comme le moteur) et c'est CE prix
    qui sert au dimensionnement : le risque dimensionné est le risque payé.
    """
    cost = edge_cost_of(spec)
    long = sig.side == Side.LONG
    entry_exec = float(sig.entry) + (cost if long else -cost)

    sized = Signal(
        timestamp=sig.timestamp, symbol=spec["symbol"], side=sig.side,
        entry=entry_exec, stop=float(sig.stop),
        target=float(sig.target) if sig.target is not None else None,
        reason=sig.reason)

    limits = RiskLimits(
        max_position_pct=sizing["risk_per_trade_pct"] / 100.0,
        max_open_positions=1)
    risk = RiskLayer(capital=capital, limits=limits)
    value_per_unit = spec["pip_value_per_lot"] / spec["pip"]
    d = risk.evaluate(sized, value_per_unit=value_per_unit)
    if not d:
        return None                       # refus tracé côté appelant

    return {
        "trade_id": f"{spec['symbol']}_{sig.side.name}_{bar_time.strftime('%Y%m%d')}",
        "side": sig.side.name,
        "entry_bar_time": bar_time.isoformat(),
        "entry_price": entry_exec,
        "stop_price": float(sig.stop),
        "target_price": float(sig.target) if sig.target is not None else None,
        "risk_distance": abs(entry_exec - float(sig.stop)),
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
# Le pas de mesure
# ─────────────────────────────────────────────────────────────────────────────

SignalFn = Callable[[pd.DataFrame], dict]      # bar_time -> Signal


def _new_symbol_state(df: pd.DataFrame, capital: float) -> dict:
    return {
        "seal_bar_time": df.index[-1].isoformat(),
        "last_bar_time": df.index[-1].isoformat(),
        "capital": capital,
        "open_position": None,
        "cooldown_bars_left": 0,
        "consecutive_losses": 0,
        "n_closed": 0,
        "cum_r": 0.0,
    }


def run_step(dfs: dict[str, pd.DataFrame], params: dict, paths: Paths,
             signal_fns: dict[str, SignalFn],
             now: Optional[datetime] = None) -> dict:
    """Un passage de mesure sur les deux bras. Idempotent, append-only, sans
    effet si rien de neuf.

    `dfs[sym]` : barres CLÔTURÉES uniquement (l'appelant retire la barre en
    formation). Un instrument absent de `dfs` (MT5 partiel) est sauté ce
    passage — son curseur ne bouge pas. `signal_fns[sym](df)` rend
    {bar_time -> Signal} — en production la stratégie s13 avec les paramètres
    scellés ; dans les tests, des signaux injectés. Retourne un résumé.
    """
    paths.ensure()
    measured_at = _now_iso(now)
    state = load_state(paths.state)
    symbols = list(params["instruments"])

    # Intégrité AVANT toute écriture : un journal altéré arrête tout ici.
    verify_journal(paths.journal, state)

    if state is None:
        # PREMIER PASSAGE — pose du scellé. Aucun signal historique n'entre au
        # journal : le test est prospectif, il commence MAINTENANT. Le curseur
        # de chaque bras est posé sur sa dernière barre close ; tout ce qui la
        # précède est de l'histoire, tout ce qui la suit sera mesuré. Le
        # scellé se pose sur les DEUX flux à la fois — pas de bras qui
        # démarre en retard.
        missing = [s for s in symbols if s not in dfs or dfs[s] is None
                   or not len(dfs[s])]
        if missing:
            raise ValueError(f"premier passage : instruments manquants "
                             f"{missing} — le scellé se pose sur les deux "
                             f"flux à la fois")
        init_journal(paths.journal)
        n_bytes, sha = os.path.getsize(paths.journal), sha256_file(paths.journal)
        cap0 = params["sizing"]["capital_initial"]
        state = {
            "schema": 1,
            "started_at": measured_at,
            "symbols": {s: _new_symbol_state(dfs[s], cap0) for s in symbols},
            "journal_bytes": n_bytes,
            "journal_sha256": sha,
        }
        save_state(paths.state, state)
        return _write_status(dfs, params, paths, state, measured_at,
                             opened=0, closed=0, first_pass=True)

    init_journal(paths.journal)
    rows: list[dict] = []
    counters = {"opened": 0, "closed": 0}

    for sym in symbols:
        if sym not in dfs or dfs[sym] is None or not len(dfs[sym]):
            continue
        _step_symbol(sym, dfs[sym], params, state, rows, counters,
                     signal_fns[sym], measured_at)

    if rows:
        n_bytes, sha = append_journal(paths.journal, rows)
        state["journal_bytes"] = n_bytes
        state["journal_sha256"] = sha

    save_state(paths.state, state)
    return _write_status(dfs, params, paths, state, measured_at,
                         opened=counters["opened"], closed=counters["closed"],
                         first_pass=False)


def _step_symbol(sym: str, df: pd.DataFrame, params: dict, state: dict,
                 rows: list[dict], counters: dict, signal_fn: SignalFn,
                 measured_at: str) -> None:
    spec = params["specs"][sym]
    arm = params["instruments"][sym]
    st = state["symbols"][sym]
    last = pd.Timestamp(st["last_bar_time"])
    new_bars = df[df.index > last]
    if not len(new_bars):
        return
    signals = signal_fn(df)

    def _row(event, ts, pos, **kw):
        return {
            "measured_at_utc": measured_at, "event": event, "arm": arm,
            "symbol": sym, "trade_id": pos["trade_id"],
            "bar_time": ts.isoformat(), "side": pos["side"],
            "entry_price": f"{pos['entry_price']:.5f}",
            "stop_price": f"{pos['stop_price']:.5f}",
            "target_price": ("" if pos["target_price"] is None
                             else f"{pos['target_price']:.5f}"),
            "size_lots": f"{pos['size_lots']:.4f}",
            "risk_ccy": f"{pos['risk_ccy']:.2f}",
            **kw,
        }

    for ts, bar in new_bars.iterrows():
        pos = st["open_position"]

        # 1 — la position ouverte sort-elle sur cette barre ? (jamais sur sa
        #     barre d'entrée : le moteur évalue à partir de la barre suivante)
        if pos is not None and ts > pd.Timestamp(pos["entry_bar_time"]):
            ex = check_exit(pos, bar)
            if ex is not None:
                exit_price, reason = ex
                pnl_r, pnl_ccy = _close_pnl(pos, exit_price, spec)
                st["capital"] += pnl_ccy
                st["n_closed"] += 1
                st["cum_r"] += pnl_r
                rows.append(_row(
                    "CLOSE", ts, pos,
                    exit_price=f"{exit_price:.5f}", exit_reason=reason,
                    pnl_r=f"{pnl_r:+.4f}", pnl_ccy=f"{pnl_ccy:+.2f}",
                    capital_after=f"{st['capital']:.2f}"))
                counters["closed"] += 1
                st["open_position"] = None
                # cooldown + circuit breaker, sémantique du moteur — avec les
                # engine_kwargs de l'étude (cooldown 0, cb_losses 999) ces
                # branches sont inertes, mais la mécanique reste conforme.
                st["cooldown_bars_left"] = params["engine"]["cooldown_bars"]
                if pnl_r < 0:
                    st["consecutive_losses"] += 1
                    if st["consecutive_losses"] >= params["engine"]["cb_losses"]:
                        st["cooldown_bars_left"] = params["engine"]["cb_cooldown_bars"]
                        st["consecutive_losses"] = 0
                else:
                    st["consecutive_losses"] = 0

        # 2 — nouveau signal sur cette barre ? (bloqué si position ouverte ou
        #     cooldown en cours — mêmes règles que le moteur ; avec cooldown 0
        #     un signal sur la barre de sortie ré-entre, comme le moteur)
        if st["open_position"] is None and st["cooldown_bars_left"] == 0:
            sig = signals.get(ts)
            if sig is not None and spec["spread_pips"] <= spec["max_spread_pips"]:
                pos_new = _open_position(sig, ts, spec, params["sizing"],
                                         st["capital"])
                if pos_new is not None:
                    st["open_position"] = pos_new
                    rows.append(_row("OPEN", ts, pos_new,
                                     capital_after=f"{st['capital']:.2f}"))
                    counters["opened"] += 1

        if st["cooldown_bars_left"] > 0:
            st["cooldown_bars_left"] -= 1

    st["last_bar_time"] = df.index[-1].isoformat()


def _write_status(dfs: dict[str, pd.DataFrame], params: dict, paths: Paths,
                  state: dict, measured_at: str, *, opened: int, closed: int,
                  first_pass: bool) -> dict:
    """status.json — l'état contre les critères d'arrêt du protocole.

    Le percentile témoin (coûteux : 200 exécutions de moteur) n'est PAS
    recalculé ici : c'est le rôle de `report_forward.py`. Le status donne les
    effectifs, le R cumulé et la distance aux seuils d'effectif/temps — les
    critères ne regardent QUE le bras principal.
    """
    rules = params["stop_rules"]
    primary = params["primary_symbol"]
    started = datetime.strptime(state["started_at"], "%Y-%m-%dT%H:%M:%SZ")
    now_dt = datetime.strptime(measured_at, "%Y-%m-%dT%H:%M:%SZ")
    months = (now_dt - started).days / 30.44

    arms = {}
    for sym, st in state["symbols"].items():
        unrealized_r = None
        pos = st["open_position"]
        df = dfs.get(sym)
        if pos is not None and df is not None and len(df):
            spec = params["specs"][sym]
            last_close = float(df["close"].iloc[-1])
            long = pos["side"] == "LONG"
            gross = ((last_close - pos["entry_price"]) if long
                     else (pos["entry_price"] - last_close))
            gross -= edge_cost_of(spec)
            unrealized_r = round(gross / pos["risk_distance"], 4)
        arms[sym] = {
            "arm": params["instruments"][sym],
            "seal_bar_time": st["seal_bar_time"],
            "last_bar_time": st["last_bar_time"],
            "n_closed_total": st["n_closed"],
            "cum_r": round(st["cum_r"], 4),
            "mean_r": (round(st["cum_r"] / st["n_closed"], 4)
                       if st["n_closed"] else None),
            "capital": round(st["capital"], 2),
            "open_position": pos,
            "unrealized_r": unrealized_r,
        }

    n_primary = state["symbols"][primary]["n_closed"]
    status = {
        "generated_at_utc": measured_at,
        "first_pass": first_pass,
        "primary_symbol": primary,
        "opened_this_pass": opened,
        "closed_this_pass": closed,
        "months_elapsed": round(months, 2),
        "arms": arms,
        "stop_criteria": {
            "scope": f"bras principal {primary} UNIQUEMENT — l'observation "
                     f"n'entre dans aucun critère",
            "fail": (f"actif dès {rules['fail']['min_trades']} trades clôturés "
                     f"(n = {n_primary}) ; verdict au percentile témoin "
                     f"< {rules['fail']['percentile_below']} — "
                     f"voir report_forward.py"),
            "success": (f"actif dès {rules['success']['min_trades']} trades "
                        f"(n = {n_primary}) ; percentile témoin "
                        f">= {rules['success']['percentile_at_least']}"),
            "time": (f"NON CONCLUSIF si < {rules['time']['min_trades']} trades "
                     f"après {rules['time']['months']} mois "
                     f"(écoulés : {months:.1f})"),
            "horizon": (f"lecture finale obligatoire à "
                        f"{rules['horizon']['months']} mois si ni (a) ni (b)"),
        },
    }
    tmp = paths.status + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    os.replace(tmp, paths.status)
    return status
