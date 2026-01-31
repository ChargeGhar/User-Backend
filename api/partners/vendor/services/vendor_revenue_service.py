"""
Vendor Revenue Service

Handles vendor revenue transaction listing and filtering.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Dict, Optional
from django.db.models import Count, Sum
from django.utils import timezone

from api.common.utils.helpers import paginate_queryset
from api.partners.common.repositories import RevenueDistributionRepository


class VendorRevenueService:
    """Service for vendor revenue operations"""
    
    @staticmethod
    def get_revenue_list(vendor_id: str, filters: Dict) -> Dict:
        """
        Get vendor's revenue transactions.
        
        Args:
            vendor_id: Vendor partner ID
            filters: Dict with period, start_date, end_date, page, page_size
            
        Returns:
            Dict with results, summary, count, page, page_size, total_pages
            
        Business Rules:
        - BR12.3: Only own transactions (vendor_id = vendor.id)
        - BR12.7: Show only vendor earnings
        """
        
        # Parse date range
        start_date, end_date = VendorRevenueService._parse_date_range(
            filters.get('period'),
            filters.get('start_date'),
            filters.get('end_date')
        )
        
        # Get base queryset
        queryset = RevenueDistributionRepository.get_by_vendor(
            vendor_id=vendor_id,
            start_date=start_date,
            end_date=end_date
        ).filter(is_reversal=False)
        
        # Add relations to avoid N+1 queries
        queryset = queryset.select_related('station', 'rental')
        
        # Calculate summary before pagination
        summary = queryset.aggregate(
            total_transactions=Count('id'),
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_vendor_share=Sum('vendor_share')
        )
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        
        paginated_data = paginate_queryset(queryset, page, page_size)
        
        # Build results
        results = []
        for rd in paginated_data['results']:
            # Calculate vendor_share_percent (not in model)
            if rd.net_amount and rd.net_amount > 0:
                vendor_share_percent = (rd.vendor_share / rd.net_amount) * 100
            else:
                vendor_share_percent = Decimal('0')
            
            results.append({
                'id': rd.id,
                'rental_id': rd.rental_id,
                'transaction_date': rd.created_at,
                'gross_revenue': rd.gross_amount,
                'net_revenue': rd.net_amount,
                'vat_amount': rd.vat_amount,
                'service_charge': rd.service_charge,
                'vendor_share': rd.vendor_share,
                'vendor_share_percent': vendor_share_percent,
                'station': {
                    'id': rd.station.id,
                    'name': rd.station.station_name,
                } if rd.station else None,
            })
        
        return {
            'results': results,
            'pagination': paginated_data['pagination'],
            'summary': {
                'total_transactions': summary['total_transactions'] or 0,
                'total_gross_revenue': summary['total_gross'] or Decimal('0'),
                'total_net_revenue': summary['total_net'] or Decimal('0'),
                'total_vendor_share': summary['total_vendor_share'] or Decimal('0'),
            }
        }
    
    @staticmethod
    def _parse_date_range(period: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> tuple:
        """Parse date range from period or custom dates"""
        today = timezone.now().date()
        
        if start_date and end_date:
            # Custom date range
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            return start, end
        
        # Period-based date range
        if period == 'today':
            return today, today
        elif period == 'week':
            week_start = today - timedelta(days=today.weekday())
            return week_start, today
        elif period == 'year':
            year_start = today.replace(month=1, day=1)
            return year_start, today
        else:  # Default to 'month'
            month_start = today.replace(day=1)
            return month_start, today
