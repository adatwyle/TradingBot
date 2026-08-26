# Study 01 — volume breakout follow-through (H3) — 2026-08-26

Data: SPY 5min RTH 2026-06-02 .. 2026-08-26 (60 days, 4624 bars)
Defaults: compress=6 bars <= 1.5xATR14, vol_mult=1.5, stop=min(window_low,EMA50)-0.25xATR

Total compression breakouts: 134

## All breakouts

| population | n | +1R before stop | stopped | median MFE (R) |
|---|---|---|---|---|
| volume >= 1.5x | 18 | 39% | 33% | 0.61 |
| volume < 1.5x | 116 | 32% | 34% | 0.67 |

| vol_ratio bucket | n | +1R before stop | stopped | median MFE (R) |
|---|---|---|---|---|
| 0-1.0 | 87 | 29% | 37% | 0.62 |
| 1.0-1.2 | 18 | 44% | 28% | 0.76 |
| 1.2-1.5 | 11 | 36% | 27% | 0.74 |
| 1.5-2.0 | 7 | 57% | 29% | 1.01 |
| 2.0-inf | 11 | 27% | 36% | 0.48 |

## 5min-EMA-aligned only

| population | n | +1R before stop | stopped | median MFE (R) |
|---|---|---|---|---|
| volume >= 1.5x | 4 | 50% | 0% | 0.74 |
| volume < 1.5x | 53 | 19% | 23% | 0.57 |

| vol_ratio bucket | n | +1R before stop | stopped | median MFE (R) |
|---|---|---|---|---|
| 0-1.0 | 40 | 15% | 22% | 0.54 |
| 1.0-1.2 | 8 | 25% | 25% | 0.72 |
| 1.2-1.5 | 5 | 40% | 20% | 0.57 |
| 1.5-2.0 | 2 | 100% | 0% | 1.02 |
| 2.0-inf | 2 | 0% | 0% | 0.40 |

## EMA alignment frequency (feasibility)

- Daily stack (known at open, spread >= 0.3 ATR): bull 47% / bear 0% / chop 53% of 60 days
- 5min stack aligned+spread: long 35% / short 33% of bars
