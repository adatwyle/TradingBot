"""
Mesure de S023 — Turnaround Tuesday (Balke). Cellule de fidélité, référence non
filtrée, grille, walk-forward ancré, témoin, bras « règles communes ».

    PYTHONIOENCODING=utf-8 python strategies/S023_balke_turnaround_tuesday/backtests/run_wf.py
    S023_SYMBOLS=DAX ...   (sous-ensemble)

N'implémente aucun moteur (R9). Par instrument :
  0. calibrage de la SORTIE — distance en barres H1 entre la première barre du
     lundi et la dernière du mardi, mesurée sur les données. C'est le seul moyen
     d'exprimer « clôture mardi 23:50 » avec `max_hold_bars` ; la distribution est
     publiée, l'approximation est déclarée (même geste que S009) ;
  1. coût de bord au spread CATALOGUE et au spread MESURÉ (colonne `spread`) ;
  2. R1 causalité, R5 conformance sur données réelles ;
  3. CELLULE DE FIDÉLITÉ (ses réglages live) + RÉFÉRENCE NON FILTRÉE
     (`sma_period=0`, achat de chaque lundi) — l'écart entre les deux EST
     l'apport du filtre SMA, et c'est la première chose à lire ;
  4. grille 18 cellules, plein échantillon, par année ;
  5. walk-forward ancré 4 fenêtres, cellules STRICT ;
  6. bras témoin (entrées aléatoires, même gabarit, même durée de détention) ;
  7. bras « règles communes » (refroidissement + coupe-circuit) — information
     seulement, il ne peut pas invalider le bras fidèle ;
  8. tout rejoué au spread mesuré.

Le P&L est rapporté en R **et en % du prix d'entrée** : avec une garde à 5 %, 1 R
vaut ~5 % du prix, et c'est le % qui se compare aux chiffres de l'auteur.
Les critères sont dans research/FALSIFICATION.md, écrits avant.
"""
from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from typing import Optional

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

from core.backtest.anchored_wf import control_arm, run_walk_forward     # noqa: E402
from core.backtest.engine import InstrumentSpec, run as run_engine      # noqa: E402
from core.data.instruments import get_spec                              # noqa: E402
from core.data.source import load_bars                                  # noqa: E402
from core.validation.causality import check as causality_check          # noqa: E402
from core.validation.conformance import check as conformance_check      # noqa: E402
from strategies.S023_balke_turnaround_tuesday.strategy import Strategy   # noqa: E402

SYMBOLS = [s for s in os.environ.get("S023_SYMBOLS", "DAX,NASDAQ,US30").split(",") if s]
DAYS = 1855                    # cache figé du 2026-09-12 (docs/data/INDICES_intraday_2026-09-12.md)
MIN_TRADES, MAX_DD_R = 20, 12.0
SWITCHES = ("sma_period", "entry_mode", "guard_pct")

# Ses réglages live, par instrument (vidéo qgsi-u0kOVw [27:41]-[29:19]).
FIDELITY = {"US30": 25, "NASDAQ": 9, "DAX": 40}
FID_MODE, FID_GUARD = "first_bar", 0.05

# Bras moteur, déclarés dans FALSIFICATION.md avant la mesure.
FAITHFUL = dict(max_positions=1, cooldown_bars=0, cb_losses=999, cb_cooldown_bars=0)
COMMON_RULES = dict(max_positions=1, cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24)

OUT = os.path.dirname(os.path.abspath(__file__))


class DispositifEnDefaut(Exception):
    """R1 ou R5 en défaut : la mesure ne vaut rien et ne doit pas être publiée.
    Portée par la PORTE du § 2 ; interceptée dans main(), qui s'arrête sans
    écrire results.json."""

    def __init__(self, failures: list[str]):
        super().__init__("; ".join(failures))
        self.failures = failures


def rule(c="=", n=104): print(c * n)
def section(t): print(); rule(); print(t); rule()


def head() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        return f"{sha}{' (arbre modifié)' if dirty else ''}"
    except Exception:
        return "inconnu"


def label(c: dict) -> str:
    n = c["sma_period"]
    return f"{'SMA' + str(n) if n else 'nu ':>5s} {c['entry_mode']:9s} g{100*c['guard_pct']:.0f}%"


def cells() -> list[dict]:
    g = Strategy().manifest().param_grid
    return [dict(zip(SWITCHES, combo)) for combo in itertools.product(*[g[k] for k in SWITCHES])]


# ── 0. calibrage de la sortie ───────────────────────────────────────────────
def hold_calibration(bars: pd.DataFrame, open_dow: Optional[int] = None) -> dict:
    """Distance en barres entre la première barre du jour d'ouverture (lundi) et
    la dernière barre du jour suivant (mardi). Le mode sert de `max_hold_bars`.

    `open_dow` vient du manifeste (R7 : source unique de vérité) — le coder en dur
    ici ferait mentir le calibrage si le jour d'ouverture changeait un jour."""
    if open_dow is None:
        open_dow = int(Strategy().manifest().default_params["open_dow"])
    idx = bars.index
    day = idx.normalize()
    pos = {ts: i for i, ts in enumerate(idx)}
    firsts, lasts = {}, {}
    for i, ts in enumerate(idx):
        d = day[i]
        firsts.setdefault(d, ts)
        lasts[d] = ts
    holds = []
    for d, ts in firsts.items():
        if d.dayofweek != open_dow:
            continue
        nxt = d + pd.Timedelta(days=1)
        if nxt in lasts:
            holds.append(pos[lasts[nxt]] - pos[ts])
    if not holds:
        return {"hold": None}
    cnt = Counter(holds)
    mode = cnt.most_common(1)[0][0]
    a = np.array(holds)
    return {"hold": int(mode), "n_weeks": len(holds),
            "share_mode": round(100.0 * cnt[mode] / len(holds), 1),
            "median": int(np.median(a)), "p10": int(np.percentile(a, 10)), "max": int(a.max()),
            "first_bar_hours": dict(Counter(ts.hour for d, ts in firsts.items()
                                            if d.dayofweek == open_dow).most_common(3)),
            "last_bar_hours": dict(Counter(ts.hour for d, ts in lasts.items()
                                           if d.dayofweek == (open_dow + 1) % 7).most_common(3))}


# ── spreads ─────────────────────────────────────────────────────────────────
def spec_with(spec: InstrumentSpec, spread_pips: float) -> InstrumentSpec:
    """Même instrument, autre spread. `max_spread_pips` est relevé (le plafond du
    catalogue est calibré sur le spread du catalogue ; sans relèvement le moteur
    refuserait tous les trades à spread mesuré, en silence). `slippage_pips` est
    REPRIS tel quel, jamais remis à 0 : les deux tarifs doivent partager le même
    régime de coût, sinon la comparaison « catalogue contre mesuré » mélangerait
    deux différences au lieu d'une (même contrat que S022/S024)."""
    return InstrumentSpec(spec.symbol, pip=spec.pip, spread_pips=spread_pips,
                          max_spread_pips=max(spec.max_spread_pips, spread_pips * 10),
                          pip_value_per_lot=spec.pip_value_per_lot,
                          slippage_pips=spec.slippage_pips)


def measured_spread_pips(bars: pd.DataFrame, spec: InstrumentSpec) -> float | None:
    """Colonne `spread` des barres MT5, en POINTS de cotation → pips du catalogue.
    Médiane sur les 365 derniers jours (régime courant).

    Chez ce courtier, le point vaut toujours pip/10 : FX 5 chiffres (pip 1e-4,
    point 1e-5), JPY 3 chiffres (pip 1e-2, point 1e-3) ET indices à 2 décimales
    (pip 0,1 = 10 points). Les valeurs obtenues ici doivent redonner celles
    mesurées le 2026-09-12 : DAX 23,0 · NASDAQ 12,0 · US30 35,0 pips.

    Renvoie None plutôt qu'une valeur douteuse : une médiane nulle, négative ou
    NaN signifie que la colonne `spread` n'est pas exploitable (0 pip pris au pied
    de la lettre donnerait un « spread mesuré » gratuit, plus flatteur que le
    catalogue, sans le dire).
    """
    if "spread" not in bars.columns:
        return None
    rec = bars.loc[bars.index >= bars.index[-1] - pd.Timedelta(days=365), "spread"]
    if rec.empty:
        return None
    point = 0.01 if spec.pip == 0.1 else spec.pip / 10.0
    val = float(rec.median() * point / spec.pip)
    if not np.isfinite(val) or val <= 0.0:
        return None
    return val


# ── exécution d'une cellule ─────────────────────────────────────────────────
def backtest(cell: dict, bars, spec, symbol, ek: dict):
    p = {**Strategy().manifest().default_params, **cell}
    s = Strategy(p)
    s._symbol = symbol
    data = s.precompute(bars, p)
    sigs = s.generate_signals(data, p, len(bars))
    return sigs, run_engine(sigs, bars, spec, **ek)


def pct_returns(res) -> dict:
    """P&L en % du prix d'entrée, net des coûts (pnl_r × risque / entrée).
    Avec une garde de g %, 1 R ≈ g % du prix : c'est cette unité qui se compare
    au « +0,4 % du notionnel par trade » annoncé par l'auteur."""
    if not res.trades:
        return {"sum_pct": 0.0, "avg_pct": None, "med_pct": None}
    v = np.array([t.pnl_r * t.risk_distance / t.entry_price for t in res.trades]) * 100.0
    return {"sum_pct": round(float(v.sum()), 2), "avg_pct": round(float(v.mean()), 4),
            "med_pct": round(float(np.median(v)), 4)}


def stats(res) -> dict:
    s = res.summary()
    s["r_per_trade"] = round(res.total_r / res.n_trades, 4) if res.n_trades else None
    s.update(pct_returns(res))
    s["guard_hits"] = sum(1 for t in res.trades if t.exit_reason == "SL")
    return s


def by_year(res) -> dict:
    agg_r, agg_p, cnt = defaultdict(float), defaultdict(float), defaultdict(int)
    for t in res.trades:
        y = pd.Timestamp(t.entry_time).year
        agg_r[y] += t.pnl_r
        agg_p[y] += 100.0 * t.pnl_r * t.risk_distance / t.entry_price
        cnt[y] += 1
    return {str(y): {"r": round(agg_r[y], 2), "pct": round(agg_p[y], 2), "n": cnt[y]}
            for y in sorted(agg_r)}


def exit_profile(res) -> dict:
    """Validation de l'approximation `max_hold_bars` : où tombent réellement les
    sorties ? Attendu en `first_bar` : mardi soir, dernière barre du jour."""
    if not res.trades:
        return {}
    ex = [pd.Timestamp(t.exit_time) for t in res.trades if t.exit_time is not None]
    en = [pd.Timestamp(t.entry_time) for t in res.trades]
    dows = Counter(t.dayofweek for t in ex)
    return {"reasons": dict(Counter(t.exit_reason for t in res.trades)),
            "entry_hours": dict(Counter(t.hour for t in en).most_common(4)),
            "exit_dow": {int(k): int(v) for k, v in sorted(dows.items())},
            "exit_hours": dict(Counter(t.hour for t in ex).most_common(4)),
            "pct_exit_tuesday": round(100.0 * dows.get(1, 0) / len(ex), 1),
            "median_bars_held": int(np.median([t.bars_held for t in res.trades]))}


def line_cell(tag: str, st: dict) -> str:
    return (f"   {tag:24s} n={st['n_trades']:4d} R={st['total_r']:8.2f} "
            f"R/tr={(st['r_per_trade'] or 0):+7.4f} %tot={st['sum_pct']:+8.2f} "
            f"%/tr={(st['avg_pct'] or 0):+7.4f} WR={(st['win_rate'] or 0):5.1f} "
            f"PF={(st['profit_factor'] or 0):5.2f} DD={st['max_dd_r']:6.2f} "
            f"garde={st['guard_hits']:2d}")


# ── un instrument ───────────────────────────────────────────────────────────
def measure(symbol: str, rep_all: dict) -> None:
    bars = load_bars(symbol, "H1", days=DAYS, max_age_hours=10 ** 9)   # cache figé
    if bars is None or len(bars) < 2000:
        print(f"\n{symbol} H1 : barres indisponibles")
        rep_all[symbol] = {"error": "barres"}
        return

    section(f"{symbol} H1 — {len(bars)} barres · {bars.index[0].date()} → {bars.index[-1].date()}")
    rep = {"symbol": symbol, "timeframe": "H1", "bars": len(bars),
           "period": [str(bars.index[0]), str(bars.index[-1])]}

    # 0. calibrage de la sortie
    cal = hold_calibration(bars)
    hold = cal["hold"]
    ek_faithful = {**FAITHFUL, "max_hold_bars": hold}
    ek_common = {**COMMON_RULES, "max_hold_bars": hold}
    print(f"0. sortie : max_hold_bars = {hold} barres "
          f"(1re barre lundi → dernière barre mardi ; mode sur {cal['n_weeks']} semaines, "
          f"{cal['share_mode']} % · médiane {cal['median']} · p10 {cal['p10']})")
    print(f"   heure de la 1re barre du lundi {cal['first_bar_hours']} · "
          f"dernière barre du mardi {cal['last_bar_hours']}")
    rep["hold_calibration"] = cal

    # 1. coût de bord
    spec_cat = get_spec(symbol)
    sp_meas = measured_spread_pips(bars, spec_cat)
    spec_meas = spec_with(spec_cat, sp_meas) if sp_meas else None
    px = float(bars["close"].median())
    print(f"1. coût : spread catalogue {spec_cat.spread_pips:.1f} pips"
          f"{f' · mesuré {sp_meas:.1f} pips' if sp_meas else ' · mesuré indisponible'}"
          f" · prix médian {px:.0f} → coût aller-retour "
          f"{100 * spec_cat.spread_pips * spec_cat.pip / px:.4f} % / "
          f"{(100 * sp_meas * spec_cat.pip / px) if sp_meas else float('nan'):.4f} % du prix")
    rep["cost"] = {"spread_catalogue": spec_cat.spread_pips, "spread_mesure": sp_meas,
                   "median_price": round(px, 1),
                   "pct_price_catalogue": round(100 * spec_cat.spread_pips * spec_cat.pip / px, 5),
                   "pct_price_mesure": (round(100 * sp_meas * spec_cat.pip / px, 5) if sp_meas else None)}

    # 2. R1 / R5 — PORTE : rien ne se publie sur un dispositif en défaut
    fid_cell = {"sma_period": FIDELITY[symbol], "entry_mode": FID_MODE, "guard_pct": FID_GUARD}
    ok, failures = True, []
    for c in (fid_cell, {"sma_period": 9, "entry_mode": "any_bar", "guard_pct": 0.03}):
        p = {**Strategy().manifest().default_params, **c}
        s = Strategy(p)
        s._symbol = symbol
        r1 = causality_check(s, bars, symbol)
        r5 = conformance_check(s, bars, symbol)
        ok &= bool(r1.ok) and bool(r5.ok)
        if not r1.ok:
            failures.append(f"{symbol} · R1 (causalité) sur {label(c)} : "
                            f"{getattr(r1, 'error', None) or 'invariant de troncature violé'}")
        if not r5.ok:
            failures.append(f"{symbol} · R5 (backtest = live) sur {label(c)} : "
                            f"{getattr(r5, 'error', None) or 'divergence live/backtest'}")
        print(f"2. {label(c):24s} R1 {'OK' if r1.ok else 'FUITE'} · "
              f"R5 {'OK' if r5.ok else 'DIVERGENCE'}")
    rep["r1_r5_ok"] = bool(ok)
    if not ok:
        # FALSIFICATION.md § « échec du dispositif » : R1 en défaut → on corrige et on
        # remesure. Publier un results.json complet par-dessus une fuite de causalité
        # ou une divergence live/backtest, ce serait transformer un bug de dispositif
        # en résultat de recherche. On s'arrête AVANT toute mesure et toute écriture.
        rep_all[symbol] = rep
        raise DispositifEnDefaut(failures)

    # 3. fidélité vs référence non filtrée
    print(f"\n3. CELLULE DE FIDÉLITÉ (ses réglages live) et RÉFÉRENCE NON FILTRÉE")
    ref_cell = {"sma_period": 0, "entry_mode": FID_MODE, "guard_pct": FID_GUARD}
    key_rows = {}
    for tag, cell, ek in (("fidélité", fid_cell, ek_faithful),
                          ("référence non filtrée", ref_cell, ek_faithful),
                          ("fidélité + règles communes", fid_cell, ek_common)):
        _, res = backtest(cell, bars, spec_cat, symbol, ek)
        st = stats(res)
        key_rows[tag] = {"cell": cell, "label": label(cell), **st,
                         "by_year": by_year(res), "exit": exit_profile(res)}
        print(line_cell(f"{tag} · {label(cell)}", st))
    ep = key_rows["fidélité"]["exit"]
    print(f"   sorties (fidélité) : {ep.get('reasons')} · jour de sortie {ep.get('exit_dow')} "
          f"· heures {ep.get('exit_hours')} · mardi {ep.get('pct_exit_tuesday')} % "
          f"· barres tenues (méd) {ep.get('median_bars_held')}")
    print(f"   entrées : heures {ep.get('entry_hours')}")
    print("   par année (fidélité) : " + "  ".join(
        f"{y}:{v['pct']:+.1f}%/{v['n']}" for y, v in key_rows["fidélité"]["by_year"].items()))
    print("   par année (non filtré) : " + "  ".join(
        f"{y}:{v['pct']:+.1f}%/{v['n']}" for y, v in key_rows["référence non filtrée"]["by_year"].items()))
    rep["key_cells"] = key_rows

    # 4. grille, plein échantillon
    print(f"\n4. grille 18 cellules (bras fidèle, spread catalogue)")
    rows = []
    for c in cells():
        _, res = backtest(c, bars, spec_cat, symbol, ek_faithful)
        st = stats(res)
        # Le profil de sortie est mesuré sur TOUTES les cellules, pas seulement les
        # cellules-clés en `first_bar` : sans cela, toute phrase sur la dérive de
        # sortie d'`any_bar` (entrée tardive → sortie mercredi) serait une supposition.
        rows.append({"cell": c, "label": label(c), **st,
                     "by_year": by_year(res), "exit": exit_profile(res)})
        print(line_cell(label(c), st))
    rep["full_sample"] = rows

    # Dérive de sortie du mode `any_bar`, mesurée — la contrepartie déclarée de sa
    # fidélité d'entrée (« check constantly »).
    drift = {}
    for mode in ("first_bar", "any_bar"):
        sel = [r for r in rows if r["cell"]["entry_mode"] == mode and r["exit"]]
        if not sel:
            continue
        tue = float(np.mean([r["exit"]["pct_exit_tuesday"] for r in sel]))
        wed = float(np.mean([100.0 * r["exit"]["exit_dow"].get(2, 0)
                             / max(sum(r["exit"]["exit_dow"].values()), 1) for r in sel]))
        drift[mode] = {"pct_exit_tuesday_moy": round(tue, 1), "pct_exit_mercredi_moy": round(wed, 1),
                       "n_cellules": len(sel)}
    print(f"   dérive de sortie (moyenne des 9 cellules de chaque mode) : "
          + " · ".join(f"{m} mardi {v['pct_exit_tuesday_moy']} % / mercredi "
                       f"{v['pct_exit_mercredi_moy']} %" for m, v in drift.items()))
    rep["exit_drift"] = drift

    # 5. walk-forward ancré
    base = Strategy({**Strategy().manifest().default_params, **fid_cell})
    base._symbol = symbol
    wf = run_walk_forward(base, bars, spec_cat, param_grid=Strategy().manifest().param_grid,
                          min_trades=MIN_TRADES, max_dd_r=MAX_DD_R, verbose=False,
                          engine_kwargs=ek_faithful)
    print("\n5. " + wf.render(top=6).replace("\n", "\n   "))
    print(f"   STRICT attendues par hasard sur {len(cells())} cellules à 5 % : "
          f"≈ {0.05 * len(cells()):.1f} · observées : {len(wf.strict())}")
    rep["wf"] = {"n_configs": wf.n_configs,
                 "strict": [{"label": r.label, "avg_oos": round(r.avg_oos, 3),
                             "oos_trades": r.total_test_trades} for r in wf.strict()],
                 "tier1": [{"label": r.label, "avg_oos": round(r.avg_oos, 3),
                            "oos_trades": r.total_test_trades} for r in wf.tier1()[:6]]}

    # 6-8. témoin, spread mesuré
    elig = [r for r in rows if r["n_trades"] >= MIN_TRADES and r["avg_pct"] is not None]
    picks = {"fidélité": key_rows["fidélité"], "référence non filtrée": key_rows["référence non filtrée"]}
    if elig:
        picks["meilleure grille (%/tr)"] = max(elig, key=lambda r: r["avg_pct"])
    # Le critère 1 de FALSIFICATION.md ouvre la porte à une cellule STRICT avec
    # ≥ 20 trades hors échantillon : elle doit donc être passée au témoin elle
    # aussi, sinon le critère n'est pas appliqué, il est contourné.
    guard_share = {r["label"]: (100.0 * r["guard_hits"] / r["n_trades"] if r["n_trades"] else 100.0)
                   for r in rows}
    best_strict = next((r for r in wf.strict() if r.total_test_trades >= MIN_TRADES), None)
    if best_strict is not None:
        sc = {k: best_strict.params[k] for k in SWITCHES}
        picks["meilleure STRICT (WF)"] = {"cell": sc, "label": label(sc)}
    # Une cellule STRICT dont la garde part > 5 % des trades n'est PLUS une
    # reproduction fidèle (FALSIFICATION.md § « ce qui n'est pas reproduit », point 1) :
    # elle a gagné un stop de gestion que Balke n'a pas. On mesure donc AUSSI la
    # meilleure STRICT qui respecte encore ce seuil — sans quoi le verdict citerait
    # un percentile obtenu sur une autre stratégie que celle annoncée.
    best_strict_fid = next((r for r in wf.strict()
                            if r.total_test_trades >= MIN_TRADES
                            and guard_share.get(label({k: r.params[k] for k in SWITCHES}), 100.0) <= 5.0),
                           None)
    if best_strict_fid is not None:
        sc = {k: best_strict_fid.params[k] for k in SWITCHES}
        if label(sc) != picks.get("meilleure STRICT (WF)", {}).get("label"):
            picks["meilleure STRICT fidèle (garde ≤ 5 %)"] = {"cell": sc, "label": label(sc)}
    print("\n6-8. témoin aléatoire (même effectif, même gabarit, même durée) et spread mesuré")
    rep["control"] = {}
    for name, r in picks.items():
        _, res = backtest(r["cell"], bars, spec_cat, symbol, ek_faithful)
        entry = {"label": r["label"], "n": res.n_trades, "total_r": round(res.total_r, 2),
                 **pct_returns(res)}
        line = f"   {name:26s} {r['label']:24s} n={res.n_trades:4d} %tot={entry['sum_pct']:+8.2f}"
        if res.n_trades >= MIN_TRADES:
            ca = control_arm(bars, spec_cat, res.trades, res.total_r, engine_kwargs=ek_faithful)
            pct = float((ca.draws_r < res.total_r).mean() * 100.0) if ca is not None else float("nan")
            entry["percentile"] = None if ca is None else round(pct, 1)
            entry["control_median_r"] = None if ca is None else round(float(np.median(ca.draws_r)), 2)
            line += (f" · témoin p{pct:5.1f} (médiane nulle {entry['control_median_r']:+.2f} R "
                     f"vs {res.total_r:+.2f} R)")
        else:
            entry["percentile"] = None
            line += " · effectif < 20, pas de témoin"
        if spec_meas is not None:
            _, rm = backtest(r["cell"], bars, spec_meas, symbol, ek_faithful)
            pm = pct_returns(rm)
            entry["spread_mesure"] = {"total_r": round(rm.total_r, 2), **pm}
            line += f" · spread mesuré : %tot={pm['sum_pct']:+8.2f} (%/tr {(pm['avg_pct'] or 0):+.4f})"
        rep["control"][name] = entry
        print(line)

    rep_all[symbol] = rep


def main() -> int:
    rule()
    print(f"S023 — TURNAROUND TUESDAY (Balke) · dépôt {head()}")
    rule()
    print("3 indices · 18 cellules + cellule de fidélité + référence non filtrée · "
          "walk-forward ancré 4 fenêtres · témoin aléatoire")
    print("critères écrits avant : research/FALSIFICATION.md · « BACKTESTED = mesuré, pas validé »")
    rep_all: dict = {"commit": head(), "run": "2026-09-12", "symbols": {}}
    for sym in SYMBOLS:
        try:
            measure(sym, rep_all["symbols"])
        except DispositifEnDefaut as exc:
            # La PORTE du § 2 a sauté. Ce n'est pas « un instrument cassé parmi
            # d'autres » : c'est la mesure elle-même qui ne vaut rien. Aucun
            # results.json n'est écrit — ni pour cet instrument, ni pour les autres.
            section("ARRÊT — DISPOSITIF EN DÉFAUT, AUCUN RÉSULTAT PUBLIÉ")
            for f in exc.failures:
                print(f"   {f}")
            print("\n   Corriger puis remesurer. Aucun results.json écrit "
                  "(cf. research/FALSIFICATION.md § « échec du dispositif, pas de "
                  "l'hypothèse »).")
            return 2
        except Exception as exc:                  # un instrument cassé ne cache pas les autres
            import traceback
            print(f"\n{sym} : ERREUR {type(exc).__name__}: {exc}")
            traceback.print_exc()
            rep_all["symbols"][sym] = {"error": f"{type(exc).__name__}: {exc}"}
    p = os.path.join(OUT, "results.json")
    json.dump(rep_all, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
    print(f"\nrésultats : {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
