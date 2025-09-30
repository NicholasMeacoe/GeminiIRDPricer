"""Enhanced authentication with JWT support."""

from __future__ import annotations
import jwt
import time
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, current_app, jsonify


class JWTAuth:
    """JWT-based authentication handler."""
    
    def __init__(self, secret_key: str, algorithm: str = 'HS256'):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token for user."""
        payload = {
            'user_id': user_id,
            'exp': time.time() + expires_in,
            'iat': time.time()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


def require_jwt_auth(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': {
                    'type': 'unauthorized',
                    'message': 'JWT token required'
                }
            }), 401
        
        token = auth_header.split(' ')[1]
        jwt_secret = current_app.config.get('JWT_SECRET_KEY')
        
        if not jwt_secret:
            return jsonify({
                'error': {
                    'type': 'server_error',
                    'message': 'JWT not configured'
                }
            }), 500
        
        jwt_auth = JWTAuth(jwt_secret)
        payload = jwt_auth.validate_token(token)
        
        if not payload:
            return jsonify({
                'error': {
                    'type': 'unauthorized',
                    'message': 'Invalid or expired token'
                }
            }), 401
        
        request.jwt_payload = payload
        return f(*args, **kwargs)
    
    return decorated_function


class RateLimiter:
    """Enhanced rate limiting with per-user tracking."""
    
    def __init__(self):
        self.requests = {}
        self.window_size = 60  # 1 minute window
    
    def is_allowed(self, identifier: str, limit: int) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        window_start = now - self.window_size
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= limit:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True


def rate_limit(limit: int = 100):
    """Decorator for rate limiting endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use JWT user_id if available, otherwise IP
            identifier = getattr(request, 'jwt_payload', {}).get('user_id') or request.remote_addr
            
            limiter = getattr(current_app, '_rate_limiter', None)
            if not limiter:
                limiter = RateLimiter()
                current_app._rate_limiter = limiter
            
            if not limiter.is_allowed(identifier, limit):
                return jsonify({
                    'error': {
                        'type': 'rate_limited',
                        'message': 'Rate limit exceeded'
                    }
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
