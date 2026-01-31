"""
Admin Revenue Service
"""

from typing import Dict, Any
from decimal import Decimal
from datetime import date

from django.db.models import Sum, Count

from api.common.utils.helpers import paginate_queryset
from api.partners.common.repositories import RevenueDistributionRepository


class AdminRevenueService:
    """Service for admin revenue operations"""
    
    def get_all_revenue(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all revenue distributions across entire platform.
        
        Args:
            filters: Dictionary containing filter parameters
            
        Returns:
            Paginated revenue distributions with summary
        """
        # Parse date filters
        start_date = self._parse_date(filters.get('start_date'))
        end_date = self._parse_date(filters.get('end_date'))
        
        # Parse boolean filters
        is_distributed = self._parse_bool(filters.get('is_distributed'))
        is_reversal = self._parse_bool(filters.get('is_reversal'))
        chargeghar_only = filters.get('chargeghar_only') == 'true'
        
        # Get filtered queryset
        queryset = RevenueDistributionRepository.filter_distributions(
            station_id=filters.get('station_id'),
            franchise_id=filters.get('franchise_id'),
            vendor_id=filters.get('vendor_id'),
            chargeghar_only=chargeghar_only,
            start_date=start_date,
            end_date=end_date,
            is_distributed=is_distributed
        ).select_related(
            'transaction__user',
            'rental',
            'station',
            'franchise',
            'vendor'
        )
        
        # Additional filters
        if filters.get('transaction_status'):
            queryset = queryset.filter(transaction__status=filters['transaction_status'])
        
        if is_reversal is not None:
            queryset = queryset.filter(is_reversal=is_reversal)
        
        # Calculate summary
        summary = queryset.aggregate(
            total_transactions=Count('id'),
            total_gross=Sum('gross_amount'),
            total_vat=Sum('vat_amount'),
            total_service_charge=Sum('service_charge'),
            total_net=Sum('net_amount'),
            total_chargeghar_share=Sum('chargeghar_share'),
            total_franchise_share=Sum('franchise_share'),
            total_vendor_share=Sum('vendor_share')
        )
        
        # Handle None values in summary
        for key in summary:
            if summary[key] is None:
                summary[key] = 0 if 'total_transactions' in key else Decimal('0')
        
        # Paginate
        page = int(filters.get('page', 1))
        page_size = int(filters.get('page_size', 20))
        paginated = paginate_queryset(queryset, page, page_size)
        
        # Format results
        paginated['results'] = [self._format_revenue_item(item) for item in paginated['results']]
        paginated['summary'] = summary
        
        return paginated
    
    def _format_revenue_item(self, rd) -> Dict[str, Any]:
        """Format single revenue distribution - flat structure"""
        return {
            # Revenue Distribution Core
            'id': str(rd.id),
            'created_at': rd.created_at.isoformat(),
            
            # Financial Breakdown
            'gross_amount': str(rd.gross_amount),
            'vat_amount': str(rd.vat_amount),
            'service_charge': str(rd.service_charge),
            'net_amount': str(rd.net_amount),
            'chargeghar_share': str(rd.chargeghar_share),
            'franchise_share': str(rd.franchise_share),
            'vendor_share': str(rd.vendor_share),
            
            # Distribution Status
            'is_distributed': rd.is_distributed,
            'distributed_at': rd.distributed_at.isoformat() if rd.distributed_at else None,
            
            # Transaction (Related)
            'transaction_id': rd.transaction.transaction_id,
            'transaction_status': rd.transaction.status,
            'payment_method': rd.transaction.payment_method_type,
            'user_email': rd.transaction.user.email if rd.transaction.user.email else None,
            
            # Rental (Related - nullable)
            'rental_code': rd.rental.rental_code if rd.rental else None,
            'rental_status': rd.rental.status if rd.rental else None,
            'started_at': rd.rental.started_at.isoformat() if rd.rental and rd.rental.started_at else None,
            'ended_at': rd.rental.ended_at.isoformat() if rd.rental and rd.rental.ended_at else None,
            
            # Station (Related)
            'station_name': rd.station.station_name,
            'station_sn': rd.station.serial_number,
            
            # Partners (Related - nullable)
            'franchise_code': rd.franchise.code if rd.franchise else None,
            'franchise_name': rd.franchise.business_name if rd.franchise else None,
            'vendor_code': rd.vendor.code if rd.vendor else None,
            'vendor_name': rd.vendor.business_name if rd.vendor else None,
            
            # Audit Trail
            'is_reversal': rd.is_reversal,
            'reversal_reason': rd.reversal_reason if rd.reversal_reason else None,
        }
    
    def _parse_date(self, date_str: str) -> date:
        """Parse date string to date object"""
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except (ValueError, AttributeError):
            return None
    
    def _parse_bool(self, value: str) -> bool:
        """Parse boolean string"""
        if value is None:
            return None
        return value.lower() in ('true', '1', 'yes')
