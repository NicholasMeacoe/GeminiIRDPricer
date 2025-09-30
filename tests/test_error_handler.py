"""Tests for error handler."""

import pytest
from pydantic import ValidationError, BaseModel, Field
from src.gemini_ird_pricer.error_handler import ErrorHandler


class TestModel(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0)


def test_handle_validation_error():
    """Test handling of Pydantic validation errors."""
    try:
        TestModel(name="", age=-1)
    except ValidationError as e:
        result, status = ErrorHandler.handle_validation_error(e)
        
        assert status == 400
        assert result["error"]["type"] == "validation_error"
        assert result["error"]["message"] == "Input validation failed"
        assert "details" in result["error"]
        assert len(result["error"]["details"]) == 2  # Two validation errors


def test_handle_value_error():
    """Test handling of value errors."""
    error = ValueError("Invalid input value")
    result, status = ErrorHandler.handle_value_error(error)
    
    assert status == 400
    assert result["error"]["type"] == "input_error"
    assert result["error"]["message"] == "Invalid input value"


def test_handle_file_not_found():
    """Test handling of file not found errors."""
    result, status = ErrorHandler.handle_file_not_found("Custom message")
    
    assert status == 404
    assert result["error"]["type"] == "not_found"
    assert result["error"]["message"] == "Custom message"


def test_handle_file_not_found_default():
    """Test handling of file not found errors with default message."""
    result, status = ErrorHandler.handle_file_not_found()
    
    assert status == 404
    assert result["error"]["type"] == "not_found"
    assert result["error"]["message"] == "Required file not found"


def test_handle_payload_too_large():
    """Test handling of payload too large errors."""
    result, status = ErrorHandler.handle_payload_too_large()
    
    assert status == 413
    assert result["error"]["type"] == "payload_too_large"
    assert result["error"]["message"] == "Request payload too large."


def test_handle_rate_limited():
    """Test handling of rate limit errors."""
    result, status = ErrorHandler.handle_rate_limited()
    
    assert status == 429
    assert result["error"]["type"] == "rate_limited"
    assert result["error"]["message"] == "Too many requests. Please retry later."


def test_handle_server_error():
    """Test handling of server errors."""
    result, status = ErrorHandler.handle_server_error("Custom server error")
    
    assert status == 500
    assert result["error"]["type"] == "server_error"
    assert result["error"]["message"] == "Custom server error"


def test_handle_server_error_default():
    """Test handling of server errors with default message."""
    result, status = ErrorHandler.handle_server_error()
    
    assert status == 500
    assert result["error"]["type"] == "server_error"
    assert result["error"]["message"] == "An unexpected error occurred."


def test_handle_unauthorized():
    """Test handling of unauthorized errors."""
    result, status = ErrorHandler.handle_unauthorized()
    
    assert status == 401
    assert result["error"]["type"] == "unauthorized"
    assert result["error"]["message"] == "Authentication required."


def test_handle_forbidden():
    """Test handling of forbidden errors."""
    result, status = ErrorHandler.handle_forbidden()
    
    assert status == 403
    assert result["error"]["type"] == "forbidden"
    assert result["error"]["message"] == "Access denied."


def test_handle_service_unavailable():
    """Test handling of service unavailable errors."""
    result, status = ErrorHandler.handle_service_unavailable("Custom unavailable message")
    
    assert status == 503
    assert result["error"]["type"] == "service_unavailable"
    assert result["error"]["message"] == "Custom unavailable message"


def test_handle_service_unavailable_default():
    """Test handling of service unavailable errors with default message."""
    result, status = ErrorHandler.handle_service_unavailable()
    
    assert status == 503
    assert result["error"]["type"] == "service_unavailable"
    assert result["error"]["message"] == "Service temporarily unavailable."
