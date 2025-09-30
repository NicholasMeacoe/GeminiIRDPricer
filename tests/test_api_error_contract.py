from __future__ import annotations
import json
import os
from typing import Any
import types

from flask import Flask

from gemini_ird_pricer import create_app as _create_app


def make_app_with_tmp_curve(tmp_path) -> Flask:
    # Create a minimal valid curve CSV in a temp DATA_DIR
    csv = tmp_path / "SwapRates_20250101.csv"
    csv.write_text("1,2\n5,3\n10,4\n", encoding="utf-8")

    # Monkeypatch get_config to set DATA_DIR to tmp
    import gemini_ird_pricer.__init__ as appmod
    real_get_config = appmod.get_config

    class _Cfg(real_get_config().__class__):
        pass

    cfg = _Cfg()
    cfg.DATA_DIR = str(tmp_path)

    def fake_get_config(env: str | None = None):
        return cfg

    appmod.get_config = fake_get_config  # type: ignore
    try:
        app = _create_app()
    finally:
        # restore
        appmod.get_config = real_get_config  # type: ignore
    app.testing = True
    return app


def test_api_price_invalid_notional_returns_400_json_error(tmp_path):
    app = make_app_with_tmp_curve(tmp_path)
    client = app.test_client()
    resp = client.post(
        "/api/price",
        json={
            "notional": "-1m",  # invalid (must be positive)
            "maturity_date": "5y",
            "fixed_rate": 3.0,
        },
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "error" in data and isinstance(data["error"], dict)
    assert "type" in data["error"] and data["error"]["type"] in {"input_error", "validation_error"}
    assert "message" in data["error"]


def test_api_price_server_error_returns_500_json_error(tmp_path):
    app = make_app_with_tmp_curve(tmp_path)
    # Force a server-side exception in price path by monkeypatching services.price_swap
    services = app.extensions.get("services")
    assert services is not None

    def boom(*args: Any, **kwargs: Any):  # pragma: no cover - used only in this test
        raise RuntimeError("boom")

    services.price_swap = boom  # type: ignore[attr-defined]

    client = app.test_client()
    resp = client.post(
        "/api/price",
        json={
            "notional": "1m",
            "maturity_date": "5y",
            "fixed_rate": 3.0,
        },
    )
    assert resp.status_code == 500
    data = resp.get_json()
    assert isinstance(data, dict)
    assert "error" in data and "type" in data["error"] and data["error"]["type"] == "server_error"
    assert "message" in data["error"]
