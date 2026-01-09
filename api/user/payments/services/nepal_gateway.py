from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Union
from decimal import Decimal
from django.conf import settings
from nepal_gateways import (
    EsewaClient, KhaltiClient, 
    ConfigurationError, InitiationError, 
    VerificationError, InvalidSignatureError
)
from api.common.services.base import ServiceException

logger = logging.getLogger(__name__)

class NepalGatewayService:
    """Service wrapper for nepal-gateways package"""
    
    def __init__(self):
        self.config = getattr(settings, 'NEPAL_GATEWAYS_CONFIG', {})
        self._esewa_client = None
        self._khalti_client = None
    
    @property
    def esewa_client(self) -> EsewaClient:
        """Get or create eSewa client"""
        if self._esewa_client is None:
            try:
                esewa_config = self.config.get('esewa', {})
                self._esewa_client = EsewaClient(config=esewa_config)
            except ConfigurationError as e:
                logger.error(f"eSewa configuration error: {e}")
                raise ServiceException(
                    detail=f"eSewa gateway configuration error: {e}",
                    code="esewa_config_error"
                )
        return self._esewa_client
    
    @property
    def khalti_client(self) -> KhaltiClient:
        """Get or create Khalti client"""
        if self._khalti_client is None:
            try:
                khalti_config = self.config.get('khalti', {})
                self._khalti_client = KhaltiClient(config=khalti_config)
            except ConfigurationError as e:
                logger.error(f"Khalti configuration error: {e}")
                raise ServiceException(
                    detail=f"Khalti gateway configuration error: {e}",
                    code="khalti_config_error"
                )
        return self._khalti_client
    
    def convert_amount_for_gateway(self, amount: Decimal, gateway: str) -> Union[float, int]:
        """Convert amount to gateway-specific format"""
        if gateway == 'esewa':
            return float(amount)  # eSewa accepts NPR as float
        elif gateway == 'khalti':
            return int(amount * 100)  # Khalti requires paisa (NPR * 100)
        else:
            raise ServiceException(
                detail=f"Unknown gateway for amount conversion: {gateway}",
                code="unknown_gateway"
            )
    
    def convert_amount_from_gateway(self, amount: Union[float, int], gateway: str) -> Decimal:
        """Convert amount from gateway-specific format to Decimal"""
        if gateway == 'esewa':
            return Decimal(str(amount))  # eSewa returns NPR
        elif gateway == 'khalti':
            return Decimal(str(amount)) / 100  # Khalti returns paisa
        else:
            raise ServiceException(
                detail=f"Unknown gateway for amount conversion: {gateway}",
                code="unknown_gateway"
            )
    
    def initiate_esewa_payment(
        self, 
        amount: Decimal, 
        order_id: str,
        description: str = "Wallet top-up",
        tax_amount: Decimal = Decimal('0'),
        product_service_charge: Decimal = Decimal('0'),
        product_delivery_charge: Decimal = Decimal('0'),
        success_url: str = None,
        failure_url: str = None
    ) -> Dict[str, Any]:
        """Initiate eSewa payment"""
        try:
            init_response = self.esewa_client.initiate_payment(
                amount=float(amount),
                order_id=order_id,
                description=description,
                tax_amount=float(tax_amount),
                product_service_charge=float(product_service_charge),
                product_delivery_charge=float(product_delivery_charge)
            )
            
            return {
                'success': True,
                'redirect_required': getattr(init_response, 'is_redirect_required', True),
                'redirect_url': getattr(init_response, 'redirect_url', ''),
                'redirect_method': getattr(init_response, 'redirect_method', 'POST'),
                'form_fields': getattr(init_response, 'form_fields', {}),
                'payment_instructions': getattr(init_response, 'payment_instructions', {})
            }
            
        except InitiationError as e:
            logger.error(f"eSewa payment initiation failed: {e}")
            raise ServiceException(
                detail=f"eSewa payment initiation failed: {e}",
                code="esewa_initiation_error"
            )
    
    def verify_esewa_payment(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify eSewa payment using nepal-gateways package"""
        try:
            # Use nepal-gateways EsewaClient.verify_payment()
            verification = self.esewa_client.verify_payment(
                transaction_data_from_callback=callback_data
            )
            
            return {
                'success': verification.is_successful,
                'order_id': verification.order_id,
                'transaction_id': verification.transaction_id,
                'status_code': verification.status_code,
                'amount': verification.verified_amount,
                'gateway_response': verification.raw_response
            }
            
        except InvalidSignatureError as e:
            logger.error(f"eSewa signature validation failed: {e}")
            raise ServiceException(
                detail="eSewa payment signature validation failed",
                code="esewa_invalid_signature"
            )
        except VerificationError as e:
            logger.error(f"eSewa payment verification failed: {e}")
            raise ServiceException(
                detail=f"eSewa payment verification failed: {e}",
                code="esewa_verification_error"
            )
    
    def initiate_khalti_payment(
        self,
        amount: Decimal,
        order_id: str,
        description: str,
        customer_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Initiate Khalti payment"""
        try:
            khalti_amount_paisa = self.convert_amount_for_gateway(amount, 'khalti')
            
            init_response = self.khalti_client.initiate_payment(
                amount=khalti_amount_paisa,
                order_id=order_id,
                description=description,
                customer_info=customer_info or {}
            )
            
            return {
                'success': True,
                'redirect_required': getattr(init_response, 'is_redirect_required', True),
                'redirect_url': getattr(init_response, 'redirect_url', ''),
                'redirect_method': getattr(init_response, 'redirect_method', 'GET'),
                'form_fields': getattr(init_response, 'form_fields', None),
                'payment_instructions': getattr(init_response, 'payment_instructions', {})
            }
            
        except InitiationError as e:
            logger.error(f"Khalti payment initiation failed: {e}")
            raise ServiceException(
                detail=f"Khalti payment initiation failed: {e}",
                code="khalti_initiation_error"
            )
    
    def verify_khalti_payment(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify Khalti payment using nepal-gateways package"""
        try:
            # Use nepal-gateways KhaltiClient.verify_payment()
            verification = self.khalti_client.verify_payment(
                transaction_data_from_callback=callback_data
            )
            
            return {
                'success': verification.is_successful,
                'order_id': verification.order_id,
                'transaction_id': verification.transaction_id,
                'status_code': verification.status_code,
                'amount': self.convert_amount_from_gateway(
                    verification.verified_amount, 'khalti'
                ),
                'gateway_response': verification.raw_response
            }
            
        except VerificationError as e:
            logger.error(f"Khalti payment verification failed: {e}")
            raise ServiceException(
                detail=f"Khalti payment verification failed: {e}",
                code="khalti_verification_error"
            )