"""Walk-forward ancré — s05_flossbach_liqsweep.

À LIRE AVANT D'INTERPRÉTER LE MOINDRE CHIFFRE
----------------------------------------------
Le motif est rare PAR CONSTRUCTION : « I skip more than 90% of the trades I see
in the chart ». Une tranche de test du walk-forward ancré vaut 10 % de
l'historique. Sur H4, cinq ans donnent quelques dizaines de trades par
instrument et par cellule — donc souvent ZÉRO par tranche de test.

Ce fichier est produit parce que c'est le protocole (R1..R10 + checklist
d'admission), pas parce qu'il peut trancher. Un « STRICT pass » sur une tranche
à 1 trade n'est pas une preuve, et l'attente par pur hasard est affichée à côté
de chaque compte.

La mesure décisive est `pooled_study_*.txt` (run_study.py).
"""
from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.backtest.anchored_wf import run_walk_forward           # noqa: E402
from core.data.instruments import get_spec                       # noqa: E402
from core.data.source import load_bars                           # noqa: E402
from strategies.s05_flossbach_liqsweep.strategy import Strategy   # noqa: E402

SYMBOLS = ["EURUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD",
           "XAUUSD", "XAGUSD", "SP500", "NASDAQ", "DAX", "WTIUSD"]


def main(tf: str) -> int:
    t0 = time.time()
    L: list[str] = []
    L.append("=" * 100)
    L.append(f"WALK-FORWARD ANCRE — s05_flossbach_liqsweep — {tf}")
    L.append("=" * 100)
    L.append("")
    L.append("AVERTISSEMENT SUR L'EFFECTIF — a garder sous les yeux en permanence.")
    L.append("")
    L.append("  Il annonce skipper > 90 % des setups. Le motif est donc RARE par")
    L.append("  construction. Une tranche de test vaut 10 % de l'historique : elle")
    L.append("  contient souvent ZERO trade. Un 'STRICT pass' obtenu sur 0 a 2 trades")
    L.append("  ne prouve RIEN — c'est exactement l'erreur des 19 trades documentee")
    L.append("  dans docs/METHODOLOGY.md.")
    L.append("")
    L.append("  64 cellules de grille -> ~3,2 reussites STRICT attendues par PUR")
    L.append("  HASARD et par instrument. Le chiffre est rappele par le harnais.")
    L.append("")
    L.append("  La mesure qui fait foi est backtests/pooled_study_*.txt.")
    L.append("")

    recap = []
    for sym in SYMBOLS:
        bars = load_bars(sym, tf)
        if bars is None or len(bars) < 3000:
            L.append(f"[SKIP] {sym}")
            continue
        spec = get_spec(sym)
        strat = Strategy({"_symbol": sym})
        rep = run_walk_forward(strat, bars, spec, min_trades=20, max_dd_r=12.0,
                               verbose=False)
        L.append("")
        L.append("#" * 100)
        L.append(f"# {sym} / {tf}")
        L.append("#" * 100)
        L.append(rep.render())
        n_strict = len(rep.strict())
        oos_tr = [r.total_test_trades for r in rep.results]
        recap.append((sym, n_strict, rep.n_configs,
                      sorted(oos_tr)[len(oos_tr) // 2] if oos_tr else 0,
                      max(oos_tr) if oos_tr else 0,
                      sum(r.avg_oos for r in rep.results) / len(rep.results)))
        print(f"  {sym} ok ({time.time() - t0:.0f}s)", flush=True)

    L.append("")
    L.append("=" * 100)
    L.append("RECAPITULATIF")
    L.append("=" * 100)
    L.append(f"  {'instrument':<12} {'STRICT':>7} {'attendu hasard':>15} "
             f"{'trades OOS med':>15} {'max':>6} {'moy OOS grille':>15}")
    L.append("  " + "-" * 76)
    for sym, ns, nc, med, mx, avg in recap:
        L.append(f"  {sym:<12} {ns:>7} {nc * 0.05:>15.1f} {med:>15} {mx:>6} {avg:>+15.2f}")
    tot_s = sum(r[1] for r in recap)
    tot_c = sum(r[2] * 0.05 for r in recap)
    L.append("  " + "-" * 76)
    L.append(f"  {'TOTAL':<12} {tot_s:>7} {tot_c:>15.1f}")
    L.append("")
    L.append("  Si STRICT <= attendu par hasard, la grille n'a rien montre : c'est")
    L.append("  la condition de falsification F2 (research/ANALYSIS.md §7).")
    L.append(f"\nDuree : {time.time() - t0:.0f}s")

    text = "\n".join(L)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        f"anchored_wf_{tf}.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text[-4000:])
    print(f"\n-> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "H4"))
