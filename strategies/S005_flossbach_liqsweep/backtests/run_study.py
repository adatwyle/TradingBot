"""Étude poolée — s05_flossbach_liqsweep.

POURQUOI CE FICHIER EXISTE À CÔTÉ DU WALK-FORWARD
--------------------------------------------------
Il annonce skipper > 90 % des setups. Le motif est donc RARE par construction :
sur H4, la séquence complète (amas non balayé -> balayage -> structure de
retournement -> cassure nette -> cible à R:R >= 2) se produit quelques dizaines
de fois en cinq ans et par instrument. Les tranches de test du walk-forward
ancré valent 10 % de l'historique : elles contiennent souvent ZÉRO trade.

Le walk-forward reste exécuté (run_wf.py, c'est le protocole), mais il ne peut
pas trancher sur un effectif pareil. La mesure décisive est ici : l'espérance
par trade, poolée sur toute la grille et tous les instruments, avec son
effectif, contre trois groupes de contrôle.

CE QUI EST MESURÉ
-----------------
    A  variante SOURCE       balayage exigé + creux plus haut exigé
    B  contrôle SANS BALAYAGE même déclencheur de retournement, sans exiger le
                             balayage préalable  -> teste la falsification F3
    C  contrôle SANS PULLBACK balayage exigé, mais entrée à la cassure sans
                             attendre le creux plus haut  -> mesure l'apport de
                             l'étape 5 (« wait the one or other minute »)
    D  PLACEBO               mêmes géométries de stop/cible, mais entrée
                             décalée de 50 à 500 barres au hasard (graine fixe).
                             Donne la ligne de base de la géométrie de sortie :
                             c'est ce que produit le HASARD avec le même R:R.

Chaque variante est jouée à spread RÉEL et à spread NUL (ablation obligatoire,
docs/METHODOLOGY.md §5.1), et découpée LONG / SHORT (§5.2).
"""
from __future__ import annotations

import dataclasses
import itertools
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

import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402

from core.backtest.engine import run as run_engine              # noqa: E402
from core.contracts.strategy import Side, Signal                # noqa: E402
from core.data.instruments import get_spec                      # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from strategies.S005_flossbach_liqsweep.strategy import Strategy  # noqa: E402

SYMBOLS = ["EURUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD",
           "XAUUSD", "XAGUSD", "SP500", "NASDAQ", "DAX", "WTIUSD"]

GRID = [dict(zip(("band_atr", "min_cluster", "stop_ref", "htf_mode",
                  "chop_max", "target_mode"), c))
        for c in itertools.product([0.5, 1.0], [2, 3],
                                   ["sweep", "higherlow"], ["off", "with"],
                                   [99.0, 1.5], ["nearest", "first_rr"])]

VARIANTS = {
    "A_source":      {"require_sweep": True,  "need_hl": True},
    "B_sans_sweep":  {"require_sweep": False, "need_hl": True},
    "C_sans_pullbk": {"require_sweep": True,  "need_hl": False},
}


def _placebo(sigs: list[Signal], bars: pd.DataFrame, seed: int) -> list[Signal]:
    """Mêmes géométries, entrées déplacées au hasard.

    Conserve le sens, la distance de risque et le R:R de chaque signal réel,
    mais place l'entrée 50 à 500 barres plus loin. Tout ce qui reste est la
    géométrie de sortie ; l'information du setup a disparu. C'est la ligne de
    base à battre.
    """
    rng = np.random.default_rng(seed)
    close = bars["close"].to_numpy(dtype=float)
    idx = bars.index
    pos = {pd.Timestamp(t): i for i, t in enumerate(idx)}
    out: list[Signal] = []
    for s in sigs:
        i = pos.get(pd.Timestamp(s.timestamp))
        if i is None:
            continue
        j = i + int(rng.integers(50, 500))
        if j >= len(close) - 2:
            continue
        risk = abs(s.entry - s.stop)
        rr = abs(s.target - s.entry) / risk if risk else 0.0
        if risk <= 0 or rr <= 0:
            continue
        e = float(close[j])
        if s.side == Side.LONG:
            st, tg = e - risk, e + rr * risk
        else:
            st, tg = e + risk, e - rr * risk
        out.append(Signal(timestamp=pd.Timestamp(idx[j]).to_pydatetime(),
                          symbol=s.symbol, side=s.side, entry=e, stop=st,
                          target=tg, reason="PLACEBO"))
    return out


def _stats(trades) -> dict:
    if not trades:
        return {"n": 0, "r": 0.0, "rpt": 0.0, "wr": None}
    r = float(sum(t.pnl_r for t in trades))
    w = sum(1 for t in trades if t.pnl_r > 0)
    return {"n": len(trades), "r": r, "rpt": r / len(trades),
            "wr": 100.0 * w / len(trades)}


def _ci95(wins: int, n: int) -> tuple[float, float]:
    """Wilson — l'IC normal est faux sur petit effectif, et c'est précisément
    le régime dans lequel se trouve cette stratégie."""
    if n == 0:
        return (0.0, 0.0)
    z, p = 1.96, wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (100 * max(0.0, c - h), 100 * min(1.0, c + h))


def main(tf: str) -> int:
    t0 = time.time()
    L: list[str] = []
    L.append("=" * 100)
    L.append(f"ETUDE POOLEE — s05_flossbach_liqsweep — timeframe {tf}")
    L.append("=" * 100)
    L.append(f"{len(SYMBOLS)} instruments x {len(GRID)} cellules de grille x "
             f"{len(VARIANTS)} variantes + placebo")
    L.append("Tout resultat est donne AVEC son effectif. R = multiples du risque.")
    L.append("")

    # accumulateurs : variante -> (liste de trades reels, liste a spread nul)
    acc: dict[str, dict] = {v: {"real": [], "free": [], "per_sym": {},
                                "cells": []} for v in VARIANTS}
    acc["D_placebo"] = {"real": [], "free": [], "per_sym": {}, "cells": []}

    for sym in SYMBOLS:
        bars = load_bars(sym, tf)
        if bars is None or len(bars) < 3000:
            L.append(f"  [SKIP] {sym} — donnees insuffisantes")
            continue
        spec = get_spec(sym)
        spec0 = dataclasses.replace(spec, spread_pips=0.0)

        for vname, vparams in VARIANTS.items():
            sym_real, sym_free = [], []
            for gi, cell in enumerate(GRID):
                p = {"_symbol": sym}
                p.update(cell)
                p.update(vparams)
                st = Strategy(p)
                data = st.precompute(bars, st.params)
                sigs = st.generate_signals(data, st.params, len(bars))
                tr = run_engine(sigs, bars, spec).trades
                tf0 = run_engine(sigs, bars, spec0).trades
                sym_real += tr
                sym_free += tf0
                acc[vname]["cells"].append((sym, gi, _stats(tr)["rpt"], len(tr)))

                if vname == "A_source":
                    pl = _placebo(sigs, bars, seed=1000 + gi)
                    acc["D_placebo"]["real"] += run_engine(pl, bars, spec).trades
                    acc["D_placebo"]["free"] += run_engine(pl, bars, spec0).trades

            acc[vname]["real"] += sym_real
            acc[vname]["free"] += sym_free
            acc[vname]["per_sym"][sym] = (sym_real, sym_free)
        L.append(f"  {sym} traite  ({time.time() - t0:.0f}s)")

    L.append("")
    L.append("--- 1. ESPERANCE POOLEE PAR VARIANTE (tous instruments, toute la grille) ---")
    L.append("")
    L.append(f"  {'variante':<16} {'n trades':>9} {'total R':>10} {'R/trade':>10} "
             f"{'WR %':>7} {'IC95 WR':>16} {'R/trade spread NUL':>20}")
    L.append("  " + "-" * 94)
    for v in ["A_source", "B_sans_sweep", "C_sans_pullbk", "D_placebo"]:
        s = _stats(acc[v]["real"])
        s0 = _stats(acc[v]["free"])
        wins = sum(1 for t in acc[v]["real"] if t.pnl_r > 0)
        lo, hi = _ci95(wins, s["n"])
        wr = f"{s['wr']:.1f}" if s["wr"] is not None else "—"
        L.append(f"  {v:<16} {s['n']:>9} {s['r']:>+10.1f} {s['rpt']:>+10.4f} "
                 f"{wr:>7} {f'[{lo:.1f} ; {hi:.1f}]':>16} {s0['rpt']:>+20.4f}")
    L.append("")
    L.append("  Lecture : le seuil de rentabilite depend du R:R median realise")
    L.append("  (~2,5 a 3,5 -> seuil 22 a 29 % de reussite). Le PLACEBO donne la")
    L.append("  reussite qu'obtient la meme geometrie SANS information de setup.")
    L.append("")

    L.append("--- 1bis. EST-CE DISTINGUABLE DE ZERO ? ---")
    L.append("")
    L.append("  Une esperance par trade n'a de sens qu'avec son incertitude. Ecart-type")
    L.append("  des R par trade, erreur-type = sd/sqrt(n), IC 95 % = +/- 1,96 x SE.")
    L.append("")
    L.append(f"  {'variante':<16} {'n':>7} {'R/trade':>10} {'sd':>7} {'SE':>8} "
             f"{'IC95 R/trade':>22} {'t':>7}")
    L.append("  " + "-" * 82)
    stat = {}
    for v in ["A_source", "B_sans_sweep", "C_sans_pullbk", "D_placebo"]:
        x = np.array([t.pnl_r for t in acc[v]["real"]], dtype=float)
        if x.size == 0:
            continue
        m, sd = float(x.mean()), float(x.std(ddof=1))
        se = sd / (x.size ** 0.5)
        stat[v] = (m, sd, se, x.size)
        L.append(f"  {v:<16} {x.size:>7} {m:>+10.4f} {sd:>7.2f} {se:>8.4f} "
                 f"{f'[{m - 1.96 * se:+.4f} ; {m + 1.96 * se:+.4f}]':>22} {m / se:>+7.2f}")
    L.append("")
    if "A_source" in stat and "D_placebo" in stat:
        ma, _, sea, _ = stat["A_source"]
        md, _, sed, _ = stat["D_placebo"]
        dse = (sea * sea + sed * sed) ** 0.5
        L.append(f"  A (source) MOINS D (placebo) : {ma - md:+.4f} R/trade, "
                 f"SE {dse:.4f}, t = {(ma - md) / dse:+.2f}")
        L.append(f"    IC95 : [{ma - md - 1.96 * dse:+.4f} ; {ma - md + 1.96 * dse:+.4f}]")
    if "A_source" in stat and "B_sans_sweep" in stat:
        ma, _, sea, _ = stat["A_source"]
        mb, _, seb, _ = stat["B_sans_sweep"]
        dse = (sea * sea + seb * seb) ** 0.5
        L.append(f"  A (source) MOINS B (sans balayage) : {ma - mb:+.4f} R/trade, "
                 f"SE {dse:.4f}, t = {(ma - mb) / dse:+.2f}")
        L.append(f"    IC95 : [{ma - mb - 1.96 * dse:+.4f} ; {ma - mb + 1.96 * dse:+.4f}]")
    L.append("")
    L.append("  |t| < 1,96 = indistinguable de zero au seuil 95 %. Les cellules de")
    L.append("  grille se recouvrant fortement (memes barres, parametres voisins), ces")
    L.append("  effectifs sont OPTIMISTES : les trades ne sont pas independants et la")
    L.append("  vraie erreur-type est PLUS GRANDE que celle affichee ici.")
    L.append("")

    L.append("--- 2. PAR INSTRUMENT — variante A (source) ---")
    L.append("")
    L.append(f"  {'instrument':<10} {'n':>6} {'R/trade':>10} {'WR %':>7} "
             f"{'R/tr spread nul':>16} {'n long':>7} {'R/tr long':>11} "
             f"{'n short':>8} {'R/tr short':>11}")
    L.append("  " + "-" * 92)
    for sym in SYMBOLS:
        if sym not in acc["A_source"]["per_sym"]:
            continue
        tr, tr0 = acc["A_source"]["per_sym"][sym]
        s, s0 = _stats(tr), _stats(tr0)
        lg = _stats([t for t in tr if t.side == Side.LONG])
        sh = _stats([t for t in tr if t.side == Side.SHORT])
        wr = f"{s['wr']:.1f}" if s["wr"] is not None else "—"
        L.append(f"  {sym:<10} {s['n']:>6} {s['rpt']:>+10.4f} {wr:>7} "
                 f"{s0['rpt']:>+16.4f} {lg['n']:>7} {lg['rpt']:>+11.4f} "
                 f"{sh['n']:>8} {sh['rpt']:>+11.4f}")
    L.append("")

    L.append("--- 3. CONTROLE LONG / SHORT — poole, variante A ---")
    lg = _stats([t for t in acc["A_source"]["real"] if t.side == Side.LONG])
    sh = _stats([t for t in acc["A_source"]["real"] if t.side == Side.SHORT])
    L.append(f"  LONG  : {lg['n']:>6} trades, {lg['rpt']:+.4f} R/trade, total {lg['r']:+.1f} R")
    L.append(f"  SHORT : {sh['n']:>6} trades, {sh['rpt']:+.4f} R/trade, total {sh['r']:+.1f} R")
    L.append("  (F4 est declenchee si UN SEUL sens porte tout le resultat positif.)")
    L.append("")

    L.append("--- 4. DISPERSION DES CELLULES — variante A ---")
    cells = [c for c in acc["A_source"]["cells"] if c[3] > 0]
    pos = sum(1 for c in cells if c[2] > 0)
    L.append(f"  cellules (instrument x config) avec au moins 1 trade : {len(cells)}")
    L.append(f"  dont R/trade > 0 : {pos}  ({100.0 * pos / len(cells):.1f} %)")
    L.append("  Si le signal etait pur bruit on attendrait ~50 %.")
    empt = sum(1 for c in acc["A_source"]["cells"] if c[3] == 0)
    L.append(f"  cellules SANS aucun trade : {empt} / {len(acc['A_source']['cells'])}")
    L.append("")

    L.append(f"Duree : {time.time() - t0:.0f}s")
    text = "\n".join(L)
    print(text)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        f"pooled_study_{tf}.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n-> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "H4"))
