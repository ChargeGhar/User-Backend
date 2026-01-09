from typing import Optional, Tuple
from decimal import Decimal
from django.db.models import QuerySet
from api.user.payments.models import Wallet, Transaction, WalletTransaction
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
        return Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal('0'), 'currency': 'NPR'}
        )

    @staticmethod
    def create_wallet_transaction(
        wallet,
        transaction_type: str,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        description: str,
        transaction_obj = None
    ) -> WalletTransaction:
        from api.user.payments.models import WalletTransaction
        return WalletTransaction.objects.create(
            wallet=wallet,
            transaction=transaction_obj,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description
        )

    @staticmethod
    def get_recent_transactions(wallet, limit: int = 5) -> QuerySet:
        from api.user.payments.models import WalletTransaction
        return WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[:limit]

    @staticmethod
    def create_wallet(user, currency: str = 'NPR') -> Wallet:
        return Wallet.objects.create(user=user, currency=currency)

    @staticmethod
    def get_total_topup(user_id: str) -> float:
        return Transaction.objects.filter(
            user_id=user_id, transaction_type='TOPUP', status='SUCCESS'
        ).aggregate(total=Sum('amount'))['total'] or 0.0
