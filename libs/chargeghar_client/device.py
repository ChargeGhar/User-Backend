"""
Device Control Client for Spring API
=====================================

Handles all device control endpoints:
- GET /check - Check device status (occupied slots only)
- GET /check_all - Check all device slots
- GET /popup_random - Pop out powerbank by minimum power
- GET /send - Send raw command to device
- GET /api/device/wifi/scan - Scan WiFi networks
- GET /api/device/wifi/connect - Connect to WiFi
- GET /api/device/mode/set - Set network mode (wifi/4g)
- GET /api/device/volume/set - Set device volume

Source: com.demo.controller.ShowController, com.demo.controller.ApiController

Auto-generated from Spring source code analysis
Date: 2026-01-10
"""
from __future__ import annotations

import logging
from typing import Optional, List

from .base import BaseClient
from .types import HttpResult, Powerbank, NetworkMode, PopupSnResult, TransactionLog


logger = logging.getLogger(__name__)


class DeviceClient(BaseClient):
    """
    Device control operations client
    
    Endpoints from ShowController.java and ApiController.java:
    - GET /check
    - GET /check_all
    - GET /popup_random
    - GET /send
    - GET /api/device/wifi/scan
    - GET /api/device/wifi/connect
    - GET /api/device/mode/set
    - GET /api/device/volume/set
    """
    
    # ==========================================
    # DEVICE STATUS
    # ==========================================
    
    def check(self, device_name: str) -> HttpResult:
        """
        Check device status - returns occupied slots only
        
        Endpoint: GET /check
        
        Query params:
        - deviceName: Device identifier (IMEI)
        
        Response (success):
        {
            "code": 200,
            "data": [
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
                },
                ...
            ],
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (device offline):
        {
            "code": 500,
            "data": null,
            "msg": "Device is Offline",
            "time": 1704844800000
        }
        
        Response (timeout):
        {
            "code": 500,
            "data": null,
            "msg": "Request Time Out",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            
        Returns:
            HttpResult with list of occupied powerbank slots
        """
        return self.get('/check', params={'deviceName': device_name})
    
    def check_typed(self, device_name: str) -> List[Powerbank]:
        """
        Check device and return typed Powerbank list
        
        Args:
            device_name: Device identifier (IMEI)
            
        Returns:
            List of Powerbank objects for occupied slots
        """
        result = self.check(device_name)
        
        if not result.success or not result.data:
            return []
        
        if isinstance(result.data, list):
            return [Powerbank.from_dict(item) for item in result.data]
        
        return []
    
    def check_all(self, device_name: str) -> HttpResult:
        """
        Check all device slots including empty ones
        
        Endpoint: GET /check_all
        
        Query params:
        - deviceName: Device identifier (IMEI)
        
        Response (success):
        {
            "code": 200,
            "data": [
                {
                    "index": 1,
                    "status": 1,
                    "power": 85,
                    "snAsString": "12345678",
                    "message": "OK",
                    ...
                },
                {
                    "index": 2,
                    "status": 0,
                    "power": 0,
                    "snAsString": "0",
                    "message": "NONE",
                    ...
                },
                ...
            ],
            "msg": "ok",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            
        Returns:
            HttpResult with list of all powerbank slots
        """
        return self.get('/check_all', params={'deviceName': device_name})
    
    def check_all_typed(self, device_name: str) -> List[Powerbank]:
        """
        Check all slots and return typed Powerbank list
        
        Args:
            device_name: Device identifier (IMEI)
            
        Returns:
            List of Powerbank objects for all slots
        """
        result = self.check_all(device_name)
        
        if not result.success or not result.data:
            return []
        
        if isinstance(result.data, list):
            return [Powerbank.from_dict(item) for item in result.data]
        
        return []
    
    # ==========================================
    # POWERBANK OPERATIONS
    # ==========================================
    
    def popup_random(self, device_name: str, min_power: int = 20) -> HttpResult:
        """
        Pop out a powerbank with minimum battery level
        
        Endpoint: GET /popup_random
        
        Query params:
        - deviceName: Device identifier (IMEI)
        - minPower: Minimum battery percentage (0-100)
        
        Response (success):
        {
            "code": 200,
            "data": "12345678",  // Powerbank SN
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (no powerbank available):
        {
            "code": 500,
            "data": null,
            "msg": "NO Powerbank",
            "time": 1704844800000
        }
        
        Response (popup failed):
        {
            "code": 500,
            "data": null,
            "msg": "Popup Error:0x02...",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            min_power: Minimum battery percentage (default: 20)
            
        Returns:
            HttpResult with powerbank SN if successful
        """
        if not 0 <= min_power <= 100:
            return HttpResult(
                code=400,
                msg="min_power must be between 0 and 100"
            )
        
        return self.get('/popup_random', params={
            'deviceName': device_name,
            'minPower': min_power
        })
    
    def popup_random_typed(self, device_name: str, min_power: int = 20) -> Optional[str]:
        """
        Pop out powerbank and return SN string
        
        Args:
            device_name: Device identifier (IMEI)
            min_power: Minimum battery percentage (default: 20)
            
        Returns:
            Powerbank SN string if successful, None otherwise
        """
        result = self.popup_random(device_name, min_power)
        
        if result.success and result.data:
            return str(result.data)
        
        return None
    
    def popup_sn(self, device_name: str, powerbank_sn: str) -> HttpResult:
        """
        Pop out specific powerbank by SN (SYNC - 15s timeout on server)
        
        Endpoint: GET /popup_sn
        
        Query params:
        - rentboxSN: Device identifier (IMEI)
        - singleSN: Powerbank SN to eject
        
        Response (success):
        {
            "code": 200,
            "data": {
                "slot": 1,
                "powerbankSN": "40818048",
                "status": 1,
                "success": true
            },
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (failed):
        {
            "code": 500,
            "data": null,
            "msg": "Popup Error:...",
            "time": 1704844800000
        }
        
        Args:
            device_name: Station serial number (IMEI)
            powerbank_sn: Powerbank SN to eject
            
        Returns:
            HttpResult with popup result
        """
        return self.get(
            '/popup_sn',
            params={'rentboxSN': device_name, 'singleSN': powerbank_sn}
        )
    
    def popup_sn_typed(self, device_name: str, powerbank_sn: str) -> Optional[PopupSnResult]:
        """
        Pop out specific powerbank, returns typed result or None on failure
        
        Args:
            device_name: Station serial number (IMEI)
            powerbank_sn: Powerbank SN to eject
            
        Returns:
            PopupSnResult if successful, None otherwise
        """
        result = self.popup_sn(device_name, powerbank_sn)
        
        if result.success and result.data:
            return PopupSnResult.from_dict(result.data)
        
        return None
    
    # ==========================================
    # TRANSACTION LOGS
    # ==========================================
    
    def get_logs(self, device_name: str, limit: int = 20, cmd: str = None) -> HttpResult:
        """
        Get device transaction logs
        
        Endpoint: GET /api/device/{deviceName}/logs
        
        Query params:
        - limit: Number of logs to return (default: 20)
        - cmd: Filter by command type (e.g., '0x31' for popup)
        
        Response (success):
        {
            "code": 200,
            "data": [
                {
                    "messageId": "abc123",
                    "deviceName": "864601069946994",
                    "cmd": "0x31",
                    "raw": "...",
                    "parsed": {...},
                    "timestamp": 1704844800000
                },
                ...
            ],
            "msg": "ok",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            limit: Number of logs to return
            cmd: Filter by command type
            
        Returns:
            HttpResult with list of transaction logs
        """
        params = {'limit': limit}
        if cmd:
            params['cmd'] = cmd
        return self.get(f'/api/device/{device_name}/logs', params=params)
    
    def get_logs_typed(self, device_name: str, limit: int = 20, cmd: str = None) -> List[TransactionLog]:
        """
        Get device logs as typed list
        
        Args:
            device_name: Device identifier (IMEI)
            limit: Number of logs to return
            cmd: Filter by command type
            
        Returns:
            List of TransactionLog objects
        """
        result = self.get_logs(device_name, limit, cmd)
        
        if not result.success or not result.data:
            return []
        
        if isinstance(result.data, list):
            return [TransactionLog.from_dict(log) for log in result.data]
        
        return []
    
    def get_transaction(self, device_name: str, message_id: str) -> HttpResult:
        """
        Get specific transaction by message ID
        
        Endpoint: GET /api/device/{deviceName}/logs/{messageId}
        
        Args:
            device_name: Device identifier (IMEI)
            message_id: Transaction message ID
            
        Returns:
            HttpResult with transaction log
        """
        return self.get(f'/api/device/{device_name}/logs/{message_id}')
    
    def get_transaction_typed(self, device_name: str, message_id: str) -> Optional[TransactionLog]:
        """
        Get specific transaction as typed object
        
        Args:
            device_name: Device identifier (IMEI)
            message_id: Transaction message ID
            
        Returns:
            TransactionLog if found, None otherwise
        """
        result = self.get_transaction(device_name, message_id)
        
        if result.success and result.data:
            return TransactionLog.from_dict(result.data)
        
        return None
    
    # ==========================================
    # RAW COMMAND
    # ==========================================
    
    def send_command(self, device_name: str, command: str) -> HttpResult:
        """
        Send raw command to device via MQTT
        
        Endpoint: GET /send
        
        Query params:
        - deviceName: Device identifier (IMEI)
        - data: Raw command string (JSON format)
        
        Common commands:
        - '{"cmd":"check"}' - Check device status
        - '{"cmd":"check_all"}' - Check all slots
        - '{"cmd":"reboot"}' - Reboot device
        - '{"cmd":"getWifi"}' - Get WiFi list
        - '{"cmd":"setWifi","username":"SSID","password":"PASS"}' - Set WiFi
        - '{"cmd":"setMode","data":"wifi"}' - Set network mode
        - '{"cmd":"volume","data":"50"}' - Set volume
        
        Response (success):
        {
            "code": 200,
            "data": null,
            "msg": "ok",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            command: Raw command JSON string
            
        Returns:
            HttpResult indicating command was sent
        """
        return self.get('/send', params={
            'deviceName': device_name,
            'data': command
        })
    
    # ==========================================
    # WIFI OPERATIONS
    # ==========================================
    
    def wifi_scan(self, device_name: str) -> HttpResult:
        """
        Scan for available WiFi networks
        
        Endpoint: GET /api/device/wifi/scan
        
        Query params:
        - deviceName: Device identifier (IMEI)
        
        Response (success):
        {
            "code": 200,
            "data": ["WiFi_Network_1", "WiFi_Network_2", "..."],
            "msg": "ok",
            "time": 1704844800000
        }
        
        Response (timeout - device may not support WiFi):
        {
            "code": 500,
            "data": null,
            "msg": "Request Time Out",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            
        Returns:
            HttpResult with list of WiFi network names
        """
        return self.get('/api/device/wifi/scan', params={'deviceName': device_name})
    
    def wifi_scan_typed(self, device_name: str) -> List[str]:
        """
        Scan WiFi and return list of network names
        
        Args:
            device_name: Device identifier (IMEI)
            
        Returns:
            List of WiFi network names (SSIDs)
        """
        result = self.wifi_scan(device_name)
        
        if not result.success or not result.data:
            return []
        
        if isinstance(result.data, list):
            return [str(item) for item in result.data]
        
        return []
    
    def wifi_connect(
        self,
        device_name: str,
        ssid: str,
        password: Optional[str] = None
    ) -> HttpResult:
        """
        Connect device to WiFi network
        
        Endpoint: GET /api/device/wifi/connect
        
        Query params:
        - deviceName: Device identifier (IMEI)
        - ssid: WiFi network name
        - password: WiFi password (optional for open networks)
        
        Response (success):
        {
            "code": 200,
            "data": null,
            "msg": "WiFi configuration sent successfully",
            "time": 1704844800000
        }
        
        Response (device offline):
        {
            "code": 500,
            "data": null,
            "msg": "Device is Offline",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            ssid: WiFi network name (SSID)
            password: WiFi password (optional)
            
        Returns:
            HttpResult indicating command was sent
        """
        params = {
            'deviceName': device_name,
            'ssid': ssid
        }
        if password:
            params['password'] = password
        
        return self.get('/api/device/wifi/connect', params=params)
    
    # ==========================================
    # NETWORK MODE
    # ==========================================
    
    def set_network_mode(self, device_name: str, mode: str) -> HttpResult:
        """
        Set device network priority mode
        
        Endpoint: GET /api/device/mode/set
        
        Query params:
        - deviceName: Device identifier (IMEI)
        - mode: Network mode ("wifi" or "4g")
        
        Response (success):
        {
            "code": 200,
            "data": null,
            "msg": "Network mode set to: wifi",
            "time": 1704844800000
        }
        
        Response (invalid mode):
        {
            "code": 500,
            "data": null,
            "msg": "Mode must be 'wifi' or '4g'",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            mode: Network mode ("wifi" or "4g")
            
        Returns:
            HttpResult indicating mode was set
        """
        # Validate mode
        valid_modes = ['wifi', '4g']
        mode_lower = mode.lower()
        
        if mode_lower not in valid_modes:
            return HttpResult(
                code=400,
                msg=f"Mode must be 'wifi' or '4g', got: {mode}"
            )
        
        return self.get('/api/device/mode/set', params={
            'deviceName': device_name,
            'mode': mode_lower
        })
    
    def set_wifi_priority(self, device_name: str) -> HttpResult:
        """Set device to prioritize WiFi connection"""
        return self.set_network_mode(device_name, 'wifi')
    
    def set_4g_priority(self, device_name: str) -> HttpResult:
        """Set device to prioritize 4G connection"""
        return self.set_network_mode(device_name, '4g')
    
    # ==========================================
    # VOLUME
    # ==========================================
    
    def set_volume(self, device_name: str, volume: int) -> HttpResult:
        """
        Set device speaker volume
        
        Endpoint: GET /api/device/volume/set
        
        Query params:
        - deviceName: Device identifier (IMEI)
        - volume: Volume level (0-100)
        
        Response (success):
        {
            "code": 200,
            "data": null,
            "msg": "Volume set to: 50",
            "time": 1704844800000
        }
        
        Response (invalid volume):
        {
            "code": 500,
            "data": null,
            "msg": "Volume must be between 0 and 100",
            "time": 1704844800000
        }
        
        Args:
            device_name: Device identifier (IMEI)
            volume: Volume level 0-100
            
        Returns:
            HttpResult indicating volume was set
        """
        # Validate volume
        if not isinstance(volume, int) or not 0 <= volume <= 100:
            return HttpResult(
                code=400,
                msg="Volume must be an integer between 0 and 100"
            )
        
        return self.get('/api/device/volume/set', params={
            'deviceName': device_name,
            'volume': str(volume)
        })
    
    def mute(self, device_name: str) -> HttpResult:
        """Mute device (set volume to 0)"""
        return self.set_volume(device_name, 0)
    
    def max_volume(self, device_name: str) -> HttpResult:
        """Set device to maximum volume (100)"""
        return self.set_volume(device_name, 100)
