"""
Reusable IoT Sync Logging Service
"""
from typing import Dict, Any, Optional
from django.utils import timezone

from api.internal.models import IotSyncLog, StationStatusHistory
from api.user.stations.models import Station


class IoTSyncLogService:
    """Reusable service for logging IoT sync operations"""
    
    @staticmethod
    def log_sync(
        station: Station,
        device_uuid: str,
        sync_type: str,
        direction: str,
        request_payload: Dict[str, Any],
        response_payload: Dict[str, Any],
        status: str,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> IotSyncLog:
        """
        Log an IoT sync operation.
        
        Args:
            station: Station instance
            device_uuid: Device IMEI or serial number
            sync_type: 'STATUS', 'FULL', or 'RETURNED'
            direction: 'INBOUND' or 'OUTBOUND'
            request_payload: Request data
            response_payload: Response data
            status: 'SUCCESS', 'FAILED', or 'TIMEOUT'
            error_message: Error message if failed
            duration_ms: Request duration in milliseconds
            
        Returns:
            Created IotSyncLog instance
        """
        return IotSyncLog.objects.create(
            station=station,
            device_uuid=device_uuid,
            sync_type=sync_type,
            direction=direction,
            request_payload=request_payload,
            response_payload=response_payload,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )
    
    @staticmethod
    def track_status_change(
        station: Station,
        new_status: str,
        triggered_by: str
    ) -> Optional[StationStatusHistory]:
        """
        Track station status change.
        
        Args:
            station: Station instance
            new_status: New status ('ONLINE', 'OFFLINE', 'MAINTENANCE')
            triggered_by: What triggered the change ('SYNC', 'HEARTBEAT', 'MANUAL', 'TIMEOUT')
            
        Returns:
            Created StationStatusHistory instance if status changed, None otherwise
        """
        now = timezone.now()
        previous_status = station.status
        
        # Only log if status actually changed
        if previous_status == new_status:
            return None
        
        # Calculate duration in previous status
        last_change = StationStatusHistory.objects.filter(
            station=station
        ).order_by('-changed_at').first()
        
        duration = None
        if last_change:
            duration = int((now - last_change.changed_at).total_seconds())
        
        # Create history record
        history = StationStatusHistory.objects.create(
            station=station,
            status=new_status,
            previous_status=previous_status,
            changed_at=now,
            duration_seconds=duration,
            triggered_by=triggered_by
        )
        
        # Update station status
        station.status = new_status
        station.save(update_fields=['status', 'updated_at'])
        
        return history
