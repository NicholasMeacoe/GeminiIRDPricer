from __future__ import annotations
from datetime import datetime
import math

from gemini_ird_pricer.utils import year_fraction


def test_act_act_exact_one_year_boundary():
    # Jan 1 to Jan 1 across a leap year boundary should be exactly 1.0 in our approximation
    start = datetime(2019, 1, 1)
    end = datetime(2020, 1, 1)  # 2019 not leap year
    assert abs(year_fraction(start, end, "ACT/ACT") - 1.0) < 1e-12


def test_act_act_prorates_across_leap_and_non_leap_years():
    # Jul 1, 2019 to Jul 1, 2020 spans half of a non-leap and half of a leap year
    start = datetime(2019, 7, 1)
    end = datetime(2020, 7, 1)
    expected = (184 / 365.0) + (182 / 366.0)  # 2019-07-01..2019-12-31 = 184 days; 2020-01-01..2020-07-01 = 182 days
    assert abs(year_fraction(start, end, "ACT/ACT") - expected) < 1e-9


def test_act_365L_uses_366_when_including_feb29():
    start = datetime(2020, 2, 28)
    end = datetime(2020, 3, 1)
    # Interval includes Feb 29 -> denominator 366
    assert abs(year_fraction(start, end, "ACT/365L") - (2 / 366.0)) < 1e-12


def test_30_360_simple_case():
    start = datetime(2024, 1, 31)
    end = datetime(2024, 2, 28)
    # Using 30/360 US simplified: both days clamped to 30
    expected = ((0) * 360 + (1) * 30 + (30 - 30)) / 360.0  # 30 days / 360 = 1/12
    assert abs(year_fraction(start, end, "30/360") - (30 / 360.0)) < 1e-12
