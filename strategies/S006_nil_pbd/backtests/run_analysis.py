"""
Diagnostics s06_nil_pbd — ablation du spread, contrôle long/short, profil de
trade confronté aux chiffres ANNONCÉS par la source.

R9 : l'exécution reste `core.backtest.engine.run`, le moteur commun. Ce script
ne simule rien lui-même ; il choisit les paramètres d'appel et agrège.

DEUX ÉCARTS ASSUMÉS PAR RAPPORT À `run_wf.py`, tous deux dans le même sens
--------------------------------------------------------------------------
1. `max_hold_bars = 288` (3 jours de M15). C'est la borne haute annoncée par la
   source (« four hours to three days », 14:23) et le walk-forward commun ne
   sait pas la passer au moteur. Sans elle, une position peut courir des mois.

2. Cette borne neutralise au passage un défaut du moteur commun : un niveau
   FRANCHI PAR UN GAP n'est jamais exécuté, parce que le test est
   `low <= niveau <= high` au lieu de `high >= cible` / `low <= stop`. Sur DAX
   (fermeture 22h-8h) une position peut alors ne jamais se clôturer et bloquer
   toutes les suivantes. Mesuré : 1 trade sur 255 valait +509 R à lui seul,
   soit 94 % du résultat du mode cassure. Voir research/VERDICT.md §7.
   Le défaut est SIGNALÉ, pas corrigé — `core/` est hors périmètre.

    python -m strategies.S006_nil_pbd.backtests.run_analysis
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

from core.backtest.engine import run as run_engine                # noqa: E402
from core.contracts.strategy import Side                          # noqa: E402
from core.data.instruments import get_spec                        # noqa: E402
from core.data.source import load_bars                            # noqa: E402
from strategies.S006_nil_pbd.backtests.run_wf import (              # noqa: E402
    GRIDS, REAL_SPREAD_PIPS, SYMBOLS,
)
from strategies.S006_nil_pbd.strategy import Strategy              # noqa: E402

MAX_HOLD = 288          # 3 jours de M15 — la borne haute de la source
L: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    L.append(s)


def cells(grid: dict) -> list[dict]:
    keys = sorted(grid)
    return [dict(zip(keys, c)) for c in itertools.product(*(grid[k] for k in keys))]


def max_loss_streak(trades) -> int:
    best = cur = 0
    for t in trades:
        cur = cur + 1 if t.pnl_r <= 0 else 0
        best = max(best, cur)
    return best


def main() -> int:
    for symbol in SYMBOLS:
        bars = load_bars(symbol, "M15")
        days = (bars.index[-1] - bars.index[0]).days
        spec_cat = get_spec(symbol)
        spec_real = dataclasses.replace(
            spec_cat, spread_pips=REAL_SPREAD_PIPS[symbol],
            max_spread_pips=REAL_SPREAD_PIPS[symbol] * 2)
        spec_free = dataclasses.replace(spec_cat, spread_pips=0.0)

        say("\n" + "=" * 96)
        say(f"{symbol} — {len(bars)} barres M15, {days} jours "
            f"({bars.index[0].date()} -> {bars.index[-1].date()})")
        say(f"spread catalogue {spec_cat.spread_pips:g} pips · "
            f"spread relevé dans les données {spec_real.spread_pips:g} pips")
        say("=" * 96)

        for mode, grid in GRIDS.items():
            say(f"\n--- mode {mode.upper()} — {len(cells(grid))} configurations, "
                f"plein échantillon, max_hold={MAX_HOLD} barres ---")
            say(f"{'configuration':<46} {'n':>5} {'WR%':>6} {'R/trade':>8} "
                f"{'R tot':>8} {'PF':>6} {'DD_R':>7} {'pertes':>7}")
            say("-" * 96)

            rows = []
            for c in cells(grid):
                p = dict(Strategy({"mode": mode}).params)
                p.update(c)
                p["_symbol"] = symbol
                s = Strategy({"mode": mode})
                data = s.precompute(bars, p)
                sig = s.generate_signals(data, p, len(bars))

                r = run_engine(sig, bars, spec_real, end_idx=len(bars),
                               max_hold_bars=MAX_HOLD)
                if r.n_trades == 0:
                    continue
                lbl = "_".join(f"{k}{c[k]}" for k in sorted(c))
                rows.append((lbl, c, r, sig, data, p))
                say(f"{lbl:<46} {r.n_trades:>5} {r.win_rate:>6.1f} "
                    f"{r.total_r / r.n_trades:>8.3f} {r.total_r:>+8.1f} "
                    f"{(r.profit_factor or 0):>6.2f} {r.max_drawdown_r:>7.1f} "
                    f"{max_loss_streak(r.trades):>7}")

            if not rows:
                continue

            # ── Ablation du spread (METHODOLOGY §5.1) ────────────────────
            say(f"\n  ABLATION DU SPREAD — mêmes signaux, coût nul vs réel")
            say(f"  {'configuration':<44} {'R/trade réel':>13} "
                f"{'R/trade gratuit':>16} {'péage':>9}")
            say("  " + "-" * 86)
            for lbl, c, r, sig, data, p in rows[:6]:
                rf = run_engine(sig, bars, spec_free, end_idx=len(bars),
                                max_hold_bars=MAX_HOLD)
                a = r.total_r / r.n_trades
                b = rf.total_r / rf.n_trades if rf.n_trades else float("nan")
                say(f"  {lbl:<44} {a:>+13.3f} {b:>+16.3f} {b - a:>+9.3f}")

            # ── Contrôle long/short (METHODOLOGY §5.2) ───────────────────
            say(f"\n  CONTRÔLE LONG / SHORT")
            say(f"  {'configuration':<40} {'n L':>5} {'R L':>9} {'WR L':>6} "
                f"{'n S':>5} {'R S':>9} {'WR S':>6}")
            say("  " + "-" * 86)
            for lbl, c, r, sig, data, p in rows[:6]:
                out = []
                for sd in (Side.LONG, Side.SHORT):
                    t = [x for x in r.trades if x.side == sd]
                    wr = 100 * sum(1 for x in t if x.is_win) / len(t) if t else float("nan")
                    out += [len(t), sum(x.pnl_r for x in t), wr]
                say(f"  {lbl:<40} {out[0]:>5} {out[1]:>+9.1f} {out[2]:>6.1f} "
                    f"{out[3]:>5} {out[4]:>+9.1f} {out[5]:>6.1f}")

            # ── Profil de trade vs chiffres annoncés ─────────────────────
            best = max(rows, key=lambda x: x[2].total_r)
            lbl, c, r, sig, data, p = best
            held = np.array([t.bars_held for t in r.trades])
            say(f"\n  PROFIL DE TRADE — meilleure config plein échantillon « {lbl} »")
            say(f"    fréquence            {r.n_trades / days:.2f} trades/jour "
                f"(annoncé : 3 à 5)")
            say(f"    win rate             {r.win_rate:.1f} % sur {r.n_trades} trades "
                f"(annoncé : 50-60 %)")
            say(f"    pertes consécutives  {max_loss_streak(r.trades)} "
                f"(annoncé : 10 à 20)")
            say(f"    durée de détention   médiane {np.median(held) * 15 / 60:.1f} h, "
                f"p90 {np.percentile(held, 90) * 15 / 60:.1f} h "
                f"(annoncé : 4 h à 3 jours)")
            say(f"    drawdown             {r.max_drawdown_r:.1f} R "
                f"= {r.max_drawdown_r:.0f} % du compte à 1 % de risque/trade "
                f"(annoncé : <10 %, max 20 %)")

            # ── Effet du filtre value area ───────────────────────────────
            say(f"\n  FILTRE VALUE AREA (profil hebdo sur TICK volume, pas volume réel)")
            say(f"  {'configuration hors va_filter':<42} {'n sans':>7} "
                f"{'R/tr sans':>10} {'n avec':>7} {'R/tr avec':>10} {'delta':>8}")
            say("  " + "-" * 88)
            byk = {lbl: (r,) for lbl, c, r, sig, data, p in rows}
            seen = set()
            for lbl, c, r, sig, data, p in rows:
                base = "_".join(f"{k}{c[k]}" for k in sorted(c) if k != "va_filter")
                if base in seen:
                    continue
                seen.add(base)
                pair = {}
                for lbl2, c2, r2, *_ in rows:
                    if "_".join(f"{k}{c2[k]}" for k in sorted(c2)
                                if k != "va_filter") == base:
                        pair[int(c2["va_filter"])] = r2
                if 0 in pair and 1 in pair:
                    a, b = pair[0], pair[1]
                    ra = a.total_r / a.n_trades
                    rb = b.total_r / b.n_trades if b.n_trades else float("nan")
                    say(f"  {base:<42} {a.n_trades:>7} {ra:>+10.3f} "
                        f"{b.n_trades:>7} {rb:>+10.3f} {rb - ra:>+8.3f}")

    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "diagnostics.txt")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\n-> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
