from __future__ import annotations
import os
import time
from pathlib import Path
import pandas as pd

from gemini_ird_pricer.services import build_services, get_cache_metrics
from gemini_ird_pricer.config import BaseConfig


def _write_curve_csv(path: Path, n: int = 5):
    df = pd.DataFrame({
        "Maturity (Years)": [i + 1 for i in range(n)],
        "Rate": [1.0 + 0.1 * i for i in range(n)],  # percent
    })
    df.to_csv(path, index=False)


def test_cache_miss_hit_ttl_and_eviction(tmp_path):
    # Create three files to exercise eviction with maxsize=2
    f1 = tmp_path / "SwapRates_20990101.csv"
    f2 = tmp_path / "SwapRates_20990102.csv"
    f3 = tmp_path / "SwapRates_20990103.csv"
    for f in (f1, f2, f3):
        _write_curve_csv(f, 4)

    cfg = BaseConfig()
    cfg.CURVE_CACHE_MAXSIZE = 2
    cfg.CURVE_CACHE_TTL_SECONDS = 1  # short TTL
    svc = build_services(cfg)

    base = get_cache_metrics().copy()

    # First loads for f1 and f2 -> two misses
    df1 = svc.load_curve(str(f1))
    df2 = svc.load_curve(str(f2))
    m1 = get_cache_metrics().copy()

    assert m1["misses"] >= base["misses"] + 2
    # Hits should still be unchanged
    assert m1["hits"] >= base["hits"]

    # Load f1 again -> should be a hit
    df1b = svc.load_curve(str(f1))
    m2 = get_cache_metrics().copy()
    assert m2["hits"] >= m1["hits"] + 1
    assert id(df1b) == id(df1)

    # Load f3 -> causes eviction of least-recently-used (f2)
    svc.load_curve(str(f3))
    m3 = get_cache_metrics().copy()
    assert m3["evictions"] >= m2["evictions"] + 1

    # Wait for TTL to expire, then load f1 -> should be a miss (refresh)
    time.sleep(cfg.CURVE_CACHE_TTL_SECONDS + 0.1)
    df1c = svc.load_curve(str(f1))
    m4 = get_cache_metrics().copy()
    assert m4["misses"] >= m3["misses"] + 1
    # Refreshed object should be a new instance
    assert id(df1c) != id(df1)


def test_cache_disabled_toggle(tmp_path):
    f = tmp_path / "SwapRates_20991231.csv"
    _write_curve_csv(f, 6)

    cfg = BaseConfig()
    cfg.CURVE_CACHE_ENABLED = False
    cfg.CURVE_CACHE_MAXSIZE = 2
    cfg.CURVE_CACHE_TTL_SECONDS = 10
    svc = build_services(cfg)

    base = get_cache_metrics().copy()
    dfa = svc.load_curve(str(f))
    dfb = svc.load_curve(str(f))
    after = get_cache_metrics().copy()

    # When cache disabled, we expect no cache hit increments
    assert after["hits"] == base["hits"]
    # And we do not increment misses/evictions either (cache bypassed entirely)
    assert after["misses"] == base["misses"]
    assert after["evictions"] == base["evictions"]
    # Each call should produce a distinct object instance
    assert id(dfa) != id(dfb)
