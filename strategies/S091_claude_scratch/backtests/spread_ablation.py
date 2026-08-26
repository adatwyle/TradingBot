"""
Ablation du spread, contrôle directionnel et examen du confondant — s91.

    python strategies/s91_claude_scratch/backtests/spread_ablation.py \
        > backtests/spread_ablation.txt

Aucun moteur réimplémenté (R9) : `core.backtest.engine.run` uniquement.
L'ablation consiste à repasser EXACTEMENT les mêmes signaux dans le même moteur
avec `spread_pips = 0.0` (`dataclasses.replace`). Elle sépare en une mesure :

    « le signal n'a pas d'edge »   de   « le signal a un edge que les coûts mangent »

Les deux appellent des décisions opposées (abandonner vs changer de terrain), et
sans cette mesure on ne peut pas trancher. C'est le diagnostic n°1 légué par le
VERDICT de s01 (§5.1).

Le second bloc est l'examen du CONFONDANT. H91 prédit que les paires JPY
échouent parce que 22-06h serveur est leur session domestique. Mais 2021-2026
est aussi la période du carry trade yen : une stratégie contre-tendance qui vend
les extensions d'une paire en tendance haussière perd, quelle que soit l'heure.
Si l'échec JPY s'explique par la tendance, il n'appuie PAS le mécanisme invoqué.
"""
from __future__ import annotations

import dataclasses
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.backtest.anchored_wf import _grid                     # noqa: E402
from core.backtest.engine import run as run_engine              # noqa: E402
from core.data.instruments import get_spec                      # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from strategies.s91_claude_scratch.strategy import (            # noqa: E402
    CONTROL_JPY, ELIGIBLE, Strategy,
)

ALL_SYMBOLS = ELIGIBLE + CONTROL_JPY


def rule(c="=", n=100):
    print(c * n)


def section(t):
    print()
    rule()
    print(t)
    rule()


def _cells():
    return _grid(Strategy().manifest().param_grid)


def _signals_cache(sym):
    """precompute() ne dépend d'aucun paramètre de grille -> un seul calcul."""
    df = load_bars(sym, "H1")
    s = Strategy()
    s._symbol = sym
    return df, s, s.precompute(df, s.params)


# ─────────────────────────────────────────────────────────────────────────────
def ablation():
    section("1. ABLATION DU SPREAD — SUR TOUTE LA GRILLE (54 x 6 = 324 cellules)")
    print("  Mêmes signaux, même moteur, spread réel -> spread nul.")
    print()
    per_sym = {}
    cells = _cells()
    for sym in ALL_SYMBOLS:
        df, s, data = _signals_cache(sym)
        spec = get_spec(sym)
        spec0 = dataclasses.replace(spec, spread_pips=0.0)
        real, free, pos_r, pos_f, ntr = [], [], 0, 0, []
        for c in cells:
            p = dict(s.params)
            p.update(c)
            sig = s.generate_signals(data, p, len(df))
            a = run_engine(sig, df, spec)
            b = run_engine(sig, df, spec0)
            if not a.trades:
                continue
            ra, rb = a.total_r / a.n_trades, b.total_r / b.n_trades
            real.append(ra)
            free.append(rb)
            ntr.append(a.n_trades)
            pos_r += ra > 0
            pos_f += rb > 0
        per_sym[sym] = dict(real=np.mean(real), free=np.mean(free),
                            pos_r=pos_r, pos_f=pos_f, n=len(real),
                            trades=int(np.median(ntr)))

    print(f"  {'instrument':<11}{'groupe':<14}{'R/tr réel':>11}{'R/tr nul':>10}"
          f"{'coût':>9}{'cell+ réel':>12}{'cell+ nul':>11}{'trades méd':>12}")
    print("  " + "-" * 90)
    for sym in ALL_SYMBOLS:
        d = per_sym[sym]
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        print(f"  {sym:<11}{grp:<14}{d['real']:>+11.4f}{d['free']:>+10.4f}"
              f"{d['free']-d['real']:>+9.4f}"
              f"{str(d['pos_r'])+'/'+str(d['n']):>12}"
              f"{str(d['pos_f'])+'/'+str(d['n']):>11}{d['trades']:>12}")
    print("  " + "-" * 90)

    for label, group in (("ÉLIGIBLES (4)", ELIGIBLE), ("CONTRÔLE JPY (2)", CONTROL_JPY)):
        r = np.mean([per_sym[s]["real"] for s in group])
        f = np.mean([per_sym[s]["free"] for s in group])
        pr = sum(per_sym[s]["pos_r"] for s in group)
        pf = sum(per_sym[s]["pos_f"] for s in group)
        tot = sum(per_sym[s]["n"] for s in group)
        print(f"  {label:<25}{r:>+11.4f}{f:>+10.4f}{f-r:>+9.4f}"
              f"{str(pr)+'/'+str(tot):>12}{str(pf)+'/'+str(tot):>11}")

    print()
    print("  LECTURE (F1) :")
    fe = np.mean([per_sym[s]["free"] for s in ELIGIBLE])
    re_ = np.mean([per_sym[s]["real"] for s in ELIGIBLE])
    print(f"    Espérance BRUTE des éligibles (spread nul) : {fe:+.4f} R/trade")
    print(f"    Espérance NETTE des éligibles (spread réel): {re_:+.4f} R/trade")
    print(f"    Péage : {fe-re_:+.4f} R/trade")
    if fe > 0 >= re_:
        print("    -> Cas « edge brut réel, mangé par les coûts ». F1 NON déclenchée,")
        print("       mais la stratégie est perdante telle qu'exécutable.")
    elif fe <= 0:
        print("    -> Cas « pas d'edge du tout ». F1 DÉCLENCHÉE.")
    return per_sym


# ─────────────────────────────────────────────────────────────────────────────
def directional_control():
    section("2. CONTRÔLE DIRECTIONNEL — SUR TOUTE LA GRILLE (F4a)")
    print("  2021-2026 fabrique de faux edges directionnels (fait #7 du projet :")
    print("  USDJPY +69,7 R en long contre -10,0 R en short). Un résultat porté")
    print("  par un seul sens est un pari sur le régime, pas un système.")
    print()
    print(f"  {'instrument':<11}{'groupe':<14}{'nL':>7}{'R/tr LONG':>12}"
          f"{'nS':>7}{'R/tr SHORT':>12}{'écart':>10}{'verdict':>22}")
    print("  " + "-" * 96)
    cells = _cells()
    out = {}
    for sym in ALL_SYMBOLS:
        df, s, data = _signals_cache(sym)
        spec = get_spec(sym)
        L, S = [], []
        for c in cells:
            p = dict(s.params)
            p.update(c)
            res = run_engine(s.generate_signals(data, p, len(df)), df, spec)
            L += [t.pnl_r for t in res.trades if t.side.value == "LONG"]
            S += [t.pnl_r for t in res.trades if t.side.value == "SHORT"]
        ml, ms = (np.mean(L) if L else np.nan), (np.mean(S) if S else np.nan)
        out[sym] = (ml, ms)
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        v = "cohérent" if (ml > 0) == (ms > 0) else "*** ASYMÉTRIQUE ***"
        print(f"  {sym:<11}{grp:<14}{len(L):>7}{ml:>+12.4f}"
              f"{len(S):>7}{ms:>+12.4f}{ml-ms:>+10.4f}{v:>22}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
def confound_trend(direction):
    section("3. LE CONFONDANT — L'ÉCHEC JPY EST-IL DÛ À LA SESSION OU À LA TENDANCE ?")
    print("  H91 attribue l'échec des paires JPY à la session de Tokyo.")
    print("  Explication concurrente, plus simple, déjà documentée par le projet :")
    print("  le carry yen 2021-2024. Vendre les extensions d'une paire en forte")
    print("  tendance haussière perd, quelle que soit l'heure.")
    print()
    print("  Si l'asymétrie long/short suit la TENDANCE de la paire, c'est la")
    print("  tendance qui explique, pas la session — et F2 ne prouve rien.")
    print()
    print(f"  {'instrument':<11}{'groupe':<14}{'dérive 5,1 ans':>16}"
          f"{'R/tr LONG':>12}{'R/tr SHORT':>12}{'asym. suit tendance ?':>24}")
    print("  " + "-" * 92)
    for sym in ALL_SYMBOLS:
        df = load_bars(sym, "H1")
        spec = get_spec(sym)
        drift = (float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / spec.pip
        ml, ms = direction[sym]
        # Tendance haussière -> les shorts contre-tendance souffrent le plus.
        follows = "OUI" if ((drift > 0 and ms < ml) or (drift < 0 and ml < ms)) else "non"
        grp = "ÉLIGIBLE" if sym in ELIGIBLE else "CONTRÔLE JPY"
        print(f"  {sym:<11}{grp:<14}{drift:>+16.0f}{ml:>+12.4f}{ms:>+12.4f}"
              f"{follows:>24}")
    print()
    print("  « dérive » = variation close final - close initial, en pips.")


# ─────────────────────────────────────────────────────────────────────────────
def yearly_stability():
    section("4. STABILITÉ ANNUELLE — cellule par défaut, groupe éligible agrégé")
    print("  Un résultat concentré sur une année n'est pas un système (le motif")
    print("  « 72 % du résultat vient de 2022 » a déjà disqualifié XAUUSD sur s01).")
    print()
    per_year = defaultdict(float)
    per_year_n = defaultdict(int)
    for sym in ELIGIBLE:
        df, s, data = _signals_cache(sym)
        res = run_engine(s.generate_signals(data, s.params, len(df)), df,
                         get_spec(sym))
        for t in res.trades:
            per_year[t.entry_time.year] += t.pnl_r
            per_year_n[t.entry_time.year] += 1
    print(f"  {'année':<8}{'R cumulé':>12}{'trades':>9}{'R/trade':>11}")
    print("  " + "-" * 40)
    for y in sorted(per_year):
        n = per_year_n[y]
        print(f"  {y:<8}{per_year[y]:>+12.1f}{n:>9}{per_year[y]/n:>+11.4f}")
    print("  " + "-" * 40)
    print(f"  {'TOTAL':<8}{sum(per_year.values()):>+12.1f}"
          f"{sum(per_year_n.values()):>9}")


def main():
    print("s91_claude_scratch — ABLATION DU SPREAD, CONTRÔLE DIRECTIONNEL, CONFONDANT")
    print(f"éligibles    : {', '.join(ELIGIBLE)}")
    print(f"contrôle JPY : {', '.join(CONTROL_JPY)}")
    print("grille       : 54 configurations")
    ablation()
    d = directional_control()
    confound_trend(d)
    yearly_stability()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
