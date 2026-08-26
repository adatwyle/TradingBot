"""
ESSAI À BLANC fxalexg+IA — CLI du pas horaire
==============================================

    python -m studies.alexg_paper.run_paper [--stale-ok] [--test-judge]

Exécutable à toute fréquence (une fois par heure suffit — H1) : idempotent,
append-only, sans effet si aucune barre nouvelle, et ne rappelle jamais le
juge IA sur un signal déjà traité. Voir PROTOCOL.md — le scellé — et
`paper_step.py` — la mécanique.

CE RUNNER NE PASSE AUCUN ORDRE. Le compte MT5 branché est un compte RÉEL
(Swissquote, trade_mode=2, relevé le 2026-08-22). Il LIT des barres ; toute
l'exécution est simulée en Python. Aucune fonction d'envoi d'ordre n'est
importée ici — et il ne faut jamais en ajouter : la promotion vers l'argent
réel est une décision d'Adrian, pas une option de ligne de commande (R10).

CODES DE SORTIE
---------------
    0  passage effectué (y compris « rien de neuf »)
    2  MT5 / données indisponibles — journal intact, réessayer plus tard
    3  scellé violé (hash des paramètres) — NE PAS « réparer » : toute
       modification des paramètres invalide l'essai (PROTOCOL.md § 1)
    4  journal altéré (chaîne cassée, troncature) — enquête requise avant
       tout nouveau passage

`--stale-ok`  : accepte un cache de barres périmé. Réservé à la validation de
                chaîne (premier passage à la main).
`--test-judge`: appelle le juge headless sur un dossier factice marqué TEST,
                affiche la décision, ne touche NI journal NI état.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Migration tbot : `core` vit dans app/ — les deux racines sont importables.
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd                                          # noqa: E402

from core.data.source import load_bars                       # noqa: E402
from strategies.S093_alexg_ai_judge.strategy import Strategy  # noqa: E402
from studies.alexg_paper.ai_judge import make_judge          # noqa: E402
from studies.alexg_paper.paper_step import (                 # noqa: E402
    PARAMS_SHA256, JournalError, Paths, SealError, load_sealed_params, run_step,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS_PATH = os.path.join(HERE, "params.json")

# Un pas horaire doit voir des barres de l'heure. 3 h de tolérance couvre un
# tick manqué sans laisser passer un cache d'hier.
FRESH_MAX_AGE_H = 3
# Warmup du détecteur (2500 barres : ~15 semaines pour 4 pivots weekly en
# corps) + marge. En-dessous, la strategie ne produit rien de toute façon.
WARMUP_MIN_BARS = 2600
# Profondeur demandée à MT5 — la même que la mesure de fréquence du scellé.
HISTORY_DAYS = 1855


def make_signal_fn(params: dict, symbol: str):
    """Le détecteur v2 avec les paramètres SCELLÉS, et rien d'autre. Même
    code que le backtest (R5 : pas de deuxième implémentation du signal).
    Seuls les signaux postérieurs au curseur sont consommés par `run_step`."""
    def fn(df: pd.DataFrame) -> dict:
        s = Strategy()
        s._symbol = symbol
        p = dict(s.manifest().default_params)
        p.update(params["detector"])
        p["pip"] = params["specs"][symbol]["pip"]
        pre = s.precompute(df, p)
        sigs = s.generate_signals(pre, p, len(df))
        return {pd.Timestamp(sig.timestamp): sig for sig in sigs}
    return fn


def test_judge(params: dict) -> int:
    """Dossier factice marqué TEST -> un appel headless réel. Rien n'est
    journalisé : c'est un contrôle de chaîne, pas une mesure."""
    from studies.alexg_paper.paper_step import clamp_decision
    dossier = {
        "TEST": ("dossier factice de validation de chaîne — ne correspond à "
                 "aucun signal réel"),
        "methode": {"id": params["strategy_id"],
                    "resume": "swing forex H1, AOI + shift de structure (TEST)"},
        "confluences_detectees": {
            "side": "SHORT", "tf_sync": "W+D", "aoi_tf": "D",
            "aoi_width_pips": 31.0, "aoi_touches": 4, "aoi_dist_atr": 0.35,
            "aoi_both_tf": True, "retrace_frac": 0.62, "shift_break_atr": 0.44,
            "engulfing": True, "hs_neckline_retest": False,
            "round_dist_pips": 7.0, "ema_side_with_trade": True,
            "ema_dist_atr": 0.9, "rr": 2.4, "sl_pips": 28.0, "tp_pips": 67.0,
            "atr_pips": 19.0, "session": "London", "bars_since_aoi_visit": 5},
        "market_bars_pct_of_entry": [
            {"o": 0.42, "h": 0.55, "l": 0.30, "c": 0.36},
            {"o": 0.36, "h": 0.44, "l": 0.12, "c": 0.18},
            {"o": 0.18, "h": 0.22, "l": -0.05, "c": 0.05},
            {"o": 0.05, "h": 0.09, "l": -0.11, "c": 0.00}],
        "account": {"capital": 10000.0, "start_capital": 10000.0,
                    "base_risk_pct": 1.0, "closed_trades": 0, "cum_r": 0.0,
                    "recent_trades_r": [], "take_rate_so_far": None},
        "bounds": params["ai"]["bounds"],
    }
    dec = make_judge(params)(dossier)
    if dec is None:
        print("[TEST-JUDGE] ÉCHEC — le CLI claude n'a pas rendu de décision "
              "(voir stderr ci-dessus). Le runner traiterait ce signal en "
              "bras IA = N/A ; les témoins continueraient.")
        return 2
    print("[TEST-JUDGE] décision brute :", json.dumps(dec, ensure_ascii=False))
    print("[TEST-JUDGE] après clamp    :",
          json.dumps(clamp_decision(dec, params["ai"]["bounds"]),
                     ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    stale_ok = "--stale-ok" in argv

    try:
        params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"[SEAL] params.json illisible : {e}", file=sys.stderr)
        return 3

    if "--test-judge" in argv:
        return test_judge(params)

    max_age = 24 * 365 * 10 if stale_ok else FRESH_MAX_AGE_H
    dfs = {}
    for sym in params["instruments"]:
        try:
            df = load_bars(sym, params["timeframe"], days=HISTORY_DAYS,
                           max_age_hours=max_age)
        except Exception as e:
            print(f"[DATA] {sym} : chargement MT5 en échec : {e}",
                  file=sys.stderr)
            df = None
        if df is None or len(df) < WARMUP_MIN_BARS:
            print(f"[DATA] {sym} : barres indisponibles — MT5 fermé ou hors "
                  f"ligne ?", file=sys.stderr)
            continue
        # La dernière barre servie par MT5 est la barre EN FORMATION : on ne
        # travaille que sur des barres clôturées.
        dfs[sym] = df.iloc[:-1]

    if not dfs:
        print("[DATA] aucun instrument disponible — journal intact, nouvel "
              "essai au prochain passage.", file=sys.stderr)
        return 2

    paths = Paths()
    signal_fns = {sym: make_signal_fn(params, sym)
                  for sym in params["instruments"]}
    try:
        status = run_step(dfs, params, paths, signal_fns, make_judge(params))
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        print("[JOURNAL] aucun passage tant que l'altération n'est pas "
              "expliquée — voir PROTOCOL.md § 5.", file=sys.stderr)
        return 4
    except ValueError as e:
        # premier passage avec instruments manquants
        print(f"[DATA] {e}", file=sys.stderr)
        return 2

    tag = "PREMIER PASSAGE — scellé posé" if status["first_pass"] else "passage"
    a = status["arms"]
    print(f"[{status['generated_at_utc']}] {tag} · "
          f"ouverts {status['opened_this_pass']} / clos "
          f"{status['closed_this_pass']} ce passage")
    for arm in ("MECH", "AI", "RND"):
        s = a[arm]
        openp = f" · ouvertes: {', '.join(s['open_positions'])}" \
            if s["open_positions"] else ""
        print(f"    {arm:<4} capital {s['capital']:.2f} · clos "
              f"{s['n_closed']} · R cumulé {s['cum_r']:+.2f}{openp}")
    ai = status["ai_stats"]
    print(f"    IA : {ai['n_decisions']} décisions ({ai['n_takes']} take, "
          f"{ai['n_na']} N/A) · shadow clos {status['shadow']['n_closed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
