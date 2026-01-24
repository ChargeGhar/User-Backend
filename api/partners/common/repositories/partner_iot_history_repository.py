from typing import Optional
from datetime import date
from django.db.models import QuerySet, Count
from django.utils import timezone

from api.partners.common.models import PartnerIotHistory


class PartnerIotHistoryRepository:
    """
    Repository for PartnerIotHistory model database operations.
    """
    
    @staticmethod
    def get_by_id(history_id: str) -> Optional[PartnerIotHistory]:
        """Get IoT history by ID"""
        try:
            return PartnerIotHistory.objects.select_related(
                'partner', 'performed_by', 'station', 'rental'
            ).get(id=history_id)
        except PartnerIotHistory.DoesNotExist:
            return None
    
    @staticmethod
    def create(
        partner_id: str,
        performed_by_id: int,
        station_id: str,
        action_type: str,
        performed_from: str,
        is_successful: bool,
        powerbank_sn: Optional[str] = None,
        slot_number: Optional[int] = None,
        rental_id: Optional[str] = None,
        is_free_ejection: bool = False,
        error_message: Optional[str] = None,
        request_payload: Optional[dict] = None,
        response_data: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> PartnerIotHistory:
        """Create a new IoT history record"""
        return PartnerIotHistory.objects.create(
            partner_id=partner_id,
            performed_by_id=performed_by_id,
            station_id=station_id,
            action_type=action_type,
            performed_from=performed_from,
            is_successful=is_successful,
            powerbank_sn=powerbank_sn,
            slot_number=slot_number,
            rental_id=rental_id,
            is_free_ejection=is_free_ejection,
            error_message=error_message,
            request_payload=request_payload or {},
            response_data=response_data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def check_vendor_free_ejection_available(partner_id: str) -> bool:
        """
        Check if vendor has free ejection available today.
        
        Returns True if vendor hasn't used their free ejection today.
        Returns False if already used.
        """
        today = timezone.now().date()
        
        used_today = PartnerIotHistory.objects.filter(
            partner_id=partner_id,
            action_type=PartnerIotHistory.ActionType.EJECT,
            is_free_ejection=True,
            created_at__date=today
        ).exists()
        
        return not used_today
    
    @staticmethod
    def get_vendor_free_ejection_count_today(partner_id: str) -> int:
        """Get the count of free ejections used today by vendor"""
        today = timezone.now().date()
        
        return PartnerIotHistory.objects.filter(
            partner_id=partner_id,
            action_type=PartnerIotHistory.ActionType.EJECT,
            is_free_ejection=True,
            created_at__date=today
        ).count()
    
    @staticmethod
    def get_by_partner(
        partner_id: str,
        action_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_successful: Optional[bool] = None
    ) -> QuerySet:
        """Get IoT history for a partner"""
        queryset = PartnerIotHistory.objects.filter(
            partner_id=partner_id
        ).select_related('station', 'performed_by')
        
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if is_successful is not None:
            queryset = queryset.filter(is_successful=is_successful)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_by_station(
        station_id: str,
        action_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> QuerySet:
        """Get IoT history for a station"""
        queryset = PartnerIotHistory.objects.filter(
            station_id=station_id
        ).select_related('partner', 'performed_by')
        
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_summary_by_partner(
        partner_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get IoT action summary for a partner"""
        queryset = PartnerIotHistory.objects.filter(partner_id=partner_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Group by action type
        summary = queryset.values('action_type').annotate(
            count=Count('id')
        )
        
        result = {
            'total_actions': queryset.count(),
            'successful_actions': queryset.filter(is_successful=True).count(),
            'failed_actions': queryset.filter(is_successful=False).count(),
            'by_action_type': {item['action_type']: item['count'] for item in summary}
        }
        
        return result
    
    @staticmethod
    def filter_history(
        partner_id: Optional[str] = None,
        station_id: Optional[str] = None,
        action_type: Optional[str] = None,
        performed_from: Optional[str] = None,
        is_successful: Optional[bool] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> QuerySet:
        """Filter IoT history with various criteria"""
        queryset = PartnerIotHistory.objects.select_related(
            'partner', 'station', 'performed_by'
        )
        
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if performed_from:
            queryset = queryset.filter(performed_from=performed_from)
        if is_successful is not None:
            queryset = queryset.filter(is_successful=is_successful)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.order_by('-created_at')
