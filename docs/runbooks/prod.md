# Production Runbook

This runbook covers operating the Gemini IRD Pricer in production.

## Environment & Configuration
- Set `ENV=production` to enable production defaults.
- Provide credentials for auth when enabled:
  - `BASIC_AUTH_USER`, `BASIC_AUTH_PASS`
- Configure CORS for allowed origins via `CORS_ALLOWED_ORIGINS`.
- Logging: `LOG_FORMAT=json` and `LOG_LEVEL=INFO` by default in prod.
- Metrics: `/metrics` endpoint (Prometheus exposition) if enabled.

## Deployment
- Recommended: Containerize with a minimal Python base image.
- Ensure non-root user and read-only filesystem where possible.
- Mount/read-only curve data directory or configure via `DATA_DIR`.
- Health check: hit `GET /api/health` (FastAPI) for readiness/liveness.

## Operations
- Rotate curve files by dropping `SwapRates_YYYYMMDD.csv` into the configured data dir; the cache validates by mtime and TTL.
- Observe logs with request_id and JSON structure.
- Monitor Prometheus metrics: request counts and latencies.

## Security
- Keep auth enabled (default); verify creds are provided.
- Validate CORS origin list is restrictive.
- Security headers are injected by middleware; adjust CSP via config.

## Troubleshooting
- 401/503 responses: check `ENABLE_AUTH` and BASIC_AUTH_* env variables.
- 404 "No SwapRates file found": verify DATA_DIR and file naming.
- Stale curves: reduce `CURVE_CACHE_TTL_SECONDS` or restart.
