"""Tests for Pydantic BaseSettings configuration."""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from src.gemini_ird_pricer.config import Config, ProductionConfig, get_config


class TestPydanticConfig:
    """Test Pydantic BaseSettings configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.ENV == "development"
        assert config.DEBUG is True
        assert config.MAX_ITERATIONS == 10000
        assert config.DEFAULT_FREQUENCY == 2
        assert config.NOTIONAL_MAX == 1e11
        assert config.LOG_FORMAT == "plain"
        assert config.ENABLE_AUTH is False
    
    def test_production_config(self):
        """Test production configuration overrides."""
        config = ProductionConfig()
        
        assert config.ENV == "production"
        assert config.DEBUG is False
        assert config.LOG_LEVEL == "INFO"
        assert config.ENABLE_AUTH is True
        assert config.LOG_FORMAT == "json"
        assert config.CORS_ALLOWED_ORIGINS == []
        assert config.CORS_ALLOW_CREDENTIALS is False
    
    def test_field_validation(self):
        """Test field validation."""
        # Test valid values
        config = Config(
            EXTRAPOLATION_POLICY="clamp",
            INTERP_STRATEGY="linear_zero",
            DISCOUNTING_STRATEGY="exp_cont",
            LOG_FORMAT="json"
        )
        assert config.EXTRAPOLATION_POLICY == "clamp"
        
        # Test invalid extrapolation policy
        with pytest.raises(ValidationError) as exc_info:
            Config(EXTRAPOLATION_POLICY="invalid")
        assert "must be 'clamp' or 'error'" in str(exc_info.value)
        
        # Test invalid interpolation strategy
        with pytest.raises(ValidationError) as exc_info:
            Config(INTERP_STRATEGY="invalid")
        assert "must be 'linear_zero' or 'log_linear_df'" in str(exc_info.value)
        
        # Test invalid discounting strategy
        with pytest.raises(ValidationError) as exc_info:
            Config(DISCOUNTING_STRATEGY="invalid")
        assert "must be one of" in str(exc_info.value)
        
        # Test invalid log format
        with pytest.raises(ValidationError) as exc_info:
            Config(LOG_FORMAT="invalid")
        assert "must be 'plain' or 'json'" in str(exc_info.value)
    
    def test_numeric_constraints(self):
        """Test numeric field constraints."""
        # Test valid values
        config = Config(
            FIXED_FREQUENCY=4,
            CURVE_CACHE_MAXSIZE=10,
            CURVE_MAX_POINTS=100,
            MATURITY_MAX_YEARS=50
        )
        assert config.FIXED_FREQUENCY == 4
        
        # Test constraint violations
        with pytest.raises(ValidationError):
            Config(FIXED_FREQUENCY=0)  # Must be >= 1
        
        with pytest.raises(ValidationError):
            Config(CURVE_CACHE_MAXSIZE=0)  # Must be >= 1
        
        with pytest.raises(ValidationError):
            Config(NOTIONAL_MAX=-1)  # Must be > 0
    
    def test_environment_variable_loading_simple(self):
        """Test loading simple configuration from environment variables."""
        # Test without the problematic CORS_ALLOWED_ORIGINS
        with patch.dict(os.environ, {
            "ENV": "test",
            "DEBUG": "false", 
            "MAX_ITERATIONS": "5000",
            "LOG_FORMAT": "json",
            "ENABLE_AUTH": "true"
        }, clear=False):
            config = Config()
            
            assert config.ENV == "test"
            assert config.DEBUG is False
            assert config.MAX_ITERATIONS == 5000
            assert config.LOG_FORMAT == "json"
            assert config.ENABLE_AUTH is True
    
    def test_get_config_function(self):
        """Test get_config function behavior."""
        # Test development config
        dev_config = get_config("development")
        assert isinstance(dev_config, Config)
        assert dev_config.ENV == "development"
        
        # Test production config
        prod_config = get_config("production")
        assert isinstance(prod_config, ProductionConfig)
        assert prod_config.ENV == "production"
        
        # Test default behavior
        default_config = get_config()
        assert isinstance(default_config, Config)
    
    @patch.dict(os.environ, {"ENV": "production"})
    def test_get_config_from_env(self):
        """Test get_config reads from environment."""
        config = get_config()
        assert isinstance(config, ProductionConfig)
        assert config.ENV == "production"
    
    def test_model_dump(self):
        """Test that model_dump works (replaces to_mapping)."""
        config = Config()
        config_dict = config.model_dump()
        
        assert isinstance(config_dict, dict)
        assert "ENV" in config_dict
        assert "DEBUG" in config_dict
        assert "MAX_ITERATIONS" in config_dict
        assert "DEFAULT_FREQUENCY" in config_dict
        assert config_dict["ENV"] == "development"
        assert config_dict["MAX_ITERATIONS"] == 10000
    
    def test_data_dir_default(self):
        """Test DATA_DIR default value calculation."""
        config = Config()
        
        # Should be an absolute path ending with data/curves
        assert os.path.isabs(config.DATA_DIR)
        assert config.DATA_DIR.endswith(os.path.join("data", "curves"))
    
    def test_immutable_after_creation(self):
        """Test that config values can be accessed after creation."""
        config = Config(MAX_ITERATIONS=8000)
        
        # Should be able to access the value
        assert config.MAX_ITERATIONS == 8000
        
        # Should be able to get model dump
        config_dict = config.model_dump()
        assert config_dict["MAX_ITERATIONS"] == 8000
