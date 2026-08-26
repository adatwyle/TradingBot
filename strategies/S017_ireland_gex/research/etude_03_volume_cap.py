"""S017 etude 03 — H3/H3b : fenetre de volume bornee + definitions de compression.

Approfondissement de l'etude 01 bootstrap sur les ~60 jours d'OHLCV 5min
disponibles (AUCUN besoin de GEX — le filtre volume est mesure sur TOUTES les
cassures de compression, condition GEX exclue pour isoler l'effet volume).

Variantes DECLAREES avant mesure :
  - vol_mult  : plage manifest [1.2, 1.5, 2.0, 2.5]
  - vol_cap   : {none, 2.0, 2.5, 3.0} — H3b declaree spec §3.5 le 2026-08-26
    (justification : etude 01 bootstrap, tranche 1.5-2x favorable, >2x defavorable)
  - compression : compress_bars {4, 6, 8, 12} x compress_range_atr {1.0, 1.5, 2.0, 2.5}
    (plages manifest §3.5) — effet mesure sur le taux de suivi des cassures a volume

Sortie : research/etude_03_volume_cap.md (reecrit a chaque run — git = historique).
Usage :  python research/etude_03_volume_cap.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from itertools import product
from pathlib import Path

import pandas as pd

import signal_lib as sl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).parent / "etude_03_volume_cap.md"

VOL_MULTS = [1.2, 1.5, 2.0, 2.5]
VOL_CAPS = [None, 2.0, 2.5, 3.0]
COMPRESS_GRID = list(product([4, 6, 8, 12], [1.0, 1.5, 2.0, 2.5]))


def collect_breakouts(df5: pd.DataFrame, compress_bars: int,
                      compress_range_atr: float) -> pd.DataFrame:
    events = []
    for _, day in df5.groupby(df5.index.date):
        if len(day) < compress_bars + sl.VOL_SMA:
            continue
        events += sl.find_breakouts(day, compress_bars=compress_bars,
                                    compress_range_atr=compress_range_atr)
    return pd.DataFrame(events)


def stats_row(sub: pd.DataFrame, label: str) -> str:
    if not len(sub):
        return f"| {label} | 0 | - | - | - |"
    n = len(sub)
    k = int((sub.outcome == "target1r").sum())
    lo, hi = sl.wilson_ci(k, n)
    return (f"| {label} | {n} | {k / n * 100:.0f}% [{lo * 100:.0f}-{hi * 100:.0f}%] "
            f"| {(sub.outcome == 'stop').mean() * 100:.0f}% | {sub.mfe.median():.2f} |")


def main() -> None:
    df5 = sl.load_5min()
    n_days = df5.index.normalize().nunique()

    # ── part 1 — vol_mult x vol_cap on the DEFAULT compression definition ────
    ev = collect_breakouts(df5, sl.COMPRESS_BARS, sl.COMPRESS_RANGE_ATR)
    lines = [
        f"# Étude 03 — fenêtre de volume bornée (H3/H3b) + compression — {datetime.now():%Y-%m-%d}",
        "",
        f"Données : SPY 5min RTH {df5.index[0].date()} → {df5.index[-1].date()} "
        f"({n_days} jours, {len(df5)} barres). Cassures de compression TOUTES "
        "(condition GEX exclue — isole l'effet volume).",
        f"Défauts compression : {sl.COMPRESS_BARS} barres ≤ {sl.COMPRESS_RANGE_ATR}×ATR14. "
        f"Total cassures : **{len(ev)}**.",
        "",
        "Variantes déclarées avant mesure : `vol_mult` (plage manifest), `vol_cap` "
        "(H3b, spec §3.5 déclarée 2026-08-26), grille compression (plages manifest). "
        f"**Nombre total de variantes balayées : {len(VOL_MULTS) * len(VOL_CAPS)} fenêtres volume "
        f"+ {len(COMPRESS_GRID)} définitions compression** — à corriger pour comparaisons "
        "multiples dans toute interprétation (aucun seuil ne sera promu défaut sur ce seul balayage).",
        "",
        "## 1. Fenêtre de volume `[vol_mult, vol_cap)` — compression par défaut",
        "",
        "| fenêtre | n | +1R avant stop [IC 95%] | stoppé | MFE médiane (R) |",
        "|---|---|---|---|---|",
        stats_row(ev, "toutes cassures (référence)"),
        stats_row(ev[ev.vol_ratio < 1.2], "< 1.2× (anti-population)"),
    ]
    for vm in VOL_MULTS:
        for vc in VOL_CAPS:
            sub = ev[(ev.vol_ratio >= vm) & (ev.vol_ratio < (vc or 1e9))]
            if vc is not None and vc <= vm:
                continue
            label = f"[{vm}, {vc if vc else '∞'})"
            lines.append(stats_row(sub, label))
    lines.append("")

    # focused H3b read: the exhaustion tranche
    hi_tr = ev[ev.vol_ratio >= 2.0]
    mid_tr = ev[(ev.vol_ratio >= 1.5) & (ev.vol_ratio < 2.0)]
    lines += [
        "### Lecture H3b (tranche épuisement)",
        "",
        f"- Tranche 1.5-2.0× : n={len(mid_tr)}, +1R {mid_tr.outcome.eq('target1r').mean() * 100:.0f}%"
        if len(mid_tr) else "- Tranche 1.5-2.0× : n=0",
        f"- Tranche ≥ 2.0×  : n={len(hi_tr)}, +1R {hi_tr.outcome.eq('target1r').mean() * 100:.0f}%"
        if len(hi_tr) else "- Tranche ≥ 2.0× : n=0",
        "",
    ]

    # ── part 2 — EMA-aligned subpopulation (closer to the real system) ───────
    al = ev[ev.aligned]
    lines += [
        "## 2. Sous-population 5min-EMA-alignée (plus proche du système réel)",
        "",
        "| fenêtre | n | +1R avant stop [IC 95%] | stoppé | MFE médiane (R) |",
        "|---|---|---|---|---|",
        stats_row(al, "alignées, toutes"),
        stats_row(al[(al.vol_ratio >= 1.5)], "alignées, ≥ 1.5×"),
        stats_row(al[(al.vol_ratio >= 1.5) & (al.vol_ratio < 2.0)], "alignées, [1.5, 2.0)"),
        stats_row(al[al.vol_ratio >= 2.0], "alignées, ≥ 2.0×"),
        "",
    ]

    # ── part 3 — compression definition sweep ────────────────────────────────
    lines += [
        "## 3. Définitions de compression (cassures à volume ≥ 1.5×, sans cap)",
        "",
        "| compress_bars | range ≤ ×ATR | n cassures | n vol≥1.5× | +1R [IC 95%] | stoppé |",
        "|---|---|---|---|---|---|",
    ]
    for cb, cr in COMPRESS_GRID:
        evv = collect_breakouts(df5, cb, cr)
        sub = evv[evv.vol_ratio >= sl.VOL_MULT] if len(evv) else evv
        if len(sub):
            k = int((sub.outcome == "target1r").sum())
            lo, hi = sl.wilson_ci(k, len(sub))
            lines.append(f"| {cb} | {cr} | {len(evv)} | {len(sub)} "
                         f"| {k / len(sub) * 100:.0f}% [{lo * 100:.0f}-{hi * 100:.0f}%] "
                         f"| {(sub.outcome == 'stop').mean() * 100:.0f}% |")
        else:
            lines.append(f"| {cb} | {cr} | {len(evv)} | 0 | - | - |")
    lines += [
        "",
        "## Verdict provisoire",
        "",
        "- Les n par cellule restent faibles : **rien n'est établi** ; ce balayage sert à "
        "suivre la stabilité des directions d'effet au fil de l'accumulation quotidienne.",
        "- Décision de promotion d'un seuil en défaut : uniquement si la direction persiste "
        "avec n ≥ 30 par tranche ET après correction pour le nombre de variantes balayées.",
        "",
        "*Relançable : `python research/etude_03_volume_cap.py` — réécrit ce fichier sur "
        "toutes les données accumulées.*",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
