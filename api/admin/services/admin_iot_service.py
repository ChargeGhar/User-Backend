"""
Admin IoT Service
"""

from typing import Dict, Any
from api.common.utils.helpers import paginate_queryset
from api.partners.common.repositories import PartnerIotHistoryRepository


class AdminIoTService:
    """Service for admin IoT operations"""
    
    def get_all_iot_history(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all IoT history across all partners.
        
        Args:
            filters: Dictionary containing filter parameters
            
        Returns:
            Paginated IoT history with essential auditable data
        """
        # Get filtered history with related data
        history = PartnerIotHistoryRepository.filter_history(
            partner_id=filters.get('partner_id'),
            station_id=filters.get('station_id'),
            action_type=filters.get('action_type'),
            performed_from=filters.get('performed_from'),
            is_successful=filters.get('is_successful'),
            start_date=filters.get('start_date'),
            end_date=filters.get('end_date')
        ).select_related('partner', 'station', 'performed_by')
        
        # Paginate results
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated = paginate_queryset(history, page, page_size)
        
        # Format results with essential auditable data
        paginated['results'] = [self._format_history_item(item) for item in paginated['results']]
        
        return paginated
    
    def _format_history_item(self, history) -> Dict[str, Any]:
        """Format history item with essential auditable data"""
        return {
            'id': str(history.id),
            'partner_code': history.partner.code,
            'partner_name': history.partner.business_name,
            'partner_type': history.partner.partner_type,
            'station_name': history.station.station_name,
            'station_sn': history.station.serial_number,
            'performed_by': history.performed_by.email,
            'action_type': history.action_type,
            'performed_from': history.performed_from,
            'powerbank_sn': history.powerbank_sn,
            'slot_number': history.slot_number,
            'is_free_ejection': history.is_free_ejection,
            'is_successful': history.is_successful,
            'error_message': history.error_message,
            'created_at': history.created_at.isoformat(),
        }
