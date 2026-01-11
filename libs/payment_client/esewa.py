"""
eSewa Gateway Client
=====================

Handles all eSewa payment operations:
- Payment initiation with signature
- Payment verification via callback
- Status checking via API

Uses nepal-gateways package EsewaClient internally.

Source: nepal-gateways EsewaClient
Date: 2026-01-10
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from nepal_gateways import (
    EsewaClient,
    ConfigurationError as NGConfigError,
    InitiationError as NGInitError,
    VerificationError as NGVerifyError,
    InvalidSignatureError as NGSigError
)

from .base import (
    BaseGatewayClient,
    ConfigurationError,
    InitiationError,
    VerificationError,
    InvalidSignatureError
)
from .types import PaymentInitiationResult, PaymentVerificationResult

logger = logging.getLogger(__name__)


class EsewaGatewayClient(BaseGatewayClient):
    """
    eSewa payment gateway client
    
    Wraps nepal-gateways EsewaClient with standardized interface.
    
    Configuration (Django settings NEPAL_GATEWAYS_CONFIG['esewa']):
        - merchant_id: eSewa merchant ID
        - secret_key: eSewa secret key for signature
        - environment: 'sandbox' or 'production'
        - success_url: URL for successful payments
        - failure_url: URL for failed payments
    
    Example:
        client = EsewaGatewayClient()
        
        # Initiate payment
        result = client.initiate_payment(
            amount=Decimal('100'),
            order_id='ORDER123',
            description='Wallet top-up'
        )
        
        # Verify payment
        verification = client.verify_payment({'data': 'base64encoded...'})
    """
    
    @property
    def gateway_name(self) -> str:
        """Return gateway identifier"""
        return 'esewa'
    
    def _get_client(self) -> EsewaClient:
        """Get or create eSewa client"""
        if self._client is None:
            try:
                self._client = EsewaClient(config=self.config)
            except NGConfigError as e:
                logger.error(f"eSewa configuration error: {e}")
                raise ConfigurationError(str(e), gateway='esewa')
        return self._client
    
    @property
    def client(self) -> EsewaClient:
        """Access underlying eSewa client"""
        return self._get_client()
    
    def initiate_payment(
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
            
        Raises:
            InitiationError: If payment initiation fails
        """
        try:
            init_response = self.client.initiate_payment(
                amount=self.convert_to_npr_float(amount),
                order_id=order_id,
                description=description,
                tax_amount=self.convert_to_npr_float(tax_amount),
                product_service_charge=self.convert_to_npr_float(product_service_charge),
                product_delivery_charge=self.convert_to_npr_float(product_delivery_charge)
            )
            
            result = PaymentInitiationResult.from_gateway_response(init_response, order_id)
            logger.info(f"eSewa payment initiated: order_id={order_id}, amount={amount}")
            return result
            
        except NGInitError as e:
            logger.error(f"eSewa payment initiation failed: {e}")
            raise InitiationError(str(e), gateway='esewa')
        except NGConfigError as e:
            logger.error(f"eSewa configuration error during initiation: {e}")
            raise ConfigurationError(str(e), gateway='esewa')
    
    def verify_payment(self, callback_data: Dict[str, Any]) -> PaymentVerificationResult:
        """
        Verify eSewa payment using callback data
        
        Args:
            callback_data: Data received from eSewa callback (contains 'data' field with base64)
            
        Returns:
            PaymentVerificationResult with verification status
            
        Raises:
            InvalidSignatureError: If signature validation fails
            VerificationError: If verification fails
        """
        try:
            verification = self.client.verify_payment(
                transaction_data_from_callback=callback_data
            )
            
            result = PaymentVerificationResult.from_gateway_verification(
                verification,
                amount_converter=self.convert_from_npr
            )
            
            logger.info(
                f"eSewa payment verified: order_id={result.order_id}, "
                f"transaction_id={result.transaction_id}, success={result.success}"
            )
            return result
            
        except NGSigError as e:
            logger.error(f"eSewa signature validation failed: {e}")
            raise InvalidSignatureError(gateway='esewa')
        except NGVerifyError as e:
            logger.error(f"eSewa payment verification failed: {e}")
            raise VerificationError(str(e), gateway='esewa')
        except NGConfigError as e:
            logger.error(f"eSewa configuration error during verification: {e}")
            raise ConfigurationError(str(e), gateway='esewa')


# ==========================================
# EXPORTS
# ==========================================

__all__ = ['EsewaGatewayClient']
