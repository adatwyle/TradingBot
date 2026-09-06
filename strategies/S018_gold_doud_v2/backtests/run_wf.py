"""
Mesure de S018 — or v2 (méthode Doud). Walk-forward ancré + contrastes.

    python strategies/S018_gold_doud_v2/backtests/run_wf.py

N'implémente AUCUN moteur (R9) : tout passe par `core.backtest.anchored_wf`,
`core.backtest.engine` et `core.validation.*`. Le script orchestre et imprime.

Ce qu'il produit, et pourquoi :

  1. EMPREINTE — commit + fenêtre de données. Sans ça un chiffre n'est pas
     reproductible.
  2. R1 sur données réelles, sur plusieurs points de la grille (pas seulement
     le défaut) — le mode `equilibrium` porte un balayage à état, c'est là que
     se logerait une fuite.
  3. R5 conformance backtest/live.
  4. LA CELLULE NEUTRE CONTRE LA V1 — égalité signal par signal, rejouée ici
     pour que la preuve soit dans le fichier archivé, pas seulement dans les
     tests.
  5. WALK-FORWARD ANCRÉ sur les 32 cellules, avec le nombre de réussites
     attendues par pur hasard en regard.
  6. CONTRASTE PAR COMMUTATEUR — effet marginal de chaque ingrédient Doud,
     moyenné sur les 16 cellules où il est actif contre les 16 où il ne l'est
     pas. C'est la lecture qui répond à la question posée : qu'ajoute-t-elle ?
  7. PLEIN ÉCHANTILLON + par année pour les cellules notables — la v1 avait
     62 % de son résultat sur 2025, il faut savoir si la v2 hérite du défaut.
  8. BRAS TÉMOIN aléatoire sur la cellule neutre et sur la meilleure.
  9. SWEEP SECONDAIRE max_hold_bars (D10) — déclaré comme secondaire, hors
     grille principale, pour ne pas gonfler la multiplicité.
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
from core.backtest.engine import run as run_engine                    # noqa: E402
from core.data.instruments import get_spec                            # noqa: E402
from core.data.source import load_bars                                # noqa: E402
from core.validation.causality import check as causality_check        # noqa: E402
from core.validation.conformance import check as conformance_check    # noqa: E402
from strategies.S011_legacy_breakout.strategy import Strategy as V1   # noqa: E402
from strategies.S018_gold_doud_v2.strategy import Strategy            # noqa: E402

SYMBOL = "XAUUSD"
# Le timeframe est un ARGUMENT, pas une constante : la source scalpe en intraday
# et le dossier H1 s'est conclu sur un manque d'effectif. Descendre d'un cran est
# donc une mesure, pas un réglage — et le coût de bord, lui, ne descend pas avec
# l'amplitude des barres. C'est ce que le § 0 chiffre avant tout le reste.
TIMEFRAME = os.environ.get("S018_TF", "H1")
MIN_TRADES = 20
MAX_DD_R = 12.0

# Exécution : exactement celle du forward scellé de la v1
# (studies/gold_forward/params.json → "engine"), pour que les deux versions
# soient comparables trade pour trade.
ENGINE_KWARGS = dict(max_positions=1, cooldown_bars=2, cb_losses=3,
                     cb_cooldown_bars=24, max_hold_bars=None)

SWITCHES = ("entry_mode", "channel_source", "side_mode", "session_filter", "htf_bias")
NEUTRAL = {"entry_mode": "breakout", "channel_source": "extremes",
           "side_mode": "both", "session_filter": "off", "htf_bias": "off"}
BASE = {"donchian": 40, "adx_min": 20.0, "tp_m": 4.0, "sl_m": 1.5,
        "atr_vol_ratio": 0.8, "adx_rising_lookback": 5,
        "rsi_long_max": 75.0, "rsi_short_min": 25.0}

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def _out(name: str) -> str:
    """H1 garde les noms canoniques (dossier de référence) ; tout autre timeframe
    écrit à côté, sans jamais écraser la mesure de référence."""
    if TIMEFRAME != "H1":
        stem, ext = os.path.splitext(name)
        name = f"{stem}_{TIMEFRAME}{ext}"
    return os.path.join(OUT_DIR, name)


def rule(c="=", n=96):
    print(c * n)


def section(title):
    print()
    rule()
    print(title)
    rule()


def head() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"],
                                        cwd=ROOT, text=True).strip()
        return f"{sha}{' (arbre modifié)' if dirty else ''}"
    except Exception:
        return "inconnu"


def label(cell: dict) -> str:
    short = {"breakout": "brk", "equilibrium": "EQU", "extremes": "ext",
             "bodies": "BOD", "both": "both", "long_only": "LONG",
             "off": "-", "doud": "SESS", "daily_ema": "BIAS"}
    return " ".join(short[cell[k]] for k in SWITCHES)


def cells() -> list[dict]:
    grid = Strategy().manifest().param_grid
    return [dict(zip(SWITCHES, combo))
            for combo in itertools.product(*[grid[k] for k in SWITCHES])]


def backtest(cell: dict, bars, spec, engine_kwargs=None):
    params = {**BASE, **cell}
    strat = Strategy(params)
    strat._symbol = SYMBOL
    sigs = strat.generate_signals(strat.precompute(bars, params), params, len(bars))
    res = run_engine(sigs, bars, spec, **(engine_kwargs or ENGINE_KWARGS))
    return sigs, res


def stats(res) -> dict:
    s = res.summary()
    s["r_per_trade"] = round(res.total_r / res.n_trades, 4) if res.n_trades else None
    longs = [t for t in res.trades if t.side.value == "LONG"]
    shorts = [t for t in res.trades if t.side.value == "SHORT"]
    s["n_long"], s["n_short"] = len(longs), len(shorts)
    s["r_long"] = round(sum(t.pnl_r for t in longs) / len(longs), 4) if longs else None
    s["r_short"] = round(sum(t.pnl_r for t in shorts) / len(shorts), 4) if shorts else None
    return s


def by_year(res) -> dict:
    agg = defaultdict(float)
    cnt = defaultdict(int)
    for t in res.trades:
        y = pd.Timestamp(t.entry_time).year
        agg[y] += t.pnl_r
        cnt[y] += 1
    return {str(y): (round(agg[y], 1), cnt[y]) for y in sorted(agg)}


def main() -> int:
    bars = load_bars(SYMBOL, TIMEFRAME)
    if bars is None or len(bars) < 5000:
        print("barres XAUUSD indisponibles — mesure impossible")
        return 2
    spec = get_spec(SYMBOL)
    report: dict = {"symbol": SYMBOL, "timeframe": TIMEFRAME, "commit": head(),
                    "bars": len(bars),
                    "from": str(bars.index[0]), "to": str(bars.index[-1])}

    rule()
    print(f"S018 — OR v2 (méthode Doud) · {SYMBOL} {TIMEFRAME}")
    rule()
    print(f"dépôt {report['commit']} · {len(bars)} barres · "
          f"{bars.index[0]} → {bars.index[-1]}")
    print(f"spread {spec.spread_pips:.0f} pips · slippage {spec.slippage_pips:.1f} pip "
          f"· moteur {ENGINE_KWARGS}")
    print("Slippage à 0 : comme la v1 et son témoin. Les chiffres restent "
          "comparables au dossier gold_forward, et optimistes d'un montant inconnu.")

    # ── 0. Ce que coûte le timeframe ────────────────────────────────────────
    section("0. COÛT DE BORD — ce que le spread pèse à ce timeframe")
    from strategies.S011_legacy_breakout.strategy import _atr as _atr_v1
    atr = _atr_v1(bars["high"].to_numpy(float), bars["low"].to_numpy(float),
                  bars["close"].to_numpy(float))
    atr_med = float(np.nanmedian(atr)) / spec.pip
    risk_med = 1.5 * atr_med                      # sl_m = 1,5 ATR
    cost = spec.spread_pips + 2.0 * spec.slippage_pips   # payé aux deux extrémités
    print(f"ATR14 médian : {atr_med:.0f} pips · risque médian (1,5 ATR) : "
          f"{risk_med:.0f} pips")
    print(f"coût aller-retour : {cost:.0f} pips = {100 * cost / risk_med:.1f} % du R")
    print("Ce pourcentage se soustrait de l'espérance par trade, quel que soit le "
          "signal. Il ne baisse pas quand on descend de timeframe — l'amplitude, si.")
    report["edge_cost"] = {"atr_median_pips": round(atr_med, 1),
                           "risk_median_pips": round(risk_med, 1),
                           "cost_pips": cost,
                           "cost_pct_of_r": round(100 * cost / risk_med, 2)}

    # ── 1. La cellule neutre EST la v1 ──────────────────────────────────────
    section("1. CELLULE NEUTRE vs V1 (S011, paramètres scellés du forward)")
    if TIMEFRAME != "H1":
        print(f"ATTENTION — timeframe {TIMEFRAME}. La v1 scellée est en H1 : ce qui "
              f"est comparé ici est S011 APPLIQUÉE À DES BARRES {TIMEFRAME}, pas la "
              f"référence du forward. L'égalité ci-dessous prouve l'équivalence des "
              f"deux CODES, elle ne rattache pas ces chiffres au dossier gold_forward.")
    v1 = V1({**BASE, "er_min": 0.0, "fr_max": 1.0})
    v1._symbol = SYMBOL
    s_v1 = v1.generate_signals(v1.precompute(bars, v1.params), v1.params, len(bars))
    s_v2, res_neutral = backtest(NEUTRAL, bars, spec)
    k = lambda s: (pd.Timestamp(s.timestamp), s.side, s.entry, s.stop, s.target)
    identical = [k(s) for s in s_v1] == [k(s) for s in s_v2]
    print(f"v1 : {len(s_v1)} signaux · v2 neutre : {len(s_v2)} signaux · "
          f"identiques : {'OUI' if identical else 'NON — LECTURE INVALIDE'}")
    report["neutral_equals_v1"] = identical
    if not identical:
        print("La grille n'est pas lisible tant que cette ligne dit NON.")
        return 1
    res_v1 = run_engine(s_v1, bars, spec, **ENGINE_KWARGS)
    print(f"témoin v1 plein échantillon : {stats(res_v1)}")
    report["v1_full_sample"] = stats(res_v1)
    report["v1_by_year"] = by_year(res_v1)

    # ── 2. R1 causalité sur données réelles ─────────────────────────────────
    section("2. R1 — invariant de causalité (données réelles)")
    probe = [NEUTRAL,
             {**NEUTRAL, "entry_mode": "equilibrium"},
             {**NEUTRAL, "entry_mode": "equilibrium", "htf_bias": "daily_ema"},
             {**NEUTRAL, "channel_source": "bodies", "session_filter": "doud"},
             {**NEUTRAL, "entry_mode": "equilibrium", "channel_source": "bodies",
              "side_mode": "long_only", "session_filter": "doud",
              "htf_bias": "daily_ema"}]
    causality_lines, all_ok = [], True
    for cell in probe:
        strat = Strategy({**BASE, **cell})
        strat._symbol = SYMBOL
        rep = causality_check(strat, bars, SYMBOL)
        all_ok &= rep.ok
        line = (f"{label(cell):28s} {'OK ' if rep.ok else 'FUITE'} "
                f"couche indicateur : {'oui' if rep.indicator_layer_covered else 'non'}")
        print(line)
        causality_lines.append(rep.render())
    report["causality_ok"] = bool(all_ok)
    with open(_out("causality.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(causality_lines))

    # ── 3. R5 conformance ───────────────────────────────────────────────────
    section("3. R5 — conformance backtest / live")
    conf_lines = []
    for cell in (NEUTRAL, {**NEUTRAL, "entry_mode": "equilibrium"}):
        strat = Strategy({**BASE, **cell})
        strat._symbol = SYMBOL
        rep = conformance_check(strat, bars, SYMBOL)
        print(f"{label(cell):28s} {'OK' if rep.ok else 'DIVERGENCE'}")
        conf_lines.append(rep.render())
    with open(_out("conformance.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(conf_lines))

    # ── 4. Plein échantillon, 32 cellules ───────────────────────────────────
    section("4. PLEIN ÉCHANTILLON — 32 cellules "
            "(à lire avec le nombre de trades, jamais sans)")
    print(f"{'cellule':30s} {'n':>5s} {'R':>8s} {'R/tr':>8s} {'WR%':>6s} "
          f"{'PF':>6s} {'DD':>7s} {'nL':>5s} {'nS':>5s}")
    rows = []
    for cell in cells():
        _, res = backtest(cell, bars, spec)
        st = stats(res)
        rows.append({"cell": cell, "label": label(cell), **st,
                     "by_year": by_year(res)})
        print(f"{label(cell):30s} {st['n_trades']:5d} {st['total_r']:8.1f} "
              f"{(st['r_per_trade'] or 0):8.3f} {(st['win_rate'] or 0):6.1f} "
              f"{(st['profit_factor'] or 0):6.2f} {st['max_dd_r']:7.1f} "
              f"{st['n_long']:5d} {st['n_short']:5d}")
    report["full_sample"] = rows

    # ── 5. Contraste par commutateur ────────────────────────────────────────
    section("5. EFFET MARGINAL DE CHAQUE INGRÉDIENT (16 cellules ON vs 16 OFF)")
    print("Moyenne du R/trade sur les cellules où l'ingrédient est actif, contre "
          "celles où il ne l'est pas.\nUn ingrédient qui n'améliore pas en moyenne "
          "n'est pas sauvé par une cellule isolée : 32 cellules produisent ≈ 1,6 "
          "réussite par hasard.")
    print(f"\n{'ingrédient':16s} {'OFF R/tr':>10s} {'ON R/tr':>10s} {'Δ':>8s} "
          f"{'n OFF':>7s} {'n ON':>7s}")
    marginal = {}
    for sw in SWITCHES:
        grid = Strategy().manifest().param_grid[sw]
        off_v, on_v = grid[0], grid[1]
        off = [r for r in rows if r["cell"][sw] == off_v and r["n_trades"] >= MIN_TRADES]
        on = [r for r in rows if r["cell"][sw] == on_v and r["n_trades"] >= MIN_TRADES]
        f_off = float(np.mean([r["r_per_trade"] for r in off])) if off else float("nan")
        f_on = float(np.mean([r["r_per_trade"] for r in on])) if on else float("nan")
        n_off = int(np.sum([r["n_trades"] for r in off]))
        n_on = int(np.sum([r["n_trades"] for r in on]))
        marginal[sw] = {"off": round(f_off, 4), "on": round(f_on, 4),
                        "delta": round(f_on - f_off, 4),
                        "trades_off": n_off, "trades_on": n_on,
                        "cells_off": len(off), "cells_on": len(on)}
        print(f"{sw:16s} {f_off:10.3f} {f_on:10.3f} {f_on - f_off:8.3f} "
              f"{n_off:7d} {n_on:7d}")
    report["marginal"] = marginal

    # ── 6. Walk-forward ancré ───────────────────────────────────────────────
    section("6. WALK-FORWARD ANCRÉ — hors échantillon")
    strat = Strategy(BASE | NEUTRAL)
    strat._symbol = SYMBOL
    wf = run_walk_forward(strat, bars, spec, param_grid=Strategy().manifest().param_grid,
                          min_trades=MIN_TRADES, max_dd_r=MAX_DD_R,
                          verbose=False, engine_kwargs=ENGINE_KWARGS)
    print(wf.render(top=10))
    report["wf"] = {
        "n_configs": wf.n_configs,
        "strict": [{"label": r.label, "params": r.params, "avg_oos": round(r.avg_oos, 3),
                    "oos_trades": r.total_test_trades} for r in wf.strict()],
        "tier1": [{"label": r.label, "params": r.params, "avg_oos": round(r.avg_oos, 3),
                   "oos_trades": r.total_test_trades} for r in wf.tier1()[:10]],
    }
    print(f"\nRéussites STRICT attendues par pur hasard sur 32 cellules à 5 % : ≈ 1,6")
    print(f"Observées : {len(wf.strict())}")

    # ── 7. Par année, cellules notables ─────────────────────────────────────
    section("7. STABILITÉ ANNUELLE — la v1 tenait 62 % de son résultat sur 2025")
    notable = {"v1 / neutre": rows[[r["label"] for r in rows].index(label(NEUTRAL))]}
    eligible = [r for r in rows if r["n_trades"] >= MIN_TRADES]
    if eligible:
        best = max(eligible, key=lambda r: r["r_per_trade"] or -9)
        notable["meilleure R/trade"] = best
        best_tot = max(eligible, key=lambda r: r["total_r"])
        notable["meilleur R total"] = best_tot
    for name, r in notable.items():
        years = r["by_year"]
        tot = sum(v[0] for v in years.values())
        share = {y: (round(100 * v[0] / tot, 0) if tot else 0) for y, v in years.items()}
        print(f"\n{name} — {r['label']} · {r['n_trades']} trades · R {r['total_r']}")
        print("   " + " | ".join(f"{y} {v[0]:+.1f} ({v[1]} tr)" for y, v in years.items()))
        print("   part du R total : " + " | ".join(f"{y} {s:.0f}%" for y, s in share.items()))
    report["notable"] = {k: {"label": v["label"], "n_trades": v["n_trades"],
                             "total_r": v["total_r"], "by_year": v["by_year"]}
                         for k, v in notable.items()}

    # ── 8. Bras témoin aléatoire ────────────────────────────────────────────
    section("8. BRAS TÉMOIN — entrée aléatoire, même dispositif de risque")
    for name, r in notable.items():
        _, res = backtest(r["cell"], bars, spec)
        if res.n_trades < MIN_TRADES:
            print(f"{name}: {res.n_trades} trades — pas de témoin sans effectif")
            continue
        ca = control_arm(bars, spec, res.trades, res.total_r,
                         engine_kwargs=ENGINE_KWARGS)
        if ca is None:
            print(f"{name}: gabarit témoin impossible")
            continue
        pct = float((ca.draws_r < res.total_r).mean() * 100.0)
        print(f"{name:20s} {r['label']:30s} R {res.total_r:7.1f} "
              f"· percentile vs témoin : {pct:5.1f}")
        report.setdefault("control", {})[name] = {"label": r["label"],
                                                  "total_r": round(res.total_r, 2),
                                                  "percentile": round(pct, 1)}

    # ── 9. Sweep secondaire max_hold_bars (D10) ─────────────────────────────
    section("9. SECONDAIRE — sortie au temps (D10, « ne pas laisser tester son stop »)")
    print("Hors grille principale : sweep exploratoire sur les cellules notables.")
    report["max_hold"] = {}
    for name, r in notable.items():
        line = [f"{name:20s} {r['label']:30s}"]
        for mh in (None, 24, 48):
            _, res = backtest(r["cell"], bars, spec,
                              {**ENGINE_KWARGS, "max_hold_bars": mh})
            rpt = res.total_r / res.n_trades if res.n_trades else 0.0
            line.append(f"mh={str(mh):>4s}: {res.n_trades:4d} tr {res.total_r:7.1f} R "
                        f"({rpt:+.3f}/tr)")
            report["max_hold"].setdefault(name, {})[str(mh)] = {
                "n": res.n_trades, "total_r": round(res.total_r, 2),
                "r_per_trade": round(rpt, 4)}
        print("  " + "  ".join(line))

    with open(_out("results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nrésultats : {os.path.join(OUT_DIR, 'results.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
