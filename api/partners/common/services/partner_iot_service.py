"""
PartnerIoTService - Common IoT operations for partners (franchise and vendor).

Business Rules:
- BR13.2: Vendor gets 1 free ejection per day
- IoT actions logged in PartnerIoTHistory
- Both franchise and vendor can perform IoT actions on their stations
"""

from typing import Dict

from api.common.services.base import BaseService, ServiceException
from api.partners.common.repositories import (
    StationDistributionRepository,
    PartnerIotHistoryRepository
)


class PartnerIoTService(BaseService):
    """Service for partner IoT operations"""
    
    def eject_powerbank(self, partner, data: Dict) -> Dict:
        """
        Eject powerbank from station.
        
        Args:
            partner: Partner object (franchise or vendor)
            data: Dict with slot_number, reason, ip_address, user_agent
            
        Returns:
            Dict with iot_history and free_ejections_remaining
            
        Raises:
            ServiceException: If validation fails or ejection fails
        """
        # Get assigned station
        distribution = StationDistributionRepository.get_active_by_partner(
            str(partner.id)
        ).filter(is_active=True).select_related('station').first()
        
        if not distribution:
            raise ServiceException(
                "No station assigned to this partner",
                code="no_station_assigned"
            )
        
        station = distribution.station
        
        # Check daily free ejection limit (only for vendors)
        is_free = False
        free_ejections_used = 0
        
        if partner.partner_type == 'VENDOR':
            free_ejections_used = PartnerIotHistoryRepository.get_today_free_ejections_count(
                str(partner.id)
            )
            is_free = free_ejections_used < 1
        
        # Get slot and powerbank
        from api.user.stations.models import Slot
        try:
            slot = Slot.objects.select_related('power_bank').get(
                station=station,
                slot_number=data['slot_number']
            )
        except Slot.DoesNotExist:
            raise ServiceException(
                f"Slot {data['slot_number']} not found",
                code="slot_not_found"
            )
        
        if not slot.power_bank:
            raise ServiceException(
                f"No powerbank in slot {data['slot_number']}",
                code="no_powerbank_in_slot"
            )
        
        powerbank = slot.power_bank
        
        # Call IoT service to eject
        from api.user.stations.services import PowerBankService
        iot_service = PowerBankService()
        
        try:
            result = iot_service.eject_powerbank(
                station=station,
                slot_number=data['slot_number']
            )
            
            # Create IoT history record
            history = PartnerIotHistoryRepository.create(
                partner_id=str(partner.id),
                performed_by_id=str(partner.user_id),
                station_id=str(station.id),
                action_type='EJECT',
                performed_from='DASHBOARD',
                powerbank_sn=powerbank.serial_number,
                slot_number=data['slot_number'],
                rental_id=None,
                is_free_ejection=is_free,
                is_successful=True,
                error_message=None,
                request_payload={'reason': data.get('reason', '')},
                response_data=result,
                ip_address=data.get('ip_address'),
                user_agent=data.get('user_agent')
            )
            
            self.log_info(
                f"Partner {partner.code} ejected powerbank {powerbank.serial_number} "
                f"from slot {data['slot_number']} (free={is_free})"
            )
            
            return {
                'iot_history': history,
                'free_ejections_remaining': max(0, 1 - (free_ejections_used + 1)) if partner.partner_type == 'VENDOR' else None
            }
            
        except Exception as e:
            # Create failed IoT history record
            history = PartnerIotHistoryRepository.create(
                partner_id=str(partner.id),
                performed_by_id=str(partner.user_id),
                station_id=str(station.id),
                action_type='EJECT',
                performed_from='DASHBOARD',
                powerbank_sn=powerbank.serial_number,
                slot_number=data['slot_number'],
                rental_id=None,
                is_free_ejection=is_free,
                is_successful=False,
                error_message=str(e),
                request_payload={'reason': data.get('reason', '')},
                response_data=None,
                ip_address=data.get('ip_address'),
                user_agent=data.get('user_agent')
            )
            
            self.log_error(
                f"Partner {partner.code} ejection failed: {str(e)}"
            )
            
            raise ServiceException(
                f"Ejection failed: {str(e)}",
                code="ejection_failed"
            )
    
    def get_iot_history(self, partner, filters: Dict) -> Dict:
        """
        Get IoT action history for partner.
        
        Args:
            partner: Partner object (franchise or vendor)
            filters: Dict with action_type, start_date, end_date, page, page_size
            
        Returns:
            Dict with count, next, previous, results
        """
        # Build filter dict
        query_filters = {
            'partner_id': str(partner.id)
        }
        
        if filters.get('action_type'):
            query_filters['action_type'] = filters['action_type']
        
        if filters.get('start_date'):
            query_filters['created_at__gte'] = filters['start_date']
        
        if filters.get('end_date'):
            query_filters['created_at__lte'] = filters['end_date']
        
        # Get history
        history = PartnerIotHistoryRepository.filter_history(query_filters)
        
        # Pagination
        from django.core.paginator import Paginator
        page_size = filters.get('page_size', 20)
        page = filters.get('page', 1)
        
        paginator = Paginator(history, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'count': paginator.count,
            'next': page_obj.has_next(),
            'previous': page_obj.has_previous(),
            'results': list(page_obj.object_list)
        }
