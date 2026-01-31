"""
Admin IoT Monitoring Service
"""
from typing import Dict, Any
from datetime import date

from django.db.models import Count, Avg, Q

from api.common.utils.helpers import paginate_queryset
from api.internal.models import IotSyncLog, StationStatusHistory


class AdminIoTMonitoringService:
    """Service for admin IoT monitoring operations"""
    
    def get_iot_logs(self, log_type: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get IoT logs based on type.
        
        Args:
            log_type: 'sync' or 'history'
            filters: Filter parameters
            
        Returns:
            Paginated logs with summary
        """
        if log_type == 'sync':
            return self._get_sync_logs(filters)
        elif log_type == 'history':
            return self._get_status_history(filters)
        else:
            raise ValueError(f"Invalid log_type: {log_type}. Must be 'sync' or 'history'")
    
    def _get_sync_logs(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get IoT sync logs"""
        queryset = IotSyncLog.objects.select_related('station').all()
        
        # Apply filters
        if filters.get('station_id'):
            queryset = queryset.filter(station_id=filters['station_id'])
        
        if filters.get('sync_type'):
            queryset = queryset.filter(sync_type=filters['sync_type'])
        
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=filters['start_date'])
        
        if filters.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=filters['end_date'])
        
        # Calculate summary
        summary = queryset.aggregate(
            total_syncs=Count('id'),
            success_count=Count('id', filter=Q(status='SUCCESS')),
            failed_count=Count('id', filter=Q(status='FAILED')),
            avg_duration_ms=Avg('duration_ms')
        )
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated = paginate_queryset(queryset.order_by('-created_at'), page, page_size)
        
        # Format results
        paginated['results'] = [self._format_sync_log(log) for log in paginated['results']]
        paginated['summary'] = summary
        
        return paginated
    
    def _get_status_history(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get station status history"""
        queryset = StationStatusHistory.objects.select_related('station').all()
        
        # Apply filters
        if filters.get('station_id'):
            queryset = queryset.filter(station_id=filters['station_id'])
        
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('start_date'):
            queryset = queryset.filter(changed_at__date__gte=filters['start_date'])
        
        if filters.get('end_date'):
            queryset = queryset.filter(changed_at__date__lte=filters['end_date'])
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated = paginate_queryset(queryset, page, page_size)
        
        # Format results
        paginated['results'] = [self._format_status_history(history) for history in paginated['results']]
        
        return paginated
    
    def _format_sync_log(self, log: IotSyncLog) -> Dict[str, Any]:
        """Format sync log for response"""
        return {
            'id': str(log.id),
            'created_at': log.created_at.isoformat(),
            'station_sn': log.station.serial_number,
            'station_name': log.station.station_name,
            'device_uuid': log.device_uuid,
            'sync_type': log.sync_type,
            'direction': log.direction,
            'status': log.status,
            'error_message': log.error_message,
            'duration_ms': log.duration_ms,
        }
    
    def _format_status_history(self, history: StationStatusHistory) -> Dict[str, Any]:
        """Format status history for response"""
        return {
            'id': str(history.id),
            'changed_at': history.changed_at.isoformat(),
            'station_sn': history.station.serial_number,
            'station_name': history.station.station_name,
            'status': history.status,
            'previous_status': history.previous_status,
            'duration_seconds': history.duration_seconds,
            'triggered_by': history.triggered_by,
        }
