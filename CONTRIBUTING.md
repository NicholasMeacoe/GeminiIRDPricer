# Contributing

Thank you for your interest in contributing to Gemini IRD Pricer!

## Development setup
- Create and activate a virtual environment
- Install dependencies: `pip install -r requirements.txt -r requirements-dev.txt`
- Run the app: `python app.py`

## Code style
- Use Black for formatting and Ruff for linting.
- Keep type hints up to date; run `mypy` locally.

## Tests
- Add tests under `tests/` using `pytest`.

## Pull Requests
- Describe the change and rationale.
- Include screenshots for UI changes when relevant.
- Ensure CI checks pass (lint, mypy, tests).

# Contributing

Thank you for your interest in contributing to Gemini IRD Pricer!

## Development setup
- Create and activate a virtual environment
- Install dependencies: `pip install -r requirements.txt -r requirements-dev.txt`
- Run the app: `python app.py`

## Code style
- Use Black for formatting and Ruff for linting.
- Keep type hints up to date; run `mypy` locally.

## Tests
- Add tests under `tests/` using `pytest`.

## Pull Requests
- Describe the change and rationale.
- Include screenshots for UI changes when relevant.
- Ensure CI checks pass (lint, mypy, tests).

## Pre-commit hooks
We use pre-commit to enforce formatting, linting, and typing locally before code lands on main.

1) Install once per machine:
   - `pip install pre-commit`
   - `pre-commit install`  (installs git hooks)

2) Run on demand:
   - `pre-commit run --all-files`

Hooks configured:
- Black (formatting)
- isort (import sorting)
- Ruff (lint + format)
- mypy (type checking)

If hooks fail, fix the reported issues and re-run. You can skip hooks with `--no-verify` in emergencies, but CI will still enforce them.
