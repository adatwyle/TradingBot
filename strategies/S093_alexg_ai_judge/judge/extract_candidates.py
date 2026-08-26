"""
Extraction des candidats historiques du détecteur v2 — l'entrée du rejeu à
l'aveugle.

Pour chaque paire du manifest :
  1. détecteur v2 -> candidats + dossier de confluences (strategy.py) ;
  2. OUTCOME par candidat via le MOTEUR COMMUN (R9), évalué INDÉPENDAMMENT
     (signals=[sig]) : le R par candidat est figé une fois pour toutes, c'est
     la base de la comparaison de sélections (juge vs aléatoire de même taux).
     Coûts réels : spread catalogue + slippage 0,5 pip ;
  3. run séquentiel réaliste (tous candidats, max_positions=1) pour référence ;
  4. jointure COT ANTI-FUITE : le rapport actif à l'instant t est le dernier
     dont available_from <= t (publication vendredi 15h30 ET, jamais l'as-of).

Sortie : judge/candidates.jsonl (1 ligne par candidat, dossier complet +
outcome + COT) et judge/extract_summary.txt.

GBPUSD : absent du catalogue core (core/ est hors périmètre s93) — spec locale
documentée, relevé Swissquote comparable aux autres majors.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from core.backtest.engine import InstrumentSpec, run as run_engine          # noqa: E402
from core.data.instruments import get_spec                                  # noqa: E402
from core.data.source import load_bars                                      # noqa: E402
from strategies.S093_alexg_ai_judge.strategy import Strategy                 # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SLIPPAGE_PIPS = 0.5

PAIRS = {
    # symbol: (pip, base, quote)
    "EURUSD": (0.0001, "EUR", "USD"),
    "USDJPY": (0.01,   "USD", "JPY"),
    "USDCHF": (0.0001, "USD", "CHF"),
    "AUDCAD": (0.0001, "AUD", "CAD"),
    "GBPUSD": (0.0001, "GBP", "USD"),
    "EURJPY": (0.01,   "EUR", "JPY"),
}

# Spec locale GBPUSD (hors catalogue core — core/ interdit à s93).
GBPUSD_SPEC = InstrumentSpec(symbol="GBPUSD", pip=0.0001, spread_pips=2.4,
                             max_spread_pips=4.0, pip_value_per_lot=10.0)


def spec_for(symbol: str) -> InstrumentSpec:
    spec = GBPUSD_SPEC if symbol == "GBPUSD" else get_spec(symbol)
    return dataclasses.replace(spec, slippage_pips=SLIPPAGE_PIPS)


def load_cot() -> pd.DataFrame:
    cot = pd.read_csv(os.path.join(HERE, "cot_percentiles.csv"),
                      parse_dates=["available_from", "as_of"])
    return cot.sort_values("available_from")


def cot_at(cot: pd.DataFrame, currency: str, t: pd.Timestamp):
    """Dernier rapport PUBLIÉ avant t. Jamais l'as-of : anti-fuite."""
    sub = cot[(cot["currency"] == currency) & (cot["available_from"] <= t)]
    if sub.empty:
        return None
    return sub.iloc[-1]


def main() -> None:
    cot = load_cot()
    out_path = os.path.join(HERE, "candidates.jsonl")
    summary = []
    n_total = 0

    with open(out_path, "w", encoding="utf-8") as fh:
        for symbol, (pip, base, quote) in PAIRS.items():
            bars = load_bars(symbol, "H1", days=1855, max_age_hours=10**9)
            spec = spec_for(symbol)
            strat = Strategy({"pip": pip})
            strat._symbol = symbol
            data = strat.precompute(bars, strat.params)
            pairs_sig = data.attrs["signals"]      # [(i, Signal)]

            # run séquentiel réaliste (référence, pas la mesure de sélection)
            seq = run_engine([s for _, s in pairs_sig], bars, spec)

            n_kept = 0
            for i, sig in pairs_sig:
                res = run_engine([sig], bars, spec)
                if not res.trades:
                    continue                        # pas de barre suivante
                tr = res.trades[0]
                t = pd.Timestamp(sig.timestamp)

                cb = cot_at(cot, base, t)
                cq = cot_at(cot, quote, t)
                cot_fields = None
                if cb is not None and cq is not None:
                    diff = float(cb["pct3y"] - cq["pct3y"])
                    long = sig.side.value == "LONG"
                    aligned = diff > 0 if long else diff < 0
                    extreme = bool(cb["pct3y"] >= 90 or cb["pct3y"] <= 10
                                   or cq["pct3y"] >= 90 or cq["pct3y"] <= 10)
                    cot_fields = {
                        "cot_aligned": bool(aligned),
                        "cot_pct_base": round(float(cb["pct3y"]), 1),
                        "cot_pct_quote": round(float(cq["pct3y"]), 1),
                        "cot_extreme": extreme,
                        "cot_report_age_days": int((t - cb["available_from"]).days),
                    }

                rec = {
                    "symbol": symbol, "bar": int(i),
                    "time": str(t), "side": sig.side.value,
                    "entry": sig.entry, "stop": sig.stop, "target": sig.target,
                    "dossier": sig.meta["dossier"],
                    "cot": cot_fields,
                    "outcome": {
                        "pnl_r": round(tr.pnl_r, 4),
                        "exit_reason": tr.exit_reason,
                        "bars_held": tr.bars_held,
                    },
                }
                fh.write(json.dumps(rec) + "\n")
                n_kept += 1

            n_total += n_kept
            rs = [t.pnl_r for t in seq.trades]
            summary.append(
                f"{symbol}: {n_kept} candidats | run séquentiel : "
                f"{seq.n_trades} trades, {seq.total_r:+.1f} R, "
                f"WR {seq.win_rate:.0f}%" if seq.trades else
                f"{symbol}: {n_kept} candidats | run séquentiel : 0 trade")

    weeks = 1855 / 7.0
    lines = ["EXTRACTION s93 — détecteur v2, 6 paires H1, spread réel + "
             f"slippage {SLIPPAGE_PIPS} pip", ""]
    lines += summary
    lines += ["", f"TOTAL : {n_total} candidats "
              f"({n_total / weeks:.2f}/semaine sur le book)"]
    txt = "\n".join(lines)
    with open(os.path.join(HERE, "extract_summary.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
