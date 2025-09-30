import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Environment
    ENV: str = "development"
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    
    # Data and file paths
    DATA_DIR: str = Field(
        default_factory=lambda: os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "data", "curves")
        ),
        description="Directory containing curve data files"
    )
    CURVE_GLOB: str = Field(default="SwapRates_*.csv", description="Pattern for curve files")
    
    # Financial calculations
    DAY_COUNT: str = Field(default="ACT/365F", description="Day count convention")
    FIXED_FREQUENCY: int = Field(default=2, ge=1, le=365, description="Payment frequency per year")
    DEFAULT_FREQUENCY: int = Field(default=2, ge=1, le=365, description="Default payment frequency")
    
    @field_validator('FIXED_FREQUENCY', 'DEFAULT_FREQUENCY')
    @classmethod
    def validate_frequency(cls, v: int) -> int:
        if v not in [1, 2, 4, 12]:
            raise ValueError(f"Frequency {v} must be 1, 2, 4, or 12 payments per year")
        return v
    
    @field_validator('DAY_COUNT')
    @classmethod
    def validate_day_count(cls, v: str) -> str:
        valid_conventions = ["ACT/365F", "ACT/360", "30/360", "ACT/ACT"]
        if v not in valid_conventions:
            raise ValueError(f"Day count {v} must be one of {valid_conventions}")
        return v
    NUM_PRECISION: int = Field(default=4, ge=0, le=10, description="Numerical precision")
    VALUATION_TIME: str = Field(default="00:00:00", description="Valuation time")
    
    # Interpolation and extrapolation
    EXTRAPOLATION_POLICY: str = Field(default="clamp", description="Extrapolation policy")
    INTERP_STRATEGY: str = Field(default="linear_zero", description="Interpolation strategy")
    DISCOUNTING_STRATEGY: str = Field(default="exp_cont", description="Discounting strategy")
    
    # Caching
    CURVE_CACHE_MAXSIZE: int = Field(default=4, ge=1, le=1024, description="Cache max size")
    CURVE_CACHE_TTL_SECONDS: int = Field(default=300, ge=1, le=86400, description="Cache TTL")
    CURVE_CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    
    # Limits and safety
    CURVE_MAX_POINTS: int = Field(default=200, ge=10, le=10000, description="Max curve points")
    MATURITY_MAX_YEARS: int = Field(default=100, ge=1, le=1000, description="Max maturity years")
    MAX_CONTENT_LENGTH: int = Field(default=1_000_000, ge=1024, le=50_000_000, description="Max request size")
    NOTIONAL_MAX: float = Field(default=1e11, gt=0, description="Max notional amount")
    MAX_ITERATIONS: int = Field(default=10000, ge=100, le=1_000_000, description="Max iterations")
    
    # Authentication
    AUTH_USER_ENV: str = Field(default="API_USER", description="Username env var name")
    AUTH_PASS_ENV: str = Field(default="API_PASS", description="Password env var name")
    ENABLE_AUTH: bool = Field(default=False, description="Enable authentication")
    
    # Security
    SECURITY_HEADERS_ENABLED: bool = Field(default=True, description="Enable security headers")
    CONTENT_SECURITY_POLICY: str = Field(default="", description="Custom CSP header")
    
    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000", 
            "http://localhost:5173",
            "http://127.0.0.1:5173"
        ],
        description="Allowed CORS origins"
    )
    
    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins from environment."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow CORS credentials")
    
    # Logging
    LOG_FORMAT: str = Field(default="plain", description="Log format")
    LOG_LEVEL: str = Field(default="DEBUG", description="Log level")
    REQUEST_ID_HEADER: str = Field(default="X-Request-ID", description="Request ID header name")
    
    # Metrics
    METRICS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    
    # Rate limiting
    ENABLE_RATE_LIMIT: bool = Field(default=False, description="Enable rate limiting")
    RATE_LIMIT_PER_MIN: int = Field(default=60, ge=1, le=100000, description="Rate limit per minute")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, le=3600, description="Rate limit window")
    
    @field_validator("EXTRAPOLATION_POLICY")
    @classmethod
    def validate_extrapolation_policy(cls, v: str) -> str:
        if v not in ["clamp", "error"]:
            raise ValueError("EXTRAPOLATION_POLICY must be 'clamp' or 'error'")
        return v
    
    @field_validator("INTERP_STRATEGY")
    @classmethod
    def validate_interp_strategy(cls, v: str) -> str:
        if v not in ["linear_zero", "log_linear_df"]:
            raise ValueError("INTERP_STRATEGY must be 'linear_zero' or 'log_linear_df'")
        return v
    
    @field_validator("DISCOUNTING_STRATEGY")
    @classmethod
    def validate_discounting_strategy(cls, v: str) -> str:
        valid = ["exp_cont", "simple", "comp_1", "comp_2", "comp_4", "comp_12"]
        if v not in valid:
            raise ValueError(f"DISCOUNTING_STRATEGY must be one of {valid}")
        return v
    
    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        if v not in ["plain", "json"]:
            raise ValueError("LOG_FORMAT must be 'plain' or 'json'")
        return v


class ProductionConfig(Config):
    ENV: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENABLE_AUTH: bool = True
    CORS_ALLOWED_ORIGINS: List[str] = Field(default=[], description="No CORS origins in production by default")
    CORS_ALLOW_CREDENTIALS: bool = False
    LOG_FORMAT: str = "json"


def get_config(env: str | None = None) -> Config:
    """Get configuration based on environment."""
    env_name = env or os.getenv("FLASK_ENV") or os.getenv("ENV") or "development"
    if env_name.lower().startswith("prod"):
        return ProductionConfig()
    return Config()
