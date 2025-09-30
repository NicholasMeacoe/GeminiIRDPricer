from __future__ import annotations
import subprocess
import sys
import os


def run_cli(args: list[str]) -> tuple[int, str]:
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "gemini_ird_pricer.cli"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    return proc.returncode, proc.stdout


def test_cli_help():
    code, out = run_cli(["-h"])
    assert code == 0
    assert "gemini-ird-pricer" in out
