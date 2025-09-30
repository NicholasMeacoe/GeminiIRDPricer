from __future__ import annotations
from datetime import datetime, timedelta
import json
import pandas as pd
from gemini_ird_pricer.plotting import plot_yield_curve


def test_plot_yield_curve_returns_json_string():
    val = datetime(2024, 1, 15)
    dates = [val + timedelta(days=int(y * 365)) for y in [0.5, 1.0, 2.0]]
    df = pd.DataFrame({
        "Maturity (Years)": [0.5, 1.0, 2.0],
        "Rate": [0.04, 0.042, 0.045],
    }, index=dates)

    s = plot_yield_curve(df)
    # The function returns a JSON string; ensure single json.loads yields a dict
    obj = json.loads(s)
    assert isinstance(obj, dict)
    assert "data" in obj and "layout" in obj
