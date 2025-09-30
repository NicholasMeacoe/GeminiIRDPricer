from __future__ import annotations
from datetime import datetime
from gemini_ird_pricer.utils import year_fraction

def test_year_fraction_act_act_simple():
    # Jan 1 to Jan 31 in non-leap year ~ 30/365
    s = datetime(2023, 1, 1)
    e = datetime(2023, 1, 31)
    yf = year_fraction(s, e, "ACT/ACT")
    assert abs(yf - (30/365.0)) < 1e-9


def test_year_fraction_act_365l_spans_feb29():
    # Period spanning Feb 29, 2024 should use 366 denominator
    s = datetime(2024, 2, 28)
    e = datetime(2024, 3, 2)
    yf = year_fraction(s, e, "ACT/365L")
    assert abs(yf - (3/366.0)) < 1e-9


def test_year_fraction_act_365l_non_leap():
    s = datetime(2023, 2, 1)
    e = datetime(2023, 3, 1)
    yf = year_fraction(s, e, "ACT/365L")
    assert abs(yf - (28/365.0)) < 1e-9
