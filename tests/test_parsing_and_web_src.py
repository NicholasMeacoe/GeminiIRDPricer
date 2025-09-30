from __future__ import annotations
import os
from datetime import datetime, timedelta
import io
import json
import pandas as pd
import pytest

# Import src package (conftest ensures src precedence)
from gemini_ird_pricer.__init__ import create_app
from gemini_ird_pricer.parsing import parse_notional, parse_maturity_date, load_yield_curve


def _fixture_path(name: str) -> str:
    here = os.path.dirname(__file__)
    return os.path.join(here, "data", name)


def test_parse_notional_variants():
    assert parse_notional("1000000") == 1_000_000
    assert parse_notional("10m") == 10_000_000
    assert parse_notional("250k") == 250_000
    assert parse_notional("2b") == 2_000_000_000
    with pytest.raises(ValueError):
        parse_notional("abc")


def test_parse_maturity_date_variants(monkeypatch):
    # Fix 'today' to a known date by monkeypatching datetime.today via freezegun-like approach is heavy;
    # Instead, just validate parsing pathways and positivity checks
    dt = parse_maturity_date("2028-12-31")
    assert dt.year == 2028 and dt.month == 12 and dt.day == 31
    with pytest.raises(ValueError):
        parse_maturity_date("-5y")


def test_load_yield_curve_from_csv_fixture(tmp_path):
    src_file = _fixture_path("SwapRates_20240115.csv")
    # Copy to data/curves-like directory since loader ensures path is inside DATA_DIR
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    dst_file = data_dir / "SwapRates_20240115.csv"
    with open(src_file, "rb") as fsrc, open(dst_file, "wb") as fdst:
        fdst.write(fsrc.read())

    # Temporarily point DATA_DIR to tmp path by creating app/config mapping
    app = create_app()
    app.config.update({"DATA_DIR": str(data_dir)})

    # load_yield_curve reads directly; set env via app config path and pass file
    df = load_yield_curve(str(dst_file))
    assert isinstance(df, pd.DataFrame)
    assert "Rate" in df.columns and "Maturity (Years)" in df.columns
    # rates converted to decimals
    assert abs(float(df["Rate"].iloc[0]) - 0.04) < 1e-9


def test_flask_routes_get_and_post(tmp_path):
    # Prepare data dir with curve file
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    curve_path = data_dir / "SwapRates_20240115.csv"
    with open(_fixture_path("SwapRates_20240115.csv"), "rb") as fsrc, open(curve_path, "wb") as fdst:
        fdst.write(fsrc.read())

    app = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": str(data_dir)})

    client = app.test_client()

    # GET should render HTML with plot_json and yield curve table
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Yield Curve" in html or "yield_curve" in html

    # POST price
    post_data = {
        "notional": "10m",
        "fixed_rate": "4.5",
        "maturity_date": "5y",
        "action": "price",
        # No form curve overrides provided -> use CSV
    }
    resp2 = client.post("/", data=post_data)
    assert resp2.status_code == 200
    html2 = resp2.get_data(as_text=True)
    assert "Swap Value:" in html2

    # POST solve par rate path
    post_data["action"] = "solve"
    resp3 = client.post("/", data=post_data)
    assert resp3.status_code == 200
    html3 = resp3.get_data(as_text=True)
    assert "Swap Value:" in html3

    # POST with bad inputs triggers error path
    bad = {"notional": "bad", "fixed_rate": "x", "maturity_date": "n/a", "action": "price"}
    resp4 = client.post("/", data=bad)
    assert resp4.status_code == 200
    assert "Error:" in resp4.get_data(as_text=True)
