"""
Base HTTP Client for Spring API
================================

Provides core HTTP functionality with:
- JWT token management (auto-login, caching, refresh)
- Standardized request/response handling
- Error handling and retry logic
- Support for both Django and standalone usage

Auto-generated from Spring source code analysis
Date: 2026-01-10
"""
from __future__ import annotations

import requests
import logging
from abc import ABC
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .types import HttpResult, LoginResponse


logger = logging.getLogger(__name__)


class ClientException(Exception):
    """Base exception for API client errors"""
    
    def __init__(self, message: str, code: str = "error", context: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.context = context or {}
        super().__init__(message)


class AuthenticationError(ClientException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="auth_failed")


class ConnectionError(ClientException):
    """Raised when connection to API fails"""
    
    def __init__(self, message: str, base_url: str = ""):
        super().__init__(message, code="connection_error", context={'base_url': base_url})


class TimeoutError(ClientException):
    """Raised when request times out"""
    
    def __init__(self, timeout: int):
        super().__init__(f"Request timeout after {timeout} seconds", code="timeout")


class BaseClient(ABC):
    """
    Base HTTP client with authentication support
    
    Configuration:
        Can be configured via Django settings or constructor parameters.
        
        Django settings (DEVICE_API dict):
        - BASE_URL: API base URL (default: 'https://api.chargeghar.com')
        - CONNECT_TIMEOUT: Connection timeout in seconds (default: 10)
        - READ_TIMEOUT: Read timeout in seconds (default: 30)
        - MAX_RETRIES: Max retry attempts for server errors (default: 2)
        - AUTH_ENABLED: Enable JWT authentication (default: True)
        - AUTH_USERNAME: Username for auto-login
        - AUTH_PASSWORD: Password for auto-login
        - AUTH_LOGIN_ENDPOINT: Login endpoint path (default: '/api/auth/login')
    
    Usage:
        # With Django settings
        client = BaseClient()
        
        # With explicit config
        client = BaseClient(
            base_url='https://api.chargeghar.com',
            auth_username='admin',
            auth_password='password'
        )
        
        # With pre-existing token (skip auto-login)
        client = BaseClient(jwt_token='eyJ...')
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        connect_timeout: int = 10,
        read_timeout: int = 30,
        max_retries: int = 2,
        auth_enabled: bool = True,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
        auth_login_endpoint: str = '/api/auth/login',
        jwt_token: Optional[str] = None
    ):
        """
        Initialize base client
        
        Args:
            base_url: API base URL
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            max_retries: Max retry attempts for 5xx errors
            auth_enabled: Enable JWT authentication
            auth_username: Username for auto-login
            auth_password: Password for auto-login
            auth_login_endpoint: Login endpoint path
            jwt_token: Pre-existing JWT token (skips auto-login)
        """
        # Try Django settings first, then fall back to parameters
        config = self._load_django_config()
        
        self.base_url = base_url or config.get('BASE_URL', 'https://api.chargeghar.com')
        self.connect_timeout = connect_timeout or config.get('CONNECT_TIMEOUT', 10)
        self.read_timeout = read_timeout or config.get('READ_TIMEOUT', 30)
        self.max_retries = max_retries or config.get('MAX_RETRIES', 2)
        self.auth_enabled = auth_enabled if auth_enabled is not None else config.get('AUTH_ENABLED', True)
        self.auth_username = auth_username or config.get('AUTH_USERNAME')
        self.auth_password = auth_password or config.get('AUTH_PASSWORD')
        self.auth_login_endpoint = auth_login_endpoint or config.get('AUTH_LOGIN_ENDPOINT', '/api/auth/login')
        
        # Token management
        self._jwt_token = jwt_token
        self._token_expires_at: Optional[datetime] = None
        
        # If token provided, assume it's valid for 24 hours
        if jwt_token:
            self._token_expires_at = datetime.now() + timedelta(hours=24)
        
        logger.info(f"BaseClient initialized - Base URL: {self.base_url}")
    
    def _load_django_config(self) -> Dict[str, Any]:
        """Load configuration from Django settings if available"""
        try:
            from django.conf import settings
            return getattr(settings, 'DEVICE_API', {})
        except (ImportError, Exception):
            return {}
    
    # ==========================================
    # TOKEN MANAGEMENT
    # ==========================================
    
    @property
    def jwt_token(self) -> Optional[str]:
        """Get current JWT token"""
        return self._jwt_token
    
    @jwt_token.setter
    def jwt_token(self, value: Optional[str]):
        """Set JWT token and reset expiry"""
        self._jwt_token = value
        if value:
            self._token_expires_at = datetime.now() + timedelta(hours=24)
        else:
            self._token_expires_at = None
    
    def is_token_valid(self) -> bool:
        """Check if current token is still valid (not expired)"""
        if not self.auth_enabled:
            return True
        
        if not self._jwt_token or not self._token_expires_at:
            return False
        
        # Refresh if token expires within 5 minutes
        buffer_time = datetime.now() + timedelta(minutes=5)
        return buffer_time < self._token_expires_at
    
    def _login(self) -> bool:
        """
        Authenticate with Spring API to get JWT token
        
        Endpoint: POST /api/auth/login
        Request body: {"username": "...", "password": "..."}
        Response: {"success": true, "message": "...", "token": "...", "user": {...}}
        
        Returns:
            bool: True if login successful
        """
        if not self.auth_enabled:
            logger.info("Authentication disabled, skipping login")
            return True
        
        if not self.auth_username or not self.auth_password:
            logger.warning("No credentials configured for auto-login")
            return False
        
        try:
            login_url = f"{self.base_url}{self.auth_login_endpoint}"
            
            payload = {
                'username': self.auth_username,
                'password': self.auth_password
            }
            
            logger.info(f"Authenticating with Spring API: {login_url}")
            
            response = requests.post(
                login_url,
                json=payload,
                timeout=(self.connect_timeout, self.read_timeout)
            )
            
            if response.status_code == 200:
                data = response.json()
                login_response = LoginResponse.from_dict(data)
                
                if login_response.success and login_response.token:
                    self.jwt_token = login_response.token
                    logger.info("Successfully authenticated with Spring API")
                    return True
                else:
                    logger.error(f"Login failed: {login_response.message}")
                    return False
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Login timeout after {self.read_timeout}s")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to {self.base_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid JWT token, login if needed
        
        Returns:
            bool: True if authenticated
        """
        if not self.auth_enabled:
            return True
        
        if self.is_token_valid():
            return True
        
        logger.info("Token expired or invalid, re-authenticating...")
        return self._login()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers including Authorization if authenticated"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.auth_enabled and self._jwt_token:
            headers['Authorization'] = f'Bearer {self._jwt_token}'
        
        return headers
    
    # ==========================================
    # HTTP REQUEST METHODS
    # ==========================================
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        retry_auth: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Make HTTP request to Spring API
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path (e.g., '/check')
            params: Query parameters
            data: Request body for POST
            retry_count: Current retry attempt
            retry_auth: Retry on 401 (re-authenticate)
        
        Returns:
            Tuple of (success: bool, response_data: dict)
            
            Success response:
            (True, {"code": 200, "data": ..., "msg": "ok", "time": ...})
            
            Error response:
            (False, {"code": 500, "msg": "error message", ...})
        """
        try:
            # Ensure authenticated
            if not self.ensure_authenticated():
                raise AuthenticationError("Failed to authenticate with Device API")
            
            url = f"{self.base_url}{endpoint}"
            headers = self._get_headers()
            
            logger.debug(f"{method} {url} - Params: {params}")
            
            if method.upper() == 'GET':
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=(self.connect_timeout, self.read_timeout)
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=(self.connect_timeout, self.read_timeout)
                )
            else:
                raise ClientException(f"Unsupported HTTP method: {method}", code="invalid_method")
            
            # Handle 401 - re-authenticate and retry once
            if response.status_code == 401 and retry_auth and retry_count == 0:
                logger.warning("Got 401, re-authenticating and retrying...")
                self._jwt_token = None
                return self._make_request(method, endpoint, params, data, retry_count + 1, retry_auth=False)
            
            # Handle 5xx - retry with backoff
            if response.status_code >= 500 and retry_count < self.max_retries:
                logger.warning(f"Server error {response.status_code}, retrying... ({retry_count + 1}/{self.max_retries})")
                import time
                time.sleep(1 * (retry_count + 1))  # Simple backoff
                return self._make_request(method, endpoint, params, data, retry_count + 1, retry_auth)
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'text': response.text}
            
            # Check success
            if response.status_code == 200:
                # Spring HttpResult format
                code = response_data.get('code', 200)
                if code == 200:
                    return (True, response_data)
                else:
                    return (False, response_data)
            else:
                if 'code' not in response_data:
                    response_data['code'] = response.status_code
                return (False, response_data)
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.read_timeout}s")
            return (False, {'code': 408, 'msg': f'Request timeout after {self.read_timeout} seconds'})
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return (False, {'code': 503, 'msg': f'Cannot connect to Device API at {self.base_url}'})
        
        except AuthenticationError as e:
            return (False, {'code': 401, 'msg': str(e)})
        
        except ClientException as e:
            return (False, {'code': 500, 'msg': str(e)})
        
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return (False, {'code': 500, 'msg': str(e)})
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> HttpResult:
        """
        Make GET request and return HttpResult
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            HttpResult with response data
        """
        success, data = self._make_request('GET', endpoint, params=params)
        return HttpResult.from_dict(data)
    
    def post(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> HttpResult:
        """
        Make POST request and return HttpResult
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            data: Request body
            
        Returns:
            HttpResult with response data
        """
        success, response_data = self._make_request('POST', endpoint, params=params, data=data)
        return HttpResult.from_dict(response_data)
