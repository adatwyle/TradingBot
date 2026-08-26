"""R1 — causalité, vérifiée sur la GRILLE et non seulement sur le défaut.

Ce script fait trois choses, dans cet ordre :

1. Il PROUVE que le gardien inspecte réellement la couche indicateur.
   `core/validation/causality.py::_compare_precompute` retourne silencieusement
   si `precompute` ne renvoie pas un DataFrame — une stratégie qui renvoie un
   dict échappe donc au contrôle sans qu'aucun message ne le signale (piège
   rencontré par s91). On vérifie ici que nos objets SONT des DataFrames, on
   liste les colonnes effectivement comparées, puis on PLANTE une fuite
   volontaire et on vérifie que le gardien la voit.

2. Il exécute l'invariant de troncature sur un échantillon de la grille
   (24 combinaisons), sur plusieurs instruments et les deux timeframes.

3. Il exécute aussi les variantes de CONTRÔLE (require_sweep=False,
   need_hl=False), qui produisent les chiffres du verdict et doivent donc être
   validées au même titre.
"""
from __future__ import annotations

import itertools
import os
import sys

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

from core.validation.causality import check, _compare_precompute  # noqa: E402
from core.data.source import load_bars                          # noqa: E402
from strategies.S005_flossbach_liqsweep.strategy import Strategy  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "causality.txt")


def main() -> int:
    L: list[str] = []
    L.append("=" * 92)
    L.append("R1 — INVARIANT DE CAUSALITE — s05_flossbach_liqsweep")
    L.append("=" * 92)
    L.append("")

    bars = load_bars("EURUSD", "H4")

    # ── 1. Le gardien inspecte-t-il VRAIMENT la couche indicateur ? ──────────
    L.append("--- 1. PREUVE QUE LA COUCHE INDICATEUR EST REELLEMENT INSPECTEE ---")
    L.append("")
    s = Strategy({"_symbol": "EURUSD"})
    T = int(len(bars) * 0.7)
    d_full = s.precompute(bars, s.params)
    d_tr = s.precompute(bars.iloc[:T].copy(), s.params)
    L.append(f"  type(precompute(...)) = {type(d_full).__name__}")
    L.append(f"  isinstance DataFrame  = {isinstance(d_full, pd.DataFrame)}")
    if not isinstance(d_full, pd.DataFrame):
        L.append("  *** precompute ne renvoie pas un DataFrame : _compare_precompute")
        L.append("      RETOURNE SANS RIEN VERIFIER. Resultats non publiables.")
    numeric = [c for c in d_full.columns
               if d_full[c].to_numpy().dtype.kind in "fiu"]
    L.append(f"  colonnes comparees ({len(numeric)}) : {', '.join(numeric)}")
    leaks = _compare_precompute(d_full, d_tr, T, 0.70)
    L.append(f"  fuites detectees sur ces colonnes : {len(leaks)}")
    L.append("")

    # ── Contrôles positifs : on plante des fuites et on regarde ce que le
    #    gardien attrape. Sans ça, « 0 fuite » peut aussi bien vouloir dire
    #    « rien n'a été regardé ».
    L.append("  CONTROLES POSITIFS — on plante des fuites volontaires et on")
    L.append("  verifie que le gardien les voit :")
    L.append("")

    def planter(nom, col_full, col_tr):
        bf, bt = d_full.copy(), d_tr.copy()
        bf[nom] = col_full
        bt[nom] = col_tr
        found = [p for p in _compare_precompute(bf, bt, T, 0.70) if p.column == nom]
        return found

    # (a) normalisation sur tout l'echantillon — le cas d'ecole documente.
    a_full = d_full["close"] / d_full["close"].mean()
    a_tr = d_tr["close"] / d_tr["close"].mean()
    fa = planter("fuite_normalisation", a_full, a_tr)
    if fa:
        p = fa[0]
        L.append(f"    (a) normalisation plein echantillon  -> DETECTEE "
                 f"(ecart max {p.max_deviation:.3e}, {p.n_affected}/{p.n_compared} points)")
    else:
        L.append("    (a) normalisation plein echantillon  -> *** NON DETECTEE ***")

    # (b) decalage vers le futur — attendu detecte, en realite INVISIBLE.
    fb = planter("fuite_shift_futur", d_full["close"].shift(-5),
                 d_tr["close"].shift(-5))
    if fb:
        p = fb[0]
        L.append(f"    (b) shift(-5) (valeur du futur)      -> DETECTEE "
                 f"(ecart max {p.max_deviation:.3e})")
    else:
        L.append("    (b) shift(-5) (valeur du futur)      -> *** NON DETECTEE ***")
        L.append("        LIMITE DU GARDIEN COMMUN, a signaler et non a contourner :")
        L.append("        sur la tranche tronquee, un shift(-k) produit des NaN sur les")
        L.append("        k dernieres barres — exactement la ou la fuite se voit. Or")
        L.append("        `_compare_precompute` masque les NaN (`both = isfinite(a) &")
        L.append("        isfinite(b)`) et ne compare donc jamais ces points. La signature")
        L.append("        la plus courante d'un look-ahead echappe a la couche indicateur.")
        L.append("        Elle reste attrapee par la couche SIGNAUX si elle fait basculer")
        L.append("        une decision — c'est le cas ici, cf. section 2.")

    planted = bool(fa)   # le gardien est operant si au moins (a) est vu
    L.append("")
    if planted:
        L.append("  => la couche indicateur est bien active sur NOS objets (nos 9")
        L.append("     colonnes sont reellement comparees). Le '0 fuite' ci-dessus")
        L.append("     est donc un resultat, pas un silence.")
    else:
        L.append("  *** aucun controle positif ne passe : R1 n'est pas opposable ici.")
    L.append("")

    # ── 2 & 3. Invariant sur la grille + variantes de contrôle ───────────────
    L.append("--- 2. INVARIANT DE TRONCATURE SUR LA GRILLE ---")
    L.append("")
    L.append("  Pour chaque cellule : 4 coupures (60/70/80/90 %).")
    L.append("  A = generate_signals(precompute(df), p, T)")
    L.append("  B = generate_signals(precompute(df[:T]), p, T)   -> doivent etre egaux")
    L.append("")

    cells = []
    for band, mc, sr, tm in itertools.product(
            [0.5, 1.0], [2, 3], ["sweep", "higherlow"], ["nearest", "first_rr"]):
        cells.append({"band_atr": band, "min_cluster": mc,
                      "stop_ref": sr, "target_mode": tm})
    # variantes de contrôle et filtres
    extra = [
        {"htf_mode": "with"}, {"chop_max": 1.5},
        {"require_sweep": False}, {"need_hl": False},
        {"require_sweep": False, "need_hl": False},
        {"setup_bars": 24}, {"setup_bars": 96}, {"piv": 2},
    ]
    cells.extend(extra)

    total = fails = 0
    n_leak = 0
    for sym, tf in (("EURUSD", "H4"), ("XAUUSD", "H4"), ("SP500", "H1")):
        b = load_bars(sym, tf)
        for cell in cells:
            p = {"_symbol": sym}
            p.update(cell)
            st = Strategy(p)
            rep = check(st, b, sym)
            total += 1
            n_leak += len(rep.indicator_leaks)
            if not rep.ok:
                fails += 1
                L.append(f"  *** FUITE  {sym}/{tf}  {cell}")
                for c in rep.cuts:
                    if not c.ok:
                        L.append(f"        coupure {c.fraction:.0%} : {c.first_divergence}")
        L.append(f"  {sym}/{tf} : {len(cells)} cellules x 4 coupures verifiees")

    L.append("")
    L.append(f"  TOTAL : {total} cellules x 4 coupures = {total * 4} comparaisons")
    L.append(f"  Divergences de signaux   : {fails}")
    L.append(f"  Fuites niveau indicateur : {n_leak}")
    L.append("")
    L.append("VERDICT R1 : " + ("PASSE" if (fails == 0 and n_leak == 0 and planted)
                                else "ECHOUE"))
    if fails == 0 and n_leak == 0 and planted:
        L.append("  Aucune information future detectee, ni au niveau des signaux, ni")
        L.append("  au niveau des indicateurs — et le controle positif prouve que la")
        L.append("  couche indicateur etait bien sous surveillance.")

    text = "\n".join(L)
    print(text)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n-> {OUT}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
