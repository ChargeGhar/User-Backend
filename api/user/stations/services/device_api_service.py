"""
Device API Service - Wrapper for chargeghar_client with business logic
========================================================================

Provides a clean interface for device communication via Spring API.
Handles popup operations, station checks, and transaction verification.

Usage:
    from api.user.stations.services.device_api_service import DeviceAPIService
    
    service = DeviceAPIService()
    success, powerbank_sn, message = service.popup_random('864601069946994')
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple, List, Any, Dict

from libs.chargeghar_client import get_client, PopupSnResult, TransactionLog, Powerbank

logger = logging.getLogger(__name__)


# Singleton instance
_device_api_service: Optional['DeviceAPIService'] = None


def get_device_api_service() -> 'DeviceAPIService':
    """Get singleton instance of DeviceAPIService"""
    global _device_api_service
    if _device_api_service is None:
        _device_api_service = DeviceAPIService()
    return _device_api_service


class DeviceAPIService:
    """
    Service for device communication via Spring API
    
    Wraps chargeghar_client with business logic and error handling.
    """
    
    def __init__(self):
        self.client = get_client()
    
    def popup_random(
        self, 
        station_sn: str, 
        min_power: int = 20
    ) -> Tuple[bool, Optional[str], str]:
        """
        Popup random available powerbank
        
        Args:
            station_sn: Station serial number (IMEI)
            min_power: Minimum battery percentage (default: 20)
        
        Returns:
            Tuple[success, powerbank_sn, message]
        """
        try:
            result = self.client.device.popup_random_typed(station_sn, min_power)
            if result:
                logger.info(f"Popup random success: station={station_sn}, powerbank={result}")
                return True, result, "Powerbank ejected successfully"
            else:
                logger.warning(f"Popup random failed: station={station_sn}")
                return False, None, "No available powerbank or device timeout"
        except Exception as e:
            logger.error(f"Popup random error: station={station_sn}, error={e}")
            return False, None, str(e)
    
    def popup_specific(
        self, 
        station_sn: str, 
        powerbank_sn: str
    ) -> Tuple[bool, Optional[PopupSnResult], str]:
        """
        Popup specific powerbank by SN
        
        Args:
            station_sn: Station serial number (IMEI)
            powerbank_sn: Powerbank SN to eject
        
        Returns:
            Tuple[success, result, message]
        """
        try:
            result = self.client.device.popup_sn_typed(station_sn, powerbank_sn)
            if result and result.success:
                logger.info(
                    f"Popup specific success: station={station_sn}, "
                    f"powerbank={powerbank_sn}, slot={result.slot}"
                )
                return True, result, "Powerbank ejected successfully"
            else:
                logger.warning(
                    f"Popup specific failed: station={station_sn}, powerbank={powerbank_sn}"
                )
                return False, result, "Popup failed - device timeout or powerbank not found"
        except Exception as e:
            logger.error(
                f"Popup specific error: station={station_sn}, "
                f"powerbank={powerbank_sn}, error={e}"
            )
            return False, None, str(e)
    
    def check_station(self, station_sn: str) -> Tuple[bool, List[Powerbank], str]:
        """
        Check station slot status
        
        Args:
            station_sn: Station serial number (IMEI)
        
        Returns:
            Tuple[success, powerbanks, message]
        """
        try:
            powerbanks = self.client.device.check_typed(station_sn)
            return True, powerbanks, "OK"
        except Exception as e:
            logger.error(f"Check station error: station={station_sn}, error={e}")
            return False, [], str(e)
    
    def check_station_all(self, station_sn: str) -> Tuple[bool, List[Powerbank], str]:
        """
        Check all station slots including empty ones
        
        Args:
            station_sn: Station serial number (IMEI)
        
        Returns:
            Tuple[success, powerbanks, message]
        """
        try:
            powerbanks = self.client.device.check_all_typed(station_sn)
            return True, powerbanks, "OK"
        except Exception as e:
            logger.error(f"Check station all error: station={station_sn}, error={e}")
            return False, [], str(e)

    def reboot_station(self, station_sn: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Reboot station device.

        Args:
            station_sn: Station serial number (IMEI)

        Returns:
            Tuple[success, response_data, message]
        """
        try:
            result = self.client.device.send_command(station_sn, '{"cmd":"reboot"}')
            response_data = self._http_result_to_dict(result)
            if result.success:
                logger.info(f"Reboot command sent: station={station_sn}")
                return True, response_data, result.msg or "Reboot command sent"
            logger.warning(
                f"Reboot command failed: station={station_sn}, code={result.code}, msg={result.msg}"
            )
            return False, response_data, result.msg or "Failed to send reboot command"
        except Exception as e:
            logger.error(f"Reboot error: station={station_sn}, error={e}")
            return False, None, str(e)

    def wifi_scan(self, station_sn: str) -> Tuple[bool, List[str], str]:
        """
        Scan station WiFi networks.

        Args:
            station_sn: Station serial number (IMEI)

        Returns:
            Tuple[success, network_names, message]
        """
        try:
            result = self.client.device.wifi_scan(station_sn)
            if not result.success:
                logger.warning(
                    f"WiFi scan failed: station={station_sn}, code={result.code}, msg={result.msg}"
                )
                return False, [], result.msg or "WiFi scan failed"

            networks: List[str] = []
            if isinstance(result.data, list):
                networks = [str(item) for item in result.data]
            logger.info(f"WiFi scan success: station={station_sn}, networks={len(networks)}")
            return True, networks, result.msg or "WiFi scan successful"
        except Exception as e:
            logger.error(f"WiFi scan error: station={station_sn}, error={e}")
            return False, [], str(e)

    def wifi_connect(
        self,
        station_sn: str,
        ssid: str,
        password: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Send WiFi connect command to station.

        Args:
            station_sn: Station serial number (IMEI)
            ssid: WiFi SSID
            password: WiFi password (optional)

        Returns:
            Tuple[success, response_data, message]
        """
        try:
            result = self.client.device.wifi_connect(station_sn, ssid, password)
            response_data = self._http_result_to_dict(result)
            if result.success:
                logger.info(f"WiFi connect command sent: station={station_sn}, ssid={ssid}")
                return True, response_data, result.msg or "WiFi connect command sent"
            logger.warning(
                f"WiFi connect failed: station={station_sn}, ssid={ssid}, "
                f"code={result.code}, msg={result.msg}"
            )
            return False, response_data, result.msg or "WiFi connect failed"
        except Exception as e:
            logger.error(f"WiFi connect error: station={station_sn}, ssid={ssid}, error={e}")
            return False, None, str(e)

    def set_volume(self, station_sn: str, volume: int) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Set station volume.

        Args:
            station_sn: Station serial number (IMEI)
            volume: Volume level 0-100

        Returns:
            Tuple[success, response_data, message]
        """
        try:
            result = self.client.device.set_volume(station_sn, volume)
            response_data = self._http_result_to_dict(result)
            if result.success:
                logger.info(f"Set volume success: station={station_sn}, volume={volume}")
                return True, response_data, result.msg or "Volume set successfully"
            logger.warning(
                f"Set volume failed: station={station_sn}, volume={volume}, "
                f"code={result.code}, msg={result.msg}"
            )
            return False, response_data, result.msg or "Failed to set volume"
        except Exception as e:
            logger.error(f"Set volume error: station={station_sn}, volume={volume}, error={e}")
            return False, None, str(e)

    def set_mode(self, station_sn: str, mode: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Set station network mode.

        Args:
            station_sn: Station serial number (IMEI)
            mode: Network mode ("wifi" or "4g")

        Returns:
            Tuple[success, response_data, message]
        """
        try:
            result = self.client.device.set_network_mode(station_sn, mode)
            response_data = self._http_result_to_dict(result)
            if result.success:
                logger.info(f"Set mode success: station={station_sn}, mode={mode}")
                return True, response_data, result.msg or "Mode set successfully"
            logger.warning(
                f"Set mode failed: station={station_sn}, mode={mode}, "
                f"code={result.code}, msg={result.msg}"
            )
            return False, response_data, result.msg or "Failed to set mode"
        except Exception as e:
            logger.error(f"Set mode error: station={station_sn}, mode={mode}, error={e}")
            return False, None, str(e)
    
    def verify_transaction(
        self, 
        station_sn: str, 
        message_id: str
    ) -> Optional[TransactionLog]:
        """
        Verify if a transaction completed (for timeout recovery)
        
        Args:
            station_sn: Station serial number (IMEI)
            message_id: Transaction message ID
        
        Returns:
            TransactionLog if found, None otherwise
        """
        try:
            return self.client.device.get_transaction_typed(station_sn, message_id)
        except Exception as e:
            logger.error(f"Verify transaction error: {e}")
            return None
    
    def get_recent_popups(
        self, 
        station_sn: str, 
        limit: int = 10
    ) -> List[TransactionLog]:
        """
        Get recent popup transactions for a station
        
        Args:
            station_sn: Station serial number (IMEI)
            limit: Number of logs to return
        
        Returns:
            List of TransactionLog objects for popup commands (0x31)
        """
        try:
            return self.client.device.get_logs_typed(station_sn, limit, cmd="0x31")
        except Exception as e:
            logger.error(f"Get recent popups error: {e}")
            return []
    
    def get_device_logs(
        self,
        station_sn: str,
        limit: int = 20,
        cmd: str = None
    ) -> List[TransactionLog]:
        """
        Get device transaction logs
        
        Args:
            station_sn: Station serial number (IMEI)
            limit: Number of logs to return
            cmd: Filter by command type
        
        Returns:
            List of TransactionLog objects
        """
        try:
            return self.client.device.get_logs_typed(station_sn, limit, cmd)
        except Exception as e:
            logger.error(f"Get device logs error: {e}")
            return []

    @staticmethod
    def _http_result_to_dict(result) -> Dict[str, Any]:
        """Normalize chargeghar_client HttpResult into a serializable dictionary."""
        return {
            'code': getattr(result, 'code', None),
            'msg': getattr(result, 'msg', ''),
            'time': getattr(result, 'time', 0),
            'data': getattr(result, 'data', None),
        }
