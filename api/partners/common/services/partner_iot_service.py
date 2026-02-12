"""
PartnerIoTService - Common IoT operations for partners (franchise and vendor).

Business Rules:
- BR13.2: Vendor gets 1 free ejection per day
- IoT actions logged in PartnerIoTHistory
- Both franchise and vendor can perform IoT actions on their stations
"""

from datetime import date
from typing import Dict

from api.common.services.base import BaseService, ServiceException
from api.common.utils.helpers import paginate_queryset
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
            free_ejections_used = PartnerIotHistoryRepository.get_vendor_free_ejection_count_today(
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
            Dict with results and pagination metadata
        """
        start_date = self._parse_iso_date(filters.get('start_date'), 'start_date')
        end_date = self._parse_iso_date(filters.get('end_date'), 'end_date')

        if start_date and end_date and start_date > end_date:
            raise ServiceException(
                detail="start_date cannot be greater than end_date",
                code="INVALID_DATE_RANGE"
            )

        # Get history using repository
        history = PartnerIotHistoryRepository.get_by_partner(
            partner_id=str(partner.id),
            action_type=filters.get('action_type'),
            start_date=start_date,
            end_date=end_date
        )
        
        # Pagination
        page = filters.get('page', 1)
        page_size = filters.get('page_size', 20)
        
        return paginate_queryset(history, page, page_size)

    @staticmethod
    def _parse_iso_date(value, field_name: str):
        """Parse YYYY-MM-DD date values from query filters."""
        if not value:
            return None

        if isinstance(value, date):
            return value

        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise ServiceException(
                detail=f"Invalid {field_name}. Expected format: YYYY-MM-DD",
                code="INVALID_DATE_FORMAT"
            ) from exc
