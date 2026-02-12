"""
Franchise Revenue Service

Service layer for franchise revenue operations.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Optional

from django.db.models import Sum, Count
from django.utils import timezone

from api.common.services.base import BaseService
from api.common.utils.helpers import paginate_queryset
from api.partners.common.models import Partner
from api.partners.common.repositories import RevenueDistributionRepository


class FranchiseRevenueService(BaseService):
    """Service for franchise revenue operations"""
    
    def get_revenue_list(self, franchise: Partner, filters: Dict) -> Dict:
        """
        Get franchise's revenue transactions.
        
        BR12.2: Only own stations' transactions
        """
        if not franchise.is_franchise:
            raise ValueError("Partner must be a Franchise")
        
        # Parse date range
        start_date, end_date = self._parse_date_range(
            filters.get('period'),
            filters.get('start_date'),
            filters.get('end_date')
        )
        
        # Get base queryset
        queryset = RevenueDistributionRepository.get_by_franchise(
            franchise_id=str(franchise.id),
            start_date=start_date,
            end_date=end_date
        ).filter(is_reversal=False)
        
        # Apply filters
        if filters.get('station_id'):
            queryset = queryset.filter(station_id=filters['station_id'])
        
        if filters.get('vendor_id'):
            queryset = queryset.filter(vendor_id=filters['vendor_id'])
        
        # Calculate summary
        summary = queryset.aggregate(
            total_transactions=Count('id'),
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            franchise_total_share=Sum('franchise_share')
        )
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated = paginate_queryset(queryset, page, page_size)
        
        # Build results
        results = []
        for rd in paginated['results']:
            results.append({
                'id': rd.id,
                'transaction_id': rd.transaction_id,
                'rental_id': rd.rental_id,
                'station': {
                    'id': rd.station.id,
                    'station_name': rd.station.station_name,
                    'serial_number': rd.station.serial_number,
                } if rd.station else None,
                'vendor': {
                    'id': rd.vendor.id,
                    'code': rd.vendor.code,
                    'business_name': rd.vendor.business_name,
                } if rd.vendor else None,
                'gross_amount': rd.gross_amount,
                'vat_amount': rd.vat_amount,
                'service_charge': rd.service_charge,
                'net_amount': rd.net_amount,
                'chargeghar_share': rd.chargeghar_share,
                'franchise_share': rd.franchise_share,
                'vendor_share': rd.vendor_share,
                'is_distributed': rd.is_distributed,
                'created_at': rd.created_at,
            })
        
        return {
            'results': results,
            'summary': {
                'total_transactions': summary['total_transactions'] or 0,
                'total_gross': summary['total_gross'] or Decimal('0'),
                'total_net': summary['total_net'] or Decimal('0'),
                'franchise_total_share': summary['franchise_total_share'] or Decimal('0'),
            },
            'pagination': paginated['pagination']
        }
    
    def _parse_date_range(
        self,
        period: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> tuple:
        """
        Parse date range from query filters.

        Behavior:
        - No date filters provided: return full history (no date bounds)
        - period filters: apply period window
        - custom period: requires start_date and end_date
        """
        today = timezone.now().date()
        
        if period == 'today':
            return today, today
        elif period == 'week':
            week_start = today - timedelta(days=today.weekday())
            return week_start, today
        elif period == 'month':
            month_start = today.replace(day=1)
            return month_start, today
        elif period == 'year':
            year_start = today.replace(month=1, day=1)
            return year_start, today
        elif period == 'custom' and start_date and end_date:
            return date.fromisoformat(start_date), date.fromisoformat(end_date)
        
        # No period/date filters => return full history
        return None, None
