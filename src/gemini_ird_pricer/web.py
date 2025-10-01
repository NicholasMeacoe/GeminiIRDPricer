from __future__ import annotations
from flask import Flask, render_template, request, jsonify
from pydantic import ValidationError as PydanticValidationError
from .parsing import parse_notional, parse_maturity_date
from .plotting import plot_yield_curve
from .services import Services
from .utils import find_curve_file
from .api_schemas import PriceRequest, SolveRequest
from .error_handler import ErrorHandler, ValidationError, BusinessLogicError
from .performance import performance_monitor
import logging

logger = logging.getLogger(__name__)


def register_routes(app: Flask, services: Services | None = None) -> None:
    """Register all routes with enhanced error handling."""
    
    # Initialize error handler
    error_handler = ErrorHandler(app)
    
    @app.errorhandler(404)
    def not_found(e):
        return render_template("index.html", error="Page not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled server error")
        return render_template("index.html", error="An unexpected error occurred."), 500

    @app.route("/", methods=["GET", "POST"])
    @performance_monitor("index_route")
    def index():
        try:
            file_path = find_curve_file(app.config)
        except FileNotFoundError:
            return render_template("index.html", error="No SwapRates file found.")
        except Exception as e:
            logger.error(f"Error finding curve file: {e}")
            return render_template("index.html", error="Error accessing curve data."), 500

        if request.method == "POST":
            return _handle_post_request(file_path, services, app)
        else:
            return _handle_get_request(file_path, services)

    # JSON API endpoints
    @app.route("/api/price", methods=["POST"])
    @performance_monitor("api_price")
    def api_price():
        return _handle_api_price(services, app)

    @app.route("/api/solve", methods=["POST"])
    @performance_monitor("api_solve")
    def api_solve():
        return _handle_api_solve(services, app)


def _handle_post_request(file_path: str, services: Services | None, app: Flask):
    """Handle POST request to index route."""
    try:
        # Parse notional first with enhanced error handling
        notional_str = request.form.get("notional", "")
        notional = parse_notional(notional_str)
        
        # Load curve data
        svc = services or app.extensions.get("services")
        if svc:
            yield_curve_df = svc.load_curve(file_path, request.form)
        else:
            from .parsing import load_yield_curve as _load
            yield_curve_df = _load(file_path, request.form)

        maturity_date_str = request.form["maturity_date"]
        maturity_date = parse_maturity_date(maturity_date_str)

        if request.form.get("action") == "solve":
            # Solve for par rate
            if svc:
                par_rate = svc.solve_par_rate(notional, maturity_date, yield_curve_df)
            else:
                from .pricer import solve_par_rate as _solve
                par_rate = _solve(notional, maturity_date, yield_curve_df)
            fixed_rate_input = par_rate * 100
            fixed_rate_for_calc = par_rate
        else:
            # Use provided fixed rate
            try:
                fixed_rate_input = float(request.form["fixed_rate"])
                fixed_rate_for_calc = fixed_rate_input / 100
            except (ValueError, KeyError) as e:
                raise ValidationError(f"Invalid fixed rate: {e}")

        # Price the swap
        if svc:
            swap_value, schedule = svc.price_swap(notional, fixed_rate_for_calc, maturity_date, yield_curve_df, app.config)
        else:
            from .pricer import price_swap as _price
            swap_value, schedule = _price(notional, fixed_rate_for_calc, maturity_date, yield_curve_df, app.config)
        
        plot_json = plot_yield_curve(yield_curve_df)

        yield_curve_display = yield_curve_df.copy()
        yield_curve_display["Rate"] *= 100

        prec = int(app.config.get("NUM_PRECISION", 4))
        return render_template(
            "index.html",
            result=f"Swap Value: {swap_value:,.{prec}f}",
            notional=notional_str,
            fixed_rate=fixed_rate_input,
            maturity_date=maturity_date_str,
            schedule=schedule,
            plot_json=plot_json,
            yield_curve=yield_curve_display.reset_index().to_dict("records"),
        )
    
    except ValidationError as ve:
        logger.info(f"Validation error: {ve}")
        return render_template("index.html", error=f"Error: {ve}")
    except BusinessLogicError as ble:
        logger.info(f"Business logic error: {ble}")
        return render_template("index.html", error=f"Error: {ble}")
    except Exception as e:
        logger.exception("Unhandled error in POST request")
        return render_template("index.html", error="An unexpected error occurred."), 500


def _handle_get_request(file_path: str, services: Services | None):
    """Handle GET request to index route."""
    try:
        svc = services or app.extensions.get("services")
        if svc:
            yield_curve_df = svc.load_curve(file_path)
        else:
            from .parsing import load_yield_curve as _load
            yield_curve_df = _load(file_path)
        
        plot_json = plot_yield_curve(yield_curve_df)

        yield_curve_display = yield_curve_df.copy()
        yield_curve_display["Rate"] *= 100

        return render_template(
            "index.html",
            plot_json=plot_json,
            yield_curve=yield_curve_display.reset_index().to_dict("records"),
            yield_curve_json=yield_curve_df.to_json(orient="split"),
        )
    except Exception as e:
        logger.exception("Error loading curve for GET request")
        return render_template("index.html", error="Error loading curve data."), 500


def _json_error(status: int, msg: str, err_type: str = "input_error", details: dict | None = None):
    """Create standardized JSON error response."""
    def _safe(obj):
        try:
            import json as _json
            _json.dumps(obj)
            return obj
        except Exception:
            if isinstance(obj, dict):
                return {str(k): _safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_safe(x) for x in obj]
            return str(obj)
    
    payload = {"error": {"type": err_type, "message": msg}}
    if details:
        payload["error"]["details"] = _safe(details)
    
    resp = jsonify(payload)
    return resp, status


class _FormProxy:
    """Proxy for curve override data."""
    def __init__(self, maturities: list[float], rates_pct: list[float]):
        self._m = [str(m) for m in maturities]
        self._r = [str(r) for r in rates_pct]
    
    def getlist(self, key: str):
        if key == "curve_maturity":
            return self._m
        if key == "curve_rate":
            return self._r
        return []


def _load_curve_with_optional_overrides(file_path: str, svc: Services | None, data: dict):
    """Load curve with optional overrides from API request."""
    curve = data.get("curve")
    form = None
    
    if isinstance(curve, list) and curve:
        try:
            maturities: list[float] = []
            rates_pct: list[float] = []
            for i, pt in enumerate(curve):
                if not isinstance(pt, dict):
                    raise ValidationError("Curve points must be objects with 'maturity' and 'rate'.")
                
                try:
                    m = float(pt.get("maturity"))
                    r = float(pt.get("rate"))  # percent
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Invalid numeric value in curve point {i}: {e}")
                
                maturities.append(m)
                rates_pct.append(r)
            
            form = _FormProxy(maturities, rates_pct)
        except Exception as ex:
            raise ValidationError(f"Invalid curve override: {ex}")
    
    if svc:
        return svc.load_curve(file_path, form)
    else:
        from .parsing import load_yield_curve as _load
        return _load(file_path, form)


def _handle_api_price(services: Services | None, app: Flask):
    """Handle API price endpoint."""
    try:
        if not request.is_json:
            return _json_error(400, "Request body must be JSON.")
        
        data = request.get_json(silent=True) or {}
        
        try:
            req = PriceRequest(**data)
        except PydanticValidationError as ve:
            return _json_error(400, "Invalid request.", err_type="validation_error", details={"errors": ve.errors()})
        
        # Parse and validate inputs
        notional = parse_notional(str(req.notional))
        maturity_date = parse_maturity_date(str(req.maturity_date))
        fixed_rate = float(req.fixed_rate) / 100.0

        # Load curve
        try:
            file_path = find_curve_file(app.config)
        except FileNotFoundError:
            return _json_error(404, "No SwapRates file found.", err_type="not_found")
        
        svc = services or app.extensions.get("services")
        yc = _load_curve_with_optional_overrides(file_path, svc, req.model_dump())
        
        # Price swap
        if svc:
            value, schedule = svc.price_swap(notional, fixed_rate, maturity_date, yc, app.config)
        else:
            from .pricer import price_swap as _price
            value, schedule = _price(notional, fixed_rate, maturity_date, yc, app.config)
        
        return jsonify({"result": {"npv": float(value), "schedule": schedule}})
    
    except (ValidationError, BusinessLogicError) as e:
        return _json_error(400, str(e), err_type="input_error")
    except Exception as e:
        logger.exception("Unhandled error in /api/price")
        return _json_error(500, "An unexpected error occurred.", err_type="server_error")


def _handle_api_solve(services: Services | None, app: Flask):
    """Handle API solve endpoint."""
    try:
        if not request.is_json:
            return _json_error(400, "Request body must be JSON.")
        
        data = request.get_json(silent=True) or {}
        
        try:
            req = SolveRequest(**data)
        except PydanticValidationError as ve:
            return _json_error(400, "Invalid request.", err_type="validation_error", details={"errors": ve.errors()})
        
        # Parse and validate inputs
        notional = parse_notional(str(req.notional))
        maturity_date = parse_maturity_date(str(req.maturity_date))

        # Load curve
        try:
            file_path = find_curve_file(app.config)
        except FileNotFoundError:
            return _json_error(404, "No SwapRates file found.", err_type="not_found")
        
        svc = services or app.extensions.get("services")
        yc = _load_curve_with_optional_overrides(file_path, svc, req.model_dump())
        
        # Solve for par rate
        if svc:
            par = svc.solve_par_rate(notional, maturity_date, yc)
        else:
            from .pricer import solve_par_rate as _solve
            par = _solve(notional, maturity_date, yc)
        
        return jsonify({"result": {"par_rate_percent": float(par * 100.0)}})
    
    except (ValidationError, BusinessLogicError) as e:
        return _json_error(400, str(e), err_type="input_error")
    except Exception as e:
        logger.exception("Unhandled error in /api/solve")
        return _json_error(500, "An unexpected error occurred.", err_type="server_error")
