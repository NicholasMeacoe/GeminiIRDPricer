import os
import logging
import json
import time
import uuid
import secrets
from flask import Flask, request, g, Response
from .config import get_config
from .web import register_routes
from .services import build_services
from .security import SecurityHeaders, setup_cors
from .logging_utils import setup_logging, RequestLogger


def create_app(env: str | None = None) -> Flask:
    cfg = get_config(env)
    # Point templates to the project-root templates directory
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'templates'))
    app = Flask(__name__, template_folder=template_dir)
    app.config.from_mapping(cfg.model_dump())
    # Enforce request size limits for safety
    try:
        mcl = int(app.config.get("MAX_CONTENT_LENGTH", cfg.MAX_CONTENT_LENGTH))
        app.config["MAX_CONTENT_LENGTH"] = mcl
    except Exception:
        app.config["MAX_CONTENT_LENGTH"] = 1_000_000

    # Default a conservative CSP in production if not explicitly configured
    try:
        if str(app.config.get("ENV", "")).lower().startswith("prod") and not app.config.get("CONTENT_SECURITY_POLICY"):
            # Plotly-friendly safe default CSP
            app.config["CONTENT_SECURITY_POLICY"] = (
                "default-src 'none'; "
                "script-src 'self' https://cdn.plot.ly; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "font-src 'self' data:; "
                "frame-ancestors 'none'"
            )
    except Exception:
        # Do not fail app startup due to config inspection
        pass

    # Configure logging
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "ts": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            # Attach contextual fields if present
            try:
                from flask import g, request
                payload.update({
                    "request_id": getattr(g, "request_id", ""),
                    "method": getattr(request, "method", None),
                    "path": getattr(request, "path", None),
                    "trace_id": getattr(g, "trace_id", ""),
                    "span_id": getattr(g, "span_id", ""),
                })
            except Exception:
                pass
            # Include environment and version if available
            try:
                payload["env"] = app.config.get("ENV")
            except Exception:
                pass
            try:
                from .version import __version__ as _ver
                payload["version"] = _ver
            except Exception:
                pass
            # Include exception info if present
            if getattr(record, "exc_info", None):
                try:
                    etype = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else None
                    evalue = str(record.exc_info[1]) if record.exc_info and record.exc_info[1] else None
                    payload["exc_type"] = etype
                    payload["exc_message"] = evalue
                except Exception:
                    pass
            # Also include any extra fields passed via logger.extra
            payload.update({k: v for k, v in record.__dict__.items() if k in {"request_id","method","path","status","duration_ms","env","version","trace_id","span_id"}})
            import json as _json
            return _json.dumps(payload)
    if app.config.get("LOG_FORMAT") == "json":
        # Configure root logger with JSON formatter so all module logs are consistent
        root = logging.getLogger()
        root.handlers = []
        root_handler = logging.StreamHandler()
        root_handler.setFormatter(JsonFormatter())
        root.addHandler(root_handler)
        root.setLevel(log_level)
        
        # Configure app and access loggers explicitly (do not propagate to avoid double logs)
        for logger_name in (app.logger.name, "flask.access"):
            logger = logging.getLogger(logger_name)
            logger.handlers = []
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            logger.addHandler(handler)
            logger.setLevel(log_level)
            logger.propagate = False
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
        app.logger.setLevel(log_level)

    # Setup security headers
    security_headers = SecurityHeaders(app, cfg.model_dump())
    
    # Setup CORS
    setup_cors(app, cfg.model_dump())

    # Startup auth configuration warning (log at startup, fail closed at request time)
    try:
        if app.config.get("ENABLE_AUTH", False):
            user_env = app.config.get("AUTH_USER_ENV", "API_USER")
            pass_env = app.config.get("AUTH_PASS_ENV", "API_PASS")
            expected_user = os.getenv(user_env, "")
            expected_pass = os.getenv(pass_env, "")
            if not expected_user or not expected_pass:
                app.logger.warning(
                    "ENABLE_AUTH is true but credentials are not set; expected envs %s and %s. Protected routes will return 503 until configured.",
                    user_env,
                    pass_env,
                )
    except Exception:
        # Never fail startup due to warning logic
        pass

    # Build and attach services container for DI
    services = build_services(cfg)
    # Flask doesn't have a built-in DI, use extensions dict to stash services
    app.extensions = getattr(app, 'extensions', {})
    app.extensions["services"] = services

    # Security headers + request id + access logging
    # Optional Prometheus metrics (gated by METRICS_ENABLED and import availability)
    metrics_enabled = bool(app.config.get("METRICS_ENABLED", True))
    try:
        if metrics_enabled:
            from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
            registry = CollectorRegistry(auto_describe=True)
            REQ_COUNT = Counter(
                "flask_requests_total",
                "Total HTTP requests",
                ["method", "path", "status"],
                registry=registry,
            )
            REQ_LATENCY = Histogram(
                "flask_request_duration_seconds",
                "Request duration in seconds",
                ["method", "path"],
                registry=registry,
            )
            # Cache metrics (services curve cache)
            CACHE_HITS = Gauge("curve_cache_hits_total", "Curve cache hits (process)", registry=registry)
            CACHE_MISSES = Gauge("curve_cache_misses_total", "Curve cache misses (process)", registry=registry)
            CACHE_EVICTIONS = Gauge("curve_cache_evictions_total", "Curve cache evictions (process)", registry=registry)
            # P1: Additional observability gauges
            BUILD_INFO = Gauge("build_info", "Build and runtime info", ["version", "env"], registry=registry)
            CACHE_SIZE = Gauge("curve_cache_size", "Current number of cached curves", registry=registry)
            CACHE_TTL = Gauge("curve_cache_ttl_seconds", "Curve cache TTL in seconds", registry=registry)

            @app.route("/metrics", methods=["GET"])  # only registered when prometheus_client available
            def metrics():
                # Update gauges at scrape time
                try:
                    from .services import get_cache_metrics as _gcm, get_cache_policy as _gcp
                    m = _gcm()
                    CACHE_HITS.set(float(m.get("hits", 0)))
                    CACHE_MISSES.set(float(m.get("misses", 0)))
                    CACHE_EVICTIONS.set(float(m.get("evictions", 0)))
                    p = _gcp()
                    CACHE_SIZE.set(float(p.get("size", 0)))
                    CACHE_TTL.set(float(p.get("ttl_seconds", 0)))
                except Exception:
                    pass
                # Build info gauge with labels
                try:
                    from .version import __version__ as _ver
                except Exception:
                    _ver = "unknown"
                try:
                    BUILD_INFO.labels(version=str(_ver), env=str(app.config.get("ENV"))).set(1)
                except Exception:
                    pass
                resp = Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)
                return resp
        else:
            registry = None
            REQ_COUNT = None
            REQ_LATENCY = None
    except Exception:
        # prometheus_client not available or failed to init -> disable metrics endpoint
        registry = None
        REQ_COUNT = None
        REQ_LATENCY = None

    @app.before_request
    def _before():
        g._start = time.time()
        header_name = app.config.get("REQUEST_ID_HEADER", "X-Request-ID")
        g.request_id = request.headers.get(header_name) or str(uuid.uuid4())
        # Optional trace context from W3C traceparent or custom headers
        try:
            tp = request.headers.get("traceparent") or request.headers.get("Traceparent")
            trace_id = ""
            span_id = ""
            if tp:
                # Format: version-traceid-spanid-flags
                parts = tp.split("-")
                if len(parts) >= 4:
                    trace_id = parts[1]
                    span_id = parts[2]
            # Fallback custom headers
            trace_id = trace_id or request.headers.get("X-Trace-Id", "")
            span_id = span_id or request.headers.get("X-Span-Id", "")
            g.trace_id = trace_id
            g.span_id = span_id
        except Exception:
            pass
        # Optional simple rate limiting for POST API endpoints
        try:
            if app.config.get("ENABLE_RATE_LIMIT", False) and request.method.upper() == "POST" and request.path in {"/api/price", "/api/solve"}:
                # Initialize limiter state lazily
                rl = app.extensions.get("rate_limit")
                if rl is None:
                    from collections import defaultdict
                    rl = {
                        "counters": defaultdict(list),  # key -> [timestamps]
                        "limit": int(app.config.get("RATE_LIMIT_PER_MIN", 60)),
                        "window": int(app.config.get("RATE_LIMIT_WINDOW_SECONDS", 60)),
                    }
                    app.extensions["rate_limit"] = rl
                key = f"{request.remote_addr or 'unknown'}|{request.path}"
                now_ts = time.time()
                window = int(rl.get("window", 60))
                limit = int(rl.get("limit", 60))
                buf = rl["counters"][key]
                # Drop old entries
                cutoff = now_ts - float(window)
                i = 0
                for t in buf:
                    if t >= cutoff:
                        break
                    i += 1
                if i > 0:
                    del buf[:i]
                # Check limit
                if len(buf) >= limit:
                    # Return 429 Too Many Requests
                    retry_after = max(1, int(window))
                    from flask import jsonify
                    if request.path.startswith("/api/"):
                        resp = jsonify({"error": {"type": "rate_limited", "message": "Too many requests. Please retry later."}})
                        resp.status_code = 429
                    else:
                        resp = Response("Too Many Requests", 429)
                    resp.headers["Retry-After"] = str(retry_after)
                    return resp
                # Record this request
                buf.append(now_ts)
        except Exception:
            # Do not fail request on limiter errors
            pass
        # Enforce auth in production if enabled, except for safe endpoints and when TESTING
        if app.config.get("ENABLE_AUTH", False):
            # Allow unauthenticated access to health/metrics endpoints
            if request.path in ("/metrics", "/health", "/live", "/ready"):
                return None
            user_env = app.config.get("AUTH_USER_ENV", "API_USER")
            pass_env = app.config.get("AUTH_PASS_ENV", "API_PASS")
            expected_user = os.getenv(user_env, "")
            expected_pass = os.getenv(pass_env, "")
            # In TESTING mode, bypass auth only if credentials are not configured
            if app.config.get("TESTING", False) and (not expected_user or not expected_pass):
                return None
            if not expected_user or not expected_pass:
                return ("Service not configured for auth", 503)
            auth = request.authorization
            if not auth or not (secrets.compare_digest(auth.username or "", expected_user) and secrets.compare_digest(auth.password or "", expected_pass)):
                resp = Response("Authentication required", 401)
                resp.headers["WWW-Authenticate"] = "Basic realm=Restricted"
                return resp

    @app.after_request
    def _after(response):
        # Request ID header
        header_name = app.config.get("REQUEST_ID_HEADER", "X-Request-ID")
        response.headers.setdefault(header_name, getattr(g, "request_id", ""))
        # Security headers
        if app.config.get("SECURITY_HEADERS_ENABLED", True):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            csp = app.config.get("CONTENT_SECURITY_POLICY", "")
            # Apply default CSP in production if not set (handles late config changes in tests)
            if (not csp) and str(app.config.get("ENV", "")).lower().startswith("prod"):
                csp = (
                    "default-src 'none'; "
                    "script-src 'self' https://cdn.plot.ly; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data:; "
                    "connect-src 'self'; "
                    "font-src 'self' data:; "
                    "frame-ancestors 'none'"
                )
            if csp:
                response.headers["Content-Security-Policy"] = csp
        # Metrics
        try:
            dur = max(time.time() - getattr(g, "_start", time.time()), 0.0)
            if 'REQ_COUNT' in locals() and REQ_COUNT is not None and 'REQ_LATENCY' in locals() and REQ_LATENCY is not None:
                # Avoid high cardinality by trimming long paths a bit (still simplistic)
                path_label = request.path[:100]
                REQ_COUNT.labels(method=request.method, path=path_label, status=str(response.status_code)).inc()
                REQ_LATENCY.labels(method=request.method, path=path_label).observe(dur)
            # Access log
            access_logger = logging.getLogger("flask.access")
            if app.config.get("LOG_FORMAT") == "json":
                access_logger.info(
                    "request",
                    extra={
                        "request_id": getattr(g, "request_id", ""),
                        "method": request.method,
                        "path": request.path,
                        "status": response.status_code,
                        "duration_ms": int(dur * 1000),
                        "trace_id": getattr(g, "trace_id", ""),
                        "span_id": getattr(g, "span_id", ""),
                    },
                )
            else:
                access_logger.info(f"{request.method} {request.path} -> {response.status_code} ({dur*1000:.1f} ms) req_id={getattr(g, 'request_id', '')}")
        except Exception:
            pass
        return response

    @app.route("/live", methods=["GET"]) 
    def live():
        try:
            payload = {"status": "ok"}
            return Response(json.dumps(payload), mimetype="application/json")
        except Exception:
            return Response(json.dumps({"status": "ok"}), mimetype="application/json")

    @app.route("/ready", methods=["GET"]) 
    def ready():
        try:
            # Hook for future dependency checks; currently always ok
            import platform
            from .version import __version__ as _ver
            payload = {
                "status": "ok",
                "service": "Gemini IRD Pricer Flask",
                "version": _ver,
                "python": platform.python_version(),
                "env": app.config.get("ENV", "development"),
            }
            return Response(json.dumps(payload), mimetype="application/json")
        except Exception:
            return Response(json.dumps({"status": "ok"}), mimetype="application/json")

    @app.route("/health", methods=["GET"]) 
    def health():
        try:
            import platform
            from .version import __version__ as _ver
            payload = {
                "status": "ok",
                "service": "Gemini IRD Pricer Flask",
                "version": _ver,
                "python": platform.python_version(),
                "env": app.config.get("ENV", "development"),
            }
            return Response(json.dumps(payload), mimetype="application/json")
        except Exception:
            return Response(json.dumps({"status": "ok"}), mimetype="application/json")

    # Payload too large handler (413)
    @app.errorhandler(413)
    def payload_too_large(e):
        try:
            from flask import jsonify, request as _req
            if str(getattr(_req, "path", "")).startswith("/api/"):
                return jsonify({"error": {"type": "payload_too_large", "message": "Request payload too large."}}), 413
        except Exception:
            pass
        return Response("Request entity too large", 413)

    register_routes(app, services)
    return app
