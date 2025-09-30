# Dependency Lock Strategy

Date: 2025-09-28

Purpose
- Provide a simple, reproducible dependency management approach for both runtime and dev tools.

Recommended options (choose one)

Option A: pip-tools (requirements.in -> requirements.txt)
- Install locally: `pip install pip-tools`
- Maintain input files:
  - `requirements.in` for runtime
  - `requirements-dev.in` for dev tools (ruff, mypy, pytest, bandit, pip-audit, etc.)
- Compile locked files:
  - `pip-compile -o requirements.txt requirements.in`
  - `pip-compile -o requirements-dev.txt requirements-dev.in`
- Upgrade intentionally with `--upgrade`.
- CI: install from the compiled `requirements*.txt` files (already configured).

Option B: uv (ultra-fast resolver)
- Install: `pip install uv` (or use the standalone binary)
- Create lock: `uv pip compile requirements.in -o requirements.txt`
- Same flow as pip-tools for dev inputs.

Notes
- Keep runtime dependencies in `requirements.txt` only; dev/test/security tools belong in `requirements-dev.txt` and are not installed in the production image.
- Our CI installs both runtime and dev dependencies to run lint/type/test/security checks.
- The Dockerfile is multi-stage and copies only runtime dependencies into the final image.

Workflow
1) Edit requirements.in / requirements-dev.in (or requirements.txt directly if you prefer pinning manually).
2) Recompile locks (pip-tools or uv).
3) Commit updated lock files.
4) CI will validate the build and run security scans (bandit, pip-audit).
