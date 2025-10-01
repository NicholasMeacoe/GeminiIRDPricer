"""Enhanced error handling with specific exception types and structured logging."""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from flask import Flask, jsonify, request, g
from pydantic import ValidationError


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class BusinessLogicError(Exception):
    """Raised when business logic constraints are violated."""
    pass


class ErrorHandler:
    """Centralized error handling with structured logging."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.logger = logging.getLogger(__name__)
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize error handlers for Flask app."""
        app.errorhandler(ValidationError)(self.handle_validation_error)
        app.errorhandler(BusinessLogicError)(self.handle_business_error)
        app.errorhandler(ConfigurationError)(self.handle_config_error)
        app.errorhandler(ValueError)(self.handle_value_error)
        app.errorhandler(FileNotFoundError)(self.handle_file_not_found)
        app.errorhandler(Exception)(self.handle_generic_error)
    
    def handle_validation_error(self, error: ValidationError) -> tuple[Any, int]:
        """Handle validation errors with structured response."""
        self.logger.warning(
            "validation_error",
            extra={
                "error_type": "validation_error",
                "error_message": str(error),
                "request_path": getattr(request, 'path', ''),
                "request_id": getattr(g, 'request_id', ''),
            }
        )
        return jsonify({
            "error": {
                "type": "validation_error",
                "message": str(error)
            }
        }), 400
    
    def handle_business_error(self, error: BusinessLogicError) -> tuple[Any, int]:
        """Handle business logic errors."""
        self.logger.warning(
            "business_logic_error",
            extra={
                "error_type": "business_logic_error",
                "error_message": str(error),
                "request_path": getattr(request, 'path', ''),
                "request_id": getattr(g, 'request_id', ''),
            }
        )
        return jsonify({
            "error": {
                "type": "business_logic_error",
                "message": str(error)
            }
        }), 422
    
    def handle_config_error(self, error: ConfigurationError) -> tuple[Any, int]:
        """Handle configuration errors."""
        self.logger.error(
            "configuration_error",
            extra={
                "error_type": "configuration_error",
                "error_message": str(error),
                "request_path": getattr(request, 'path', ''),
                "request_id": getattr(g, 'request_id', ''),
            }
        )
        return jsonify({
            "error": {
                "type": "configuration_error",
                "message": "Service configuration error"
            }
        }), 503
    
    def handle_value_error(self, error: ValueError) -> tuple[Any, int]:
        """Handle value errors from input parsing."""
        self.logger.info(
            "input_error",
            extra={
                "error_type": "input_error",
                "error_message": str(error),
                "request_path": getattr(request, 'path', ''),
                "request_id": getattr(g, 'request_id', ''),
            }
        )
        return jsonify({
            "error": {
                "type": "input_error",
                "message": str(error)
            }
        }), 400
    
    def handle_file_not_found(self, error: FileNotFoundError) -> tuple[Any, int]:
        """Handle file not found errors."""
        self.logger.warning(
            "file_not_found",
            extra={
                "error_type": "not_found",
                "error_message": str(error),
                "request_path": getattr(request, 'path', ''),
                "request_id": getattr(g, 'request_id', ''),
            }
        )
        return jsonify({
            "error": {
                "type": "not_found",
                "message": "Required file not found"
            }
        }), 404
    
    def handle_generic_error(self, error: Exception) -> tuple[Any, int]:
        """Handle unexpected errors with full logging."""
        self.logger.exception(
            "unexpected_error",
            extra={
                "error_type": "server_error",
                "error_class": error.__class__.__name__,
                "error_message": str(error),
                "request_path": getattr(request, 'path', ''),
                "request_id": getattr(g, 'request_id', ''),
            }
        )
        return jsonify({
            "error": {
                "type": "server_error",
                "message": "An unexpected error occurred"
            }
        }), 500


def safe_config_get(config: Dict[str, Any], key: str, default: Any, expected_type: type = str) -> Any:
    """Safely get configuration value with type checking."""
    try:
        value = config.get(key, default)
        if not isinstance(value, expected_type):
            if expected_type in (int, float):
                return expected_type(value)
            return default
        return value
    except (ValueError, TypeError) as e:
        logging.getLogger(__name__).warning(f"Invalid config value for {key}: {e}, using default {default}")
        return default


def validate_financial_inputs(notional: float, rate: float, maturity_years: float) -> None:
    """Validate financial calculation inputs."""
    if notional <= 0:
        raise BusinessLogicError("Notional must be positive")
    
    if notional > 1e12:
        raise BusinessLogicError("Notional exceeds maximum allowed value")
    
    if not (-0.1 <= rate <= 0.5):
        raise BusinessLogicError("Interest rate must be between -10% and 50%")
    
    if not (0 < maturity_years <= 100):
        raise BusinessLogicError("Maturity must be between 0 and 100 years")
