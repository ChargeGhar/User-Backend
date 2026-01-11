"""
Type definitions for Payment Gateway Client
============================================

Provides type definitions for payment gateway operations:
- GatewayResult: Standardized result for all gateway operations
- PaymentInitiationResult: Result from payment initiation
- PaymentVerificationResult: Result from payment verification

Designed for use with nepal-gateways package.
Date: 2026-01-10
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from decimal import Decimal
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class GatewayType(Enum):
    """Supported payment gateways"""
    ESEWA = "esewa"
    KHALTI = "khalti"


class PaymentStatus(Enum):
    """Payment status codes"""
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class RedirectMethod(Enum):
    """HTTP redirect methods for gateway"""
    GET = "GET"
    POST = "POST"


# ==========================================
# RESULT TYPES
# ==========================================

@dataclass
class PaymentInitiationResult:
    """
    Result from payment initiation
    
    Attributes:
        success: Whether initiation was successful
        redirect_required: Whether redirect is needed
        redirect_url: URL to redirect user to
        redirect_method: HTTP method for redirect (GET/POST)
        form_fields: Form fields for POST redirect (if applicable)
        payment_instructions: Additional instructions for payment
        order_id: Order ID for this payment
        error_message: Error message if failed
        error_code: Error code if failed
    """
    success: bool = False
    redirect_required: bool = True
    redirect_url: str = ""
    redirect_method: str = "POST"
    form_fields: Dict[str, str] = field(default_factory=dict)
    payment_instructions: Dict[str, Any] = field(default_factory=dict)
    order_id: str = ""
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def from_gateway_response(cls, response: Any, order_id: str = "") -> 'PaymentInitiationResult':
        """Create from gateway response object"""
        return cls(
            success=True,
            redirect_required=getattr(response, 'is_redirect_required', True),
            redirect_url=getattr(response, 'redirect_url', ''),
            redirect_method=getattr(response, 'redirect_method', 'POST'),
            form_fields=getattr(response, 'form_fields', {}),
            payment_instructions=getattr(response, 'payment_instructions', {}),
            order_id=order_id
        )
    
    @classmethod
    def error(cls, message: str, code: str) -> 'PaymentInitiationResult':
        """Create error result"""
        return cls(
            success=False,
            error_message=message,
            error_code=code
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'success': self.success,
            'redirect_required': self.redirect_required,
            'redirect_url': self.redirect_url,
            'redirect_method': self.redirect_method,
            'form_fields': self.form_fields,
            'payment_instructions': self.payment_instructions,
            'order_id': self.order_id,
            'error_message': self.error_message,
            'error_code': self.error_code
        }


@dataclass
class PaymentVerificationResult:
    """
    Result from payment verification
    
    Attributes:
        success: Whether verification was successful
        order_id: Original order ID
        transaction_id: Gateway transaction ID
        status_code: Gateway status code
        amount: Verified amount in NPR (Decimal)
        gateway_response: Raw gateway response
        error_message: Error message if failed
        error_code: Error code if failed
    """
    success: bool = False
    order_id: str = ""
    transaction_id: str = ""
    status_code: str = ""
    amount: Decimal = Decimal('0')
    gateway_response: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    @classmethod
    def from_gateway_verification(
        cls, 
        verification: Any, 
        amount_converter: callable = None
    ) -> 'PaymentVerificationResult':
        """Create from gateway verification object"""
        amount = verification.verified_amount
        if amount_converter:
            amount = amount_converter(amount)
        else:
            amount = Decimal(str(amount))
            
        return cls(
            success=verification.is_successful,
            order_id=verification.order_id,
            transaction_id=verification.transaction_id,
            status_code=verification.status_code,
            amount=amount,
            gateway_response=verification.raw_response
        )
    
    @classmethod
    def error(cls, message: str, code: str) -> 'PaymentVerificationResult':
        """Create error result"""
        return cls(
            success=False,
            error_message=message,
            error_code=code
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'success': self.success,
            'order_id': self.order_id,
            'transaction_id': self.transaction_id,
            'status_code': self.status_code,
            'amount': float(self.amount),
            'gateway_response': self.gateway_response,
            'error_message': self.error_message,
            'error_code': self.error_code
        }


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Enums
    'GatewayType',
    'PaymentStatus',
    'RedirectMethod',
    # Result types
    'PaymentInitiationResult',
    'PaymentVerificationResult',
]
