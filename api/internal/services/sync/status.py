"""
Status update mixin - handles station status changes
"""
from __future__ import annotations

from typing import Dict, Any
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from api.common.services.base import ServiceException
from api.user.stations.models import Station


class StatusUpdateMixin:
    """Mixin for processing station status updates"""
    
    @transaction.atomic
    def update_station_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update station status (online/offline/maintenance)
        
        Args:
            data: Status update payload from IoT system
            
        Returns:
            Summary of status update
        """
        try:
            self._validate_status_data(data)
            
            device_data = data.get('device', {})
            serial_number = device_data.get('serial_number')
            imei = device_data.get('imei')
            new_status = device_data.get('status')
            
            identifier = imei or serial_number
            if not identifier:
                raise ServiceException(
                    detail="Missing device identifier (imei or serial_number)",
                    code="missing_device_identifier"
                )
            
            # Check if identifier matches IMEI or serial_number field
            station = Station.objects.filter(
                Q(imei=identifier) | Q(serial_number=identifier)
            ).first()
            
            if not station:
                raise ServiceException(
                    detail=f"Station with identifier {identifier} not found",
                    code="station_not_found"
                )
            
            # Validate status value
            if new_status not in self.STATION_STATUS_MAP:
                raise ServiceException(
                    detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(self.STATION_STATUS_MAP.keys())}",
                    code="invalid_status"
                )
            
            # Update station status and heartbeat
            station.status = self.STATION_STATUS_MAP.get(new_status, 'OFFLINE')
            station.last_heartbeat = timezone.now()
            
            # Update hardware info if provided
            if device_data.get('hardware_info'):
                station.hardware_info.update(device_data['hardware_info'])
            
            station.save(update_fields=['status', 'last_heartbeat', 'hardware_info'])
            
            result = {
                'station_id': str(station.id),
                'serial_number': station.serial_number,
                'status': station.status,
                'last_heartbeat': station.last_heartbeat.isoformat(),
                'updated_at': timezone.now().isoformat()
            }
            
            self.log_info(f"Station {identifier} status updated to {station.status}")
            return result
        
        except ServiceException:
            raise
        except Exception as e:
            identifier = data.get('device', {}).get('imei') or data.get('device', {}).get('serial_number', 'unknown')
            self.handle_service_error(e, f"Failed to update station status for {identifier}")
