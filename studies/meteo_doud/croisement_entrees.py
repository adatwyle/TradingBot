"""
Croisement des entrées annoncées par Doud contre nos propres barres XAUUSD.

    python studies/meteo_doud/croisement_entrees.py

LA QUESTION
------------
Elle décrit son déclencheur ainsi : le marché va **balayer la liquidité** (prendre
les stops sous le prix), il **rejette**, il **réintègre**, et elle entre sur
l'impulsion (`docs/sources/doudtrading/SYNTHESE_METHODE.md` § 1.3).

Ses points d'entrée sont extraits de ses lives publics, horodatés et validés : le
prix qu'elle annonce à l'oral tombe dans la bougie M5 réelle de l'instant cité
(`_entries_aligned.json`). La question devient donc mesurable :

    ses entrées tombent-elles sur un balayage de liquidité, PLUS SOUVENT
    qu'un instant quelconque de la même session ?

Si oui, son déclencheur est détectable mécaniquement et S019 a un objet.
Si non, ce que nous avons traduit n'est pas ce qu'elle fait.

PARAMÈTRES — FIXÉS AVANT MESURE
--------------------------------
    LOOKBACK_REF   60 barres M1  — l'horizon dont on prend le plus-bas de référence
    WINDOW         30 barres M1  — la fenêtre avant l'entrée où le balayage peut avoir lieu
    WICK_MIN       0,50          — part de mèche basse minimale pour parler de rejet
    HORIZON        60 barres M1  — l'après, pour mesurer MFE/MAE
    N_CONTROL      200 tirages   — témoin par entrée, même heure de session, autres jours
    SEED           20260906      — graine figée

Le témoin est le point central : sur un actif volatil, un balayage se trouve
partout si on le cherche mal. La seule lecture qui compte est **le taux observé
chez elle contre le taux observé au hasard dans la même session**.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (ROOT, os.path.join(ROOT, "app")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.data.source import load_bars  # noqa: E402

LOOKBACK_REF = 60
WINDOW = 30
WICK_MIN = 0.50
HORIZON = 60
N_CONTROL = 200
SEED = 20260906
PIP = 0.01
ALIGNED = os.path.join(ROOT, "docs", "sources", "doudtrading", "_entries_aligned.json")


def sweep_at(bars: pd.DataFrame, i: int) -> dict:
    """Un balayage haussier a-t-il eu lieu dans les WINDOW barres avant i ?

    Balayage = une barre j qui perce le plus-bas des LOOKBACK_REF barres qui la
    précèdent, ET qui referme au-dessus de ce plus-bas (le perçage est rejeté).
    """
    lo = bars["low"].to_numpy()
    hi = bars["high"].to_numpy()
    op = bars["open"].to_numpy()
    cl = bars["close"].to_numpy()
    start = i - WINDOW
    if start - LOOKBACK_REF < 0 or i >= len(bars):
        return {"sweep": None}

    for j in range(start, i + 1):
        ref = lo[j - LOOKBACK_REF:j].min()
        if lo[j] < ref and cl[j] > ref:
            rng = hi[j] - lo[j]
            wick = (min(op[j], cl[j]) - lo[j]) / rng if rng > 0 else 0.0
            return {"sweep": True, "bars_before": i - j,
                    "depth_pips": round((ref - lo[j]) / PIP, 1),
                    "wick": round(float(wick), 2),
                    "rejet": bool(wick >= WICK_MIN)}
    return {"sweep": False}


def forward(bars: pd.DataFrame, i: int, entry: float) -> dict:
    end = min(len(bars), i + 1 + HORIZON)
    win = bars.iloc[i + 1:end]
    if win.empty:
        return {}
    return {"mfe_pips": round(float(win["high"].max() - entry) / PIP, 0),
            "mae_pips": round(float(entry - win["low"].min()) / PIP, 0)}


def main() -> int:
    if not os.path.exists(ALIGNED):
        print("entrées alignées introuvables")
        return 2
    ents = [e for e in json.load(open(ALIGNED, encoding="utf-8")) if e.get("aligne")]
    bars = load_bars("XAUUSD", "M1", days=365 * 2)
    if bars is None:
        print("barres M1 indisponibles")
        return 2
    print(f"{len(ents)} entrées alignées · M1 {bars.index[0]} → {bars.index[-1]} "
          f"({len(bars)} barres)")
    print(f"balayage = perce le plus-bas des {LOOKBACK_REF} barres puis referme "
          f"au-dessus · fenêtre {WINDOW} barres · rejet si mèche ≥ {WICK_MIN:.0%}\n")

    rng = np.random.default_rng(SEED)
    idx = bars.index
    print(f"{'live':12s} {'date/heure':17s} {'prix':>9s} {'balayage':>9s} "
          f"{'il y a':>7s} {'profond':>8s} {'mèche':>6s} {'MFE':>6s} {'MAE':>6s}")
    hits = wicks = 0
    used = []
    for e in ents:
        i = int(idx.searchsorted(pd.Timestamp(e["dt"])))
        if i <= 0 or i >= len(bars):
            continue
        s = sweep_at(bars, i)
        if s["sweep"] is None:
            continue
        f = forward(bars, i, float(e["prix"]))
        used.append((e, s, f, i))
        hits += 1 if s["sweep"] else 0
        wicks += 1 if s.get("rejet") else 0
        print(f"{e['vid'][:11]:12s} {e['dt'][:16]:17s} {e['prix']:9.2f} "
              f"{('OUI' if s['sweep'] else 'non'):>9s} "
              f"{(str(s.get('bars_before','')) + ' b') if s['sweep'] else '':>7s} "
              f"{(str(s.get('depth_pips','')) ) if s['sweep'] else '':>8s} "
              f"{(str(s.get('wick','')) ) if s['sweep'] else '':>6s} "
              f"{f.get('mfe_pips',''):>6} {f.get('mae_pips',''):>6}")

    n = len(used)
    if not n:
        print("aucune entrée exploitable")
        return 0

    # ── Témoin : mêmes heures de session, autres jours ───────────────────────
    hours = sorted({pd.Timestamp(e["dt"]).hour for e, _, _, _ in used})
    pool = np.flatnonzero(np.isin(idx.hour, hours))
    pool = pool[(pool > LOOKBACK_REF + WINDOW + 1) & (pool < len(bars) - HORIZON - 1)]
    draws = rng.choice(pool, size=min(N_CONTROL, len(pool)), replace=False)
    c_sweep = c_wick = 0
    for j in draws:
        s = sweep_at(bars, int(j))
        if s["sweep"] is None:
            continue
        c_sweep += 1 if s["sweep"] else 0
        c_wick += 1 if s.get("rejet") else 0

    print(f"\n{'':-<78}")
    print(f"SES ENTRÉES      balayage {hits}/{n} = {100*hits/n:.0f} %   "
          f"· dont rejet net (mèche ≥ {WICK_MIN:.0%}) {wicks}/{n} = {100*wicks/n:.0f} %")
    print(f"TÉMOIN ALÉATOIRE balayage {c_sweep}/{len(draws)} = {100*c_sweep/len(draws):.0f} %   "
          f"· dont rejet net {c_wick}/{len(draws)} = {100*c_wick/len(draws):.0f} %")
    print(f"{'':-<78}")
    print("Le témoin tire dans les MÊMES heures de session, sur les autres jours.")
    print("Un taux identique signifierait que le balayage est partout, donc qu'il "
          "ne caractérise\nrien — et que notre traduction de son déclencheur est à "
          "revoir.")
    if n < 30:
        print(f"\n[EFFECTIF] {n} entrées. Un écart n'est indicatif qu'au-delà de "
              "~30 observations ;\nce résultat oriente la construction de S019, il "
              "ne la justifie pas à lui seul.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
