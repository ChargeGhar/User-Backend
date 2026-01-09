from __future__ import annotations

from decimal import Decimal
from django.db import transaction

from api.common.services.base import CRUDService, ServiceException
from api.user.payments.models import Wallet, Transaction
from api.user.payments.repositories import WalletRepository

class WalletService(CRUDService):
    """Service for wallet operations"""
    model = Wallet

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = WalletRepository()

    def get_or_create_wallet(self, user) -> Wallet:
        """Get or create user wallet"""
        try:
            wallet, created = self.repository.get_or_create(user)
            return wallet
        except Exception as e:
            self.handle_service_error(e, "Failed to get or create wallet")

    @transaction.atomic
    def add_balance(self, user, amount: Decimal, description: str, transaction_obj: Transaction = None):
        """Add balance to user wallet"""
        try:
            wallet = self.get_or_create_wallet(user)

            balance_before = wallet.balance
            wallet.balance += amount
            wallet.save(update_fields=['balance', 'updated_at'])

            # Create wallet transaction record using repository
            wallet_transaction = self.repository.create_wallet_transaction(
                wallet=wallet,
                transaction_obj=transaction_obj,
                transaction_type='CREDIT',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description
            )

            self.log_info(f"Balance added to wallet: {user.username} +{amount}")
            return wallet_transaction

        except Exception as e:
            self.handle_service_error(e, "Failed to add wallet balance")

    @transaction.atomic
    def deduct_balance(self, user, amount: Decimal, description: str, transaction_obj: Transaction = None):
        """Deduct balance from user wallet"""
        try:
            wallet = self.get_or_create_wallet(user)

            if wallet.balance < amount:
                raise ServiceException(
                    detail="Insufficient wallet balance",
                    code="insufficient_balance"
                )

            balance_before = wallet.balance
            wallet.balance -= amount
            wallet.save(update_fields=['balance', 'updated_at'])

            # Create wallet transaction record using repository
            wallet_transaction = self.repository.create_wallet_transaction(
                wallet=wallet,
                transaction_obj=transaction_obj,
                transaction_type='DEBIT',
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                description=description
            )

            self.log_info(f"Balance deducted from wallet: {user.username} -{amount}")
            return wallet_transaction

        except Exception as e:
            self.handle_service_error(e, "Failed to deduct wallet balance")

    def get_wallet_balance(self, user) -> dict:
        """Get user wallet balance with recent transactions"""
        try:
            wallet = self.get_or_create_wallet(user)
            
            # Get recent wallet transactions using repository
            recent_transactions = self.repository.get_recent_transactions(wallet)
            
            from api.user.payments.serializers import WalletTransactionSerializer
            transaction_serializer = WalletTransactionSerializer(recent_transactions, many=True)
            
            return {
                'balance': wallet.balance,
                'currency': wallet.currency,
                'formatted_balance': f"{wallet.currency} {wallet.balance:,.2f}",
                'is_active': wallet.is_active,
                'recent_transactions': transaction_serializer.data,
                'last_updated': wallet.updated_at
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get wallet balance")
