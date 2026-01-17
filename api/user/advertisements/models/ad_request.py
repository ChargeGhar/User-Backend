"""
AdRequest Model
===============
Represents an advertisement request submitted by a user.
"""
from django.db import models
from api.common.models import BaseModel


class AdRequest(BaseModel):
    """
    AdRequest - Advertisement request submitted by user
    """
    
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),            # Awaiting admin review
        ('UNDER_REVIEW', 'Under Review'),      # Admin reviewing
        ('APPROVED', 'Approved'),              # Approved, price set
        ('REJECTED', 'Rejected'),              # Admin rejected
        ('PENDING_PAYMENT', 'Pending Payment'), # Awaiting user payment
        ('PAID', 'Paid'),                      # Payment received
        ('SCHEDULED', 'Scheduled'),            # Waiting for start_date
        ('RUNNING', 'Running'),                # Currently active
        ('PAUSED', 'Paused'),                  # Temporarily paused
        ('COMPLETED', 'Completed'),            # Duration ended
        ('CANCELLED', 'Cancelled'),            # User/Admin cancelled
    ]
    
    # User information
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='ad_requests',
        help_text="User who submitted the ad request"
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Full name of the advertiser"
    )
    contact_number = models.CharField(
        max_length=50,
        help_text="Contact number for the advertiser"
    )
    
    # Ad details (set by admin)
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Ad title (set by admin)"
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Ad description (set by admin)"
    )
    duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration in days (set by admin)"
    )
    
    # Status and workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SUBMITTED',
        help_text="Current status of the ad request"
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ad was submitted"
    )
    
    # Admin review
    reviewed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_ads',
        help_text="Admin who reviewed the ad"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ad was reviewed"
    )
    admin_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price set by admin"
    )
    admin_notes = models.TextField(
        null=True,
        blank=True,
        help_text="Admin notes about the ad"
    )
    rejection_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Reason for rejection if rejected"
    )
    
    # Approval
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_ads',
        help_text="Admin who approved the ad"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ad was approved"
    )
    
    # Payment
    transaction = models.ForeignKey(
        'payments.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ad_requests',
        help_text="Payment transaction"
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was received"
    )
    
    # Schedule
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When ad starts running"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When ad ends"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ad was completed"
    )
    
    class Meta:
        db_table = 'ad_requests'
        verbose_name = 'Ad Request'
        verbose_name_plural = 'Ad Requests'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['status', 'end_date']),
            models.Index(fields=['status', 'paid_at']),
            models.Index(fields=['user', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title or 'Untitled'} - {self.user.username} ({self.status})"
