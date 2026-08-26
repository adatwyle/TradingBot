"""Walk-forward ancré — s04_aipathways_trendcore.

LIRE AVANT D'INTERPRÉTER LE MOINDRE CHIFFRE DE CE FICHIER
---------------------------------------------------------
Le moteur commun ne sait pas sortir sur bascule de régime (ANALYSIS.md §5). Les
positions ouvertes ici survivent au retournement du régime jusqu'au stop de
catastrophe ou à la fin de tranche. **Ces chiffres ne mesurent donc PAS la
stratégie de la source.** Ils sont produits par transparence, pas comme preuve.

La mesure qui fait foi est `run_analysis.py`.
"""
from __future__ import annotations

import dataclasses
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:                                    # console Windows en cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.backtest.anchored_wf import run_walk_forward       # noqa: E402
from core.data.instruments import get_spec                   # noqa: E402
from core.data.source import load_bars                       # noqa: E402
from strategies.S004_aipathways_trendcore.strategy import Strategy  # noqa: E402

LEGS = [("risk", "NASDAQ"), ("hedge", "XAUUSD")]


def main() -> int:
    out = []
    out.append("=" * 96)
    out.append("WALK-FORWARD ANCRE — s04_aipathways_trendcore")
    out.append("=" * 96)
    out.append("")
    out.append("AVERTISSEMENT — CES CHIFFRES NE MESURENT PAS LA STRATEGIE.")
    out.append("")
    out.append("  Trend core est une bascule d'allocation : toujours investie, sortie")
    out.append("  UNIQUEMENT sur retournement de regime. Le moteur commun ne connait")
    out.append("  que trois sorties : SL, TP, fin de tranche. Il n'accepte aucun ordre")
    out.append("  de sortie sur signal (ANALYSIS.md §5).")
    out.append("")
    out.append("  Consequence : chaque position survit ici a la bascule de regime")
    out.append("  jusqu'au stop de catastrophe (8xATR) ou a la fin de la tranche.")
    out.append("  Ce qui est mesure = qualite du moment d'entree en regime avec un")
    out.append("  plancher de desastre. PAS la strategie de la source.")
    out.append("")
    out.append("  Ces resultats sont publies par transparence (R1 doit passer, la")
    out.append("  plateforme doit pouvoir charger la strategie). Le verdict s'appuie")
    out.append("  sur run_analysis.py / equity_analysis.txt.")
    out.append("")
    out.append("EFFECTIF — a garder sous les yeux en permanence :")
    out.append("  ~13 bascules de regime sur 5 ans. Les tranches de test font 10 % de")
    out.append("  l'historique, soit ~1 episode chacune. Aucun 'pass' n'est ici une")
    out.append("  preuve. 12 configurations -> ~0,6 reussite attendue par PUR HASARD.")
    out.append("")

    for leg, symbol in LEGS:
        bars = load_bars(symbol, "D1")
        spec = get_spec(symbol)
        strat = Strategy({"leg": leg, "_symbol": symbol})
        rep = run_walk_forward(strat, bars, spec, min_trades=20, max_dd_r=12.0,
                               verbose=False)
        out.append("")
        out.append("#" * 96)
        out.append(f"# JAMBE {leg.upper()} — {symbol} "
                   f"({'long quand NASDAQ > MM' if leg == 'risk' else 'long quand NASDAQ < MM'})")
        out.append("#" * 96)
        out.append(rep.render())

        # Plein echantillon, cellule de la source (ma200 / buffer 0).
        out.append("")
        out.append(f"--- plein echantillon, cellule de la source (ma_len=200, buffer=0) ---")
        for label, sp in (("spread reel", spec),
                          ("spread NUL ", dataclasses.replace(spec, spread_pips=0.0))):
            from core.backtest.engine import run as run_engine
            s = Strategy({"leg": leg, "ma_len": 200, "buffer_pct": 0.0, "_symbol": symbol})
            data = s.precompute(bars, s.params)
            sigs = s.generate_signals(data, s.params, len(bars))
            res = run_engine(sigs, bars, sp)
            d = res.summary()
            rpt = (d["total_r"] / d["n_trades"]) if d["n_trades"] else 0.0
            out.append(f"    {label} : {d['n_trades']:>3} trades, "
                       f"total {d['total_r']:>+8.2f} R, {rpt:>+7.4f} R/trade, "
                       f"WR {d['win_rate']}, DD {d['max_dd_r']:.2f} R")
        out.append("")

    text = "\n".join(out)
    print(text)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anchored_wf.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n-> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
