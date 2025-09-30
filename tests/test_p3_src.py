from __future__ import annotations
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import pytest

from gemini_ird_pricer.pricer import generate_payment_schedule, solve_par_rate
from gemini_ird_pricer.services import build_services
from gemini_ird_pricer.config import BaseConfig


def _make_curve(start: datetime) -> pd.DataFrame:
    dates = [start + timedelta(days=int(y * 365)) for y in [0.5, 1.0, 2.0, 5.0]]
    df = pd.DataFrame({
        "Maturity (Years)": [0.5, 1.0, 2.0, 5.0],
        "Rate": [0.04, 0.042, 0.045, 0.05],
    }, index=dates)
    return df


def test_generate_payment_schedule_month_based_and_guard():
    start = datetime(2025, 1, 31)
    # Maturity equal to start -> empty schedule
    assert generate_payment_schedule(start, start, 2) == []

    # Semi-annual (2) should step by 6 months, with clamped end-of-month logic
    maturity = datetime(2026, 1, 31)
    sched = generate_payment_schedule(start, maturity, 2)
    # Expect dates: 2025-07-31 and 2026-01-31
    assert len(sched) == 2
    assert sched[-1].date() == maturity.date()


def test_interp_strategy_and_policy_behavior():
    start = datetime(2024, 1, 15)
    yc = _make_curve(start)
    mdate = start + timedelta(days=int(3 * 365))
    # Compare linear_zero vs log_linear_df
    r_linear = solve_par_rate(1_000_000.0, mdate, yc, config={"INTERP_STRATEGY": "linear_zero"})
    r_logdf = solve_par_rate(1_000_000.0, mdate, yc, config={"INTERP_STRATEGY": "log_linear_df"})
    assert abs(r_linear - r_logdf) < 0.01  # within 100 bps for coarse curve

    # Extrapolation policy error beyond curve end
    far_mdate = start + timedelta(days=int(30 * 365))
    with pytest.raises(ValueError):
        _ = solve_par_rate(1_000_000.0, far_mdate, yc, config={"EXTRAPOLATION_POLICY": "error"})


def test_curve_cache_lru_ttl(tmp_path):
    # Prepare a temporary curve CSV in a temp data dir
    data_dir = tmp_path / "curves"
    data_dir.mkdir(parents=True)
    fpath = data_dir / "SwapRates_20240115.csv"
    fpath.write_text("Maturity (Years),Rate\n1,5.0\n2,5.5\n")

    # Build services with small cache and tiny TTL
    cfg = BaseConfig()
    cfg.DATA_DIR = str(data_dir)
    cfg.CURVE_CACHE_MAXSIZE = 1
    cfg.CURVE_CACHE_TTL_SECONDS = 0.05

    svc = build_services(cfg)

    # First load -> parse
    df1 = svc.load_curve(str(fpath))
    # Second load immediately -> cache hit returns same object
    df2 = svc.load_curve(str(fpath))
    assert df1 is df2

    # Wait for TTL to expire -> reload should return a different DataFrame object
    time.sleep(0.06)
    df3 = svc.load_curve(str(fpath))
    assert df3 is not df2
