"""
AdPayment Service
=================
Handles payment processing for approved advertisements.
"""
from __future__ import annotations

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from api.common.services.base import BaseService, ServiceException
from api.common.utils.codes import generate_transaction_id
from api.user.advertisements.models import AdRequest
from api.user.advertisements.repositories import AdRequestRepository
from api.user.payments.models import Transaction, Wallet, WalletTransaction


class AdPaymentService(BaseService):
    """Service for ad payment operations"""
    
    @transaction.atomic
    def process_ad_payment(self, ad_request_id: str, user) -> AdRequest:
        """
        Process payment for approved ad request using wallet balance.
        
        Business Rules:
        1. Ad must belong to user
        2. Ad status must be 'PENDING_PAYMENT'
        3. admin_price must be set and > 0
        4. User wallet must exist and be active
        5. Wallet balance must be >= admin_price
        6. Create Transaction with type='ADVERTISEMENT', status='SUCCESS'
        7. Create WalletTransaction for audit trail
        8. Deduct from wallet balance
        9. Update ad: transaction, paid_at, status='PAID'
        10. Use row-level locking to prevent race conditions
        
        Args:
            ad_request_id: ID of ad request to pay for
            user: User making the payment
            
        Returns:
            AdRequest: Updated ad request with payment info
            
        Raises:
            ServiceException: If validation fails or insufficient balance
        """
        try:
            # Get ad request with row-level lock
            ad_request = AdRequest.objects.select_for_update().get(
                id=ad_request_id,
                user=user
            )
            
            # Validate status
            if ad_request.status != 'PENDING_PAYMENT':
                raise ServiceException(
                    detail=f"Ad is not pending payment. Current status: {ad_request.status}",
                    code="invalid_ad_status"
                )
            
            # Validate price is set
            if not ad_request.admin_price or ad_request.admin_price <= 0:
                raise ServiceException(
                    detail="Admin price not set for this ad",
                    code="price_not_set"
                )
            
            # Get user wallet with row-level lock
            try:
                wallet = Wallet.objects.select_for_update().get(
                    user=user,
                    is_active=True
                )
            except Wallet.DoesNotExist:
                raise ServiceException(
                    detail="User wallet not found or inactive",
                    code="wallet_not_found"
                )
            
            # Check sufficient balance
            if wallet.balance < ad_request.admin_price:
                raise ServiceException(
                    detail=f"Insufficient balance. Required: NPR {ad_request.admin_price}, Available: NPR {wallet.balance}",
                    code="insufficient_balance"
                )
            
            # Create Transaction record
            txn = Transaction.objects.create(
                user=user,
                transaction_id=generate_transaction_id(),
                transaction_type='ADVERTISEMENT',
                amount=ad_request.admin_price,
                currency='NPR',
                status='SUCCESS',
                payment_method_type='WALLET',
                gateway_response={
                    'ad_request_id': str(ad_request.id),
                    'ad_title': ad_request.title or 'Advertisement',
                    'payment_method': 'wallet_deduction'
                }
            )
            
            # Create WalletTransaction for audit trail
            balance_before = wallet.balance
            balance_after = wallet.balance - ad_request.admin_price
            
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction=txn,
                transaction_type='DEBIT',
                amount=ad_request.admin_price,
                balance_before=balance_before,
                balance_after=balance_after,
                description=f'Payment for advertisement: {ad_request.title or ad_request.id}',
                metadata={
                    'ad_request_id': str(ad_request.id),
                    'payment_type': 'ad_payment',
                    'ad_title': ad_request.title
                }
            )
            
            # Update wallet balance
            wallet.balance = balance_after
            wallet.save(update_fields=['balance', 'updated_at'])
            
            # Update ad request
            ad_request.transaction = txn
            ad_request.paid_at = timezone.now()
            ad_request.status = 'PAID'
            ad_request.save(update_fields=['transaction', 'paid_at', 'status', 'updated_at'])
            
            self.log_info(
                f"Ad payment processed: {ad_request.id} - NPR {ad_request.admin_price} "
                f"by user {user.username}. Transaction: {txn.transaction_id}"
            )
            
            return ad_request
            
        except AdRequest.DoesNotExist:
            raise ServiceException(
                detail="Ad request not found or access denied",
                code="ad_not_found"
            )
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to process ad payment")
