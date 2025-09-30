# ARCHITECTURE — Gemini IRD Pricer (Flask)

Date: 2025-09-28

Purpose
- Provide a concise overview of the runtime architecture, module responsibilities, and request flow for the Flask-only stack.

Overview
- Web Layer (Flask): HTTP routing, templates, JSON APIs, error handling, security headers.
- Services (Dependency Container): Wiring and policies for curve loading (cache), pricer entry points.
- Domain Logic: Parsing/validation, pricer numerics, utilities (dates, discount functions, path safety), plotting helper.
- Configuration: Environment-driven settings via dataclasses with sane defaults for development and production.
- Observability/Security: Structured logs (optional JSON), Prometheus metrics (optional), basic auth (optional, default ON in production), security headers + CSP.

Key Modules
- src/gemini_ird_pricer/__init__.py
  - create_app(): Flask app factory.
  - Logging configuration (plain or JSON), security headers, request ID.
  - Optional /metrics route (Prometheus) when METRICS_ENABLED=true and prometheus_client available.
  - Registers web routes via web.register_routes().
- src/gemini_ird_pricer/web.py
  - HTML index route (GET/POST) for interactive pricing.
  - JSON APIs:
    - POST /api/price — prices a swap given notional, maturity_date, fixed_rate (%), optional curve override.
    - POST /api/solve — solves par rate for given notional and maturity_date.
  - Standardized JSON error schema: {"error": {"type", "message", "details?"}} for 4xx/5xx.
  - Uses utils.find_curve_file(app.config) to locate the latest SwapRates CSV.
- src/gemini_ird_pricer/services.py
  - Services dataclass containing: load_curve, price_swap, solve_par_rate.
  - Curve cache: in-process LRU + TTL keyed by file path and mtime; bypassed when overrides present.
  - get_cache_metrics()/get_cache_policy() for observability.
- src/gemini_ird_pricer/parsing.py
  - parse_notional, parse_maturity_date with validation/limits.
  - load_yield_curve: CSV schema validation; optional overrides; caps/sanity checks.
- src/gemini_ird_pricer/pricer.py
  - Core valuation functions: price_swap, solve_par_rate; schedule construction; discounting.
- src/gemini_ird_pricer/utils.py
  - year_fraction with common day counts (see limitations below), discount function builders, valuation time normalization.
  - ensure_in_data_dir path guard, find_curve_file with latest-by-date and project-root fallback.
- src/gemini_ird_pricer/config.py
  - BaseConfig/ProductionConfig with env-driven overrides via from_env(); get_config() selects by ENV.

Request Flow
1) create_app() builds config, logging, metrics (optional), services (cache policy), and registers routes.
2) Incoming requests receive a request_id; security headers applied in after_request.
3) / and /api/* handlers locate a curve CSV using utils.find_curve_file and load via Services.load_curve.
4) Pricing/Solving calls into Services.price_swap/solve_par_rate, which wrap pricer functions with explicit config mapping.
5) Results are rendered (HTML) or returned as JSON; errors adhere to the standard schema for APIs.

Security & Observability
- Default CSP in production if not explicitly configured; disable or adjust via CONTENT_SECURITY_POLICY.
- Basic auth enabled by default in ProductionConfig (ENABLE_AUTH=true). /metrics and /health are unauthenticated.
- Optional simple in-process rate limiting for POST APIs when ENABLE_RATE_LIMIT=true.
- Optional Prometheus /metrics with request counters/latency, build_info, and curve cache gauges.

Numerics Limitations
- ACT/ACT implementation is an approximation (calendar-year prorating) and not full ISDA day count.
- ACT/365L uses 366 when the interval includes Feb 29; otherwise 365.
- Consider specialized date libraries if production-grade accrual accuracy is required.

References
- Configuration details: docs/CONFIG.md, docs/CONFIG_SCHEMA.md
- Operations runbook: docs/OPERATIONS.md
- Dependency lock: docs/DEPENDENCY_LOCK.md
