from __future__ import annotations

from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.common.utils.helpers import generate_transaction_id
from .validation import WithdrawalValidationService

class WithdrawalService(WithdrawalValidationService):
    """Service for withdrawal processing logic (approve/reject/cancel)"""

    @transaction.atomic
    def request_withdrawal(self, user, amount: Decimal, withdrawal_method: str, account_details: Dict[str, Any]) -> Any:
        """Create a new withdrawal request"""
        try:
            # Validate
            self.validate_request(user, amount, withdrawal_method, account_details)
            
            # Fees
            processing_fee = self.calculate_withdrawal_fee(amount)
            net_amount = amount - processing_fee
            
            payment_method = self.method_repository.get_by_gateway(withdrawal_method)
            
            # Create
            withdrawal = self.withdrawal_repository.create_request(
                user=user,
                amount=amount,
                bank_name=account_details.get('bank_name', withdrawal_method),
                account_number=account_details.get('account_number', account_details.get('phone_number')),
                account_holder_name=account_details.get('account_holder_name', user.username),
                processing_fee=processing_fee,
                net_amount=net_amount,
                payment_method=payment_method,
                account_details=account_details,
                internal_reference=f"WD{generate_transaction_id()[-10:]}"
            )
            
            # Deduct from wallet
            self.wallet_service.deduct_balance(
                user=user,
                amount=amount,
                description=f"Withdrawal request - {withdrawal.internal_reference}"
            )
            
            # Notify
            self._notify_status(user, 'requested', amount=amount, reference=withdrawal.internal_reference)
            
            return withdrawal
        except Exception as e:
            self.handle_service_error(e, "Withdrawal request failed")

    @transaction.atomic
    def approve_withdrawal(self, withdrawal_id: str, admin_user, admin_notes: str = None) -> Any:
        """Approve a withdrawal request"""
        withdrawal = self.get_withdrawal_by_id(withdrawal_id)
        if withdrawal.status not in ['REQUESTED', 'PENDING']:
            raise ServiceException(detail=f"Cannot approve {withdrawal.status} withdrawal")
            
        withdrawal.status = 'APPROVED'
        withdrawal.processed_by = admin_user
        withdrawal.processed_at = timezone.now()
        if admin_notes:
            withdrawal.admin_notes = admin_notes
        withdrawal.save()
        
        # In real scenario, here we'd call the gateway API
        withdrawal.status = 'COMPLETED'
        withdrawal.save()
        
        self._notify_status(withdrawal.user, 'approved', amount=withdrawal.amount, reference=withdrawal.internal_reference)
        return withdrawal

    @transaction.atomic
    def reject_withdrawal(self, withdrawal_id: str, admin_user, reason: str) -> Any:
        """Reject a withdrawal request"""
        withdrawal = self.get_withdrawal_by_id(withdrawal_id)
        if withdrawal.status not in ['REQUESTED', 'PENDING']:
            raise ServiceException(detail=f"Cannot reject {withdrawal.status} withdrawal")
            
        withdrawal.status = 'REJECTED'
        withdrawal.processed_by = admin_user
        withdrawal.admin_notes = reason
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        # Refund wallet
        self.wallet_service.add_balance(
            user=withdrawal.user,
            amount=withdrawal.amount,
            description=f"Withdrawal rejected - {withdrawal.internal_reference}"
        )
        
        self._notify_status(withdrawal.user, 'rejected', amount=withdrawal.amount, reference=withdrawal.internal_reference, reason=reason)
        return withdrawal

    @transaction.atomic
    def cancel_withdrawal(self, withdrawal_id: str, user) -> Any:
        """Cancel a pending withdrawal request by the user"""
        withdrawal = self.get_withdrawal_by_id(withdrawal_id)
        
        # Ownership check
        if withdrawal.user != user:
            raise ServiceException(
                detail="You are not authorized to cancel this withdrawal",
                code="unauthorized_withdrawal"
            )
            
        # Status check - only REQUESTED or PENDING withdrawals can be cancelled by user
        if withdrawal.status not in ['REQUESTED', 'PENDING']:
            raise ServiceException(
                detail=f"Cannot cancel withdrawal in {withdrawal.status} status",
                code="invalid_withdrawal_status"
            )
            
        # Update status
        withdrawal.status = 'CANCELLED'
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        # Refund wallet balance
        self.wallet_service.add_balance(
            user=user,
            amount=withdrawal.amount,
            description=f"Withdrawal cancelled by user - {withdrawal.internal_reference}"
        )
        
        # Notify user
        self._notify_status(user, 'cancelled', amount=withdrawal.amount, reference=withdrawal.internal_reference)
        
        return withdrawal

    def _notify_status(self, user, status_key: str, **kwargs):
        """Helper to send notifications with correct template context"""
        try:
            from api.user.notifications.services import notify
            
            context = {}
            if 'amount' in kwargs:
                context['amount'] = str(kwargs['amount'])
            if 'reference' in kwargs:
                context['withdrawal_reference'] = kwargs['reference']
            if 'reason' in kwargs:
                context['rejection_reason'] = kwargs['reason']
            if 'admin_notes' in kwargs:
                context['admin_notes'] = kwargs['admin_notes']
            
            withdrawal = None
            if 'reference' in kwargs:
                try:
                    withdrawal = self.withdrawal_repository.get_queryset().filter(
                        internal_reference=kwargs['reference']
                    ).first()
                except Exception:
                    pass
            
            if withdrawal:
                context['processing_fee'] = str(withdrawal.processing_fee)
                context['net_amount'] = str(withdrawal.net_amount)
            
            notify(user, f'withdrawal_{status_key}', async_send=True, **context)
        except Exception as e:
            self.log_warning(f"Notification failed for withdrawal_{status_key}: {str(e)}")
