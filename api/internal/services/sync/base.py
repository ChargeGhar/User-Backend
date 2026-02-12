"""
Base mixin with shared constants and validation helpers
"""
from __future__ import annotations

from typing import Dict, Any
from api.common.services.base import ServiceException


class StationSyncBaseMixin:
    """Base mixin with status mappings and validation helpers"""
    
    # Status mapping from IoT system to Django models
    SLOT_STATUS_MAP = {
        'AVAILABLE': 'AVAILABLE',
        'OCCUPIED': 'OCCUPIED',
        'ERROR': 'ERROR',
        'MAINTENANCE': 'MAINTENANCE'
    }
    
    POWERBANK_STATUS_MAP = {
        'AVAILABLE': 'AVAILABLE',
        'RENTED': 'RENTED',
        'MAINTENANCE': 'MAINTENANCE',
        'DAMAGED': 'DAMAGED'
    }
    
    STATION_STATUS_MAP = {
        'ONLINE': 'ONLINE',
        'OFFLINE': 'OFFLINE',
        'MAINTENANCE': 'MAINTENANCE'
    }

    def _resolve_station_imei(self, device_data: Dict[str, Any]) -> str:
        """
        Canonical station identifier for sync operations.
        IoT payload should provide IMEI; fallback to serial_number only if needed.
        """
        imei = str(device_data.get('imei') or device_data.get('serial_number') or '').strip()
        if not imei:
            raise ServiceException(
                detail="Missing device identifier (imei or serial_number)",
                code="missing_device_identifier"
            )
        return imei

    def _validate_sync_data(self, data: Dict[str, Any]) -> None:
        """Validate sync data structure"""
        if not isinstance(data, dict):
            raise ServiceException(detail="Data must be a dictionary", code="invalid_data_format")

        device_data = data.get('device', {})
        self._resolve_station_imei(device_data)

        slots_data = data.get('slots', [])
        if slots_data and not isinstance(slots_data, list):
            raise ServiceException(detail="Slots data must be a list", code="invalid_slots_format")
        
        powerbanks_data = data.get('power_banks', [])
        if powerbanks_data and not isinstance(powerbanks_data, list):
            raise ServiceException(detail="PowerBanks data must be a list", code="invalid_powerbanks_format")
    
    def _validate_return_data(self, data: Dict[str, Any]) -> None:
        """Validate return event data structure"""
        device_data = data.get('device', {})
        self._resolve_station_imei(device_data)
        return_event = data.get('return_event', {})

        required_fields = {
            'return_event.power_bank_serial': return_event.get('power_bank_serial'),
            'return_event.slot_number': return_event.get('slot_number')
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            raise ServiceException(
                detail=f"Missing required fields: {', '.join(missing_fields)}",
                code="missing_return_fields"
            )
    
    def _validate_status_data(self, data: Dict[str, Any]) -> None:
        """Validate status update data structure"""
        if not isinstance(data, dict):
            raise ServiceException(detail="Data must be a dictionary", code="invalid_data_format")

        device_data = data.get('device', {})
        self._resolve_station_imei(device_data)

        if not device_data.get('status'):
            raise ServiceException(detail="Missing device status", code="missing_status")
