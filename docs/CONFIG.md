# CONFIGURATION OVERVIEW

Date: 2025-09-28

This document summarizes key configuration knobs for the Flask application. See docs/CONFIG_SCHEMA.md for the authoritative schema with types, defaults, and environment variable names.

Quick Start
- Print resolved configuration (from environment):
  - python -m gemini_ird_pricer.cli --config
- Production defaults are selected when ENV=production (see ProductionConfig in src/gemini_ird_pricer/config.py).

Core Settings
- ENV: development | production (default development)
- DEBUG: bool (default True in development, False in production)
- DATA_DIR: Directory containing curve CSVs (default: data/curves under project root)
- CURVE_GLOB: Filename pattern (default: SwapRates_*.csv)
- NUM_PRECISION: Output decimal precision for UI strings (default: 4)
- VALUATION_TIME: Time of day applied to valuation dates (HH:MM:SS; default 00:00:00)

Numerics
- DAY_COUNT: e.g., ACT/365F (default)
- FIXED_FREQUENCY: coupons per year (default 2)
- INTERP_STRATEGY: linear_zero | log_linear_df (default linear_zero)
- DISCOUNTING_STRATEGY: exp_cont | simple | comp_N (default exp_cont)
- EXTRAPOLATION_POLICY: clamp | error (default clamp)

Limits & Validation
- CURVE_MAX_POINTS: max curve rows/overrides (default 200)
- MATURITY_MAX_YEARS: max tenor in years for shorthand inputs (default 100)

Security & Headers
- ENABLE_AUTH: Require HTTP Basic Auth (default False in dev, True in prod)
- AUTH_USER_ENV / AUTH_PASS_ENV: Names of env vars containing credentials (defaults API_USER / API_PASS)
- SECURITY_HEADERS_ENABLED: Add X-Content-Type-Options, X-Frame-Options, Referrer-Policy (default True)
- CONTENT_SECURITY_POLICY: CSP value; when empty in production, a conservative default is applied.
- CORS_ALLOWED_ORIGINS: Allowed origins in dev; empty by default in production.
- CORS_ALLOW_CREDENTIALS: Whether to include credentials in CORS (default True in dev, False in prod)

Observability
- LOG_LEVEL: DEBUG|INFO (default DEBUG in dev, INFO in prod)
- LOG_FORMAT: plain|json (default plain in dev, json in prod)
- REQUEST_ID_HEADER: Correlation header name (default X-Request-ID)
- METRICS_ENABLED: Enable /metrics when prometheus_client is available (default True)

Rate Limiting (Optional)
- ENABLE_RATE_LIMIT: Enable simple in-process rate limiting for POST /api endpoints (default False)
- RATE_LIMIT_PER_MIN: Allowed requests per window (default 60)
- RATE_LIMIT_WINDOW_SECONDS: Window length in seconds (default 60)

Cache Policy (Yield Curves)
- CURVE_CACHE_MAXSIZE: In-process cache size (default 4)
- CURVE_CACHE_TTL_SECONDS: Entry TTL in seconds (default 300)

Notes
- Most booleans and integers can be overridden via environment variables; invalid values are logged at WARNING and defaulted.
- See src/gemini_ird_pricer/config.py for exact parsing and defaults; BaseConfig.from_env() documents normalization and bounds.
