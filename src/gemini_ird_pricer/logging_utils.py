from __future__ import annotations
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from flask import request, g, has_request_context


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive data from log entries."""
    sensitive_keys = {
        'notional', 'fixed_rate', 'rate', 'password', 'token', 
        'api_key', 'authorization', 'user_id', 'email'
    }
    
    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_log_data(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add request context if available
        if has_request_context():
            log_data.update({
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
            })
            
            # Add request ID if available
            request_id = getattr(g, 'request_id', None)
            if request_id:
                log_data['request_id'] = request_id
            
            # Add trace information if available
            trace_id = getattr(g, 'trace_id', None)
            if trace_id:
                log_data['trace_id'] = trace_id
            
            span_id = getattr(g, 'span_id', None)
            if span_id:
                log_data['span_id'] = span_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'):
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class PlainFormatter(logging.Formatter):
    """Plain text formatter with request context."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text with context."""
        formatted = super().format(record)
        
        # Add request context if available
        if has_request_context():
            request_id = getattr(g, 'request_id', None)
            if request_id:
                formatted = f"[{request_id}] {formatted}"
        
        return formatted


def setup_logging(app, config: Dict[str, Any]) -> None:
    """Setup application logging based on configuration."""
    log_level = getattr(logging, config.get('LOG_LEVEL', 'INFO').upper())
    log_format = config.get('LOG_FORMAT', 'plain')
    
    # Remove default Flask handlers
    app.logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Set formatter based on config
    if log_format == 'json':
        formatter = StructuredFormatter()
    else:
        formatter = PlainFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    
    # Configure app logger
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    
    # Configure root logger to prevent duplicate logs
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Return a module logger.

    Handlers/formatters are configured centrally in the Flask app factory.
    This helper exists to provide a single import point for future tweaks
    (e.g., adding contextual filters or adapter classes).
    """
    return logging.getLogger(name)


class RequestLogger:
    """Middleware for logging HTTP requests."""
    
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize request logging for Flask app."""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Log request start and setup request context."""
        import uuid
        import time
        
        # Generate request ID
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()
        
        # Extract trace information from headers
        traceparent = request.headers.get('traceparent')
        if traceparent:
            try:
                # Parse W3C trace context
                parts = traceparent.split('-')
                if len(parts) >= 3:
                    g.trace_id = parts[1]
                    g.span_id = parts[2]
            except Exception:
                pass
        
        # Alternative trace headers
        if not hasattr(g, 'trace_id'):
            g.trace_id = request.headers.get('X-Trace-Id')
        if not hasattr(g, 'span_id'):
            g.span_id = request.headers.get('X-Span-Id')
        
        # Log request start
        logger = get_logger(__name__)
        logger.info(
            "Request started",
            extra={
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
            }
        )
    
    def after_request(self, response):
        """Log request completion."""
        import time
        
        duration_ms = (time.time() - g.start_time) * 1000 if hasattr(g, 'start_time') else 0
        
        logger = get_logger(__name__)
        logger.info(
            "Request completed",
            extra={
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': round(duration_ms, 2),
            }
        )
        
        return response
