"""Unit tests for signal_lib (pure functions — no network, no data store).

Run:  python -m pytest research/test_signal_lib.py -q
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import signal_lib as sl


def _mk_day(prices: list[tuple[float, float, float, float]],
            volumes: list[float] | None = None) -> pd.DataFrame:
    """Build a 5min RTH day frame with the indicator columns find_breakouts needs."""
    idx = pd.date_range("2026-01-05 09:30", periods=len(prices), freq="5min",
                        tz="America/New_York")
    df = pd.DataFrame(prices, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = volumes if volumes is not None else [1000.0] * len(df)
    df["ema9"], df["ema21"], df["ema50"] = sl.ema(df.close, 9), sl.ema(df.close, 21), sl.ema(df.close, 50)
    df["atr14"] = sl.atr(df)
    df["vol_sma"] = df.volume.rolling(3, min_periods=1).mean()
    return df


class TestWilsonCI:
    def test_empty(self):
        lo, hi = sl.wilson_ci(0, 0)
        assert np.isnan(lo) and np.isnan(hi)

    def test_bounds_and_containment(self):
        lo, hi = sl.wilson_ci(5, 10)
        assert 0.0 <= lo < 0.5 < hi <= 1.0

    def test_extremes_stay_in_unit_interval(self):
        lo, hi = sl.wilson_ci(0, 8)
        assert lo == 0.0 and hi < 0.5
        lo, hi = sl.wilson_ci(8, 8)
        assert lo > 0.5 and hi == 1.0

    def test_narrows_with_n(self):
        w_small = np.subtract(*sl.wilson_ci(5, 10)[::-1])
        w_big = np.subtract(*sl.wilson_ci(500, 1000)[::-1])
        assert w_big < w_small


class TestWalkROutcome:
    def _flat_then(self, path: list[tuple[float, float, float, float]]):
        base = [(100.0, 100.5, 99.5, 100.0)] * 3
        return _mk_day(base + path)

    def test_long_target_hit(self):
        day = self._flat_then([(100, 104.2, 99.9, 104.0)])
        outcome, r = sl.walk_r_outcome(day, 2, "long", entry=100.0, stop=98.0, target=104.0)
        assert outcome == "target" and r == pytest.approx(2.0)

    def test_long_stop_hit(self):
        day = self._flat_then([(100, 100.1, 97.5, 98.0)])
        outcome, r = sl.walk_r_outcome(day, 2, "long", entry=100.0, stop=98.0, target=104.0)
        assert outcome == "stop" and r == -1.0

    def test_both_in_same_bar_counts_as_stop(self):
        day = self._flat_then([(100, 105.0, 97.0, 100.0)])
        outcome, r = sl.walk_r_outcome(day, 2, "long", entry=100.0, stop=98.0, target=104.0)
        assert outcome == "stop" and r == -1.0

    def test_eod_mark_to_close(self):
        day = self._flat_then([(100, 101.2, 99.8, 101.0)])
        outcome, r = sl.walk_r_outcome(day, 2, "long", entry=100.0, stop=98.0, target=104.0)
        assert outcome == "eod" and r == pytest.approx(0.5)

    def test_short_symmetry(self):
        day = self._flat_then([(100, 100.1, 95.8, 96.0)])
        outcome, r = sl.walk_r_outcome(day, 2, "short", entry=100.0, stop=102.0, target=96.0)
        assert outcome == "target" and r == pytest.approx(2.0)


class TestFirstTouchMultiHorizon:
    def test_no_touch_returns_none(self):
        day = _mk_day([(100, 100.5, 99.5, 100.0)] * 10)
        assert sl.first_touch_multi_horizon(day, 120.0) is None

    def test_hold_from_above(self):
        # price comes down to 99.5, touches, then closes back above at all horizons
        bars = [(101, 101.2, 100.8, 101.0)] * 3 + [(101, 101.0, 99.4, 100.5)] + \
               [(100.5, 101.5, 100.2, 101.2)] * 13
        day = _mk_day(bars)
        r = sl.first_touch_multi_horizon(day, 99.5, horizons=(3, 6, 12))
        assert r is not None and r["from_above"] is True
        assert r["held_h3"] and r["held_h6"] and r["held_h12"]

    def test_break_through_not_held(self):
        bars = [(101, 101.2, 100.8, 101.0)] * 3 + [(101, 101.0, 99.4, 99.6)] + \
               [(99.5, 99.6, 97.0, 97.2)] * 13
        day = _mk_day(bars)
        r = sl.first_touch_multi_horizon(day, 99.5, horizons=(3, 6))
        assert r is not None
        assert not r["held_h3"] and not r["held_h6"]
        assert r["pen_h3"] > r["rej_h3"]


class TestFindBreakouts:
    def test_long_breakout_detected_with_volume(self):
        # 6 tight bars then a wide up-close on 5x volume
        tight = [(100.0, 100.2, 99.9, 100.1)] * 8
        breakout = [(100.1, 101.5, 100.0, 101.4)]
        after = [(101.4, 102.5, 101.3, 102.4)] * 4
        vols = [1000.0] * 8 + [5000.0] + [1200.0] * 4
        day = _mk_day(tight + breakout + after, vols)
        events = sl.find_breakouts(day)
        assert len(events) >= 1
        ev = events[0]
        # NOTE: vol_sma includes the breakout bar itself (convention frozen with
        # study_01) — the spike raises its own baseline: 5000/((1k+1k+5k)/3) = 2.14
        assert ev["side"] == "long" and ev["vol_ratio"] == pytest.approx(2.14, abs=0.01)
        assert ev["stop"] < ev["entry"]

    def test_no_breakout_without_compression(self):
        # wide-ranging bars — window range always exceeds compress_range_atr * ATR
        rng = np.random.default_rng(7)
        bars = []
        px = 100.0
        for _ in range(20):
            px += float(rng.normal(0, 2.0))
            bars.append((px, px + 3.0, px - 3.0, px + float(rng.normal(0, 1.5))))
        day = _mk_day(bars)
        events = sl.find_breakouts(day, compress_range_atr=0.3)
        assert events == []
