"""
Mesure de S024 — « Go Long » (René Balke) sur DAX, NASDAQ, US30 en H1.

    PYTHONIOENCODING=utf-8 python strategies/S024_balke_go_long/backtests/run_wf.py
    S024_SYMBOLS=DAX ...            (sous-ensemble)

N'implémente aucun moteur (R9) : tout passe par `core.backtest.engine.run` et
`core.backtest.anchored_wf`. Les critères sont dans `research/FALSIFICATION.md`,
écrits AVANT ce run.

Cette stratégie est du BÊTA INDICIEL par construction (un achat par jour, sans
filtre). Un R/trade positif ne dit rien seul. L'ordre des sections est donc
celui de la lecture qui décide :

  0. séance réellement observée -> heure d'entrée et nombre de barres de détention
  1. R1 causalité, R5 conformance
  2. ÉTALONS : acheter-et-tenir, puis décomposition jambe intraday / jambe overnight
     calculée directement sur les barres (la thèse de l'auteur, testée de front)
  3. les 6 cellules en plein échantillon, au spread catalogue ET au spread mesuré
  4. walk-forward ancré (deux passes : une par entry_hour_offset — cf. FALSIFICATION)
  5. témoins : bras commun (déclaré non informatif ici) + balayage horaire exhaustif
  6. bras « règles communes » (information seulement, jamais un verdict)
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
from strategies.S024_balke_go_long.strategy import Strategy           # noqa: E402

SYMBOLS = [s for s in os.environ.get("S024_SYMBOLS", "DAX,NASDAQ,US30").split(",") if s]
DAYS = 1855                      # cache mesuré le 2026-09-12 : 2021-08-16 -> 2026-09-11
FREEZE = 10 ** 9                 # cache gelé : MT5 est en ligne, on ne veut pas
                                 # que la fenêtre glisse pendant le run
MIN_TRADES, MAX_DD_R = 20, 40.0  # DD en R : ~1250 trades par instrument, le seuil
                                 # par défaut (12 R) est calibré pour des effectifs
                                 # de quelques dizaines de trades
FIDELITY = {"guard_pct": 0.05, "entry_hour_offset": 0}
GUARDS = [0.03, 0.05, 0.10]
OFFSETS = [0, 1]
OUT = os.path.dirname(os.path.abspath(__file__))

# Bras fidèle : aucune règle commune (doctrine Adrian 2026-09-12).
FAITHFUL = dict(max_positions=1, cooldown_bars=0, cb_losses=999, cb_cooldown_bars=0)
# Bras règles communes : information seulement.
COMMON = dict(max_positions=1, cooldown_bars=2, cb_losses=3, cb_cooldown_bars=24)


class DispositifEnDefaut(Exception):
    """R1 ou R5 en défaut : la mesure ne vaut rien et ne doit pas être publiée.

    Levée par la PORTE du § 1, AVANT toute mesure ; interceptée dans `main()`, qui
    s'arrête alors sans écrire `results.json` — ni pour cet instrument, ni pour les
    autres. Sans cette porte, une fuite de causalité ou une divergence live/backtest
    se transformerait en résultat de recherche publiable. Motif écrit d'avance dans
    research/FALSIFICATION.md § « échec du dispositif, pas de l'hypothèse ».
    """

    def __init__(self, failures: list[str]):
        super().__init__("; ".join(failures))
        self.failures = failures


def rule(c="=", n=104): print(c * n)
def section(t): print(); rule(); print(t); rule()


def head() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"],
                                        cwd=ROOT, text=True).strip()
        return f"{sha}{' (arbre modifié)' if dirty else ''}"
    except Exception:
        return "inconnu"


def cell_label(c: dict) -> str:
    return f"garde {100*c['guard_pct']:4.1f}% · offset {c['entry_hour_offset']}"


def cells() -> list[dict]:
    g = Strategy().manifest().param_grid
    return [{"guard_pct": a, "entry_hour_offset": b}
            for a, b in itertools.product(g["guard_pct"], g["entry_hour_offset"])]


# ─────────────────────────────────────────────────────────────────────────────
# 0. la séance, lue dans les barres — pas supposée
# ─────────────────────────────────────────────────────────────────────────────
def session_profile(bars: pd.DataFrame) -> dict:
    """Journée serveur type : combien de barres, quelles heures, laquelle est la première.

    C'est CE profil qui fixe `start_hour` et `max_hold_bars`. Le lire dans les
    données plutôt que le coder en dur est la seule façon de rendre visible un
    changement de séance chez le courtier.
    """
    h = pd.DataFrame({"day": bars.index.normalize(), "hour": bars.index.hour})
    per_day = h.groupby("day")["hour"].apply(lambda x: tuple(sorted(x)))
    counts = per_day.map(len)
    modal_n = int(counts.mode().iloc[0])
    modal_hours = Counter(per_day[counts == modal_n]).most_common(1)[0][0]
    return {
        "day_bars": modal_n,
        "session_hours": list(modal_hours),
        "start_hour": int(modal_hours[0]),
        "n_days_total": int(len(per_day)),
        "n_days_modal": int((counts == modal_n).sum()),
        "hour_histogram": {int(k): int(v) for k, v in
                           sorted(Counter(counts.tolist()).items())},
    }


def hold_bars(prof: dict, offset: int) -> int:
    """Barres de détention pour sortir au close de la DERNIÈRE barre de la séance.

    Entrée au close de la barre d'indice `offset` ; sortie au close de la barre
    d'indice `day_bars - 1`. Le moteur ferme `max_hold_bars` barres après
    l'entrée -> k = (day_bars - 1) - offset.
    """
    return prof["day_bars"] - 1 - offset


# ─────────────────────────────────────────────────────────────────────────────
# coût de bord
# ─────────────────────────────────────────────────────────────────────────────
def spec_with(spec: InstrumentSpec, spread_pips: float) -> InstrumentSpec:
    """Même instrument, autre spread.

    `max_spread_pips` est RELEVÉ délibérément : le moteur refuse d'ouvrir quand
    `spread_pips > max_spread_pips`, et le plafond du catalogue est calibré sur le
    spread du catalogue. Sur DAX, le spread mesuré (23 pips) dépasse le plafond
    catalogue (20) — sans ce relèvement le moteur refuserait TOUS les trades et
    la colonne « spread mesuré » serait silencieusement vide. Le relèvement est
    donc nécessaire, mais il neutralise de fait le garde-fou anti-news : à
    spread mesuré, aucune barre n'est jamais écartée pour spread excessif.
    Déclaré dans research/VERDICT.md § Réserves. `slippage_pips` est conservé tel
    quel (et vaut 0 dans le catalogue — autre réserve, celle-là non corrigeable ici).
    """
    return InstrumentSpec(spec.symbol, pip=spec.pip, spread_pips=spread_pips,
                          max_spread_pips=max(spec.max_spread_pips, spread_pips * 10),
                          pip_value_per_lot=spec.pip_value_per_lot,
                          slippage_pips=spec.slippage_pips)


def measured_spread_pips(bars: pd.DataFrame, spec: InstrumentSpec) -> float | None:
    """Colonne `spread` des barres MT5 (en POINTS de cotation) -> pips du catalogue.

    Médiane sur les 365 derniers jours (régime courant). Nos trois indices ont
    `digits=2`, donc point = 0,01 et pip = 0,1 = 10 points : la division par 10
    est vérifiée contre `docs/data/INDICES_intraday_2026-09-12.md` (DAX 23,
    NASDAQ 12, US30 35 pips).

    Renvoie None plutôt qu'une valeur douteuse : une médiane nulle, négative ou
    NaN signifie que la colonne `spread` n'est pas exploitable sur cette fenêtre
    (et 0 pip, pris au pied de la lettre, produirait un « spread mesuré » GRATUIT,
    c'est-à-dire un résultat plus flatteur que le catalogue, sans le dire).
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


# ─────────────────────────────────────────────────────────────────────────────
# exécution d'une cellule
# ─────────────────────────────────────────────────────────────────────────────
def backtest(cell: dict, bars, spec, symbol, prof, engine_arm=FAITHFUL):
    p = {"start_hour": prof["start_hour"], **cell}
    s = Strategy(p); s._symbol = symbol
    data = s.precompute(bars, p)
    sigs = s.generate_signals(data, p, len(bars))
    ek = dict(engine_arm, max_hold_bars=hold_bars(prof, int(cell["entry_hour_offset"])))
    return sigs, run_engine(sigs, bars, spec, **ek), ek


def _dd(series: np.ndarray) -> float:
    if not len(series):
        return 0.0
    eq = np.cumsum(series)
    return float(np.max(np.maximum.accumulate(eq) - eq))


def trade_pct(t) -> float:
    """Rendement NET d'un trade, en % du prix d'entrée. Le moteur fait foi.

    PIÈGE CORRIGÉ LE 2026-09-12 (revue qualité) — ne JAMAIS écrire
    `(exit_price - entry_price) / entry_price` : le moteur replie le coût de bord
    d'ENTRÉE dans `entry_price`, mais stocke `exit_price` BRUT et ne déduit le coût
    de SORTIE que dans `pnl_r`. Cette formule-là ne payait donc que la MOITIÉ du
    spread. Sur ce dossier elle surestimait le total de 4 à 9 points de % selon
    l'instrument. On passe par `pnl_r`, net des deux côtés :

        pnl_r = (gross - edge_cost) / risk    =>    gross_net = pnl_r * risk

    `risk_distance` et `entry_price` sont tous deux post-coût : la conversion est
    exacte, et le moteur reste la source unique de vérité (R9).
    """
    return 100.0 * t.pnl_r * t.risk_distance / t.entry_price


def pct_series(trades) -> np.ndarray:
    return (np.array([trade_pct(t) for t in trades], dtype=float)
            if trades else np.array([], dtype=float))


def stats(res, n_signals: int | None = None) -> dict:
    """Résumé moteur + les deux lectures propres à cette stratégie : le % du prix
    d'entrée (seule unité comparable entre gardes différentes) et l'heure de sortie."""
    s = dict(res.summary())
    tr = res.trades
    s["r_per_trade"] = round(res.total_r / len(tr), 4) if tr else None
    pct = pct_series(tr)
    s["total_pct"] = round(float(pct.sum()), 3) if len(pct) else None
    s["pct_per_trade"] = round(float(pct.mean()), 5) if len(pct) else None
    s["max_dd_pct"] = round(_dd(pct), 2) if len(pct) else None
    s["guard_hits"] = sum(1 for t in tr if t.exit_reason == "SL")
    s["exit_reasons"] = dict(Counter(t.exit_reason for t in tr))
    s["exit_hours"] = {int(k): int(v) for k, v in sorted(
        Counter(pd.Timestamp(t.exit_time).hour for t in tr if t.exit_time).items())}
    s["exits_next_day"] = sum(
        1 for t in tr if t.exit_time and
        pd.Timestamp(t.exit_time).normalize() != pd.Timestamp(t.entry_time).normalize())
    s["bars_held"] = dict(Counter(t.bars_held for t in tr))
    if n_signals is not None:
        s["n_signals"] = n_signals
        s["signals_not_executed"] = n_signals - len(tr)
    return s


def dd_episode(trades) -> dict | None:
    """Le pire épisode de drawdown en % du prix d'entrée, AVEC SES DATES.

    Sans les dates, on ne peut pas vérifier le repère de fidélité F4 (le
    drawdown du printemps 2025, annonces de droits de douane américains) : il
    est invisible dans un total annuel, puisque 2025 finit positive partout.
    """
    tr = sorted(trades, key=lambda t: pd.Timestamp(t.entry_time))
    if not tr:
        return None
    pct = pct_series(tr)
    eq = np.cumsum(pct)
    peak = np.maximum.accumulate(eq)
    j = int(np.argmax(peak - eq))
    i = int(np.argmax(eq[:j + 1]))
    return {"depth_pct": round(float(peak[j] - eq[j]), 2),
            "from": str(pd.Timestamp(tr[i].entry_time).date()),
            "trough": str(pd.Timestamp(tr[j].exit_time or tr[j].entry_time).date()),
            "n_trades": j - i}


def by_year(res) -> dict:
    """Par année : R, % et DRAWDOWN INTRA-ANNÉE.

    Le drawdown par année n'est pas décoratif : le repère de fidélité F4 (le
    creux du printemps 2025, droits de douane américains) est invisible dans un
    simple total annuel — 2025 finit positive sur les trois indices.
    """
    r, p, c = defaultdict(float), defaultdict(float), defaultdict(int)
    per_year = defaultdict(list)
    for t in sorted(res.trades, key=lambda t: pd.Timestamp(t.entry_time)):
        y = pd.Timestamp(t.entry_time).year
        r[y] += t.pnl_r
        p[y] += trade_pct(t)
        c[y] += 1
        per_year[y].append(t)
    out = {}
    for y in sorted(r):
        ep = dd_episode(per_year[y]) or {}
        out[str(y)] = {"r": round(r[y], 1), "pct": round(p[y], 2), "n": c[y],
                       "dd_pct": ep.get("depth_pct"), "dd_from": ep.get("from"),
                       "dd_trough": ep.get("trough")}
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 2. étalons — sans moteur, directement sur les barres
# ─────────────────────────────────────────────────────────────────────────────
def entry_positions(bars: pd.DataFrame, prof: dict, offset: int = 0) -> np.ndarray:
    """Indices des barres de signal — le calendrier de la règle, sans le moteur."""
    p = {"start_hour": prof["start_hour"], "entry_hour_offset": offset,
         "guard_pct": 0.05}
    s = Strategy(p)
    return np.flatnonzero(s.precompute(bars, p)["entry_bar"].to_numpy() > 0.5)


def legs(bars: pd.DataFrame, prof: dict, offset: int = 0,
         positions: np.ndarray | None = None, drop_overlaps: bool = True) -> dict:
    """Décompose l'indice en jambe INTRADAY (séance) et jambe OVERNIGHT (le reste).

    Sa thèse : la jambe intraday porte le rendement, la jambe overnight porte le
    risque de gap et le swap. On la mesure de front, sans stratégie, sans coût.

        intraday_k  = close(sortie_k)  / close(entrée_k) − 1
        overnight_k = close(entrée_k+1)/ close(sortie_k)  − 1

    PAS UN CONTRÔLE (corrigé le 2026-09-12, revue qualité) : le produit
    Π(1+intra)·Π(1+over) vaut le trajet total par simple télescopage des prix. Il
    tiendrait même sur un ordre de journées tiré au hasard. Il est donc publié
    comme identité algébrique, jamais comme vérification — un « contrôle » qui ne
    peut pas échouer ne contrôle rien.

    CHEVAUCHEMENTS. Quand une journée est tronquée (férié, décalage d'heure d'été),
    la sortie de la journée k peut tomber APRÈS l'entrée de la journée k+1. La
    jambe overnight y serait alors calculée sur un intervalle de temps NÉGATIF, et
    le gap de week-end serait crédité à la jambe intraday. `drop_overlaps` écarte
    ces journées-là (chevauchement STRICT `sortie_k > entrée_{k+1}`). Les égalités
    `sortie_k == entrée_{k+1}` sont conservées : elles décrivent un enchaînement
    sans trou, leur overnight vaut exactement 0, et les écarter supprimerait des
    journées parfaitement valides. Les deux effectifs sont publiés.

    `positions` permet de restreindre l'étalon aux journées RÉELLEMENT tradées par
    la stratégie — les seules comparables, puisque les journées sautées ne sont
    pas tirées au hasard.
    """
    close = bars["close"].to_numpy(dtype=float)
    n = len(close)
    k = hold_bars(prof, offset)

    e = entry_positions(bars, prof, offset) if positions is None else np.asarray(
        sorted(set(int(v) for v in positions)), dtype=int)
    e = e[e + k < n]
    if len(e) < 2:
        return {"error": "pas assez de jours exploitables"}

    x = e + k
    n_strict = int(np.sum(x[:-1] > e[1:]))
    n_ties = int(np.sum(x[:-1] == e[1:]))
    if drop_overlaps and n_strict:
        keep = np.ones(len(e), dtype=bool)
        keep[:-1] &= ~(x[:-1] > e[1:])
        e, x = e[keep], x[keep]
        if len(e) < 2:
            return {"error": "pas assez de jours après retrait des chevauchements"}

    years = pd.DatetimeIndex(bars.index[e]).year.to_numpy()
    intra = close[x] / close[e] - 1.0
    over = close[e[1:]] / close[x[:-1]] - 1.0          # une de moins, par construction

    def pack(v, yrs):
        cum = np.cumprod(1.0 + v)
        per = defaultdict(float)
        for y, r in zip(yrs, v):
            per[int(y)] += 100.0 * r
        return {
            "n": int(len(v)),
            "sum_pct": round(100.0 * float(v.sum()), 2),
            "compounded_pct": round(100.0 * (float(cum[-1]) - 1.0), 2),
            "max_dd_pct_sum": round(_dd(100.0 * v), 2),
            "mean_pct": round(100.0 * float(v.mean()), 5),
            "by_year": {str(y): round(per[y], 2) for y in sorted(per)},
        }

    first, last = int(e[0]), int(x[-1])
    return {
        "n_days": int(len(e)),
        "hold_bars": k,
        "drop_overlaps": bool(drop_overlaps),
        "overlaps_strict": n_strict,       # sortie_k > entrée_{k+1} : temps négatif
        "overlaps_ties": n_ties,           # sortie_k == entrée_{k+1} : overnight nul, gardées
        "entry_hour": int(pd.Timestamp(bars.index[e[0]]).hour),
        "exit_hour_modal": int(Counter(pd.DatetimeIndex(bars.index[x]).hour)
                               .most_common(1)[0][0]),
        "intraday": pack(intra, years),
        "overnight": pack(over, years[1:]),
        "buy_hold_pct_full": round(100.0 * (close[-1] / close[0] - 1.0), 2),
        "buy_hold_pct_span": round(100.0 * (close[last] / close[first] - 1.0), 2),
        # Identité algébrique (télescopage), PAS un contrôle : elle tient quel que
        # soit l'ordre des journées. Publiée pour lecture, jamais comme garantie.
        "identity_algebraic_pct": round(
            100.0 * (float(np.prod(1.0 + intra) * np.prod(1.0 + over)) - 1.0), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. témoin c2 — balayage horaire exhaustif (l'entrée aléatoire, énumérée)
# ─────────────────────────────────────────────────────────────────────────────
def hour_sweep(bars, spec, symbol, prof, guard: float) -> dict:
    """Même règle, même garde, MÊME NOMBRE DE BARRES DE DÉTENTION, à chaque heure.

    C'est l'énumération complète de « et si on entrait à une autre heure ? » —
    l'entrée aléatoire du bras témoin, énumérée au lieu d'être tirée, donc
    strictement plus forte. Le bras témoin commun ne peut pas la donner ici
    (il recopie le filtre horaire de la stratégie — cf. FALSIFICATION §c1).

    CE QUE CE BALAYAGE NE SÉPARE PAS, et qu'il faut lire avec :
    à nombre de barres constant, une entrée plus tardive fait déborder la
    fenêtre hors séance. La colonne `duree_horloge_h` chiffre ce débordement
    (durée médiane entre entrée et sortie en heures d'horloge) : quand elle
    dépasse le nombre de barres, la fenêtre porte de l'overnight. Sur un indice
    24/24 l'écart reste petit (coupure quotidienne d'une heure + week-ends) ;
    sur le DAX, dont la séance ne fait que 14 h sur 24, il est massif — et le
    balayage y mesure alors « séance contre overnight » autant que « heure
    d'entrée ». Dit ici, pas découvert après coup.
    """
    k = hold_bars(prof, 0)
    rows = []
    for h in prof["session_hours"]:
        p = {"start_hour": int(h), "entry_hour_offset": 0, "guard_pct": guard}
        s = Strategy(p); s._symbol = symbol
        sigs = s.generate_signals(s.precompute(bars, p), p, len(bars))
        res = run_engine(sigs, bars, spec, **dict(FAITHFUL, max_hold_bars=k))
        pct = float(pct_series(res.trades).sum())
        span = [(pd.Timestamp(t.exit_time) - pd.Timestamp(t.entry_time)).total_seconds() / 3600.0
                for t in res.trades if t.exit_time]
        rows.append({"hour": int(h), "n": res.n_trades,
                     "total_r": round(res.total_r, 1), "total_pct": round(pct, 2),
                     "duree_horloge_h": round(float(np.median(span)), 1) if span else None})
    ref = prof["start_hour"]
    me = next(r for r in rows if r["hour"] == ref)
    others = [r for r in rows if r["hour"] != ref]
    # CONVENTION, à citer avec le chiffre : rang parmi les AUTRES heures (la
    # référence est exclue de sa propre population nulle). La convention « toutes
    # heures », celle de ControlArm.percentile, divise par le total et donnerait
    # un chiffre plus bas — les deux sont publiés pour qu'aucune lecture ne
    # dépende du choix.
    pctile = (100.0 * sum(1 for r in others if r["total_pct"] < me["total_pct"])
              / len(others)) if others else float("nan")
    pctile_all = 100.0 * (sum(1 for r in rows if r["total_pct"] < me["total_pct"])
                          + 0.5 * sum(1 for r in rows if r["total_pct"] == me["total_pct"])) / len(rows)
    return {"rows": rows, "reference_hour": ref, "reference_pct": me["total_pct"],
            "percentile": round(pctile, 1),
            "percentile_convention": "rang parmi les autres heures (référence exclue)",
            "percentile_toutes_heures": round(pctile_all, 1),
            "n_hours": len(rows)}


# ─────────────────────────────────────────────────────────────────────────────
# un instrument, de bout en bout
# ─────────────────────────────────────────────────────────────────────────────
def measure(symbol: str, out: dict) -> None:
    bars = load_bars(symbol, "H1", days=DAYS, max_age_hours=FREEZE)
    if bars is None or len(bars) < 5000:
        print(f"\n{symbol} : barres indisponibles")
        out[symbol] = {"error": "barres indisponibles"}
        return

    prof = session_profile(bars)
    spec_cat = get_spec(symbol)
    sp_meas = measured_spread_pips(bars, spec_cat)
    spec_meas = spec_with(spec_cat, sp_meas) if sp_meas else spec_cat
    rep: dict = {"symbol": symbol, "timeframe": "H1", "bars": len(bars),
                 "from": str(bars.index[0]), "to": str(bars.index[-1]),
                 "session": prof,
                 "spread_catalogue_pips": spec_cat.spread_pips,
                 "spread_mesure_pips": sp_meas}

    section(f"{symbol} H1 — {len(bars)} barres · {bars.index[0]} → {bars.index[-1]}")

    # ── 0. séance
    sh = prof["start_hour"]
    hrs = prof["session_hours"]
    print(f"0. séance : journée type = {prof['day_bars']} barres, heures "
          f"{hrs[0]:02d}:00 → {hrs[-1]:02d}:00 · {prof['n_days_modal']}/{prof['n_days_total']} "
          f"jours au profil type")
    print(f"   entrée = close de la barre {sh:02d}:00 (soit {(sh+1) % 24:02d}:00 serveur) · "
          f"détention offset 0 = {hold_bars(prof,0)} barres → sortie au close de la barre "
          f"{hrs[-1]:02d}:00 (soit {(hrs[-1]+1) % 24:02d}:00 serveur)")
    print(f"   coût : spread catalogue {spec_cat.spread_pips:.1f} pips"
          + (f" · mesuré {sp_meas:.1f} pips (×{sp_meas/spec_cat.spread_pips:.2f})"
             if sp_meas else " · mesuré indisponible"))

    # ── 1. R1 / R5 — PORTE : rien n'est mesuré tant qu'elle n'est pas franchie
    ok_r1 = ok_r5 = True
    failures: list[str] = []
    for c in (FIDELITY, {"guard_pct": 0.10, "entry_hour_offset": 1}):
        p = {"start_hour": sh, **c}
        s = Strategy(p); s._symbol = symbol
        r1 = causality_check(s, bars, symbol)
        r5 = conformance_check(s, bars, symbol)
        ok_r1 &= r1.ok; ok_r5 &= r5.ok
        if not r1.ok:
            failures.append(f"{symbol} · {cell_label(c)} : R1 EN DÉFAUT (fuite de causalité)")
        if not r5.ok:
            failures.append(f"{symbol} · {cell_label(c)} : R5 EN DÉFAUT (divergence live/backtest)")
        print(f"1. {cell_label(c):24s} R1 {'OK' if r1.ok else 'FUITE'} · "
              f"R5 {'OK' if r5.ok else 'DIVERGENCE'}")
    rep["r1_ok"], rep["r5_ok"] = bool(ok_r1), bool(ok_r5)
    if failures:
        # Mesurer après ça, ce serait publier le bug du dispositif comme un
        # résultat de recherche. On s'arrête AVANT toute mesure et toute écriture.
        out[symbol] = rep
        raise DispositifEnDefaut(failures)

    # ── 2. étalons
    # Les journées effectivement tradées sont la SEULE population comparable à la
    # stratégie : celles qu'elle saute (position de la veille encore ouverte) ne
    # sont pas tirées au hasard, ce sont des lendemains de séance anormale. Les
    # trois variantes sont publiées côte à côte pour que l'écart soit lisible.
    _, res_fid_bench, _ = backtest(FIDELITY, bars, spec_meas, symbol, prof)
    traded = np.array([bars.index.get_loc(pd.Timestamp(t.entry_time))
                       for t in res_fid_bench.trades], dtype=int)
    variants = {
        "toutes journées": legs(bars, prof, offset=0, drop_overlaps=False),
        "sans chevauchement": legs(bars, prof, offset=0, drop_overlaps=True),
        "journées tradées": legs(bars, prof, offset=0, positions=traded,
                                 drop_overlaps=True),
    }
    lg = variants["journées tradées"]          # l'étalon de référence du verdict
    rep["benchmarks"] = {"reference": "journées tradées", "variants": variants}

    raw = variants["toutes journées"]
    print(f"\n2. ÉTALONS (sans moteur, sans coût)")
    print(f"   acheter-et-tenir, période complète : {raw['buy_hold_pct_full']:+8.2f} %")
    print(f"   chevauchements sortie_k ≥ entrée_k+1 : {raw['overlaps_strict']} stricts "
          f"(temps négatif — écartés dans les variantes suivantes) + "
          f"{raw['overlaps_ties']} égalités (overnight nul, conservées)")
    for vname, v in variants.items():
        if "error" in v:
            print(f"   {vname:19s} : {v['error']}")
            continue
        mark = "  <<< étalon du verdict" if vname == "journées tradées" else ""
        print(f"   — {vname} ({v['n_days']} journées){mark}")
        for name in ("intraday", "overnight"):
            j = v[name]
            print(f"       jambe {name:9s} somme {j['sum_pct']:+8.2f} % · composée "
                  f"{j['compounded_pct']:+9.2f} % · moyenne {j['mean_pct']:+.4f} %/jour · "
                  f"DD max (somme) {j['max_dd_pct_sum']:6.2f} pts")
            print(f"           par année : " + "  ".join(
                f"{y[2:]}:{v2:+.1f}" for y, v2 in j["by_year"].items()))
    print(f"   identité algébrique (télescopage, PAS un contrôle — elle tient même sur "
          f"un ordre de journées quelconque) : {lg['identity_algebraic_pct']:+.2f} % "
          f"vs trajet {lg['buy_hold_pct_span']:+.2f} %")

    # ── 3. plein échantillon, 6 cellules, deux spreads
    print(f"\n3. PLEIN ÉCHANTILLON — 6 cellules")
    print(f"   {'cellule':24s} {'n':>5s} {'sig':>5s} {'R':>9s} {'R/tr':>7s} "
          f"{'%tot':>8s} {'%/tr':>8s} {'WR%':>5s} {'PF':>5s} {'DDr':>7s} {'DD%':>6s} "
          f"{'garde':>5s} {'J+1':>4s}")
    rows = []
    for c in cells():
        sigs, res, ek = backtest(c, bars, spec_cat, symbol, prof)
        st = stats(res, n_signals=len(sigs))
        _, res_m, _ = backtest(c, bars, spec_meas, symbol, prof)
        stm = stats(res_m)
        rows.append({"cell": c, "label": cell_label(c), "engine_kwargs": ek,
                     "catalogue": st, "mesure": stm, "by_year": by_year(res_m)})
        print(f"   {cell_label(c):24s} {st['n_trades']:5d} {len(sigs):5d} "
              f"{st['total_r']:9.1f} {(st['r_per_trade'] or 0):7.3f} "
              f"{(st['total_pct'] or 0):8.2f} {(st['pct_per_trade'] or 0):8.4f} "
              f"{(st['win_rate'] or 0):5.1f} {(st['profit_factor'] or 0):5.2f} "
              f"{st['max_dd_r']:7.1f} {(st['max_dd_pct'] or 0):6.2f} "
              f"{st['guard_hits']:5d} {st['exits_next_day']:4d}")
    print(f"   (au spread MESURÉ)")
    for r in rows:
        m = r["mesure"]
        print(f"   {r['label']:24s} {m['n_trades']:5d} {'':5s} {m['total_r']:9.1f} "
              f"{(m['r_per_trade'] or 0):7.3f} {(m['total_pct'] or 0):8.2f} "
              f"{(m['pct_per_trade'] or 0):8.4f} {(m['win_rate'] or 0):5.1f} "
              f"{(m['profit_factor'] or 0):5.2f} {m['max_dd_r']:7.1f} "
              f"{(m['max_dd_pct'] or 0):6.2f} {m['guard_hits']:5d} {m['exits_next_day']:4d}")
    rep["full_sample"] = rows

    fid = next(r for r in rows
               if r["cell"]["guard_pct"] == FIDELITY["guard_pct"]
               and r["cell"]["entry_hour_offset"] == FIDELITY["entry_hour_offset"])

    # heures de sortie de la cellule de fidélité — l'approximation, mesurée
    eh = fid["mesure"]["exit_hours"] or fid["catalogue"]["exit_hours"]
    tot = sum(eh.values())
    print(f"\n   heures de sortie (cellule de fidélité) : " + "  ".join(
        f"{h:02d}:00={100*v/tot:.1f}%" for h, v in sorted(eh.items(), key=lambda x: -x[1])[:5]))
    fc = fid["catalogue"]
    print(f"   sorties le lendemain : {fc['exits_next_day']} / {fc['n_trades']} · "
          f"jours sautés (position de la veille encore ouverte) : "
          f"{fc['signals_not_executed']} / {fc['n_signals']} "
          f"({100*fc['signals_not_executed']/max(1,fc['n_signals']):.1f} %)")
    print(f"     [le moteur les impute à skipped_cooldown={fc['skipped_cooldown']} et non à "
          f"skipped_open={fc['skipped_open']} : avec cooldown_bars=0 le test de "
          f"refroidissement est atteint le premier — même cause, autre compteur]")
    print(f"   par année (spread mesuré) : " + "  ".join(
        f"{y[2:]}:{v['pct']:+.1f}%/{v['n']}" for y, v in fid["by_year"].items()))
    print(f"   drawdown intra-année      : " + "  ".join(
        f"{y[2:]}:-{v['dd_pct']:.1f}" for y, v in fid["by_year"].items()))
    print(f"   creux de chaque année     : " + "  ".join(
        f"{y[2:]}:{v['dd_from']}→{v['dd_trough']}" for y, v in fid["by_year"].items()))
    _, res_fid_m, _ = backtest(fid["cell"], bars, spec_meas, symbol, prof)
    ep = dd_episode(res_fid_m.trades)
    fid["dd_episode"] = ep
    if ep:
        print(f"   pire drawdown (cumul des % , spread mesuré) : -{ep['depth_pct']:.2f} points, "
              f"du {ep['from']} au {ep['trough']} ({ep['n_trades']} trades)")

    # ── 4. walk-forward, une passe par offset (max_hold_bars en dépend)
    print(f"\n4. WALK-FORWARD ANCRÉ — deux passes (offset 0 puis 1), 3 cellules chacune")
    rep["wf"] = {}
    for off in OFFSETS:
        base = {"start_hour": sh, "entry_hour_offset": off, "guard_pct": GUARDS[1]}
        s = Strategy(base); s._symbol = symbol
        wf = run_walk_forward(
            s, bars, spec_meas,
            param_grid={"guard_pct": GUARDS, "entry_hour_offset": [off]},
            min_trades=MIN_TRADES, max_dd_r=MAX_DD_R, verbose=False,
            engine_kwargs=dict(FAITHFUL, max_hold_bars=hold_bars(prof, off)))
        st = wf.strict()
        print(f"   offset {off} · détention {hold_bars(prof, off)} barres · "
              f"STRICT {len(st)}/{wf.n_configs} · TIER1 {len(wf.tier1())}/{wf.n_configs}")
        for r in sorted(wf.results, key=lambda r: -r.avg_oos):
            print(f"      {r.label:34s} oos moy {r.avg_oos:+8.2f} R · "
                  f"{r.total_test_trades:4d} trades hors éch. · "
                  f"fenêtres {' '.join(f'{v:+.2f}' for v in r.oos_series)}"
                  f"{'  [STRICT]' if r.strict_pass else ''}")
        rep["wf"][f"offset_{off}"] = {
            "n_configs": wf.n_configs, "hold_bars": hold_bars(prof, off),
            "strict": [r.label for r in st],
            "results": [{"label": r.label, "avg_oos": round(r.avg_oos, 3),
                         "oos_trades": r.total_test_trades,
                         "oos_series": [round(v, 2) for v in r.oos_series],
                         "strict": bool(r.strict_pass)} for r in wf.results]}

    # ── 5. témoins
    print(f"\n5. TÉMOINS")
    _, res_fid, ek_fid = backtest(fid["cell"], bars, spec_meas, symbol, prof)
    ca = control_arm(bars, spec_meas, res_fid.trades, res_fid.total_r,
                     engine_kwargs=ek_fid)
    if ca is not None:
        print(f"   (c1) bras commun — {ca.line()}")
        print(f"        RÉSERVE ÉCRITE D'AVANCE : la stratégie n'occupe qu'une heure sur "
              f"{len(prof['session_hours'])}, le module recopie donc ce filtre horaire au "
              f"témoin. Il ne mesure PAS le timing ici. Publié pour comparabilité (R9).")
        rep["control_common"] = {"percentile": round(ca.percentile, 1),
                                 "null_median_r": round(ca.null_median, 2),
                                 "n_trades_ref": ca.n_trades_ref,
                                 "median_draw_trades": ca.median_draw_trades,
                                 "effectif_ok": bool(ca.effectif_ok),
                                 "informatif": False,
                                 "raison": "filtre horaire recopié par le module"}
    else:
        rep["control_common"] = None
        print("   (c1) bras commun : gabarit impossible")

    hs = hour_sweep(bars, spec_meas, symbol, prof, FIDELITY["guard_pct"])
    rep["hour_sweep"] = hs
    print(f"   (c2) balayage horaire — {hs['n_hours']} heures de séance, même garde, "
          f"même détention ({hold_bars(prof,0)} barres), spread mesuré")
    ordered = sorted(hs["rows"], key=lambda r: -r["total_pct"])
    print(f"        (durée horloge médiane > {hold_bars(prof,0)} h = la fenêtre déborde "
          f"hors séance et porte de l'overnight)")
    for r in ordered:
        mark = "  <-- heure de fidélité" if r["hour"] == hs["reference_hour"] else ""
        print(f"        {r['hour']:02d}:00  n={r['n']:5d}  R={r['total_r']:9.1f}  "
              f"%={r['total_pct']:+8.2f}  durée {r['duree_horloge_h']:5.1f} h{mark}")
    print(f"        PERCENTILE DE L'HEURE DE FIDÉLITÉ : {hs['percentile']:.1f} "
          f"(rang {1+[r['hour'] for r in ordered].index(hs['reference_hour'])}"
          f"/{hs['n_hours']}) — convention : rang parmi les AUTRES heures.")
    print(f"        Convention « toutes heures » (celle de ControlArm.percentile) : "
          f"{hs['percentile_toutes_heures']:.1f}. Les deux sont publiées pour qu'aucune "
          f"lecture ne dépende du choix de convention.")

    # ── 6. bras règles communes
    _, res_com, ek_com = backtest(fid["cell"], bars, spec_meas, symbol, prof,
                                  engine_arm=COMMON)
    stc = stats(res_com)
    rep["common_rules_arm"] = {"engine_kwargs": ek_com, **stc}
    f = fid["mesure"]
    print(f"\n6. BRAS RÈGLES COMMUNES (cooldown 2, coupe-circuit 3/24) — information seulement")
    print(f"   fidèle   n={f['n_trades']:5d}  R={f['total_r']:9.1f}  %={f['total_pct']:+8.2f}")
    print(f"   communes n={stc['n_trades']:5d}  R={stc['total_r']:9.1f}  "
          f"%={stc['total_pct']:+8.2f}  · refusés par cooldown/coupe-circuit : "
          f"{stc['skipped_cooldown']}")
    print(f"   coût des règles communes : {(stc['total_pct'] or 0) - (f['total_pct'] or 0):+.2f} "
          f"points de % et {stc['n_trades'] - f['n_trades']:+d} trades")

    out[symbol] = rep


def main() -> int:
    rule()
    print(f"S024 — GO LONG (René Balke) · dépôt {head()}")
    rule()
    print("Achat d'indice quotidien à heure fixe, clôture le soir · 6 cellules · "
          "walk-forward ancré 4 fenêtres")
    print("Étalons : acheter-et-tenir, jambe intraday vs jambe overnight, balayage horaire")
    print("Critères écrits AVANT : research/FALSIFICATION.md")
    print(f"Données : cache gelé 1855 jours (2021-08-16 → 2026-09-11), heure SERVEUR broker")

    out: dict = {"commit": head(), "run_utc": str(pd.Timestamp.utcnow()), "symbols": {}}
    broken: list[str] = []
    for sym in SYMBOLS:
        try:
            measure(sym, out["symbols"])
        except DispositifEnDefaut as exc:
            # La PORTE du § 1 a sauté. Ce n'est pas « un instrument cassé parmi
            # d'autres » : c'est la mesure elle-même qui ne vaut rien. Aucun
            # results.json n'est écrit — ni pour cet instrument, ni pour les autres.
            section("ARRÊT — DISPOSITIF EN DÉFAUT, AUCUN RÉSULTAT PUBLIÉ")
            for f in exc.failures:
                print(f"   {f}")
            print("\n   Corriger puis remesurer. Aucun results.json écrit "
                  "(research/FALSIFICATION.md § « échec du dispositif, pas de "
                  "l'hypothèse »).")
            return 2
        except Exception as exc:          # un instrument cassé ne cache pas les autres
            import traceback
            print(f"\n{sym} : ERREUR {type(exc).__name__}: {exc}")
            traceback.print_exc()
            out["symbols"][sym] = {"error": f"{type(exc).__name__}: {exc}"}
            broken.append(sym)

    p = os.path.join(OUT, "results.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nrésultats : {p}")
    if broken:
        # Un run partiel ne doit pas passer pour un run réussi : le code de sortie
        # est la seule chose que verra un appelant automatisé.
        print(f"\nATTENTION — instrument(s) en erreur : {', '.join(broken)}. "
              f"Résultats partiels, code de sortie non nul.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
