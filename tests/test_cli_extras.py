from __future__ import annotations
import os
import sys
import subprocess


def run_cli(args: list[str], env: dict | None = None) -> tuple[int, str]:
    env_vars = os.environ.copy()
    if env:
        env_vars.update(env)
    cmd = [sys.executable, "-m", "gemini_ird_pricer.cli"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_vars)
    return proc.returncode, proc.stdout


def test_cli_version_flag():
    code, out = run_cli(["--version"]) 
    assert code == 0
    assert out.strip().startswith("0.") or out.strip().isdigit() or len(out.strip()) > 0


essential_keys = [
    "ENV",
    "DATA_DIR",
    "INTERP_STRATEGY",
]


def test_cli_config_flag_prints_json():
    env = {"INTERP_STRATEGY": "log_linear_df"}
    code, out = run_cli(["--config"], env=env)
    assert code == 0
    for key in essential_keys:
        assert key in out
    assert "log_linear_df" in out
