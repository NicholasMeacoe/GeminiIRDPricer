from __future__ import annotations
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from typing import Mapping, Any
from .utils import year_fraction, build_discount_function, apply_valuation_time

# Default configuration used when no explicit mapping is provided (keeps domain pure)
_DEFAULT_CFG: dict[str, Any] = {
    "FIXED_FREQUENCY": 2,
    "DAY_COUNT": "ACT/365F",
    "DISCOUNTING_STRATEGY": "exp_cont",
    "EXTRAPOLATION_POLICY": "clamp",
    "INTERP_STRATEGY": "linear_zero",
}


def generate_payment_schedule(start_date: datetime, maturity_date: datetime, frequency: int) -> list[datetime]:
    """Generate a payment schedule with guards and optional month-based stepping.

    - Returns a list of payment dates strictly greater than start_date and up to maturity_date.
    - Uses month-based stepping when 12 is divisible by frequency (e.g., 1, 2, 3, 4, 6, 12),
      otherwise falls back to day-based steps (365/frequency).
    - Guards against infinite loops and handles maturity <= start by returning an empty list.
    """
    if maturity_date <= start_date:
        return []

    schedule: list[datetime] = []
    current_date = start_date

    def _add_months(dt: datetime, n: int) -> datetime:
        # Minimal month adder: increases month while clamping day to last valid day
        y = dt.year + (dt.month - 1 + n) // 12
        m = (dt.month - 1 + n) % 12 + 1
        # Clamp day to 28-31 depending on month
        from calendar import monthrange
        last_day = monthrange(y, m)[1]
        d = min(dt.day, last_day)
        return dt.replace(year=y, month=m, day=d)

    use_months = frequency > 0 and (12 % max(1, frequency) == 0)
    step_months = int(12 / max(1, frequency)) if use_months else None
    step_days = int(365.0 / max(1, frequency))

    max_iters = 10000
    iters = 0
    while current_date < maturity_date and iters < max_iters:
        if use_months and step_months:
            current_date = _add_months(current_date, step_months)
        else:
            current_date = current_date + timedelta(days=step_days)
        if current_date > maturity_date:
            current_date = maturity_date
        if current_date > start_date:
            schedule.append(current_date)
        iters += 1
    return schedule


def _interp_market_rate(target_days: int, dates: np.ndarray, rates: np.ndarray, policy: str, strategy: str, disc_func) -> float:
    """Interpolate a market rate according to strategy and extrapolation policy.

    - strategy: 'linear_zero' | 'log_linear_df'
    - policy: 'clamp' | 'error'
    disc_func: discount function D(r, t) used to compute discount factors
    """
    days = int(target_days)
    dmin = int(dates.min())
    dmax = int(dates.max())
    if days < dmin:
        if policy == "error":
            raise ValueError("Maturity before curve start; extrapolation forbidden")
        days = dmin
    if days > dmax:
        if policy == "error":
            raise ValueError("Maturity beyond curve end; extrapolation forbidden")
        days = dmax

    if strategy == "log_linear_df":
        # Interpolate ln(DF) over year time to reduce arbitrage-like bumps
        t_nodes = dates.astype(float) / 365.0
        # Convert node rates to discount factors using provided discount function
        # Avoid t=0 by replacing with a small epsilon
        eps = 1e-9
        dfs = np.array([disc_func(r, max(t, eps)) for r, t in zip(rates, t_nodes)], dtype=float)
        ln_dfs = np.log(dfs)
        t = max(days / 365.0, eps)
        ln_df_t = float(np.interp(t, t_nodes, ln_dfs))
        df_t = float(np.exp(ln_df_t))
        # Convert back to equivalent continuously-compounded rate
        r_t = -np.log(max(df_t, eps)) / t
        return float(r_t)

    # Default: linear interpolation on zero/market rates vs days
    return float(np.interp(days, dates, rates))


def price_swap(notional: float, fixed_rate: float, maturity_date: datetime, yield_curve: pd.DataFrame, config: Mapping[str, Any] | None = None, valuation_date: datetime | None = None) -> tuple[float, list[dict]]:
    """Price a plain-vanilla fixed-for-floating swap and return (NPV, schedule).

    - notional: positive notional amount
    - fixed_rate: fixed leg annualized rate (decimal)
    - maturity_date: final payment date
    - yield_curve: DataFrame indexed by datetime with a 'Rate' column (zero/market rates)
    - config: optional mapping overriding config values
    - valuation_date: optional override; if None uses first curve date or today
    """
    valuation_date = valuation_date or (yield_curve.index[0] if len(yield_curve.index) else datetime.today())
    valuation_date = apply_valuation_time(valuation_date)
    cfg_map = {**_DEFAULT_CFG, **(dict(config) if config is not None else {})}
    freq = int(cfg_map.get("FIXED_FREQUENCY", 2))
    dc = str(cfg_map.get("DAY_COUNT", "ACT/365F"))
    disc = build_discount_function(str(cfg_map.get("DISCOUNTING_STRATEGY", "exp_cont")))
    payment_dates = generate_payment_schedule(valuation_date, maturity_date, freq)

    schedule: list[dict] = []
    dates = np.array([(d - valuation_date).days for d in yield_curve.index])
    rates = yield_curve["Rate"].values

    policy = str(cfg_map.get("EXTRAPOLATION_POLICY", "clamp"))
    interp = str(cfg_map.get("INTERP_STRATEGY", "linear_zero"))

    total_pv_fixed = 0.0
    total_pv_floating = 0.0
    prev_date = valuation_date

    for payment_date in payment_dates:
        t = year_fraction(valuation_date, payment_date, dc)
        if t <= 0:
            prev_date = payment_date
            continue

        maturity_days = (payment_date - valuation_date).days
        market_rate = _interp_market_rate(maturity_days, dates, rates, policy, interp, disc)
        discount_factor = float(disc(market_rate, t))

        accrual = max(year_fraction(prev_date, payment_date, dc), 0.0)
        fixed_payment = notional * fixed_rate * accrual
        pv_fixed = fixed_payment * discount_factor
        total_pv_fixed += pv_fixed

        floating_payment = notional * market_rate * accrual
        pv_floating = floating_payment * discount_factor
        total_pv_floating += pv_floating

        schedule.append(
            {
                "payment_date": payment_date.strftime("%Y-%m-%d"),
                "days": maturity_days,
                "fixed_payment": fixed_payment,
                "floating_payment": floating_payment,
                "discount_factor": discount_factor,
                "pv_fixed": pv_fixed,
                "pv_floating": pv_floating,
            }
        )

        prev_date = payment_date

    swap_value = total_pv_floating - total_pv_fixed
    return swap_value, schedule


def solve_par_rate(notional: float, maturity_date: datetime, yield_curve: pd.DataFrame, config: Mapping[str, Any] | None = None, valuation_date: datetime | None = None) -> float:
    """Solve the par fixed rate that makes the swap NPV zero for given inputs."""
    valuation_date = valuation_date or (yield_curve.index[0] if len(yield_curve.index) else datetime.today())
    valuation_date = apply_valuation_time(valuation_date)
    cfg_map = {**_DEFAULT_CFG, **(dict(config) if config is not None else {})}
    freq = int(cfg_map.get("FIXED_FREQUENCY", 2))
    dc = str(cfg_map.get("DAY_COUNT", "ACT/365F"))
    disc = build_discount_function(str(cfg_map.get("DISCOUNTING_STRATEGY", "exp_cont")))
    policy = str(cfg_map.get("EXTRAPOLATION_POLICY", "clamp"))
    interp = str(cfg_map.get("INTERP_STRATEGY", "linear_zero"))
    payment_dates = generate_payment_schedule(valuation_date, maturity_date, freq)

    dates = np.array([(d - valuation_date).days for d in yield_curve.index])
    rates = yield_curve["Rate"].values

    pv_annuity = 0.0
    pv_floating_leg = 0.0
    prev_date = valuation_date

    for payment_date in payment_dates:
        t = year_fraction(valuation_date, payment_date, dc)
        if t <= 0:
            prev_date = payment_date
            continue

        maturity_days = (payment_date - valuation_date).days
        market_rate = _interp_market_rate(maturity_days, dates, rates, policy, interp, disc)
        discount_factor = float(disc(market_rate, t))

        accrual = max(year_fraction(prev_date, payment_date, dc), 0.0)
        pv_annuity += accrual * discount_factor
        pv_floating_leg += notional * market_rate * accrual * discount_factor
        prev_date = payment_date

    if pv_annuity == 0:
        return 0.0

    return float(pv_floating_leg / (notional * pv_annuity))
