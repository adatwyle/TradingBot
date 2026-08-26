# Study 02 — day-0 GEX levels vs intraday (plumbing for H1) — 2026-08-26

Premarket snapshot: spot 766.23, majors [760.0, 765.0], net regime negative
Intraday bars available: 22 (09:30:00 .. 11:15:00 ET)
Horizon: 6 bars (30 min) after first touch; units = day ATR at touch

| group | n touched | median rejection (ATR) | median penetration (ATR) |
|---|---|---|---|
| major | 1 | 0.17 | 1.75 |

## Touch detail

| group   |   level | touch_time                | from_above   |   rejection_atr |   penetration_atr |
|:--------|--------:|:--------------------------|:-------------|----------------:|------------------:|
| major   |     765 | 2026-08-26 09:30:00-04:00 | False        |            0.17 |              1.75 |

**Caveat**: n = 1 day -> anecdotal. Re-run daily as snapshots
accumulate; aggregate across days once n_days >= 20.