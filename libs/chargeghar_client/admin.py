"""
Admin Management Client for Spring API
=======================================

Handles all admin/management endpoints:
- POST /device/create - Register new device
- GET  /device/delete - Delete device
- GET  /api/admin/statistics - Get admin dashboard statistics

Source: com.demo.controller.IndexController

Auto-generated from Spring source code analysis
Date: 2026-01-10
"""
from __future__ import annotations

import logging
from typing import Optional

from .base import BaseClient
from .types import HttpResult, DeviceCreateResult, AdminStatistics


logger = logging.getLogger(__name__)


class AdminClient(BaseClient):
    """
    Admin management operations client
    
    Endpoints from IndexController.java:
    - POST /device/create
    - GET  /device/delete
    - GET  /api/admin/statistics
    """
    
    # ==========================================
    # DEVICE MANAGEMENT
    # ==========================================
    
    def create_device(
        self,
        device_name: str,
        imei: Optional[str] = None
    ) -> HttpResult:
        """
        Register new device with EMQX platform
        
        Endpoint: POST /device/create
        
        Query params:
        - deviceName: Device identifier (required)
        - imei: Device IMEI number (optional)
        
        Response (success):
        {
            "code": 200,
            "data": {
                "deviceName": "864601069946994",
                "imei": "864601069946994",
                "password": "Abc123Xyz",
                "emqxRegistered": true,
                "username": "864601069946994",
                "host": "emqx.chargeghar.com",
                "port": 1883,
                "message": "Device created successfully and registered with EMQX platform"
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (already exists - updated):
        {
            "code": 200,
            "data": {
                "deviceName": "864601069946994",
                "imei": "864601069946994",
                "password": "Abc123Xyz",
                "emqxRegistered": true,
                "message": "Device created successfully and registered with EMQX platform"
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (error):
        {
            "code": 500,
            "data": null,
            "msg": "Device creation failed: ...",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (usually IMEI)
            imei: Device IMEI number (optional, defaults to device_name)
            
        Returns:
            HttpResult with device credentials
        """
        if not device_name or not device_name.strip():
            return HttpResult(
                code=400,
                msg="Device name cannot be empty"
            )
        
        params = {'deviceName': device_name}
        if imei:
            params['imei'] = imei
        
        return self.post('/device/create', params=params)
    
    def create_device_typed(
        self,
        device_name: str,
        imei: Optional[str] = None
    ) -> Optional[DeviceCreateResult]:
        """
        Create device and return typed result
        
        Args:
            device_name: Device identifier
            imei: Device IMEI number (optional)
            
        Returns:
            DeviceCreateResult if successful, None otherwise
        """
        result = self.create_device(device_name, imei)
        
        if result.success and isinstance(result.data, dict):
            return DeviceCreateResult.from_dict(result.data)
        
        return None
    
    def delete_device(self, device_name: str) -> HttpResult:
        """
        Delete device from system
        
        Endpoint: GET /device/delete
        
        Query params:
        - deviceName: Device identifier to delete
        
        Response (success):
        {
            "code": 200,
            "data": "Device deleted successfully",
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (not found):
        {
            "code": 500,
            "data": null,
            "msg": "Device not found: 864601069946994",
            "time": 1704844800000
        }
        
        Response (error):
        {
            "code": 500,
            "data": null,
            "msg": "Device deletion failed: ...",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier to delete
            
        Returns:
            HttpResult indicating success/failure
        """
        if not device_name or not device_name.strip():
            return HttpResult(
                code=400,
                msg="Device name cannot be empty"
            )
        
        return self.get('/device/delete', params={'deviceName': device_name})
    
    # ==========================================
    # STATISTICS
    # ==========================================
    
    def get_statistics(self) -> HttpResult:
        """
        Get admin dashboard statistics
        
        Endpoint: GET /api/admin/statistics
        
        Note: Requires authentication
        
        Response (success):
        {
            "code": 200,
            "data": {
                "totalDevices": 10,
                "onlineDevices": 5,
                "offlineDevices": 5,
                "totalAdmins": 3,
                "activeAdmins": 2,
                "systemStatus": "Online",
                "currentUser": 1,
                "currentUserRole": "SUPER_ADMIN"
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (not authenticated):
        {
            "code": 500,
            "data": null,
            "msg": "Authentication required",
            "time": 1704844800000
        }
        
        Returns:
            HttpResult with statistics data
        """
        return self.get('/api/admin/statistics')
    
    def get_statistics_typed(self) -> Optional[AdminStatistics]:
        """
        Get statistics as typed object
        
        Returns:
            AdminStatistics if successful, None otherwise
        """
        result = self.get_statistics()
        
        if result.success and isinstance(result.data, dict):
            return AdminStatistics.from_dict(result.data)
        
        return None
    
    # ==========================================
    # CONVENIENCE METHODS
    # ==========================================
    
    def get_device_count(self) -> int:
        """Get total number of devices"""
        stats = self.get_statistics_typed()
        return stats.total_devices if stats else 0
    
    def get_online_device_count(self) -> int:
        """Get number of online devices"""
        stats = self.get_statistics_typed()
        return stats.online_devices if stats else 0
    
    def is_system_online(self) -> bool:
        """Check if system is online"""
        stats = self.get_statistics_typed()
        return stats.system_status == "Online" if stats else False
