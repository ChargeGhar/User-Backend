"""
Authentication Client for Spring API
=====================================

Handles all authentication endpoints:
- POST /api/auth/login - User login
- POST /api/auth/logout - User logout  
- GET  /api/auth/me - Get current user
- POST /api/auth/validate - Validate token
- POST /api/auth/refresh - Refresh token
- GET  /api/auth/admins - Get all admins (SUPER_ADMIN only)
- POST /api/auth/admins - Create admin (SUPER_ADMIN only)

Source: com.demo.controller.AuthController

Auto-generated from Spring source code analysis
Date: 2026-01-10
"""
from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from .base import BaseClient
from .types import (
    HttpResult,
    LoginResponse,
    AdminUser,
    TokenInfo
)


logger = logging.getLogger(__name__)


class AuthClient(BaseClient):
    """
    Authentication operations client
    
    Endpoints from AuthController.java:
    - POST /api/auth/login
    - POST /api/auth/logout
    - GET  /api/auth/me
    - POST /api/auth/validate
    - POST /api/auth/refresh
    - GET  /api/auth/admins
    - POST /api/auth/admins
    """
    
    # ==========================================
    # LOGIN / LOGOUT
    # ==========================================
    
    def login(self, username: str, password: str) -> LoginResponse:
        """
        Authenticate user and get JWT token
        
        Endpoint: POST /api/auth/login
        
        Request body:
        {
            "username": "admin",
            "password": "password123"
        }
        
        Response (success):
        {
            "success": true,
            "message": "Login successful",
            "token": "eyJhbGciOiJIUzI1NiJ9...",
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "fullName": "Admin User",
                "role": "SUPER_ADMIN",
                "isActive": true,
                "createdAt": "2026-01-01T00:00:00",
                "updatedAt": "2026-01-01T00:00:00",
                "lastLogin": "2026-01-10T12:00:00"
            }
        }
        
        Response (failure):
        {
            "success": false,
            "message": "Invalid username or password",
            "token": null,
            "user": null
        }
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            LoginResponse with token and user info if successful
        """
        success, data = self._make_request(
            'POST',
            '/api/auth/login',
            data={'username': username, 'password': password}
        )
        
        response = LoginResponse.from_dict(data)
        
        # Store token if login successful
        if response.success and response.token:
            self.jwt_token = response.token
            logger.info(f"Login successful for user: {username}")
        else:
            logger.warning(f"Login failed for user: {username} - {response.message}")
        
        return response
    
    def logout(self) -> HttpResult:
        """
        Logout current user
        
        Endpoint: POST /api/auth/logout
        
        Response:
        {
            "code": 200,
            "data": "Logged out successfully",
            "msg": "ok",
            "time": 1704844800000
        }
        
        Returns:
            HttpResult indicating success/failure
        """
        result = self.post('/api/auth/logout')
        
        if result.success:
            # Clear stored token
            self._jwt_token = None
            self._token_expires_at = None
            logger.info("Logged out successfully")
        
        return result
    
    # ==========================================
    # USER INFO
    # ==========================================
    
    def get_current_user(self) -> HttpResult:
        """
        Get current authenticated user info
        
        Endpoint: GET /api/auth/me
        
        Response (success):
        {
            "code": 200,
            "data": {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "fullName": "Admin User",
                "role": "SUPER_ADMIN",
                "isActive": true,
                "createdAt": "2026-01-01T00:00:00",
                "updatedAt": "2026-01-01T00:00:00",
                "lastLogin": "2026-01-10T12:00:00"
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (with token refresh):
        {
            "code": 200,
            "data": {
                "user": { ... },
                "newToken": "eyJ...",
                "refreshed": true
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (not authenticated):
        {
            "code": 401,
            "data": null,
            "msg": "Not authenticated",
            "time": 1704844800000
        }
        
        Returns:
            HttpResult with user data or error
        """
        result = self.get('/api/auth/me')
        
        # Handle automatic token refresh
        if result.success and isinstance(result.data, dict):
            if result.data.get('refreshed') and result.data.get('newToken'):
                self.jwt_token = result.data['newToken']
                logger.info("Token refreshed automatically")
        
        return result
    
    def get_current_user_typed(self) -> Optional[AdminUser]:
        """
        Get current user as typed AdminUser object
        
        Returns:
            AdminUser if authenticated, None otherwise
        """
        result = self.get_current_user()
        
        if not result.success:
            return None
        
        if isinstance(result.data, dict):
            # Handle refreshed response format
            user_data = result.data.get('user', result.data)
            return AdminUser.from_dict(user_data)
        
        return None
    
    # ==========================================
    # TOKEN OPERATIONS
    # ==========================================
    
    def validate_token(self) -> HttpResult:
        """
        Validate current JWT token
        
        Endpoint: POST /api/auth/validate
        
        Response (valid):
        {
            "code": 200,
            "data": {
                "valid": true,
                "userId": 1,
                "username": "admin",
                "role": "SUPER_ADMIN"
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (invalid):
        {
            "code": 401,
            "data": null,
            "msg": "Invalid or expired token",
            "time": 1704844800000
        }
        
        Returns:
            HttpResult with token validation info
        """
        return self.post('/api/auth/validate')
    
    def validate_token_typed(self) -> TokenInfo:
        """
        Validate token and return typed TokenInfo
        
        Returns:
            TokenInfo with validation result
        """
        result = self.validate_token()
        
        if result.success and isinstance(result.data, dict):
            return TokenInfo.from_dict(result.data)
        
        return TokenInfo(valid=False)
    
    def refresh_token(self) -> HttpResult:
        """
        Refresh JWT token
        
        Endpoint: POST /api/auth/refresh
        
        Response (success):
        {
            "code": 200,
            "data": {
                "token": "eyJ...",
                "user": { ... }
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (failure):
        {
            "code": 401,
            "data": null,
            "msg": "Not authenticated",
            "time": 1704844800000
        }
        
        Returns:
            HttpResult with new token
        """
        result = self.post('/api/auth/refresh')
        
        if result.success and isinstance(result.data, dict):
            new_token = result.data.get('token')
            if new_token:
                self.jwt_token = new_token
                logger.info("Token refreshed successfully")
        
        return result
    
    # ==========================================
    # ADMIN MANAGEMENT (SUPER_ADMIN only)
    # ==========================================
    
    def get_all_admins(self) -> HttpResult:
        """
        Get list of all admin users
        
        Endpoint: GET /api/auth/admins
        
        Note: Requires SUPER_ADMIN role
        
        Response (success):
        {
            "code": 200,
            "data": [
                {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "fullName": "Admin User",
                    "role": "SUPER_ADMIN",
                    "isActive": true,
                    "createdAt": "2026-01-01T00:00:00"
                },
                ...
            ],
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (access denied):
        {
            "code": 403,
            "data": null,
            "msg": "Access denied. SUPER_ADMIN only.",
            "time": 1704844800000
        }
        
        Returns:
            HttpResult with list of admins
        """
        return self.get('/api/auth/admins')
    
    def get_all_admins_typed(self) -> List[AdminUser]:
        """
        Get all admins as typed list
        
        Returns:
            List of AdminUser objects
        """
        result = self.get_all_admins()
        
        if not result.success or not result.data:
            return []
        
        if isinstance(result.data, list):
            return [AdminUser.from_dict(item) for item in result.data]
        
        return []
    
    def create_admin(
        self,
        username: str,
        password: str,
        email: str,
        full_name: str,
        role: str = "ADMIN"
    ) -> HttpResult:
        """
        Create new admin user
        
        Endpoint: POST /api/auth/admins
        
        Note: Requires SUPER_ADMIN role
        
        Request body:
        {
            "username": "newadmin",
            "password": "password123",
            "email": "newadmin@example.com",
            "fullName": "New Admin",
            "role": "ADMIN"
        }
        
        Response (success):
        {
            "code": 200,
            "data": {
                "id": 2,
                "username": "newadmin",
                "email": "newadmin@example.com",
                "fullName": "New Admin",
                "role": "ADMIN",
                "isActive": true,
                "createdAt": "2026-01-10T12:00:00",
                "createdBy": 1
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (access denied):
        {
            "code": 403,
            "data": null,
            "msg": "Access denied. Only SUPER_ADMIN can create admins.",
            "time": 1704844800000
        }
        
        Args:
            username: New admin's username
            password: New admin's password
            email: New admin's email
            full_name: New admin's full name
            role: Role (ADMIN or SUPER_ADMIN, default: ADMIN)
            
        Returns:
            HttpResult with created admin data
        """
        return self.post(
            '/api/auth/admins',
            data={
                'username': username,
                'password': password,
                'email': email,
                'fullName': full_name,
                'role': role
            }
        )
