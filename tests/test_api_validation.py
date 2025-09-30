from __future__ import annotations
import os
import json
import pytest
from gemini_ird_pricer import create_app


@pytest.fixture()
def app_client(tmp_path):
    app = create_app()
    # Point data dir to tests/data where a sample curve exists
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    app.config.update({
        "TESTING": True,
        "DATA_DIR": data_dir,
        "ENV": "development",
    })
    return app.test_client()


def test_price_success_with_minimal_body(app_client):
    payload = {
        "notional": "1m",
        "fixed_rate": 4.5,
        "maturity_date": "5y",
    }
    resp = app_client.post("/api/price", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "result" in body
    assert "npv" in body["result"]
    assert "schedule" in body["result"]
    assert isinstance(body["result"]["schedule"], list)


def test_price_validation_error_missing_fixed_rate(app_client):
    payload = {
        "notional": "1m",
        "maturity_date": "5y",
    }
    resp = app_client.post("/api/price", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["type"] in {"validation_error", "input_error"}


def test_solve_success_and_curve_override(app_client):
    payload = {
        "notional": "2m",
        "maturity_date": "3y",
        "curve": [
            {"maturity": 1, "rate": 5.1},
            {"maturity": 3, "rate": 4.9},
        ],
    }
    resp = app_client.post("/api/solve", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "result" in body and "par_rate_percent" in body["result"]


def test_validation_error_bad_curve_point(app_client):
    payload = {
        "notional": "1m",
        "maturity_date": "5y",
        "fixed_rate": 4.0,
        "curve": [
            {"maturity": -1, "rate": 5.0}
        ],
    }
    resp = app_client.post("/api/price", data=json.dumps(payload), headers={"Content-Type": "application/json"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["type"] == "validation_error"
    assert "details" in body["error"]
