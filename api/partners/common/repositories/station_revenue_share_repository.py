from typing import Optional
from django.db.models import QuerySet

from api.partners.common.models import StationRevenueShare


class StationRevenueShareRepository:
    """
    Repository for StationRevenueShare model database operations.
    """
    
    @staticmethod
    def get_by_id(share_id: str) -> Optional[StationRevenueShare]:
        """Get revenue share by ID"""
        try:
            return StationRevenueShare.objects.select_related(
                'distribution', 'distribution__partner', 'distribution__station'
            ).get(id=share_id)
        except StationRevenueShare.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_distribution_id(distribution_id: str) -> Optional[StationRevenueShare]:
        """Get revenue share by distribution ID"""
        try:
            return StationRevenueShare.objects.select_related(
                'distribution', 'distribution__partner', 'distribution__station'
            ).get(distribution_id=distribution_id)
        except StationRevenueShare.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_partner_id(partner_id: str) -> QuerySet:
        """Get all revenue shares for a partner"""
        return StationRevenueShare.objects.filter(
            distribution__partner_id=partner_id,
            distribution__is_active=True
        ).select_related('distribution', 'distribution__station')
    
    @staticmethod
    def get_by_station_id(station_id: str) -> Optional[StationRevenueShare]:
        """Get active revenue share for a station (vendor's revenue model)"""
        return StationRevenueShare.objects.filter(
            distribution__station_id=station_id,
            distribution__is_active=True
        ).select_related('distribution', 'distribution__partner').first()
    
    @staticmethod
    def create(
        distribution_id: str,
        revenue_model: str,
        partner_percent: Optional[float] = None,
        fixed_amount: Optional[float] = None
    ) -> StationRevenueShare:
        """Create a new station revenue share"""
        return StationRevenueShare.objects.create(
            distribution_id=distribution_id,
            revenue_model=revenue_model,
            partner_percent=partner_percent,
            fixed_amount=fixed_amount
        )
    
    @staticmethod
    def update(
        share_id: str,
        revenue_model: Optional[str] = None,
        partner_percent: Optional[float] = None,
        fixed_amount: Optional[float] = None
    ) -> Optional[StationRevenueShare]:
        """Update revenue share"""
        try:
            share = StationRevenueShare.objects.get(id=share_id)
            
            if revenue_model is not None:
                share.revenue_model = revenue_model
            if partner_percent is not None:
                share.partner_percent = partner_percent
            if fixed_amount is not None:
                share.fixed_amount = fixed_amount
            
            share.save()
            return share
        except StationRevenueShare.DoesNotExist:
            return None
    
    @staticmethod
    def delete_by_distribution_id(distribution_id: str) -> bool:
        """Delete revenue share by distribution ID"""
        deleted, _ = StationRevenueShare.objects.filter(
            distribution_id=distribution_id
        ).delete()
        return deleted > 0
    
    @staticmethod
    def delete_by_partner_id(partner_id: str) -> int:
        """Delete all revenue shares for a partner"""
        deleted, _ = StationRevenueShare.objects.filter(
            distribution__partner_id=partner_id
        ).delete()
        return deleted
