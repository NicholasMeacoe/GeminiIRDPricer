from __future__ import annotations
import os
import json
import base64
from flask import Flask
from gemini_ird_pricer.__init__ import create_app


def _prepare_curve(tmp_path) -> str:
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    src = os.path.join(os.path.dirname(__file__), "data", "SwapRates_20240115.csv")
    dst = data_dir / "SwapRates_20240115.csv"
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        fdst.write(fsrc.read())
    return str(data_dir)


def test_api_price_success(tmp_path):
    data_dir = _prepare_curve(tmp_path)
    app: Flask = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": data_dir})
    client = app.test_client()

    payload = {"notional": "1m", "fixed_rate": 5.0, "maturity_date": "5y"}
    resp = client.post("/api/price", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "result" in data
    assert "npv" in data["result"]
    assert isinstance(data["result"]["npv"], (int, float))


def test_api_solve_success(tmp_path):
    data_dir = _prepare_curve(tmp_path)
    app: Flask = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": data_dir})
    client = app.test_client()

    payload = {"notional": "1m", "maturity_date": "5y"}
    resp = client.post("/api/solve", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "result" in data
    assert "par_rate_percent" in data["result"]
    assert isinstance(data["result"]["par_rate_percent"], (int, float))


def test_api_input_error_returns_400(tmp_path):
    data_dir = _prepare_curve(tmp_path)
    app: Flask = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": data_dir})
    client = app.test_client()

    payload = {"notional": "-10", "fixed_rate": 5.0, "maturity_date": "5y"}
    resp = client.post("/api/price", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("error", {}).get("type") == "input_error"


def test_api_auth_enforced_in_production(tmp_path, monkeypatch):
    data_dir = _prepare_curve(tmp_path)
    # Configure production and auth
    monkeypatch.setenv("API_USER", "alice")
    monkeypatch.setenv("API_PASS", "s3cret")
    app: Flask = create_app(env="production")
    app.config.update({"TESTING": True, "DATA_DIR": data_dir, "ENABLE_AUTH": True})
    client = app.test_client()

    payload = {"notional": "1m", "fixed_rate": 5.0, "maturity_date": "5y"}
    # Without auth -> 401
    resp = client.post("/api/price", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 401
    # With auth header -> 200
    creds = base64.b64encode(b"alice:s3cret").decode("ascii")
    resp2 = client.post(
        "/api/price",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"Authorization": f"Basic {creds}"},
    )
    assert resp2.status_code == 200
