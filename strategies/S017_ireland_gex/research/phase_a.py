"""S017 ireland_gex — Phase A incremental harness (H1 / H2 / A+ setups).

ONE command, re-runnable any time; each run reloads ALL snapshotted days in
C:/db/tradingBot/S017/ and rewrites research/PHASE_A_LOG.md (git carries the
history of successive runs — the log itself is always the current full picture).

    python research/phase_a.py

Measures (spec-strategie.md §4-5, defaults frozen in manifest.yaml):
  H1  — reaction at major GEX levels vs placebo levels (offset / round / random)
        at first touch, horizons 15/30/60 min. Net effect + Wilson 95% CI.
  H2  — premarket gamma regime vs realized day behaviour (RV, range, trend
        efficiency). 1 point per snapshot day, no setup needed.
  A+  — full 5-condition checklist applied to every snapshot day: count of
        complete setups and their outcome in R.

No backtest engine (R9): pure signal measurement, no costs, no sizing.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import signal_lib as sl

if hasattr(sys.stdout, "reconfigure"):        # Windows console is cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).parent / "PHASE_A_LOG.md"
HORIZONS = (3, 6, 12)          # 5min bars -> 15 / 30 / 60 min
H_LABEL = {3: "15min", 6: "30min", 12: "60min"}


# ── H1 — level reaction event study ─────────────────────────────────────────
def run_h1(gex_days: list[sl.GexDay], df5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gd in gex_days:
        day = df5[df5.index.date == pd.Timestamp(gd.date).date()]
        if len(day) < 5:
            continue
        g = pd.read_csv(gd.path)
        universe = g[(g.strike - gd.spot).abs() <= gd.spot * sl.LEVEL_UNIVERSE_PCT / 100.0]
        groups = sl.placebo_levels(gd, universe)
        for group, levels in groups.items():
            for lv in levels:
                r = sl.first_touch_multi_horizon(day, lv, HORIZONS)
                if r:
                    rows.append({"date": gd.date, "group": group, **r})
    return pd.DataFrame(rows)


def h1_table(ev: pd.DataFrame) -> list[str]:
    lines = ["### H1 — réaction aux niveaux (premier contact, tous jours agrégés)", ""]
    if not len(ev):
        return lines + ["Aucun contact mesurable (pas de jour GEX + OHLCV complet).", ""]
    lines += ["| horizon | groupe | n | P(hold) [IC 95%] | rejet médian (ATR) | pénétration médiane (ATR) |",
              "|---|---|---|---|---|---|"]
    effects = []
    for h in HORIZONS:
        for group, sub in ev.groupby("group"):
            k = int(sub[f"held_h{h}"].sum())
            n = len(sub)
            lo, hi = sl.wilson_ci(k, n)
            lines.append(
                f"| {H_LABEL[h]} | {group} | {n} | {k / n * 100:.0f}% [{lo * 100:.0f}-{hi * 100:.0f}%] "
                f"| {sub[f'rej_h{h}'].median():.2f} | {sub[f'pen_h{h}'].median():.2f} |")
        maj = ev[ev.group == "major"]
        pla = ev[ev.group != "major"]
        if len(maj) and len(pla):
            p_m = maj[f"held_h{h}"].mean()
            p_p = pla[f"held_h{h}"].mean()
            effects.append(f"effet net h={H_LABEL[h]} : P(hold|major) − P(hold|placebo) = "
                           f"{(p_m - p_p) * 100:+.0f} pts (n={len(maj)} vs {len(pla)})")
    lines.append("")
    lines += [f"- {e}" for e in effects]
    lines.append("")
    return lines


# ── H2 — regime vs realized behaviour ───────────────────────────────────────
def run_h2(gex_days: list[sl.GexDay], df5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gd in gex_days:
        day = df5[df5.index.date == pd.Timestamp(gd.date).date()]
        if len(day) < 5:
            continue
        o, c = day.open.iloc[0], day.close.iloc[-1]
        hi, lo = day.high.max(), day.low.min()
        lr = np.log(day.close / day.close.shift()).dropna()
        rows.append({
            "date": gd.date,
            "regime": gd.regime,
            "net_gex_musd": round(gd.net_gex / 1e6),
            "n_bars": len(day),
            "partial": len(day) < sl.RTH_BARS_FULL,
            "rv_pct": round(float(np.sqrt((lr ** 2).sum())) * 100, 3),
            "range_pct": round(float((hi - lo) / o) * 100, 3),
            "efficiency": round(float(abs(c - o) / (hi - lo)) if hi > lo else np.nan, 3),
        })
    return pd.DataFrame(rows)


def h2_table(days: pd.DataFrame) -> list[str]:
    lines = ["### H2 — régime gamma pré-market vs comportement réalisé (1 pt/jour)", ""]
    if not len(days):
        return lines + ["Aucun jour mesurable.", ""]
    lines += ["| régime | n jours | RV 5min médiane (%) | range médian (%) | efficience médiane |",
              "|---|---|---|---|---|"]
    for reg, sub in days.groupby("regime"):
        lines.append(f"| {reg} | {len(sub)} | {sub.rv_pct.median():.2f} "
                     f"| {sub.range_pct.median():.2f} | {sub.efficiency.median():.2f} |")
    lines += ["", "Jours (détail) :", "",
              days.to_markdown(index=False), ""]
    return lines


# ── A+ setups — full 5-condition checklist ──────────────────────────────────
def run_setups(gex_days: list[sl.GexDay], df5: pd.DataFrame,
               dstack: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for gd in gex_days:
        dts = pd.Timestamp(gd.date).date()
        day = df5[df5.index.date == dts]
        if len(day) < sl.COMPRESS_BARS + 2:
            continue
        drow = dstack[dstack.index.date == dts]
        bull_d = bool(drow.bull_known.iloc[0]) if len(drow) else False
        bear_d = bool(drow.bear_known.iloc[0]) if len(drow) else False
        for b in sl.find_breakouts(day):
            side = b["side"]
            # condition 3 — daily + 5min alignment, same direction as breakout
            if side == "long" and not (bull_d and b["aligned"]):
                continue
            if side == "short" and not (bear_d and b["aligned"]):
                continue
            # condition 4 — breakout volume
            if b["vol_ratio"] < sl.VOL_MULT:
                continue
            # condition 1 — compression window overlaps a major GEX level
            tol = sl.NEAR_LEVEL_PCT / 100.0 * b["entry"]
            at_level = [k for k in gd.majors
                        if b["w_low"] - tol <= k <= b["w_high"] + tol]
            if not at_level:
                continue
            # condition 5 — target = next major in trade direction, else 2R
            risk = abs(b["entry"] - b["stop"])
            if side == "long":
                nxt = [k for k in gd.majors if k > b["entry"] + tol]
                target = min(nxt) if nxt else b["entry"] + 2 * risk
            else:
                nxt = [k for k in gd.majors if k < b["entry"] - tol]
                target = max(nxt) if nxt else b["entry"] - 2 * risk
            rr = abs(target - b["entry"]) / risk
            if rr < sl.RR_MIN:
                # next major too close -> fall back to pure 2R (spec §3.6)
                target = b["entry"] + 2 * risk if side == "long" else b["entry"] - 2 * risk
                rr = 2.0
            outcome, r = sl.walk_r_outcome(day, b["bar_idx"], side,
                                           b["entry"], b["stop"], target)
            rows.append({"date": gd.date, "ts": str(b["ts"]), "side": side,
                         "level": at_level[0], "regime": gd.regime,
                         "vol_ratio": round(b["vol_ratio"], 2), "rr": round(rr, 2),
                         "outcome": outcome, "realized_r": r})
    return pd.DataFrame(rows)


def setups_table(st: pd.DataFrame, gex_days: list[sl.GexDay]) -> list[str]:
    lines = ["### Setups A+ (checklist 5 conditions, jours snapshotés uniquement)", ""]
    if not len(st):
        return lines + [f"**0 setup complet** sur {len(gex_days)} jour(s) snapshoté(s). "
                        "Attendu à ce stade : la checklist est très sélective "
                        "(la vidéo revendique 2-3 setups A+/semaine).", ""]
    lines += ["| date | heure | side | niveau | régime | vol | RR | issue | R réalisé |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in st.itertuples():
        lines.append(f"| {r.date} | {r.ts[11:16]} | {r.side} | {r.level:.0f} | {r.regime} "
                     f"| {r.vol_ratio}x | {r.rr} | {r.outcome} | {r.realized_r:+.2f} |")
    tot = st.realized_r.sum()
    lines += ["", f"**Total : {len(st)} setup(s), somme {tot:+.2f} R** "
              f"(sans coûts — étude de signal, pas un backtest).", ""]
    return lines


# ── verdicts ────────────────────────────────────────────────────────────────
def verdicts(ev: pd.DataFrame, h2days: pd.DataFrame, st: pd.DataFrame,
             gex_days: list[sl.GexDay]) -> list[str]:
    n_days = len(gex_days)
    n_maj = int((ev.group == "major").sum()) if len(ev) else 0
    lines = ["## Verdicts provisoires", "",
             "| hypothèse | n actuel | seuil de mesure | verdict |",
             "|---|---|---|---|"]
    lines.append(f"| H1 (réaction niveaux) | {n_maj} contacts majeurs / {n_days} jour(s) "
                 f"| ≥ 100 contacts (≈ 20-30 jours) | **n insuffisant** — plomberie validée, aucun verdict |")
    npos = int((h2days.regime == "positive").sum()) if len(h2days) else 0
    nneg = int((h2days.regime == "negative").sum()) if len(h2days) else 0
    lines.append(f"| H2 (régime vs RV) | {npos} jour(s) + / {nneg} jour(s) − "
                 f"| ≥ 60 jours, les 2 régimes représentés | **n insuffisant** |")
    lines.append(f"| Setups A+ | {len(st)} setup(s) sur {n_days} jour(s) "
                 f"| ≥ 30 setups (H4 non conclusif en deçà) | **n insuffisant** |")
    lines.append("")
    return lines


# ── main ────────────────────────────────────────────────────────────────────
def main() -> None:
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    gex_days = sl.list_gex_days()
    df5 = sl.load_5min()
    dstack = sl.daily_stack(sl.load_daily())

    ev = run_h1(gex_days, df5)
    h2days = run_h2(gex_days, df5)
    st = run_setups(gex_days, df5, dstack)

    quality_notes = []
    for gd in gex_days:
        if gd.quality != "ok":
            quality_notes.append(
                f"- {gd.date} : {gd.n_premarket_rows} captures « premarket » le même jour — "
                f"le fichier canonique correspond à la DERNIÈRE (asof {gd.asof}, spot {gd.spot}) ; "
                f"si capturé après l'open, les contacts H1 de ce jour sont à interpréter avec prudence.")
    ohlcv_last = df5.index[-1] if len(df5) else None

    lines = [
        "# PHASE_A_LOG — S017 ireland_gex",
        "",
        f"**Dernier run** : {run_ts} — `python research/phase_a.py` (relançable à volonté ; "
        "recharge TOUS les jours snapshotés et réécrit ce fichier)",
        "",
        "## Inventaire données",
        "",
        f"- Snapshots GEX (pré-market canoniques) : **{len(gex_days)} jour(s)** — "
        + (", ".join(f"{g.date} ({g.regime}, majeurs {'/'.join(f'{m:.0f}' for m in g.majors)})"
                     for g in gex_days) if gex_days else "aucun"),
        f"- OHLCV 5min : {df5.index[0].date()} → {ohlcv_last.date() if ohlcv_last is not None else '-'} "
        f"({df5.index.normalize().nunique()} jours, {len(df5)} barres RTH)",
        f"- Collecte planifiée : tâche Windows 14:55 CH jours ouvrés → C:/db/tradingBot/S017/",
        "",
    ]
    if quality_notes:
        lines += ["**Qualité données :**", ""] + quality_notes + [""]

    lines += ["## Mesures", ""]
    lines += h1_table(ev)
    lines += h2_table(h2days)
    lines += setups_table(st, gex_days)
    lines += verdicts(ev, h2days, st, gex_days)
    lines += [
        "## Validation croisée externe (best-effort, 2026-08-26)",
        "",
        "Aucun dashboard GEX gratuit sans compte n'est lisible par simple requête HTTP : "
        "GravityGEX et FlashAlpha renvoient des pages vides (rendu JS côté client), "
        "AlgoStorm est derrière un challenge Cloudflare (non contourné — interdit). "
        "**Passé** ; la seule validation externe reste la comparaison visuelle bootstrap "
        "avec les frames ITMatrix de la vidéo (géométrie des niveaux concordante).",
        "",
        "## Jalons attendus",
        "",
        "- **n ≥ 5 jours** : rodage agrégation multi-jours ; premiers ratios hold major vs placebo "
        "(bruit dominant, aucun verdict) ; vérifier que chaque jour produit 2-5 majeurs et des contacts.",
        "- **n ≥ 20 jours** : ~50-100 contacts majeurs attendus → première lecture H1 avec IC exploitables ; "
        "H2 encore court (viser 60 j) ; premiers setups A+ si le marché en offre.",
        "",
        "*Étude de signal Phase A — pas un backtest (R9). Coûts, slippage et sizing absents par construction.*",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    if len(ev):
        ev.to_csv(OUT.parent / "phase_a_h1_contacts.csv", index=False)
    print("\n".join(lines))
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
