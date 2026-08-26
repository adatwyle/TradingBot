"""R5 — cohérence backtest / live, s05_flossbach_liqsweep.

POURQUOI CE SCRIPT EXISTE ICI ET PAS DANS core/
------------------------------------------------
`CLAUDE.md` (Phase 3) et `STRATEGY_RULES.md` (R5) prescrivent :

    python -m core.validation.conformance --strategy <id>

**Ce module n'existe pas dans le dépôt.** `core/validation/` contient
`causality.py`, `intrabar.py` et `selftest.py`, rien d'autre (verifie le
2026-08-16). La commande de la checklist d'admission est donc inexecutable pour
TOUTES les strategies, pas seulement celle-ci.

Je ne corrige pas `core/` (interdit par CLAUDE.md). Ce script fait localement ce
que ferait R5 : il rejoue `on_bar` barre par barre sur une fenetre d'historique
et compare a ce que `generate_signals` a produit sur la meme fenetre.

Chez nous, R5 est vrai par CONSTRUCTION : `on_bar` appelle litteralement
`precompute` + `generate_signals` et ne retient que la decision de la derniere
barre. Il n'existe pas deux implementations pouvant diverger. Le test verifie
que cette construction tient reellement — y compris le fait que `on_bar` ne voie
QUE `ctx.bars`, donc jamais le futur.
"""
from __future__ import annotations

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

import pandas as pd                                              # noqa: E402

from core.contracts.strategy import MarketContext                # noqa: E402
from core.data.instruments import get_spec                       # noqa: E402
from core.data.source import load_bars                           # noqa: E402
from strategies.S005_flossbach_liqsweep.strategy import Strategy   # noqa: E402


def main() -> int:
    L: list[str] = []
    L.append("=" * 88)
    L.append("R5 — COHERENCE BACKTEST / LIVE — s05_flossbach_liqsweep")
    L.append("=" * 88)
    L.append("")
    L.append("NOTE SUR L'OUTILLAGE COMMUN :")
    L.append("  `core/validation/conformance.py` N'EXISTE PAS dans le depot, alors que")
    L.append("  CLAUDE.md Phase 3 et la checklist d'admission de STRATEGY_RULES.md le")
    L.append("  prescrivent. core/validation/ ne contient que causality.py, intrabar.py")
    L.append("  et selftest.py. La lacune est signalee, pas corrigee (core/ interdit).")
    L.append("  Ce script fait localement le travail de R5.")
    L.append("")

    total_bars = total_sig = mismatch = 0
    for sym, tf in (("EURUSD", "H4"), ("XAUUSD", "H4"), ("SP500", "H1")):
        bars = load_bars(sym, tf)
        # Fenetre de test : les 600 dernieres barres, chacune rejouee en live.
        n = len(bars)
        start = n - 600

        strat = Strategy({"_symbol": sym})
        data = strat.precompute(bars, strat.params)
        bt = {pd.Timestamp(s.timestamp): s
              for s in strat.generate_signals(data, strat.params, n)}

        local_mis = 0
        for i in range(start, n):
            hist = bars.iloc[:i + 1]
            ctx = MarketContext(symbol=sym, timeframe=tf, bars=hist,
                                now=pd.Timestamp(bars.index[i]).to_pydatetime(),
                                spread=get_spec(sym).spread_pips)
            live = strat.on_bar(ctx)
            ts = pd.Timestamp(bars.index[i])
            ref = bt.get(ts)
            total_bars += 1
            if (live is None) != (ref is None):
                local_mis += 1
                continue
            if live is not None and ref is not None:
                total_sig += 1
                same = (live.side == ref.side
                        and abs(live.entry - ref.entry) < 1e-9
                        and abs(live.stop - ref.stop) < 1e-9
                        and abs((live.target or 0) - (ref.target or 0)) < 1e-9)
                if not same:
                    local_mis += 1
        mismatch += local_mis
        L.append(f"  {sym}/{tf} : 600 barres rejouees en live, "
                 f"{sum(1 for t in bt if t >= bars.index[start])} signaux backtest "
                 f"sur la fenetre, divergences : {local_mis}")

    L.append("")
    L.append(f"  TOTAL : {total_bars} barres rejouees, {total_sig} signaux compares, "
             f"{mismatch} divergences")
    L.append("")
    L.append("VERDICT R5 : " + ("PASSE" if mismatch == 0 else "ECHOUE"))
    if mismatch == 0:
        L.append("  `on_bar` et `generate_signals` prennent la meme decision sur le")
        L.append("  meme etat de marche. `on_bar` ne voit que ctx.bars — il ne peut")
        L.append("  donc pas utiliser de barre posterieure.")

    text = "\n".join(L)
    print(text)
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conformance.txt")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\n-> {dest}")
    return 0 if mismatch == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
