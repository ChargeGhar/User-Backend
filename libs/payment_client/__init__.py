"""
Payment Gateway Client
=======================

A modular Python client for Nepal payment gateways (eSewa, Khalti).

This package provides:
- EsewaGatewayClient: eSewa payment operations
- KhaltiGatewayClient: Khalti payment operations
- PaymentGatewayClient: Unified facade combining all gateways

Installation:
    Uses nepal-gateways package. Ensure it's installed:
    pip install nepal-gateways

Configuration (Django):
    Add to settings.py:
    
    NEPAL_GATEWAYS_CONFIG = {
        'esewa': {
            'product_code': 'your_product_code',
            'secret_key': 'your_secret_key',
            'mode': 'sandbox',  # or 'live'
            'success_url': 'https://yoursite.com/payments/esewa/success',
            'failure_url': 'https://yoursite.com/payments/esewa/failure',
        },
        'khalti': {
            'live_secret_key': 'your_live_secret_key',
            'mode': 'sandbox',  # or 'live'
            'return_url_config': 'https://yoursite.com/payments/khalti/callback',
            'website_url_config': 'https://yoursite.com',
        }
    }

Quick Start:
    from libs.payment_client import PaymentGatewayClient
    from decimal import Decimal
    
    # Create client
    client = PaymentGatewayClient()
    
    # Initiate eSewa payment
    result = client.initiate_esewa_payment(
        amount=Decimal('100'),
        order_id='ORDER123',
        description='Wallet top-up'
    )
    print(f"Redirect to: {result.redirect_url}")
    
    # Verify eSewa payment (from callback)
    verification = client.verify_esewa_payment({'data': 'base64encoded...'})
    if verification.success:
        print(f"Payment verified: {verification.transaction_id}")
    
    # Initiate Khalti payment
    result = client.initiate_khalti_payment(
        amount=Decimal('100'),
        order_id='ORDER456',
        description='Wallet top-up',
        customer_info={'name': 'John', 'email': 'john@example.com'}
    )
    
    # Verify Khalti payment
    verification = client.verify_khalti_payment({'pidx': '...'})

Module Structure:
    payment_client/
    ├── __init__.py     # This file - exports and facade
    ├── types.py        # Type definitions (result types, enums)
    ├── base.py         # Base client with exceptions
    ├── esewa.py        # EsewaGatewayClient
    └── khalti.py       # KhaltiGatewayClient

Date: 2026-01-10
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from decimal import Decimal

# Type exports
from .types import (
    # Enums
    GatewayType,
    PaymentStatus,
    RedirectMethod,
    # Result types
    PaymentInitiationResult,
    PaymentVerificationResult,
)

# Exception exports
from .base import (
    GatewayException,
    ConfigurationError,
    InitiationError,
    VerificationError,
    InvalidSignatureError,
    BaseGatewayClient,
)

# Client exports
from .esewa import EsewaGatewayClient
from .khalti import KhaltiGatewayClient

logger = logging.getLogger(__name__)

__version__ = '1.0.0'
__author__ = 'ChargeGhar'


class PaymentGatewayClient:
    """
    Unified facade for all payment gateway operations
    
    Combines EsewaGatewayClient and KhaltiGatewayClient into a single interface.
    Lazy-loads gateway clients on first use.
    
    Attributes:
        esewa: EsewaGatewayClient for eSewa operations
        khalti: KhaltiGatewayClient for Khalti operations
    
    Example:
        # With Django settings (auto-configured)
        client = PaymentGatewayClient()
        
        # With explicit config
        client = PaymentGatewayClient(
            esewa_config={'merchant_id': '...', 'secret_key': '...'},
            khalti_config={'secret_key': '...', 'public_key': '...'}
        )
        
        # Use individual gateway methods
        client.initiate_esewa_payment(amount, order_id, description)
        client.verify_khalti_payment(callback_data)
    """
    
    def __init__(
        self,
        esewa_config: Optional[Dict[str, Any]] = None,
        khalti_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize unified payment gateway client
        
        Args:
            esewa_config: eSewa configuration dict (optional, loads from Django settings if None)
            khalti_config: Khalti configuration dict (optional, loads from Django settings if None)
        """
        self._esewa_config = esewa_config
        self._khalti_config = khalti_config
        self._esewa_client: Optional[EsewaGatewayClient] = None
        self._khalti_client: Optional[KhaltiGatewayClient] = None
        
        logger.info("PaymentGatewayClient initialized")
    
    # ==========================================
    # GATEWAY CLIENT PROPERTIES (LAZY LOADING)
    # ==========================================
    
    @property
    def esewa(self) -> EsewaGatewayClient:
        """Get eSewa gateway client (lazy-loaded)"""
        if self._esewa_client is None:
            self._esewa_client = EsewaGatewayClient(config=self._esewa_config)
        return self._esewa_client
    
    @property
    def khalti(self) -> KhaltiGatewayClient:
        """Get Khalti gateway client (lazy-loaded)"""
        if self._khalti_client is None:
            self._khalti_client = KhaltiGatewayClient(config=self._khalti_config)
        return self._khalti_client
    
    # ==========================================
    # ESEWA METHODS
    # ==========================================
    
    def initiate_esewa_payment(
        self,
        amount: Decimal,
        order_id: str,
        description: str = "Payment",
        tax_amount: Decimal = Decimal('0'),
        product_service_charge: Decimal = Decimal('0'),
        product_delivery_charge: Decimal = Decimal('0'),
        success_url: Optional[str] = None,
        failure_url: Optional[str] = None
    ) -> PaymentInitiationResult:
        """
        Initiate eSewa payment
        
        Args:
            amount: Payment amount in NPR
            order_id: Unique order identifier
            description: Payment description
            tax_amount: Tax amount in NPR
            product_service_charge: Service charge in NPR
            product_delivery_charge: Delivery charge in NPR
            success_url: Override success callback URL
            failure_url: Override failure callback URL
            
        Returns:
            PaymentInitiationResult with redirect URL and form fields
        """
        return self.esewa.initiate_payment(
            amount=amount,
            order_id=order_id,
            description=description,
            tax_amount=tax_amount,
            product_service_charge=product_service_charge,
            product_delivery_charge=product_delivery_charge,
            success_url=success_url,
            failure_url=failure_url
        )
    
    def verify_esewa_payment(self, callback_data: Dict[str, Any]) -> PaymentVerificationResult:
        """
        Verify eSewa payment
        
        Args:
            callback_data: Data received from eSewa callback
            
        Returns:
            PaymentVerificationResult with verification status
        """
        return self.esewa.verify_payment(callback_data)
    
    # ==========================================
    # KHALTI METHODS
    # ==========================================
    
    def initiate_khalti_payment(
        self,
        amount: Decimal,
        order_id: str,
        description: str = "Payment",
        customer_info: Optional[Dict[str, str]] = None
    ) -> PaymentInitiationResult:
        """
        Initiate Khalti payment
        
        Args:
            amount: Payment amount in NPR
            order_id: Unique order identifier
            description: Payment description
            customer_info: Customer details {'name': ..., 'email': ..., 'phone': ...}
            
        Returns:
            PaymentInitiationResult with redirect URL
        """
        return self.khalti.initiate_payment(
            amount=amount,
            order_id=order_id,
            description=description,
            customer_info=customer_info
        )
    
    def verify_khalti_payment(self, callback_data: Dict[str, Any]) -> PaymentVerificationResult:
        """
        Verify Khalti payment
        
        Args:
            callback_data: Data received from Khalti callback
            
        Returns:
            PaymentVerificationResult with verification status
        """
        return self.khalti.verify_payment(callback_data)
    
    # ==========================================
    # UNIFIED GATEWAY METHODS
    # ==========================================
    
    def initiate_payment(
        self,
        gateway: str,
        amount: Decimal,
        order_id: str,
        description: str = "Payment",
        **kwargs
    ) -> PaymentInitiationResult:
        """
        Initiate payment with specified gateway
        
        Args:
            gateway: Gateway name ('esewa' or 'khalti')
            amount: Payment amount in NPR
            order_id: Unique order identifier
            description: Payment description
            **kwargs: Gateway-specific parameters
            
        Returns:
            PaymentInitiationResult with redirect URL
            
        Raises:
            ValueError: If gateway is not supported
        """
        if gateway == 'esewa':
            return self.initiate_esewa_payment(
                amount=amount,
                order_id=order_id,
                description=description,
                tax_amount=kwargs.get('tax_amount', Decimal('0')),
                product_service_charge=kwargs.get('product_service_charge', Decimal('0')),
                product_delivery_charge=kwargs.get('product_delivery_charge', Decimal('0')),
                success_url=kwargs.get('success_url'),
                failure_url=kwargs.get('failure_url')
            )
        elif gateway == 'khalti':
            return self.initiate_khalti_payment(
                amount=amount,
                order_id=order_id,
                description=description,
                customer_info=kwargs.get('customer_info')
            )
        else:
            raise ValueError(f"Unsupported gateway: {gateway}")
    
    def verify_payment(self, gateway: str, callback_data: Dict[str, Any]) -> PaymentVerificationResult:
        """
        Verify payment with specified gateway
        
        Args:
            gateway: Gateway name ('esewa' or 'khalti')
            callback_data: Data received from gateway callback
            
        Returns:
            PaymentVerificationResult with verification status
            
        Raises:
            ValueError: If gateway is not supported
        """
        if gateway == 'esewa':
            return self.verify_esewa_payment(callback_data)
        elif gateway == 'khalti':
            return self.verify_khalti_payment(callback_data)
        else:
            raise ValueError(f"Unsupported gateway: {gateway}")


# ==========================================
# SINGLETON INSTANCE (for Django integration)
# ==========================================

_client_instance: Optional[PaymentGatewayClient] = None


def get_payment_client() -> PaymentGatewayClient:
    """
    Get singleton instance of PaymentGatewayClient
    
    Uses Django settings for configuration if available.
    
    Usage:
        from libs.payment_client import get_payment_client
        
        client = get_payment_client()
        result = client.initiate_esewa_payment(amount, order_id, description)
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = PaymentGatewayClient()
    return _client_instance


def reset_payment_client():
    """Reset singleton instance (for testing)"""
    global _client_instance
    _client_instance = None


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Main client
    'PaymentGatewayClient',
    'get_payment_client',
    'reset_payment_client',
    
    # Individual clients
    'EsewaGatewayClient',
    'KhaltiGatewayClient',
    'BaseGatewayClient',
    
    # Exceptions
    'GatewayException',
    'ConfigurationError',
    'InitiationError',
    'VerificationError',
    'InvalidSignatureError',
    
    # Types - Enums
    'GatewayType',
    'PaymentStatus',
    'RedirectMethod',
    
    # Types - Result models
    'PaymentInitiationResult',
    'PaymentVerificationResult',
]
