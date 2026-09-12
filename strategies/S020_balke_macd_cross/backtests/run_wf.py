"""
Mesure de S020 — MACD cross + filtre zéro (Balke). Walk-forward ancré + témoin.

    PYTHONIOENCODING=utf-8 python strategies/S020_balke_macd_cross/backtests/run_wf.py
    S020_SYMBOLS=NASDAQ,XAUUSD ... (sous-ensemble)

N'implémente aucun moteur (R9). Par instrument :
  0. coût de bord au spread CATALOGUE et au spread MESURÉ (colonne `spread` des
     barres), rapporté au risque médian — la géométrie en % de la vidéo peut être
     serrée ou large selon l'instrument, et c'est le coût qui le dit ;
  1. R1 causalité, R5 conformance sur données réelles ;
  2. plein échantillon, 18 cellules ;
  3. walk-forward ancré, cellules STRICT, multiplicité attendue ;
  4. bras témoin sur la meilleure cellule et sur la cellule par défaut de la vidéo ;
  5. les mêmes cellules rejouées au spread mesuré.

Mailles : D1 pour les indices (seule maille en cache tant que MT5 est hors ligne —
la démo de l'auteur est intraday, donc la conclusion « indices » reste OUVERTE),
H1 pour FX et or. Les critères sont dans research/FALSIFICATION.md, écrits avant.
"""
from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.backtest.anchored_wf import control_arm, run_walk_forward   # noqa: E402
from core.backtest.engine import InstrumentSpec, run as run_engine    # noqa: E402
from core.data.instruments import get_spec                            # noqa: E402
from core.data.source import load_bars                                # noqa: E402
from core.validation.causality import check as causality_check        # noqa: E402
from core.validation.conformance import check as conformance_check    # noqa: E402
from strategies.S020_balke_macd_cross.strategy import Strategy        # noqa: E402

TF = {"NASDAQ": "D1", "SP500": "D1", "DAX": "D1",
      "XAUUSD": "H1", "EURUSD": "H1", "GBPUSD": "H1", "USDJPY": "H1"}
SYMBOLS = [s for s in os.environ.get("S020_SYMBOLS", ",".join(TF)).split(",") if s]
MIN_TRADES, MAX_DD_R = 20, 12.0
SWITCHES = ("zero_filter", "sl_pct", "tp_pct")
BASE = {"side_mode": "both"}
ENGINE_KWARGS = dict(max_positions=1, cooldown_bars=2, cb_losses=3,
                     cb_cooldown_bars=24, max_hold_bars=None)
OUT = os.path.dirname(os.path.abspath(__file__))


def rule(c="=", n=100): print(c * n)
def section(t): print(); rule(); print(t); rule()


def head():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        return f"{sha}{' (arbre modifié)' if dirty else ''}"
    except Exception:
        return "inconnu"


def label(c):
    return f"{'Z' if c['zero_filter'] else '-'} sl{100*c['sl_pct']:.1f}% tp{100*c['tp_pct']:.0f}%"


def cells():
    g = Strategy().manifest().param_grid
    return [dict(zip(SWITCHES, combo)) for combo in itertools.product(*[g[k] for k in SWITCHES])]


def spec_with(spec: InstrumentSpec, spread_pips: float) -> InstrumentSpec:
    return InstrumentSpec(spec.symbol, pip=spec.pip, spread_pips=spread_pips,
                          max_spread_pips=max(spec.max_spread_pips, spread_pips * 10),
                          pip_value_per_lot=spec.pip_value_per_lot, slippage_pips=0.0)


def measured_spread_pips(bars: pd.DataFrame, spec: InstrumentSpec) -> float | None:
    """Colonne `spread` des barres MT5, en points de cotation → pips du catalogue.
    Médiane sur les 365 derniers jours (régime courant)."""
    if "spread" not in bars.columns:
        return None
    rec = bars.loc[bars.index >= bars.index[-1] - pd.Timedelta(days=365), "spread"]
    if rec.empty:
        return None
    # point de cotation = pip/10 pour FX 5 chiffres et or 3 chiffres ; = pip pour
    # les indices cotés au dixième. On lit le nombre de chiffres depuis le pip.
    point = spec.pip / 10.0 if spec.pip in (0.0001, 0.01) else spec.pip
    return float(rec.median() * point / spec.pip)


def backtest(cell, bars, spec, symbol):
    p = {**BASE, **cell}
    s = Strategy(p); s._symbol = symbol
    data = s.precompute(bars, p)
    sigs = s.generate_signals(data, p, len(bars))
    return sigs, run_engine(sigs, bars, spec, **ENGINE_KWARGS)


def stats(res):
    s = res.summary()
    s["r_per_trade"] = round(res.total_r / res.n_trades, 4) if res.n_trades else None
    return s


def by_year(res):
    agg, cnt = defaultdict(float), defaultdict(int)
    for t in res.trades:
        y = pd.Timestamp(t.entry_time).year
        agg[y] += t.pnl_r; cnt[y] += 1
    return {str(y): (round(agg[y], 1), cnt[y]) for y in sorted(agg)}


def measure(symbol: str, rep_all: dict) -> None:
    tf = TF[symbol]
    bars = load_bars(symbol, tf, days=365 * 5 + 30)
    if bars is None or len(bars) < 1000:
        print(f"\n{symbol} {tf} : barres indisponibles"); rep_all[symbol] = {"error": "barres"}; return
    spec_cat = get_spec(symbol)
    sp_meas = measured_spread_pips(bars, spec_cat)
    spec = spec_cat
    rep = {"symbol": symbol, "timeframe": tf, "bars": len(bars),
           "spread_catalogue": spec_cat.spread_pips, "spread_mesure": sp_meas}

    section(f"{symbol} {tf} — {len(bars)} barres · {bars.index[0].date()} → {bars.index[-1].date()}")

    # 0. coût de bord
    _, r0 = backtest(dict(zip(SWITCHES, [True, 0.02, 0.02])), bars, spec, symbol)
    risks = np.array([t.risk_distance / spec.pip for t in r0.trades]) if r0.trades else np.array([np.nan])
    med = float(np.nanmedian(risks))
    print(f"0. coût : spread catalogue {spec_cat.spread_pips:.1f} pips"
          f"{f' · mesuré {sp_meas:.1f} pips' if sp_meas else ' · mesuré indisponible'}"
          f" · risque médian (sl 2 %) {med:.0f} pips → coût "
          f"{100*spec_cat.spread_pips/med:.1f} % / "
          f"{(100*sp_meas/med) if sp_meas else float('nan'):.1f} % du R")
    rep["cost"] = {"median_risk_pips": round(med, 1),
                   "pct_catalogue": round(100 * spec_cat.spread_pips / med, 2) if med else None,
                   "pct_mesure": round(100 * sp_meas / med, 2) if (sp_meas and med) else None}

    # 1. R1 / R5
    ok = True
    for c in (dict(zip(SWITCHES, [True, 0.02, 0.02])), dict(zip(SWITCHES, [False, 0.005, 0.04]))):
        s = Strategy({**BASE, **c}); s._symbol = symbol
        r1 = causality_check(s, bars, symbol); ok &= r1.ok
        r5 = conformance_check(s, bars, symbol)
        print(f"1. {label(c):18s} R1 {'OK' if r1.ok else 'FUITE'} · R5 {'OK' if r5.ok else 'DIVERGENCE'}")
    rep["r1_ok"] = bool(ok)

    # 2. plein échantillon
    print(f"\n2. {'cellule':18s} {'n':>5s} {'R':>8s} {'R/tr':>7s} {'WR%':>6s} {'PF':>5s} {'DD':>6s}  années")
    rows = []
    for c in cells():
        _, res = backtest(c, bars, spec, symbol)
        st = stats(res)
        rows.append({"cell": c, "label": label(c), **st, "by_year": by_year(res)})
        print(f"   {label(c):18s} {st['n_trades']:5d} {st['total_r']:8.1f} {(st['r_per_trade'] or 0):7.3f} "
              f"{(st['win_rate'] or 0):6.1f} {(st['profit_factor'] or 0):5.2f} {st['max_dd_r']:6.1f}  "
              f"{' '.join(f'{y[2:]}:{v[0]:+.0f}' for y, v in rows[-1]['by_year'].items())}")
    rep["full_sample"] = rows

    # 3. walk-forward
    s = Strategy({**BASE, **cells()[0]}); s._symbol = symbol
    wf = run_walk_forward(s, bars, spec, param_grid=Strategy().manifest().param_grid,
                          min_trades=MIN_TRADES, max_dd_r=MAX_DD_R, verbose=False,
                          engine_kwargs=ENGINE_KWARGS)
    print("\n3. " + wf.render(top=6).replace("\n", "\n   "))
    print(f"   STRICT attendues par hasard sur {len(cells())} cellules à 5 % : ≈ {0.05*len(cells()):.1f} · observées : {len(wf.strict())}")
    rep["wf"] = {"strict": [{"label": r.label, "avg_oos": round(r.avg_oos, 3), "oos_trades": r.total_test_trades}
                            for r in wf.strict()], "n_configs": wf.n_configs}

    # 4. témoin + 5. spread mesuré
    elig = [r for r in rows if r["n_trades"] >= MIN_TRADES]
    picks = {"vidéo (Z 2%/2%)": rows[[r["label"] for r in rows].index(label(dict(zip(SWITCHES, [True, 0.02, 0.02]))))]}
    if elig:
        picks["meilleure R/tr"] = max(elig, key=lambda r: r["r_per_trade"] or -9)
    print("\n4-5. témoin et spread mesuré")
    rep["control"] = {}
    for name, r in picks.items():
        _, res = backtest(r["cell"], bars, spec, symbol)
        line = f"   {name:16s} {r['label']:18s} n={res.n_trades:4d} R={res.total_r:7.1f}"
        if res.n_trades >= MIN_TRADES:
            ca = control_arm(bars, spec, res.trades, res.total_r, engine_kwargs=ENGINE_KWARGS)
            pct = float((ca.draws_r < res.total_r).mean() * 100.0) if ca is not None else float("nan")
            line += f" · percentile témoin {pct:5.1f}"
        else:
            pct = None; line += " · effectif < 20, pas de témoin"
        if sp_meas:
            _, rm = backtest(r["cell"], bars, spec_with(spec, sp_meas), symbol)
            line += f" · au spread mesuré : R={rm.total_r:7.1f} ({(rm.total_r/rm.n_trades) if rm.n_trades else 0:+.3f}/tr)"
            rep["control"][name] = {"label": r["label"], "n": res.n_trades, "total_r": round(res.total_r, 2),
                                    "percentile": None if pct is None else round(pct, 1),
                                    "total_r_spread_mesure": round(rm.total_r, 2)}
        else:
            rep["control"][name] = {"label": r["label"], "n": res.n_trades, "total_r": round(res.total_r, 2),
                                    "percentile": None if pct is None else round(pct, 1)}
        print(line)
    rep_all[symbol] = rep


def main() -> int:
    rule(); print(f"S020 — MACD CROSS + FILTRE ZÉRO (Balke) · dépôt {head()}"); rule()
    print("18 cellules · walk-forward ancré 4 fenêtres · témoin aléatoire · critères : research/FALSIFICATION.md")
    rep_all: dict = {"commit": head(), "symbols": {}}
    for sym in SYMBOLS:
        try:
            measure(sym, rep_all["symbols"])
        except Exception as exc:                 # un instrument cassé ne cache pas les autres
            print(f"\n{sym} : ERREUR {type(exc).__name__}: {exc}")
            rep_all["symbols"][sym] = {"error": f"{type(exc).__name__}: {exc}"}
    p = os.path.join(OUT, "results.json")
    json.dump(rep_all, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
    print(f"\nrésultats : {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
