from typing import Optional, Tuple
from api.payments.models import Wallet, Transaction
from django.db.models import Sum

class WalletRepository:
    """Repository for Wallet data operations"""
    
    @staticmethod
    def get_by_user_id(user_id: str) -> Optional[Wallet]:
        try:
            return Wallet.objects.get(user_id=user_id)
        except Wallet.DoesNotExist:
            return None

    @staticmethod
    def get_or_create(user) -> Tuple[Wallet, bool]:
        return Wallet.objects.get_or_create(user=user)

    @staticmethod
    def create_wallet(user, currency: str = 'NPR') -> Wallet:
        return Wallet.objects.create(user=user, currency=currency)

    @staticmethod
    def get_total_topup(user_id: str) -> float:
        return Transaction.objects.filter(
            user_id=user_id, transaction_type='TOPUP', status='SUCCESS'
        ).aggregate(total=Sum('amount'))['total'] or 0.0
