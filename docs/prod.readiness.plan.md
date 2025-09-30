# Production Readiness Implementation Plan — Gemini IRD Pricer

Last updated: 2025-09-28 17:37 (local)
Owner: Engineering Lead
Version: 1.0

Purpose
- Convert the recommendations in recommendations.junie.md into an executable, phased plan with clear outcomes, milestones, and acceptance criteria to bring the service to production-grade quality (A rating).

Guiding principles
- Minimal risk, incremental delivery, and backward compatibility.
- Preserve current API contracts unless explicitly versioned.
- Tests-first for user-facing behavior changes. Maintain >=90% coverage.
- Security and operability improvements are prioritized alongside user/documentation fixes.

Scope of work (by theme)
1) Concurrency and cache metrics integrity
- Objective: Ensure thread-safe cache metrics and predictable cache behavior under load.
- Deliverables:
  - Thread-safe increments for hits/misses/evictions in src/gemini_ird_pricer/services.py.
  - Unit and concurrency tests (TTL, eviction, staleness on mtime change).
  - Optional config to disable caching for troubleshooting.
- Acceptance criteria:
  - All related tests pass; no data races found by stress tests; metrics match expectations under synthetic load.

2) API request/response schema validation
- Objective: Strong input validation for /api/price and /api/solve and explicit response schemas.
- Deliverables:
  - Pydantic or Marshmallow models for request/response payloads.
  - Validation errors return 400 with schema: {"error": {"type":"input_error", "message": str, "details": {..}}}.
  - Golden contract tests for representative success and failure cases.
- Acceptance criteria:
  - Tests assert correct shapes and error messaging; backward-compatible for existing clients.

3) Documentation alignment and clarity
- Objective: Eliminate inconsistencies and confusion in docs/examples.md and ensure alignment with Flask endpoints and ports.
- Deliverables:
  - Updated docs/examples.md to use /api/price and /api/solve on port 5000.
  - Cross-link to README API contract section; add error examples.
  - CLI examples verified against current cli.py.
- Acceptance criteria:
  - Examples run as-is; no references to FastAPI/uvicorn/8000 remain.

4) Security hardening (headers, auth, CSP, redaction)
- Objective: Strengthen default security posture without breaking UX.
- Deliverables:
  - Logging middleware redacts Authorization/Cookie/Set-Cookie; avoids logging secrets.
  - Configurable CSP with safe production defaults documented.
  - Clear startup/health signals when auth is enabled but credentials are missing (fail closed for protected routes while health clearly reports misconfiguration).
- Acceptance criteria:
  - Manual verification of headers; automated tests for redaction and auth fail-closed behavior.

5) Performance/numerical options (non-breaking)
- Objective: Offer numerically safer interpolation/extrapolation while keeping defaults stable.
- Deliverables:
  - Optional interpolation strategy on discount factors or monotone; ensure current linear remains default.
  - Enforce EXTRAPOLATION_POLICY=error behavior when requested.
- Acceptance criteria:
  - Tests cover strategy selection and error policy; no performance regressions for typical inputs.

6) Configuration UX and documentation
- Objective: Make configuration explicit and easy to operate.
- Deliverables:
  - docs/CONFIG_SCHEMA.md enumerating keys, types, defaults, env names, and examples.
  - docs/OPERATIONS.md runbook: common failures (missing data, auth creds, metrics dep), troubleshooting, and metrics reference.
- Acceptance criteria:
  - Docs reviewed; onboarding feedback from a fresh engineer is positive.

7) Observability and metrics
- Objective: Improve metrics fidelity and visibility of cache behavior.
- Deliverables:
  - Prometheus metrics for cache (counters/gauges) when prometheus_client present; gracefully disabled otherwise.
  - Expose cache policy via existing /metrics or a small diagnostics endpoint when metrics disabled.
- Acceptance criteria:
  - /metrics shows curve_cache_* metrics when enabled; unit tests skip when dependency absent.

8) Testing and DX
- Objective: Increase confidence and streamline contributor workflow.
- Deliverables:
  - API contract tests, cache concurrency tests, date utilities properties.
  - Optional pre-commit hooks (ruff, black, mypy); nox docs in README.
- Acceptance criteria:
  - CI (or local nox) runs clean; developers use hooks successfully.

Phased delivery plan
- Phase 0 (Day 0): Planning & scaffolding
  - Add this plan and tasks documents; verify README links.
- Phase 1 (Week 1): Docs alignment and cache metrics fix
  - Update docs/examples.md; implement thread-safe metrics; add basic tests.
- Phase 2 (Week 2): API schema validation and security redaction
  - Add request/response schemas; map validation errors; redact sensitive headers in logs.
- Phase 3 (Week 3): Config docs and observability
  - Add CONFIG_SCHEMA.md and OPERATIONS.md; add Prometheus cache metrics integration.
- Phase 4 (Week 4, optional): Numerical options and DX polish
  - Optional interpolation strategy; pre-commit; finalize tests.

Milestones and success criteria
- M1: Docs consistency complete; cache metrics thread-safe; tests passing.
- M2: API validation integrated; contract tests green; error UX improved.
- M3: Config and ops docs published; metrics enhanced; health/readiness clear for auth misconfig.
- M4: Optional numerical/DX enhancements feature-flagged; performance steady.

Risks and mitigations
- Risk: Introducing validation may break undocumented clients.
  - Mitigation: Maintain backward-compatible fields; comprehensive negative tests; version endpoints if needed.
- Risk: CSP may block Plotly in some deployments.
  - Mitigation: Provide clear CSP defaults and documentation on script-src and data sources; allow config override.
- Risk: Metrics library absence.
  - Mitigation: Soft dependency with graceful disable.

Measurements and telemetry
- Track error rates (4xx vs 5xx), request duration, and cache hit ratio after changes.
- Monitor documentation usage by verifying cURL examples in CI or a doc test job.

Change management
- Use small PRs per theme; require tests and documentation updates.
- Tag releases in CHANGELOG.md with notable production readiness improvements.

Dependencies and external factors
- prometheus_client for metrics exposure (optional).
- plotly for plotting; note CSP considerations.

Out of scope (for now)
- Full OAuth2/JWT; advanced calendars/business-day conventions; multi-curve framework.

Sign-off checklist
- [ ] All milestones completed
- [ ] Coverage >= 90% remains
- [ ] Security headers and redaction verified
- [ ] Docs reviewed by at least one peer
- [ ] CHANGELOG updated
