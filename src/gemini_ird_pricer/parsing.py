from __future__ import annotations
import os
import re
import math
from datetime import datetime, timedelta
import pandas as pd
from .utils import parse_valuation_date_from_filename, ensure_in_data_dir, apply_valuation_time
from .config import get_config
from .error_handler import ValidationError, BusinessLogicError
from .performance import performance_monitor


@performance_monitor("parse_notional")
def parse_notional(notional_str: str) -> float:
    """Parse notional amount with enhanced validation."""
    if not isinstance(notional_str, str):
        raise ValidationError("Notional must be a string")
    
    s = notional_str.lower().strip()
    if not s:
        raise ValidationError("Notional cannot be empty")
    
    match = re.match(r"^(\d+\.?\d*)\s*([mkb])?$", s)
    if not match:
        raise ValidationError("Invalid notional format. Examples: 1000000, 10m, 250k.")
    
    value_str, suffix = match.groups()
    
    try:
        v = float(value_str)
    except ValueError:
        raise ValidationError(f"Invalid numeric value: {value_str}")
    
    if suffix == "m":
        v *= 1_000_000
    elif suffix == "k":
        v *= 1_000
    elif suffix == "b":
        v *= 1_000_000_000
    
    if v <= 0:
        raise BusinessLogicError("Notional must be positive.")
    
    # Safety cap from configuration
    try:
        cfg = get_config()
        notional_max = float(getattr(cfg, "NOTIONAL_MAX", 1e11))
        if v > notional_max:
            raise BusinessLogicError(f"Notional exceeds maximum of {notional_max:,.0f}.")
    except Exception as e:
        # Log config error but don't fail parsing
        import logging
        logging.getLogger(__name__).warning(f"Config error checking notional max: {e}")
    
    return v


@performance_monitor("parse_maturity_date")
def parse_maturity_date(maturity_str: str) -> datetime:
    """Parse maturity date with enhanced validation."""
    if not isinstance(maturity_str, str):
        raise ValidationError("Maturity date must be a string")
    
    s = maturity_str.lower().strip()
    if not s:
        raise ValidationError("Maturity date cannot be empty")
    
    # Try parsing as ISO date first
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        if dt <= datetime.today():
            raise BusinessLogicError("Maturity date must be in the future")
        return apply_valuation_time(dt)
    except ValueError:
        pass
    
    # Parse tenor format (e.g., "5y", "18m", "30d")
    match = re.match(r"^(\d+)\s*(y|m|d)?$", s)
    if not match:
        raise ValidationError("Invalid maturity date format. Examples: 2028-12-31, 5y, 18m, 30d.")
    
    value_str, unit = match.groups()
    
    try:
        value_i = int(value_str)
    except ValueError:
        raise ValidationError(f"Invalid numeric value: {value_str}")
    
    if value_i <= 0:
        raise BusinessLogicError("Maturity tenor must be positive.")
    
    try:
        cfg = get_config()
        max_years = getattr(cfg, "MATURITY_MAX_YEARS", 100)
    except Exception:
        max_years = 100
    
    today = datetime.today()
    
    # Calculate maturity date and validate bounds
    if unit == "y" or unit is None:
        if value_i > max_years:
            raise BusinessLogicError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i * 365)
    elif unit == "m":
        if (value_i / 12) > max_years:
            raise BusinessLogicError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i * 30)
    elif unit == "d":
        if (value_i / 365) > max_years:
            raise BusinessLogicError(f"Maturity exceeds maximum of {max_years} years.")
        dt = today + timedelta(days=value_i)
    else:
        raise ValidationError(f"Invalid maturity unit: {unit}")
    
    return apply_valuation_time(dt)


@performance_monitor("load_yield_curve")
def load_yield_curve(file_path: str, form_data=None, valuation_date: datetime | None = None) -> pd.DataFrame:
    """Load a yield curve CSV with enhanced validation and error handling."""
    # Security: ensure file access is limited to the configured data directory
    try:
        ensure_in_data_dir(file_path)
    except Exception as e:
        raise ValidationError(f"Invalid file path: {e}")

    if form_data is not None and hasattr(form_data, "getlist"):
        return _load_curve_from_form_data(form_data, file_path, valuation_date)
    
    return _load_curve_from_csv(file_path, valuation_date)


def _load_curve_from_form_data(form_data, file_path: str, valuation_date: datetime | None) -> pd.DataFrame:
    """Load curve from form data with validation."""
    form_maturities = form_data.getlist("curve_maturity")
    form_rates = form_data.getlist("curve_rate")
    
    if len(form_maturities) == 0 and len(form_rates) == 0:
        return _load_curve_from_csv(file_path, valuation_date)
    
    try:
        cfg = get_config()
        max_points = getattr(cfg, "CURVE_MAX_POINTS", 200)
    except Exception:
        max_points = 200
    
    # Validate input lengths
    if len(form_maturities) != len(form_rates):
        raise ValidationError("Curve inputs length mismatch between maturities and rates.")
    
    if len(form_maturities) > max_points:
        raise ValidationError(f"Too many curve points; maximum is {max_points}.")
    
    if len(form_maturities) == 0:
        raise ValidationError("At least one curve point is required.")
    
    # Parse and validate data
    try:
        maturities = [float(m) for m in form_maturities]
        rates = [float(r) / 100 for r in form_rates]  # Convert from percentage
    except ValueError as e:
        raise ValidationError(f"Invalid numeric data in curve: {e}")
    
    # Validate data quality
    _validate_curve_data(maturities, rates)
    
    if valuation_date is None:
        valuation_date = parse_valuation_date_from_filename(file_path)
    
    # Build DataFrame
    dates = [valuation_date + timedelta(days=int(y * 365)) for y in maturities]
    df = pd.DataFrame({"Maturity (Years)": maturities, "Rate": rates, "Date": dates})
    df = df.set_index("Date")
    
    return df


def _load_curve_from_csv(file_path: str, valuation_date: datetime | None) -> pd.DataFrame:
    """Load curve from CSV file with validation."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Curve file not found: {file_path}")
    
    if valuation_date is None:
        try:
            valuation_date = parse_valuation_date_from_filename(file_path)
        except Exception as e:
            raise ValidationError(f"Cannot parse valuation date from filename: {e}")
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValidationError(f"Cannot read CSV file: {e}")
    
    # Validate CSV structure
    if df.shape[1] < 2:
        cols = list(df.columns)
        raise ValidationError(f"CSV must have at least two columns: Maturity (Years), Rate; found {len(cols)} columns: {cols}")
    
    df = df.iloc[:, :2]
    df.columns = ["Maturity (Years)", "Rate"]
    
    # Validate data types
    if not pd.api.types.is_numeric_dtype(df["Maturity (Years)"]):
        raise ValidationError("First column must be numeric maturities in years.")
    
    if not pd.api.types.is_numeric_dtype(df["Rate"]):
        raise ValidationError("Second column must be numeric rates in percent.")
    
    try:
        cfg = get_config()
        max_points = getattr(cfg, "CURVE_MAX_POINTS", 200)
    except Exception:
        max_points = 200
    
    if df.shape[0] > max_points:
        raise ValidationError(f"CSV has too many rows; maximum is {max_points}.")
    
    if df.shape[0] == 0:
        raise ValidationError("CSV file is empty.")
    
    # Validate data quality
    maturities = df["Maturity (Years)"].astype(float).tolist()
    rates = df["Rate"].astype(float).tolist()
    
    _validate_curve_data(maturities, rates)
    
    # Convert rates from percentage to decimal
    df["Rate"] = df["Rate"] / 100
    df["Date"] = df["Maturity (Years)"].apply(lambda y: valuation_date + timedelta(days=int(float(y) * 365)))
    df = df.set_index("Date")
    
    return df


def _validate_curve_data(maturities: list[float], rates: list[float]) -> None:
    """Validate curve data quality."""
    # Check for finite values
    if any(not math.isfinite(m) for m in maturities):
        raise ValidationError("Maturities must be finite numbers.")
    
    if any(not math.isfinite(r) for r in rates):
        raise ValidationError("Rates must be finite numbers.")
    
    # Check bounds
    if any(m < 0 for m in maturities):
        raise ValidationError("Maturity years must be non-negative.")
    
    if any(r < -10.0 or r > 50.0 for r in rates):
        raise ValidationError("Rates must be between -10% and 50%.")
    
    # Check ordering
    if any(m2 <= m1 for m1, m2 in zip(maturities, maturities[1:])):
        raise ValidationError("Maturities must be strictly increasing.")
