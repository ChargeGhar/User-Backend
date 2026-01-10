"""
ChargeGhar Device API Client
=============================

A modular Python client for the ChargeGhar Spring API.

This package provides:
- AuthClient: Authentication and user management
- DeviceClient: Device control and status
- AdminClient: Admin management and statistics
- DeviceAPIClient: Unified facade combining all clients

Installation:
    Copy this folder to your Django project or install as a package.

Configuration (Django):
    Add to settings.py:
    
    DEVICE_API = {
        'BASE_URL': 'https://api.chargeghar.com',
        'CONNECT_TIMEOUT': 10,
        'READ_TIMEOUT': 30,
        'MAX_RETRIES': 2,
        'AUTH_ENABLED': True,
        'AUTH_USERNAME': 'system_user',
        'AUTH_PASSWORD': 'your_password',
        'AUTH_LOGIN_ENDPOINT': '/api/auth/login',
    }

Configuration (Standalone):
    client = DeviceAPIClient(
        base_url='https://api.chargeghar.com',
        auth_username='admin',
        auth_password='password'
    )

Quick Start:
    from python_lib_client import DeviceAPIClient
    
    # Create client
    client = DeviceAPIClient()
    
    # Login
    login = client.auth.login('admin', 'password')
    if login.success:
        print(f"Logged in as: {login.user.username}")
    
    # Check device
    powerbanks = client.device.check_typed('864601069946994')
    for pb in powerbanks:
        print(f"Slot {pb.index}: {pb.power}% battery")
    
    # Pop powerbank
    sn = client.device.popup_random_typed('864601069946994', min_power=30)
    print(f"Popped: {sn}")
    
    # Get statistics
    stats = client.admin.get_statistics_typed()
    print(f"Devices: {stats.total_devices} ({stats.online_devices} online)")

Module Structure:
    python_lib_client/
    ├── __init__.py     # This file - exports and facade
    ├── types.py        # Type definitions (HttpResult, Powerbank, etc.)
    ├── base.py         # Base HTTP client with auth
    ├── auth.py         # AuthClient - authentication endpoints
    ├── device.py       # DeviceClient - device control endpoints
    └── admin.py        # AdminClient - admin management endpoints

Auto-generated from Spring source code analysis
Date: 2026-01-10
"""
from __future__ import annotations

from typing import Optional

# Type exports
from .types import (
    # Enums
    DeviceOnlineStatus,
    UserRole,
    NetworkMode,
    # Response types
    HttpResult,
    LoginResponse,
    AdminUser,
    Powerbank,
    DeviceCreateResult,
    AdminStatistics,
    TokenInfo,
)

# Client exports
from .base import BaseClient, ClientException, AuthenticationError, ConnectionError, TimeoutError
from .auth import AuthClient
from .device import DeviceClient
from .admin import AdminClient


__version__ = '1.0.0'
__author__ = 'ChargeGhar'


class DeviceAPIClient:
    """
    Unified facade for all ChargeGhar API operations
    
    Combines AuthClient, DeviceClient, and AdminClient into a single interface.
    Shares authentication state across all clients.
    
    Attributes:
        auth: AuthClient for authentication operations
        device: DeviceClient for device control
        admin: AdminClient for admin management
    
    Example:
        # With Django settings
        client = DeviceAPIClient()
        
        # With explicit config
        client = DeviceAPIClient(
            base_url='https://api.chargeghar.com',
            auth_username='admin',
            auth_password='password'
        )
        
        # With pre-existing token
        client = DeviceAPIClient(jwt_token='eyJ...')
        
        # Use individual clients
        client.auth.login('admin', 'password')
        client.device.check('864601069946994')
        client.admin.get_statistics()
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
        Initialize unified API client
        
        Args:
            base_url: API base URL (default from Django settings or 'https://api.chargeghar.com')
            connect_timeout: Connection timeout in seconds (default: 10)
            read_timeout: Read timeout in seconds (default: 30)
            max_retries: Max retry attempts for 5xx errors (default: 2)
            auth_enabled: Enable JWT authentication (default: True)
            auth_username: Username for auto-login
            auth_password: Password for auto-login
            auth_login_endpoint: Login endpoint path (default: '/api/auth/login')
            jwt_token: Pre-existing JWT token (skips auto-login)
        """
        # Common config for all clients
        config = {
            'base_url': base_url,
            'connect_timeout': connect_timeout,
            'read_timeout': read_timeout,
            'max_retries': max_retries,
            'auth_enabled': auth_enabled,
            'auth_username': auth_username,
            'auth_password': auth_password,
            'auth_login_endpoint': auth_login_endpoint,
            'jwt_token': jwt_token,
        }
        
        # Initialize individual clients
        self._auth = AuthClient(**config)
        self._device = DeviceClient(**config)
        self._admin = AdminClient(**config)
        
        # Sync token across clients
        self._sync_token()
    
    def _sync_token(self):
        """Sync JWT token across all clients"""
        # Use auth client as source of truth
        token = self._auth._jwt_token
        expires = self._auth._token_expires_at
        
        self._device._jwt_token = token
        self._device._token_expires_at = expires
        
        self._admin._jwt_token = token
        self._admin._token_expires_at = expires
    
    @property
    def auth(self) -> AuthClient:
        """Authentication operations"""
        return self._auth
    
    @property
    def device(self) -> DeviceClient:
        """Device control operations"""
        # Sync token from auth client
        if self._auth._jwt_token != self._device._jwt_token:
            self._device._jwt_token = self._auth._jwt_token
            self._device._token_expires_at = self._auth._token_expires_at
        return self._device
    
    @property
    def admin(self) -> AdminClient:
        """Admin management operations"""
        # Sync token from auth client
        if self._auth._jwt_token != self._admin._jwt_token:
            self._admin._jwt_token = self._auth._jwt_token
            self._admin._token_expires_at = self._auth._token_expires_at
        return self._admin
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication"""
        return self._auth.is_token_valid()
    
    @property
    def jwt_token(self) -> Optional[str]:
        """Get current JWT token"""
        return self._auth._jwt_token
    
    @jwt_token.setter
    def jwt_token(self, value: Optional[str]):
        """Set JWT token for all clients"""
        self._auth.jwt_token = value
        self._sync_token()
    
    def login(self, username: str, password: str) -> LoginResponse:
        """
        Login and authenticate all clients
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            LoginResponse with token and user info
        """
        response = self._auth.login(username, password)
        if response.success:
            self._sync_token()
        return response
    
    def logout(self) -> HttpResult:
        """Logout and clear authentication"""
        result = self._auth.logout()
        self._sync_token()
        return result


# ==========================================
# SINGLETON INSTANCE (for Django integration)
# ==========================================

_client_instance: Optional[DeviceAPIClient] = None


def get_client() -> DeviceAPIClient:
    """
    Get singleton instance of DeviceAPIClient
    
    Uses Django settings for configuration if available.
    
    Usage:
        from python_lib_client import get_client
        
        client = get_client()
        result = client.device.check('864601069946994')
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = DeviceAPIClient()
    return _client_instance


def reset_client():
    """Reset singleton instance (for testing)"""
    global _client_instance
    _client_instance = None


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Main client
    'DeviceAPIClient',
    'get_client',
    'reset_client',
    
    # Individual clients
    'AuthClient',
    'DeviceClient', 
    'AdminClient',
    'BaseClient',
    
    # Exceptions
    'ClientException',
    'AuthenticationError',
    'ConnectionError',
    'TimeoutError',
    
    # Types - Enums
    'DeviceOnlineStatus',
    'UserRole',
    'NetworkMode',
    
    # Types - Response models
    'HttpResult',
    'LoginResponse',
    'AdminUser',
    'Powerbank',
    'DeviceCreateResult',
    'AdminStatistics',
    'TokenInfo',
]
