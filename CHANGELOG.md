# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Removed FastAPI backend (backend/) in favor of a single Flask web stack. This is a breaking removal; use app.py or Flask routes instead of backend/main.py.
- Added versioned data directory convention (data/curves) and deterministic latest file selection.
- Introduced basic logging configuration with environment-based levels.
- Added config-driven numerical precision for UI formatting.
- Guarded interpolation with configurable extrapolation policy (clamp/error).
- Pinned dependencies and added requirements-dev.txt.
- Added CONTRIBUTING.md and mypy.ini for type checking setup.
- Improved form with defaults and client-side validation patterns.

## [M4] - 2025-09-29
- Enforced EXTRAPOLATION_POLICY=error across pricing paths; out-of-domain maturities now raise ValueError when configured.
- Added alternative interpolation strategy 'log_linear_df' operating on discount factors; controlled by INTERP_STRATEGY with default unchanged.
- Added tests for extrapolation policy and interpolation strategy under tests/test_m4_numerical_options.py.
- Added .pre-commit-config.yaml with Black, Ruff, and mypy hooks; documented usage in README and CONTRIBUTING.
- Updated docs/prod.readiness.tasks.md to mark M4 tasks as Done.

## [M3] - 2025-09-29
- Added docs/CONFIG_SCHEMA.md covering all configuration keys, types, defaults, and environment overrides.
- Added docs/OPERATIONS.md with deployment/runbook guidance, health/readiness, metrics, troubleshooting, and Docker examples.
- Implemented Prometheus metrics integration in Flask app factory with request counters/histogram and curve cache gauges (hits, misses, evictions, size, ttl). Endpoint /metrics is enabled only when prometheus_client is present and METRICS_ENABLED=true; otherwise gracefully disabled.
- Updated documentation across README and tasks to reflect configuration, security headers, and observability.
