"""
FORWARD-TEST SCELLÉ — CLI du pas de mesure
===========================================

    python -m studies.gold_forward.run_forward [--stale-ok]

Exécutable à toute fréquence (une fois par heure ou par jour) : idempotent,
append-only, sans effet si aucune barre nouvelle. Voir PROTOCOL.md — le
scellé — et `forward_step.py` — la mécanique.

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
from strategies.S011_legacy_breakout.strategy import Strategy  # noqa: E402
from studies.first_pass import first_pass_refused          # noqa: E402
from studies.gold_forward.forward_step import (            # noqa: E402
    JournalError, Paths, SealError, load_sealed_params, run_step,
)

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS_PATH = os.path.join(HERE, "params.json")

# LE SCELLÉ. Ce hash est aussi consigné dans PROTOCOL.md (committé). Modifier
# params.json, ce hash ou les deux laisse une trace git — c'est le but.
PARAMS_SHA256 = "225fa9ab188450fa44883d404d797267251c6a945f23ea8c5e0e48be5583ed2f"

# Cache court : un pas de mesure horaire doit voir des barres fraîches.
FRESH_MAX_AGE_H = 1
WARMUP_MIN_BARS = 450        # warmup s11 (400) + marge


def make_signal_fn(params: dict):
    """La stratégie s11 avec les paramètres SCELLÉS, et rien d'autre.

    Les signaux sont recalculés sur l'historique complet à chaque passage —
    même code que le backtest (R5 : pas de deuxième implémentation). Seuls les
    signaux postérieurs au curseur sont consommés par `run_step` ; le journal
    passé n'est jamais retouché.
    """
    def fn(df: pd.DataFrame) -> dict:
        s = Strategy()
        s._symbol = params["instrument"]
        p = dict(s.params)
        p.update(params["cell"])
        p.update(params["fixed_params"])
        pre = s.precompute(df, p)
        return {pd.Timestamp(sig.timestamp): sig
                for _, sig in pre.attrs["signals"]}
    return fn


def main(argv: list[str]) -> int:
    stale_ok = "--stale-ok" in argv

    # Garde first-pass (studies/first_pass.py) : journal absent = étude pas
    # encore basculée (CUTOVER.md) — refus AVANT toute écriture.
    paths = Paths()
    if first_pass_refused(paths.journal, "gold_forward"):
        return 2

    try:
        params = load_sealed_params(PARAMS_PATH, PARAMS_SHA256)
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"[SEAL] params.json illisible : {e}", file=sys.stderr)
        return 3

    max_age = 24 * 365 * 10 if stale_ok else FRESH_MAX_AGE_H
    try:
        df = load_bars(params["instrument"], params["timeframe"],
                       max_age_hours=max_age)
    except Exception as e:
        print(f"[DATA] chargement MT5 en échec : {e}", file=sys.stderr)
        return 2
    if df is None or len(df) < WARMUP_MIN_BARS:
        print(f"[DATA] barres indisponibles ({params['instrument']} "
              f"{params['timeframe']}) — MT5 fermé ou hors ligne ? "
              f"Journal intact, nouvel essai au prochain passage.",
              file=sys.stderr)
        return 2

    # La dernière barre servie par MT5 est la barre EN FORMATION : la traiter
    # exécuterait des décisions sur un close qui n'existe pas encore. On ne
    # travaille que sur des barres clôturées.
    df = df.iloc[:-1]

    try:
        status = run_step(df, params, paths, make_signal_fn(params))
    except SealError as e:
        print(f"[SEAL] {e}", file=sys.stderr)
        return 3
    except JournalError as e:
        print(f"[JOURNAL] {e}", file=sys.stderr)
        print("[JOURNAL] aucun passage tant que l'altération n'est pas "
              "expliquée — voir PROTOCOL.md § intégrité.", file=sys.stderr)
        return 4

    tag = "PREMIER PASSAGE — scellé posé" if status["first_pass"] else "passage"
    print(f"[{status['generated_at_utc']}] {tag} · "
          f"barres jusqu'à {status['last_bar_time']} · "
          f"ouverts {status['opened_this_pass']} / clos {status['closed_this_pass']} "
          f"ce passage · total clos {status['n_closed_total']} · "
          f"R cumulé {status['cum_r']:+.2f} · capital {status['capital']:.2f}")
    if status["open_position"]:
        p = status["open_position"]
        print(f"    position ouverte : {p['side']} depuis {p['entry_bar_time']} "
              f"({p['size_lots']:.4f} lots, {p['risk_ccy']:.2f} risqués) · "
              f"latent {status['unrealized_r']:+.3f} R"
              if status["unrealized_r"] is not None else
              f"    position ouverte : {p['side']} depuis {p['entry_bar_time']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
