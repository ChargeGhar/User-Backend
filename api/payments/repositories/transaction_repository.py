from typing import Optional, List
from django.db.models import QuerySet
from api.payments.models import Transaction

class TransactionRepository:
    """Repository for Transaction data operations"""
    
    @staticmethod
    def get_by_id(transaction_id: str) -> Optional[Transaction]:
        try:
            return Transaction.objects.get(id=transaction_id)
        except Transaction.DoesNotExist:
            return None

    @staticmethod
    def get_by_txn_id(txn_id: str) -> Optional[Transaction]:
        try:
            return Transaction.objects.get(transaction_id=txn_id)
        except Transaction.DoesNotExist:
            return None

    @staticmethod
    def get_by_id_or_txn_id(identifier: str) -> Optional[Transaction]:
        """Get transaction by UUID id or string transaction_id"""
        # Try as UUID first
        try:
            import uuid
            val = uuid.UUID(identifier)
            return Transaction.objects.filter(id=val).first()
        except (ValueError, AttributeError):
            pass
        
        # Try as transaction_id
        return TransactionRepository.get_by_txn_id(identifier)

    @staticmethod
    def get_user_transactions(user) -> QuerySet:
        return Transaction.objects.filter(user=user).order_by('-created_at')

    @staticmethod
    def create(
        user, 
        transaction_id: str, 
        transaction_type: str, 
        amount: float, 
        status: str = 'PENDING',
        payment_method_type: str = 'WALLET',
        **kwargs
    ) -> Transaction:
        return Transaction.objects.create(
            user=user,
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=amount,
            status=status,
            payment_method_type=payment_method_type,
            **kwargs
        )

    @staticmethod
    def update_status(transaction_obj: Transaction, status: str) -> Transaction:
        transaction_obj.status = status
        transaction_obj.save(update_fields=['status', 'updated_at'])
        return transaction_obj
