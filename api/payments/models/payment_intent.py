from django.db import models
from api.common.models import BaseModel


class PaymentIntent(BaseModel):
    """
    PaymentIntent - Payment intents for gateway transactions
    """
    INTENT_TYPE_CHOICES = [
        ('WALLET_TOPUP', 'Wallet Top Up'),
        ('RENTAL_PAYMENT', 'Rental Payment'),
        ('DUE_PAYMENT', 'Due Payment'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='payment_intents')
    related_rental = models.ForeignKey('rentals.Rental', on_delete=models.SET_NULL, null=True, blank=True)
    
    intent_id = models.CharField(max_length=255, unique=True)
    intent_type = models.CharField(max_length=50, choices=INTENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NPR')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    gateway_url = models.URLField(null=True, blank=True)
    intent_metadata = models.JSONField(default=dict)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_intents"
        verbose_name = "Payment Intent"
        verbose_name_plural = "Payment Intents"

    def __str__(self):
        return f"{self.intent_id} - {self.intent_type}"
