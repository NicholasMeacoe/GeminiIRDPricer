from __future__ import annotations
from pathlib import Path
import os

from gemini_ird_pricer.utils import find_curve_file


class _Cfg:
    def __init__(self, data_dir: str | None, glob: str = "SwapRates_*.csv") -> None:
        self.DATA_DIR = data_dir
        self.CURVE_GLOB = glob


def test_find_curve_file_picks_latest_by_date(tmp_path):
    # Create multiple files and ensure latest (by YYYYMMDD token) is chosen
    (tmp_path / "SwapRates_20240101.csv").write_text("1,2\n", encoding="utf-8")
    (tmp_path / "SwapRates_20250101.csv").write_text("1,2\n", encoding="utf-8")
    (tmp_path / "SwapRates_20241231.csv").write_text("1,2\n", encoding="utf-8")
    cfg = _Cfg(str(tmp_path))
    picked = find_curve_file(cfg)
    assert Path(picked).name == "SwapRates_20250101.csv"


def test_find_curve_file_fallbacks_to_project_root_when_no_primary_match(tmp_path):
    # Ensure DATA_DIR has no matches
    empty_dir = tmp_path / "primary"
    empty_dir.mkdir()

    # Create a file in the project root to exercise fallback
    project_root = Path(__file__).resolve().parents[1]
    fallback_file = project_root / "SwapRates_20231231.csv"
    try:
        fallback_file.write_text("1,2\n", encoding="utf-8")
        cfg = _Cfg(str(empty_dir))
        picked = find_curve_file(cfg)
        assert Path(picked).resolve() == fallback_file.resolve()
    finally:
        try:
            fallback_file.unlink()
        except FileNotFoundError:
            pass
