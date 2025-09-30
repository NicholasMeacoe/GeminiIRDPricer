from __future__ import annotations
import os
import pytest

from gemini_ird_pricer.__init__ import create_app


def test_flask_user_error_returns_400(tmp_path):
    # Prepare data dir with a valid curve file
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    src = os.path.join(os.path.dirname(__file__), "data", "SwapRates_20240115.csv")
    dst = data_dir / "SwapRates_20240115.csv"
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        fdst.write(fsrc.read())

    app = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": str(data_dir)})
    client = app.test_client()

    # Invalid notional triggers ValueError -> 400
    resp = client.post("/", data={
        "notional": "-10",  # invalid
        "fixed_rate": "5.0",
        "maturity_date": "5y",
        "action": "price",
    })
    assert resp.status_code == 400
    assert b"Notional must be positive" in resp.data or b"error" in resp.data.lower()


def test_flask_server_error_returns_500(tmp_path, monkeypatch):
    data_dir = tmp_path / "data" / "curves"
    data_dir.mkdir(parents=True)
    src = os.path.join(os.path.dirname(__file__), "data", "SwapRates_20240115.csv")
    dst = data_dir / "SwapRates_20240115.csv"
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        fdst.write(fsrc.read())

    app = create_app()
    app.config.update({"TESTING": True, "DATA_DIR": str(data_dir)})

    # Monkeypatch the registered Services to raise a generic exception to simulate server error
    svc = app.extensions.get("services")
    assert svc is not None

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(svc, "price_swap", boom)
    client = app.test_client()

    resp = client.post("/", data={
        "notional": "1000000",
        "fixed_rate": "5.0",
        "maturity_date": "5y",
        "action": "price",
    })
    assert resp.status_code == 500
    assert b"unexpected error" in resp.data.lower()
