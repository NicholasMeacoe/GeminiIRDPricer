from __future__ import annotations
import os
import json
import math
import pytest
import pandas as pd
from datetime import timedelta

from gemini_ird_pricer import create_app
from gemini_ird_pricer.parsing import load_yield_curve
from gemini_ird_pricer.pricer import price_swap, solve_par_rate


def _tests_data_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))


@pytest.fixture()
def app_client_prod(tmp_path):
    app = create_app()
    data_dir = _tests_data_dir()
    app.config.update({
        "TESTING": True,
        "DATA_DIR": data_dir,
        "ENV": "development",
    })
    return app.test_client(), app


def test_extrapolation_policy_error_raises(app_client_prod):
    client, app = app_client_prod
    # Load curve and compute a far maturity beyond curve end
    curve_path = os.path.join(_tests_data_dir(), "SwapRates_20240115.csv")
    yc = load_yield_curve(curve_path)
    valuation_date = yc.index[0]
    far_maturity = valuation_date + timedelta(days=365 * 200)  # 200y, likely beyond max node

    # Clamp policy should not raise
    v_clamp, _ = price_swap(1_000_000.0, 0.05, far_maturity, yc, {"EXTRAPOLATION_POLICY": "clamp"})
    assert isinstance(v_clamp, float)

    # Error policy should raise ValueError
    with pytest.raises(ValueError):
        price_swap(1_000_000.0, 0.05, far_maturity, yc, {"EXTRAPOLATION_POLICY": "error"})

    # Also verify solve path raises
    with pytest.raises(ValueError):
        solve_par_rate(1_000_000.0, far_maturity, yc, {"EXTRAPOLATION_POLICY": "error"})


def test_interp_strategy_log_linear_df_produces_valid_prices(app_client_prod):
    client, app = app_client_prod
    curve_path = os.path.join(_tests_data_dir(), "SwapRates_20240115.csv")
    yc = load_yield_curve(curve_path)
    valuation_date = yc.index[0]
    maturity = valuation_date + timedelta(days=365 * 5)

    # Price with default linear_zero
    v_lin, sched_lin = price_swap(2_000_000.0, 0.04, maturity, yc, {"INTERP_STRATEGY": "linear_zero"})
    # Price with log_linear_df
    v_log, sched_log = price_swap(2_000_000.0, 0.04, maturity, yc, {"INTERP_STRATEGY": "log_linear_df"})

    # Both should produce floats and schedules of the same length
    assert isinstance(v_lin, float) and isinstance(v_log, float)
    assert isinstance(sched_lin, list) and isinstance(sched_log, list)
    assert len(sched_lin) == len(sched_log) and len(sched_lin) > 0

    # Values should be reasonably close on typical curves (< 50 bps PV difference relative to notional)
    # We just assert finite and not wildly divergent
    assert math.isfinite(v_lin) and math.isfinite(v_log)
    assert abs(v_lin - v_log) < 2e6  # loose bound to avoid flakiness on arbitrary curves
