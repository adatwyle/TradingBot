"""
L'ÉCART DE SHARPE EST-IL UN RÉSULTAT OU DU BRUIT ?
===================================================

Le moteur conclut « bat toutes les références » parce que le Sharpe de la
stratégie (0,87) dépasse celui de l'équipondéré naïf (0,82). L'écart vaut 0,05.

`docs/METHODOLOGY.md` §6 impose de rapporter l'effectif et de comparer au
hasard avant de traiter un écart comme un résultat. Un Sharpe estimé sur 7,8 ans
porte une incertitude importante, et 0,05 pourrait tenir entièrement dedans.

MÉTHODE
-------
1. Erreur-type analytique du Sharpe (Lo, 2002) :
       SE(Sh) ~ sqrt( (1 + Sh^2 / 2) / T_years )
2. Bootstrap par blocs sur la DIFFÉRENCE de Sharpe entre la stratégie et le
   naïf. Les deux séries partagent les mêmes actifs et sont fortement
   corrélées : la différence est bien mieux estimée que chaque terme isolé, et
   c'est elle qui nous intéresse. Blocs de 21 jours pour préserver
   l'autocorrélation et les grappes de volatilité.

Le bootstrap répond à la seule question qui compte : si l'on rejouait
l'histoire, à quelle fréquence la stratégie afficherait-elle un Sharpe
supérieur au naïf ?

USAGE
-----
    python -m strategies.s07_ionita_gaussian.significance
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.allocation_engine import run_allocation
from strategies.s07_ionita_gaussian.run_backtest import (
    load_universe, make_specs, UNIVERSE_CRYPTO,
)
from strategies.s07_ionita_gaussian.strategy import Strategy

PPY = 365.0
BLOCK = 21
N_BOOT = 5000
SEED = 12345


def _sharpe(r: np.ndarray) -> float:
    sd = r.std()
    return float(r.mean() / sd * np.sqrt(PPY)) if sd > 1e-12 else 0.0


def run() -> str:
    L = []
    L.append("=" * 78)
    L.append("SIGNIFICATIVITÉ DE L'ÉCART DE SHARPE")
    L.append("=" * 78)

    bars = load_universe(UNIVERSE_CRYPTO)
    n = len(next(iter(bars.values())))

    strat = Strategy(universe=UNIVERSE_CRYPTO)
    p = dict(strat.params)
    p["weight_mode"] = "normalized"
    p["enable_shorts"] = False
    data = strat.precompute(bars, p)
    allocs = strat.generate_allocations(data, p, n)
    res = run_allocation(allocs, bars, make_specs(UNIVERSE_CRYPTO), end_idx=n,
                         periods_per_year=PPY)

    r_strat = res.equity.pct_change().fillna(0.0).to_numpy()

    opens = pd.DataFrame({s: bars[s]["open"] for s in sorted(bars)})
    rets = opens.pct_change().fillna(0.0)
    r_naive = (rets * (1.0 / rets.shape[1])).sum(axis=1).to_numpy()

    m = min(len(r_strat), len(r_naive))
    r_strat, r_naive = r_strat[:m], r_naive[:m]
    years = m / PPY

    sh_s, sh_n = _sharpe(r_strat), _sharpe(r_naive)
    diff = sh_s - sh_n

    L.append(f"  {m} observations quotidiennes ({years:.1f} ans)")
    L.append("")
    L.append(f"  Sharpe stratégie          {sh_s:>7.3f}")
    L.append(f"  Sharpe naïf équipondéré   {sh_n:>7.3f}")
    L.append(f"  écart                     {diff:>+7.3f}")
    L.append("")

    se_s = np.sqrt((1 + sh_s ** 2 / 2) / years)
    se_n = np.sqrt((1 + sh_n ** 2 / 2) / years)
    L.append("  Erreur-type analytique (Lo 2002), chaque Sharpe pris isolément :")
    L.append(f"    stratégie  {sh_s:.3f} +/- {se_s:.3f}   "
             f"IC95 [{sh_s - 1.96 * se_s:+.2f} ; {sh_s + 1.96 * se_s:+.2f}]")
    L.append(f"    naïf       {sh_n:.3f} +/- {se_n:.3f}   "
             f"IC95 [{sh_n - 1.96 * se_n:+.2f} ; {sh_n + 1.96 * se_n:+.2f}]")
    L.append("    Les deux intervalles se recouvrent presque entièrement.")
    L.append("")

    rng = np.random.default_rng(SEED)
    nb = int(np.ceil(m / BLOCK))
    diffs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        starts = rng.integers(0, m - BLOCK, size=nb)
        idx = np.concatenate([np.arange(s, s + BLOCK) for s in starts])[:m]
        diffs[b] = _sharpe(r_strat[idx]) - _sharpe(r_naive[idx])

    lo, hi = np.percentile(diffs, [2.5, 97.5])
    p_le0 = float((diffs <= 0).mean())
    L.append(f"  Bootstrap par blocs ({N_BOOT} tirages, blocs de {BLOCK} jours) "
             f"sur la DIFFÉRENCE :")
    L.append(f"    écart moyen        {diffs.mean():+.3f}")
    L.append(f"    IC95 de l'écart    [{lo:+.3f} ; {hi:+.3f}]")
    L.append(f"    P(écart <= 0)      {p_le0:.3f}")
    L.append("")

    if lo <= 0.0 <= hi:
        L.append("  CONCLUSION : l'intervalle de confiance de l'écart CONTIENT ZÉRO.")
        L.append("  La supériorité de Sharpe n'est pas distinguable du bruit. Le")
        L.append("  « bat toutes les références » du moteur repose sur un écart que")
        L.append("  cet échantillon ne permet pas d'établir.")
    else:
        L.append("  CONCLUSION : l'écart exclut zéro à 95 %. Il est statistiquement")
        L.append("  établi sur cet échantillon.")

    L.append("")
    L.append("  Rappel de cadrage : même établi, un écart de Sharpe de cette taille")
    L.append("  s'accompagne ici d'un rendement total inférieur de 355 points et")
    L.append("  d'un drawdown de 65 %. La question de l'intérêt pratique reste")
    L.append("  entière, indépendamment de la significativité statistique.")
    L.append("=" * 78)
    return "\n".join(L)


def main() -> int:
    report = run()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "significance.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(report.encode(enc, errors="replace").decode(enc) + "\n")
    print(f"\n  -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
