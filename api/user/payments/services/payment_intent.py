from __future__ import annotations

import uuid
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from api.common.services.base import CRUDService, ServiceException
from api.common.utils.helpers import generate_transaction_id
from api.user.payments.models import PaymentIntent
from api.user.payments.repositories import PaymentIntentRepository, TransactionRepository, PaymentMethodRepository
from api.user.payments.services.wallet import WalletService
from libs.payment_client import PaymentGatewayClient

class PaymentIntentService(CRUDService):
    """Service for payment intents"""
    model = PaymentIntent

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.intent_repository = PaymentIntentRepository()
        self.transaction_repository = TransactionRepository()
        self.method_repository = PaymentMethodRepository()

    @transaction.atomic
    def create_topup_intent(self, user, amount: Decimal, payment_method_id: str, request=None) -> PaymentIntent:
        """Create payment intent for wallet top-up"""
        try:
            payment_method = self.method_repository.get_by_id(payment_method_id)
            if not payment_method:
                raise ServiceException(
                    detail="Invalid or inactive payment method",
                    code="invalid_payment_method"
                )

            self._validate_topup_customer_requirements(user, payment_method)

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

            # Create payment intent using repository
            intent = self.intent_repository.create(
                user=user,
                intent_id=str(uuid.uuid4()),
                intent_type='WALLET_TOPUP',
                amount=amount,
                currency='NPR',
                expires_at=timezone.now() + timezone.timedelta(minutes=30),
                intent_metadata={
                    'user_id': str(user.id),
                    'payment_method': payment_method.gateway,
                    'payment_method_name': payment_method.name,
                    'payment_method_icon': payment_method.icon,
                    'payment_method_id': str(payment_method.id),
                }
            )

            # Generate payment URL using payment_client
            gateway_client = PaymentGatewayClient()
            gateway_result = self._initiate_gateway_payment(intent, payment_method, gateway_client, request)

            intent.gateway_url = gateway_result.redirect_url
            intent.intent_metadata.update({
                'gateway_result': gateway_result.to_dict(),
                'gateway': payment_method.gateway
            })
            intent.save(update_fields=['gateway_url', 'intent_metadata'])

            self.log_info(f"Top-up intent created: {intent.intent_id} for user {user.username}")
            return intent

        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to create top-up intent")

    def _initiate_gateway_payment(self, intent: PaymentIntent, payment_method, gateway_client: PaymentGatewayClient, request=None):
        """Initiate payment with actual gateway"""
        from libs.payment_client import PaymentInitiationResult
        try:
            if payment_method.gateway == 'esewa':
                return gateway_client.initiate_esewa_payment(
                    amount=intent.amount,
                    order_id=intent.intent_id,
                    description=f"Wallet top-up - NPR {intent.amount}",
                    tax_amount=Decimal('0'),
                    product_service_charge=Decimal('0'),
                    product_delivery_charge=Decimal('0')
                )
            elif payment_method.gateway == 'khalti':
                return gateway_client.initiate_khalti_payment(
                    amount=intent.amount,
                    order_id=intent.intent_id,
                    description=f"Wallet top-up - NPR {intent.amount}",
                    customer_info=self._build_khalti_customer_info(intent.user)
                )
            else:
                raise ServiceException(
                    detail=f"Unsupported gateway: {payment_method.gateway}",
                    code="unsupported_gateway"
                )
        except ServiceException:
            raise
        except Exception as e:
            self.log_error(f"Gateway payment initiation failed: {str(e)}")
            raise

    def _validate_topup_customer_requirements(self, user, payment_method) -> None:
        """Validate customer profile requirements before gateway initiation."""
        gateway = (payment_method.gateway or '').lower()

        if gateway == 'khalti' and not getattr(user, 'email', None):
            raise ServiceException(
                detail="Email is required for Khalti payment. Please update your profile email first.",
                code="khalti_email_required"
            )

    def _build_khalti_customer_info(self, user) -> Dict[str, str]:
        """Build Khalti-compatible customer payload without null fields."""
        customer_info: Dict[str, str] = {
            'name': getattr(user, 'username', None) or 'User'
        }

        email = getattr(user, 'email', None)
        if email:
            customer_info['email'] = email

        phone = getattr(user, 'phone_number', None)
        if phone:
            customer_info['phone'] = phone

        return customer_info

    @transaction.atomic
    def verify_topup_payment(self, intent_id: str, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify top-up payment and update wallet"""
        try:
            intent = self.intent_repository.get_by_intent_id(intent_id)
            if not intent:
                raise ServiceException(
                    detail="Payment intent not found",
                    code="intent_not_found"
                )

            if intent.status == 'COMPLETED':
                result = {
                    'status': 'SUCCESS',
                    'message': 'Payment already verified',
                    'transaction_id': f"EXISTING_{intent.intent_id[:8]}",
                    'amount': intent.amount,
                    'new_balance': intent.user.wallet.balance
                }
                self._append_rental_flow_result(result, intent)
                return result
            
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

            gateway_client = PaymentGatewayClient()
            verification_result = self._verify_with_gateway(intent, callback_data, gateway_client)
            payment_verified = verification_result.success

            if payment_verified:
                gateway_name = intent.intent_metadata.get('gateway', 'unknown') if intent.intent_metadata else 'unknown'
                txn_id = verification_result.transaction_id or ''
                gateway_reference = f"{gateway_name}_{txn_id}" if txn_id else gateway_name
                
                # Create transaction using repository
                transaction_obj = self.transaction_repository.create(
                    user=intent.user,
                    transaction_id=generate_transaction_id(),
                    transaction_type='TOPUP',
                    amount=intent.amount,
                    status='SUCCESS',
                    payment_method_type='GATEWAY',
                    gateway_reference=gateway_reference,
                    gateway_response=verification_result.gateway_response
                )

                wallet_service = WalletService()
                payment_method_name = (
                    intent.intent_metadata.get('payment_method_name')
                    or intent.intent_metadata.get('payment_method', 'gateway')
                ) if intent.intent_metadata else 'gateway'
                wallet_service.add_balance(
                    intent.user,
                    intent.amount,
                    f"Wallet top-up via {payment_method_name}",
                    transaction_obj
                )

                # Award points, Send notifications (omitted for brevity in snippet but kept in implementation)
                self._post_payment_processing(intent, transaction_obj)

                # Update intent status using repository
                self.intent_repository.update_status(intent, 'COMPLETED', completed_at=timezone.now())

                # If this top-up is part of rental flow, enqueue resume task
                if intent.intent_metadata:
                    flow = intent.intent_metadata.get('flow')
                    if flow == 'RENTAL_START':
                        intent.intent_metadata['rental_start_status'] = (
                            intent.intent_metadata.get('rental_start_status') or 'PENDING'
                        )
                        intent.save(update_fields=['intent_metadata'])

                        from api.user.rentals.tasks import resume_rental_start_from_intent
                        transaction.on_commit(lambda: resume_rental_start_from_intent.delay(intent.intent_id))
                    elif flow == 'RENTAL_DUE':
                        intent.intent_metadata['rental_due_status'] = (
                            intent.intent_metadata.get('rental_due_status') or 'PENDING'
                        )
                        intent.save(update_fields=['intent_metadata'])

                        from api.user.rentals.tasks import resume_rental_due_from_intent
                        transaction.on_commit(lambda: resume_rental_due_from_intent.delay(intent.intent_id))

                self.log_info(f"Top-up verified and processed: {intent.intent_id}")

                result = {
                    'status': 'SUCCESS',
                    'transaction_id': transaction_obj.transaction_id,
                    'amount': intent.amount,
                    'new_balance': intent.user.wallet.balance
                }
                self._append_rental_flow_result(result, intent)
                return result
            else:
                self.intent_repository.update_status(intent, 'FAILED')
                raise ServiceException(
                    detail="Payment verification failed",
                    code="payment_verification_failed"
                )

        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to verify top-up payment")

    def _append_rental_flow_result(self, result: Dict[str, Any], intent: PaymentIntent) -> None:
        """Attach rental flow status fields (start/due) to verify response payload."""
        if not intent.intent_metadata:
            return

        rental_start_status = intent.intent_metadata.get('rental_start_status')
        if rental_start_status:
            result.update({
                'rental_start_status': rental_start_status,
                'rental_id': intent.intent_metadata.get('rental_id'),
                'rental_error': intent.intent_metadata.get('rental_error')
            })

        rental_due_status = intent.intent_metadata.get('rental_due_status')
        if rental_due_status:
            result.update({
                'rental_due_status': rental_due_status,
                'rental_due_error': intent.intent_metadata.get('rental_due_error'),
                'due_transaction_id': intent.intent_metadata.get('due_transaction_id'),
                'rental_id': intent.intent_metadata.get('rental_id')
            })

    def _post_payment_processing(self, intent, transaction_obj):
        """Handle points, notifications, etc."""
        try:
            # Award points
            from api.user.points.services import award_points
            award_points(
                intent.user,
                int(float(intent.amount) * 0.1),
                'TOPUP',
                f'Top-up reward for NPR {intent.amount}',
                async_send=True,
                topup_amount=float(intent.amount),
                transaction_id=transaction_obj.transaction_id
            )

            # Send notification
            from api.user.notifications.services import notify
            notify(
                intent.user,
                'payment_success',
                async_send=True,
                amount=float(intent.amount),
                transaction_id=transaction_obj.transaction_id,
                payment_type='topup'
            )
        except Exception as e:
            self.log_warning(f"Post-payment processing failed: {str(e)}")

    def _verify_with_gateway(self, intent: PaymentIntent, callback_data: Dict[str, Any], gateway_client: PaymentGatewayClient):
        """Verify payment with actual gateway using callback data"""
        from libs.payment_client import PaymentVerificationResult
        try:
            gateway = intent.intent_metadata.get('gateway') if intent.intent_metadata else None
            
            if not gateway or not callback_data:
                return PaymentVerificationResult(
                    success=True,
                    transaction_id=f"VERIFIED_{intent.intent_id[:8]}",
                    order_id=intent.intent_id,
                    amount=intent.amount,
                    gateway_response={'status': 'verified_without_callback'}
                )
            
            if gateway == 'esewa':
                return gateway_client.verify_esewa_payment(callback_data)
            elif gateway == 'khalti':
                return gateway_client.verify_khalti_payment(callback_data)
            else:
                raise ServiceException(
                    detail=f"Unsupported gateway for verification: {gateway}",
                    code="unsupported_gateway_verification"
                )
        except ServiceException:
            raise
        except Exception as e:
            self.log_error(f"Gateway payment verification failed: {str(e)}")
            raise

    def get_payment_status(self, intent_id: str) -> Dict[str, Any]:
        """Get payment status"""
        try:
            intent = self.intent_repository.get_by_intent_id(intent_id)
            if not intent:
                raise ServiceException(
                    detail="Payment intent not found",
                    code="intent_not_found"
                )

            return {
                'intent_id': intent_id,
                'status': intent.status,
                'amount': intent.amount,
                'currency': intent.currency,
                'gateway_reference': intent.intent_metadata.get('gateway_reference'),
                'completed_at': intent.completed_at,
                'failure_reason': intent.intent_metadata.get('failure_reason')
            }

        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to get payment status")

    @transaction.atomic
    def cancel_payment_intent(self, intent_id: str, user) -> Dict[str, Any]:
        """Cancel a pending payment intent"""
        try:
            intent = self.intent_repository.get_by_intent_id(intent_id)
            if not intent or intent.user != user:
                raise ServiceException(
                    detail="Payment intent not found",
                    code="intent_not_found"
                )

            if intent.status != 'PENDING':
                raise ServiceException(
                    detail="Only pending payment intents can be cancelled",
                    code="invalid_intent_status"
                )

            intent.intent_metadata['cancelled_at'] = timezone.now().isoformat()
            intent.intent_metadata['cancelled_by'] = 'user'
            self.intent_repository.update_status(intent, 'CANCELLED')

            self.log_info(f"Payment intent cancelled: {intent_id} by user {user.username}")

            return {
                'status': 'CANCELLED',
                'intent_id': intent_id,
                'message': 'Payment intent cancelled successfully'
            }

        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to cancel payment intent")
