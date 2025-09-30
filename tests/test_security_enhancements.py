"""Tests for security enhancements."""

import pytest
from unittest.mock import Mock, patch
from flask import Flask
from src.gemini_ird_pricer.security import SecurityHeaders, setup_cors, validate_auth_credentials, require_auth


class TestSecurityHeaders:
    """Test SecurityHeaders middleware."""
    
    def test_security_headers_init(self):
        """Test SecurityHeaders initialization."""
        app = Flask(__name__)
        config = {'ENV': 'production'}
        
        security = SecurityHeaders(app, config)
        assert security.config == config
    
    def test_basic_security_headers(self):
        """Test basic security headers are added."""
        app = Flask(__name__)
        config = {}
        
        SecurityHeaders(app, config)
        
        with app.test_client() as client:
            response = client.get('/')
            
            assert response.headers.get('X-Content-Type-Options') == 'nosniff'
            assert response.headers.get('X-Frame-Options') == 'DENY'
            assert response.headers.get('X-XSS-Protection') == '1; mode=block'
            assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    
    def test_csp_header_production(self):
        """Test CSP header in production."""
        app = Flask(__name__)
        config = {'ENV': 'production'}
        
        SecurityHeaders(app, config)
        
        with app.test_client() as client:
            response = client.get('/')
            
            csp = response.headers.get('Content-Security-Policy')
            assert csp is not None
            assert "default-src 'self'" in csp
    
    def test_custom_csp_header(self):
        """Test custom CSP header."""
        app = Flask(__name__)
        custom_csp = "default-src 'none'; script-src 'self'"
        config = {'CONTENT_SECURITY_POLICY': custom_csp}
        
        SecurityHeaders(app, config)
        
        with app.test_client() as client:
            response = client.get('/')
            
            assert response.headers.get('Content-Security-Policy') == custom_csp
    
    def test_permissions_policy(self):
        """Test Permissions Policy header."""
        app = Flask(__name__)
        config = {}
        
        SecurityHeaders(app, config)
        
        with app.test_client() as client:
            response = client.get('/')
            
            permissions = response.headers.get('Permissions-Policy')
            assert permissions is not None
            assert 'geolocation=()' in permissions
            assert 'microphone=()' in permissions


class TestCORS:
    """Test CORS setup."""
    
    def test_cors_allowed_origins(self):
        """Test CORS with allowed origins."""
        app = Flask(__name__)
        config = {
            'CORS_ALLOWED_ORIGINS': ['http://localhost:3000'],
            'CORS_ALLOW_CREDENTIALS': True
        }
        
        setup_cors(app, config)
        
        with app.test_client() as client:
            response = client.get('/', headers={'Origin': 'http://localhost:3000'})
            
            assert response.headers.get('Access-Control-Allow-Origin') == 'http://localhost:3000'
            assert response.headers.get('Access-Control-Allow-Credentials') == 'true'
    
    def test_cors_disallowed_origin(self):
        """Test CORS with disallowed origin."""
        app = Flask(__name__)
        config = {
            'CORS_ALLOWED_ORIGINS': ['http://localhost:3000']
        }
        
        setup_cors(app, config)
        
        with app.test_client() as client:
            response = client.get('/', headers={'Origin': 'http://evil.com'})
            
            assert 'Access-Control-Allow-Origin' not in response.headers
    
    def test_cors_preflight(self):
        """Test CORS preflight request."""
        app = Flask(__name__)
        config = {
            'CORS_ALLOWED_ORIGINS': ['http://localhost:3000']
        }
        
        setup_cors(app, config)
        
        with app.test_client() as client:
            response = client.options('/', headers={'Origin': 'http://localhost:3000'})
            
            assert response.headers.get('Access-Control-Allow-Methods') is not None
            assert response.headers.get('Access-Control-Allow-Headers') is not None
            assert response.headers.get('Access-Control-Max-Age') == '86400'


class TestAuthValidation:
    """Test authentication validation."""
    
    @patch.dict('os.environ', {'API_USER': 'testuser', 'API_PASS': 'testpass'})
    def test_validate_auth_credentials_success(self):
        """Test successful credential validation."""
        config = {'AUTH_USER_ENV': 'API_USER', 'AUTH_PASS_ENV': 'API_PASS'}
        
        username, password = validate_auth_credentials(config)
        
        assert username == 'testuser'
        assert password == 'testpass'
    
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_auth_credentials_missing(self):
        """Test missing credentials."""
        config = {'AUTH_USER_ENV': 'API_USER', 'AUTH_PASS_ENV': 'API_PASS'}
        
        username, password = validate_auth_credentials(config)
        
        assert username is None
        assert password is None
    
    def test_require_auth_disabled(self):
        """Test require_auth when authentication is disabled."""
        app = Flask(__name__)
        config = {'ENABLE_AUTH': False}
        
        @require_auth(config)
        def test_route():
            return 'success'
        
        with app.test_request_context():
            result = test_route()
            assert result == 'success'
    
    @patch.dict('os.environ', {}, clear=True)
    def test_require_auth_not_configured(self):
        """Test require_auth when credentials not configured."""
        app = Flask(__name__)
        config = {'ENABLE_AUTH': True, 'AUTH_USER_ENV': 'API_USER', 'AUTH_PASS_ENV': 'API_PASS'}
        
        @require_auth(config)
        def test_route():
            return 'success'
        
        with app.test_request_context():
            result, status = test_route()
            assert status == 503
            assert 'not configured' in result.get_json()['error']['message']
    
    @patch.dict('os.environ', {'API_USER': 'testuser', 'API_PASS': 'testpass'})
    def test_require_auth_missing_credentials(self):
        """Test require_auth with missing request credentials."""
        app = Flask(__name__)
        config = {'ENABLE_AUTH': True, 'AUTH_USER_ENV': 'API_USER', 'AUTH_PASS_ENV': 'API_PASS'}
        
        @require_auth(config)
        def test_route():
            return 'success'
        
        with app.test_request_context():
            result, status = test_route()
            assert status == 401
            assert 'Authentication required' in result.get_json()['error']['message']
    
    @patch.dict('os.environ', {'API_USER': 'testuser', 'API_PASS': 'testpass'})
    def test_require_auth_valid_basic_auth(self):
        """Test require_auth with valid Basic Auth header."""
        import base64
        
        app = Flask(__name__)
        config = {'ENABLE_AUTH': True, 'AUTH_USER_ENV': 'API_USER', 'AUTH_PASS_ENV': 'API_PASS'}
        
        @require_auth(config)
        def test_route():
            return 'success'
        
        # Create valid Basic Auth header
        credentials = base64.b64encode(b'testuser:testpass').decode('utf-8')
        auth_header = f'Basic {credentials}'
        
        with app.test_request_context(headers={'Authorization': auth_header}):
            result = test_route()
            assert result == 'success'
    
    @patch.dict('os.environ', {'API_USER': 'testuser', 'API_PASS': 'testpass'})
    def test_require_auth_invalid_credentials(self):
        """Test require_auth with invalid credentials."""
        import base64
        
        app = Flask(__name__)
        config = {'ENABLE_AUTH': True, 'AUTH_USER_ENV': 'API_USER', 'AUTH_PASS_ENV': 'API_PASS'}
        
        @require_auth(config)
        def test_route():
            return 'success'
        
        # Create invalid Basic Auth header
        credentials = base64.b64encode(b'wronguser:wrongpass').decode('utf-8')
        auth_header = f'Basic {credentials}'
        
        with app.test_request_context(headers={'Authorization': auth_header}):
            result, status = test_route()
            assert status == 401
            assert 'Invalid credentials' in result.get_json()['error']['message']
