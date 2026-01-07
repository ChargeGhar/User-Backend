from __future__ import annotations

from typing import Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.payments.services.wallet import WalletService
from .core import RefundBaseService

class RefundService(RefundBaseService):
    """Service for refund processing logic (request/approve/reject)"""

    @transaction.atomic
    def request_refund(self, user, transaction_id: str, reason: str) -> Any:
        """Request refund for a transaction"""
        try:
            # Find transaction
            transaction_obj = self.transaction_repository.get_by_id_or_txn_id(transaction_id)
            if not transaction_obj:
                raise ServiceException(detail=f"Transaction {transaction_id} not found", code="transaction_not_found")

            # Ownership check
            if transaction_obj.user_id != user.id:
                raise ServiceException(detail="Unauthorized transaction", code="unauthorized_transaction")

            # Status check
            if transaction_obj.status != 'SUCCESS':
                raise ServiceException(detail="Only successful transactions can be refunded", code="invalid_status")

            # Duplicate check
            if self.refund_repository.get_by_user(user).filter(transaction=transaction_obj).exists():
                raise ServiceException(detail="Refund already requested", code="duplicate_refund")

            # Create
            refund = self.refund_repository.create(
                user=user,
                transaction=transaction_obj,
                amount=transaction_obj.amount,
                reason=reason.strip(),
                refund_id=f"REF{transaction_id[-10:]}",
                status='REQUESTED'
            )
            
            # Notify
            self._notify_status(user, 'requested', amount=transaction_obj.amount, reference=transaction_id)
            return refund
        except Exception as e:
            self.handle_service_error(e, "Refund request failed")

    @transaction.atomic
    def approve_refund(self, refund_id: str, admin_user, admin_notes: str = None) -> Any:
        """Approve a refund request"""
        refund = self.get_refund_by_id(refund_id)
        if refund.status != 'REQUESTED':
            raise ServiceException(detail=f"Cannot approve {refund.status} refund")
            
        refund.status = 'APPROVED'
        refund.approved_by = admin_user
        refund.processed_at = timezone.now()
        if admin_notes:
            refund.admin_notes = admin_notes
        refund.save()
        
        # Add to wallet
        wallet_service = WalletService()
        wallet_service.add_balance(
            user=refund.requested_by,
            amount=refund.amount,
            description=f"Refund approved for {refund.transaction.transaction_id}"
        )
        
        # Update transaction status
        self.transaction_repository.update_status(refund.transaction, 'REFUNDED')
        
        self._notify_status(refund.requested_by, 'approved', amount=refund.amount, reference=refund.transaction.transaction_id)
        return refund

    @transaction.atomic
    def reject_refund(self, refund_id: str, admin_user, reason: str) -> Any:
        """Reject a refund request"""
        refund = self.get_refund_by_id(refund_id)
        if refund.status != 'REQUESTED':
            raise ServiceException(detail=f"Cannot reject {refund.status} refund")
            
        refund.status = 'REJECTED'
        refund.approved_by = admin_user
        refund.admin_notes = reason
        refund.processed_at = timezone.now()
        refund.save()
        
        self._notify_status(refund.requested_by, 'rejected', amount=refund.amount, reference=refund.transaction.transaction_id, reason=reason)
        return refund

    def _notify_status(self, user, status_key: str, **kwargs):
        """Helper to send notifications"""
        try:
            from api.notifications.services import notify
            notify(user, f'refund_{status_key}', async_send=True, **kwargs)
        except Exception:
            pass
