"""
FORWARD-TEST SCELLÉ s13 — LA LECTURE
=====================================

    python -m studies.s13_forward.report_forward

Affiche l'état du forward-test CONTRE les critères d'arrêt de PROTOCOL.md, et
rien d'autre. Ce script ne décide pas : il dit lequel des critères, écrits
avant le premier signal, est atteint — ou qu'aucun ne l'est.

LES CRITÈRES NE REGARDENT QUE LE BRAS PRINCIPAL (AUDCAD). Le bras
d'observation (EURJPY) est lu avec les mêmes instruments de mesure — même
témoin, mêmes engine_kwargs — mais n'entre dans AUCUN critère : sa jumelle
n'a pas battu son beta au hold-out, elle est là pour apprendre.

LE TÉMOIN
---------
Le percentile est recalculé sur LA FENÊTRE ÉCOULÉE du forward-test (du scellé
à la dernière barre mesurée), via `core.backtest.anchored_wf.control_arm` —
le même bras témoin que l'étude, avec les MÊMES engine_kwargs que la
stratégie (cooldown 0, circuit breaker désarmé — ceux de
`run_holdout.py`). 200 tirages, graine figée : deux exécutions du rapport
donnent le même percentile.

Lecture : le R cumulé du forward est comparé à la distribution de R que
produisent des entrées aléatoires au dispositif de risque identique sur les
mêmes barres. Sous le percentile 20 après >= 20 trades, le protocole dit STOP.
"""
from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np                                        # noqa: E402
import pandas as pd                                       # noqa: E402

from core.backtest.anchored_wf import control_arm         # noqa: E402
from core.backtest.engine import ExecutedTrade, InstrumentSpec  # noqa: E402
from core.contracts.strategy import Side                  # noqa: E402
from core.data.source import load_bars                    # noqa: E402
from studies.s13_forward.forward_step import (             # noqa: E402
    JournalError, Paths, SealError, load_sealed_params, load_state,
    read_journal, verify_journal,
)
from studies.s13_forward.run_forward import (              # noqa: E402
    PARAMS_PATH, PARAMS_SHA256,
)


def mean_ci95(x: list[float]) -> tuple[float, float, float]:
    a = np.asarray(x, dtype=float)
    if a.size == 0:
        return (float("nan"),) * 3
    m = float(a.mean())
    if a.size < 2:
        return m, float("nan"), float("nan")
    se = float(a.std(ddof=1) / math.sqrt(a.size))
    return m, m - 1.96 * se, m + 1.96 * se


def closed_trades(journal: list[dict], symbol: str) -> list[dict]:
    rows = [r for r in journal if r["symbol"] == symbol]
    opens = {r["trade_id"]: r for r in rows if r["event"] == "OPEN"}
    out = []
    for r in rows:
        if r["event"] != "CLOSE":
            continue
        o = opens.get(r["trade_id"], {})
        # bar_time de l'OPEN = barre d'entrée ; celui du CLOSE = barre de sortie
        out.append({**r, "entry_bar_time": o.get("bar_time", r["bar_time"])})
    return out


def to_executed(rows: list[dict], symbol: str) -> list[ExecutedTrade]:
    """Reconstruit les trades clos au format du moteur, pour nourrir le témoin
    (qui n'utilise que le sens, l'heure d'entrée, le stop et la cible en ATR)."""
    out = []
    for r in rows:
        entry = float(r["entry_price"])
        stop = float(r["stop_price"])
        target = float(r["target_price"]) if r.get("target_price") else None
        out.append(ExecutedTrade(
            signal_time=pd.Timestamp(r.get("entry_bar_time")
                                     or r["bar_time"]).to_pydatetime(),
            entry_time=pd.Timestamp(r.get("entry_bar_time")
                                    or r["bar_time"]).to_pydatetime(),
            exit_time=pd.Timestamp(r["bar_time"]).to_pydatetime(),
            symbol=symbol, side=Side[r["side"]],
            entry_price=entry, exit_price=float(r["exit_price"]),
            stop_price=stop, target_price=target,
            exit_reason=r["exit_reason"], risk_distance=abs(entry - stop),
            pnl_r=float(r["pnl_r"]), bars_held=0,
        ))
    return out


def arm_section(sym: str, params: dict, state: dict,
                journal: list[dict]) -> tuple[int, float, object, object]:
    """Affiche la section d'un bras ; retourne (n, cum_r, percentile, p_fail)
    pour l'évaluation des critères (utilisés seulement pour le bras principal).
    """
    role = params["instruments"][sym]
    st = state["symbols"][sym]
    closed = closed_trades(journal, sym)
    rs = [float(r["pnl_r"]) for r in closed]
    n = len(rs)
    cum_r = float(sum(rs))
    rules = params["stop_rules"]

    label = ("BRAS PRINCIPAL — comptable dans les critères"
             if role == "PRIMARY" else
             "BRAS D'OBSERVATION — jamais dans les critères (apprentissage)")
    print(f"── {sym} · {label} " + "─" * max(0, 60 - len(sym)))
    print(f"scellé posé sur la barre {st['seal_bar_time']} · dernière barre "
          f"mesurée : {st['last_bar_time']}")
    m, lo, hi = mean_ci95(rs)
    print(f"trades clôturés : {n}   R cumulé : {cum_r:+.2f}   "
          f"capital virtuel : {st['capital']:.2f} "
          f"(départ {params['sizing']['capital_initial']:.0f})")
    if n:
        print(f"R moyen : {m:+.3f}   IC 95 % : [{lo:+.3f} ; {hi:+.3f}]   "
              f"effectif n = {n}"
              + ("   (IC indicatif : n < 40)" if n < 40 else ""))
        wins = sum(1 for r in rs if r > 0)
        print(f"taux de réussite : {100*wins/n:.1f} % ({wins}/{n})")
    if st.get("open_position"):
        p = st["open_position"]
        print(f"position ouverte : {p['side']} depuis {p['entry_bar_time']} "
              f"(hors R cumulé — valorisée seulement au status)")

    # ── Le témoin, sur la fenêtre écoulée ───────────────────────────────────
    percentile = p_fail = None
    if n == 0:
        print("Témoin aléatoire : non calculable — aucun trade clôturé.")
    else:
        df = load_bars(sym, params["timeframe"], max_age_hours=24)
        if df is None:
            print(f"Témoin aléatoire : barres indisponibles ({sym}, MT5 hors "
                  f"ligne) — percentile non recalculé ce passage.",
                  file=sys.stderr)
        else:
            first = pd.Timestamp(min(pd.Timestamp(r.get("entry_bar_time")
                                                  or r["bar_time"])
                                     for r in closed))
            last = pd.Timestamp(st["last_bar_time"])
            # marge amont pour l'ATR du témoin (14 barres D1 + confort)
            sl = df[(df.index >= first - pd.Timedelta(days=40))
                    & (df.index <= last)]
            spec = InstrumentSpec(**params["specs"][sym])
            ca = control_arm(
                sl, spec, to_executed(closed, sym),
                strategy_r=cum_r,
                draws=params["control"]["draws"],
                seed=params["control"]["seed"],
                engine_kwargs=dict(params["engine"]),
            )
            if ca is None:
                print("Témoin aléatoire : gabarit inconstructible sur cette "
                      "fenêtre (effectif/ATR insuffisants).")
            else:
                percentile = ca.percentile
                p_fail = float(np.percentile(
                    ca.draws_r, rules["fail"]["percentile_below"]))
                print("Témoin aléatoire — mêmes barres, même dispositif de "
                      "risque, mêmes engine_kwargs :")
                print(f"    {ca.line()}")
                print(f"    percentile {rules['fail']['percentile_below']} du "
                      f"témoin : {p_fail:+.2f} R   (le R cumulé du forward "
                      f"vaut {cum_r:+.2f})")
    print()
    return n, cum_r, percentile, p_fail


def main() -> int:
    try:
        params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3

    paths = Paths()
    state = load_state(paths.state)
    if state is None:
        print("Aucun état : le forward-test n'a jamais tourné "
              "(python -m studies.s13_forward.run_forward).")
        return 1
    try:
        verify_journal(paths.journal, state)
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        return 4

    journal = read_journal(paths.journal)
    rules = params["stop_rules"]
    primary = params["primary_symbol"]

    started = datetime.strptime(state["started_at"], "%Y-%m-%dT%H:%M:%SZ")
    months = (datetime.now(timezone.utc).replace(tzinfo=None) - started).days / 30.44

    print("=" * 88)
    print("FORWARD-TEST SCELLÉ — s13 extrême-MACD long D1 — lecture contre "
          "PROTOCOL.md")
    print("=" * 88)
    print(f"scellé posé le {state['started_at']} · {months:.1f} mois écoulés")
    print()

    n = cum_r = percentile = p_fail = None
    for sym in params["instruments"]:
        res = arm_section(sym, params, state, journal)
        if sym == primary:
            n, cum_r, percentile, p_fail = res

    # ── Verdict contre les critères, dans l'ordre du protocole — bras
    #    principal UNIQUEMENT ─────────────────────────────────────────────────
    print("-" * 88)
    print(f"Critères d'arrêt — évalués sur {primary} seul :")
    verdicts = []
    f_ = rules["fail"]
    if n >= f_["min_trades"] and percentile is not None and cum_r < p_fail:
        verdicts.append(
            f"ARRÊT-ÉCHEC (critère a) : n = {n} >= {f_['min_trades']} et "
            f"R cumulé {cum_r:+.2f} < percentile {f_['percentile_below']} du "
            f"témoin ({p_fail:+.2f}). STOP DÉFINITIF — pas d'edge confirmé en "
            f"prospectif.")
    s_ = rules["success"]
    if n >= s_["min_trades"] and percentile is not None \
            and percentile >= s_["percentile_at_least"]:
        verdicts.append(
            f"ARRÊT-SUCCÈS (critère b) : n = {n} >= {s_['min_trades']} et "
            f"percentile témoin {percentile:.1f} >= "
            f"{s_['percentile_at_least']}. Promotion en discussion — "
            f"décision Adrian.")
    t_ = rules["time"]
    if months >= t_["months"] and n < t_["min_trades"]:
        verdicts.append(
            f"ARRÊT-TEMPS (critère c1) : {months:.1f} mois écoulés et "
            f"seulement {n} trades < {t_['min_trades']}. NON CONCLUSIF — "
            f"fréquence effondrée, on ferme.")
    h_ = rules["horizon"]
    if not verdicts and months >= h_["months"]:
        verdicts.append(
            f"HORIZON (critère c2) : {months:.1f} mois écoulés sans (a) ni "
            f"(b). NON CONCLUSIF — lecture finale obligatoire, on ferme.")

    if verdicts:
        for v in verdicts:
            print(v)
    else:
        print("AUCUN critère d'arrêt atteint — continuer.")
        print(f"    critère a (échec)   : armé à {f_['min_trades']} trades "
              f"(encore {max(0, f_['min_trades']-n)})"
              + (f" ; marge actuelle au percentile "
                 f"{f_['percentile_below']} : {cum_r - p_fail:+.2f} R"
                 if p_fail is not None else ""))
        print(f"    critère b (succès)  : armé à {s_['min_trades']} trades "
              f"(encore {max(0, s_['min_trades']-n)})"
              + (f" ; percentile témoin actuel : {percentile:.1f}"
                 if percentile is not None else ""))
        print(f"    critère c1 (temps)  : {t_['months']} mois si "
              f"< {t_['min_trades']} trades (écoulés {months:.1f}, "
              f"reste {max(0.0, t_['months']-months):.1f})")
        print(f"    critère c2 (horizon): lecture finale à {h_['months']} mois "
              f"(reste {max(0.0, h_['months']-months):.1f})")
    print("-" * 88)
    print("Rappel critère d : toute modification des paramètres scellés "
          "invalide le test (redémarrage à zéro).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
