"""
Rental Start - Payment Module
=============================

Handles payment processing for rental start:
- PREPAID: Process payment before popup
- POSTPAID: Create pending transaction (future enhancement)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from api.common.services.base import ServiceException

if TYPE_CHECKING:
    from api.user.rentals.models import Rental, RentalPackage
    from api.user.payments.models import Transaction


def process_prepayment(
    user,
    package: 'RentalPackage',
    rental: Optional['Rental'] = None,
    amount: Optional[Decimal] = None,
    payment_mode: str = 'wallet_points',
    wallet_amount: Optional[Decimal] = None,
    points_to_use: Optional[int] = None
) -> 'Transaction':
    """
    Process pre-payment for PREPAID rental.
    
    Calculates payment options using wallet + points, then processes payment.
    
    Args:
        user: User making payment
        package: Rental package being purchased
        rental: The rental being paid for (optional, for linking)
        amount: Override amount (if discount applied), defaults to package.price
    
    Returns:
        Transaction object
    
    Raises:
        ServiceException if insufficient balance
    """
    from api.user.payments.services import PaymentCalculationService, RentalPaymentService
    
    payment_amount = amount if amount is not None else package.price
    
    calc_service = PaymentCalculationService()
    payment_options = calc_service.calculate_payment_options(
        user=user,
        scenario='pre_payment',
        package_id=str(package.id),
        amount=payment_amount,
        payment_mode=payment_mode,
        wallet_amount=wallet_amount,
        points_to_use=points_to_use
    )
    
    if not payment_options['is_sufficient']:
        raise ServiceException(
            detail=f"Insufficient balance. Need NPR {payment_options['shortfall']} more.",
            code="insufficient_balance"
        )
    
    breakdown = payment_options.get('payment_breakdown', {}) or {}
    # Normalize key names for RentalPaymentService
    normalized_breakdown = {
        'points_to_use': breakdown.get('points_to_use', breakdown.get('points_used', 0)),
        'points_amount': breakdown.get('points_amount', Decimal('0')),
        'wallet_amount': breakdown.get('wallet_amount', breakdown.get('wallet_used', Decimal('0')))
    }
    
    payment_service = RentalPaymentService()
    return payment_service.process_rental_payment(
        user=user,
        rental=rental,
        payment_breakdown=normalized_breakdown
    )


def create_postpaid_transaction(
    user,
    rental: 'Rental',
    amount: Decimal
) -> 'Transaction':
    """
    Create a PENDING transaction for POSTPAID rental.
    
    This tracks the rental from start. Transaction will be updated
    to SUCCESS when payment is collected at return.
    
    Args:
        user: User starting rental
        rental: The rental
        amount: Expected payment amount
    
    Returns:
        Transaction object with status=PENDING
    """
    from api.user.payments.models import Transaction
    from api.common.utils.helpers import generate_transaction_id
    
    transaction = Transaction.objects.create(
        user=user,
        related_rental=rental,
        transaction_id=generate_transaction_id(),
        transaction_type='RENTAL',
        amount=amount,
        status='PENDING',
        payment_method_type='WALLET',
        currency='NPR'
    )
    
    return transaction
