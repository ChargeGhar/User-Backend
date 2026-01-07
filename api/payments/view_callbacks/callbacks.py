from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from django.shortcuts import redirect
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.payments.services import PaymentIntentService

router = CustomViewRouter()
logger = logging.getLogger(__name__)


# Serializers
class CallbackSerializer(serializers.Serializer):
    """Base callback serializer"""
    pass


class PaymentVerificationSerializer(serializers.Serializer):
    """Payment verification request serializer"""
    gateway = serializers.CharField()
    intent_id = serializers.CharField()
    callback_data = serializers.JSONField()


class PaymentCallbackMixin:
    """Mixin for common payment callback functionality"""
    
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL from environment"""
        return os.getenv('FRONTEND_URL', 'https://chargeghar.app')
    
    @staticmethod
    def build_payment_redirect(status: str, provider: str, **params) -> Response:
        """Build frontend payment status redirect URL"""
        frontend_url = PaymentCallbackMixin.get_frontend_url()
        query_params = urlencode({'status': status, 'provider': provider, **params})
        return redirect(f"{frontend_url}/payment-status?{query_params}")
    
    @staticmethod
    def check_existing_payment_status(intent_id: str, provider: str) -> Optional[Response]:
        """
        Check if payment was already processed and return appropriate redirect if so.
        Returns None if payment should be processed.
        """
        try:
            from api.payments.repositories.payment_intent_repository import PaymentIntentRepository
            intent = PaymentIntentRepository.get_by_intent_id(intent_id)
            
            if not intent:
                return None

            if intent.status == 'COMPLETED':
                logger.info(f"{provider} payment already processed: {intent_id}")
                return PaymentCallbackMixin.build_payment_redirect(
                    status='success',
                    provider=provider,
                    intent_id=intent_id
                )
            elif intent.status == 'FAILED':
                return PaymentCallbackMixin.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason='Payment verification failed',
                    intent_id=intent_id
                )
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def verify_and_redirect(
        intent_id: str,
        callback_data: Dict[str, Any],
        provider: str
    ) -> Response:
        """
        Verify payment and redirect to frontend with appropriate status.
        Handles success, failure, and already-processed cases.
        """
        service = PaymentIntentService()
        
        try:
            result = service.verify_topup_payment(intent_id, callback_data)
            
            if result.get('status') == 'SUCCESS':
                logger.info(f"{provider} payment verified successfully: {intent_id}")
                return PaymentCallbackMixin.build_payment_redirect(
                    status='success',
                    provider=provider,
                    intent_id=intent_id
                )
            else:
                logger.warning(f"{provider} payment verification failed: {intent_id}")
                return PaymentCallbackMixin.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason='Payment verification failed',
                    intent_id=intent_id
                )
                
        except Exception as verify_error:
            logger.error(f"{provider} payment verification failed: {str(verify_error)}")
            
            # Check if already processed
            existing_redirect = PaymentCallbackMixin.check_existing_payment_status(
                intent_id, provider
            )
            if existing_redirect:
                return existing_redirect
            
            # Return verification error
            return PaymentCallbackMixin.build_payment_redirect(
                status='failure',
                provider=provider,
                reason='Verification error',
                intent_id=intent_id
            )
    
    @staticmethod
    def mark_payment_failed(intent_id: str, reason: str) -> None:
        """Mark payment intent as failed with reason"""
        try:
            from api.payments.repositories.payment_intent_repository import PaymentIntentRepository
            intent = PaymentIntentRepository.get_by_intent_id(intent_id)
            if intent and intent.status == 'PENDING':
                intent.intent_metadata['failure_reason'] = reason
                PaymentIntentRepository.update_status(intent, 'FAILED')
                logger.info(f"Payment intent {intent_id} marked as failed")
        except Exception as e:
            logger.error(f"Failed to update payment intent {intent_id}: {str(e)}")


@router.register(r"payments/esewa/success", name="payment-esewa-success")
@extend_schema(
    tags=["Payments"],
    summary="eSewa Success Callback",
    responses={302: BaseResponseSerializer}
)
class ESewaSuccessCallbackView(GenericAPIView, BaseAPIView, PaymentCallbackMixin):
    permission_classes = [AllowAny]
    serializer_class = CallbackSerializer
    
    def get(self, request: Request) -> Response:
        """Handle eSewa success callback - Process payment and redirect to frontend"""
        provider = 'esewa'
        
        try:
            # Extract and validate callback data
            data = request.GET.get('data')
            if not data:
                return self.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason='Missing callback data'
                )
            
            # Decode eSewa base64 JSON data
            try:
                decoded_json = json.loads(base64.b64decode(data))
                intent_id = decoded_json.get('transaction_uuid')
                
                if not intent_id:
                    return self.build_payment_redirect(
                        status='failure',
                        provider=provider,
                        reason='Invalid callback data'
                    )
            except Exception as decode_error:
                logger.error(f"eSewa data decode error: {str(decode_error)}")
                return self.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason='Invalid data format'
                )
            
            # Verify payment and redirect
            return self.verify_and_redirect(intent_id, {'data': data}, provider)
            
        except Exception as e:
            logger.error(f"eSewa callback error: {str(e)}")
            return self.build_payment_redirect(
                status='failure',
                provider=provider,
                reason=str(e)
            )


@router.register(r"payments/esewa/failure", name="payment-esewa-failure")
@extend_schema(
    tags=["Payments"],
    summary="eSewa Failure Callback",
    responses={302: BaseResponseSerializer}
)
class ESewaFailureCallbackView(GenericAPIView, BaseAPIView, PaymentCallbackMixin):
    permission_classes = [AllowAny]
    serializer_class = CallbackSerializer
    
    def get(self, request: Request) -> Response:
        """Handle eSewa failure callback - Process failure and redirect to frontend"""
        provider = 'esewa'
        
        try:
            error_message = request.GET.get('message', 'Payment cancelled or failed')
            data = request.GET.get('data')
            
            # Try to extract intent_id from data if available
            intent_id = None
            if data:
                try:
                    decoded_json = json.loads(base64.b64decode(data))
                    intent_id = decoded_json.get('transaction_uuid')
                except Exception:
                    pass
            
            # Mark payment as failed if we have intent_id
            if intent_id:
                self.mark_payment_failed(intent_id, error_message)
                return self.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason=error_message,
                    intent_id=intent_id
                )
            else:
                return self.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason=error_message
                )
            
        except Exception as e:
            logger.error(f"eSewa failure callback error: {str(e)}")
            return self.build_payment_redirect(
                status='failure',
                provider=provider,
                reason='Payment processing error'
            )


@router.register(r"payments/khalti/callback", name="payment-khalti-callback")
@extend_schema(
    tags=["Payments"],
    summary="Khalti Callback",
    responses={302: BaseResponseSerializer}
)
class KhaltiCallbackView(GenericAPIView, BaseAPIView, PaymentCallbackMixin):
    permission_classes = [AllowAny]
    serializer_class = CallbackSerializer
    
    def get(self, request: Request) -> Response:
        """Handle Khalti return callback - Process payment and redirect to frontend"""
        provider = 'khalti'
        
        try:
            # Extract and validate required parameters
            pidx = request.GET.get('pidx')
            purchase_order_id = request.GET.get('purchase_order_id')
            
            if not pidx or not purchase_order_id:
                logger.error("Khalti callback missing required parameters")
                return self.build_payment_redirect(
                    status='failure',
                    provider=provider,
                    reason='Invalid callback - missing parameters'
                )
            
            # For Khalti, purchase_order_id is our intent_id
            intent_id = purchase_order_id
            
            # Build callback data with all Khalti parameters
            callback_data = {
                'pidx': pidx,
                'status': request.GET.get('status'),
                'txnId': request.GET.get('txnId'),
                'transaction_id': request.GET.get('transaction_id'),
                'tidx': request.GET.get('tidx'),
                'amount': request.GET.get('amount'),
                'total_amount': request.GET.get('total_amount'),
                'mobile': request.GET.get('mobile'),
                'purchase_order_id': purchase_order_id,
                'purchase_order_name': request.GET.get('purchase_order_name')
            }
            
            # Verify payment and redirect
            return self.verify_and_redirect(intent_id, callback_data, provider)
            
        except Exception as e:
            logger.error(f"Khalti callback error: {str(e)}")
            return self.build_payment_redirect(
                status='failure',
                provider=provider,
                reason=str(e)
            )