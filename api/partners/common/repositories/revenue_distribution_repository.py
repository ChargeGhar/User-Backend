from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from django.db.models import QuerySet, Sum, Count, Q
from django.utils import timezone

from api.partners.common.models import RevenueDistribution


class RevenueDistributionRepository:
    """
    Repository for RevenueDistribution model database operations.
    """
    
    @staticmethod
    def get_by_id(distribution_id: str) -> Optional[RevenueDistribution]:
        """Get revenue distribution by ID"""
        try:
            return RevenueDistribution.objects.select_related(
                'transaction', 'rental', 'station', 'franchise', 'vendor'
            ).get(id=distribution_id)
        except RevenueDistribution.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_transaction_id(transaction_id: str) -> Optional[RevenueDistribution]:
        """Get revenue distribution by transaction ID"""
        try:
            return RevenueDistribution.objects.select_related(
                'transaction', 'rental', 'station', 'franchise', 'vendor'
            ).get(transaction_id=transaction_id)
        except RevenueDistribution.DoesNotExist:
            return None
    
    @staticmethod
    def create(
        transaction_id: str,
        station_id: str,
        gross_amount: Decimal,
        vat_amount: Decimal,
        service_charge: Decimal,
        net_amount: Decimal,
        chargeghar_share: Decimal,
        rental_id: Optional[str] = None,
        franchise_id: Optional[str] = None,
        franchise_share: Decimal = Decimal('0'),
        vendor_id: Optional[str] = None,
        vendor_share: Decimal = Decimal('0'),
        is_reversal: bool = False,
        reversed_distribution_id: Optional[str] = None,
        reversal_reason: str = '',
        calculation_details: Optional[dict] = None
    ) -> RevenueDistribution:
        """Create a new revenue distribution"""
        return RevenueDistribution.objects.create(
            transaction_id=transaction_id,
            rental_id=rental_id,
            station_id=station_id,
            gross_amount=gross_amount,
            vat_amount=vat_amount,
            service_charge=service_charge,
            net_amount=net_amount,
            chargeghar_share=chargeghar_share,
            franchise_id=franchise_id,
            franchise_share=franchise_share,
            vendor_id=vendor_id,
            vendor_share=vendor_share,
            calculation_details=calculation_details or {},
            is_reversal=is_reversal,
            reversed_distribution_id=reversed_distribution_id,
            reversal_reason=reversal_reason
        )
    @staticmethod
    def mark_as_distributed(distribution_id: str) -> Optional[RevenueDistribution]:
        """Mark a distribution as distributed to partner balances"""
        try:
            dist = RevenueDistribution.objects.get(id=distribution_id)
            dist.is_distributed = True
            dist.distributed_at = timezone.now()
            dist.save(update_fields=['is_distributed', 'distributed_at', 'updated_at'])
            return dist
        except RevenueDistribution.DoesNotExist:
            return None
    
    @staticmethod
    def get_undistributed() -> QuerySet:
        """Get all undistributed revenue distributions"""
        return RevenueDistribution.objects.filter(
            is_distributed=False
        ).select_related('franchise', 'vendor')
    
    @staticmethod
    def get_by_franchise(
        franchise_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_distributed: Optional[bool] = None
    ) -> QuerySet:
        """Get revenue distributions for a franchise"""
        queryset = RevenueDistribution.objects.filter(
            franchise_id=franchise_id
        ).select_related('station', 'vendor')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if is_distributed is not None:
            queryset = queryset.filter(is_distributed=is_distributed)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_by_vendor(
        vendor_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_distributed: Optional[bool] = None
    ) -> QuerySet:
        """Get revenue distributions for a vendor"""
        queryset = RevenueDistribution.objects.filter(
            vendor_id=vendor_id
        ).select_related('station')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if is_distributed is not None:
            queryset = queryset.filter(is_distributed=is_distributed)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_by_station(
        station_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> QuerySet:
        """Get revenue distributions for a station"""
        queryset = RevenueDistribution.objects.filter(
            station_id=station_id
        ).select_related('franchise', 'vendor')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_summary_by_franchise(
        franchise_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get revenue summary for a franchise"""
        queryset = RevenueDistribution.objects.filter(franchise_id=franchise_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        result = queryset.aggregate(
            total_transactions=Count('id'),
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_franchise_share=Sum('franchise_share'),
            total_vendor_share=Sum('vendor_share'),
            total_chargeghar_share=Sum('chargeghar_share')
        )
        
        # Handle None values
        for key in result:
            if result[key] is None:
                result[key] = 0 if 'total' in key and 'transactions' not in key else 0
        
        return result
    
    @staticmethod
    def get_summary_by_vendor(
        vendor_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get revenue summary for a vendor"""
        queryset = RevenueDistribution.objects.filter(vendor_id=vendor_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        result = queryset.aggregate(
            total_transactions=Count('id'),
            total_gross=Sum('gross_amount'),
            total_net=Sum('net_amount'),
            total_vendor_share=Sum('vendor_share')
        )
        
        # Handle None values
        for key in result:
            if result[key] is None:
                result[key] = 0 if 'total' in key and 'transactions' not in key else 0
        
        return result
    
    @staticmethod
    def filter_distributions(
        station_id: Optional[str] = None,
        franchise_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        chargeghar_only: bool = False,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_distributed: Optional[bool] = None
    ) -> QuerySet:
        """
        Filter revenue distributions with various criteria.
        
        chargeghar_only: Returns transactions where franchise_id IS NULL AND vendor_id IS NULL
        """
        queryset = RevenueDistribution.objects.select_related(
            'station', 'franchise', 'vendor', 'transaction'
        )
        
        if chargeghar_only:
            queryset = queryset.filter(
                franchise__isnull=True,
                vendor__isnull=True
            )
        else:
            if station_id:
                queryset = queryset.filter(station_id=station_id)
            if franchise_id:
                queryset = queryset.filter(franchise_id=franchise_id)
            if vendor_id:
                queryset = queryset.filter(vendor_id=vendor_id)
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if is_distributed is not None:
            queryset = queryset.filter(is_distributed=is_distributed)
        
        return queryset.order_by('-created_at')
