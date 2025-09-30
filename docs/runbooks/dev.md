# Development Runbook

This runbook explains how to develop, test, and run the Gemini IRD Pricer locally.

## Prerequisites
- Python 3.11
- Node.js 18 (optional if working on frontend)

## Setup
1. Create a virtual environment and install dependencies:
   - `python -m venv .venv && .venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (macOS/Linux)
   - `pip install -r requirements.txt -r requirements-dev.txt`
   - `pip install pre-commit && pre-commit install`
2. Place a curve CSV under `data/curves/` like `SwapRates_20250815.csv`.

## Running
- Flask UI: `python app.py` then visit http://localhost:5000
- FastAPI API: `python backend/main.py` then visit http://localhost:8000
- CLI: `python -m gemini_ird_pricer.cli --help`

## Testing & Quality
- Run unit tests: `pytest`
- Type check: `mypy`
- Lint/format: `ruff` and `black`, or `pre-commit run --all-files`

## Common Issues
- No curve file found: ensure `data/curves/SwapRates_*.csv` exists or set DATA_DIR via config/env.
- Auth errors: in dev, set `ENABLE_AUTH=false` or provide BASIC_AUTH_USER/PASS.
