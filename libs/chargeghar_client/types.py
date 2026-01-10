"""
Type definitions for Spring API responses
=========================================

These types match exactly the Java models in ChargeGhar_Devices:
- HttpResult: com.demo.common.HttpResult
- LoginResponse: com.demo.model.LoginResponse
- AdminUser: com.demo.model.AdminUser
- Powerbank: com.demo.message.Powerbank

Auto-generated from Spring source code analysis
Date: 2026-01-10
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict
from datetime import datetime
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class DeviceOnlineStatus(Enum):
    """Device online status from EMQX"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class UserRole(Enum):
    """Admin user roles"""
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class NetworkMode(Enum):
    """Device network mode"""
    WIFI = "wifi"
    FOURG = "4g"


# ==========================================
# RESPONSE TYPES
# ==========================================

@dataclass
class HttpResult:
    """
    Standard API response format
    
    Matches: com.demo.common.HttpResult
    
    Response format:
    {
        "code": 200,
        "type": 0,
        "data": <any>,
        "msg": "ok",
        "time": 1704844800000
    }
    """
    code: int = 200
    type: int = 0
    data: Optional[Any] = None
    msg: str = "ok"
    time: int = 0
    
    @property
    def success(self) -> bool:
        """Check if response is successful (code 200)"""
        return self.code == 200
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HttpResult':
        """Create HttpResult from API response dict"""
        return cls(
            code=data.get('code', 200),
            type=data.get('type', 0),
            data=data.get('data'),
            msg=data.get('msg', 'ok'),
            time=data.get('time', 0)
        )


@dataclass
class LoginResponse:
    """
    Login response format
    
    Matches: com.demo.model.LoginResponse
    
    Response format:
    {
        "success": true,
        "message": "Login successful",
        "token": "eyJ...",
        "user": { ... }
    }
    """
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional['AdminUser'] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoginResponse':
        """Create LoginResponse from API response dict"""
        user_data = data.get('user')
        user = AdminUser.from_dict(user_data) if user_data else None
        
        return cls(
            success=data.get('success', False),
            message=data.get('message', ''),
            token=data.get('token'),
            user=user
        )


@dataclass
class AdminUser:
    """
    Admin user model
    
    Matches: com.demo.model.AdminUser
    
    Response format:
    {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "fullName": "Admin User",
        "role": "SUPER_ADMIN",
        "isActive": true,
        "createdAt": "2026-01-01T00:00:00",
        "updatedAt": "2026-01-01T00:00:00",
        "lastLogin": "2026-01-10T12:00:00",
        "createdBy": null
    }
    """
    id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_by: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdminUser':
        """Create AdminUser from API response dict"""
        if not data:
            return cls()
        
        return cls(
            id=data.get('id'),
            username=data.get('username'),
            email=data.get('email'),
            full_name=data.get('fullName'),
            role=data.get('role'),
            is_active=data.get('isActive'),
            created_at=_parse_datetime(data.get('createdAt')),
            updated_at=_parse_datetime(data.get('updatedAt')),
            last_login=_parse_datetime(data.get('lastLogin')),
            created_by=data.get('createdBy')
        )


@dataclass
class Powerbank:
    """
    Powerbank slot data
    
    Matches: com.demo.message.Powerbank
    
    Response format (from /check, /check_all):
    {
        "index": 1,
        "pinboardIndex": 0,
        "status": 1,
        "power": 85,
        "temp": 25,
        "voltage": 4200,
        "current": 500,
        "snAsInt": 12345678,
        "snAsString": "12345678",
        "area": 357,
        "softVersion": 1,
        "hardVersion": 1,
        "message": "OK",
        "locked": false,
        "lockCount": 0,
        "putaway": true,
        "microSwitch": "0",
        "solenoidValveSwitch": "0"
    }
    """
    index: int = 0
    pinboard_index: int = 0
    status: int = 0
    power: int = 0
    temp: int = 0
    voltage: int = 0
    current: int = 0
    sn_as_int: int = 0
    sn_as_string: str = ""
    area: int = 0
    soft_version: int = 0
    hard_version: int = 0
    message: str = ""
    locked: bool = False
    lock_count: int = 0
    putaway: bool = False
    micro_switch: str = ""
    solenoid_valve_switch: str = ""
    battery_vol: int = 0
    
    @property
    def is_occupied(self) -> bool:
        """Check if slot has a powerbank"""
        return self.status > 0 and self.sn_as_int > 0
    
    @property
    def is_available(self) -> bool:
        """Check if powerbank is available for rental"""
        return self.is_occupied and self.message == "OK" and not self.locked
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Powerbank':
        """Create Powerbank from API response dict"""
        if not data:
            return cls()
        
        return cls(
            index=data.get('index', 0),
            pinboard_index=data.get('pinboardIndex', 0),
            status=data.get('status', 0),
            power=data.get('power', 0),
            temp=data.get('temp', 0),
            voltage=data.get('voltage', 0),
            current=data.get('current', 0),
            sn_as_int=data.get('snAsInt', 0),
            sn_as_string=data.get('snAsString', ''),
            area=data.get('area', 0),
            soft_version=data.get('softVersion', 0),
            hard_version=data.get('hardVersion', 0),
            message=data.get('message', ''),
            locked=data.get('locked', False),
            lock_count=data.get('lockCount', 0),
            putaway=data.get('putaway', False),
            micro_switch=data.get('microSwitch', ''),
            solenoid_valve_switch=data.get('solenoidValveSwitch', ''),
            battery_vol=data.get('batteryVol', 0)
        )


@dataclass
class DeviceCreateResult:
    """
    Device creation response
    
    Response from /device/create:
    {
        "deviceName": "864601069946994",
        "imei": "864601069946994",
        "password": "generated_password",
        "emqxRegistered": true,
        "username": "864601069946994",
        "host": "emqx.chargeghar.com",
        "port": 1883,
        "message": "Device created successfully"
    }
    """
    device_name: str = ""
    imei: Optional[str] = None
    password: str = ""
    emqx_registered: bool = False
    username: str = ""
    host: str = ""
    port: int = 1883
    message: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceCreateResult':
        """Create DeviceCreateResult from API response dict"""
        if not data:
            return cls()
        
        return cls(
            device_name=data.get('deviceName', ''),
            imei=data.get('imei'),
            password=data.get('password', ''),
            emqx_registered=data.get('emqxRegistered', False),
            username=data.get('username', ''),
            host=data.get('host', ''),
            port=data.get('port', 1883),
            message=data.get('message', '')
        )


@dataclass
class AdminStatistics:
    """
    Admin statistics response
    
    Response from /api/admin/statistics:
    {
        "totalDevices": 10,
        "onlineDevices": 5,
        "offlineDevices": 5,
        "totalAdmins": 3,
        "activeAdmins": 2,
        "systemStatus": "Online",
        "currentUser": 1,
        "currentUserRole": "SUPER_ADMIN"
    }
    """
    total_devices: int = 0
    online_devices: int = 0
    offline_devices: int = 0
    total_admins: int = 0
    active_admins: int = 0
    system_status: str = ""
    current_user: Optional[int] = None
    current_user_role: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdminStatistics':
        """Create AdminStatistics from API response dict"""
        if not data:
            return cls()
        
        return cls(
            total_devices=data.get('totalDevices', 0),
            online_devices=data.get('onlineDevices', 0),
            offline_devices=data.get('offlineDevices', 0),
            total_admins=data.get('totalAdmins', 0),
            active_admins=data.get('activeAdmins', 0),
            system_status=data.get('systemStatus', ''),
            current_user=data.get('currentUser'),
            current_user_role=data.get('currentUserRole')
        )


@dataclass 
class TokenInfo:
    """
    Token validation response
    
    Response from /api/auth/validate:
    {
        "valid": true,
        "userId": 1,
        "username": "admin",
        "role": "SUPER_ADMIN"
    }
    """
    valid: bool = False
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenInfo':
        """Create TokenInfo from API response dict"""
        if not data:
            return cls()
        
        return cls(
            valid=data.get('valid', False),
            user_id=data.get('userId'),
            username=data.get('username'),
            role=data.get('role')
        )


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from various formats"""
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        try:
            # ISO format
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        try:
            # Common format
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    
    if isinstance(value, (int, float)):
        # Unix timestamp (milliseconds)
        if value > 1e12:
            value = value / 1000
        return datetime.fromtimestamp(value)
    
    return None
