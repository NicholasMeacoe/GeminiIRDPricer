# OPERATIONS — Runbook

Date: 2025-09-29

Purpose
- Provide concise operational guidance for deploying, configuring, observing, and troubleshooting the Gemini IRD Pricer (Flask) service.

Deployment
- Package: Python app started via `python app.py` (uses Flask app factory `create_app`).
- Env selection: `ENV=production` enables production defaults (auth on, INFO logs, JSON format).
- Data: Place curve CSVs under the configured DATA_DIR (default: data/curves). Filenames like `SwapRates_YYYYMMDD.csv`.

Configuration
- See docs/CONFIG_SCHEMA.md for the full list. Common variables:
  - ENV=production|development
  - DATA_DIR, CURVE_GLOB
  - ENABLE_AUTH=true|false, AUTH_USER_ENV, AUTH_PASS_ENV and corresponding secret values via env names
  - CONTENT_SECURITY_POLICY (default applied in production if empty)
  - METRICS_ENABLED=true|false
  - LOG_LEVEL=INFO|DEBUG, LOG_FORMAT=plain|json
- Validate: `python -m gemini_ird_pricer.cli --config` prints the resolved configuration as JSON.

Secrets
- Basic Auth credentials are read from environment variables named by AUTH_USER_ENV and AUTH_PASS_ENV (defaults API_USER, API_PASS).
- Inject secrets via your orchestrator (Kubernetes Secret, Docker env). Do not commit secrets.

Security
- Auth: In production, ENABLE_AUTH defaults to true; requests to app routes require HTTP Basic Auth unless accessing /health or /metrics.
- CSP: In production, a conservative Content Security Policy is set by default if CONTENT_SECURITY_POLICY is empty (allows cdn.plot.ly scripts for charts).
- File access: The service only reads curve files inside DATA_DIR; access outside is rejected.

Observability
- Logs: JSON in production. Fields include request_id, method, path, status, duration_ms, env, version; if trace headers are present, trace_id/span_id are included.
- Metrics: If prometheus_client is installed and METRICS_ENABLED=true, /metrics exposes:
  - flask_requests_total{method,path,status}
  - flask_request_duration_seconds{method,path}
  - build_info{version,env} (set to 1 with labels)
  - curve_cache_hits_total, curve_cache_misses_total, curve_cache_evictions_total
  - curve_cache_size, curve_cache_ttl_seconds
- Health: Liveness at /live (always ok). Readiness at /ready (ok when deps are healthy; currently no external deps, returns ok). Legacy /health remains for compatibility.

Troubleshooting
- 401 Unauthorized: Ensure ENABLE_AUTH and credentials are configured; set user/password envs named by AUTH_USER_ENV/PASS.
- 503 Service not configured for auth: ENABLE_AUTH is true but credential envs missing; set and restart.
- Curve not found: Verify DATA_DIR and CURVE_GLOB; place a SwapRates_YYYYMMDD.csv file.
- Plotly blocked by CSP: Provide a CSP compatible with your deployment (see README guidance) or serve plotly.js locally.

Operations Tips
- Rotate credentials: Change the underlying env vars referenced by AUTH_USER_ENV/PASS and restart.
- Cache: Curve cache is in-process with TTL and max size; restart clears it. Metrics include hits/misses/evictions.
- Config drift: Use `--config` dump in CI/CD to verify environment configuration before rollout.

# Operations Guide

## Running in Docker

- Build the local image:
  - docker build -t gemini-ird-pricer:local .
- Run the container:
  - docker run --rm -p 5000:5000 -e ENV=production -e LOG_FORMAT=json gemini-ird-pricer:local
- Or use docker-compose:
  - docker compose up --build

Endpoints
- Health: GET /health
- Metrics: GET /metrics (when METRICS_ENABLED=true)
- APIs: POST /api/price, POST /api/solve

Rate Limiting (optional)
- Enable by setting ENABLE_RATE_LIMIT=true
- Defaults: RATE_LIMIT_PER_MIN=60, RATE_LIMIT_WINDOW_SECONDS=60
- Applies to POST /api/price and /api/solve

Dependency Lock Strategy
- See docs/DEPENDENCY_LOCK.md for uv/pip-tools workflows.

Security Notes
- In production (ENV=production), Basic Auth is enabled by default (ENABLE_AUTH=true). Provide credentials via env vars named by AUTH_USER_ENV and AUTH_PASS_ENV (default API_USER/API_PASS).
- A conservative Content-Security-Policy header is applied by default unless overridden with CONTENT_SECURITY_POLICY.
