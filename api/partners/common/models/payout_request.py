from django.db import models
from api.common.models import BaseModel
import uuid


class PayoutRequest(BaseModel):
    """
    PayoutRequest - Payout workflow for partners.
    
    Payout Types (determined by partner hierarchy):
    - CHARGEGHAR_TO_FRANCHISE: ChargeGhar pays Franchise
    - CHARGEGHAR_TO_VENDOR: ChargeGhar pays Direct Vendor
    - FRANCHISE_TO_VENDOR: Franchise pays Sub-Vendor
    
    IMPORTANT - No VAT Deduction at Payout:
    - VAT/Service Charge already deducted per-transaction in revenue_distributions
    - Partner balance already contains net share amounts
    - vat_deducted and service_charge_deducted fields = 0 (kept for audit trail only)
    - net_amount = amount (no further deductions)
    
    Business Rules:
    - BR8.1: ChargeGhar pays Franchises
    - BR8.2: ChargeGhar pays CG-level Vendors
    - BR8.3: Franchise pays Franchise-level Vendors
    - BR8.4: Non-Revenue vendors cannot create payout requests
    """
    
    class PayoutType(models.TextChoices):
        CHARGEGHAR_TO_FRANCHISE = 'CHARGEGHAR_TO_FRANCHISE', 'ChargeGhar to Franchise'
        CHARGEGHAR_TO_VENDOR = 'CHARGEGHAR_TO_VENDOR', 'ChargeGhar to Vendor'
        FRANCHISE_TO_VENDOR = 'FRANCHISE_TO_VENDOR', 'Franchise to Vendor'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'
    
    # Requester
    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.CASCADE,
        related_name='payout_requests'
    )
    
    # Payout type (auto-determined by partner hierarchy)
    payout_type = models.CharField(
        max_length=30,
        choices=PayoutType.choices
    )
    
    # Payout amount
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Requested payout amount'
    )
    
    # Deductions (kept for audit trail - always 0 since VAT already deducted)
    vat_deducted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='VAT deducted (always 0 - already in balance)'
    )
    service_charge_deducted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Service charge deducted (always 0 - already in balance)'
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Net payout amount (equals amount)'
    )
    
    # Bank details (snapshot at request time)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Reference ID (unique)
    reference_id = models.CharField(
        max_length=50,
        unique=True,
        help_text='Internal payout reference'
    )
    
    # Processing
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payout_requests'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    admin_notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'payout_requests'
        verbose_name = 'Payout Request'
        verbose_name_plural = 'Payout Requests'
        constraints = [
            # Amount must be positive
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='payout_amount_positive'
            ),
            # Valid payout type
            models.CheckConstraint(
                check=models.Q(
                    payout_type__in=[
                        'CHARGEGHAR_TO_FRANCHISE',
                        'CHARGEGHAR_TO_VENDOR',
                        'FRANCHISE_TO_VENDOR'
                    ]
                ),
                name='valid_payout_type'
            ),
            # Valid status
            models.CheckConstraint(
                check=models.Q(
                    status__in=['PENDING', 'APPROVED', 'PROCESSING', 'COMPLETED', 'REJECTED']
                ),
                name='valid_payout_status'
            ),
        ]
        indexes = [
            models.Index(fields=['partner', 'status']),
            models.Index(fields=['payout_type', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['reference_id']),
        ]

    def __str__(self):
        return f"{self.reference_id} - {self.partner.business_name} - NPR {self.amount}"
    
    def save(self, *args, **kwargs):
        # reference_id and payout_type must be set by PayoutRequestRepository.create()
        if not self.reference_id:
            raise ValueError("reference_id must be set before saving. Use PayoutRequestRepository.create()")
        if not self.payout_type:
            raise ValueError("payout_type must be set before saving. Use PayoutRequestRepository.create()")
        
        # Set net_amount = amount (no deductions)
        if not self.net_amount:
            self.net_amount = self.amount
        
        super().save(*args, **kwargs)
    
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING
    
    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED
    
    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED
    
    @property
    def can_be_processed(self):
        """Check if payout can be processed"""
        return self.status in [self.Status.PENDING, self.Status.APPROVED]
    
    @property
    def processor_entity(self):
        """
        Get the entity responsible for processing this payout.
        
        Returns:
        - 'CHARGEGHAR' for CHARGEGHAR_TO_FRANCHISE and CHARGEGHAR_TO_VENDOR
        - Partner (Franchise) for FRANCHISE_TO_VENDOR
        """
        if self.payout_type == self.PayoutType.FRANCHISE_TO_VENDOR:
            return self.partner.parent
        return 'CHARGEGHAR'
    
    # NOTE: Status transition methods moved to PayoutService:
    # - approve() -> PayoutService.approve()
    # - process() -> PayoutService.process()
    # - complete() -> PayoutService.complete()
    # - reject() -> PayoutService.reject()
