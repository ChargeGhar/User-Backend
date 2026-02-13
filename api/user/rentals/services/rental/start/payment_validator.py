"""
Payment Validation Logic
========================

Validates payment requirements and determines if gateway payment is needed.
"""
from decimal import Decimal
from typing import Optional, Tuple, Dict

from api.common.services.base import ServiceException


def validate_payment_mode(payment_mode: str, payment_model: str) -> None:
    """
    Validate payment mode is supported for payment model.
    
    Args:
        payment_mode: wallet, points, wallet_points, direct
        payment_model: PREPAID or POSTPAID
        
    Raises:
        ServiceException: If payment mode not supported
    """
    if payment_model == 'POSTPAID' and payment_mode in {'points', 'wallet_points'}:
        raise ServiceException(
            detail=f"Payment mode '{payment_mode}' is not supported for POSTPAID packages",
            code="payment_mode_not_supported",
            context={
                'payment_mode': payment_mode,
                'payment_model': payment_model,
                'supported_modes': ['wallet', 'direct']
            }
        )


def check_prepaid_sufficiency(
    user,
    actual_price: Decimal,
    payment_mode: str,
    package_id: str,
    wallet_amount: Optional[Decimal] = None,
    points_to_use: Optional[int] = None
) -> Tuple[bool, Dict]:
    """
    Check if user has sufficient balance for PREPAID payment.
    
    Args:
        user: User instance
        actual_price: Price after discount
        payment_mode: Payment mode
        package_id: Package ID
        wallet_amount: Optional wallet amount for split
        points_to_use: Optional points for split
        
    Returns:
        Tuple of (is_sufficient, payment_options)
    """
    from api.user.payments.services import RentalPaymentFlowService
    
    flow_service = RentalPaymentFlowService()
    payment_options = flow_service.calculate_payment_options(
        user=user,
        scenario='pre_payment',
        package_id=package_id,
        amount=actual_price,
        payment_mode=payment_mode,
        wallet_amount=wallet_amount,
        points_to_use=points_to_use,
    )
    
    return payment_options['is_sufficient'], payment_options


def check_postpaid_minimum(user) -> Tuple[bool, Decimal, Decimal]:
    """
    Check if user meets POSTPAID minimum balance requirement.
    
    Args:
        user: User instance
        
    Returns:
        Tuple of (meets_minimum, min_balance, current_balance)
    """
    from api.user.system.services import AppConfigService
    
    min_balance = Decimal(
        str(AppConfigService().get_config_cached('POSTPAID_MINIMUM_BALANCE', '50'))
    )
    wallet_balance = (
        user.wallet.balance if hasattr(user, 'wallet') and user.wallet else Decimal('0')
    )
    
    meets_minimum = wallet_balance >= min_balance
    return meets_minimum, min_balance, wallet_balance


def resolve_resume_mode(requested_mode: str, points_short: bool) -> str:
    """
    Determine payment mode after gateway top-up.
    
    Args:
        requested_mode: Originally requested payment mode
        points_short: Whether points are insufficient
        
    Returns:
        Resume mode for rental continuation
    """
    if requested_mode == 'direct':
        return 'wallet'
    elif requested_mode == 'points' and points_short:
        return 'wallet'  # Points can't be bought
    elif requested_mode == 'wallet_points' and points_short:
        return 'wallet_points'  # Keep mode but clear split
    else:
        return requested_mode


def resolve_resume_preferences(
    payment_mode: str,
    wallet_amount: Optional[Decimal],
    points_to_use: Optional[int],
    payment_options: Dict
) -> Tuple[str, Optional[Decimal], Optional[int]]:
    """
    Build deterministic resume preferences for async rental continuation.
    
    Args:
        payment_mode: Selected payment mode
        wallet_amount: Requested wallet amount
        points_to_use: Requested points
        payment_options: Payment calculation results
        
    Returns:
        Tuple of (resume_mode, resume_wallet, resume_points)
    """
    points_shortfall = int(payment_options.get('points_shortfall', 0) or 0)
    points_short = points_shortfall > 0
    
    resume_mode = resolve_resume_mode(payment_mode, points_short)
    resume_wallet = wallet_amount
    resume_points = points_to_use
    
    # Clear requested split if points are short (gateway can't add points)
    if payment_mode == 'wallet_points' and points_short:
        if wallet_amount is not None and points_to_use is not None:
            resume_wallet = None
            resume_points = None
    
    return resume_mode, resume_wallet, resume_points
