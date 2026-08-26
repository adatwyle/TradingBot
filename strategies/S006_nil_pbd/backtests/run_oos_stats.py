"""
Significativité et plateau — sur les seules tranches HORS ÉCHANTILLON.

Le walk-forward commun donne le R par fenêtre. Il ne dit pas si ce R se
distingue du bruit, ni si le voisinage de paramètres tient. Ce script répond aux
deux questions sur les MÊMES fenêtres (60/70/80/90 %), avec le moteur commun
(R9) et `max_hold_bars = 288` (la borne de détention de la source).

Agrégation : pour chaque fenêtre, on ne garde que les trades ENTRÉS après la fin
de la tranche d'entraînement — exactement la définition de `anchored_wf`.

    python -m strategies.s06_nil_pbd.backtests.run_oos_stats
"""
from __future__ import annotations

import dataclasses
import itertools
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import WINDOWS                     # noqa: E402
from core.backtest.engine import run as run_engine                # noqa: E402
from core.contracts.strategy import Side                          # noqa: E402
from core.data.instruments import get_spec                        # noqa: E402
from core.data.source import load_bars                            # noqa: E402
from strategies.s06_nil_pbd.backtests.run_wf import (              # noqa: E402
    GRIDS, REAL_SPREAD_PIPS, SYMBOLS,
)
from strategies.s06_nil_pbd.strategy import Strategy              # noqa: E402

MAX_HOLD = 288
L: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    L.append(s)


def oos_trades(strat, data, p, bars, spec):
    """Trades hors échantillon, concaténés sur les 4 fenêtres ancrées."""
    n = len(bars)
    out = []
    for a, b in WINDOWS:
        tr_end = int(n * a)
        te_end = int(n * b) if b < 1.0 else n
        sig = strat.generate_signals(data, p, te_end)
        res = run_engine(sig, bars, spec, end_idx=te_end, max_hold_bars=MAX_HOLD)
        cut = bars.index[tr_end - 1]
        out += [t for t in res.trades if t.entry_time > cut]
    return out


def main() -> int:
    for symbol in SYMBOLS:
        bars = load_bars(symbol, "M15")
        spec = dataclasses.replace(
            get_spec(symbol), spread_pips=REAL_SPREAD_PIPS[symbol],
            max_spread_pips=REAL_SPREAD_PIPS[symbol] * 2)
        spec_free = dataclasses.replace(spec, spread_pips=0.0)

        for mode, grid in GRIDS.items():
            say("\n" + "=" * 100)
            say(f"{symbol} — mode {mode.upper()} — TRANCHES HORS ÉCHANTILLON "
                f"agrégées (4 fenêtres), spread réel {spec.spread_pips:g} pips")
            say("=" * 100)
            say(f"{'configuration':<46} {'n':>5} {'WR%':>6} {'R/trade':>8} "
                f"{'t':>6} {'R tot':>8} {'R/tr @0':>8} {'L':>7} {'S':>7}")
            say("-" * 100)

            keys = sorted(grid)
            pos = 0
            tot = 0
            for combo in itertools.product(*(grid[k] for k in keys)):
                c = dict(zip(keys, combo))
                s = Strategy({"mode": mode})
                p = dict(s.params)
                p.update(c)
                p["_symbol"] = symbol
                data = s.precompute(bars, p)

                tr = oos_trades(s, data, p, bars, spec)
                if len(tr) < 10:
                    continue
                r = np.array([t.pnl_r for t in tr])
                # t de Student sur la moyenne : n grand, distribution non
                # normale mais bornée en bas (-1 R) -> approximation acceptable.
                t_stat = r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) \
                    if r.std(ddof=1) > 0 else 0.0
                free = np.array([x.pnl_r for x in
                                 oos_trades(s, data, p, bars, spec_free)])
                rl = sum(x.pnl_r for x in tr if x.side == Side.LONG)
                rs = sum(x.pnl_r for x in tr if x.side == Side.SHORT)

                tot += 1
                pos += r.mean() > 0
                lbl = "_".join(f"{k}{c[k]}" for k in keys)
                say(f"{lbl:<46} {len(r):>5} "
                    f"{100 * (r > 0).mean():>6.1f} {r.mean():>+8.3f} "
                    f"{t_stat:>+6.2f} {r.sum():>+8.1f} "
                    f"{free.mean() if len(free) else np.nan:>+8.3f} "
                    f"{rl:>+7.1f} {rs:>+7.1f}")

            say(f"\n  PLATEAU : {pos}/{tot} configurations à espérance OOS "
                f"positive (hasard pur : {tot / 2:.0f}/{tot})")

    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "oos_stats.txt")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\n-> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
