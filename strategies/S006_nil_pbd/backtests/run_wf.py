"""
Walk-forward ancré — s06_nil_pbd, les DEUX modes testés SÉPARÉMENT.

R9 : ce script n'exécute rien lui-même. Il appelle `core.backtest.anchored_wf`,
le harnais commun, une fois par (instrument, mode). Les deux modes ne sont
jamais dans la même grille : « le range tient » et « le range cède » sont deux
hypothèses opposées, et les fondre reviendrait à laisser l'optimiseur choisir
son camp cellule par cellule.

    python -m strategies.S006_nil_pbd.backtests.run_wf
"""
from __future__ import annotations

import dataclasses
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward          # noqa: E402
from core.data.instruments import get_spec                       # noqa: E402
from core.data.source import load_bars                           # noqa: E402
from strategies.S006_nil_pbd.strategy import Strategy             # noqa: E402

SYMBOLS = ["DAX", "WTIUSD"]

# ── Les deux grilles, volontairement petites ────────────────────────────────
# 32 et 24 cellules -> ~1,6 et ~1,2 réussites STRICT attendues par PUR HASARD.
# Une grille large ne trouve pas un meilleur edge, elle trouve un meilleur
# faux positif.
GRIDS = {
    "fade": {
        "stop_mode": ["edge025", "edge05", "edge10", "extreme"],
        "target_mode": ["pingpong", "impulse_start"],
        "imp_atr": [1.5, 2.5],
        "va_filter": [0, 1],
    },
    "break": {
        "stop_mode": ["mid", "opp", "atr"],
        "tgt_mult": [1.0, 2.0],
        "imp_atr": [1.5, 2.5],
        "va_filter": [0, 1],
    },
}

# Spread DAX relevé DANS LES DONNÉES (colonne `spread`, médiane 280 points à
# 0,01 = 2,80 points d'indice) contre 0,80 au catalogue. Le catalogue sous-estime
# le péage réel d'un facteur 3,5 ; on mesure donc aux deux niveaux plutôt que de
# choisir celui qui arrange. Le catalogue n'est PAS modifié (interdit).
REAL_SPREAD_PIPS = {"DAX": 28.0, "WTIUSD": 2.6}


def main() -> int:
    out = []
    for symbol in SYMBOLS:
        bars = load_bars(symbol, "M15")
        if bars is None or len(bars) < 5000:
            out.append(f"[SKIP] {symbol} — données insuffisantes")
            continue

        for mode, grid in GRIDS.items():
            for spread_label, spec in (
                ("catalogue", get_spec(symbol)),
                ("réel mesuré", dataclasses.replace(
                    get_spec(symbol),
                    spread_pips=REAL_SPREAD_PIPS[symbol],
                    max_spread_pips=max(get_spec(symbol).max_spread_pips,
                                        REAL_SPREAD_PIPS[symbol] * 2))),
            ):
                strat = Strategy({"mode": mode})
                strat.params["_symbol"] = symbol
                rep = run_walk_forward(strat, bars, spec, param_grid=grid,
                                       min_trades=30, max_dd_r=25.0,
                                       verbose=False)
                head = (f"\n\n{'#' * 96}\n# {symbol} — mode {mode.upper()} "
                        f"— spread {spread_label} ({spec.spread_pips:g} pips)\n"
                        f"{'#' * 96}")
                print(head, flush=True)
                print(rep.render(), flush=True)
                out.append(head)
                out.append(rep.render())

    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "anchored_wf.txt")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"\n-> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
