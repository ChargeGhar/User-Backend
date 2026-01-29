"""
Discount Service - Handle discount validation and application
"""
from decimal import Decimal
from typing import Optional, Tuple, Dict
from django.utils import timezone
from django.db import transaction

from api.common.services.base import BaseService
from api.user.promotions.models import StationPackageDiscount


class DiscountService(BaseService):
    """Service for handling station package discounts"""
    
    @staticmethod
    def calculate_discounted_price(
        original_price: Decimal,
        discount_percent: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate discount breakdown.
        
        Args:
            original_price: Original package price
            discount_percent: Discount percentage (0-100)
        
        Returns:
            Tuple of (discount_amount, final_price)
        """
        discount_amount = (original_price * discount_percent / Decimal('100')).quantize(Decimal('0.01'))
        final_price = original_price - discount_amount
        return discount_amount, final_price
    
    @staticmethod
    def get_applicable_discount(
        station_sn: str,
        package_id: str,
        user
    ) -> Optional[StationPackageDiscount]:
        """
        Get applicable discount for station-package-user combination.
        
        Args:
            station_sn: Station serial number
            package_id: Package ID
            user: User object
        
        Returns:
            StationPackageDiscount object if valid, None otherwise
        """
        now = timezone.now()
        
        try:
            discount = StationPackageDiscount.objects.select_related(
                'station', 'package'
            ).get(
                station__serial_number=station_sn,
                package_id=package_id,
                status='ACTIVE',
                valid_from__lte=now,
                valid_until__gte=now
            )
            
            # Check if user can use this discount
            if not discount.can_user_use(user):
                return None
            
            return discount
            
        except StationPackageDiscount.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_discounts_for_station(
        station_id: str,
        user
    ) -> Dict[str, StationPackageDiscount]:
        """
        Get all active discounts for a station that user can use.
        
        Args:
            station_id: Station ID
            user: User object
        
        Returns:
            Dictionary mapping package_id to discount object
        """
        now = timezone.now()
        
        discounts = StationPackageDiscount.objects.select_related(
            'station', 'package'
        ).filter(
            station_id=station_id,
            status='ACTIVE',
            valid_from__lte=now,
            valid_until__gte=now
        )
        
        # Filter by user eligibility
        discount_map = {}
        for discount in discounts:
            if discount.can_user_use(user):
                discount_map[str(discount.package_id)] = discount
        
        return discount_map
    
    @staticmethod
    def get_user_usage_count(discount_id: str, user_id: str) -> int:
        """
        Get user's usage count for a specific discount.
        
        Args:
            discount_id: Discount ID
            user_id: User ID
        
        Returns:
            Usage count
        """
        from api.user.rentals.models import Rental
        
        return Rental.objects.filter(
            user_id=user_id,
            rental_metadata__discount__discount_id=discount_id
        ).count()
    
    @staticmethod
    def get_total_usage_count(discount_id: str) -> int:
        """
        Get total usage count for a specific discount.
        
        Args:
            discount_id: Discount ID
        
        Returns:
            Total usage count
        """
        from api.user.rentals.models import Rental
        
        return Rental.objects.filter(
            rental_metadata__discount__discount_id=discount_id
        ).count()
    
    @staticmethod
    @transaction.atomic
    def apply_discount(
        discount: StationPackageDiscount,
        user,
        rental,
        package_price: Decimal
    ) -> Decimal:
        """
        Apply discount and record usage.
        Must be called within rental creation transaction.
        
        Args:
            discount: StationPackageDiscount object
            user: User object
            rental: Rental object
            package_price: Original package price
        
        Returns:
            Final price after discount
        """
        from django.db.models import F
        
        discount_amount, final_price = DiscountService.calculate_discounted_price(
            package_price, discount.discount_percent
        )
        
        # Update rental metadata
        if not rental.rental_metadata:
            rental.rental_metadata = {}
        
        rental.rental_metadata['discount'] = {
            'discount_id': str(discount.id),
            'original_price': str(package_price),
            'discount_percent': str(discount.discount_percent),
            'discount_amount': str(discount_amount),
            'final_price': str(final_price)
        }
        rental.save(update_fields=['rental_metadata'])
        
        # Increment usage count
        discount.current_usage_count = F('current_usage_count') + 1
        discount.save(update_fields=['current_usage_count'])
        
        return final_price
