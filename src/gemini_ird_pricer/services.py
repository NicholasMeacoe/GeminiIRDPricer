from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Protocol, Any, Mapping
import os
import pandas as pd

from .config import Config
from . import parsing as parsing_mod
from . import pricer as pricer_mod
from .utils import ensure_in_data_dir

# Simple file-based cache for parsed yield curves to avoid recomputation (#42)
# Keyed by absolute file path; invalidated when file mtime changes.
from collections import OrderedDict
import time
from threading import Lock

_curve_cache: "OrderedDict[str, tuple[float, pd.DataFrame, float]]" = OrderedDict()
_cache_lock: Lock = Lock()
# Cache policy (overridden by build_services via config)
_CACHE_MAXSIZE: int = 4
_CACHE_TTL_SECONDS: float = 300.0
# Optional cache enable switch (overridden by build_services via config)
_CACHE_ENABLED: bool = True

# Cache observability counters (module-level; scraped by Flask metrics endpoint)
_cache_hits: int = 0
_cache_misses: int = 0
_cache_evictions: int = 0


def get_cache_metrics() -> dict[str, int]:
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "evictions": _cache_evictions,
    }


def get_cache_policy() -> dict[str, float | int]:
    """Return current cache policy and size for observability.

    Keys:
    - size: current number of entries in cache
    - maxsize: configured maximum size
    - ttl_seconds: configured TTL in seconds
    """
    with _cache_lock:
        size = len(_curve_cache)
    return {
        "size": int(size),
        "maxsize": int(_CACHE_MAXSIZE),
        "ttl_seconds": float(_CACHE_TTL_SECONDS),
    }


class CurveProvider(Protocol):
    def __call__(self, file_path: str, form_data: Any | None = None) -> pd.DataFrame: ...


def _cached_load_curve(file_path: str, form_data: Any | None = None) -> pd.DataFrame:
    # If form-provided curve data, bypass cache since inputs aren't part of the key
    if form_data is not None or not _CACHE_ENABLED:
        # Still enforce path safety even when bypassing cache
        abs_path = os.path.abspath(file_path)
        ensure_in_data_dir(abs_path)
        return parsing_mod.load_yield_curve(file_path, form_data)

    abs_path = os.path.abspath(file_path)
    # Enforce path traversal guard prior to any filesystem stat
    ensure_in_data_dir(abs_path)
    try:
        mtime = os.path.getmtime(abs_path)
    except FileNotFoundError:
        # Delegate to parser to raise a proper error
        return parsing_mod.load_yield_curve(file_path, form_data)

    now = time.time()
    with _cache_lock:
        entry = _curve_cache.get(abs_path)
        if entry:
            cached_mtime, df, ts = entry
            # Validate staleness by TTL and file mtime match
            if cached_mtime == mtime and (now - ts) <= _CACHE_TTL_SECONDS:
                # Mark as recently used (move to end)
                _curve_cache.move_to_end(abs_path, last=True)
                global _cache_hits
                _cache_hits += 1
                return df
            else:
                # Invalidate stale entry if present
                try:
                    del _curve_cache[abs_path]
                except KeyError:
                    pass
        # Count miss under lock before releasing for IO
        global _cache_misses
        _cache_misses += 1

    # Cache miss: load fresh outside of lock
    df = parsing_mod.load_yield_curve(file_path, form_data)
    with _cache_lock:
        # Evict least-recently-used if over capacity after insert
        _curve_cache[abs_path] = (mtime, df, now)
        while len(_curve_cache) > _CACHE_MAXSIZE:
            _curve_cache.popitem(last=False)
            global _cache_evictions
            _cache_evictions += 1
    return df


@dataclass
class Services:
    """Simple dependency container.

    This wraps the core swappable services used by web layers so they can be
    injected for tests or alternative implementations.
    """
    config: Config
    load_curve: CurveProvider
    price_swap: Callable[[float, float, Any, pd.DataFrame, Mapping[str, Any] | None], tuple[float, list[dict]]]
    solve_par_rate: Callable[[float, Any, pd.DataFrame], float]


def build_services(config: Config) -> Services:
    """Build the default Services container from the current modules."""
    # Apply cache policy from config
    global _CACHE_MAXSIZE, _CACHE_TTL_SECONDS, _CACHE_ENABLED
    try:
        _CACHE_MAXSIZE = int(getattr(config, "CURVE_CACHE_MAXSIZE", 4))
    except Exception:
        _CACHE_MAXSIZE = 4
    try:
        _CACHE_TTL_SECONDS = float(getattr(config, "CURVE_CACHE_TTL_SECONDS", 300))
    except Exception:
        _CACHE_TTL_SECONDS = 300.0
    try:
        _CACHE_ENABLED = bool(getattr(config, "CURVE_CACHE_ENABLED", True))
    except Exception:
        _CACHE_ENABLED = True

    # Wrap module functions to inject config mapping explicitly, keeping
    # public service signatures stable for callers.
    def _price_swap(notional: float, fixed_rate: float, maturity_date, yield_curve: pd.DataFrame, cfg_override: Mapping[str, Any] | None = None):
        cfg_map = cfg_override if cfg_override is not None else config.model_dump()
        return pricer_mod.price_swap(notional, fixed_rate, maturity_date, yield_curve, cfg_map)

    def _solve_par_rate(notional: float, maturity_date, yield_curve: pd.DataFrame):
        return pricer_mod.solve_par_rate(notional, maturity_date, yield_curve, config.model_dump())

    return Services(
        config=config,
        load_curve=_cached_load_curve,
        price_swap=_price_swap,
        solve_par_rate=_solve_par_rate,
    )
