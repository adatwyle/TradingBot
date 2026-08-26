# -*- coding: utf-8 -*-
"""
s13 — variante session UNIQUE déclarée (FALSIFICATION §Variante session).

H4, entrées restreintes aux heures serveur 12-19 (chevauchement Londres/NY),
appliquée à la (aux) candidate(s) finale(s) UNIQUEMENT, exploration seulement
(index < 2025-02-16). INFORMATIF : ne crée pas de candidate, ne va pas au
hold-out.

La restriction d'heure filtre les SIGNAUX (le signal H4 est émis à la clôture
d'une barre dont l'heure de début est dans la fenêtre) — le témoin apparié
recopie ce profil d'heures via `_allowed_positions` du harnais commun.

Usage : python strategies/s13_macd_fx/backtests/run_session_variant.py
Sortie : backtests/session_variant.txt
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import run_walk_forward, attach_control_arm  # noqa: E402
from core.backtest.engine import run as run_engine                          # noqa: E402
from core.data.instruments import get_spec                                  # noqa: E402
from core.data.source import load_bars                                      # noqa: E402
from strategies.S013_macd_fx.strategy import Strategy                        # noqa: E402

HERE = os.path.dirname(__file__)
SEAL = pd.Timestamp("2025-02-16")
SLIPPAGE = 0.5
HOURS = range(12, 20)          # heures serveur autorisées (début de barre H4)

# (pair, params, engine_kwargs) — candidates finales uniquement.
# lookback D1 252 j -> 1512 barres H4 (équivalence temporelle déclarée ;
# MACD/ATR restent 12/26/9/14 en barres H4 — la variante teste le MOTIF à
# l'échelle intra-journalière, pas une traduction paramétrique exacte).
EK = dict(cooldown_bars=0, cb_losses=999)
CANDIDATES: list[tuple] = [
    ("EURJPY", dict(family="ext", direction="long", lookback=1512, q=0.10,
                    exit="atr_1.5_1.5"), EK),
    ("AUDCAD", dict(family="ext", direction="long", lookback=1512, q=0.10,
                    exit="atr_1.5_1.5"), EK),
]


class SessionStrategy(Strategy):
    """Même stratégie, signaux H4 filtrés sur la fenêtre de session.

    Le filtre s'applique au timestamp du signal (barre de décision) — aucune
    autre différence avec la version D1. Sous-classe locale au runner : le
    module stratégie lui-même reste inchangé (la variante est déclarée UNE
    fois, ici)."""

    def generate_signals(self, data, params, end_idx):
        sigs = super().generate_signals(data, params, end_idx)
        return [s for s in sigs if pd.Timestamp(s.timestamp).hour in HOURS]


def rpt(res):
    if not res.n_trades:
        return "0 trade"
    return (f"{res.n_trades:>4} tr, {res.total_r:>+8.2f} R, "
            f"{res.total_r/res.n_trades:>+8.4f} R/t, WR {res.win_rate:.1f} %")


def main():
    if not CANDIDATES:
        raise SystemExit("Liste vide — à remplir avec les candidates finales.")
    L = []
    for pair, params, ek in CANDIDATES:
        bars = load_bars(pair, "H4", days=7300, max_age_hours=10**9)
        bars = bars[bars.index < SEAL]
        spec = replace(get_spec(pair), slippage_pips=SLIPPAGE)
        for cls, tag in ((Strategy, "H4 toutes heures"),
                         (SessionStrategy, "H4 fenêtre 12-19")):
            st = cls()
            st._symbol = pair
            grid1 = {k: [v] for k, v in params.items()}
            report = run_walk_forward(st, bars, spec, param_grid=grid1,
                                      min_trades=60, verbose=False,
                                      engine_kwargs=ek)
            cell = report.results[0]
            attach_control_arm(report, bars, spec, configs=[cell],
                               engine_kwargs=ek, verbose=False)
            fs = cell.full_sample
            L.append(f"{pair} {params} — {tag}")
            L.append(f"  plein échantillon : {rpt(fs)}")
            L.append(f"  OOS honest_r {cell.honest_r:+.2f} "
                     f"({cell.total_test_trades} tr)")
            if cell.control:
                L.append(f"  {cell.control.line()}")
            L.append("")
    txt = "\n".join(L)
    with open(os.path.join(HERE, "session_variant.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    sys.stdout.buffer.write((txt + "\n-> session_variant.txt\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
