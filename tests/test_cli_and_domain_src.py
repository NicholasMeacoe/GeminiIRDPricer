from __future__ import annotations
import os
from datetime import datetime, timedelta
import io
import sys
import types
import pandas as pd
import pytest

from gemini_ird_pricer.cli import main as cli_main
from gemini_ird_pricer.domain import CurvePoint, Notional, Tenor
from gemini_ird_pricer.parsing import load_yield_curve


def _fixture_path(name: str) -> str:
    here = os.path.dirname(__file__)
    return os.path.join(here, "data", name)


def test_domain_dataclasses_immutable():
    cp = CurvePoint(1.0, 0.05, datetime(2024, 1, 1))
    n = Notional(1_000_000)
    t = Tenor(5.0)
    assert cp.maturity_years == 1.0 and abs(cp.rate - 0.05) < 1e-12
    assert n.amount == 1_000_000
    assert t.years == 5.0
    # dataclasses with frozen=True should be immutable
    with pytest.raises(Exception):
        # type: ignore[attr-defined]
        cp.rate = 0.06  # noqa: F841


def test_cli_main_fixed_and_par_rate(tmp_path, capsys, monkeypatch):
    # Prepare a temporary data dir with a curve file visible to CLI
    data_dir = tmp_path / "curves"
    data_dir.mkdir(parents=True)
    curve_path = data_dir / "SwapRates_20240115.csv"
    with open(_fixture_path("SwapRates_20240115.csv"), "rb") as fsrc, open(curve_path, "wb") as fdst:
        fdst.write(fsrc.read())

    # Run pricing with fixed rate
    rc = cli_main(["price", "--fixed", "4.5", "--maturity", "5y", "--data-dir", str(data_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Swap NPV:" in out

    # Run par rate solving (omit --fixed)
    rc2 = cli_main(["price", "--maturity", "5y", "--data-dir", str(data_dir)])
    assert rc2 == 0
    out2 = capsys.readouterr().out
    assert "Par rate:" in out2


def test_parsing_load_with_form_data_branch(tmp_path):
    # Create a minimal file path to provide valuation date token
    data_dir = tmp_path / "curves"
    data_dir.mkdir(parents=True)
    fpath = data_dir / "SwapRates_20231231.csv"
    fpath.write_text("Maturity (Years),Rate\n1,5.0\n2,5.5\n")

    class DummyForm:
        def __init__(self):
            self._m = ["1", "2"]
            self._r = ["5.0", "5.5"]
        def getlist(self, key):
            if key == "curve_maturity":
                return self._m
            if key == "curve_rate":
                return self._r
            return []
        def __contains__(self, key):
            return key in {"curve_maturity", "curve_rate"}
    df = load_yield_curve(str(fpath), form_data=DummyForm())
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Maturity (Years)", "Rate"]
    # Ensure rates converted to decimals
    assert abs(float(df["Rate"].iloc[0]) - 0.05) < 1e-12
