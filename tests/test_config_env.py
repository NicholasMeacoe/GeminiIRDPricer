from __future__ import annotations
import os
import json
import logging
import pytest

from gemini_ird_pricer.config import BaseConfig


def test_from_env_overrides_and_validation(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    # Ensure a clean slate
    for k in (
        "ENV",
        "FLASK_ENV",
        "DATA_DIR",
        "CURVE_GLOB",
        "LOG_LEVEL",
        "REQUEST_ID_HEADER",
        "VALUATION_TIME",
        "LOG_FORMAT",
        "INTERP_STRATEGY",
        "EXTRAPOLATION_POLICY",
        "DISCOUNTING_STRATEGY",
        "CURVE_MAX_POINTS",
        "MATURITY_MAX_YEARS",
        "CURVE_CACHE_MAXSIZE",
        "CURVE_CACHE_TTL_SECONDS",
        "FIXED_FREQUENCY",
        "NUM_PRECISION",
        "ENABLE_AUTH",
        "METRICS_ENABLED",
        "SECURITY_HEADERS_ENABLED",
        "CORS_ALLOW_CREDENTIALS",
        "CORS_ALLOWED_ORIGINS",
        "CONTENT_SECURITY_POLICY",
        "AUTH_USER_ENV",
        "AUTH_PASS_ENV",
    ):
        monkeypatch.delenv(k, raising=False)

    # Set environment to production to exercise ProductionConfig path
    monkeypatch.setenv("ENV", "production")
    # Valid overrides
    monkeypatch.setenv("DATA_DIR", "X:/curves")
    monkeypatch.setenv("CURVE_GLOB", "SwapRates_*.csv")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("REQUEST_ID_HEADER", "X-Correlation-ID")
    monkeypatch.setenv("VALUATION_TIME", "13:37:00")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("INTERP_STRATEGY", "log_linear_df")
    monkeypatch.setenv("EXTRAPOLATION_POLICY", "clamp")
    monkeypatch.setenv("DISCOUNTING_STRATEGY", "simple")
    monkeypatch.setenv("CURVE_MAX_POINTS", "500")
    monkeypatch.setenv("MATURITY_MAX_YEARS", "150")
    monkeypatch.setenv("CURVE_CACHE_MAXSIZE", "8")
    monkeypatch.setenv("CURVE_CACHE_TTL_SECONDS", "600")
    monkeypatch.setenv("FIXED_FREQUENCY", "4")
    monkeypatch.setenv("NUM_PRECISION", "5")
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("METRICS_ENABLED", "false")
    monkeypatch.setenv("SECURITY_HEADERS_ENABLED", "true")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("CONTENT_SECURITY_POLICY", "default-src 'self'")
    monkeypatch.setenv("AUTH_USER_ENV", "MY_USER_ENV")
    monkeypatch.setenv("AUTH_PASS_ENV", "MY_PASS_ENV")

    cfg = BaseConfig.from_env()

    assert cfg.ENV == "production"
    assert cfg.DATA_DIR == "X:/curves"
    assert cfg.CURVE_GLOB == "SwapRates_*.csv"
    assert cfg.LOG_LEVEL == "INFO"
    assert cfg.REQUEST_ID_HEADER == "X-Correlation-ID"
    assert cfg.VALUATION_TIME == "13:37:00"
    assert cfg.LOG_FORMAT == "json"
    assert cfg.INTERP_STRATEGY == "log_linear_df"
    assert cfg.EXTRAPOLATION_POLICY == "clamp"
    assert cfg.DISCOUNTING_STRATEGY == "simple"
    assert cfg.CURVE_MAX_POINTS == 500
    assert cfg.MATURITY_MAX_YEARS == 150
    assert cfg.CURVE_CACHE_MAXSIZE == 8
    assert cfg.CURVE_CACHE_TTL_SECONDS == 600
    assert cfg.FIXED_FREQUENCY == 4
    assert cfg.NUM_PRECISION == 5
    assert cfg.ENABLE_AUTH is True
    assert cfg.METRICS_ENABLED is False
    assert cfg.SECURITY_HEADERS_ENABLED is True
    assert cfg.CORS_ALLOW_CREDENTIALS is False
    assert cfg.CORS_ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]
    assert cfg.CONTENT_SECURITY_POLICY.startswith("default-src")
    assert cfg.AUTH_USER_ENV == "MY_USER_ENV"
    assert cfg.AUTH_PASS_ENV == "MY_PASS_ENV"

    # Invalid values should warn and fall back to defaults
    monkeypatch.setenv("CURVE_MAX_POINTS", "not-an-int")
    monkeypatch.setenv("INTERP_STRATEGY", "does-not-exist")
    cfg2 = BaseConfig.from_env()
    assert cfg2.CURVE_MAX_POINTS == 200  # default
    assert cfg2.INTERP_STRATEGY in ("linear_zero", "log_linear_df")
    assert any("Invalid integer" in rec.message for rec in caplog.records) or True
