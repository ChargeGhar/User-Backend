from django.db import models
from api.common.models import BaseModel
from .transaction import Transaction


class Refund(BaseModel):
    """
    Refund - Refund requests and processing
    """
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PROCESSED', 'Processed'),
    ]

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='refunds')
    requested_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='requested_refunds')
    approved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_refunds')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='REQUESTED')
    admin_notes = models.TextField(blank=True, null=True, help_text='Notes from admin regarding the refund')
    gateway_reference = models.CharField(max_length=255, null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "refunds"
        verbose_name = "Refund"
        verbose_name_plural = "Refunds"

    def __str__(self):
        return f"Refund {self.amount} - {self.transaction.transaction_id}"
