"""Tests for the Weija cleaner and loader (run: python -m pytest tests -q).

  * ramp_mask flags runs of >= RAMP_MIN collinear points (hidden linear interpolation) and
    nothing in a noisy or flat series
  * the cleaned file honours the cleaning rules, and load_weija gives a bounded-DPS-ready
    dataset that stays inside the real co-sampled window
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "src"); sys.path.insert(0, "src/data")
from clean_weija import RAMP_MIN, RANGE, ramp_mask  # noqa: E402

rng = np.random.default_rng(0)
t = pd.Series(pd.date_range("2018-11-01", periods=60, freq="32min"))


def test_ramp_mask_finds_interpolated_run():
    v = rng.normal(30, 0.5, 60)
    v[20:30] = np.linspace(v[20], v[29], 10)            # 10 collinear points = interpolation
    m = ramp_mask(t, v)
    assert m[20:30].all() and m.sum() == 10


def test_ramp_mask_ignores_short_runs_noise_and_flat():
    v = rng.normal(30, 0.5, 60)
    v[10:10 + RAMP_MIN - 1] = np.linspace(v[10], v[10 + RAMP_MIN - 2], RAMP_MIN - 1)   # too short
    v[40:50] = 31.0                                      # flat: zero slope is not a ramp
    assert not ramp_mask(t, v).any()


def test_ramp_mask_catches_per_row_ramp_on_irregular_time():
    """the real Weija case: EC falls by exactly 0.133219 per ROW while timestamps are irregular"""
    tt = t + pd.to_timedelta(rng.integers(0, 12, len(t)), unit="min")
    v = rng.normal(180, 2, 60)
    v[15:35] = 183.439 - 0.133219 * np.arange(20)
    m = ramp_mask(tt, v)
    assert m[15:35].all() and m.sum() == 20


CLEAN = Path("data/clean/weija_cycles.csv")


@pytest.mark.skipif(not CLEAN.exists(), reason="run src/data/clean_weija.py first")
def test_cleaned_file_respects_rules():
    c = pd.read_csv(CLEAN, parse_dates=["t"])
    for v, (lo, hi) in RANGE.items():
        assert c[v].dropna().between(lo, hi).all()
    assert c.t.is_monotonic_increasing


@pytest.mark.skipif(not CLEAN.exists() or not Path("results/weija/check_b_runs.csv").exists(),
                    reason="run clean_weija.py and weija_phase1.py first")
def test_load_weija_window_and_split():
    from sim.data import load_weija
    ds = load_weija()
    assert ds.params == ["T", "EC"] and not np.isnan(ds.X).any()
    assert ds.t.max() < pd.Timestamp("2019-01-05")      # real T (Sensor Two) ends early Jan
    assert 30 < ds.step_min < 35
    assert 0.75 < ds.test.mean() < 0.85                 # 80 % of the time span is test
    assert (pd.to_datetime(ds.events.start) >= ds.t[ds.test].iloc[0]).all()
