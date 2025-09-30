# Configuration Schema

This document describes all configuration settings supported by Gemini IRD Pricer, their types, defaults, and notes. Settings can be overridden via environment variables or by updating `app.config` at runtime.

Environment detection:
- ENV: "development" (default) or "production". In production, stricter defaults apply.

Settings
- ENV (str) — Default: development
  - Purpose: Environment name; when set to production, enables stricter defaults.
  - Env var: ENV or FLASK_ENV
- DEBUG (bool) — Default: True (False in production)
  - Purpose: Flask debug mode (do not enable in production).
- DATA_DIR (str) — Default: <project_root>/data/curves
  - Purpose: Directory containing curve CSV files.
  - Notes: Must not be a drive root; access outside this directory is blocked.
  - Env var: DATA_DIR
- CURVE_GLOB (str) — Default: SwapRates_*.csv
  - Purpose: Filename pattern for locating curve CSVs.
- DAY_COUNT (str) — Default: ACT/365F
  - Purpose: Day-count convention for year fraction calculations.
  - Allowed: ACT/365F, ACT/365, ACT/365.25, ACT/360, 30/360, ACT/ACT, ACT/365L
- FIXED_FREQUENCY (int) — Default: 2
  - Purpose: Fixed leg payment frequency per year.
- NUM_PRECISION (int) — Default: 4
  - Purpose: Decimal places for UI formatting.
- EXTRAPOLATION_POLICY (str) — Default: clamp
  - Purpose: Behavior outside curve support: clamp or error.
  - Allowed: clamp, error
- INTERP_STRATEGY (str) — Default: linear_zero
  - Purpose: Interpolation method.
  - Allowed: linear_zero, log_linear_df
- DISCOUNTING_STRATEGY (str) — Default: exp_cont
  - Purpose: Discount function.
  - Allowed: exp_cont, simple, comp_<n>
- LOG_LEVEL (str) — Default: DEBUG (INFO in production)
  - Purpose: Logging level.
  - Env var: LOG_LEVEL
- VALUATION_TIME (str) — Default: 00:00:00
  - Purpose: Time of day applied to valuation datetimes (HH:MM:SS).
- CURVE_CACHE_MAXSIZE (int) — Default: 4
  - Purpose: Max cached curves (LRU eviction).
- CURVE_CACHE_TTL_SECONDS (int) — Default: 300
  - Purpose: Cache TTL in seconds; 0 disables TTL expiry.
- CURVE_MAX_POINTS (int) — Default: 200
  - Purpose: Upper bound for points in a curve (CSV or form input).
- MATURITY_MAX_YEARS (int) — Default: 100
  - Purpose: Upper bound on maturity tenor.
- AUTH_USER_ENV (str) — Default: API_USER
  - Purpose: Name of environment variable holding Basic Auth username.
- AUTH_PASS_ENV (str) — Default: API_PASS
  - Purpose: Name of environment variable holding Basic Auth password.
- SECURITY_HEADERS_ENABLED (bool) — Default: True
  - Purpose: Emit standard security headers on all responses.
- CONTENT_SECURITY_POLICY (str) — Default: "" (empty). In production, a safe default is applied if left empty:
  - default-src 'none'; script-src 'self' https://cdn.plot.ly; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'
- ENABLE_AUTH (bool) — Default: False (True in production)
  - Purpose: Require HTTP Basic Auth for all endpoints except /health and /metrics.
  - Notes: Set expected credentials via environment variables named by AUTH_USER_ENV and AUTH_PASS_ENV.
- CORS_ALLOWED_ORIGINS (list[str]) — Default: Localhost dev origins; empty in production.
- CORS_ALLOW_CREDENTIALS (bool) — Default: True (False in production)
- LOG_FORMAT (str) — Default: plain (json in production)
  - Purpose: Logging output format.
- REQUEST_ID_HEADER (str) — Default: X-Request-ID
  - Purpose: Incoming header name to use or generate for request id; echoed on responses.
- METRICS_ENABLED (bool) — Default: True
  - Purpose: Enable Prometheus metrics and /metrics endpoint when prometheus_client is available.
- MAX_CONTENT_LENGTH (int) — Default: 1000000
  - Purpose: Maximum request payload size in bytes.
- NOTIONAL_MAX (float) — Default: 1e11
  - Purpose: Safety cap for user-provided notional values.
- CURVE_CACHE_ENABLED (bool) — Default: True
  - Purpose: Master switch to bypass the curve cache entirely when false.
- ENABLE_RATE_LIMIT (bool) — Default: False
  - Purpose: Enable simple in-app rate limiting for POST /api/price and /api/solve.
- RATE_LIMIT_PER_MIN (int) — Default: 60
  - Purpose: Allowed requests per minute per IP+path when rate limiting is enabled.
- RATE_LIMIT_WINDOW_SECONDS (int) — Default: 60
  - Purpose: Sliding window in seconds used by the limiter.

Environment Overrides
- BaseConfig.from_env() supports overriding: DATA_DIR, LOG_LEVEL, INTERP_STRATEGY, CURVE_MAX_POINTS, MATURITY_MAX_YEARS, AUTH_USER_ENV, AUTH_PASS_ENV.
- Production mode is selected when ENV or FLASK_ENV starts with "prod" (case-insensitive), which also flips defaults for DEBUG, LOG_LEVEL, ENABLE_AUTH, CORS, LOG_FORMAT.

Security Notes
- Never commit secrets. Provide Basic Auth credentials via process environment variables.
- Use a custom CSP if loading third-party assets; prefer self-hosted assets or nonces.
- Keep DATA_DIR confined; path traversal is prevented by default.
