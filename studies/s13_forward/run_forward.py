"""
FORWARD-TEST SCELLÉ s13 — CLI du pas de mesure
===============================================

    python -m studies.s13_forward.run_forward [--stale-ok]

Exécutable à toute fréquence (une fois par jour suffit — barres D1) :
idempotent, append-only, sans effet si aucune barre nouvelle. Voir
PROTOCOL.md — le scellé — et `forward_step.py` — la mécanique.

CODES DE SORTIE
---------------
    0  passage effectué (y compris « rien de neuf »)
    2  MT5 / données indisponibles — journal intact, réessayer plus tard
    3  scellé violé (hash des paramètres) — NE PAS « réparer » : toute
       modification des paramètres invalide le test (PROTOCOL.md, critère d)
    4  journal altéré (chaîne cassée, troncature) — enquête requise avant
       tout nouveau passage

`--stale-ok` : accepte un cache de barres périmé. Réservé à la validation de
chaîne (premier passage à la main) — un passage de MESURE doit voir des barres
fraîches, sinon il ne mesure rien.
"""
from __future__ import annotations

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
from strategies.S013_macd_fx.strategy import Strategy     # noqa: E402
from studies.s13_forward.forward_step import (             # noqa: E402
    JournalError, Paths, SealError, load_sealed_params, run_step,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS_PATH = os.path.join(HERE, "params.json")

# LE SCELLÉ. Ce hash est aussi consigné dans PROTOCOL.md (committé). Modifier
# params.json, ce hash ou les deux laisse une trace git — c'est le but.
PARAMS_SHA256 = "df098b0e9699fa8ffeb109114f127dc67de88716d7663500e8ffe62436ef69e2"

# Cache : un pas de mesure quotidien (barres D1) doit voir la barre d'hier.
FRESH_MAX_AGE_H = 12
# lookback 252 (percentile glissant) + ATR 14 + marge : en dessous, la cellule
# n'a même pas son indicateur — refuser de mesurer plutôt que mesurer faux.
WARMUP_MIN_BARS = 320


def make_signal_fn(params: dict, symbol: str):
    """La stratégie s13 avec les paramètres SCELLÉS, et rien d'autre.

    Les signaux sont recalculés sur l'historique complet à chaque passage —
    même code que le backtest et le hold-out (R5 : pas de deuxième
    implémentation ; `strategy.precompute` + `generate_signals`, exactement
    comme `backtests/run_holdout.py`). Seuls les signaux postérieurs au
    curseur sont consommés par `run_step` ; le journal passé n'est jamais
    retouché.
    """
    def fn(df: pd.DataFrame) -> dict:
        s = Strategy()
        s._symbol = symbol
        p = dict(s.params)
        p.update(params["cell"])
        data = s.precompute(df, p)
        sigs = s.generate_signals(data, p, len(df))
        return {pd.Timestamp(sig.timestamp): sig for sig in sigs}
    return fn


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

    max_age = 24 * 365 * 10 if stale_ok else FRESH_MAX_AGE_H
    dfs = {}
    for sym in params["instruments"]:
        try:
            df = load_bars(sym, params["timeframe"], max_age_hours=max_age)
        except Exception as e:
            print(f"[DATA] chargement MT5 en échec ({sym}) : {e}",
                  file=sys.stderr)
            df = None
        if df is None or len(df) < WARMUP_MIN_BARS:
            print(f"[DATA] barres indisponibles ({sym} {params['timeframe']}) "
                  f"— MT5 fermé ou hors ligne ? Curseur intact, nouvel essai "
                  f"au prochain passage.", file=sys.stderr)
            continue
        # La dernière barre servie par MT5 est la barre EN FORMATION : la
        # traiter exécuterait des décisions sur un close qui n'existe pas
        # encore. On ne travaille que sur des barres clôturées.
        dfs[sym] = df.iloc[:-1]

    if not dfs:
        print("[DATA] aucun instrument disponible — passage annulé, journal "
              "intact.", file=sys.stderr)
        return 2

    paths = Paths()
    signal_fns = {sym: make_signal_fn(params, sym)
                  for sym in params["instruments"]}
    try:
        status = run_step(dfs, params, paths, signal_fns)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        print("[JOURNAL] aucun passage tant que l'altération n'est pas "
              "expliquée — voir PROTOCOL.md § intégrité.", file=sys.stderr)
        return 4
    except ValueError as e:
        # premier passage avec un flux manquant : le scellé ne se pose pas.
        print(f"[DATA] {e}", file=sys.stderr)
        return 2

    tag = "PREMIER PASSAGE — scellé posé" if status["first_pass"] else "passage"
    print(f"[{status['generated_at_utc']}] {tag} · "
          f"ouverts {status['opened_this_pass']} / clos "
          f"{status['closed_this_pass']} ce passage")
    for sym, arm in status["arms"].items():
        line = (f"    {sym} ({arm['arm']}) : barres jusqu'à "
                f"{arm['last_bar_time']} · total clos {arm['n_closed_total']} "
                f"· R cumulé {arm['cum_r']:+.2f} · capital "
                f"{arm['capital']:.2f}")
        print(line)
        if arm["open_position"]:
            p = arm["open_position"]
            extra = (f" · latent {arm['unrealized_r']:+.3f} R"
                     if arm["unrealized_r"] is not None else "")
            print(f"        position ouverte : {p['side']} depuis "
                  f"{p['entry_bar_time']} ({p['size_lots']:.4f} lots, "
                  f"{p['risk_ccy']:.2f} risqués){extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
