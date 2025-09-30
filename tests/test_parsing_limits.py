from __future__ import annotations
import math
import os
import pandas as pd
import pytest

from gemini_ird_pricer.parsing import load_yield_curve
from gemini_ird_pricer.config import BaseConfig
from gemini_ird_pricer.__init__ import create_app


class _Form:
    def __init__(self, maturities, rates):
        self._m = [str(x) for x in maturities]
        self._r = [str(x) for x in rates]

    def getlist(self, key: str):
        if key == "curve_maturity":
            return self._m
        if key == "curve_rate":
            return self._r
        return []


def _make_csv(path: str, rows: int = 5):
    df = pd.DataFrame({
        "Maturity (Years)": [i + 1 for i in range(rows)],
        "Rate": [1.0 + 0.1 * i for i in range(rows)],
    })
    df.to_csv(path, index=False)


def test_form_limits_and_validation(tmp_path):
    # Setup app to supply DATA_DIR for ensure_in_data_dir
    app = create_app()
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    csv_path = data_dir / "SwapRates_20990101.csv"
    _make_csv(str(csv_path), 10)
    app.config.update({"DATA_DIR": str(data_dir)})

    # Too many points (beyond CURVE_MAX_POINTS=200 default) — first pass should succeed
    # Now test exactly beyond a very small cap by overriding config for this test by constructing large list
    maturities = list(range(1, 205))
    rates = [1.0] * len(maturities)
    form = _Form(maturities, rates)
    with pytest.raises(ValueError):
        load_yield_curve(str(csv_path), form)

    # Non-finite values
    form2 = _Form([1, 2, 3], [1.0, float("nan"), 2.0])
    with pytest.raises(ValueError):
        load_yield_curve(str(csv_path), form2)

    # Non-increasing maturities
    form3 = _Form([1, 1, 2], [1.0, 1.1, 1.2])
    with pytest.raises(ValueError):
        load_yield_curve(str(csv_path), form3)

    # Out-of-bounds rates
    form4 = _Form([1, 2, 3], [-20.0, 0.0, 0.1])
    with pytest.raises(ValueError):
        load_yield_curve(str(csv_path), form4)


def test_csv_limits_and_validation(tmp_path):
    app = create_app()
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    csv_path = data_dir / "SwapRates_20990102.csv"

    # Build a CSV exceeding the default max points
    _make_csv(str(csv_path), rows=250)
    app.config.update({"DATA_DIR": str(data_dir)})

    with pytest.raises(ValueError):
        load_yield_curve(str(csv_path))

    # Valid small CSV passes basic checks
    csv2 = data_dir / "SwapRates_20990103.csv"
    _make_csv(str(csv2), rows=5)
    df = load_yield_curve(str(csv2))
    assert len(df) == 5

    # Non-increasing maturities in CSV should fail
    bad = data_dir / "SwapRates_20990104.csv"
    pd.DataFrame({"Maturity (Years)": [1, 1, 2], "Rate": [1.0, 1.1, 1.2]}).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        load_yield_curve(str(bad))
