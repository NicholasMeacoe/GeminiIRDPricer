from __future__ import annotations
import os
import contextlib
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


def test_default_csp_applied_in_production_when_empty(tmp_path, monkeypatch):
    data_dir = _prepare_curve(tmp_path)
    # Simulate production
    app: Flask = create_app(env="production")
    app.config.update({"TESTING": True, "DATA_DIR": data_dir, "CONTENT_SECURITY_POLICY": ""})
    client = app.test_client()

    resp = client.get("/")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None and "default-src" in csp


def test_auth_enforced_with_401_when_enabled_and_creds_configured(tmp_path, monkeypatch):
    data_dir = _prepare_curve(tmp_path)
    # Set expected credentials in environment and enable auth
    monkeypatch.setenv("API_USER", "alice")
    monkeypatch.setenv("API_PASS", "s3cret")
    app: Flask = create_app(env="production")
    app.config.update({"TESTING": True, "DATA_DIR": data_dir, "ENABLE_AUTH": True})
    client = app.test_client()

    resp = client.get("/")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate", "").lower().startswith("basic")


def test_metrics_endpoint_absent_when_disabled(tmp_path):
    data_dir = _prepare_curve(tmp_path)
    app: Flask = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": data_dir, "METRICS_ENABLED": False})
    client = app.test_client()

    # When metrics disabled, route should not exist
    resp = client.get("/metrics")
    assert resp.status_code in (404, 405)  # 404 expected
