# Pricing Assumptions and Conventions

Last updated: 2025-09-25 20:15

This project implements a simple, transparent set of conventions for demonstration and testing. Where applicable, these are configurable.

Day Count Conventions
- Supported: ACT/365F (default), ACT/365, ACT/365.25, ACT/360, 30/360 (US simplified), ACT/ACT (approx), ACT/365L
- Notes: ACT/365F and ACT/365 both use a 365-day denominator in this simplified implementation; ACT/ACT is an approximation that prorates by each calendar year's day count; ACT/365L uses 366 if the period includes Feb 29.
- Configuration: config.DAY_COUNT

Compounding / Discounting
- Strategies:
  - exp_cont: D = exp(-r * t) (default)
  - simple: D = 1 / (1 + r * t)
  - comp_n: D = 1 / (1 + r/n)^(n * t), e.g., comp_1 (annual), comp_2 (semi-annual), comp_4 (quarterly)
- Configuration: config.DISCOUNTING_STRATEGY

Interpolation
- Current approach: linear interpolation on rates vs maturity in days
- Extrapolation policy: clamp beyond curve endpoints by default (config.EXTRAPOLATION_POLICY = clamp | error)

Payment Schedule
- Frequency: configurable fixed leg frequency (config.FIXED_FREQUENCY), default 2
- Schedule generation: month-based stepping when 12 is divisible by frequency (e.g., 1,2,3,4,6,12); otherwise day-based steps of approximately 365/frequency. Calendars and business day adjustments are not modeled in this simplified engine.

Floating Leg
- The floating leg amount per period uses the interpolated market rate at each payment date with accrual computed as year_fraction between consecutive schedule dates. This is a simple forward estimation rather than a full bootstrapped forward curve.

Valuation Date/Time and Timezones
- The engine uses naive datetimes. A specific time-of-day is applied via config.VALUATION_TIME (default "00:00:00") to ensure consistency across computations.

Limitations
- No holidays/business day conventions
- No multi-curve framework or index-specific forward projection
- Linear interpolation only; no cubic splines or monotone convex
- Simplified accrual and schedule generation

These constraints are deliberate to keep the implementation compact and easy to reason about; they can be extended as needed.
