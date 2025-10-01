"""Configuration validation and runtime checks."""
from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Any, Dict, List
from .config import Config
from .error_handler import ConfigurationError


logger = logging.getLogger(__name__)


def validate_config(config: Config) -> None:
    """Validate configuration at startup."""
    errors: List[str] = []
    
    # Validate data directory
    if not os.path.exists(config.DATA_DIR):
        errors.append(f"DATA_DIR does not exist: {config.DATA_DIR}")
    elif not os.path.isdir(config.DATA_DIR):
        errors.append(f"DATA_DIR is not a directory: {config.DATA_DIR}")
    
    # Validate financial parameters
    if config.NOTIONAL_MAX <= 0:
        errors.append("NOTIONAL_MAX must be positive")
    
    if config.MATURITY_MAX_YEARS <= 0:
        errors.append("MATURITY_MAX_YEARS must be positive")
    
    if config.CURVE_MAX_POINTS <= 0:
        errors.append("CURVE_MAX_POINTS must be positive")
    
    # Validate cache settings
    if config.CURVE_CACHE_MAXSIZE <= 0:
        errors.append("CURVE_CACHE_MAXSIZE must be positive")
    
    if config.CURVE_CACHE_TTL_SECONDS <= 0:
        errors.append("CURVE_CACHE_TTL_SECONDS must be positive")
    
    # Validate authentication in production
    if config.ENV.lower().startswith("prod") and config.ENABLE_AUTH:
        user_env = config.AUTH_USER_ENV
        pass_env = config.AUTH_PASS_ENV
        
        if not os.getenv(user_env):
            errors.append(f"Production auth enabled but {user_env} not set")
        
        if not os.getenv(pass_env):
            errors.append(f"Production auth enabled but {pass_env} not set")
    
    # Validate rate limiting
    if config.ENABLE_RATE_LIMIT:
        if config.RATE_LIMIT_PER_MIN <= 0:
            errors.append("RATE_LIMIT_PER_MIN must be positive")
        
        if config.RATE_LIMIT_WINDOW_SECONDS <= 0:
            errors.append("RATE_LIMIT_WINDOW_SECONDS must be positive")
    
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
    
    logger.info("Configuration validation passed")


def validate_runtime_dependencies() -> None:
    """Validate runtime dependencies are available."""
    try:
        import pandas
        import numpy
        import plotly
        import pydantic
        import flask
    except ImportError as e:
        raise ConfigurationError(f"Missing required dependency: {e}")
    
    logger.info("Runtime dependencies validated")


def check_curve_files(data_dir: str, curve_glob: str) -> bool:
    """Check if curve files are available."""
    try:
        from glob import glob
        pattern = os.path.join(data_dir, curve_glob)
        files = glob(pattern)
        return len(files) > 0
    except Exception as e:
        logger.warning(f"Error checking curve files: {e}")
        return False


def get_system_info() -> Dict[str, Any]:
    """Get system information for diagnostics."""
    import platform
    import sys
    
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "hostname": platform.node(),
    }
