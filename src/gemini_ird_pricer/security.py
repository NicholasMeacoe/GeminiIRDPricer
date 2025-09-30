"""Security middleware and utilities."""

from flask import Flask, Response, request
from typing import Optional


class SecurityHeaders:
    """Security headers middleware for Flask applications."""
    
    def __init__(self, app: Optional[Flask] = None, config: Optional[dict] = None):
        self.config = config or {}
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize security headers for Flask app."""
        app.after_request(self.add_security_headers)
    
    def add_security_headers(self, response: Response) -> Response:
        """Add comprehensive security headers to response."""
        # Basic security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HSTS for HTTPS
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        csp = self.config.get('CONTENT_SECURITY_POLICY')
        if csp:
            response.headers['Content-Security-Policy'] = csp
        else:
            # Safe default CSP for production
            if self.config.get('ENV') == 'production':
                default_csp = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' data:; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self'"
                )
                response.headers['Content-Security-Policy'] = default_csp
        
        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        return response


def setup_cors(app: Flask, config: dict) -> None:
    """Setup CORS headers based on configuration."""
    
    @app.after_request
    def add_cors_headers(response: Response) -> Response:
        """Add CORS headers to response."""
        allowed_origins = config.get('CORS_ALLOWED_ORIGINS', [])
        allow_credentials = config.get('CORS_ALLOW_CREDENTIALS', False)
        
        origin = request.headers.get('Origin')
        
        # Handle CORS for allowed origins
        if origin and allowed_origins:
            if origin in allowed_origins or '*' in allowed_origins:
                response.headers['Access-Control-Allow-Origin'] = origin
                if allow_credentials:
                    response.headers['Access-Control-Allow-Credentials'] = 'true'
        elif not allowed_origins and config.get('ENV') != 'production':
            # Allow all origins in development if none specified
            response.headers['Access-Control-Allow-Origin'] = '*'
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = (
                'Content-Type, Authorization, X-Requested-With, X-Request-ID'
            )
            response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response


def validate_auth_credentials(config: dict) -> tuple[Optional[str], Optional[str]]:
    """Validate and retrieve authentication credentials from environment."""
    import os
    
    user_env = config.get('AUTH_USER_ENV', 'API_USER')
    pass_env = config.get('AUTH_PASS_ENV', 'API_PASS')
    
    username = os.getenv(user_env)
    password = os.getenv(pass_env)
    
    return username, password


def require_auth(config: dict):
    """Decorator to require authentication for routes."""
    from functools import wraps
    from flask import request, jsonify
    import base64
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not config.get('ENABLE_AUTH', False):
                return f(*args, **kwargs)
            
            username, password = validate_auth_credentials(config)
            
            if not username or not password:
                return jsonify({
                    "error": {
                        "type": "service_unavailable",
                        "message": "Authentication not configured"
                    }
                }), 503
            
            auth = request.authorization
            if not auth:
                # Try to parse Authorization header manually
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Basic '):
                    try:
                        encoded = auth_header[6:]
                        decoded = base64.b64decode(encoded).decode('utf-8')
                        auth_username, auth_password = decoded.split(':', 1)
                        if auth_username == username and auth_password == password:
                            return f(*args, **kwargs)
                    except Exception:
                        pass
                
                return jsonify({
                    "error": {
                        "type": "unauthorized",
                        "message": "Authentication required"
                    }
                }), 401
            
            if auth.username != username or auth.password != password:
                return jsonify({
                    "error": {
                        "type": "unauthorized",
                        "message": "Invalid credentials"
                    }
                }), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
