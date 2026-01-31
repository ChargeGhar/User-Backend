"""
Vendor Dashboard Service

Handles vendor dashboard statistics and data aggregation.
"""

from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from api.partners.common.repositories import (
    PartnerRepository,
    StationDistributionRepository,
    RevenueDistributionRepository,
    PayoutRequestRepository
)


class VendorDashboardService:
    """Service for vendor dashboard operations"""
    
    @staticmethod
    def get_dashboard_stats(vendor_id: str) -> dict:
        """
        Get vendor dashboard statistics
        
        BR2.3: Vendor has ONLY ONE station
        BR12.3: Filter revenue by vendor_id
        BR12.7: Show only own earnings
        """
        
        # Get vendor
        vendor = PartnerRepository.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("Vendor not found")
        
        if not vendor.is_revenue_vendor:
            raise PermissionDenied("Non-revenue vendors have no dashboard access")
        
        # Get vendor's single station (BR2.3)
        distribution = StationDistributionRepository.get_active_by_partner(vendor_id).first()
        
        if distribution:
            station = distribution.station
            station_info = {
                "id": str(station.id),
                "name": station.station_name,
                "code": station.serial_number
            }
        else:
            station_info = None
        
        # Get pending payout
        payout_summary = PayoutRequestRepository.get_summary_by_partner(vendor_id)
        pending_payout = payout_summary.get('pending_amount', Decimal('0'))
        
        # Get revenue stats
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        today_stats = RevenueDistributionRepository.get_summary_by_vendor(
            vendor_id=vendor_id,
            start_date=today,
            end_date=today
        )
        
        week_stats = RevenueDistributionRepository.get_summary_by_vendor(
            vendor_id=vendor_id,
            start_date=week_start,
            end_date=today
        )
        
        month_stats = RevenueDistributionRepository.get_summary_by_vendor(
            vendor_id=vendor_id,
            start_date=month_start,
            end_date=today
        )
        
        return {
            "balance": vendor.balance,
            "total_earnings": vendor.total_earnings,
            "pending_payout": pending_payout,
            "station": station_info,
            "today": {
                "transactions": today_stats.get('total_transactions', 0),
                "revenue": today_stats.get('total_net', Decimal('0')),
                "my_share": today_stats.get('total_vendor_share', Decimal('0'))
            },
            "this_week": {
                "transactions": week_stats.get('total_transactions', 0),
                "revenue": week_stats.get('total_net', Decimal('0')),
                "my_share": week_stats.get('total_vendor_share', Decimal('0'))
            },
            "this_month": {
                "transactions": month_stats.get('total_transactions', 0),
                "revenue": month_stats.get('total_net', Decimal('0')),
                "my_share": month_stats.get('total_vendor_share', Decimal('0'))
            }
        }
