"""
ESSAI À BLANC MACD+IA — CLI du pas quotidien
=============================================

    python -m studies.macd_ai_paper.run_paper [--stale-ok] [--test-judge]

Exécutable à toute fréquence (une fois par jour suffit — D1) : idempotent,
append-only, sans effet si aucune barre nouvelle, et ne rappelle jamais le
juge IA sur un signal déjà traité. Voir PROTOCOL.md — le scellé — et
`paper_step.py` — la mécanique.

CODES DE SORTIE
---------------
    0  passage effectué (y compris « rien de neuf »)
    2  MT5 / données indisponibles — journal intact, réessayer plus tard
    3  scellé violé (hash des paramètres) — NE PAS « réparer » : toute
       modification des paramètres invalide l'essai (PROTOCOL.md, invariance)
    4  journal altéré (chaîne cassée, troncature) — enquête requise avant
       tout nouveau passage

`--stale-ok`  : accepte un cache de barres périmé. Réservé à la validation de
                chaîne (premier passage à la main).
`--test-judge`: appelle le juge headless sur un dossier factice marqué TEST,
                affiche la décision, ne touche NI journal NI état. C'est la
                validation de bout en bout du maillon CLI.
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

import pandas as pd                                       # noqa: E402

from core.data.source import load_bars                    # noqa: E402
from strategies.S012_prt_macd_meanrev.strategy import Strategy  # noqa: E402
from studies.first_pass import first_pass_refused          # noqa: E402
from studies.macd_ai_paper.ai_judge import make_judge     # noqa: E402
from studies.macd_ai_paper.paper_step import (            # noqa: E402
    JournalError, Paths, SealError, load_sealed_params, run_step,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS_PATH = os.path.join(HERE, "params.json")

# LE SCELLÉ. Ce hash est aussi consigné dans PROTOCOL.md (committé). Modifier
# params.json, ce hash ou les deux laisse une trace git — c'est le but.
PARAMS_SHA256 = "36b635bd775bef284456000d73ca7c39ff420551d27265a7fd382cb372a20a5b"

# Un pas de mesure quotidien doit voir des barres du jour.
FRESH_MAX_AGE_H = 20
WARMUP_MIN_BARS = 80         # warmup s12 (60) + marge


def make_signal_fn(params: dict, symbol: str):
    """La stratégie s12 avec la cellule SCELLÉE, et rien d'autre. Même code
    que le backtest (R5 : pas de deuxième implémentation). Seuls les signaux
    postérieurs au curseur sont consommés par `run_step`."""
    def fn(df: pd.DataFrame) -> dict:
        s = Strategy()
        s._symbol = symbol
        p = dict(s.manifest().default_params)
        p.update(params["cell"])
        pre = s.precompute(df, p)
        sigs = s.generate_signals(pre, p, len(df))
        return {pd.Timestamp(sig.timestamp): sig for sig in sigs}
    return fn


def test_judge(params: dict) -> int:
    """Dossier factice marqué TEST -> un appel headless réel. Rien n'est
    journalisé : c'est un contrôle de chaîne, pas une mesure."""
    from studies.macd_ai_paper.paper_step import clamp_decision
    dossier = {
        "TEST": ("dossier factice de validation de chaîne — ne correspond à "
                 "aucun signal réel"),
        "strategy": {"id": params["strategy_id"],
                     "rules": "LONG only, indice D1, mean reversion (TEST)"},
        "signal": {"side": "LONG", "stop_distance_pct_of_entry": 2.5,
                   "target_distance_pct_of_entry": 0.9, "reward_risk": 0.36,
                   "macd_pct_of_entry": -0.4, "range_pos": 0.12,
                   "atr_pct_of_entry": 0.85},
        "market_bars_pct_of_entry": [
            {"o": -1.2, "h": -0.6, "l": -1.8, "c": -1.5},
            {"o": -1.5, "h": -0.9, "l": -2.1, "c": -1.0},
            {"o": -1.0, "h": -0.2, "l": -1.4, "c": -0.4},
            {"o": -0.4, "h": 0.3, "l": -0.8, "c": 0.0}],
        "account": {"capital": 10000.0, "start_capital": 10000.0,
                    "base_risk_pct": 1.0, "closed_trades": 0, "cum_r": 0.0,
                    "recent_trades_r": []},
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

    # Garde first-pass (studies/first_pass.py) : journal absent = étude pas
    # encore basculée (CUTOVER.md) — refus AVANT toute écriture. Après le
    # --test-judge : la sonde ne touche ni journal ni état.
    paths = Paths()
    if first_pass_refused(paths.journal, "macd_ai_paper"):
        return 2

    max_age = 24 * 365 * 10 if stale_ok else FRESH_MAX_AGE_H
    dfs = {}
    for sym in params["instruments"]:
        try:
            df = load_bars(sym, params["timeframe"], max_age_hours=max_age)
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
              "expliquée — voir PROTOCOL.md § intégrité.", file=sys.stderr)
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
          f"{ai['n_na']} N/A)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
