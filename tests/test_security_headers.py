from __future__ import annotations
import os
from gemini_ird_pricer import create_app


def _make_client(env: str, csp: str | None = None):
    app = create_app()
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    app.config.update({
        "TESTING": True,
        "DATA_DIR": data_dir,
        "ENV": env,
    })
    if csp is not None:
        app.config["CONTENT_SECURITY_POLICY"] = csp
    return app.test_client()


def test_prod_default_csp_header_present():
    c = _make_client("production")
    resp = c.get("/live")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "cdn.plot.ly" in csp


def test_custom_csp_override():
    custom = "default-src 'self'"
    c = _make_client("production", csp=custom)
    resp = c.get("/live")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Security-Policy") == custom
