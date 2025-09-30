from __future__ import annotations
import os
from gemini_ird_pricer.services import build_services, get_cache_metrics
from gemini_ird_pricer.config import get_config
from gemini_ird_pricer.parsing import load_yield_curve


def _fixture_path(name: str) -> str:
    here = os.path.join(os.path.dirname(__file__), "data")
    return os.path.join(here, name)


def test_cache_metrics_increment_on_hit(tmp_path, monkeypatch):
    # Use a real curve file from tests/data
    src = _fixture_path("SwapRates_20240115.csv")
    # Copy into temp to avoid modifying original
    dst_dir = tmp_path / "curves"
    dst_dir.mkdir()
    dst = dst_dir / "SwapRates_20240115.csv"
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        fdst.write(fsrc.read())

    cfg = get_config()
    svc = build_services(cfg)
    # First load -> miss
    df1 = svc.load_curve(str(dst))
    m1 = get_cache_metrics()
    # Second load -> hit
    df2 = svc.load_curve(str(dst))
    m2 = get_cache_metrics()

    assert m2["hits"] >= m1["hits"] + 1
    assert df1.equals(df2)
