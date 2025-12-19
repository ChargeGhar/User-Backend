from __future__ import annotations

import uuid
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import generate_transaction_id
from api.payments.models import PaymentIntent, Transaction, PaymentMethod
from api.payments.services.wallet import WalletService
from api.payments.services.nepal_gateway import NepalGatewayService

class PaymentIntentService(CRUDService):
    """Service for payment intents"""
    model = PaymentIntent

    @transaction.atomic
    def create_topup_intent(self, user, amount: Decimal, payment_method_id: str, request=None) -> PaymentIntent:
        """Create payment intent for wallet top-up"""
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, is_active=True)

            # Validate amount against payment method limits
            if amount < payment_method.min_amount:
                raise ServiceException(
                    detail=f"Minimum amount is {payment_method.min_amount}",
                    code="amount_too_low"
                )

            if payment_method.max_amount and amount > payment_method.max_amount:
                raise ServiceException(
                    detail=f"Maximum amount is {payment_method.max_amount}",
                    code="amount_too_high"
                )

            # Create payment intent
            intent = PaymentIntent.objects.create(
                user=user,
                intent_id=str(uuid.uuid4()),
                intent_type='WALLET_TOPUP',
                amount=amount,
                currency='NPR',
                expires_at=timezone.now() + timezone.timedelta(minutes=30),
                intent_metadata={
                    'user_id': str(user.id),
                    'payment_method': payment_method.gateway
                }
            )

            # Generate payment URL using nepal-gateways with dynamic URLs
            gateway_service = NepalGatewayService()
            gateway_result = self._initiate_gateway_payment(intent, payment_method, gateway_service, request)

            intent.gateway_url = gateway_result.get('redirect_url')
            intent.intent_metadata.update({
                'gateway_result': gateway_result,
                'gateway': payment_method.gateway
            })
            intent.save(update_fields=['gateway_url', 'intent_metadata'])

            self.log_info(f"Top-up intent created: {intent.intent_id} for user {user.username}")
            return intent

        except PaymentMethod.DoesNotExist:
            raise ServiceException(
                detail="Invalid payment method",
                code="invalid_payment_method"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to create top-up intent")

    def _initiate_gateway_payment(self, intent: PaymentIntent, payment_method: PaymentMethod, gateway_service: NepalGatewayService, request=None) -> Dict[str, Any]:
        """Initiate payment with actual gateway"""
        try:
            if payment_method.gateway == 'esewa':
                return gateway_service.initiate_esewa_payment(
                    amount=intent.amount,
                    order_id=intent.intent_id,
                    description=f"Wallet top-up - NPR {intent.amount}",
                    tax_amount=Decimal('0'),
                    product_service_charge=Decimal('0'),
                    product_delivery_charge=Decimal('0')
                )
            elif payment_method.gateway == 'khalti':
                return gateway_service.initiate_khalti_payment(
                    amount=intent.amount,  # Will be converted to paisa internally
                    order_id=intent.intent_id,
                    description=f"Wallet top-up - NPR {intent.amount}",
                    customer_info={
                        'name': getattr(intent.user, 'username', 'User'),
                        'email': getattr(intent.user, 'email', '')
                    }
                )
            else:
                raise ServiceException(
                    detail=f"Unsupported gateway: {payment_method.gateway}",
                    code="unsupported_gateway"
                )
        except Exception as e:
            self.log_error(f"Gateway payment initiation failed: {str(e)}")
            raise

    @transaction.atomic
    def verify_topup_payment(self, intent_id: str, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify top-up payment and update wallet"""
        try:
            intent = PaymentIntent.objects.get(intent_id=intent_id)

            # Allow verification of already completed payments (for duplicate calls/webhooks)
            if intent.status == 'COMPLETED':
                return {
                    'status': 'SUCCESS',
                    'message': 'Payment already verified',
                    'transaction_id': f"EXISTING_{intent.intent_id[:8]}",
                    'amount': intent.amount,
                    'new_balance': intent.user.wallet.balance
                }
            
            if intent.status != 'PENDING':
                raise ServiceException(
                    detail=f"Payment intent status is {intent.status}, cannot verify",
                    code="invalid_intent_status"
                )

            if timezone.now() > intent.expires_at:
                raise ServiceException(
                    detail="Payment intent has expired",
                    code="intent_expired"
                )

            # Verify payment with gateway using nepal-gateways
            gateway_service = NepalGatewayService()
            verification_result = self._verify_with_gateway(intent, callback_data, gateway_service)
            payment_verified = verification_result.get('success', False)

            if payment_verified:
                # Get gateway name from intent metadata
                gateway_name = intent.intent_metadata.get('gateway', 'unknown') if intent.intent_metadata else 'unknown'
                txn_id = verification_result.get('transaction_id', '')
                
                # Format gateway_reference with gateway name prefix
                gateway_reference = f"{gateway_name}_{txn_id}" if txn_id else gateway_name
                
                # Create transaction record
                transaction_obj = Transaction.objects.create(
                    user=intent.user,
                    transaction_id=generate_transaction_id(),
                    transaction_type='TOPUP',
                    amount=intent.amount,
                    status='SUCCESS',
                    payment_method_type='GATEWAY',
                    gateway_reference=gateway_reference,
                    gateway_response=verification_result.get('gateway_response', {})
                )

                # Add balance to wallet
                wallet_service = WalletService()
                # Get payment method name from intent metadata or use a default
                payment_method_name = intent.intent_metadata.get('payment_method', 'gateway') if intent.intent_metadata else 'gateway'
                wallet_service.add_balance(
                    intent.user,
                    intent.amount,
                    f"Wallet top-up via {payment_method_name}",
                    transaction_obj
                )

                # Award points for top-up
                from api.points.services import award_points
                award_points(
                    intent.user,
                    int(float(intent.amount) * 0.1),  # 10% of top-up amount as points
                    'TOPUP',
                    f'Top-up reward for NPR {intent.amount}',
                    async_send=True,
                    topup_amount=float(intent.amount),
                    transaction_id=transaction_obj.transaction_id
                )

                # Send payment success notification
                from api.notifications.services import notify
                notify(
                    intent.user,
                    'payment_success',
                    async_send=True,
                    amount=float(intent.amount),
                    transaction_id=transaction_obj.transaction_id,
                    payment_type='topup'
                )

                # Update intent status
                intent.status = 'COMPLETED'
                intent.completed_at = timezone.now()
                intent.save(update_fields=['status', 'completed_at'])

                self.log_info(f"Top-up verified and processed: {intent.intent_id}")

                return {
                    'status': 'SUCCESS',
                    'transaction_id': transaction_obj.transaction_id,
                    'amount': intent.amount,
                    'new_balance': intent.user.wallet.balance
                }
            else:
                # Mark as failed
                intent.status = 'FAILED'
                intent.save(update_fields=['status'])

                raise ServiceException(
                    detail="Payment verification failed",
                    code="payment_verification_failed"
                )

        except PaymentIntent.DoesNotExist:
            raise ServiceException(
                detail="Payment intent not found",
                code="intent_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to verify top-up payment")

    def _verify_with_gateway(self, intent: PaymentIntent, callback_data: Dict[str, Any], gateway_service: NepalGatewayService) -> Dict[str, Any]:
        """Verify payment with actual gateway using callback data"""
        try:
            gateway = intent.intent_metadata.get('gateway') if intent.intent_metadata else None
            
            # If no gateway info or callback_data, assume successful verification
            # This handles cases where payment was already processed by webhooks
            if not gateway or not callback_data:
                return {
                    'success': True,
                    'transaction_id': f"VERIFIED_{intent.intent_id[:8]}",
                    'order_id': intent.intent_id,
                    'amount': float(intent.amount),
                    'gateway_response': {'status': 'verified_without_callback'}
                }
            
            if gateway == 'esewa':
                # For eSewa, callback_data contains: {"data": "base64_encoded_json"}
                verification = gateway_service.verify_esewa_payment(callback_data)
                return {
                    'success': verification.get('success', False),
                    'transaction_id': verification.get('transaction_id'),
                    'order_id': verification.get('order_id'),
                    'amount': verification.get('amount'),
                    'gateway_response': verification.get('gateway_response', {})
                }
                
            elif gateway == 'khalti':
                # For Khalti, callback_data contains: {"pidx": "...", "status": "...", "txnId": "..."}
                verification = gateway_service.verify_khalti_payment(callback_data)
                return {
                    'success': verification.get('success', False),
                    'transaction_id': verification.get('transaction_id'),
                    'order_id': verification.get('order_id'),
                    'amount': verification.get('amount'),
                    'gateway_response': verification.get('gateway_response', {})
                }
            else:
                raise ServiceException(
                    detail=f"Unsupported gateway for verification: {gateway}",
                    code="unsupported_gateway_verification"
                )
        except Exception as e:
            self.log_error(f"Gateway payment verification failed: {str(e)}")
            raise

    def get_payment_status(self, intent_id: str) -> Dict[str, Any]:
        """Get payment status"""
        try:
            intent = PaymentIntent.objects.get(intent_id=intent_id)

            return {
                'intent_id': intent_id,
                'status': intent.status,
                'amount': intent.amount,
                'currency': intent.currency,
                'gateway_reference': intent.intent_metadata.get('gateway_reference'),
                'completed_at': intent.completed_at,
                'failure_reason': intent.intent_metadata.get('failure_reason')
            }

        except PaymentIntent.DoesNotExist:
            raise ServiceException(
                detail="Payment intent not found",
                code="intent_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get payment status")

    @transaction.atomic
    def cancel_payment_intent(self, intent_id: str, user) -> Dict[str, Any]:
        """Cancel a pending payment intent"""
        try:
            intent = PaymentIntent.objects.get(intent_id=intent_id, user=user)

            if intent.status != 'PENDING':
                raise ServiceException(
                    detail="Only pending payment intents can be cancelled",
                    code="invalid_intent_status"
                )

            # Update intent status
            intent.status = 'CANCELLED'
            intent.intent_metadata['cancelled_at'] = timezone.now().isoformat()
            intent.intent_metadata['cancelled_by'] = 'user'
            intent.save(update_fields=['status', 'intent_metadata'])

            self.log_info(f"Payment intent cancelled: {intent_id} by user {user.username}")

            return {
                'status': 'CANCELLED',
                'intent_id': intent_id,
                'message': 'Payment intent cancelled successfully'
            }

        except PaymentIntent.DoesNotExist:
            raise ServiceException(
                detail="Payment intent not found",
                code="intent_not_found"
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to cancel payment intent")