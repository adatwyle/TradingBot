"""
Mesure de S019 — balayage de liquidité. Walk-forward ancré + bras témoin.

    python strategies/S019_gold_sweep/backtests/run_wf.py            (M15)
    S019_TF=M5 python strategies/S019_gold_sweep/backtests/run_wf.py

N'implémente AUCUN moteur (R9). Ce que le script impose, dans l'ordre :

  0. LE COÛT AVANT TOUT. Cette stratégie place un stop structurel, donc court.
     Le spread réel de XAUUSD est de 52 pips (TCK-018) quand le catalogue en
     déclare 25. Si le risque médian d'un trade est de 200 pips, le coût pèse
     26 % du R. Ce rapport est imprimé AVANT le moindre résultat, et toute la
     mesure est jouée à spread réel.
  1. R1 causalité et R5 conformance sur données réelles.
  2. Grille de 16 cellules, plein échantillon et walk-forward ancré.
  3. Bras témoin aléatoire — la seule référence qui vaille.
  4. Profil des trades : profondeur de balayage, risque, part de stops
     structurels contre stops planchonnés.
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
from core.data.source import load_bars                                # noqa: E402
from core.validation.causality import check as causality_check        # noqa: E402
from core.validation.conformance import check as conformance_check    # noqa: E402
from strategies.S019_gold_sweep.strategy import Strategy              # noqa: E402

SYMBOL = "XAUUSD"
TIMEFRAME = os.environ.get("S019_TF", "M15")
MIN_TRADES = 20
MAX_DD_R = 12.0
PIP = 0.01
SPREAD_REEL = 52.0            # médiane mesurée sur nos barres (TCK-018)
SPREAD_CATALOGUE = 25.0       # valeur héritée, conservée pour comparaison
SWITCHES = ("min_stop_atr", "tp_r", "htf_bias", "session_filter")
BASE = {"sweep_lookback": 60, "sweep_window": 5, "stop_buffer_atr": 0.10,
        "side_mode": "both", "htf_ema_days": 20, "cooldown_bars": 3}
ENGINE_KWARGS = dict(max_positions=1, cooldown_bars=2, cb_losses=3,
                     cb_cooldown_bars=24, max_hold_bars=None)
OUT = os.path.dirname(os.path.abspath(__file__))


def _out(name):
    if TIMEFRAME != "M15":
        stem, ext = os.path.splitext(name)
        name = f"{stem}_{TIMEFRAME}{ext}"
    return os.path.join(OUT, name)


def rule(c="=", n=96): print(c * n)
def section(t): print(); rule(); print(t); rule()


def head():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"],
                                        cwd=ROOT, text=True).strip()
        return f"{sha}{' (arbre modifié)' if dirty else ''}"
    except Exception:
        return "inconnu"


def label(c):
    short = {"off": "-", "doud": "SESS", "daily_ema": "BIAS"}
    return (f"stop{c['min_stop_atr']:.1f} tp{c['tp_r']:.0f} "
            f"{short[c['htf_bias']]:>4s} {short[c['session_filter']]:>4s}")


def cells():
    g = Strategy().manifest().param_grid
    return [dict(zip(SWITCHES, combo))
            for combo in itertools.product(*[g[k] for k in SWITCHES])]


def spec_for(spread_pips):
    return InstrumentSpec(SYMBOL, pip=PIP, spread_pips=spread_pips,
                          max_spread_pips=500.0, pip_value_per_lot=1.0,
                          slippage_pips=0.0)


def backtest(cell, bars, spec):
    p = {**BASE, **cell}
    s = Strategy(p); s._symbol = SYMBOL
    data = s.precompute(bars, p)
    sigs = s.generate_signals(data, p, len(bars))
    return sigs, run_engine(sigs, bars, spec, **ENGINE_KWARGS)


def stats(res):
    s = res.summary()
    s["r_per_trade"] = round(res.total_r / res.n_trades, 4) if res.n_trades else None
    L = [t for t in res.trades if t.side.value == "LONG"]
    S = [t for t in res.trades if t.side.value == "SHORT"]
    s["n_long"], s["n_short"] = len(L), len(S)
    return s


def by_year(res):
    agg, cnt = defaultdict(float), defaultdict(int)
    for t in res.trades:
        y = pd.Timestamp(t.entry_time).year
        agg[y] += t.pnl_r; cnt[y] += 1
    return {str(y): (round(agg[y], 1), cnt[y]) for y in sorted(agg)}


def main() -> int:
    bars = load_bars(SYMBOL, TIMEFRAME, days=365 * 5 + 30)
    if bars is None or len(bars) < 5000:
        print("barres indisponibles"); return 2
    spec = spec_for(SPREAD_REEL)
    rep = {"symbol": SYMBOL, "timeframe": TIMEFRAME, "commit": head(),
           "bars": len(bars), "spread_pips": SPREAD_REEL}

    rule(); print(f"S019 — BALAYAGE DE LIQUIDITÉ · {SYMBOL} {TIMEFRAME}"); rule()
    print(f"dépôt {rep['commit']} · {len(bars)} barres · {bars.index[0]} → {bars.index[-1]}")
    print(f"spread {SPREAD_REEL:.0f} pips (mesuré, TCK-018 — le catalogue en déclare "
          f"{SPREAD_CATALOGUE:.0f}) · slippage 0")

    # ── 0. Le coût avant tout ────────────────────────────────────────────────
    section("0. COÛT DE BORD RAPPORTÉ AU RISQUE — le piège propre à cette stratégie")
    _, res0 = backtest(dict(zip(SWITCHES, [0.5, 2.0, "off", "off"])), bars, spec)
    risks = np.array([t.risk_distance / PIP for t in res0.trades]) if res0.trades else np.array([0.0])
    med_risk = float(np.median(risks)) if len(risks) else float("nan")
    print(f"risque médian d'un trade : {med_risk:.0f} pips  (stop structurel, plancher 0,5 ATR)")
    print(f"coût aller-retour        : {SPREAD_REEL:.0f} pips = "
          f"{100 * SPREAD_REEL / med_risk:.1f} % du R" if med_risk == med_risk and med_risk > 0 else "")
    print("Un stop court est un stop cher. C'est ce rapport, et non le signal, qui")
    print("décide si une entrée intraday peut survivre à nos frais.")
    rep["cost"] = {"median_risk_pips": round(med_risk, 1),
                   "cost_pct_of_r": round(100 * SPREAD_REEL / med_risk, 2) if med_risk else None}

    # ── 1. R1 / R5 ───────────────────────────────────────────────────────────
    section("1. R1 CAUSALITÉ et R5 CONFORMANCE (données réelles)")
    probes = [dict(zip(SWITCHES, v)) for v in
              [[0.5, 2.0, "off", "off"], [1.0, 4.0, "daily_ema", "doud"],
               [0.5, 4.0, "daily_ema", "off"]]]
    caus, ok = [], True
    for c in probes:
        s = Strategy({**BASE, **c}); s._symbol = SYMBOL
        r = causality_check(s, bars, SYMBOL)
        ok &= r.ok
        print(f"  R1 {label(c):28s} {'OK' if r.ok else 'FUITE'} "
              f"· couche indicateur : {'oui' if r.indicator_layer_covered else 'non'}")
        caus.append(r.render())
    open(_out("causality.txt"), "w", encoding="utf-8").write("\n\n".join(caus))
    conf = []
    for c in probes[:2]:
        s = Strategy({**BASE, **c}); s._symbol = SYMBOL
        r = conformance_check(s, bars, SYMBOL)
        print(f"  R5 {label(c):28s} {'OK' if r.ok else 'DIVERGENCE'}")
        conf.append(r.render())
    open(_out("conformance.txt"), "w", encoding="utf-8").write("\n\n".join(conf))
    rep["r1_ok"] = bool(ok)

    # ── 2. Plein échantillon ─────────────────────────────────────────────────
    section("2. PLEIN ÉCHANTILLON — 16 cellules (à lire avec le nombre de trades)")
    print(f"{'cellule':26s} {'n':>5s} {'R':>8s} {'R/tr':>8s} {'WR%':>6s} {'PF':>6s} "
          f"{'DD':>7s} {'risq.méd':>9s} {'%struct':>8s}")
    rows = []
    for c in cells():
        sigs, res = backtest(c, bars, spec)
        st = stats(res)
        rk = [t.risk_distance / PIP for t in res.trades]
        struct = [s.meta.get("stop_structurel") for s in sigs]
        pct_struct = 100 * sum(1 for x in struct if x) / len(struct) if struct else 0
        rows.append({"cell": c, "label": label(c), **st,
                     "median_risk_pips": round(float(np.median(rk)), 1) if rk else None,
                     "pct_stop_structurel": round(pct_struct, 1),
                     "by_year": by_year(res)})
        print(f"{label(c):26s} {st['n_trades']:5d} {st['total_r']:8.1f} "
              f"{(st['r_per_trade'] or 0):8.3f} {(st['win_rate'] or 0):6.1f} "
              f"{(st['profit_factor'] or 0):6.2f} {st['max_dd_r']:7.1f} "
              f"{(np.median(rk) if rk else 0):9.0f} {pct_struct:7.0f}%")
    rep["full_sample"] = rows

    # ── 3. Walk-forward ──────────────────────────────────────────────────────
    section("3. WALK-FORWARD ANCRÉ — hors échantillon")
    s = Strategy({**BASE, **cells()[0]}); s._symbol = SYMBOL
    wf = run_walk_forward(s, bars, spec, param_grid=Strategy().manifest().param_grid,
                          min_trades=MIN_TRADES, max_dd_r=MAX_DD_R, verbose=False,
                          engine_kwargs=ENGINE_KWARGS)
    print(wf.render(top=8))
    print("\nRéussites STRICT attendues par pur hasard sur 16 cellules à 5 % : ≈ 0,8")
    print(f"Observées : {len(wf.strict())}")
    rep["wf"] = {"strict": [{"label": r.label, "avg_oos": round(r.avg_oos, 3),
                             "oos_trades": r.total_test_trades} for r in wf.strict()],
                 "n_configs": wf.n_configs}

    # ── 4. Bras témoin ───────────────────────────────────────────────────────
    section("4. BRAS TÉMOIN — entrée aléatoire, même dispositif de risque")
    eligible = [r for r in rows if r["n_trades"] >= MIN_TRADES]
    notable = {}
    if eligible:
        notable["meilleure R/trade"] = max(eligible, key=lambda r: r["r_per_trade"] or -9)
        notable["meilleur R total"] = max(eligible, key=lambda r: r["total_r"])
    notable["défaut"] = rows[[r["label"] for r in rows].index(label(cells()[0]))]
    for name, r in notable.items():
        _, res = backtest(r["cell"], bars, spec)
        if res.n_trades < MIN_TRADES:
            print(f"{name:20s} {r['label']:26s} {res.n_trades} trades — pas de témoin"); continue
        ca = control_arm(bars, spec, res.trades, res.total_r, engine_kwargs=ENGINE_KWARGS)
        if ca is None:
            print(f"{name:20s} gabarit témoin impossible"); continue
        pct = float((ca.draws_r < res.total_r).mean() * 100.0)
        print(f"{name:20s} {r['label']:26s} n={res.n_trades:4d} R {res.total_r:8.1f} "
              f"· percentile vs témoin {pct:5.1f}")
        rep.setdefault("control", {})[name] = {"label": r["label"],
                                               "n": res.n_trades,
                                               "total_r": round(res.total_r, 2),
                                               "percentile": round(pct, 1)}

    # ── 5. Ce que le spread coûte, chiffré ───────────────────────────────────
    section("5. SENSIBILITÉ AU SPREAD — catalogue contre réel")
    for name, r in notable.items():
        line = f"{name:20s} {r['label']:26s}"
        for sp in (SPREAD_CATALOGUE, SPREAD_REEL):
            _, res = backtest(r["cell"], bars, spec_for(sp))
            rpt = res.total_r / res.n_trades if res.n_trades else 0.0
            line += f"  {sp:.0f}p: {res.total_r:7.1f} R ({rpt:+.3f}/tr)"
        print(line)
    print("\nL'écart entre les deux colonnes est ce que le catalogue nous cachait.")

    json.dump(rep, open(_out("results.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False, default=str)
    print(f"\nrésultats : {_out('results.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
