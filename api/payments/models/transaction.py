from django.db import models
from api.common.models import BaseModel


class Transaction(BaseModel):
    """
    Transaction - All financial transactions in the system
    """
    TRANSACTION_TYPE_CHOICES = [
        ('TOPUP', 'Top Up'),
        ('RENTAL', 'Rental'),
        ('RENTAL_DUE', 'Rental Due'),
        ('REFUND', 'Refund'),
        ('FINE', 'Fine'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    PAYMENT_METHOD_TYPE_CHOICES = [
        ('WALLET', 'Wallet'),
        ('POINTS', 'Points'),
        ('COMBINATION', 'Combination'),
        ('GATEWAY', 'Gateway'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='transactions')
    related_rental = models.ForeignKey('rentals.Rental', on_delete=models.SET_NULL, null=True, blank=True)
    
    transaction_id = models.CharField(max_length=255, unique=True)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NPR')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    payment_method_type = models.CharField(max_length=50, choices=PAYMENT_METHOD_TYPE_CHOICES)
    
    gateway_reference = models.CharField(max_length=255, null=True, blank=True)
    gateway_response = models.JSONField(default=dict)

    class Meta:
        db_table = "transactions"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.transaction_id} - {self.transaction_type}"
