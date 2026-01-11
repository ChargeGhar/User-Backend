"""
Khalti Gateway Client
======================

Handles all Khalti payment operations:
- Payment initiation via API
- Payment verification via callback/lookup

Uses nepal-gateways package KhaltiClient internally.

Source: nepal-gateways KhaltiClient
Date: 2026-01-10
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from nepal_gateways import (
    KhaltiClient,
    ConfigurationError as NGConfigError,
    InitiationError as NGInitError,
    VerificationError as NGVerifyError
)

from .base import (
    BaseGatewayClient,
    ConfigurationError,
    InitiationError,
    VerificationError
)
from .types import PaymentInitiationResult, PaymentVerificationResult

logger = logging.getLogger(__name__)


class KhaltiGatewayClient(BaseGatewayClient):
    """
    Khalti payment gateway client
    
    Wraps nepal-gateways KhaltiClient with standardized interface.
    
    Configuration (Django settings NEPAL_GATEWAYS_CONFIG['khalti']):
        - secret_key: Khalti secret key
        - public_key: Khalti public key
        - environment: 'sandbox' or 'production'
        - return_url: URL for callback after payment
        - website_url: Your website URL
    
    Note:
        Khalti uses paisa (1 NPR = 100 paisa) for amounts.
        This client handles conversion automatically.
    
    Example:
        client = KhaltiGatewayClient()
        
        # Initiate payment (amount in NPR)
        result = client.initiate_payment(
            amount=Decimal('100'),
            order_id='ORDER123',
            description='Wallet top-up',
            customer_info={'name': 'John', 'email': 'john@example.com'}
        )
        
        # Verify payment
        verification = client.verify_payment({'pidx': '...'})
    """
    
    @property
    def gateway_name(self) -> str:
        """Return gateway identifier"""
        return 'khalti'
    
    def _get_client(self) -> KhaltiClient:
        """Get or create Khalti client"""
        if self._client is None:
            try:
                self._client = KhaltiClient(config=self.config)
            except NGConfigError as e:
                logger.error(f"Khalti configuration error: {e}")
                raise ConfigurationError(str(e), gateway='khalti')
        return self._client
    
    @property
    def client(self) -> KhaltiClient:
        """Access underlying Khalti client"""
        return self._get_client()
    
    def initiate_payment(
        self,
        amount: Decimal,
        order_id: str,
        description: str = "Payment",
        customer_info: Optional[Dict[str, str]] = None
    ) -> PaymentInitiationResult:
        """
        Initiate Khalti payment
        
        Args:
            amount: Payment amount in NPR (will be converted to paisa)
            order_id: Unique order identifier
            description: Payment description (purchase_order_name)
            customer_info: Customer details {'name': ..., 'email': ..., 'phone': ...}
            
        Returns:
            PaymentInitiationResult with redirect URL
            
        Raises:
            InitiationError: If payment initiation fails
        """
        try:
            # Convert NPR to paisa for Khalti
            amount_paisa = self.convert_to_paisa(amount)
            
            init_response = self.client.initiate_payment(
                amount=amount_paisa,
                order_id=order_id,
                description=description,
                customer_info=customer_info or {}
            )
            
            result = PaymentInitiationResult.from_gateway_response(init_response, order_id)
            # Khalti uses GET redirect
            result.redirect_method = 'GET'
            
            logger.info(f"Khalti payment initiated: order_id={order_id}, amount={amount} NPR ({amount_paisa} paisa)")
            return result
            
        except NGInitError as e:
            logger.error(f"Khalti payment initiation failed: {e}")
            raise InitiationError(str(e), gateway='khalti')
        except NGConfigError as e:
            logger.error(f"Khalti configuration error during initiation: {e}")
            raise ConfigurationError(str(e), gateway='khalti')
    
    def verify_payment(self, callback_data: Dict[str, Any]) -> PaymentVerificationResult:
        """
        Verify Khalti payment using callback data
        
        Args:
            callback_data: Data received from Khalti callback (contains 'pidx' field)
            
        Returns:
            PaymentVerificationResult with verification status (amount in NPR)
            
        Raises:
            VerificationError: If verification fails
        """
        try:
            verification = self.client.verify_payment(
                transaction_data_from_callback=callback_data
            )
            
            # Khalti returns amount in paisa, convert to NPR
            result = PaymentVerificationResult.from_gateway_verification(
                verification,
                amount_converter=self.convert_from_paisa
            )
            
            logger.info(
                f"Khalti payment verified: order_id={result.order_id}, "
                f"transaction_id={result.transaction_id}, success={result.success}"
            )
            return result
            
        except NGVerifyError as e:
            logger.error(f"Khalti payment verification failed: {e}")
            raise VerificationError(str(e), gateway='khalti')
        except NGConfigError as e:
            logger.error(f"Khalti configuration error during verification: {e}")
            raise ConfigurationError(str(e), gateway='khalti')


# ==========================================
# EXPORTS
# ==========================================

__all__ = ['KhaltiGatewayClient']
