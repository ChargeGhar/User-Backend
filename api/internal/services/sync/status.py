"""
Status update mixin - handles station status changes
"""
from __future__ import annotations

from typing import Dict, Any
import time
from django.utils import timezone
from django.db import transaction

from api.common.services.base import ServiceException
from api.user.stations.models import Station
from api.internal.services.iot_sync_log_service import IoTSyncLogService


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
        start_time = time.time()
        station = None
        log_status = 'SUCCESS'
        error_message = None
        result = {}
        
        try:
            self._validate_status_data(data)
            
            device_data = data.get('device', {})
            station_imei = self._resolve_station_imei(device_data)
            new_status = device_data.get('status')

            station = Station.objects.filter(imei=station_imei).first()
            
            if not station:
                raise ServiceException(
                    detail=f"Station with imei {station_imei} not found",
                    code="station_not_found"
                )
            
            # Validate status value
            if new_status not in self.STATION_STATUS_MAP:
                raise ServiceException(
                    detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(self.STATION_STATUS_MAP.keys())}",
                    code="invalid_status"
                )
            
            # Track status change BEFORE updating
            mapped_status = self.STATION_STATUS_MAP.get(new_status, 'OFFLINE')
            history = IoTSyncLogService.track_status_change(station, mapped_status, 'SYNC')
            
            # Update heartbeat and hardware info
            station.last_heartbeat = timezone.now()
            if device_data.get('hardware_info'):
                station.hardware_info.update(device_data['hardware_info'])
            station.save(update_fields=['last_heartbeat', 'hardware_info', 'updated_at'])
            
            result = {
                'station_id': str(station.id),
                'serial_number': station.serial_number,
                'status': station.status,
                'status_changed': history is not None,
                'last_heartbeat': station.last_heartbeat.isoformat(),
                'updated_at': timezone.now().isoformat()
            }
            
            self.log_info(f"Station {station_imei} status updated to {station.status}")
            return result
        
        except ServiceException as e:
            log_status = 'FAILED'
            error_message = str(e)
            raise
        except Exception as e:
            log_status = 'FAILED'
            error_message = str(e)
            identifier = data.get('device', {}).get('imei') or data.get('device', {}).get('serial_number', 'unknown')
            self.handle_service_error(e, f"Failed to update station status for {identifier}")
        finally:
            # Log sync operation
            if station:
                duration_ms = int((time.time() - start_time) * 1000)
                device_data = data.get('device', {})
                IoTSyncLogService.log_sync(
                    station=station,
                    device_uuid=device_data.get('imei', device_data.get('serial_number', 'unknown')),
                    sync_type='STATUS',
                    direction='INBOUND',
                    request_payload=data,
                    response_payload=result,
                    status=log_status,
                    error_message=error_message,
                    duration_ms=duration_ms
                )
