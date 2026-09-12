"""
Mesure de S022 — ATR Candle Breakout (Balke), or H1. Walk-forward ancré + témoin.

    PYTHONIOENCODING=utf-8 python strategies/S022_balke_atr_candle/backtests/run_wf.py

N'implémente aucun moteur (R9). Sur XAUUSD H1, 6 ans :
  0. coût de bord au spread CATALOGUE et au spread MESURÉ (colonne `spread` des
     barres), rapporté au risque médian — un stop à 0,5 % sur l'or et un spread
     réellement coté à ~90 pips ne sont pas du même ordre, et c'est le coût qui le dit ;
  1. R1 causalité, R5 conformance sur données réelles ;
  2. plein échantillon, 12 cellules, R et effectif par année ;
  3. walk-forward ancré (4 fenêtres), cellules STRICT, multiplicité attendue ;
  4. bras témoin aléatoire sur la cellule par défaut, la meilleure et chaque STRICT ;
  5. les mêmes cellules rejouées au spread mesuré ;
  F. FIDÉLITÉ : fréquence, taux de réussite, motifs de sortie et R/trade de la cellule
     par défaut (= ses réglages live) face à ses chiffres publiés — 1 552 trades sur
     11 ans (≈ 141/an), WR ≈ 23 %, PF 1,15, +19 527 €/50 k€, DD ≈ 9,6 % ;
  C. bras « règles communes » (refroidissement 2, coupe-circuit 3 → 24 barres) sur la
     cellule par défaut, pour information : ce qu'elles coûteraient si le portefeuille
     les imposait à une règle dont l'auteur annonce 23 % de réussite.

Le bras de DÉCISION est le bras FIDÈLE : une position, pas de refroidissement, pas de
coupe-circuit (règle propre de S022 — doctrine Adrian 2026-09-12). Les critères sont
dans research/FALSIFICATION.md, écrits avant.
"""
from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

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
from strategies.S022_balke_atr_candle.strategy import Strategy        # noqa: E402

SYMBOL, TF, DAYS = "XAUUSD", "H1", 2190          # 6 ans de barres H1
MIN_TRADES, MAX_DD_R = 20, 12.0
SWITCHES = ("atr_mult", "proximity", "sl_pct")
BASE = {"atr_period": 200, "tp_pct": 0.02, "min_body_ratio": 0.0,
        "atr_mode": "sma", "side_mode": "both"}
DEFAULT_CELL = {"atr_mult": 2.5, "proximity": 0.25, "sl_pct": 0.005}   # ses réglages live

# Bras FIDÈLE — celui qui décide. Son EA n'a pas de coupe-circuit ; à 23 % de
# réussite annoncée, trois pertes d'affilée arrivent une fois sur deux.
FAITHFUL = dict(max_positions=1, cooldown_bars=0, cb_losses=999,
                cb_cooldown_bars=0, max_hold_bars=None)
# Bras RÈGLES COMMUNES — information seule, jamais utilisé pour trancher.
COMMON = dict(max_positions=1, cooldown_bars=2, cb_losses=3,
              cb_cooldown_bars=24, max_hold_bars=None)

# Ses chiffres publiés (blog 2026-06-09, XAUUSD tick réel 2015-2026).
PUB = {"trades": 1552, "years": 11, "trades_per_year": 1552 / 11, "win_rate": 23.0,
       "profit_factor": 1.15, "net_eur": 19527, "capital_eur": 50000, "max_dd_pct": 9.6,
       "live_since": "2026-03", "live_trades": 24, "live_eur": 515.65,
       "test_trades": 23, "test_eur": 634.03}
FID_TRADES_YR = (85.0, 200.0)     # fenêtres de fidélité, écrites avant la mesure
FID_WR = (17.0, 30.0)
GROSS_EXPECTANCY_R = 0.23 * 4 - 0.77      # +0,15 R/trade à RR 4 et WR 23 %

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


def label(c: dict) -> str:
    return f"×{c['atr_mult']:.1f} p{100*c['proximity']:.0f}% sl{100*c['sl_pct']:.1f}%"


def cells() -> list[dict]:
    g = Strategy().manifest().param_grid
    return [dict(zip(SWITCHES, combo)) for combo in itertools.product(*[g[k] for k in SWITCHES])]


def spec_with(spec: InstrumentSpec, spread_pips: float) -> InstrumentSpec:
    """Même instrument, autre tarif. `max_spread_pips` est relevé : le catalogue le
    fixe à 60 pips pour l'or alors que le spread réellement coté en dépasse 90 —
    sans ce relèvement le moteur refuserait TOUS les signaux, en silence. Le
    `slippage_pips` est REPRIS tel quel (et non remis à 0) : les deux tarifs doivent
    partager le même régime de coût, sinon la comparaison « catalogue contre mesuré »
    mélangerait deux différences au lieu d'une."""
    return InstrumentSpec(spec.symbol, pip=spec.pip, spread_pips=spread_pips,
                          max_spread_pips=max(spec.max_spread_pips, spread_pips * 10),
                          pip_value_per_lot=spec.pip_value_per_lot,
                          slippage_pips=spec.slippage_pips)


def measured_spread_pips(bars: pd.DataFrame, spec: InstrumentSpec) -> float | None:
    """Colonne `spread` des barres MT5, en points de cotation → pips du catalogue.
    Médiane sur les 365 derniers jours (régime courant)."""
    if "spread" not in bars.columns:
        return None
    rec = bars.loc[bars.index >= bars.index[-1] - pd.Timedelta(days=365), "spread"]
    if rec.empty:
        return None
    point = spec.pip / 10.0 if spec.pip in (0.0001, 0.01) else spec.pip
    return float(rec.median() * point / spec.pip)


def backtest(cell: dict, bars, spec, engine_kwargs=FAITHFUL):
    p = {**BASE, **cell}
    s = Strategy(p); s._symbol = SYMBOL
    data = s.precompute(bars, p)
    sigs = s.generate_signals(data, p, len(bars))
    return sigs, run_engine(sigs, bars, spec, **engine_kwargs)


def stats(res) -> dict:
    s = res.summary()
    s["r_per_trade"] = round(res.total_r / res.n_trades, 4) if res.n_trades else None
    return s


def by_year(res) -> dict:
    agg, cnt = defaultdict(float), defaultdict(int)
    for t in res.trades:
        y = pd.Timestamp(t.entry_time).year
        agg[y] += t.pnl_r; cnt[y] += 1
    return {str(y): (round(agg[y], 1), cnt[y]) for y in sorted(agg)}


def exits(res) -> dict:
    return dict(Counter(t.exit_reason for t in res.trades))


def main() -> int:
    rule(); print(f"S022 — ATR CANDLE BREAKOUT (Balke) · or H1 · dépôt {head()}"); rule()
    print("12 cellules · walk-forward ancré 4 fenêtres · témoin aléatoire · bras fidèle "
          "(sans coupe-circuit)")
    print("critères écrits avant la mesure : research/FALSIFICATION.md")

    bars = load_bars(SYMBOL, TF, days=DAYS, max_age_hours=10 ** 9)   # cache figé : results.json reproductible
    if bars is None or len(bars) < 2000:
        print(f"{SYMBOL} {TF} : barres indisponibles"); return 1
    spec_cat = get_spec(SYMBOL)
    sp_meas = measured_spread_pips(bars, spec_cat)
    spec = spec_cat
    spec_m = spec_with(spec_cat, sp_meas) if sp_meas else None
    years = (bars.index[-1] - bars.index[0]).days / 365.25

    rep: dict = {"commit": head(), "symbol": SYMBOL, "timeframe": TF, "bars": len(bars),
                 "start": str(bars.index[0]), "end": str(bars.index[-1]),
                 "years": round(years, 2),
                 "spread_catalogue": spec_cat.spread_pips, "spread_mesure": sp_meas,
                 "engine_faithful": FAITHFUL, "engine_common": COMMON,
                 "published": PUB}

    section(f"{SYMBOL} {TF} — {len(bars)} barres · {bars.index[0].date()} → "
            f"{bars.index[-1].date()} ({years:.1f} ans)")

    # ── 0. coût de bord ────────────────────────────────────────────────────
    _, r0 = backtest(DEFAULT_CELL, bars, spec)
    risks = np.array([t.risk_distance / spec.pip for t in r0.trades]) if r0.trades else np.array([np.nan])
    med = float(np.nanmedian(risks))
    pct_cat = 100 * spec_cat.spread_pips / med if med else float("nan")
    pct_mes = (100 * sp_meas / med) if (sp_meas and med) else float("nan")
    print(f"0. coût de bord · spread catalogue {spec_cat.spread_pips:.1f} pips"
          f"{f' · mesuré {sp_meas:.1f} pips' if sp_meas else ' · mesuré indisponible'}"
          f" · risque médian (cellule live, sl 0,5 %) {med:.0f} pips")
    print(f"   → le coût vaut {pct_cat:.1f} % du R au catalogue, {pct_mes:.1f} % au "
          f"spread mesuré (seuil d'échec : 35 %)")
    rep["cost"] = {"median_risk_pips": round(med, 1),
                   "pct_catalogue": round(pct_cat, 2) if med else None,
                   "pct_mesure": round(pct_mes, 2) if (sp_meas and med) else None}

    # ── 1. R1 / R5 — PORTE : rien ne se publie sur un dispositif en défaut ──
    ok, failures = True, []
    for c in (DEFAULT_CELL, {"atr_mult": 2.0, "proximity": 0.35, "sl_pct": 0.01}):
        s = Strategy({**BASE, **c}); s._symbol = SYMBOL
        r1 = causality_check(s, bars, SYMBOL)
        r5 = conformance_check(s, bars, SYMBOL)
        ok &= bool(r1.ok) and bool(r5.ok)
        if not r1.ok:
            failures.append(f"R1 (causalité) sur {label(c)} : "
                            f"{getattr(r1, 'error', None) or 'invariant de troncature violé'}")
        if not r5.ok:
            failures.append(f"R5 (backtest = live) sur {label(c)} : "
                            f"{getattr(r5, 'error', None) or 'divergence live/backtest'}")
        print(f"1. {label(c):22s} R1 {'OK' if r1.ok else 'FUITE'} · "
              f"R5 {'OK' if r5.ok else 'DIVERGENCE'}")
    rep["r1_r5_ok"] = bool(ok)
    if not ok:
        # FALSIFICATION.md : « R1 en défaut → on corrige et on remesure ». Publier un
        # results.json complet par-dessus une fuite de causalité, c'est transformer un
        # bug de dispositif en résultat de recherche. On s'arrête ici.
        section("ARRÊT — DISPOSITIF EN DÉFAUT, AUCUN RÉSULTAT PUBLIÉ")
        for f in failures:
            print(f"   {f}")
        print("\n   Corriger puis remesurer. Aucun results.json écrit "
              "(cf. research/FALSIFICATION.md § « échec du dispositif »).")
        return 2

    # ── 2. plein échantillon ───────────────────────────────────────────────
    print(f"\n2. plein échantillon (bras fidèle, spread catalogue)")
    print(f"   {'cellule':22s} {'n':>5s} {'R':>8s} {'R/tr':>7s} {'WR%':>6s} {'PF':>5s} "
          f"{'DD':>6s}  années (R)")
    rows = []
    for c in cells():
        sigs, res = backtest(c, bars, spec)
        st = stats(res)
        row = {"cell": c, "label": label(c), "n_signals": len(sigs), **st,
               "by_year": by_year(res), "exits": exits(res)}
        rows.append(row)
        print(f"   {row['label']:22s} {st['n_trades']:5d} {st['total_r']:8.1f} "
              f"{(st['r_per_trade'] or 0):7.3f} {(st['win_rate'] or 0):6.1f} "
              f"{(st['profit_factor'] or 0):5.2f} {st['max_dd_r']:6.1f}  "
              f"{' '.join(f'{y[2:]}:{v[0]:+.0f}' for y, v in row['by_year'].items())}")
    rep["full_sample"] = rows
    by_label = {r["label"]: r for r in rows}

    # ── 3. walk-forward ancré ──────────────────────────────────────────────
    s = Strategy({**BASE, **DEFAULT_CELL}); s._symbol = SYMBOL
    wf = run_walk_forward(s, bars, spec, param_grid=Strategy().manifest().param_grid,
                          min_trades=MIN_TRADES, max_dd_r=MAX_DD_R, verbose=False,
                          engine_kwargs=FAITHFUL)
    print("\n3. " + wf.render(top=6).replace("\n", "\n   "))
    # Le critère écrit d'avance est « STRICT **avec ≥ 20 trades hors échantillon** ».
    # On l'applique ICI, dans le code, plutôt qu'à la main dans le verdict : une
    # cellule STRICT à 12 trades hors échantillon ne compte pas, et cette décision ne
    # doit pas dépendre de qui relit le tableau.
    strict_raw = wf.strict()
    strict = [r for r in strict_raw if r.total_test_trades >= MIN_TRADES]
    print(f"   STRICT brutes : {len(strict_raw)} · retenues après le seuil "
          f"« ≥ {MIN_TRADES} trades hors échantillon » : {len(strict)}")
    print(f"   attendues par pur hasard sur {len(cells())} cellules à 5 % : "
          f"≈ {0.05*len(cells()):.1f} (le moteur affiche ce même nombre arrondi à l'entier)")

    def _cell_of(r):
        return {k: r.params[k] for k in SWITCHES}

    rep["wf"] = {"n_configs": wf.n_configs,
                 "min_oos_trades": MIN_TRADES,
                 "strict_raw": [{"label": label(_cell_of(r)),
                                 "avg_oos": round(r.avg_oos, 3),
                                 "oos_trades": r.total_test_trades} for r in strict_raw],
                 "strict": [{"label": label(_cell_of(r)),
                             "avg_oos": round(r.avg_oos, 3),
                             "oos_trades": r.total_test_trades,
                             "oos_series": [round(x, 2) for x in r.oos_series]}
                            for r in strict],
                 "all": [{"label": label({k: r.params[k] for k in SWITCHES}),
                          "avg_oos": round(r.avg_oos, 3),
                          "oos_trades": r.total_test_trades,
                          "honest_r": round(r.honest_r, 2),
                          "illusion_r": round(r.illusion_r, 2),
                          "strict": r.strict_pass} for r in wf.results]}

    # ── 4 & 5. témoin + spread mesuré ──────────────────────────────────────
    elig = [r for r in rows if r["n_trades"] >= MIN_TRADES]
    picks: dict[str, dict] = {"live (×2,5 p25% sl0,5%)": by_label[label(DEFAULT_CELL)]}
    if elig:
        picks["meilleure R/tr"] = max(elig, key=lambda r: r["r_per_trade"] or -9)
    for r in strict:
        picks.setdefault(f"STRICT {label(_cell_of(r))}", by_label[label(_cell_of(r))])

    print("\n4-5. témoin aléatoire et spread mesuré (bras fidèle)")
    rep["control"] = {}
    for name, r in picks.items():
        _, res = backtest(r["cell"], bars, spec)
        line = f"   {name:28s} {r['label']:22s} n={res.n_trades:4d} R={res.total_r:8.1f}"
        pct, ctrl_extra = None, {}
        if res.n_trades >= MIN_TRADES:
            ca = control_arm(bars, spec, res.trades, res.total_r, engine_kwargs=FAITHFUL)
            if ca is not None:
                pct = float(ca.percentile)
                line += (f" · témoin p{pct:5.1f} (nul médian {ca.null_median:+6.1f} R"
                         f"{'' if ca.effectif_ok else ', EFFECTIF ÉCARTÉ'})")
                ctrl_extra = {"null_median_r": round(ca.null_median, 2),
                              "null_p95_r": round(ca.null_p95, 2),
                              "median_draw_trades": ca.median_draw_trades,
                              "effectif_ok": bool(ca.effectif_ok)}
            else:
                line += " · témoin indisponible"
        else:
            line += " · effectif < 20, pas de témoin"
        entry = {"label": r["label"], "cell": r["cell"], "n": res.n_trades,
                 "total_r": round(res.total_r, 2),
                 "r_per_trade": round(res.total_r / res.n_trades, 4) if res.n_trades else None,
                 "percentile": None if pct is None else round(pct, 1), **ctrl_extra}
        if spec_m is not None:
            _, rm = backtest(r["cell"], bars, spec_m)
            rpt_m = (rm.total_r / rm.n_trades) if rm.n_trades else 0.0
            line += f" · spread mesuré : R={rm.total_r:8.1f} ({rpt_m:+.3f}/tr)"
            entry["total_r_spread_mesure"] = round(rm.total_r, 2)
            entry["r_per_trade_spread_mesure"] = round(rpt_m, 4)
            entry["n_spread_mesure"] = rm.n_trades
        rep["control"][name] = entry
        print(line)

    # ── F. fidélité aux chiffres publiés ───────────────────────────────────
    section("F. FIDÉLITÉ — cellule par défaut (ses réglages live) contre ses chiffres publiés")
    d = by_label[label(DEFAULT_CELL)]
    _, res_d = backtest(DEFAULT_CELL, bars, spec)
    tpy = res_d.n_trades / years
    ex = exits(res_d)
    sl_share = 100.0 * ex.get("SL", 0) / max(1, res_d.n_trades)
    rpt_cat = res_d.total_r / res_d.n_trades if res_d.n_trades else float("nan")
    rpt_mes = None
    if spec_m is not None:
        _, res_dm = backtest(DEFAULT_CELL, bars, spec_m)
        rpt_mes = res_dm.total_r / res_dm.n_trades if res_dm.n_trades else float("nan")
    fid_freq = FID_TRADES_YR[0] <= tpy <= FID_TRADES_YR[1]
    fid_wr = FID_WR[0] <= (d["win_rate"] or 0) <= FID_WR[1]
    print(f"   trades              {res_d.n_trades:6d} sur {years:.1f} ans → "
          f"{tpy:6.1f}/an   · publié ≈ {PUB['trades_per_year']:.0f}/an "
          f"(1 552 sur 11 ans) · fenêtre {FID_TRADES_YR[0]:.0f}-{FID_TRADES_YR[1]:.0f} "
          f"→ {'OK' if fid_freq else 'HORS FENÊTRE'}")
    print(f"   taux de réussite    {(d['win_rate'] or 0):6.1f} %"
          f"{'':>17s}· publié ≈ {PUB['win_rate']:.0f} % · fenêtre "
          f"{FID_WR[0]:.0f}-{FID_WR[1]:.0f} → {'OK' if fid_wr else 'HORS FENÊTRE'}")
    print(f"   profit factor       {(d['profit_factor'] or 0):6.2f}"
          f"{'':>20s}· publié {PUB['profit_factor']:.2f}")
    print(f"   motifs de sortie    {ex} → stops {sl_share:.0f} % "
          f"({'dominé par les stops' if sl_share > 50 else 'NON dominé par les stops'})")
    print(f"   R/trade             {rpt_cat:+.3f} (catalogue)"
          + (f" · {rpt_mes:+.3f} (spread mesuré)" if rpt_mes is not None else "")
          + f" · espérance brute théorique à RR4/WR23 % : {GROSS_EXPECTANCY_R:+.2f} R")
    print(f"   coût de bord        {pct_mes:.1f} % du R au spread mesuré")
    rep["fidelity"] = {
        "trades": res_d.n_trades, "years": round(years, 2), "trades_per_year": round(tpy, 1),
        "win_rate": d["win_rate"], "profit_factor": d["profit_factor"],
        "exits": ex, "sl_share_pct": round(sl_share, 1),
        "r_per_trade_catalogue": round(rpt_cat, 4),
        "r_per_trade_mesure": None if rpt_mes is None else round(rpt_mes, 4),
        "gross_expectancy_r": round(GROSS_EXPECTANCY_R, 3),
        "window_trades_per_year": FID_TRADES_YR, "window_win_rate": FID_WR,
        "freq_ok": bool(fid_freq), "wr_ok": bool(fid_wr),
        "by_year": by_year(res_d),
    }

    # ── F-bis. description du dispositif (aucun nouveau test, aucune cellule) ──
    # FALSIFICATION.md nomme d'avance l'écart d'exécution (tick contre barre close)
    # comme premier suspect en cas d'échec. On le DÉCRIT ici : combien de signaux la
    # règle produit, combien la contrainte « une position » en retire, et combien de
    # stops sont pris sur une barre qui touchait aussi la cible. Ce sont des
    # descriptions du dispositif, pas des variantes de la stratégie.
    sigs_d, _ = backtest(DEFAULT_CELL, bars, spec)
    wins = [t.pnl_r for t in res_d.trades if t.pnl_r > 0]
    losses = [t.pnl_r for t in res_d.trades if t.pnl_r <= 0]
    holds = [t.bars_held for t in res_d.trades]
    pos = {pd.Timestamp(t): i for i, t in enumerate(bars.index)}
    hi, lo = bars["high"].to_numpy(), bars["low"].to_numpy()
    edge = spec.spread_pips * spec.pip / 2.0 + spec.slippage_pips * spec.pip
    conflicts, gain_if_tp = 0, 0.0
    for t in res_d.trades:
        if t.exit_reason != "SL" or t.target_price is None or t.exit_time is None:
            continue
        j = pos.get(pd.Timestamp(t.exit_time))
        if j is None:
            continue
        touched = (hi[j] >= t.target_price) if t.side.value == "LONG" else (lo[j] <= t.target_price)
        if touched:
            conflicts += 1
            g = ((t.target_price - t.entry_price) if t.side.value == "LONG"
                 else (t.entry_price - t.target_price)) - edge
            gain_if_tp += g / t.risk_distance - t.pnl_r
    print(f"\n   dispositif · signaux produits {len(sigs_d)} ({len(sigs_d)/years:.0f}/an) ; "
          f"retenus {res_d.n_trades} ; refusés car une position est déjà ouverte "
          f"{res_d.skipped_cooldown + res_d.skipped_open}")
    print(f"   dispositif · gain moyen {np.mean(wins) if wins else 0:+.2f} R, perte "
          f"moyenne {np.mean(losses) if losses else 0:+.2f} R, durée médiane "
          f"{int(np.median(holds)) if holds else 0} barres")
    print(f"   dispositif · stops pris sur une barre qui touchait AUSSI la cible : "
          f"{conflicts} ({100*conflicts/max(1,res_d.n_trades):.1f} % des trades) — "
          f"borne haute si tous se résolvaient en cible : R={res_d.total_r + gain_if_tp:+.1f} "
          f"(contre {res_d.total_r:+.1f})")
    rep["fidelity"].update({
        "n_signals": len(sigs_d), "signals_per_year": round(len(sigs_d) / years, 1),
        "refused_position_open": res_d.skipped_cooldown + res_d.skipped_open,
        "avg_win_r": round(float(np.mean(wins)), 3) if wins else None,
        "avg_loss_r": round(float(np.mean(losses)), 3) if losses else None,
        "median_bars_held": int(np.median(holds)) if holds else None,
        "same_bar_sl_tp_conflicts": conflicts,
        "upper_bound_r_if_conflicts_were_tp": round(res_d.total_r + gain_if_tp, 2),
    })

    # ── C. bras « règles communes », information seule ─────────────────────
    section("C. BRAS RÈGLES COMMUNES (information) — cellule par défaut")
    _, res_c = backtest(DEFAULT_CELL, bars, spec, engine_kwargs=COMMON)
    st_c = stats(res_c)
    print(f"   fidèle          n={res_d.n_trades:4d} R={res_d.total_r:8.1f} "
          f"({rpt_cat:+.3f}/tr) WR {(d['win_rate'] or 0):.1f} %")
    print(f"   règles communes n={res_c.n_trades:4d} R={res_c.total_r:8.1f} "
          f"({(st_c['r_per_trade'] or 0):+.3f}/tr) WR {(st_c['win_rate'] or 0):.1f} % "
          f"· refusés : refroidissement {res_c.skipped_cooldown}, position ouverte "
          f"{res_c.skipped_open}")
    # Une seule convention de signe, ici et dans le verdict : « communes − fidèle ».
    d_tr, d_r = res_c.n_trades - res_d.n_trades, res_c.total_r - res_d.total_r
    print(f"   → par rapport au bras fidèle : {d_tr:+d} trades, {d_r:+.1f} R")
    rep["common_rules_arm"] = {**st_c, "by_year": by_year(res_c), "exits": exits(res_c),
                               "delta_vs_faithful": {"trades": d_tr, "r": round(d_r, 2)}}

    p = os.path.join(OUT, "results.json")
    json.dump(rep, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
    print(f"\nrésultats : {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
