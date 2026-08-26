"""
s09 — diagnostics post walk-forward (moteur commun R9, aucun moteur maison) :

  1. F4  ablation du spread : réel vs spread nul, toute la grille + split
         train/test (0-60 % / 60-100 %) pour les configs clefs
  2. F2  contrôle long/short (USDJPY et tous instruments, config défaut)
  3. F3  permutation horaire à instrument constant (3-6h vs 9-12h décalé de
         +6h intégralement, spread nul) — post-hoc, hors manifest, déclaré
  4. F5  conformité inverse GBPUSD : SA config, pré-live (-> 2024-03-31) vs
         post-live (2024-04-01 ->), en R et en € à 500 €/trade de risque
  5.     stabilité annuelle (config défaut USDJPY)
  6.     1 vs 2 breakouts en R/TRADE (son ablation du transcript 04, jugée
         comme le projet l'exige : au R/trade, pas au PnL total)

Sortie : backtests/diagnostics.txt
"""
from __future__ import annotations

import dataclasses
import io
import os
import pickle
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.engine import InstrumentSpec, run as run_engine   # noqa: E402
from core.data.instruments import get_spec                           # noqa: E402
from core.data.source import CACHE_DIR                               # noqa: E402
from strategies.S009_balke_rangebreakout.strategy import Strategy     # noqa: E402
from strategies.S009_balke_rangebreakout.backtests.run_wf import (    # noqa: E402
    GRIDS, load_bars, spec_for)

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "diagnostics.txt")


def grid_cells(pg: dict) -> list[dict]:
    import itertools
    keys = sorted(pg)
    return [dict(zip(keys, c)) for c in itertools.product(*(pg[k] for k in keys))]


def run_cell(strat, bars, spec, params, ek, end_idx=None):
    data = strat.precompute(bars, params)
    sigs = strat.generate_signals(data, params, len(bars))
    return run_engine(sigs, bars, spec, end_idx=end_idx, **ek), sigs


def split_oos(res, cut_ts):
    tr = [t for t in res.trades if t.entry_time <= cut_ts]
    te = [t for t in res.trades if t.entry_time > cut_ts]
    return tr, te


def rpt(trades):
    if not trades:
        return 0.0, 0
    return float(np.sum([t.pnl_r for t in trades])) / len(trades), len(trades)


def main():
    buf = io.StringIO()
    W = buf.write
    W("s09 — diagnostics (ablation, long/short, permutation, F5, stabilité)\n")
    W("=" * 78 + "\n")

    strat = Strategy()
    defaults = dict(strat.manifest().default_params)

    # ═════ 1. F4 — ablation du spread, toute la grille ══════════════════════
    W("\n### 1. F4 — ABLATION DU SPREAD (plein échantillon, R/trade)\n")
    summary = {}
    for sym, cfg in GRIDS.items():
        bars = load_bars(sym)
        spec = spec_for(sym, bars)
        spec0 = dataclasses.replace(spec, spread_pips=0.0)
        ek = cfg["engine_kwargs"]
        cut_ts = bars.index[int(len(bars) * 0.60) - 1]
        W(f"\n--- {sym} (spread {spec.spread_pips} pips) ---\n")
        W(f"    {'config':<58} {'réel':>8} {'nul':>8} {'péage':>8} {'n':>6}\n")
        rows = []
        for cell in grid_cells(cfg["param_grid"]):
            p = dict(defaults); p.update(cell)
            res_r, sigs = run_cell(strat, bars, spec, p, ek)
            res_0 = run_engine(sigs, bars, spec0, **ek)
            rr, n = rpt(res_r.trades)
            r0, _ = rpt(res_0.trades)
            lbl = "_".join(f"{k}{v}" for k, v in sorted(cell.items()))
            W(f"    {lbl:<58} {rr:>+8.4f} {r0:>+8.4f} {r0-rr:>8.4f} {n:>6}\n")
            rows.append((rr, r0, n))
            # split train/test pour la cellule par défaut de chaque instrument
            if all(p[k] == defaults[k] for k in
                   ("range_end_hour", "sl_mode", "breakouts", "range_filter_pct")) \
                    or (sym == "GBPUSD" and cell["range_end_hour"] == 12):
                _, te_r = split_oos(res_r, cut_ts)
                _, te_0 = split_oos(res_0, cut_ts)
                trr, tn = rpt(te_r)
                tr0, _ = rpt(te_0)
                W(f"      -> tranche test 60-100%% : réel {trr:+.4f} | nul {tr0:+.4f} "
                  f"| péage {tr0-trr:.4f} ({tn} trades)\n")
        arr = np.array(rows)
        pos_r = int((arr[:, 0] > 0).sum()); pos_0 = int((arr[:, 1] > 0).sum())
        W(f"    agrégat : réel moy {arr[:,0].mean():+.4f} ({pos_r}/{len(arr)} cellules >0) "
          f"| nul moy {arr[:,1].mean():+.4f} ({pos_0}/{len(arr)} >0) "
          f"| péage moy {(arr[:,1]-arr[:,0]).mean():.4f}\n")
        summary[sym] = arr

    # ═════ 2. F2 — contrôle long/short (config défaut par instrument) ═══════
    W("\n### 2. F2 — CONTRÔLE LONG/SHORT (config défaut, plein échantillon, réel)\n")
    W(f"    {'sym':<8} {'L R/t':>9} {'nL':>5} {'S R/t':>9} {'nS':>5} "
      f"{'L total':>9} {'S total':>9}\n")
    for sym, cfg in GRIDS.items():
        bars = load_bars(sym)
        spec = spec_for(sym, bars)
        p = dict(defaults)
        if sym == "GBPUSD":
            p.update(range_start_hour=4, range_end_hour=12)
        res, _ = run_cell(strat, bars, spec, p, cfg["engine_kwargs"])
        L = [t for t in res.trades if t.side.value == "LONG"]
        S = [t for t in res.trades if t.side.value == "SHORT"]
        lr, ln = rpt(L); sr, sn = rpt(S)
        W(f"    {sym:<8} {lr:>+9.4f} {ln:>5} {sr:>+9.4f} {sn:>5} "
          f"{lr*ln:>+9.2f} {sr*sn:>+9.2f}\n")

    # ═════ 3. F3 — permutation horaire à instrument constant (spread nul) ═══
    W("\n### 3. F3 — PERMUTATION HORAIRE (USDJPY, spread nul, géométrie figée)\n")
    W("    Contrat identique décalé en bloc : range 9-12h, entrées 12-23h,\n")
    W("    même max_hold_bars. Post-hoc, hors manifest — ne promeut rien.\n")
    bars = load_bars("USDJPY")
    spec0 = dataclasses.replace(get_spec("USDJPY"), spread_pips=0.0)
    ek = GRIDS["USDJPY"]["engine_kwargs"]
    cut_ts = bars.index[int(len(bars) * 0.60) - 1]
    variants = {
        "H09  3-6h, entrées 6-17h (défaut)": dict(defaults),
        "ctrl 9-12h, entrées 12-23h": dict(defaults, range_start_hour=9,
                                           range_end_hour=12, last_entry_hour=23),
        "ctrl 12-15h, entrées 15-2h(+j)": dict(defaults, range_start_hour=12,
                                               range_end_hour=15, last_entry_hour=23),
    }
    W(f"    {'variante':<38} {'full R/t':>9} {'train':>9} {'test':>9} {'n':>6}\n")
    for name, p in variants.items():
        res, _ = run_cell(strat, bars, spec0, p, ek)
        fr, n = rpt(res.trades)
        tr, te = split_oos(res, cut_ts)
        trr, _ = rpt(tr); ter, tn = rpt(te)
        W(f"    {name:<38} {fr:>+9.4f} {trr:>+9.4f} {ter:>+9.4f} {n:>6}\n")

    # même chose à spread réel pour information
    spec_r = get_spec("USDJPY")
    W("    (à spread réel :)\n")
    for name, p in variants.items():
        res, _ = run_cell(strat, bars, spec_r, p, ek)
        fr, n = rpt(res.trades)
        _, te = split_oos(res, cut_ts)
        ter, tn = rpt(te)
        W(f"    {name:<38} {fr:>+9.4f} {'':>9} {ter:>+9.4f} {n:>6}\n")

    # ═════ 4. F5 — GBPUSD pré/post live ═════════════════════════════════════
    W("\n### 4. F5 — CONFORMITÉ INVERSE GBPUSD (sa config exacte : 4-11:30≈4-12h,\n")
    W("    SL=range, 1 breakout, sans filtre, clôture 18h ; live fin mars 2024)\n")
    bars = load_bars("GBPUSD")
    spec = spec_for("GBPUSD", bars)
    ekg = GRIDS["GBPUSD"]["engine_kwargs"]
    p = dict(defaults, range_start_hour=4, range_end_hour=12)
    res, sigs = run_cell(strat, bars, spec, p, ekg)
    live_cut = pd.Timestamp("2024-03-31 23:59")
    pre = [t for t in res.trades if t.entry_time <= live_cut]
    post = [t for t in res.trades if t.entry_time > live_cut]
    for lbl, tr in (("pré-live  (2021-07 -> 2024-03)", pre),
                    ("post-live (2024-04 -> 2026-08)", post)):
        r, n = rpt(tr)
        tot = r * n
        W(f"    {lbl} : {n} trades, {tot:+.2f} R ({r:+.4f} R/trade) "
          f"= {tot*500:+,.0f} EUR à 500 EUR/trade\n")
    W("    référence live déclarée : -8 778 EUR sur ~360 trades (~-17,6 R)\n")
    # par année post-live
    yr = pd.Series([t.pnl_r for t in res.trades],
                   index=pd.DatetimeIndex([t.entry_time for t in res.trades]))
    W("    par année (toute la période) :\n")
    for y, g in yr.groupby(yr.index.year):
        W(f"      {y} : {g.sum():>+7.2f} R sur {len(g):>4} trades\n")

    # ═════ 5. stabilité annuelle USDJPY (config défaut, réel) ═══════════════
    W("\n### 5. STABILITÉ ANNUELLE — USDJPY config défaut (réel)\n")
    bars = load_bars("USDJPY")
    res, _ = run_cell(strat, bars, get_spec("USDJPY"), dict(defaults),
                      GRIDS["USDJPY"]["engine_kwargs"])
    yr = pd.Series([t.pnl_r for t in res.trades],
                   index=pd.DatetimeIndex([t.entry_time for t in res.trades]))
    for y, g in yr.groupby(yr.index.year):
        W(f"      {y} : {g.sum():>+7.2f} R sur {len(g):>4} trades "
          f"({g.mean():+.4f} R/trade)\n")
    W(f"      TOTAL : {yr.sum():+.2f} R sur {len(yr)} trades ({yr.mean():+.4f})\n")

    # ═════ 6. 1 vs 2 breakouts au R/trade (son ablation `04`) ═══════════════
    W("\n### 6. 1 vs 2 BREAKOUTS — au R/TRADE (USDJPY 3-6h SL=range, réel)\n")
    for nb in (1, 2):
        p = dict(defaults, breakouts=nb)
        res, _ = run_cell(strat, bars, get_spec("USDJPY"), p,
                          GRIDS["USDJPY"]["engine_kwargs"])
        r, n = rpt(res.trades)
        # décomposer : trades #1 vs #2 via reason
        first = [t for t in res.trades if "#1" in t.reason]
        second = [t for t in res.trades if "#2" in t.reason]
        r1, n1 = rpt(first); r2, n2 = rpt(second)
        W(f"    breakouts={nb} : total {r*n:+.2f} R / {n} trades ({r:+.4f} R/t) "
          f"| #1 : {r1:+.4f} x{n1} | #2 : {r2:+.4f} x{n2}\n")

    txt = buf.getvalue()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write(txt.encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
