"""
Payment Intent Builder
======================

Builds payment intent and metadata for gateway payment.
"""
from decimal import Decimal
from typing import Optional, Dict, Any

from api.common.services.base import ServiceException


def build_intent_metadata(
    station_sn: str,
    package_id: str,
    powerbank_sn: Optional[str],
    actual_price: Decimal,
    discount,
    discount_amount: Decimal,
    rental_metadata: Dict,
    payment_model: str,
    payment_mode_requested: str,
    payment_mode_resume: str,
    wallet_amount: Optional[Decimal],
    points_to_use: Optional[int],
    topup_amount: Decimal,
    shortfall: Decimal,
    payment_options: Optional[Dict] = None,
    postpaid_min_balance: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    Build intent metadata for rental resume after payment.
    
    Args:
        station_sn: Station serial number
        package_id: Package ID
        powerbank_sn: Optional powerbank serial
        actual_price: Price after discount
        discount: Discount instance
        discount_amount: Discount amount
        rental_metadata: Rental metadata dict
        payment_model: PREPAID or POSTPAID
        payment_mode_requested: Originally requested mode
        payment_mode_resume: Mode to use after top-up
        wallet_amount: Wallet amount for split
        points_to_use: Points for split
        topup_amount: Gateway top-up amount
        shortfall: Actual shortfall
        payment_options: Payment calculation results
        postpaid_min_balance: POSTPAID minimum balance
        
    Returns:
        Intent metadata dict
    """
    from api.user.payments.services import RentalPaymentFlowService
    
    flow_service = RentalPaymentFlowService()
    
    metadata = {
        'flow': 'RENTAL_START',
        'station_sn': station_sn,
        'package_id': str(package_id),
        'powerbank_sn': powerbank_sn,
        'actual_price': str(actual_price),
        'discount_id': str(discount.id) if discount else None,
        'discount_amount': str(discount_amount),
        'discount_metadata': rental_metadata,
        'payment_model': payment_model,
        'payment_mode_requested': payment_mode_requested,
        'payment_mode': payment_mode_resume,
        'wallet_amount': str(wallet_amount) if wallet_amount is not None else None,
        'points_to_use': points_to_use,
        'topup_amount_required': str(topup_amount),
        'shortfall': str(shortfall)
    }
    
    if payment_options:
        metadata['payment_breakdown'] = flow_service.serialize_for_metadata(
            payment_options.get('payment_breakdown')
        )
        metadata['shortfall'] = str(payment_options.get('shortfall', shortfall))
    
    if postpaid_min_balance:
        metadata['postpaid_min_balance'] = str(postpaid_min_balance)
    
    return metadata


def create_payment_intent(
    user,
    payment_method_id: str,
    topup_amount: Decimal,
    metadata: Dict[str, Any]
):
    """
    Create payment intent via RentalPaymentFlowService.
    
    Args:
        user: User instance
        payment_method_id: Payment method ID
        topup_amount: Amount to top-up
        metadata: Intent metadata
        
    Returns:
        PaymentIntent instance
    """
    from api.user.payments.services import RentalPaymentFlowService
    
    flow_service = RentalPaymentFlowService()
    return flow_service.create_topup_intent(
        user=user,
        payment_method_id=payment_method_id,
        amount=topup_amount,
        metadata=metadata
    )


def raise_payment_required(
    user,
    payment_method_id: Optional[str],
    topup_amount: Decimal,
    station_sn: str,
    package_id: str,
    powerbank_sn: Optional[str],
    actual_price: Decimal,
    discount,
    discount_amount: Decimal,
    rental_metadata: Dict,
    payment_model: str,
    payment_mode_requested: str,
    payment_mode_resume: str,
    wallet_amount: Optional[Decimal],
    points_to_use: Optional[int],
    payment_options: Optional[Dict] = None,
    postpaid_min_balance: Optional[Decimal] = None
) -> None:
    """
    Create payment intent and raise payment_required exception.
    
    Args:
        user: User instance
        payment_method_id: Payment method ID
        topup_amount: Amount to top-up
        station_sn: Station serial number
        package_id: Package ID
        powerbank_sn: Optional powerbank serial
        actual_price: Price after discount
        discount: Discount instance
        discount_amount: Discount amount
        rental_metadata: Rental metadata
        payment_model: PREPAID or POSTPAID
        payment_mode_requested: Originally requested mode
        payment_mode_resume: Mode after top-up
        wallet_amount: Wallet amount for split
        points_to_use: Points for split
        payment_options: Payment calculation results
        postpaid_min_balance: POSTPAID minimum balance
        
    Raises:
        ServiceException: With code='payment_required' and status_code=402
    """
    from api.user.payments.services import RentalPaymentFlowService
    
    if not payment_method_id:
        raise ServiceException(
            detail="Payment method is required when balance is insufficient",
            code="payment_method_required",
            context={
                'payment_mode': payment_mode_requested,
                'shortfall': str(topup_amount)
            }
        )
    
    flow_service = RentalPaymentFlowService()
    
    # Resolve gateway minimum amount
    gateway_topup_amount = flow_service.resolve_gateway_topup_amount(
        payment_method_id=payment_method_id,
        requested_amount=topup_amount,
    )
    
    # Build metadata
    metadata = build_intent_metadata(
        station_sn=station_sn,
        package_id=package_id,
        powerbank_sn=powerbank_sn,
        actual_price=actual_price,
        discount=discount,
        discount_amount=discount_amount,
        rental_metadata=rental_metadata,
        payment_model=payment_model,
        payment_mode_requested=payment_mode_requested,
        payment_mode_resume=payment_mode_resume,
        wallet_amount=wallet_amount,
        points_to_use=points_to_use,
        topup_amount=gateway_topup_amount,
        shortfall=topup_amount,
        payment_options=payment_options,
        postpaid_min_balance=postpaid_min_balance
    )
    
    # Create intent
    intent = create_payment_intent(
        user=user,
        payment_method_id=payment_method_id,
        topup_amount=gateway_topup_amount,
        metadata=metadata
    )
    
    # Build context
    context = flow_service.build_payment_required_context(
        intent=intent,
        shortfall=topup_amount if not payment_options else payment_options.get('shortfall'),
        payment_mode=payment_mode_requested,
        payment_options=payment_options
    )
    
    # Raise exception
    raise ServiceException(
        detail="Payment required to start rental",
        code="payment_required",
        status_code=402,
        context=context
    )
