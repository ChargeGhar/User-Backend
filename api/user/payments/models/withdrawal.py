from django.db import models
from api.common.models import BaseModel
from .payment_method import PaymentMethod


class WithdrawalRequest(BaseModel):
    """
    WithdrawalRequest - User withdrawal requests
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Account details (denormalized for easier reporting/filtering)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    account_number = models.CharField(max_length=255, null=True, blank=True)
    account_holder_name = models.CharField(max_length=255, null=True, blank=True)
    
    processing_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Reuse existing PaymentMethod model for withdrawal methods
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    account_details = models.JSONField(default=dict, help_text='Bank account, eSewa phone, Khalti phone details')
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='REQUESTED')
    admin_notes = models.TextField(blank=True, null=True, help_text='Notes from admin regarding the withdrawal')
    
    # Admin tracking
    processed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_withdrawals')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Reference tracking
    gateway_reference = models.CharField(max_length=255, null=True, blank=True)
    internal_reference = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "withdrawal_requests"
        verbose_name = "Withdrawal Request"
        verbose_name_plural = "Withdrawal Requests"
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.internal_reference} - {self.user.username} - NPR {self.amount}"
