from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Protocol, Any, Mapping
import os
import pandas as pd
import logging

from .config import Config
from . import parsing as parsing_mod
from . import pricer as pricer_mod
from .utils import ensure_in_data_dir
from .performance import performance_monitor, performance_tracker
from .error_handler import ConfigurationError

# Simple file-based cache for parsed yield curves to avoid recomputation
from collections import OrderedDict
import time
from threading import Lock

logger = logging.getLogger(__name__)

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
    """Get cache performance metrics."""
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "evictions": _cache_evictions,
    }


def get_cache_policy() -> dict[str, float | int]:
    """Return current cache policy and size for observability."""
    with _cache_lock:
        size = len(_curve_cache)
    return {
        "size": int(size),
        "maxsize": int(_CACHE_MAXSIZE),
        "ttl_seconds": float(_CACHE_TTL_SECONDS),
    }


class CurveProvider(Protocol):
    def __call__(self, file_path: str, form_data: Any | None = None) -> pd.DataFrame: ...


@performance_monitor("load_curve_cached", log_threshold_ms=50.0)
def _cached_load_curve(file_path: str, form_data: Any | None = None) -> pd.DataFrame:
    """Load curve with caching and performance monitoring."""
    # If form-provided curve data, bypass cache since inputs aren't part of the key
    if form_data is not None or not _CACHE_ENABLED:
        # Still enforce path safety even when bypassing cache
        abs_path = os.path.abspath(file_path)
        try:
            ensure_in_data_dir(abs_path)
        except Exception as e:
            logger.error(f"Path validation failed: {e}")
            raise ConfigurationError(f"Invalid file path: {e}")
        
        return parsing_mod.load_yield_curve(file_path, form_data)

    abs_path = os.path.abspath(file_path)
    
    # Enforce path traversal guard prior to any filesystem stat
    try:
        ensure_in_data_dir(abs_path)
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        raise ConfigurationError(f"Invalid file path: {e}")
    
    try:
        mtime = os.path.getmtime(abs_path)
    except FileNotFoundError:
        logger.warning(f"Curve file not found: {abs_path}")
        # Delegate to parser to raise a proper error
        return parsing_mod.load_yield_curve(file_path, form_data)
    except OSError as e:
        logger.error(f"Error accessing file {abs_path}: {e}")
        raise ConfigurationError(f"Cannot access curve file: {e}")

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
                logger.debug(f"Cache hit for {abs_path}")
                return df
            else:
                # Invalidate stale entry if present
                try:
                    del _curve_cache[abs_path]
                    logger.debug(f"Invalidated stale cache entry for {abs_path}")
                except KeyError:
                    pass
        
        # Count miss under lock before releasing for IO
        global _cache_misses
        _cache_misses += 1
        logger.debug(f"Cache miss for {abs_path}")

    # Cache miss: load fresh outside of lock
    start_time = time.time()
    try:
        df = parsing_mod.load_yield_curve(file_path, form_data)
        load_time = (time.time() - start_time) * 1000
        performance_tracker.record("curve_load", load_time)
        
        with _cache_lock:
            # Evict least-recently-used if over capacity after insert
            _curve_cache[abs_path] = (mtime, df, now)
            while len(_curve_cache) > _CACHE_MAXSIZE:
                evicted_path, _ = _curve_cache.popitem(last=False)
                global _cache_evictions
                _cache_evictions += 1
                logger.debug(f"Evicted cache entry for {evicted_path}")
        
        return df
    except Exception as e:
        logger.error(f"Failed to load curve from {file_path}: {e}")
        raise


@dataclass
class Services:
    """Simple dependency container with enhanced error handling."""
    config: Config
    load_curve: CurveProvider
    price_swap: Callable[[float, float, Any, pd.DataFrame, Mapping[str, Any] | None], tuple[float, list[dict]]]
    solve_par_rate: Callable[[float, Any, pd.DataFrame], float]


def build_services(config: Config) -> Services:
    """Build the default Services container with validation."""
    # Validate configuration
    try:
        from .config_validator import validate_config
        validate_config(config)
    except ImportError:
        logger.warning("Config validator not available, skipping validation")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ConfigurationError(f"Invalid configuration: {e}")
    
    # Apply cache policy from config with validation
    global _CACHE_MAXSIZE, _CACHE_TTL_SECONDS, _CACHE_ENABLED
    
    try:
        _CACHE_MAXSIZE = max(1, int(getattr(config, "CURVE_CACHE_MAXSIZE", 4)))
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid CURVE_CACHE_MAXSIZE: {e}, using default 4")
        _CACHE_MAXSIZE = 4
    
    try:
        _CACHE_TTL_SECONDS = max(1.0, float(getattr(config, "CURVE_CACHE_TTL_SECONDS", 300)))
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid CURVE_CACHE_TTL_SECONDS: {e}, using default 300")
        _CACHE_TTL_SECONDS = 300.0
    
    try:
        _CACHE_ENABLED = bool(getattr(config, "CURVE_CACHE_ENABLED", True))
    except Exception as e:
        logger.warning(f"Invalid CURVE_CACHE_ENABLED: {e}, using default True")
        _CACHE_ENABLED = True

    logger.info(f"Cache configured: maxsize={_CACHE_MAXSIZE}, ttl={_CACHE_TTL_SECONDS}s, enabled={_CACHE_ENABLED}")

    # Wrap module functions to inject config mapping explicitly
    @performance_monitor("price_swap", log_threshold_ms=200.0)
    def _price_swap(notional: float, fixed_rate: float, maturity_date, yield_curve: pd.DataFrame, cfg_override: Mapping[str, Any] | None = None):
        try:
            cfg_map = cfg_override if cfg_override is not None else config.model_dump()
            return pricer_mod.price_swap(notional, fixed_rate, maturity_date, yield_curve, cfg_map)
        except Exception as e:
            logger.error(f"Swap pricing failed: {e}")
            raise

    @performance_monitor("solve_par_rate", log_threshold_ms=100.0)
    def _solve_par_rate(notional: float, maturity_date, yield_curve: pd.DataFrame):
        try:
            return pricer_mod.solve_par_rate(notional, maturity_date, yield_curve, config.model_dump())
        except Exception as e:
            logger.error(f"Par rate solving failed: {e}")
            raise

    return Services(
        config=config,
        load_curve=_cached_load_curve,
        price_swap=_price_swap,
        solve_par_rate=_solve_par_rate,
    )
