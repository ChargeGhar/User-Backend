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
        Get vendor dashboard statistics.

        BR2.3: Vendor can have MULTIPLE stations (updated from one-to-one)
        BR12.3: Filter revenue by vendor_id
        BR12.7: Show only own earnings
        """

        # Get vendor
        vendor = PartnerRepository.get_by_id(vendor_id)
        if not vendor:
            raise ValueError("Vendor not found")

        if not vendor.is_revenue_vendor:
            raise PermissionDenied("Non-revenue vendors have no dashboard access")

        # Get all vendor stations (updated for multi-station support)
        distributions = StationDistributionRepository.get_active_by_partner(vendor_id)

        stations = []
        for distribution in distributions:
            station = distribution.station
            stations.append({
                "id": str(station.id),
                "name": station.station_name,
                "code": station.serial_number,
                "status": station.status,
                "distribution_id": str(distribution.id)
            })

        # Get pending payout
        payout_summary = PayoutRequestRepository.get_summary_by_partner(vendor_id)
        pending_payout = payout_summary.get('pending_amount', Decimal('0'))

        # Get revenue stats (already aggregates across all vendor stations by vendor_id)
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
            "stations": stations,
            "station_count": len(stations),
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
