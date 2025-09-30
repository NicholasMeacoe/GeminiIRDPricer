# Production Readiness Task Backlog — Gemini IRD Pricer

Last updated: 2025-09-29 08:35 (local)
Owner: Project Manager / Tech Lead
Version: 1.0

Legend
- P: Priority (P0 critical, P1 high, P2 medium, P3 low)
- Est: Estimate (XS <0.5d, S 1d, M 2-3d)
- Dep: Dependencies
- DoD: Definition of Done (acceptance criteria)
- Owner: To be assigned (TBA)

Milestone grouping
- M1: Docs consistency + cache metrics fix
- M2: API schema validation + security redaction
- M3: Config/ops docs + observability metrics
- M4 (optional): Numerical options + DX polish

M1 — Documentation alignment and cache metrics integrity
1. Update docs/examples.md to match Flask endpoints
   - P: P0, Est: S, Dep: None, Owner: TBA
   - Tasks:
     - Replace FastAPI/uvicorn/8000 references with Flask/5000
     - Use /api/price and /api/solve endpoints consistently
     - Verify CLI examples against src/gemini_ird_pricer/cli.py
   - DoD:
     - Examples runnable as-is; links and commands verified locally
   - Status: Done — Updated docs/examples.md; now uses Flask on :5000 with /api/price and /api/solve. Verified against CLI and app.py.

2. Thread-safe cache metrics increments in services.py
   - P: P0, Est: XS, Dep: None, Owner: TBA
   - Tasks:
     - Move _cache_hits/_cache_misses/_cache_evictions increments into _cache_lock regions
     - Add unit tests covering hit/miss/eviction paths and TTL expiry
   - DoD:
     - Tests reliably reproduce and verify counts; no race issues in stress run
   - Status: Done — Metrics increments are now under _cache_lock. Tests added: tests/test_services_cache_metrics.py, tests/test_services_cache_policy.py, and concurrency test passes.

3. Optional: Config switch to disable curve cache
   - P: P2, Est: XS, Dep: #2, Owner: TBA
   - Tasks:
     - Add config flag CURVE_CACHE_ENABLED (default true)
     - Bypass caching when false; add tests
   - DoD:
     - Toggle works; behavior documented in CONFIG_SCHEMA.md
   - Status: Done — Implemented CURVE_CACHE_ENABLED with full bypass path and path safety; tests added in tests/test_services_cache_policy.py. Documentation will be captured in Task 7 (M3: docs/CONFIG_SCHEMA.md).

M2 — API validation and security redaction
4. Introduce request/response schemas for /api endpoints
   - P: P0, Est: M, Dep: None, Owner: TBA
   - Tasks:
     - Choose library (pydantic preferred) and add lightweight dependency
     - Define models: PriceRequest, SolveRequest, PriceResponse, SolveResponse
     - Parse and validate request JSON; map errors to 400 with details
     - Update tests: success and negative cases; golden responses
   - DoD:
     - Contract tests pass; error JSON includes type/message/details
   - Status: Done — Pydantic models added (api_schemas.py); /api endpoints validate inputs and return structured 400 with details. Tests added in tests/test_api_validation.py.

5. Redact sensitive headers in logging
    - P: P1, Est: S, Dep: None, Owner: TBA
    - Tasks:
      - In app factory/middleware, remove Authorization, Cookie, Set-Cookie from logs
      - Add unit tests ensuring redaction
    - DoD:
      - Logs contain no sensitive header content
    - Status: Done — Access logging does not include request headers; sensitive values (Authorization, Cookie, Set-Cookie) are never logged. Tests added in tests/test_logging_redaction.py verify secrets do not appear in logs.

6. Configurable CSP with safe default
   - P: P2, Est: S, Dep: None, Owner: TBA
   - Tasks:
     - Add CSP config key and sensible default for Plotly usage
     - Document how to override per environment
     - Test header presence in production mode
   - DoD:
     - CSP applied in prod; documented trade-offs
   - Status: Done — Default CSP now Plotly-friendly and applied via response headers in production; tests added in tests/test_security_headers.py. Overrides respected via CONTENT_SECURITY_POLICY.

M3 — Config docs and observability
7. Create docs/CONFIG_SCHEMA.md
   - P: P1, Est: S, Dep: None, Owner: TBA
   - Tasks:
     - Enumerate keys, types, defaults, env var names, and examples
     - Cross-check with src/gemini_ird_pricer/config.py
   - DoD:
     - Document matches implemented defaults and types
   - Status: Done — Added docs/CONFIG_SCHEMA.md enumerating all BaseConfig keys (including CURVE_CACHE_ENABLED, MAX_CONTENT_LENGTH, NOTIONAL_MAX, CORS, rate limiting, CSP defaults). Cross-checked with config.py and app factory CSP implementation.

8. Create docs/OPERATIONS.md
   - P: P1, Est: S, Dep: None, Owner: TBA
   - Tasks:
     - Add runbook: startup, health, readiness, metrics, common failures and resolutions
     - Include troubleshooting for missing data, auth creds, and metrics dependency
   - DoD:
     - Reviewed by ops-minded engineer
   - Status: Done — Added docs/OPERATIONS.md with deployment/runbook, health/readiness/metrics, troubleshooting (auth, data, metrics dependency), and Docker examples. Date refreshed to 2025-09-29.

9. Prometheus cache metrics integration (optional when dependency present)
   - P: P2, Est: S, Dep: #2, Owner: TBA
   - Tasks:
     - Define counters/gauges for curve_cache_* when prometheus_client available
     - Ensure graceful disable when not installed
     - Add tests with dependency mocked/skipped
   - DoD:
     - /metrics exposes counters; disabled otherwise without errors
   - Status: Done — Implemented /metrics with request counters/histograms and curve cache gauges (hits, misses, evictions, size, ttl). Endpoint registers only when prometheus_client is available and METRICS_ENABLED=true; otherwise gracefully disabled.

M4 — Numerical options and DX polish (optional)
10. Enforce EXTRAPOLATION_POLICY=error behavior
    - P: P2, Est: S, Dep: None, Owner: TBA
    - Tasks:
      - Verify pricer respects policy across code paths; add guard if missing
      - Add tests for out-of-domain maturities
    - DoD:
      - Behavior correct and documented
    - Status: Done — Pricer enforces 'error' policy via _interp_market_rate raising ValueError; tests added in tests/test_m4_numerical_options.py.

11. Optional interpolation strategy on discount factors
    - P: P3, Est: M, Dep: None, Owner: TBA
    - Tasks:
      - Add alternative interpolation path (log-linear DF or monotone)
      - Feature-flag via INTERP_STRATEGY; defaults preserved
      - Add numerical tests
    - DoD:
      - Option available; default unchanged; tests green
    - Status: Done — Implemented 'log_linear_df' interpolation; controlled by INTERP_STRATEGY with default preserved. Tests added in tests/test_m4_numerical_options.py.

12. Developer experience: pre-commit hooks
    - P: P3, Est: XS, Dep: None, Owner: TBA
    - Tasks:
      - Add .pre-commit-config.yaml with ruff, black, mypy (and optional pytest)
      - Document usage in README and CONTRIBUTING
    - DoD:
      - Hooks run locally; contributors can install easily
    - Status: Done — Added .pre-commit-config.yaml with Black, Ruff, and mypy; documented in README and CONTRIBUTING.

Cross-cutting tasks
13. Update README references and summaries (if needed)
    - P: P2, Est: XS, Dep: After M1 docs updates, Owner: TBA
    - Tasks:
      - Ensure links to prod.readiness.plan.md and prod.readiness.tasks.md are present and correct
    - DoD:
      - README links valid
    - Status: Done — README references verified and pre-commit usage documented.

14. CHANGELOG entries
    - P: P2, Est: XS, Dep: Per milestone, Owner: TBA
    - Tasks:
      - Add entries summarizing each milestone delivery
    - DoD:
      - CHANGELOG reflects production readiness work
    - Status: Done — CHANGELOG updated with M4 entry summarizing tasks and tests.

Tracking template (copy for each task when creating issues)
- Title:
- Description:
- Priority: P0/P1/P2/P3
- Estimate: XS/S/M
- Dependencies:
- Acceptance criteria (DoD):
- Owner:
- Status: Todo / In progress / Review / Done
