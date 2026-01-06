from django.db import models
from api.common.models import BaseModel
from .transaction import Transaction


class Wallet(BaseModel):
    """
    Wallet - User's wallet for storing balance
    """
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='NPR')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "wallets"
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self):
        return f"{self.user.username} - {self.balance} {self.currency}"


class WalletTransaction(BaseModel):
    """
    WalletTransaction - Individual wallet balance changes
    """
    TRANSACTION_TYPE_CHOICES = [
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
        ('ADJUSTMENT', 'Adjustment'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True)
    
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "wallet_transactions"
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"

    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} {self.amount}"
