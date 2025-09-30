from __future__ import annotations
import os
import re
import math
from datetime import datetime, timedelta
import pandas as pd
from .utils import parse_valuation_date_from_filename, ensure_in_data_dir, apply_valuation_time
from .config import get_config


def parse_notional(notional_str: str) -> float:
    s = notional_str.lower().strip()
    match = re.match(r"(\d+\.?\d*)\s*([mkb])?", s)
    if not match:
        raise ValueError("Invalid notional format. Examples: 1000000, 10m, 250k.")
    value, suffix = match.groups()
    v = float(value)
    if suffix == "m":
        v *= 1_000_000
    elif suffix == "k":
        v *= 1_000
    elif suffix == "b":
        v *= 1_000_000_000
    if v <= 0:
        raise ValueError("Notional must be positive.")
    # Safety cap from configuration
    try:
        from .config import get_config
        cfg = get_config()
        notional_max = float(getattr(cfg, "NOTIONAL_MAX", 1e11))
        if v > notional_max:
            raise ValueError(f"Notional exceeds maximum of {notional_max:,.0f}.")
    except Exception:
        # On config errors, proceed without additional cap
        pass
    return v


def parse_maturity_date(maturity_str: str) -> datetime:
    s = maturity_str.lower().strip()
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return apply_valuation_time(dt)
    except ValueError:
        pass
    match = re.match(r"(\d+)\s*(y|m|d)?", s)
    if not match:
        raise ValueError("Invalid maturity date format. Examples: 2028-12-31, 5y, 18m, 30d.")
    value, unit = match.groups()
    value_i = int(value)
    if value_i <= 0:
        raise ValueError("Maturity tenor must be positive.")
    cfg = get_config()
    max_years = getattr(cfg, "MATURITY_MAX_YEARS", 100)
    today = datetime.today()
    # Enforce upper bounds regardless of unit
    if unit == "y":
        if value_i > max_years:
            raise ValueError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i * 365)
    elif unit == "m":
        if (value_i / 12) > max_years:
            raise ValueError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i * 30)
    elif unit == "d":
        if (value_i / 365) > max_years:
            raise ValueError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i)
    else:
        # No unit provided -> treat as years
        if value_i > max_years:
            raise ValueError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i * 365)
    return apply_valuation_time(dt)


def load_yield_curve(file_path: str, form_data=None, valuation_date: datetime | None = None) -> pd.DataFrame:
    """Load a yield curve CSV into a DataFrame with Date index.

    If form_data provided, it must include curve_maturity and curve_rate fields.
    Rates are provided in percent and converted to decimals. Maturities are years.
    """
    # Security: ensure file access is limited to the configured data directory
    ensure_in_data_dir(file_path)

    if form_data is not None and hasattr(form_data, "getlist"):
        # Only use form-provided curve points when at least one point is present
        form_maturities = form_data.getlist("curve_maturity")
        form_rates = form_data.getlist("curve_rate")
        if len(form_maturities) > 0 or len(form_rates) > 0:
            cfg = get_config()
            maturities = [float(m) for m in form_maturities]
            rates = [float(r) / 100 for r in form_rates]
            # Basic validation
            if len(maturities) != len(rates):
                raise ValueError("Curve inputs length mismatch between maturities and rates.")
            if len(maturities) > getattr(cfg, "CURVE_MAX_POINTS", 200):
                raise ValueError(f"Too many curve points; maximum is {getattr(cfg, 'CURVE_MAX_POINTS', 200)}.")
            if any((not math.isfinite(m)) for m in maturities):
                raise ValueError("Maturities must be finite numbers.")
            if any((not math.isfinite(r)) for r in rates):
                raise ValueError("Rates must be finite numbers.")
            if any(m < 0 for m in maturities):
                raise ValueError("Maturity years must be non-negative.")
            if any(r < -0.10 or r > 0.50 for r in rates):
                raise ValueError("Rates must be between -10% and 50% for safety.")
            if any(m2 <= m1 for m1, m2 in zip(maturities, maturities[1:])):
                raise ValueError("Maturities must be strictly increasing.")

            if valuation_date is None:
                valuation_date = parse_valuation_date_from_filename(file_path)
            # Use ACT/365F by default for mapping years to days when building dates
            dates = [valuation_date + timedelta(days=int(y * 365)) for y in maturities]
            df = pd.DataFrame({"Maturity (Years)": maturities, "Rate": rates, "Date": dates})
            df = df.set_index("Date")
            return df

    if valuation_date is None:
        valuation_date = parse_valuation_date_from_filename(file_path)
    df = pd.read_csv(file_path)
    # CSV schema validation: must have at least two numeric columns
    if df.shape[1] < 2:
        cols = list(df.columns)
        raise ValueError(f"CSV must have at least two columns: Maturity (Years), Rate; found {len(cols)} columns: {cols}")
    df = df.iloc[:, :2]
    df.columns = ["Maturity (Years)", "Rate"]
    if not pd.api.types.is_numeric_dtype(df["Maturity (Years)"]):
        raise ValueError("First column must be numeric maturities in years.")
    if not pd.api.types.is_numeric_dtype(df["Rate"]):
        raise ValueError("Second column must be numeric rates in percent.")
    cfg = get_config()
    max_points = getattr(cfg, "CURVE_MAX_POINTS", 200)
    if df.shape[0] > max_points:
        raise ValueError(f"CSV has too many rows; maximum is {max_points}.")
    # Basic validation similar to form-data path
    if (df["Maturity (Years)"] < 0).any():
        raise ValueError("Maturity years must be non-negative.")
    if not df["Maturity (Years)"].apply(lambda x: math.isfinite(float(x))).all():
        raise ValueError("Maturities must be finite numbers.")
    if not df["Rate"].apply(lambda x: math.isfinite(float(x))).all():
        raise ValueError("Rates must be finite numbers.")
    maturities = df["Maturity (Years)"].astype(float).tolist()
    if any(m2 <= m1 for m1, m2 in zip(maturities, maturities[1:])):
        raise ValueError("Maturities must be strictly increasing.")
    if ((df["Rate"] < -10.0) | (df["Rate"] > 50.0)).any():
        raise ValueError("Rates must be between -10% and 50%.")
    df["Rate"] = df["Rate"] / 100
    df["Date"] = df["Maturity (Years)"].apply(lambda y: valuation_date + timedelta(days=int(float(y) * 365)))
    df = df.set_index("Date")
    return df
