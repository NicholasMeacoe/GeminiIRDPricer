from __future__ import annotations
from flask import Flask, render_template, request
from pydantic import ValidationError
from .parsing import parse_notional, parse_maturity_date
from .plotting import plot_yield_curve
from .services import Services
from .utils import find_curve_file
from .api_schemas import PriceRequest, SolveRequest
from .error_handler import ErrorHandler
from .security import require_auth






def register_routes(app: Flask, services: Services | None = None) -> None:
    @app.errorhandler(404)
    def not_found(e):
        return render_template("index.html", error="Page not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return render_template("index.html", error="An unexpected error occurred."), 500

    @app.route("/", methods=["GET", "POST"])
    def index():
        try:
            file_path = find_curve_file(app.config)
        except Exception:
            file_path = None
        if not file_path:
            return render_template("index.html", error="No SwapRates file found.")

        if request.method == "POST":
            # Parse notional first: on failure, return 400 per tests
            notional_str = request.form.get("notional", "")
            try:
                notional = parse_notional(notional_str)
            except ValueError as ve:
                app.logger.info("User input error", extra={"error": str(ve)})
                msg = str(ve).lower()
                if "must be positive" in msg or notional_str.strip().startswith("-"):
                    return render_template("index.html", error=f"Error: {ve}") , 400
                # For other notional parsing errors (e.g., bad format), return 200 with error
                return render_template("index.html", error=f"Error: {ve}")
            try:
                svc = services or app.extensions.get("services")
                yield_curve_df = (svc.load_curve if svc else None)(file_path, request.form) if svc else None
                if yield_curve_df is None:
                    # Fallback: import directly if services missing
                    from .parsing import load_yield_curve as _load
                    yield_curve_df = _load(file_path, request.form)

                maturity_date_str = request.form["maturity_date"]
                maturity_date = parse_maturity_date(maturity_date_str)

                if request.form.get("action") == "solve":
                    if svc:
                        par_rate = svc.solve_par_rate(notional, maturity_date, yield_curve_df)
                    else:
                        from .pricer import solve_par_rate as _solve
                        par_rate = _solve(notional, maturity_date, yield_curve_df)
                    fixed_rate_input = par_rate * 100
                    fixed_rate_for_calc = par_rate
                else:
                    fixed_rate_input = float(request.form["fixed_rate"])
                    fixed_rate_for_calc = fixed_rate_input / 100

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
            except ValueError as ve:
                app.logger.info("User input error", extra={"error": str(ve)})
                # Return 200 with error message for other user input errors per legacy behavior
                return render_template("index.html", error=f"Error: {ve}")
            except Exception as e:
                app.logger.exception("Unhandled server error during POST")
                return render_template("index.html", error="An unexpected error occurred."), 500
        else:
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

    # ---- JSON API endpoints (/api) ----
    def _json_error(status: int, msg: str, err_type: str = "input_error", details: dict | None = None):
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
        from flask import jsonify
        resp = jsonify(payload)
        return resp, status

    class _FormProxy:
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
        curve = data.get("curve")
        form = None
        if isinstance(curve, list) and curve:
            try:
                maturities: list[float] = []
                rates_pct: list[float] = []
                for i, pt in enumerate(curve):
                    if not isinstance(pt, dict):
                        raise ValueError("Curve points must be objects with 'maturity' and 'rate'.")
                    m = float(pt.get("maturity"))
                    r = float(pt.get("rate"))  # percent
                    maturities.append(m)
                    rates_pct.append(r)
                form = _FormProxy(maturities, rates_pct)
            except Exception as ex:
                raise ValueError(f"Invalid curve override: {ex}")
        if svc:
            return svc.load_curve(file_path, form)
        else:
            from .parsing import load_yield_curve as _load
            return _load(file_path, form)

    @app.route("/api/price", methods=["POST"])
    def api_price():
        try:
            if not request.is_json:
                return _json_error(400, "Request body must be JSON.")
            data = request.get_json(silent=True) or {}
            try:
                req = PriceRequest(**data)
            except ValidationError as ve:
                return _json_error(400, "Invalid request.", err_type="validation_error", details={"errors": ve.errors()})
            try:
                notional = parse_notional(str(req.notional))
                maturity_date = parse_maturity_date(str(req.maturity_date))
                fixed_rate = float(req.fixed_rate) / 100.0
            except ValueError as ve:
                return _json_error(400, str(ve), err_type="input_error")

            try:
                file_path = find_curve_file(app.config)
            except Exception:
                file_path = None
            if not file_path:
                return _json_error(404, "No SwapRates file found.", err_type="not_found")
            svc = services or app.extensions.get("services")
            yc = _load_curve_with_optional_overrides(file_path, svc, req.model_dump())
            if svc:
                value, schedule = svc.price_swap(notional, fixed_rate, maturity_date, yc, app.config)
            else:
                from .pricer import price_swap as _price
                value, schedule = _price(notional, fixed_rate, maturity_date, yc, app.config)
            from flask import jsonify
            return jsonify({"result": {"npv": float(value), "schedule": schedule}})
        except ValueError as ve:
            return _json_error(400, str(ve), err_type="input_error")
        except Exception:
            app.logger.exception("Unhandled server error in /api/price")
            return _json_error(500, "An unexpected error occurred.", err_type="server_error")

    @app.route("/api/solve", methods=["POST"])
    def api_solve():
        try:
            if not request.is_json:
                return _json_error(400, "Request body must be JSON.")
            data = request.get_json(silent=True) or {}
            try:
                req = SolveRequest(**data)
            except ValidationError as ve:
                return _json_error(400, "Invalid request.", err_type="validation_error", details={"errors": ve.errors()})
            try:
                notional = parse_notional(str(req.notional))
                maturity_date = parse_maturity_date(str(req.maturity_date))
            except ValueError as ve:
                return _json_error(400, str(ve), err_type="input_error")

            try:
                file_path = find_curve_file(app.config)
            except Exception:
                file_path = None
            if not file_path:
                return _json_error(404, "No SwapRates file found.", err_type="not_found")
            svc = services or app.extensions.get("services")
            yc = _load_curve_with_optional_overrides(file_path, svc, req.model_dump())
            if svc:
                par = svc.solve_par_rate(notional, maturity_date, yc)
            else:
                from .pricer import solve_par_rate as _solve
                par = _solve(notional, maturity_date, yc)
            from flask import jsonify
            return jsonify({"result": {"par_rate_percent": float(par * 100.0)}})
        except ValueError as ve:
            return _json_error(400, str(ve), err_type="input_error")
        except Exception:
            app.logger.exception("Unhandled server error in /api/solve")
            return _json_error(500, "An unexpected error occurred.", err_type="server_error")
