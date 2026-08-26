"""
s90 « fade de l'échec » — validation complète (Phase 3).

    python strategies/s90_adrian_synthesis/research/run_validation.py

Protocole : research/HYPOTHESIS.md, FIGÉ avant exécution (commit f1e9d0c).
Phases :
  P0  économie a priori — drag par instrument à cible 1 ATR (seuil 25 % = F4 grid)
  P1  R1 invariant de troncature multi-instruments (complément du CLI --save)
  P2  walk-forward ancré 17 instruments × 6 cellules, coûts réels
      (spread catalogue + slippage 0,5 pip) + témoin NON conditionné (F1/F3a)
  P3  ablation : spread nul + slippage nul, mêmes signaux (F7)
  P4  synthèses : dose-réponse par seuil (F8), pool hors découverte (F2),
      long/short (F4), par instrument
  P5  stabilité multi-graines des cellules passantes (F5)
  P6  témoin CONDITIONNÉ à l'état d'excursion (F3b — réserve grid §5.7)

Aucun moteur maison (R9) : tout passe par core.backtest. Les tirages
conditionnés de P6 réutilisent les briques du bras témoin commun
(_reference_profile, _draw_entry_bars) et le moteur commun.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.backtest.anchored_wf import (  # noqa: E402
    _draw_entry_bars, _reference_profile, attach_control_arm, run_walk_forward,
)
from core.backtest.engine import BacktestResult, run as run_engine  # noqa: E402
from core.contracts.strategy import Side, Signal  # noqa: E402
from core.data.instruments import get_spec  # noqa: E402
from core.data.source import load_bars  # noqa: E402

from strategies.s90_adrian_synthesis.strategy import (  # noqa: E402
    ADX_GATE, ATR_PERIOD, SPACING_ATR, Strategy, SYMBOLS, WARMUP,
)

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

FROZEN_MAX_AGE_H = 24 * 365          # snapshot figé — pas de retéléchargement
SLIPPAGE_PIPS = 0.5
DRAG_DEAD = 25.0                     # % de la cible 1 ATR — mort sur papier
MIN_OOS_TRADES = 20

DISCOVERY = {"EURUSD", "XAUUSD", "DAX"}      # ensemble de découverte (étude grid)
PRIMARY = {"threshold_atr": 3, "sl_atr": 1.0, "tp_atr": 1.0}
SEEDS = [20260816, 20260817, 7, 424242, 990001]

EK = dict(max_positions=1, cooldown_bars=2, cb_losses=3,
          cb_cooldown_bars=24, max_hold_bars=None)

GRID = {"threshold_atr": [2, 3, 4], "sl_atr": [1.0, 2.0], "tp_atr": [1.0]}


def head() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "core"],
                                        cwd=ROOT, text=True).strip()
        return f"{sha}{' (core modifié localement)' if dirty else ''}"
    except Exception:
        return "inconnu"


def load(symbol: str) -> pd.DataFrame:
    df = load_bars(symbol, "H1", max_age_hours=FROZEN_MAX_AGE_H)
    if df is None or len(df) < 1000:
        raise RuntimeError(f"barres indisponibles pour {symbol}")
    return df


def atr_series(df: pd.DataFrame) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(ATR_PERIOD).mean()


def mean_ci(x) -> tuple[float, float, float, int]:
    a = np.asarray(list(x), dtype=float)
    if a.size == 0:
        return (float("nan"),) * 3 + (0,)
    m = float(a.mean())
    se = float(a.std(ddof=1) / np.sqrt(a.size)) if a.size > 1 else float("nan")
    return m, m - 1.96 * se, m + 1.96 * se, int(a.size)


def is_primary(p: dict) -> bool:
    return all(p[k] == v for k, v in PRIMARY.items())


class Tee:
    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")

    def write(self, s):
        sys.stdout.write(s)
        self.f.write(s)
        self.f.flush()

    def close(self):
        self.f.close()


# ═════════════════════════════════════════════════════════════════════════════
# P0 — économie a priori
# ═════════════════════════════════════════════════════════════════════════════

def phase0(bars: dict, specs: dict, log) -> dict:
    log.write("\n" + "=" * 100 + "\nP0 — ÉCONOMIE A PRIORI (cible 1 ATR)\n" + "=" * 100 + "\n")
    log.write(f"coût aller-retour = spread + 2 × {SLIPPAGE_PIPS} pip ; drag = coût / (1 ATR médiane) ; "
              f"mort sur papier si > {DRAG_DEAD:.0f} %\n\n")
    log.write(f"{'instrument':<10} {'ATR H1 méd (pips)':>18} {'coût (pips)':>12} {'drag %':>8}  statut\n")
    log.write("-" * 64 + "\n")
    viable = {}
    for sym in SYMBOLS:
        spec = specs[sym]
        atr_pips = float(atr_series(bars[sym]).median()) / spec.pip
        cost = spec.spread_pips + 2 * SLIPPAGE_PIPS
        drag = 100.0 * cost / atr_pips
        viable[sym] = drag <= DRAG_DEAD
        tag = "" if viable[sym] else "MORT-PAPIER (exclu du verdict de généralité)"
        log.write(f"{sym:<10} {atr_pips:>18.1f} {cost:>12.1f} {drag:>8.1f}  {tag}\n")
    log.write(f"\nInstruments viables : {sum(viable.values())}/{len(viable)} — "
              f"hors découverte viables : "
              f"{sorted(s for s in viable if viable[s] and s not in DISCOVERY)}\n")
    return viable


# ═════════════════════════════════════════════════════════════════════════════
# P1 — R1 invariant de troncature (complément multi-instruments)
# ═════════════════════════════════════════════════════════════════════════════

def phase1(bars: dict, log) -> bool:
    log.write("\n" + "=" * 100 + "\nP1 — R1 INVARIANT DE TRONCATURE (complément)\n" + "=" * 100 + "\n")
    ok_all = True
    for sym in ["USDCHF", "NASDAQ", "XAGUSD"]:
        df = bars[sym]
        for th in (2, 3, 4):
            strat = Strategy({"threshold_atr": th})
            full = strat.precompute(df, strat.params)
            for c in (0.60, 0.90):
                T = int(len(df) * c)
                s_full = strat.generate_signals(full, strat.params, T)
                trunc = strat.precompute(df.iloc[:T], strat.params)
                s_trunc = strat.generate_signals(trunc, strat.params, T)
                same = (len(s_full) == len(s_trunc)
                        and all(a.timestamp == b.timestamp and a.side == b.side
                                and abs(a.entry - b.entry) < 1e-9
                                and abs(a.stop - b.stop) < 1e-9
                                for a, b in zip(s_full, s_trunc)))
                ok_all &= same
                log.write(f"  {sym} t{th} T={T:>6} : {len(s_full):>4} vs {len(s_trunc):>4}"
                          f" -> {'OK' if same else '*** FUITE ***'}\n")
    log.write(f"\nR1 complément : {'PASSÉ' if ok_all else 'ÉCHEC — résultats NON publiables'}\n")
    return ok_all


# ═════════════════════════════════════════════════════════════════════════════
# P2/P3 — walk-forward + témoin non conditionné, puis ablation
# ═════════════════════════════════════════════════════════════════════════════

def run_wf(sym, bars_df, spec, log, with_control: bool):
    strat = Strategy()
    rep = run_walk_forward(strat, bars_df, spec, param_grid=GRID,
                           min_trades=MIN_OOS_TRADES, verbose=False,
                           engine_kwargs=EK)
    if with_control:
        candidates = [r for r in rep.results
                      if (r.honest_r > 0 or is_primary(r.params))
                      and r.total_test_trades >= MIN_OOS_TRADES]
        log.write(f"  {sym} : {len(candidates)} cellules au témoin non conditionné "
                  f"(candidates OOS > 0 et/ou primaire, ≥ {MIN_OOS_TRADES} tr)\n")
        if candidates:
            attach_control_arm(rep, bars_df, spec, configs=candidates,
                               verbose=False, engine_kwargs=EK)
    return rep


def cell_rows(rep):
    rows = []
    for r in rep.results:
        p = r.params
        oos_trades = [t for w in r.windows for t in w.test.trades]
        rows.append(dict(
            th=p["threshold_atr"], sl=p["sl_atr"],
            honest=r.honest_r, n_oos=r.total_test_trades,
            rpt=(r.honest_r / r.total_test_trades) if r.total_test_trades else float("nan"),
            pctile=(r.control.percentile if r.control is not None else None),
            eff_ok=(r.control.effectif_ok if r.control is not None else None),
            beta=(r.control.beta_directionnel if r.control is not None else None),
            oos_trades=oos_trades,
            cfg=r,
        ))
    return rows


def print_cells(sym, rows, viable, log):
    v = "" if viable.get(sym, True) else "   [MORT-PAPIER]"
    log.write(f"\n--- {sym} : 6 cellules (walk-forward ancré, OOS honnête, coûts réels){v} ---\n")
    log.write(f"    {'cellule':<12} {'OOS R':>8} {'n OOS':>6} {'R/t OOS':>9} {'témoin pct':>11} {'beta':>8}\n")
    log.write("    " + "-" * 60 + "\n")
    for r in sorted(rows, key=lambda x: (x["th"], x["sl"])):
        pct = f"{r['pctile']:.1f}" if r["pctile"] is not None else "—"
        if r["pctile"] is not None and r["eff_ok"] is False:
            pct += "*"
        beta = f"{r['beta']:+.3f}" if r["beta"] is not None else "—"
        star = " <= PRIMAIRE" if r["th"] == 3 and r["sl"] == 1.0 else ""
        log.write(f"    t{r['th']}_sl{r['sl']:<8} {r['honest']:>+8.2f} {r['n_oos']:>6} "
                  f"{r['rpt']:>+9.4f} {pct:>11} {beta:>8}{star}\n")
    log.write("    (* = effectif témoin écarté)\n")


# ═════════════════════════════════════════════════════════════════════════════
# P4 — synthèses F2 / F4 / F8
# ═════════════════════════════════════════════════════════════════════════════

def phase4(all_rows, free_rows, viable, log):
    log.write("\n" + "=" * 100 + "\nP4 — SYNTHÈSES (F2 généralité, F4 sens, F8 dose-réponse)\n" + "=" * 100 + "\n")

    def pool(rows_by_sym, syms, th, sl=None):
        return [t.pnl_r for s in syms for r in rows_by_sym[s]
                if r["th"] == th and (sl is None or r["sl"] == sl)
                for t in r["oos_trades"]]

    viable_syms = [s for s in SYMBOLS if viable[s]]
    nd_viable = [s for s in viable_syms if s not in DISCOVERY]
    disc = [s for s in SYMBOLS if s in DISCOVERY]

    log.write("\n--- F8 dose-réponse : R/t OOS réel poolé par seuil (instruments viables, sl 1.0) ---\n")
    log.write(f"    {'seuil':<8} {'R/t réel':>10} {'IC95':>22} {'n':>7} {'R/t coût nul':>13} {'n':>7}\n")
    log.write("    " + "-" * 72 + "\n")
    for th in (2, 3, 4):
        m, lo, hi, n = mean_ci(pool(all_rows, viable_syms, th, 1.0))
        mf, _, _, nf = mean_ci(pool(free_rows, viable_syms, th, 1.0))
        log.write(f"    t{th:<7} {m:>+10.4f} [{lo:>+8.4f};{hi:>+8.4f}] {n:>7} {mf:>+13.4f} {nf:>7}\n")
    log.write("    (même tableau, sl 2.0)\n")
    for th in (2, 3, 4):
        m, lo, hi, n = mean_ci(pool(all_rows, viable_syms, th, 2.0))
        mf, _, _, nf = mean_ci(pool(free_rows, viable_syms, th, 2.0))
        log.write(f"    t{th:<7} {m:>+10.4f} [{lo:>+8.4f};{hi:>+8.4f}] {n:>7} {mf:>+13.4f} {nf:>7}\n")

    log.write("\n--- F2 : cellule PRIMAIRE (t3_sl1.0), pools réels ---\n")
    for name, syms in [
        ("découverte (EURUSD/XAUUSD/DAX)", disc),
        ("HORS DÉCOUVERTE viables (le juge)", nd_viable),
        ("hors découverte tous", [s for s in SYMBOLS if s not in DISCOVERY]),
        ("univers viable entier", viable_syms),
    ]:
        m, lo, hi, n = mean_ci(pool(all_rows, syms, 3, 1.0))
        mf, _, _, nf = mean_ci(pool(free_rows, syms, 3, 1.0))
        log.write(f"    {name:<38} R/t {m:>+8.4f} [{lo:>+8.4f};{hi:>+8.4f}] n {n:>5}"
                  f"   (coût nul {mf:>+8.4f}, n {nf})\n")

    log.write("\n--- F4 : long/short, cellule primaire, pools réels ---\n")
    for name, syms in [("découverte", disc), ("hors découverte viables", nd_viable)]:
        trades = [t for s in syms for r in all_rows[s]
                  if r["th"] == 3 and r["sl"] == 1.0 for t in r["oos_trades"]]
        lo = [t.pnl_r for t in trades if t.side == Side.LONG]
        sh = [t.pnl_r for t in trades if t.side == Side.SHORT]
        ml = np.mean(lo) if lo else float("nan")
        ms = np.mean(sh) if sh else float("nan")
        log.write(f"    {name:<28} LONG {ml:>+8.4f} (n {len(lo):>4})   "
                  f"SHORT {ms:>+8.4f} (n {len(sh):>4})\n")

    log.write("\n--- par instrument : cellule primaire (réel) ---\n")
    log.write(f"    {'instrument':<10} {'R/t OOS':>9} {'n':>5} {'OOS R':>8} {'pct':>7} "
              f"{'coût nul R/t':>13}  groupe\n")
    log.write("    " + "-" * 70 + "\n")
    for s in SYMBOLS:
        r = next(x for x in all_rows[s] if x["th"] == 3 and x["sl"] == 1.0)
        rf = next(x for x in free_rows[s] if x["th"] == 3 and x["sl"] == 1.0)
        pct = f"{r['pctile']:.1f}" if r["pctile"] is not None else "—"
        if r["pctile"] is not None and r["eff_ok"] is False:
            pct += "*"
        grp = "DÉCOUVERTE" if s in DISCOVERY else ("hors-déc." if viable[s] else "mort-papier")
        log.write(f"    {s:<10} {r['rpt']:>+9.4f} {r['n_oos']:>5} {r['honest']:>+8.2f} {pct:>7} "
                  f"{rf['rpt']:>+13.4f}  {grp}\n")


# ═════════════════════════════════════════════════════════════════════════════
# P5 — stabilité multi-graines
# ═════════════════════════════════════════════════════════════════════════════

def phase5(passing, bars, specs, log):
    log.write("\n" + "=" * 100 + "\nP5 — STABILITÉ MULTI-GRAINES (F5) des cellules pct ≥ 95\n" + "=" * 100 + "\n")
    log.write(f"graines : {SEEDS} — 200 tirages chacune\n\n")
    results = {}
    for sym, row in passing:
        pcts = []
        for seed in SEEDS:
            cfg = row["cfg"]
            attach_control_arm(
                _report_stub(cfg), bars[sym], specs[sym],
                configs=[cfg], seed=seed, verbose=False, engine_kwargs=EK)
            pcts.append(cfg.control.percentile if cfg.control else float("nan"))
        n95 = sum(1 for p in pcts if p >= 95)
        results[(sym, cell_label(row))] = (pcts, n95)
        log.write(f"  {sym:<10} {cell_label(row):<10} pct par graine : "
                  f"{'  '.join(f'{p:5.1f}' for p in pcts)}  -> {n95}/5 ≥ 95 "
                  f"{'STABLE' if n95 >= 4 else 'ÉCARTÉE (F5)'}\n")
    return results


def _report_stub(cfg):
    from core.backtest.anchored_wf import WalkForwardReport
    return WalkForwardReport(strategy_id="s90", symbol="", bars=0, n_configs=1,
                             results=[cfg], elapsed_s=0.0,
                             min_trades=MIN_OOS_TRADES, max_dd_r=12.0)


def cell_label(row) -> str:
    return f"t{row['th']}_sl{row['sl']}"


# ═════════════════════════════════════════════════════════════════════════════
# P6 — témoin CONDITIONNÉ à l'état d'excursion (F3b)
# ═════════════════════════════════════════════════════════════════════════════

def excursion_state(df: pd.DataFrame, threshold: int) -> np.ndarray:
    """Masque booléen causal : tendance active, ADX > gate, excursion ≥ seuil ATR.

    Même logique d'ancre que la stratégie ; toutes les barres DANS l'état, pas
    seulement les franchissements de palier. C'est le témoin « plus dur » de la
    réserve grid §5.7 : entrer au hasard n'importe où dans l'état.
    """
    s = Strategy({"threshold_atr": threshold})
    data = s.precompute(df, s.params)
    high = data["high"].to_numpy()
    low = data["low"].to_numpy()
    close = data["close"].to_numpy()
    atr = data["atr"].to_numpy()
    trend = data["st_trend"].to_numpy()
    adx = data["adx"].to_numpy()
    n = len(df)
    mask = np.zeros(n, dtype=bool)
    prev_t = 0.0
    anchor = np.nan
    for i in range(WARMUP, n):
        t = trend[i]
        if not np.isfinite(t) or not np.isfinite(atr[i]) or atr[i] <= 0:
            continue
        if t != prev_t:
            prev_t = t
            anchor = high[i] if t > 0 else low[i]
            continue
        if t > 0:
            if high[i] > anchor:
                anchor = high[i]
            exc = anchor - close[i]
        else:
            if low[i] < anchor:
                anchor = low[i]
            exc = close[i] - anchor
        if exc >= threshold * SPACING_ATR * atr[i] and np.isfinite(adx[i]) and adx[i] > ADX_GATE:
            mask[i] = True
    return mask


def conditioned_control(sym, row, bars_df, spec, log, draws: int = 200):
    """F3b : tirages aléatoires restreints aux barres dans l'état, géométrie
    identique (profil permuté des trades OOS), mêmes engine_kwargs, agrégé sur
    les 4 fenêtres par indice de tirage — 5 graines."""
    cfg = row["cfg"]
    mask_full = excursion_state(bars_df, row["th"])
    atr_full = atr_series(bars_df).to_numpy()

    out_pcts, out_ec = [], []
    for seed in SEEDS:
        tot_r = np.zeros(draws)
        tot_n = np.zeros(draws, dtype=int)
        n_ref = covered = 0
        for w in cfg.windows:
            refs = w.test.trades
            if not refs:
                continue
            sl_bars = bars_df.iloc[w.train_end:w.test_end]
            atr_sl = atr_full[w.train_end:w.test_end]
            mask_sl = mask_full[w.train_end:w.test_end].copy()
            mask_sl[-1:] = False          # il faut une barre suivante pour exécuter
            allowed = np.flatnonzero(mask_sl & np.isfinite(atr_sl) & (atr_sl > 0))
            if len(allowed) < 5:
                continue
            profile = _reference_profile(
                refs, {ts: atr_sl[i] for i, ts in enumerate(sl_bars.index)})
            if profile is None:
                continue
            idx = sl_bars.index
            close = sl_bars["close"].to_numpy(dtype=float)
            rng = np.random.default_rng(seed * 10 + w.index)
            nprof = len(profile["sides"])
            for d in range(draws):
                bars_at = _draw_entry_bars(rng, allowed, nprof)
                if not len(bars_at):
                    continue
                sides = [profile["sides"][k] for k in rng.permutation(nprof)]
                pair = rng.permutation(nprof)
                slv = profile["sl_atr"][pair]
                tpv = profile["tp_atr"][pair]
                sigs = []
                for k, j in enumerate(np.sort(bars_at)):
                    a = float(atr_sl[j])
                    entry = float(close[j])
                    long = sides[k] == Side.LONG
                    dist = float(slv[k]) * a
                    if dist <= 0:
                        continue
                    stop = entry - dist if long else entry + dist
                    if stop == entry:
                        continue
                    target = None
                    if np.isfinite(tpv[k]):
                        td = float(tpv[k]) * a
                        target = entry + td if long else entry - td
                    sigs.append(Signal(timestamp=idx[j], symbol=spec.symbol,
                                       side=Side.LONG if long else Side.SHORT,
                                       entry=entry, stop=stop, target=target,
                                       reason="témoin conditionné à l'état d'excursion"))
                res = run_engine(sigs, sl_bars, spec, **EK) if sigs else BacktestResult()
                tot_r[d] += res.total_r
                tot_n[d] += res.n_trades
            n_ref += nprof
            covered += 1
        if not covered or not n_ref:
            log.write(f"  {sym:<10} {cell_label(row):<10} graine {seed} : témoin conditionné IMPOSSIBLE "
                      f"(pas assez de barres dans l'état)\n")
            continue
        strat_r = cfg.honest_r
        pct = float(100.0 * (np.sum(tot_r < strat_r) + 0.5 * np.sum(tot_r == strat_r)) / draws)
        with np.errstate(invalid="ignore", divide="ignore"):
            ec = float(np.nanmean(np.where(tot_n > 0, tot_r / tot_n, np.nan)))
        med_n = float(np.median(tot_n))
        eff = "OK" if abs(med_n - n_ref) <= 0.15 * n_ref else "EFFECTIF ÉCARTÉ"
        out_pcts.append(pct)
        out_ec.append(ec)
        log.write(f"  {sym:<10} {cell_label(row):<10} graine {seed} : pct {pct:5.1f}  "
                  f"E_c {ec:+.4f} R/t  (méd. {med_n:.0f}/{n_ref} tr, {eff})\n")
    return out_pcts, out_ec


# ═════════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    log = Tee(os.path.join(OUT, "run_validation.txt"))
    log.write(f"s90 VALIDATION — commit {head()} — {time.strftime('%Y-%m-%d %H:%M')}\n")
    log.write("Protocole : research/HYPOTHESIS.md (figé, commit f1e9d0c). Moteur commun R9.\n")
    log.write(f"Coûts réels : spread catalogue + slippage {SLIPPAGE_PIPS} pip. EK={EK}\n")

    bars = {s: load(s) for s in SYMBOLS}
    specs = {}
    for s in SYMBOLS:
        sp = get_spec(s)
        sp.slippage_pips = SLIPPAGE_PIPS
        specs[s] = sp
    for s in SYMBOLS:
        log.write(f"  {s:<8} {len(bars[s]):>6} barres H1  {bars[s].index[0]} -> {bars[s].index[-1]}\n")

    viable = phase0(bars, specs, log)
    if not phase1(bars, log):
        log.write("ARRÊT : R1 en échec.\n")
        return

    log.write("\n" + "=" * 100 + "\nP2 — WALK-FORWARD ANCRÉ (réel) + TÉMOIN NON CONDITIONNÉ\n" + "=" * 100 + "\n")
    all_rows = {}
    for sym in SYMBOLS:
        t1 = time.time()
        rep = run_wf(sym, bars[sym], specs[sym], log, with_control=True)
        all_rows[sym] = cell_rows(rep)
        print_cells(sym, all_rows[sym], viable, log)
        with open(os.path.join(OUT, f"wf_{sym}.txt"), "w", encoding="utf-8") as f:
            f.write(rep.render(top=6))
        log.write(f"  [{sym} terminé en {time.time()-t1:.0f}s]\n")

    log.write("\n" + "=" * 100 + "\nP3 — ABLATION : spread nul + slippage nul (F7)\n" + "=" * 100 + "\n")
    free_rows = {}
    for sym in SYMBOLS:
        free_spec = dataclasses.replace(specs[sym], spread_pips=0.0, slippage_pips=0.0)
        rep = run_wf(sym, bars[sym], free_spec, log, with_control=False)
        free_rows[sym] = cell_rows(rep)
        log.write(f"  {sym:<8} cellules OOS > 0 à coût nul : "
                  f"{sum(1 for r in free_rows[sym] if r['honest'] > 0)}/6 "
                  f"(réel : {sum(1 for r in all_rows[sym] if r['honest'] > 0)}/6)\n")

    phase4(all_rows, free_rows, viable, log)

    # Cellules passant F1 (pct >= 95, effectif témoin OK, >= 20 tr OOS)
    passing = [(sym, r) for sym in SYMBOLS for r in all_rows[sym]
               if r["pctile"] is not None and r["pctile"] >= 95
               and r["eff_ok"] and r["n_oos"] >= MIN_OOS_TRADES]
    log.write(f"\nCellules F1 (pct ≥ 95, eff OK, ≥ {MIN_OOS_TRADES} tr OOS) : {len(passing)}\n")
    for sym, r in passing:
        log.write(f"  {sym:<10} {cell_label(r):<10} OOS {r['honest']:>+7.2f} R "
                  f"({r['n_oos']} tr, R/t {r['rpt']:+.4f})  pct {r['pctile']:.1f}\n")

    seed_res = phase5(passing, bars, specs, log)

    log.write("\n" + "=" * 100 + "\nP6 — TÉMOIN CONDITIONNÉ À L'ÉTAT D'EXCURSION (F3b)\n" + "=" * 100 + "\n")
    log.write("Tirages restreints aux barres dans l'état (tendance, ADX > 20, excursion ≥ seuil ATR),\n"
              "géométrie identique (profil OOS permuté), mêmes engine_kwargs, 200 tirages × 5 graines.\n"
              "Lecture (HYPOTHESIS §3 mapping) : pct ≥ 95 = le palier ajoute ; pct < 95 avec E_c > 0 =\n"
              "l'état est l'edge (réserve levée) ; pct < 95 et E_c ≤ 0 = artefact, au plus NON CONCLUSIF.\n\n")
    # cible : cellule primaire des instruments de découverte + toute cellule F1-passante
    targets, seen = [], set()
    for sym in sorted(DISCOVERY):
        r = next(x for x in all_rows[sym] if x["th"] == 3 and x["sl"] == 1.0)
        targets.append((sym, r))
        seen.add((sym, cell_label(r)))
    for sym, r in passing:
        if (sym, cell_label(r)) not in seen:
            targets.append((sym, r))
            seen.add((sym, cell_label(r)))
    cond = {}
    for sym, r in targets:
        pcts, ecs = conditioned_control(sym, r, bars[sym], specs[sym], log)
        if pcts:
            cond[(sym, cell_label(r))] = (pcts, ecs)
            log.write(f"  => {sym} {cell_label(r)} : pct méd {np.median(pcts):5.1f}, "
                      f"E_c méd {np.median(ecs):+.4f} R/t\n\n")

    log.write(f"\nDurée totale : {(time.time()-t0)/60:.1f} min\n")
    log.close()


if __name__ == "__main__":
    main()
