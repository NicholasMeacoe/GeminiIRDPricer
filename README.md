# Gemini IRD Pricer

A lightweight, production-ready Flask web service and CLI for pricing plain-vanilla interest rate swaps.

Primary Web Stack: Flask
- Single Flask app (no FastAPI, no separate React SPA).
- HTML form UI served by Flask at GET /. Optional JSON APIs under /api.
- App factory: src/gemini_ird_pricer/__init__.py#create_app, entrypoint app.py.

Key capabilities
- Price a swap (NPV) or solve the par rate
- Upload/override yield curve points from the form or via JSON
- Built-in validations and safe defaults (day count, interpolation, rate bounds)
- Observability: optional Prometheus /metrics endpoint, JSON access logs with request IDs
- Security: security headers, optional Basic Auth in production, optional simple rate limiting


Quick start (local)
- Prerequisites: Python 3.11+
- Place a curve CSV under data/curves/ matching SwapRates_YYYYMMDD.csv (sample included)
- Install deps and run:
  - pip install -r requirements.txt
  - python app.py
- Open http://localhost:5000 for the UI.

Windows helpers
- start-app.bat, start-dev.bat are provided for convenience.

Docker
- docker build -t gemini-ird-pricer:local .
- docker run --rm -p 5000:5000 -e ENV=production -e LOG_FORMAT=json gemini-ird-pricer:local
- Or: docker compose up --build (see docker-compose.yml)


API endpoints (JSON)
- POST /api/price
  - Body: {"notional": "10m", "fixed_rate": 4.25, "maturity_date": "2028-12-31" | "5y", "curve"?: [{"maturity": 1.0, "rate": 3.2}, ...]}
  - Returns: {"result": {"npv": number, "schedule": [...]}}
- POST /api/solve
  - Body: {"notional": "10m", "maturity_date": "5y", "curve"?: [...]}
  - Returns: {"result": {"par_rate_percent": number}}
- GET /live — liveness probe (always ok)
- GET /ready — readiness probe (ok when deps healthy; currently always ok)
- GET /health — legacy liveness info (version, env)
- GET /metrics — Prometheus metrics (when METRICS_ENABLED=true and prometheus_client installed)

Curl examples
- Price
  - curl -s -X POST http://localhost:5000/api/price -H "Content-Type: application/json" -d '{"notional":"10m","fixed_rate":4.5,"maturity_date":"5y"}'
- Solve
  - curl -s -X POST http://localhost:5000/api/solve -H "Content-Type: application/json" -d '{"notional":"10m","maturity_date":"5y"}'


API Error Contract
- All JSON API errors return the schema: {"error": {"type": string, "message": string, "details"?: object}}
- Examples:
  - 400 input error: {"error": {"type": "input_error", "message": "Invalid notional format. Examples: 1000000, 10m, 250k."}}
  - 404 not found: {"error": {"type": "not_found", "message": "No SwapRates file found."}}
  - 413 payload too large: {"error": {"type": "payload_too_large", "message": "Request payload too large."}}
  - 429 rate limited: {"error": {"type": "rate_limited", "message": "Too many requests. Please retry later."}}
  - 500 server error: {"error": {"type": "server_error", "message": "An unexpected error occurred."}}

CLI usage
- Show help: python -m gemini_ird_pricer.cli -h
- Solve par:  python -m gemini_ird_pricer.cli --notional 10m --maturity 5y
- Price NPV:   python -m gemini_ird_pricer.cli --notional 10m --maturity 5y --fixed 4.25
- Print version: python -m gemini_ird_pricer.cli --version
- Print config:  python -m gemini_ird_pricer.cli --config

Notes
- CLI loads the latest SwapRates_*.csv from config.DATA_DIR (defaults to data/curves/, falls back to project root).


Configuration
- Full schema: docs/CONFIG_SCHEMA.md (keys, types, defaults, env overrides)
- Operations/runbook: docs/OPERATIONS.md
- Common keys (see src/gemini_ird_pricer/config.py):
  - DATA_DIR, CURVE_GLOB
  - LOG_FORMAT (plain|json), LOG_LEVEL, REQUEST_ID_HEADER
  - METRICS_ENABLED (true/false)
  - ENABLE_AUTH (prod default true), AUTH_USER_ENV (API_USER), AUTH_PASS_ENV (API_PASS)
  - CURVE_MAX_POINTS, MATURITY_MAX_YEARS
  - INTERP_STRATEGY (linear_zero|log_linear_df), EXTRAPOLATION_POLICY (clamp|error)
  - DISCOUNTING_STRATEGY (exp_cont|simple|comp_1|comp_2|comp_4|comp_12)

Security & auth
- In production (ENV=production) auth defaults to enabled. Set API creds via env vars named by AUTH_USER_ENV/AUTH_PASS_ENV.
- When auth enabled but creds missing, protected routes fail closed with 503 until configured.
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy) are set; a safe default CSP is applied in production when not configured.
- Optional simple rate limit for POST /api endpoints: ENABLE_RATE_LIMIT, RATE_LIMIT_PER_MIN, RATE_LIMIT_WINDOW_SECONDS.

Observability
- If LOG_FORMAT=json, structured logs include request_id, method, path, status, duration_ms, env, version. If trace headers (traceparent, X-Trace-Id/X-Span-Id) are present, logs also include trace_id/span_id.
- Prometheus: /metrics exports:
  - flask_requests_total{method,path,status}
  - flask_request_duration_seconds{method,path}
  - build_info{version,env}
  - curve_cache_hits_total, curve_cache_misses_total, curve_cache_evictions_total
  - curve_cache_size, curve_cache_ttl_seconds
  Disabled if METRICS_ENABLED=false or dependency missing.

Architecture
- App factory creates Flask app and registers routes (src/gemini_ird_pricer/web.py)
- Services container provides DI and a small LRU+TTL curve cache (src/gemini_ird_pricer/services.py)
- Domain logic in parsing.py, pricer.py, utils.py; plotting via Plotly JSON (plotting.py)

Data & CSV format
- Expected CSV: two columns [Maturity (Years), Rate] where Rate is percent.
- File discovery picks the latest-dated SwapRates_YYYYMMDD.csv from DATA_DIR (fallback to project root).

Legal & assumptions
- See docs/assumptions.md for conventions and numerical approximations (e.g., ACT/ACT approximation).

Pre-commit hooks
- Install: pip install pre-commit && pre-commit install
- Run on all files: pre-commit run --all-files
- Hooks: Black, Ruff, mypy (see .pre-commit-config.yaml)

Related docs
- Production Readiness Plan: docs/prod.readiness.plan.md
- Production Readiness Tasks: docs/prod.readiness.tasks.md
- Code Quality Grade: code_quality.junie.md
- Recommendations: recommendations.junie.md
