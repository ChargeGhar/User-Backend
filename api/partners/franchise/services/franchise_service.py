"""
Franchise Service

Service layer for franchise dashboard operations.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Dict

from django.db.models import Sum, Count
from django.utils import timezone

from api.common.services.base import BaseService
from api.partners.common.models import Partner, RevenueDistribution, PayoutRequest, StationDistribution


class FranchiseService(BaseService):
    """Service for Franchise dashboard operations"""
    
    def get_dashboard_stats(self, franchise: Partner) -> Dict:
        """
        Get aggregated dashboard statistics for franchise.
        
        Args:
            franchise: Partner object (must be FRANCHISE type)
            
        Returns:
            Dict with dashboard statistics
            
        Business Rules Implemented:
        - BR3.5: franchise.revenue_share_percent
        - BR7.1: franchise_share calculation
        - BR10.2: Only own data (filtered by franchise_id)
        - BR12.2: Only own transactions
        """
        # Validate partner type
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        # 1. Profile data
        profile_data = {
            'id': franchise.id,
            'code': franchise.code,
            'business_name': franchise.business_name,
            'status': franchise.status,
            'revenue_share_percent': franchise.revenue_share_percent,
        }
        
        # 2. Balance and earnings
        balance = franchise.balance
        total_earnings = franchise.total_earnings
        
        # 3. Vendors count (child partners)
        vendors_count = Partner.objects.filter(
            parent_id=franchise.id,
            partner_type=Partner.PartnerType.VENDOR
        ).count()
        
        # 4. Stations count (owned by franchise)
        stations_count = StationDistribution.objects.filter(
            partner_id=franchise.id,
            distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE,
            is_active=True
        ).count()
        
        # 5. Own pending payout (from ChargeGhar)
        pending_payout = PayoutRequest.objects.filter(
            partner_id=franchise.id,
            payout_type=PayoutRequest.PayoutType.CHARGEGHAR_TO_FRANCHISE,
            status=PayoutRequest.Status.PENDING
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # 6. Vendor payouts pending franchise approval
        vendor_payouts_pending = PayoutRequest.objects.filter(
            payout_type=PayoutRequest.PayoutType.FRANCHISE_TO_VENDOR,
            partner__parent_id=franchise.id,
            status=PayoutRequest.Status.PENDING
        ).aggregate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        vendor_payouts_count = vendor_payouts_pending['count'] or 0
        vendor_payouts_amount = vendor_payouts_pending['total'] or Decimal('0')
        
        # 7. Revenue aggregation for periods
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        month_start = today.replace(day=1)
        
        today_stats = self._get_period_stats(franchise.id, today, today)
        week_stats = self._get_period_stats(franchise.id, week_start, today)
        month_stats = self._get_period_stats(franchise.id, month_start, today)
        
        # Build response
        return {
            'profile': profile_data,
            'balance': balance,
            'total_earnings': total_earnings,
            'pending_payout': pending_payout,
            'stations_count': stations_count,
            'vendors_count': vendors_count,
            'vendor_payouts_pending': vendor_payouts_count,
            'vendor_payouts_amount': vendor_payouts_amount,
            'today': today_stats,
            'this_week': week_stats,
            'this_month': month_stats,
        }
    
    def _get_period_stats(self, franchise_id: str, start_date: date, end_date: date) -> Dict:
        """
        Get revenue statistics for a date range.
        
        Args:
            franchise_id: Franchise UUID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dict with transactions, gross_revenue, my_share
        """
        result = RevenueDistribution.objects.filter(
            franchise_id=franchise_id,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_reversal=False  # Exclude reversals per our decision
        ).aggregate(
            transactions=Count('id'),
            gross_revenue=Sum('gross_amount'),
            my_share=Sum('franchise_share')
        )
        
        # Handle None values
        return {
            'transactions': result['transactions'] or 0,
            'gross_revenue': result['gross_revenue'] or Decimal('0'),
            'my_share': result['my_share'] or Decimal('0'),
        }
