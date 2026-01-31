"""
Rental Start - Discount Module
==============================

Handles discount lookup and calculation for rental start.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from api.user.promotions.models import Discount
    from api.user.rentals.models import Rental

logger = logging.getLogger(__name__)


def get_applicable_discount(
    station_sn: str,
    package_id: str,
    user
) -> Tuple[Optional['Discount'], Decimal, Decimal]:
    """
    Get applicable discount for a rental.
    
    Args:
        station_sn: Station serial number
        package_id: Rental package ID
        user: User starting rental
    
    Returns:
        Tuple of (discount, discount_amount, final_price)
        If no discount, returns (None, 0, original_price)
    """
    try:
        from api.user.promotions.services import DiscountService
        from api.user.rentals.models import RentalPackage
        
        package = RentalPackage.objects.get(id=package_id)
        original_price = package.price
        
        discount = DiscountService.get_applicable_discount(station_sn, package_id, user)
        
        if discount:
            discount_amount, final_price = DiscountService.calculate_discounted_price(
                original_price, discount.discount_percent
            )
            logger.info(
                f"Discount applied: {discount.discount_percent}% off, "
                f"original: {original_price}, final: {final_price}"
            )
            return discount, discount_amount, final_price
        
        return None, Decimal('0'), original_price
        
    except Exception as e:
        logger.warning(f"Failed to check discount: {e}. Continuing with original price.")
        from api.user.rentals.models import RentalPackage
        package = RentalPackage.objects.get(id=package_id)
        return None, Decimal('0'), package.price


def build_discount_metadata(
    discount: Optional['Discount'],
    original_price: Decimal,
    discount_amount: Decimal,
    final_price: Decimal
) -> dict:
    """
    Build rental metadata for discount tracking.
    
    Returns:
        Dictionary to store in rental.rental_metadata
    """
    if not discount:
        return {}
    
    return {
        'discount': {
            'discount_id': str(discount.id),
            'original_price': str(original_price),
            'discount_percent': str(discount.discount_percent),
            'discount_amount': str(discount_amount),
            'final_price': str(final_price)
        }
    }


def record_discount_usage(
    discount: Optional['Discount'],
    user,
    rental: 'Rental',
    original_price: Decimal
) -> bool:
    """
    Record discount usage after successful rental activation.
    
    Args:
        discount: The applied discount
        user: User who used the discount
        rental: The completed rental
        original_price: Original price before discount
    
    Returns:
        True if recorded successfully, False otherwise
    """
    if not discount:
        return False
    
    try:
        from api.user.promotions.services import DiscountService
        DiscountService.apply_discount(discount, user, rental, original_price)
        logger.info(f"Discount usage recorded for rental {rental.rental_code}")
        return True
    except Exception as e:
        logger.warning(f"Failed to record discount usage: {e}")
        return False
