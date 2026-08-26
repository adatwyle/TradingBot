"""S017 study 02 — day-0 plumbing check for H1: do today's premarket GEX levels
mark intraday reaction points, compared to placebo levels?

With only the day-0 snapshot (no GEX history yet), this is a PLUMBING VALIDATION
+ anecdote, NOT a test of H1 (n = 1 day). The same code re-runs on every
accumulated snapshot day, so n grows daily with the collection pipeline.

Method (spec §4 H1): for each level, find the FIRST touch of the level by a 5min
RTH bar (low <= level <= high). Measure the forward excursion over the next
H bars: rejection = max excursion AWAY from the touch side, in ATR units.
Compare major GEX levels vs placebo levels (half-strikes offset by $2.50 and
non-major round strikes in the same universe).

Output: research/results_study02_<date>.md
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

DB = Path("C:/db/tradingBot/S017")
HORIZON_BARS = 6          # 30 min forward
NEAR_UNIVERSE_PCT = 2.0   # same universe as level detection


def load_day_5min(day: str) -> pd.DataFrame:
    df = pd.read_csv(DB / "ohlcv" / "SPY_5min.csv", index_col=0, parse_dates=True)
    df = df.tz_convert("America/New_York").between_time("09:30", "15:55")
    df = df[df.index.date == pd.Timestamp(day).date()]
    # ATR from full series would leak across days; day-local TR mean is enough here
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    df = df.assign(atr=tr.ewm(alpha=1 / 14, adjust=False).mean())
    return df


def first_touch_reaction(df: pd.DataFrame, level: float) -> dict | None:
    """First bar touching the level; forward rejection/penetration in ATR."""
    touch = df[(df.low <= level) & (df.high >= level)]
    if not len(touch):
        return None
    i = df.index.get_loc(touch.index[0])
    bar = df.iloc[i]
    fwd = df.iloc[i + 1: i + 1 + HORIZON_BARS]
    if len(fwd) < 2 or not np.isfinite(bar.atr) or bar.atr <= 0:
        return None
    approach_from_above = bar.open > level  # price came down onto the level
    if approach_from_above:
        rejection = (fwd.high.max() - level) / bar.atr      # bounce up
        penetration = (level - fwd.low.min()) / bar.atr     # break down
    else:
        rejection = (level - fwd.low.min()) / bar.atr       # rejection down
        penetration = (fwd.high.max() - level) / bar.atr    # break up
    return dict(level=level, touch_time=str(touch.index[0]),
                from_above=approach_from_above,
                rejection_atr=round(rejection, 2),
                penetration_atr=round(penetration, 2))


def main(day: str | None = None) -> None:
    day = day or datetime.now().strftime("%Y-%m-%d")
    gex_path = DB / "gex" / f"SPY_gex_{day}.csv"
    if not gex_path.exists():
        raise SystemExit(f"no GEX snapshot for {day}: {gex_path}")
    g = pd.read_csv(gex_path)
    spot = g.spot.iloc[0]
    df = load_day_5min(day)
    if not len(df):
        raise SystemExit(f"no 5min RTH bars for {day} (market not open yet?)")

    uni = g[(g.strike - spot).abs() <= spot * NEAR_UNIVERSE_PCT / 100.0]
    majors = uni[uni.is_major].strike.tolist()
    placebo_offset = [k + 2.5 for k in majors] + [k - 2.5 for k in majors]
    placebo_round = [k for k in uni[~uni.is_major].strike
                     if k % 5 == 0 and min(abs(k - m) for m in majors) > 2.5]

    rows = []
    for name, levels in [("major", majors),
                         ("placebo_offset", placebo_offset),
                         ("placebo_round", placebo_round)]:
        for lv in levels:
            r = first_touch_reaction(df, lv)
            if r:
                rows.append({"group": name, **r})
    res = pd.DataFrame(rows)

    lines = [f"# Study 02 — day-0 GEX levels vs intraday (plumbing for H1) — {day}",
             "",
             f"Premarket snapshot: spot {spot:.2f}, majors {majors}, "
             f"net regime {'negative' if g.gex.sum() < 0 else 'positive'}",
             f"Intraday bars available: {len(df)} "
             f"({df.index[0].time()} .. {df.index[-1].time()} ET)",
             f"Horizon: {HORIZON_BARS} bars (30 min) after first touch; "
             f"units = day ATR at touch", ""]
    if len(res):
        lines += ["| group | n touched | median rejection (ATR) | median penetration (ATR) |",
                  "|---|---|---|---|"]
        for grp, sub in res.groupby("group"):
            lines.append(f"| {grp} | {len(sub)} | {sub.rejection_atr.median():.2f} "
                         f"| {sub.penetration_atr.median():.2f} |")
        lines += ["", "## Touch detail", "",
                  res.to_markdown(index=False)]
    else:
        lines.append("No level touched today (price stayed away from all levels).")
    lines += ["", "**Caveat**: n = 1 day -> anecdotal. Re-run daily as snapshots",
              "accumulate; aggregate across days once n_days >= 20."]

    out = Path(__file__).parent / f"results_study02_{day}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
