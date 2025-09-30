"""Centralized error handling for consistent API responses."""

from typing import Dict, Any, Tuple
from pydantic import ValidationError
from flask import jsonify


class ErrorHandler:
    """Centralized error handler for consistent API responses."""
    
    @staticmethod
    def handle_validation_error(e: ValidationError) -> Tuple[Dict[str, Any], int]:
        """Handle Pydantic validation errors."""
        return {
            "error": {
                "type": "validation_error",
                "message": "Input validation failed",
                "details": e.errors()
            }
        }, 400
    
    @staticmethod
    def handle_value_error(e: ValueError) -> Tuple[Dict[str, Any], int]:
        """Handle value errors."""
        return {
            "error": {
                "type": "input_error",
                "message": str(e)
            }
        }, 400
    
    @staticmethod
    def handle_file_not_found(message: str = "Required file not found") -> Tuple[Dict[str, Any], int]:
        """Handle file not found errors."""
        return {
            "error": {
                "type": "not_found",
                "message": message
            }
        }, 404
    
    @staticmethod
    def handle_payload_too_large() -> Tuple[Dict[str, Any], int]:
        """Handle payload too large errors."""
        return {
            "error": {
                "type": "payload_too_large",
                "message": "Request payload too large."
            }
        }, 413
    
    @staticmethod
    def handle_rate_limited() -> Tuple[Dict[str, Any], int]:
        """Handle rate limit exceeded errors."""
        return {
            "error": {
                "type": "rate_limited",
                "message": "Too many requests. Please retry later."
            }
        }, 429
    
    @staticmethod
    def handle_server_error(message: str = "An unexpected error occurred.") -> Tuple[Dict[str, Any], int]:
        """Handle internal server errors."""
        return {
            "error": {
                "type": "server_error",
                "message": message
            }
        }, 500
    
    @staticmethod
    def handle_unauthorized() -> Tuple[Dict[str, Any], int]:
        """Handle unauthorized access."""
        return {
            "error": {
                "type": "unauthorized",
                "message": "Authentication required."
            }
        }, 401
    
    @staticmethod
    def handle_forbidden() -> Tuple[Dict[str, Any], int]:
        """Handle forbidden access."""
        return {
            "error": {
                "type": "forbidden",
                "message": "Access denied."
            }
        }, 403
    
    @staticmethod
    def handle_service_unavailable(message: str = "Service temporarily unavailable.") -> Tuple[Dict[str, Any], int]:
        """Handle service unavailable errors."""
        return {
            "error": {
                "type": "service_unavailable",
                "message": message
            }
        }, 503
