from __future__ import annotations
import os
import sys
import io
import contextlib
from gemini_ird_pricer.cli import main as cli_main


def test_cli_missing_curve_file_returns_nonzero(tmp_path, monkeypatch):
    # Point to empty directory so no curve file found
    data_dir = tmp_path / "empty"
    data_dir.mkdir(parents=True)
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        rc = cli_main(["price", "--data-dir", str(data_dir)])
    assert rc != 0
    assert "Error:" in stderr.getvalue()


def test_cli_bad_maturity_returns_nonzero(tmp_path):
    # Use tests fixture directory; even if a curve exists elsewhere, maturity parse fails
    stderr = io.StringIO()
    from pathlib import Path
    # Pick a directory that likely won't be used due to maturity error
    with contextlib.redirect_stderr(stderr):
        rc = cli_main(["price", "--maturity", "-5y"])  # invalid
    assert rc != 0
    assert "invalid maturity" in stderr.getvalue().lower()
