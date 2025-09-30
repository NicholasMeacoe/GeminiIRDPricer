from datetime import timedelta
import os
import math
import pandas as pd
from gemini_ird_pricer.parsing import load_yield_curve
from gemini_ird_pricer.pricer import price_swap, solve_par_rate


def _fixture_path(name: str) -> str:
    here = os.path.dirname(__file__)
    return os.path.join(here, "data", name)


def test_par_rate_yields_zero_npv_with_fixture_curve():
    # Use repo root sample as a secondary check if present
    # Primary: dedicated test curve with fixed valuation date in filename to keep determinism
    curve_path = _fixture_path("SwapRates_20240115.csv")
    if not os.path.exists(curve_path):
        # Fallback to generic sample if renamed
        curve_path = _fixture_path("sample_curve.csv")
    yc = load_yield_curve(curve_path)
    # Set a 5-year maturity from valuation date approximation
    valuation_date = yc.index[0]
    maturity_date = valuation_date + timedelta(days=365 * 5)
    notional = 10_000_000

    # Solve par rate
    par = solve_par_rate(notional, maturity_date, yc)

    # Price at par should be ~0
    pv, schedule = price_swap(notional, par, maturity_date, yc)
    assert abs(pv) < 1.0  # within $1 tolerance on $10mm notional

    # Price away from par should have the expected sign: +1% -> payer PV negative (pay more fixed)
    pv_up, _ = price_swap(notional, par + 0.01, maturity_date, yc)
    pv_dn, _ = price_swap(notional, par - 0.01, maturity_date, yc)
    assert pv_up < 0
    assert pv_dn > 0

    # Basic schedule sanity
    assert len(schedule) > 0
    days = [row["days"] for row in schedule]
    assert days == sorted(days)
    # Discount factors in (0,1]
    for row in schedule:
        df = float(row["discount_factor"])
        assert df > 0 and df <= 1.0
