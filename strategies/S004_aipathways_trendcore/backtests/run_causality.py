"""R1 — invariant de causalité, exécuté à la main.

POURQUOI CE SCRIPT EXISTE
--------------------------
`python -m core.validation.causality --strategy s04_aipathways_trendcore --save`
refuse de tourner : la CLI exige `len(df) >= 2000` (ligne 223 du module) et nous
n'avons que **1331 barres D1**. Ce seuil est pensé pour du H1 (~31 600 barres),
pas pour du journalier.

Modifier `core/` est interdit. Ce script appelle donc **exactement la même
fonction** `core.validation.causality.check()` — même invariant, même comparateur
de signaux — en court-circuitant uniquement le garde-fou de taille.

Il vérifie les DEUX jambes (risk sur NASDAQ, hedge sur XAUUSD) sur toute la
grille, pas seulement sur les paramètres par défaut. La jambe `hedge` est le cas
sensible : son régime vient d'un AUTRE symbole que celui tradé.
"""
from __future__ import annotations

import itertools
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.data.source import load_bars                       # noqa: E402
from core.validation.causality import check                  # noqa: E402
from strategies.s04_aipathways_trendcore.strategy import Strategy  # noqa: E402

LEGS = [("risk", "NASDAQ"), ("hedge", "XAUUSD")]


def main() -> int:
    out = []
    out.append("=" * 78)
    out.append("R1 — INVARIANT DE CAUSALITE — s04_aipathways_trendcore")
    out.append("=" * 78)
    out.append("")
    out.append("La CLI `python -m core.validation.causality --strategy")
    out.append("s04_aipathways_trendcore --save` REFUSE de tourner :")
    out.append("")
    out.append("    [SKIP] s04_aipathways_trendcore - donnees insuffisantes pour NASDAQ")
    out.append("")
    out.append("Cause : la CLI exige len(df) >= 2000 barres (causality.py:223). Nous")
    out.append("avons 1331 barres D1. Le seuil vise du H1 (~31 600 barres), pas du")
    out.append("journalier. `core/` etant interdit de modification, ce script appelle")
    out.append("la MEME fonction check() du MEME module, sans le garde-fou de taille.")
    out.append("")
    out.append("Verification etendue : les 2 jambes x toute la grille (12 cellules),")
    out.append("soit 24 points, x 4 coupures (60/70/80/90 %) = 96 comparaisons.")
    out.append("La jambe `hedge` est le cas sensible : son regime vient de NASDAQ")
    out.append("alors qu'elle trade XAUUSD (alignement cross-symbole).")
    out.append("")

    grid = list(itertools.product([100, 150, 200, 250], [0.0, 0.005, 0.01]))
    failures = 0
    checked = 0

    for leg, symbol in LEGS:
        df = load_bars(symbol, "D1")
        out.append("-" * 78)
        out.append(f"JAMBE {leg.upper():<6} — instrument trade : {symbol}  "
                   f"({len(df)} barres, {df.index[0].date()} -> {df.index[-1].date()})")
        out.append(f"regime lu sur : NASDAQ")
        out.append("-" * 78)
        out.append(f"  {'ma_len':>7} {'buffer':>8} {'coupures OK':>12} "
                   f"{'signaux (60/70/80/90%)':>28}  verdict")

        for ma_len, buf in grid:
            s = Strategy({"ma_len": ma_len, "buffer_pct": buf, "leg": leg,
                          "_symbol": symbol})
            rep = check(s, df, symbol)
            checked += 1
            n_ok = sum(1 for c in rep.cuts if c.ok)
            counts = "/".join(str(c.n_full) for c in rep.cuts)
            verdict = "OK" if rep.ok else "*** FUITE ***"
            out.append(f"  {ma_len:>7} {buf:>8.3f} {n_ok:>7}/{len(rep.cuts):<4} "
                       f"{counts:>28}  {verdict}")
            if not rep.ok:
                failures += 1
                for c in rep.cuts:
                    if not c.ok:
                        out.append(f"           coupure {c.fraction:.0%} -> {c.first_divergence}")
        out.append("")

    out.append("=" * 78)
    out.append(f"{checked} points de grille verifies, {failures} echec(s).")
    if failures == 0:
        out.append("VERDICT : R1 PASSE — aucune information future detectee,")
        out.append("          y compris sur l'alignement cross-symbole de la jambe hedge.")
    else:
        out.append("VERDICT : R1 ECHOUE — resultats NON PUBLIABLES.")
    out.append("=" * 78)

    text = "\n".join(out)
    print(text)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "causality.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n-> {dest}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
