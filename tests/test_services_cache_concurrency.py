import os
import threading
import time
from pathlib import Path
import pandas as pd

from gemini_ird_pricer.services import build_services
from gemini_ird_pricer.config import BaseConfig
from gemini_ird_pricer.parsing import load_yield_curve


def _write_curve_csv(path: Path, n: int = 5):
    df = pd.DataFrame({
        "Maturity (Years)": [i + 1 for i in range(n)],
        "Rate": [1.0 + 0.1 * i for i in range(n)],  # percent
    })
    df.to_csv(path, index=False)


def test_cached_load_curve_concurrent_access(tmp_path):
    # Prepare a temporary curve file
    f = tmp_path / "SwapRates_20990101.csv"
    _write_curve_csv(f, 8)

    # Build services with small TTL to exercise refresh logic
    cfg = BaseConfig()
    cfg.CURVE_CACHE_MAXSIZE = 2
    cfg.CURVE_CACHE_TTL_SECONDS = 2
    svc = build_services(cfg)

    # Warm the cache and capture the object id
    df0 = svc.load_curve(str(f))
    assert len(df0) == 8

    # Concurrent readers should not error and should get the same object while valid
    results = []
    errors = []

    def worker():
        try:
            df = svc.load_curve(str(f))
            results.append(id(df))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors occurred: {errors}"
    # Expect all object ids to match the cached df0 id
    assert all(x == id(df0) for x in results)

    # Touch the file mtime to trigger invalidation
    time.sleep(1.1)
    os.utime(str(f), None)

    df1 = svc.load_curve(str(f))
    assert len(df1) == 8
    # After mtime change, may be a new object (cache refresh)
    assert id(df1) != id(df0)

    # Wait for TTL expiry and ensure refresh again yields a new object
    time.sleep(cfg.CURVE_CACHE_TTL_SECONDS + 0.2)
    df2 = svc.load_curve(str(f))
    assert id(df2) != id(df1)
