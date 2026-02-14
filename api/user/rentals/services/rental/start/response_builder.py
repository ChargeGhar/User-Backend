"""
Response Builder
================

Builds standardized response data structures for rental start.
"""
from decimal import Decimal
from typing import Dict, Any, Optional


def _extract_discount_info(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Support both legacy nested and current flat discount metadata shapes."""
    payload = metadata or {}
    discount_info = payload.get('discount')
    if isinstance(discount_info, dict) and discount_info:
        return discount_info

    nested = payload.get('discount_metadata', {})
    if isinstance(nested, dict):
        nested_discount = nested.get('discount', {})
        if isinstance(nested_discount, dict):
            return nested_discount

    return {}


def build_rental_success_data(rental) -> Dict[str, Any]:
    """
    Build success response data with nested structure.
    
    Args:
        rental: Rental instance
        
    Returns:
        Response data dict
    """
    metadata = rental.rental_metadata or {}
    
    # Extract discount info from metadata
    discount_info = _extract_discount_info(metadata)
    
    original_price = str(rental.package.price)
    discount_amount = str(discount_info.get('discount_amount', '0.00'))
    actual_price = str(discount_info.get('final_price', rental.package.price))
    
    return {
        'rental_id': str(rental.id),
        'rental_code': rental.rental_code,
        'status': rental.status,
        'user': {
            'id': str(rental.user.id),
            'username': rental.user.username
        },
        'station': {
            'id': str(rental.station.id),
            'serial_number': rental.station.serial_number,
            'name': rental.station.station_name
        },
        'power_bank': {
            'id': str(rental.power_bank.id) if rental.power_bank else None,
            'serial_number': rental.power_bank.serial_number if rental.power_bank else None,
            'battery_level': rental.power_bank.battery_level if rental.power_bank else None
        } if rental.power_bank else None,
        'package': {
            'id': str(rental.package.id),
            'name': rental.package.name,
            'duration_minutes': rental.package.duration_minutes,
            'price': str(rental.package.price),
            'payment_model': rental.package.payment_model
        },
        'pricing': {
            'original_price': original_price,
            'discount_amount': discount_amount,
            'actual_price': actual_price,
            'amount_paid': str(rental.amount_paid)
        },
        'payment': {
            'payment_model': rental.package.payment_model,
            'payment_mode': metadata.get('payment_mode'),
            'payment_status': rental.payment_status,
            'breakdown': build_payment_breakdown(rental),
            'pending_transaction_id': metadata.get('pending_transaction_id')
        },
        'timing': {
            'started_at': rental.started_at.isoformat() if rental.started_at else None,
            'due_at': rental.due_at.isoformat() if rental.due_at else None
        },
        'discount': build_discount_data(rental)
    }


def build_payment_breakdown(rental) -> Optional[Dict[str, Any]]:
    """
    Build payment breakdown from rental metadata.
    
    Args:
        rental: Rental instance
        
    Returns:
        Payment breakdown dict or None
    """
    if rental.package.payment_model == 'POSTPAID':
        return None
    
    metadata = rental.rental_metadata or {}
    payment_mode = metadata.get('payment_mode', 'wallet_points')
    
    # Try to get from transaction
    from api.user.payments.models import Transaction
    try:
        txn = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='SUCCESS'
        ).first()
        
        if txn and txn.gateway_response:
            breakdown = txn.gateway_response
            return {
                'wallet_amount': str(Decimal(str(breakdown.get('wallet_amount', '0.00'))).quantize(Decimal('0.01'))),
                'points_used': int(breakdown.get('points_used', 0) or 0),
                'points_amount': str(Decimal(str(breakdown.get('points_amount', '0.00'))).quantize(Decimal('0.01')))
            }
    except Exception:
        pass
    
    # Fallback: infer from payment mode
    if payment_mode == 'wallet':
        return {
            'wallet_amount': str(rental.amount_paid),
            'points_used': 0,
            'points_amount': '0.00'
        }
    elif payment_mode == 'points':
        return {
            'wallet_amount': '0.00',
            'points_used': int(float(rental.amount_paid) * 10),  # Rough estimate
            'points_amount': str(rental.amount_paid)
        }
    else:
        # wallet_points - try to extract from metadata
        wallet_amt = metadata.get('wallet_amount_requested', '0.00')
        points_used = metadata.get('points_to_use_requested', 0)
        points_amt = Decimal(str(rental.amount_paid)) - Decimal(str(wallet_amt))
        
        return {
            'wallet_amount': str(wallet_amt),
            'points_used': int(points_used),
            'points_amount': str(points_amt.quantize(Decimal('0.01')))
        }


def build_discount_data(rental) -> Optional[Dict[str, Any]]:
    """
    Build discount data from rental metadata.
    
    Args:
        rental: Rental instance
        
    Returns:
        Discount data dict or None
    """
    metadata = rental.rental_metadata or {}
    discount_info = _extract_discount_info(metadata)
    
    if not discount_info:
        return None
    
    return {
        'id': discount_info.get('discount_id') or discount_info.get('id'),
        'code': discount_info.get('code'),
        'discount_percent': str(discount_info.get('discount_percent', '0.00')),
        'discount_amount': str(discount_info.get('discount_amount', '0.00')),
        'description': discount_info.get('description', '')
    }
