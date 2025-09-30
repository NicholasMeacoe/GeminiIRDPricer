from __future__ import annotations
import os
import json
import logging
import pytest
from gemini_ird_pricer import create_app


@pytest.fixture()
def client_and_caplog(caplog):
    app = create_app()
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    app.config.update({
        "TESTING": True,
        "DATA_DIR": data_dir,
        "ENV": "development",
        "LOG_FORMAT": "plain",  # use plain logs for easier substring search
    })
    caplog.set_level(logging.INFO)
    return app.test_client(), caplog


def test_sensitive_headers_not_logged(client_and_caplog):
    client, caplog = client_and_caplog
    payload = {
        "notional": "1m",
        "maturity_date": "5y",
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer super_secret_token",
        "Cookie": "sessionid=verysecret; csrftoken=xyz",
    }
    resp = client.post("/api/solve", data=json.dumps(payload), headers=headers)
    assert resp.status_code in (200, 400)  # body may be invalid due to missing fields
    # Ensure secret substrings are not present in logs
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "super_secret_token" not in text
    assert "sessionid=verysecret" not in text
