"""
Service for Device API integration - HTTP client for Java Spring API
============================================================

This service handles communication with the Java Spring API for device control.
All device operations (MQTT commands) are handled by the Java API, this is just a bridge.

Auto-generated for Device Integration
Date: 2025-11-05
"""
from __future__ import annotations

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings

from api.common.services.base import BaseService, ServiceException


logger = logging.getLogger(__name__)


class DeviceAPIService(BaseService):
    """
    HTTP client for Java Spring Device API with JWT authentication
    
    This service bridges Django to the Java API which handles all MQTT device communication.
    Features:
    - Auto-login to get JWT token
    - Token caching and auto-refresh
    - Automatic retry on 401 (re-authenticate)
    - Error handling following project patterns
    """
    
    def __init__(self):
        """Initialize with settings from Django config"""
        super().__init__()
        
        # Load configuration from settings
        config = getattr(settings, 'DEVICE_API', {})
        self.base_url = config.get('BASE_URL', 'https://api.chargeghar.com')
        self.connect_timeout = config.get('CONNECT_TIMEOUT', 10)
        self.read_timeout = config.get('READ_TIMEOUT', 30)
        self.max_retries = config.get('MAX_RETRIES', 2)
        
        # Authentication configuration
        self.auth_enabled = config.get('AUTH_ENABLED', True)
        self.auth_username = config.get('AUTH_USERNAME', 'system_user')
        self.auth_password = config.get('AUTH_PASSWORD', '')
        self.auth_login_endpoint = config.get('AUTH_LOGIN_ENDPOINT', '/api/auth/login')
        
        # Token management
        self.jwt_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        self.log_info(f"DeviceAPIService initialized - Base URL: {self.base_url}")
        self.log_info(f"Authentication: {'Enabled' if self.auth_enabled else 'Disabled'}")
    
    # ==========================================
    # AUTHENTICATION METHODS
    # ==========================================
    
    def _login(self) -> bool:
        """
        Authenticate with Java API to get JWT token
        
        Returns:
            bool: True if login successful, False otherwise
        """
        if not self.auth_enabled:
            self.log_info("Authentication disabled, skipping login")
            return True
        
        try:
            login_url = f"{self.base_url}{self.auth_login_endpoint}"
            
            payload = {
                'username': self.auth_username,
                'password': self.auth_password
            }
            
            self.log_info(f"Attempting login to Java API: {login_url}")
            
            response = requests.post(
                login_url,
                json=payload,
                timeout=(self.connect_timeout, self.read_timeout)
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract token from response
                # Adjust based on your Java API response format
                self.jwt_token = data.get('token') or data.get('access_token') or data.get('jwt')
                
                if self.jwt_token:
                    # Token valid for 24 hours by default
                    self.token_expires_at = datetime.now() + timedelta(hours=24)
                    self.log_info("Successfully authenticated with Java API")
                    return True
                else:
                    self.log_error(f"No token found in login response: {data}")
                    return False
            else:
                self.log_error(f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_error(f"Login exception: {str(e)}")
            return False
    
    def _is_token_valid(self) -> bool:
        """Check if JWT token is still valid"""
        if not self.auth_enabled:
            return True
            
        if not self.jwt_token or not self.token_expires_at:
            return False
        
        # Check if token expires in next 5 minutes (refresh early)
        expires_soon = datetime.now() + timedelta(minutes=5)
        return datetime.now() < self.token_expires_at and expires_soon < self.token_expires_at
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid JWT token, login if needed
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        if not self.auth_enabled:
            return True
            
        if self._is_token_valid():
            return True
        
        self.log_info("Token expired or invalid, re-authenticating...")
        return self._login()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers including JWT token if authentication is enabled
        
        Returns:
            Dict with Authorization header if authenticated
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.auth_enabled and self.jwt_token:
            headers['Authorization'] = f'Bearer {self.jwt_token}'
        
        return headers
    
    # ==========================================
    # HTTP REQUEST METHOD
    # ==========================================
    
    def _make_request(
        self, 
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        retry_auth: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Java API with error handling
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (e.g., '/send', '/check')
            params: Query parameters
            data: Request body data (for POST)
            retry_count: Current retry attempt
            retry_auth: Whether to retry on 401 (re-authenticate)
        
        Returns:
            Dict with standardized response format:
            {
                'success': bool,
                'data': Any,
                'message': str,
                'code': int
            }
        """
        try:
            # Ensure we're authenticated
            if not self._ensure_authenticated():
                raise ServiceException(
                    detail="Failed to authenticate with Device API",
                    code="auth_failed",
                    context={'base_url': self.base_url}
                )
            
            # Build full URL
            url = f"{self.base_url}{endpoint}"
            
            # Get headers with auth token
            headers = self._get_auth_headers()
            
            # Make request
            self.log_info(f"{method} {url} - Params: {params}")
            
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
                raise ServiceException(
                    detail=f"Unsupported HTTP method: {method}",
                    code="invalid_method"
                )
            
            # Handle 401 Unauthorized - token expired, retry with new token
            if response.status_code == 401 and retry_auth and retry_count == 0:
                self.log_warning("Got 401, re-authenticating and retrying...")
                self.jwt_token = None  # Force re-login
                return self._make_request(method, endpoint, params, data, retry_count + 1, retry_auth=False)
            
            # Handle server errors with retry
            if response.status_code >= 500 and retry_count < self.max_retries:
                self.log_warning(f"Server error {response.status_code}, retrying... (attempt {retry_count + 1}/{self.max_retries})")
                return self._make_request(method, endpoint, params, data, retry_count + 1, retry_auth)
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'text': response.text}
            
            # Check if request was successful
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response_data,
                    'message': 'ok',
                    'code': 200
                }
            else:
                # Error response
                error_message = response_data.get('message') or response_data.get('error') or response.text
                return {
                    'success': False,
                    'data': None,
                    'message': error_message,
                    'code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            self.log_error(f"Request timeout after {self.read_timeout} seconds")
            return {
                'success': False,
                'data': None,
                'message': f'Request timeout after {self.read_timeout} seconds',
                'code': 408
            }
        except requests.exceptions.ConnectionError as e:
            self.log_error(f"Connection error: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': f'Cannot connect to Device API at {self.base_url}',
                'code': 503
            }
        except ServiceException:
            raise
        except Exception as e:
            self.log_error(f"Unexpected error in _make_request: {str(e)}")
            return {
                'success': False,
                'data': None,
                'message': str(e),
                'code': 500
            }
    
    # ==========================================
    # PUBLIC API METHODS
    # ==========================================
    
    def send_command(self, device_name: str, command: str) -> Dict[str, Any]:
        """
        Send raw command to device
        
        Args:
            device_name: Device identifier (e.g., "CG001")
            command: Raw command string to send to device
        
        Returns:
            Dict with success status and response data
            
        Example:
            result = service.send_command("CG001", '{"cmd":"check"}')
            if result['success']:
                print(f"Command sent: {result['data']}")
        """
        try:
            if not device_name or not command:
                raise ServiceException(
                    detail="Device name and command are required",
                    code="invalid_params",
                    context={'device_name': device_name, 'command': command}
                )
            
            result = self._make_request(
                method='GET',
                endpoint='/send',
                params={
                    'deviceName': device_name,
                    'data': command
                }
            )
            
            if result['success']:
                self.log_info(f"Command sent to {device_name}: {command}")
            else:
                self.log_warning(f"Failed to send command to {device_name}: {result['message']}")
            
            return result
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to send command to device {device_name}")
    
    def check_device(self, device_name: str) -> Dict[str, Any]:
        """
        Check device status and get powerbank information (only occupied slots)
        
        Args:
            device_name: Device identifier (e.g., "CG001")
        
        Returns:
            Dict with success status and list of powerbanks in occupied slots
            
        Example:
            result = service.check_device("CG001")
            if result['success']:
                for pb in result['data']:
                    print(f"Slot {pb['index']}: {pb['power']}% battery")
        """
        try:
            if not device_name:
                raise ServiceException(
                    detail="Device name is required",
                    code="invalid_params"
                )
            
            result = self._make_request(
                method='GET',
                endpoint='/check',
                params={'deviceName': device_name}
            )
            
            if result['success']:
                powerbanks = result['data']
                self.log_info(f"Device {device_name} check successful: {len(powerbanks)} powerbanks found")
            else:
                self.log_warning(f"Failed to check device {device_name}: {result['message']}")
            
            return result
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to check device {device_name}")
    
    def check_all_devices(self, device_name: str) -> Dict[str, Any]:
        """
        Check all device slots including empty ones
        
        Args:
            device_name: Device identifier (e.g., "CG001")
        
        Returns:
            Dict with success status and list of all slots (occupied and empty)
            
        Example:
            result = service.check_all_devices("CG001")
            if result['success']:
                for slot in result['data']:
                    status = "Occupied" if slot['online'] else "Empty"
                    print(f"Slot {slot['index']}: {status}")
        """
        try:
            if not device_name:
                raise ServiceException(
                    detail="Device name is required",
                    code="invalid_params"
                )
            
            result = self._make_request(
                method='GET',
                endpoint='/check_all',
                params={'deviceName': device_name}
            )
            
            if result['success']:
                slots = result['data']
                self.log_info(f"Device {device_name} check_all successful: {len(slots)} total slots")
            else:
                self.log_warning(f"Failed to check_all for device {device_name}: {result['message']}")
            
            return result
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to check all slots for device {device_name}")
    
    def popup_powerbank(
        self, 
        device_name: str, 
        min_power: int = 20
    ) -> Dict[str, Any]:
        """
        Pop out a powerbank from device with minimum battery level
        
        Args:
            device_name: Device identifier (e.g., "CG001")
            min_power: Minimum battery percentage required (default: 20)
        
        Returns:
            Dict with success status and powerbank serial number
            
        Example:
            result = service.popup_powerbank("CG001", min_power=30)
            if result['success']:
                sn = result['data']
                print(f"Popped powerbank: {sn}")
            else:
                print(f"Error: {result['message']}")
        """
        try:
            if not device_name:
                raise ServiceException(
                    detail="Device name is required",
                    code="invalid_params"
                )
            
            if not 0 <= min_power <= 100:
                raise ServiceException(
                    detail="min_power must be between 0 and 100",
                    code="invalid_params",
                    context={'min_power': min_power}
                )
            
            result = self._make_request(
                method='GET',
                endpoint='/popup_random',
                params={
                    'deviceName': device_name,
                    'minPower': min_power
                }
            )
            
            if result['success']:
                powerbank_sn = result['data']
                self.log_info(f"Successfully popped powerbank {powerbank_sn} from {device_name}")
            else:
                self.log_warning(f"Failed to popup powerbank from {device_name}: {result['message']}")
            
            return result
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to popup powerbank from device {device_name}")
    
    def create_device(
        self, 
        device_name: str, 
        imei: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new device in the system
        
        Args:
            device_name: Device identifier (e.g., "CG001")
            imei: Device IMEI number (optional)
        
        Returns:
            Dict with success status and device credentials
            
        Example:
            result = service.create_device("CG001", imei="123456789012345")
            if result['success']:
                creds = result['data']
                print(f"Username: {creds['username']}")
                print(f"Password: {creds['password']}")
        """
        try:
            if not device_name:
                raise ServiceException(
                    detail="Device name is required",
                    code="invalid_params"
                )
            
            params = {'deviceName': device_name}
            if imei:
                params['imei'] = imei
            
            result = self._make_request(
                method='POST',
                endpoint='/device/create',
                params=params
            )
            
            if result['success']:
                self.log_info(f"Successfully created device {device_name}")
            else:
                self.log_warning(f"Failed to create device {device_name}: {result['message']}")
            
            return result
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, f"Failed to create device {device_name}")


# ==========================================
# SINGLETON INSTANCE
# ==========================================

_service_instance = None

def get_device_api_service() -> DeviceAPIService:
    """
    Get singleton instance of DeviceAPIService
    
    Usage:
        from api.user.stations.services import get_device_api_service
        
        service = get_device_api_service()
        result = service.check_device("CG001")
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = DeviceAPIService()
    return _service_instance
