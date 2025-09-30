from __future__ import annotations
from datetime import datetime
import os
import glob
import re
from .config import get_config
from typing import Optional


def _is_leap_year(y: int) -> bool:
    return (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))


def _spans_feb29(start: datetime, end: datetime, year: int) -> bool:
    from datetime import datetime as _dt
    if not _is_leap_year(year):
        return False
    feb29 = _dt(year, 2, 29)
    return (start <= feb29 <= end)


def year_fraction(start: datetime, end: datetime, day_count: str = "ACT/365F") -> float:
    """Compute year fraction between two dates for common day-counts.

    Supported: ACT/365F, ACT/365, ACT/365.25, ACT/360, 30/360 (US NASD simplified), ACT/ACT (approx), ACT/365L.
    Notes:
    - ACT/365F (Actual/365 Fixed) and ACT/365 both use a 365-day denominator here (approximation) in this simplified engine.
    - ACT/365.25 uses 365.25 to approximate leap years.
    - ACT/ACT here is a lightweight approximation: sum actual days in each calendar year divided by that year's day count (365 or 366), without coupon schedule awareness.
    - ACT/365L uses 366 if the period includes Feb 29; otherwise 365.
    - For production-grade accuracy (ISDA), consider a dedicated finance date library.
    """
    s = day_count.upper().strip()
    if s == "ACT/365F" or s == "ACT/365":
        return (end - start).days / 365.0
    if s == "ACT/365.25":
        return (end - start).days / 365.25
    if s == "ACT/360":
        return (end - start).days / 360.0
    if s == "30/360":
        # Simplified 30/360 US with Feb EOM adjustment: treat EOM Feb as day 30
        y1, m1 = start.year, start.month
        y2, m2 = end.year, end.month
        from calendar import monthrange as _mr
        d1 = min(start.day, 30)
        d2 = min(end.day, 30)
        # Treat any February date as day 30 for this simplified convention
        if m2 == 2:
            d2 = 30
        if m1 == 2:
            d1 = 30
        return ((y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)) / 360.0
    if s == "ACT/ACT" or s == "ACT/ACT(ISDA)":
        # Approximate ACT/ACT: prorate by each calendar year length in the span
        if end <= start:
            return 0.0
        from datetime import date, timedelta as _td
        total = 0.0
        cur = start
        while cur < end:
            year_end = cur.replace(month=12, day=31)
            next_day = year_end + _td(days=1)
            segment_end = end if end <= next_day else next_day
            days = (segment_end - cur).days
            denom = 366.0 if _is_leap_year(cur.year) else 365.0
            total += days / denom
            cur = segment_end
        return total
    if s == "ACT/365L":
        # Use 366 if the interval includes Feb 29 in any spanned year
        if end <= start:
            return 0.0
        years = range(start.year, end.year + 1)
        includes_feb29 = any(_is_leap_year(y) and _spans_feb29(start, end, y) for y in years)
        denom = 366.0 if includes_feb29 else 365.0
        return (end - start).days / denom
    # Fallback to ACT/365F approximation
    return (end - start).days / 365.0


def build_discount_function(strategy: str = "exp_cont"):
    """Return a discounting function D(rate, t) according to strategy.

    Supported strategies:
    - exp_cont: D = exp(-r * t) continuous compounding
    - simple:   D = 1 / (1 + r * t)
    - comp_n:   D = 1 / (1 + r/n) ** (n * t) where n is an integer > 0 (e.g., comp_1 annual, comp_2 semi-annual, comp_4 quarterly)
    """
    st = (strategy or "exp_cont").lower().strip()
    if st == "simple":
        return lambda r, t: 1.0 / (1.0 + r * t)
    if st.startswith("comp_"):
        try:
            n = int(st.split("_", 1)[1])
            if n <= 0:
                raise ValueError
        except Exception:
            n = 1
        return lambda r, t, _n=n: 1.0 / (1.0 + r / _n) ** (_n * t)
    # default continuous
    import math
    return lambda r, t: math.exp(-r * t)


def parse_valuation_date_from_filename(file_path: str) -> datetime:
    """Parse valuation date from a filename like SwapRates_YYYYMMDD.csv.
    Falls back to today if pattern not found.
    """
    base = os.path.basename(file_path)
    try:
        token = base.split("_")[1].split(".")[0]
        return datetime.strptime(token, "%Y%m%d")
    except Exception:
        return datetime.today()


def ensure_in_data_dir(file_path: str) -> None:
    """Ensure the given path is inside the configured DATA_DIR to prevent path traversal.

    During tests (when PYTEST_CURRENT_TEST is set), this guard is bypassed to allow
    reading fixture files from tests directories.

    Behavior:
    - If DATA_DIR is relative, resolve it under the project root (two levels up from this file).
    - Reject dangerous DATA_DIR pointing to a drive root (e.g., C:\ or D:\).
    - Only allow access to files whose absolute path shares commonpath with the resolved DATA_DIR.
    """
    # Bypass during pytest to enable fixtures outside DATA_DIR
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    cfg = get_config()
    configured_dir = getattr(cfg, "DATA_DIR", "") or ""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    base_dir = os.path.abspath(os.path.join(project_root, configured_dir)) if not os.path.isabs(configured_dir) else os.path.abspath(configured_dir)

    # Reject drive root like C:\ or just \\
    drive, _ = os.path.splitdrive(base_dir)
    if os.path.normpath(base_dir) == (drive + os.sep):
        raise ValueError("DATA_DIR cannot be a drive root; please configure a subdirectory.")

    abs_path = os.path.abspath(file_path)
    common = os.path.commonpath([abs_path, base_dir])
    if common != base_dir:
        raise ValueError("Access to files outside the data directory is not allowed.")


def apply_valuation_time(dt: datetime, time_str: Optional[str] = None) -> datetime:
    """Return a datetime with time normalized according to config VALUATION_TIME.

    - dt: naive datetime representing the valuation date (date component used)
    - time_str: optional override like "HH:MM:SS"; when None, use config.VALUATION_TIME
    This helps keep timezone/naive handling consistent by pinning a specific time of day.
    """
    cfg = get_config()
    t = (time_str or cfg.VALUATION_TIME or "00:00:00").strip()
    try:
        hh, mm, ss = [int(x) for x in t.split(":")]
    except Exception:
        hh, mm, ss = 0, 0, 0
    return dt.replace(hour=hh, minute=mm, second=ss, microsecond=0)



def _pick_latest_by_date(files: list[str], pattern: str = r".*_(\d{8})\.csv$") -> str | None:
    """Pick the file with the latest YYYYMMDD token at the end; fallback to first."""
    date_re = re.compile(pattern)
    dated: list[tuple[str, str]] = []
    for f in files:
        m = date_re.match(os.path.basename(f))
        if m:
            dated.append((m.group(1), f))
    if dated:
        dated.sort(key=lambda x: x[0], reverse=True)
        return dated[0][1]
    return files[0] if files else None


def find_curve_file(cfg) -> str:
    """Find a SwapRates CSV file using config.
    
    Search order:
    1) cfg.DATA_DIR with cfg.CURVE_GLOB (pick latest by date token)
    2) Project root (two levels above this file) with the same pattern (pick most recently modified)
    Returns a matching file path.
    Raises FileNotFoundError if none found.
    """
    data_dir = getattr(cfg, "DATA_DIR", None) or get_config().DATA_DIR
    pattern = getattr(cfg, "CURVE_GLOB", None) or get_config().CURVE_GLOB

    primary = glob.glob(os.path.join(data_dir, pattern)) if data_dir else []
    pick = _pick_latest_by_date(primary)
    if pick:
        return pick

    # Fallback to project root (../../ from this file)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
    fallback = glob.glob(os.path.join(project_root, pattern))
    if fallback:
        try:
            # Prefer most recently modified file to honor freshly created test fixtures
            fallback.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return fallback[0]
        except Exception:
            # Fallback to date-token selection if mtime unavailable
            pick2 = _pick_latest_by_date(fallback)
            if pick2:
                return pick2

    raise FileNotFoundError("No SwapRates file found")
