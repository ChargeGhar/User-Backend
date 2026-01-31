"""
Rental Start - Revenue Module
=============================

Handles revenue distribution trigger for completed rental transactions.
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from api.user.rentals.models import Rental
    from api.user.payments.models import Transaction
    from api.partners.common.models import RevenueDistribution

logger = logging.getLogger(__name__)


def trigger_revenue_distribution(
    rental: 'Rental'
) -> Optional['RevenueDistribution']:
    """
    Trigger revenue distribution for a PREPAID rental after successful activation.
    
    Called after popup success, when the rental is confirmed ACTIVE and 
    payment transaction is SUCCESS.
    
    For POSTPAID rentals, revenue distribution is triggered in
    rental_payment.py after pay_rental_due() succeeds.
    
    Args:
        rental: The activated rental
    
    Returns:
        RevenueDistribution record if created, None otherwise
    """
    try:
        from api.user.payments.models import Transaction
        from api.partners.common.services import RevenueDistributionService
        
        # Find the RENTAL transaction for this rental
        transaction = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='SUCCESS'
        ).first()
        
        if not transaction:
            logger.warning(
                f"No SUCCESS transaction found for rental {rental.rental_code}, "
                f"skipping revenue distribution"
            )
            return None
        
        rev_service = RevenueDistributionService()
        distribution = rev_service.create_revenue_distribution(transaction, rental)
        
        if distribution:
            logger.info(
                f"Revenue distribution created for PREPAID rental {rental.rental_code}: "
                f"distribution_id={distribution.id}"
            )
        
        return distribution
        
    except Exception as e:
        # Log but don't fail the rental - revenue distribution can be recalculated
        logger.warning(
            f"Failed to create revenue distribution for {rental.rental_code}: {str(e)}"
        )
        return None
