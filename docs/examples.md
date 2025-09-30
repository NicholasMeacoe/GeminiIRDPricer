# Examples: Pricing a Swap and Solving for Par Rate

This page shows quick, reproducible examples using the core library and the HTTP API.

Last updated: 2025-09-26 17:29

## 1) Python library usage

Prerequisites:
- Install dependencies: `pip install -r requirements.txt`
- Ensure a curve CSV exists under `data/curves/` named like `SwapRates_YYYYMMDD.csv`.

Example script (run with `python -q` or in a REPL):

```python
from datetime import timedelta
from gemini_ird_pricer.parsing import load_yield_curve
from gemini_ird_pricer.pricer import price_swap, solve_par_rate

# Load a test curve
curve_path = "tests/data/SwapRates_20240115.csv"
yc = load_yield_curve(curve_path)

valuation_date = yc.index[0]
maturity_date = valuation_date + timedelta(days=365*5)  # 5 years
notional = 10_000_000

# Solve par rate
par = solve_par_rate(notional, maturity_date, yc)
print(f"Par rate: {par*100:.4f}%")

# Price at par should be ~0
pv, schedule = price_swap(notional, par, maturity_date, yc)
print(f"PV at par: {pv:.2f}")
print(f"Payments: {len(schedule)}")
```

## 2) HTTP API usage

Start the backend (Flask):
- python app.py  # binds to http://localhost:5000 by default

Then:

Solve par rate:
```bash
curl -s -X POST http://localhost:5000/api/solve \
  -H "Content-Type: application/json" \
  -d '{
        "notional": "10m",
        "maturity_date": "5y"
      }'
```

Price a swap (payer side):
```bash
curl -s -X POST http://localhost:5000/api/price \
  -H "Content-Type: application/json" \
  -d '{
        "notional": "10m",
        "fixed_rate": 4.50,
        "maturity_date": "5y"
      }'
```

Override specific curve points (rates in percent):
```bash
curl -s -X POST http://localhost:5000/api/price \
  -H "Content-Type: application/json" \
  -d '{
        "notional": "10m",
        "fixed_rate": 4.50,
        "maturity_date": "5y",
        "curve": [
          {"maturity": 1, "rate": 5.25},
          {"maturity": 5, "rate": 5.10}
        ]
      }'
```

Notes:
- The API returns rates in percent and monetary values rounded according to configuration.
- The server will clamp extrapolation by default; configure behavior via config.
