"""
s12 — Walk-forward ancré + bras témoin + diagnostics figés par le gel.

Grille FIGÉE dans research/FALSIFICATION.md (16 cellules). `engine_kwargs`
fidèles à la source (cooldown 0, pas de circuit breaker, pas de max_hold) —
transmis à run_walk_forward ET attach_control_arm.

Diagnostics ajoutés au rapport (tous sur la config PAR DÉFAUT, plein
échantillon, sauf mention) :
  * ablation du spread (F2) : mêmes signaux, spread nul vs réel
  * split juin 2022 (F4) : pré-release vs post-release, sa propre doctrine
  * cellule vendredi : R/trade avec vs sans (jamais le PnL total)
  * MAE : pire excursion adverse par trade, en R et en % du prix
  * durées de détention (validation de l'approximation cible statique)

Usage : python strategies/s12_prt_macd_meanrev/backtests/run_wf.py [SYMBOL...]
Sortie : backtests/anchored_wf_<sym>.txt
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward, attach_control_arm  # noqa: E402
from core.backtest.engine import run as run_engine                          # noqa: E402
from core.data.instruments import get_spec                                  # noqa: E402
from core.data.source import load_bars                                      # noqa: E402
from strategies.s12_prt_macd_meanrev.strategy import Strategy               # noqa: E402

HERE = os.path.dirname(__file__)
DAYS = 365 * 30
ENGINE_KWARGS = dict(cooldown_bars=0, cb_losses=999)      # fidélité source
RELEASE = pd.Timestamp("2022-06-21")   # release exacte (prorealalgos/10 @14:30)


def rpt(res) -> str:
    if not res.n_trades:
        return "0 trade"
    return (f"{res.n_trades:>4} trades, {res.total_r:>+8.2f} R total, "
            f"{res.total_r / res.n_trades:>+7.4f} R/trade, WR {res.win_rate:.1f} %")


def run_default(strat, bars, spec, params, end=None) -> "object":
    data = strat.precompute(bars, params)
    sigs = strat.generate_signals(data, params, len(bars) if end is None else end)
    return run_engine(sigs, bars, spec, end_idx=end, **ENGINE_KWARGS)


def mae_stats(trades, bars) -> str:
    """Pire excursion adverse par trade — lue dans les barres, PAS recalculée
    par une boucle de backtest (analyse d'un output moteur)."""
    lows = bars["low"]
    pos = {ts: i for i, ts in enumerate(bars.index)}
    maes_r, maes_pct = [], []
    for t in trades:
        i = pos.get(pd.Timestamp(t.entry_time))
        j = pos.get(pd.Timestamp(t.exit_time)) if t.exit_time is not None else None
        if i is None or j is None or j <= i:
            continue
        low_min = float(lows.iloc[i + 1:j + 1].min())
        adverse = max(0.0, t.entry_price - low_min)
        maes_r.append(adverse / t.risk_distance if t.risk_distance else np.nan)
        maes_pct.append(100.0 * adverse / t.entry_price)
    if not maes_r:
        return "  (aucun trade)"
    r = pd.Series(maes_r)
    p = pd.Series(maes_pct)
    return (f"  MAE ({len(r)} trades) : méd {r.median():.2f} R / {p.median():.2f} %, "
            f"p90 {r.quantile(.9):.2f} R / {p.quantile(.9):.2f} %, "
            f"max {r.max():.2f} R / {p.max():.2f} %")


def hold_stats(trades) -> str:
    if not trades:
        return "  (aucun trade)"
    h = pd.Series([t.bars_held for t in trades])
    er = pd.Series([t.exit_reason for t in trades]).value_counts()
    return (f"  détention : méd {h.median():.0f} j, p90 {h.quantile(.9):.0f} j, "
            f"max {h.max():.0f} j — sorties {dict(er)}")


def run_symbol(symbol: str) -> None:
    bars = load_bars(symbol, "D1", days=DAYS)
    spec = get_spec(symbol)
    strat = Strategy()
    dflt = dict(strat.manifest().default_params)
    print(f"=== {symbol} : {len(bars)} barres "
          f"({bars.index[0].date()} -> {bars.index[-1].date()}), "
          f"spread {spec.spread_pips * spec.pip} pts ===")

    # ── Walk-forward + témoin ────────────────────────────────────────────────
    report = run_walk_forward(strat, bars, spec, engine_kwargs=ENGINE_KWARGS)

    def is_default(r):
        return all(r.params.get(k) == v for k, v in dflt.items())

    chosen, seen = [], set()
    pool = ([r for r in report.results if is_default(r)]
            + report.strict()[:3] + report.tier1()[:3]
            + sorted(report.results, key=lambda r: -r.avg_oos)[:3])
    for r in pool:
        if id(r) not in seen:
            seen.add(id(r))
            chosen.append(r)
    attach_control_arm(report, bars, spec, configs=chosen,
                       engine_kwargs=ENGINE_KWARGS)

    txt = report.render(top=8)

    # ── Diagnostics config par défaut ───────────────────────────────────────
    L = ["", "=" * 96, f"DIAGNOSTICS — config par défaut {dflt}", "=" * 96]

    res_real = run_default(strat, bars, spec, dflt)
    spec0 = replace(spec, spread_pips=0.0, slippage_pips=0.0)
    res_zero = run_default(strat, bars, spec0, dflt)
    L.append("F2 — ablation du spread (plein échantillon) :")
    L.append(f"  spread réel : {rpt(res_real)}")
    L.append(f"  spread nul  : {rpt(res_zero)}")
    if res_zero.n_trades:
        peage = (res_zero.total_r - res_real.total_r) / max(res_real.n_trades, 1)
        L.append(f"  péage mesuré : {peage:+.4f} R/trade")

    L.append("")
    L.append(f"F4 — sa propre doctrine (split release {RELEASE.date()}, spread réel) :")
    pre = bars[bars.index < RELEASE]
    post = bars[bars.index >= RELEASE - pd.Timedelta(days=120)]  # warmup rejoué
    res_pre = run_default(Strategy(), pre, spec, dflt)
    res_post_all = run_default(Strategy(), post, spec, dflt)
    post_trades = [t for t in res_post_all.trades if pd.Timestamp(t.entry_time) >= RELEASE]
    from core.backtest.engine import BacktestResult
    res_post = BacktestResult(trades=post_trades)
    L.append(f"  pré-release  ({pre.index[0].date()} -> {RELEASE.date()}) : {rpt(res_pre)}")
    L.append(f"  post-release ({RELEASE.date()} -> {bars.index[-1].date()}) : {rpt(res_post)}")

    L.append("")
    L.append("Cellule vendredi (R/trade, jamais le total — plein échantillon, spread réel) :")
    fri = dict(dflt)
    fri["no_friday"] = True
    res_fri = run_default(Strategy(), bars, spec, fri)
    L.append(f"  vendredi autorisé : {rpt(res_real)}")
    L.append(f"  vendredi interdit : {rpt(res_fri)}")

    L.append("")
    L.append("Exposition « sans stop » (proxy 10 ATR) — config par défaut, spread réel :")
    L.append(mae_stats(res_real.trades, bars))
    L.append(hold_stats(res_real.trades))

    txt += "\n".join(L) + "\n"

    txt += "\n--- TÉMOIN PAR CONFIG (toutes les configs armées) ---\n"
    for r in chosen:
        if r.control is not None:
            txt += (f"  {r.label:<58} honest_r {r.honest_r:>+8.2f} "
                    f"({r.total_test_trades} trades OOS)\n      {r.control.line()}\n")

    out = os.path.join(HERE, f"anchored_wf_{symbol}.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write((txt + f"\n-> {out}\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["SP500", "NASDAQ", "DAX"]):
        run_symbol(s)
