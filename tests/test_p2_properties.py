from __future__ import annotations
from datetime import datetime, timedelta
import math
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, strategies as st, settings

from gemini_ird_pricer.pricer import generate_payment_schedule, _interp_market_rate
from gemini_ird_pricer.utils import build_discount_function


# Strategies for random but bounded inputs
years_strategy = st.integers(min_value=1, max_value=30)
month_strategy = st.integers(min_value=1, max_value=11)
start_date_strategy = st.builds(
    lambda y, m, d: datetime(y, m, d),
    st.integers(min_value=2015, max_value=2026),
    st.integers(min_value=1, max_value=12),
    st.integers(min_value=1, max_value=28),  # avoid month-end pitfalls in generation
)
frequency_strategy = st.sampled_from([1, 2, 3, 4, 6, 12, 24, 5, 7, 9])  # include non-divisors to hit day-stepping


@settings(deadline=None, max_examples=50)
@given(start=start_date_strategy, years=years_strategy, freq=frequency_strategy)
def test_schedule_is_monotonic_and_bounded(start: datetime, years: int, freq: int):
    maturity = start + timedelta(days=years * 365)
    sched = generate_payment_schedule(start, maturity, freq)

    # All dates strictly greater than start and <= maturity
    assert all(d > start for d in sched)
    assert all(d <= maturity for d in sched)

    # Monotonic strictly increasing, no duplicates
    assert all(later > earlier for earlier, later in zip(sched, sched[1:]))

    # Bounded length: cannot exceed a safe cap (guard against infinite loops)
    assert len(sched) < 10000

    # If schedule not empty, last should equal maturity due to clamping logic
    if sched:
        assert sched[-1] == maturity


def _make_curve(valuation_date: datetime) -> pd.DataFrame:
    # Construct a tiny yield curve with a negative and positive rate and near-zero tenor
    dates = [valuation_date, valuation_date + timedelta(days=1), valuation_date + timedelta(days=365)]
    rates = [-0.01, 0.0, 0.15]  # decimals
    df = pd.DataFrame({"Rate": rates, "Maturity (Years)": [0.0, 1/365.0, 1.0]}, index=dates)
    return df


def _mk_arrays(df: pd.DataFrame, valuation_date: datetime):
    dates = np.array([(d - valuation_date).days for d in df.index])
    rates = df["Rate"].values.astype(float)
    return dates, rates


@given(
    target_days=st.integers(min_value=-100, max_value=2000),
    strategy=st.sampled_from(["linear_zero", "log_linear_df"]),
    policy=st.sampled_from(["clamp", "error"]),
)
@settings(deadline=None, max_examples=60)
def test_interp_edges_and_policies(target_days: int, strategy: str, policy: str):
    valuation_date = datetime(2023, 1, 1)
    df = _make_curve(valuation_date)
    dates, rates = _mk_arrays(df, valuation_date)
    disc = build_discount_function("exp_cont")

    if policy == "error" and (target_days < int(dates.min()) or target_days > int(dates.max())):
        with pytest.raises(ValueError):
            _ = _interp_market_rate(target_days, dates, rates, policy, strategy, disc)
        return

    # Should not raise for clamp or in-range
    r = _interp_market_rate(target_days, dates, rates, policy, strategy, disc)
    assert math.isfinite(r)

    # For linear_zero with clamp/in-range, interpolated rate lies within endpoint range
    if strategy == "linear_zero":
        lo, hi = float(rates.min()), float(rates.max())
        assert lo - 1e-9 <= r <= hi + 1e-9

    # For log_linear_df, just ensure non-NaN and non-negative DF equivalent
    # i.e., D = exp(-r*t) should be in (0, 1] for t>0 when r>=0; negative r => D>1 is allowed
    t = max(target_days / 365.0, 0.0)
    if t > 0:
        # DF computed with returned r should be positive
        df_val = float(disc(r, t))
        assert df_val > 0.0
