"""
s12 — Addendum 2026-08-16 : règles EXACTES (source indépendante prorealalgos/10)

Corrections de FIDÉLITÉ reçues APRÈS le gel et APRÈS les premiers runs (déclaré
dans FALSIFICATION.md §Addendum) :
  * condition supplémentaire : close < close[1]   (« close weaker than yesterday »)
  * release exacte : 2022-06-21
  * leur MACD est peut-être le « S-MACD » normalisé prix -> proxy MACD/close

3 variantes, config par défaut sinon (range 20, q 0.2, vendredi ok, stop 10 ATR) :
  A0  grille gelée (référence, déjà mesurée)
  A1  A0 + close_down          <- la règle fidèle
  A2  A1 + macd_rel (proxy S-MACD)

Pour chacune : WF ancré + témoin (SP500), plein échantillon spread réel/nul,
split 2022-06-21. Usage : python .../run_addendum.py   Sortie : addendum.txt
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward, attach_control_arm  # noqa: E402
from core.backtest.engine import BacktestResult, run as run_engine          # noqa: E402
from core.data.instruments import get_spec                                  # noqa: E402
from core.data.source import load_bars                                      # noqa: E402
from strategies.s12_prt_macd_meanrev.strategy import Strategy               # noqa: E402

HERE = os.path.dirname(__file__)
ENGINE_KWARGS = dict(cooldown_bars=0, cb_losses=999)
RELEASE = pd.Timestamp("2022-06-21")

VARIANTS = {
    "A0_gel": {},
    "A1_close_down": {"close_down": True},
    "A2_smacd_proxy": {"close_down": True, "macd_rel": True},
}


def rpt(res) -> str:
    if not res.n_trades:
        return "0 trade"
    return (f"{res.n_trades:>4} trades, {res.total_r:>+8.2f} R, "
            f"{res.total_r / res.n_trades:>+7.4f} R/trade, WR {res.win_rate:.1f} %")


def full_run(bars, spec, params, strat=None):
    s = strat or Strategy()
    data = s.precompute(bars, params)
    return run_engine(s.generate_signals(data, params, len(bars)), bars, spec,
                      **ENGINE_KWARGS)


def main() -> None:
    L: list[str] = []
    for symbol in ["SP500", "NASDAQ", "DAX"]:
        bars = load_bars(symbol, "D1", days=365 * 30)
        spec = get_spec(symbol)
        spec0 = replace(spec, spread_pips=0.0)
        L.append("=" * 96)
        L.append(f"ADDENDUM règles exactes — {symbol} ({len(bars)} barres, "
                 f"release {RELEASE.date()})")
        L.append("=" * 96)

        for name, over in VARIANTS.items():
            params = dict(Strategy().manifest().default_params)
            params.update(over)
            res = full_run(bars, spec, params)
            res0 = full_run(bars, spec0, params)
            pre = bars[bars.index < RELEASE]
            post = bars[bars.index >= RELEASE - pd.Timedelta(days=120)]
            r_pre = full_run(pre, spec, params)
            r_post_all = full_run(post, spec, params)
            r_post = BacktestResult(trades=[
                t for t in r_post_all.trades
                if pd.Timestamp(t.entry_time) >= RELEASE])
            L.append(f"[{name}] {over or 'défauts gelés'}")
            L.append(f"  plein échantillon (réel) : {rpt(res)}")
            L.append(f"  plein échantillon (nul)  : {rpt(res0)}")
            L.append(f"  pré-release  : {rpt(r_pre)}")
            L.append(f"  post-release : {rpt(r_post)}")

            if symbol == "SP500" and name != "A0_gel":
                strat = Strategy()
                report = run_walk_forward(strat, bars, spec,
                                          param_grid={k: [v] for k, v in params.items()},
                                          engine_kwargs=ENGINE_KWARGS)
                attach_control_arm(report, bars, spec, configs=report.results,
                                   engine_kwargs=ENGINE_KWARGS, verbose=False)
                r = report.results[0]
                oos = " ".join(f"{v:+.2f}" for v in r.oos_series)
                L.append(f"  WF OOS [{oos}] honest_r {r.honest_r:+.2f} "
                         f"({r.total_test_trades} trades OOS)")
                if r.control is not None:
                    L.append(f"  {r.control.line()}")
            L.append("")

    txt = "\n".join(L)
    out = os.path.join(HERE, "addendum.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write((txt + f"\n-> {out}\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
