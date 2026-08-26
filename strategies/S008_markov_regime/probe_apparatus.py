"""
LE TEST QUI PASSE EN PREMIER — l'appareil markovien contribue-t-il à quelque chose ?
=====================================================================================

Ce fichier ne mesure aucune performance. Il répond à quatre questions
structurelles qui, si elles tombent mal, rendent toute mesure de performance
sans objet — parce qu'on mesurerait alors autre chose que ce qu'on croit.

    Q1  De combien la persistance chute-t-elle quand on retire le
        recouvrement des fenêtres ? (correction n°1 de la source)

    Q2  Le signal markovien produit-il d'autres positions que la règle naïve
        « long si ret20 > +5 %, short si < -5 % » ? Si non, tout l'appareil est
        de la décoration. (research/FALSIFICATION.md §F1)

    Q3  De combien la matrice fuitée (plein échantillon) diffère-t-elle de la
        matrice causale ? (correction n°2, et mesure directe de l'ampleur du
        biais de fuite — utile bien au-delà de s08)

    Q4  Quel écart entre `P^n` (juste) et l'exponentiation scalaire décrite
        dans la source (fausse) ?

USAGE
-----
    python -m strategies.s08_markov_regime.probe_apparatus
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strategies.s08_markov_regime import markov as mk
from strategies.s08_markov_regime.run_backtest import load_universe

UNIVERSE = ["SP500", "NASDAQ", "BTCUSD"]
LBL = ["bear", "side", "bull"]


def load(sym: str) -> pd.DataFrame:
    """Passe par le chargeur du harnais : il retire les barres à prix nul.

    Sans ce filtre, la barre entièrement à zéro du 2015-01-07 sur `#BTCUSD`
    fausse le rendement 20 j sur 20 barres et fabrique des états inexistants.
    """
    return load_universe([sym])[sym]


def fmt_matrix(P: np.ndarray, C: np.ndarray) -> list[str]:
    head = "de -> vers"
    L = [f"    {head:<10} {'bear':>8} {'side':>8} {'bull':>8}   {'n obs':>7}"]
    for a in range(3):
        row = "  ".join(f"{P[a, b]:>6.3f}" for b in range(3))
        L.append(f"    {LBL[a]:<10} {row}   {int(C[a].sum()):>7}")
    return L


def q1_persistence(states: np.ndarray) -> list[str]:
    L = ["  Q1 — PERSISTANCE : l'artefact de recouvrement", "  " + "-" * 74]
    L.append("  Deux fenêtres de 20 j consécutives partagent 19 j. La persistance")
    L.append("  mesurée sur des fenêtres qui se chevauchent est donc mécanique.")
    L.append("")
    for step, tag in ((1, "recouvrantes (step=1)"), (20, "SANS recouvrement (step=20)")):
        P, C = mk.stationary_matrix(states, step, alpha=1.0)
        L.append(f"  {tag} — n = {int(C.sum())} transitions")
        L += fmt_matrix(P, C)
        diag = [P[a, a] for a in range(3)]
        L.append(f"    persistance diagonale : bear {diag[0]:.3f}  side {diag[1]:.3f} "
                 f" bull {diag[2]:.3f}")
        L.append("")
    P1, _ = mk.stationary_matrix(states, 1)
    P20, _ = mk.stationary_matrix(states, 20)
    L.append("  CHUTE de persistance (step=1 -> step=20), en points :")
    for a in range(3):
        L.append(f"    {LBL[a]:<6} {100*P1[a,a]:>6.1f} %  ->  {100*P20[a,a]:>6.1f} %"
                 f"   ({100*(P20[a,a]-P1[a,a]):+.1f} pt)")
    L.append("")
    return L


def q2_marginal(states: np.ndarray, step: int) -> list[str]:
    """Le test décisif : le signal markovien change-t-il de position ?"""
    L = ["  Q2 — CONTRIBUTION MARGINALE DE L'APPAREIL", "  " + "-" * 74]
    res = mk.markov_signal(states, step, causal=True)
    sig = res["signal"]
    ntr = res["n_trans"]

    naive = np.zeros(len(states), dtype=float)
    naive[states == mk.BULL] = 1.0
    naive[states == mk.BEAR] = -1.0

    # On ne compare que là où la matrice a un contenu défendable.
    valid = (states >= 0) & (ntr >= 30)
    sm, nv = np.sign(sig[valid]), np.sign(naive[valid])
    n = int(valid.sum())
    agree = float((sm == nv).mean()) if n else float("nan")

    L.append(f"  Barres exploitables (état défini, >= 30 transitions connues) : {n}")
    L.append(f"  Concordance de SIGNE markov / naïf : {100*agree:.2f} %  (n = {n})")
    L.append(f"  Désaccords : {int((sm != nv).sum())}")
    L.append("")

    # Le SEUL mécanisme par lequel l'appareil peut différer du naïf : que le
    # signe du signal change pour un MÊME état au fil du temps.
    L.append("  Signe du signal par état, au fil du temps :")
    for a, lab in enumerate(LBL):
        m = valid & (states == a)
        if not m.any():
            continue
        s = np.sign(sig[m])
        pos, neg, zer = int((s > 0).sum()), int((s < 0).sum()), int((s == 0).sum())
        rng = f"[{sig[m].min():+.3f} ; {sig[m].max():+.3f}]"
        L.append(f"    {lab:<6} n={int(m.sum()):>5}   signe +:{pos:>5}  -:{neg:>5} "
                 f" 0:{zer:>4}   amplitude {rng}")
    L.append("")
    L.append("  Lecture : si chaque état ne présente qu'un seul signe, la matrice")
    L.append("  glissante ne fait varier que l'AMPLITUDE, jamais la direction —")
    L.append("  la stratégie est alors la règle naïve, dimensionnée autrement.")
    L.append("")
    return L


def q3_leak(states: np.ndarray, step: int) -> list[str]:
    L = ["  Q3 — AMPLEUR DU BIAIS DE FUITE (matrice causale vs plein échantillon)",
         "  " + "-" * 74]
    causal = mk.markov_signal(states, step, causal=True)["signal"]
    leaky = mk.markov_signal(states, step, causal=False)["signal"]
    ntr = mk.markov_signal(states, step, causal=True)["n_trans"]
    m = (states >= 0) & (ntr >= 30)
    n = int(m.sum())
    if not n:
        return L + ["  (pas assez de transitions)", ""]
    d = np.abs(causal[m] - leaky[m])
    flip = int((np.sign(causal[m]) != np.sign(leaky[m])).sum())
    L.append(f"  n = {n} barres comparées")
    L.append(f"  écart absolu moyen du signal : {d.mean():.4f}   médian {np.median(d):.4f}"
             f"   max {d.max():.4f}")
    L.append(f"  barres où la fuite CHANGE LE SIGNE de la position : {flip} "
             f"({100*flip/n:.2f} %)")
    L.append("")
    return L


def q4_power(states: np.ndarray, step: int) -> list[str]:
    L = ["  Q4 — P^n CONTRE L'EXPONENTIATION SCALAIRE DE LA SOURCE", "  " + "-" * 74]
    P, C = mk.stationary_matrix(states, step)
    L.append("  Matrice de plein échantillon élevée aux puissances successives :")
    L.append(f"    {'n':>3}  {'P^n[bull,bull]':>15} {'signal(bull)':>14}"
             f" {'scalaire^n':>12}")
    s1 = P[mk.BULL, mk.BULL] - P[mk.BULL, mk.BEAR]
    for n in (1, 2, 3, 5, 10, 20, 50):
        Pn = mk.matrix_power_rows(P, n)
        sig = Pn[mk.BULL, mk.BULL] - Pn[mk.BULL, mk.BEAR]
        L.append(f"    {n:>3}  {Pn[mk.BULL, mk.BULL]:>15.4f} {sig:>14.4f}"
                 f" {np.sign(s1)*abs(s1)**n:>12.6f}")
    # Distribution stationnaire, pour montrer vers quoi P^n converge réellement.
    Pn = mk.matrix_power_rows(P, 200)
    L.append(f"  P^200 (distribution stationnaire) : "
             f"bear {Pn[0,0]:.3f} side {Pn[0,1]:.3f} bull {Pn[0,2]:.3f}")
    L.append("  Le scalaire tend vers 0 ; P^n tend vers la stationnaire. Les deux")
    L.append("  décrivent des mondes opposés — la source décrit le mauvais.")
    L.append("")
    return L


def main() -> int:
    L = ["=" * 78,
         "s08 — SONDE DE L'APPAREIL MARKOVIEN (avant toute mesure de performance)",
         "=" * 78, ""]
    for sym in UNIVERSE:
        df = load(sym)
        close = df["close"].to_numpy(dtype=float)
        ret = mk.rolling_return(close, 20)
        st = mk.classify(ret, 0.05, -0.05)
        L.append("#" * 78)
        L.append(f"# {sym} — {len(df)} barres D1  ({df.index[0].date()} -> "
                 f"{df.index[-1].date()})")
        occ = {LBL[a]: int((st == a).sum()) for a in range(3)}
        L.append(f"# occurrences d'états : {occ}")
        L.append("#" * 78)
        L.append("")
        L += q1_persistence(st)
        L += q2_marginal(st, 20)
        L += q3_leak(st, 20)
        L += q4_power(st, 20)

    txt = "\n".join(L)
    print(txt)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "backtests", "probe_apparatus.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
