from __future__ import annotations
from flask import Flask

from gemini_ird_pricer import create_app as _create_app


def create_app_with_metrics_disabled() -> Flask:
    import gemini_ird_pricer.__init__ as appmod
    real_get_config = appmod.get_config

    class _Cfg(real_get_config().__class__):
        pass

    cfg = _Cfg()
    cfg.METRICS_ENABLED = False

    def fake_get_config(env: str | None = None):
        return cfg

    appmod.get_config = fake_get_config  # type: ignore
    try:
        app = _create_app()
    finally:
        appmod.get_config = real_get_config  # type: ignore
    app.testing = True
    return app


def test_metrics_endpoint_absent_when_disabled():
    app = create_app_with_metrics_disabled()
    client = app.test_client()
    resp = client.get("/metrics")
    # Route should not exist -> 404
    assert resp.status_code == 404
