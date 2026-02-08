from django.db import models
from api.common.models import BaseModel


class Partner(BaseModel):
    """
    Partner - Represents Franchise or Vendor in the ChargeGhar system.
    
    Hierarchy:
    - parent_id IS NULL + partner_type='FRANCHISE' → Franchise under ChargeGhar
    - parent_id IS NULL + partner_type='VENDOR' → Direct Vendor under ChargeGhar
    - parent_id IS NOT NULL + partner_type='VENDOR' → Sub-Vendor under Franchise
    
    Business Rules:
    - BR1.2: ChargeGhar creates Franchises
    - BR1.3: ChargeGhar creates own Vendors
    - BR1.5: Franchise creates own Vendors
    - BR1.7: Non-Revenue Vendors have no dashboard access
    - BR9.1-6: Vendor type rules
    """
    
    class PartnerType(models.TextChoices):
        FRANCHISE = 'FRANCHISE', 'Franchise'
        VENDOR = 'VENDOR', 'Vendor'
    
    class VendorType(models.TextChoices):
        REVENUE = 'REVENUE', 'Revenue Vendor'
        NON_REVENUE = 'NON_REVENUE', 'Non-Revenue Vendor'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        SUSPENDED = 'SUSPENDED', 'Suspended'
    
    # Link to existing user (OneToOne)
    user = models.OneToOneField(
        'users.User',
        on_delete=models.PROTECT,
        related_name='partner_profile'
    )
    
    # Partner classification
    partner_type = models.CharField(
        max_length=20,
        choices=PartnerType.choices
    )
    vendor_type = models.CharField(
        max_length=20,
        choices=VendorType.choices,
        null=True,
        blank=True,
        help_text='Only applicable for VENDOR partner_type'
    )
    
    # Hierarchy: NULL = under ChargeGhar, FK = under that Franchise
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_partners',
        help_text='NULL for ChargeGhar-level, FK to Franchise for sub-vendors'
    )
    
    # Business info
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Partner code e.g., FR-001, VN-001'
    )
    business_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # Franchise-specific fields (BR3.5)
    upfront_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='One-time upfront payment received from Franchise'
    )
    revenue_share_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Franchise revenue share % (y% of station net revenue)'
    )
    
    # Balances (denormalized for quick access)
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Available balance for payout'
    )
    total_earnings = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Lifetime total earnings'
    )
    
    # Admin tracking
    assigned_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_partners'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'partners'
        verbose_name = 'Partner'
        verbose_name_plural = 'Partners'
        constraints = [
            # Vendor must have vendor_type
            models.CheckConstraint(
                check=(
                    models.Q(partner_type='FRANCHISE') |
                    (models.Q(partner_type='VENDOR') & models.Q(vendor_type__isnull=False))
                ),
                name='vendor_must_have_vendor_type'
            ),
            # Franchise cannot have vendor_type
            models.CheckConstraint(
                check=(
                    models.Q(partner_type='VENDOR') |
                    (models.Q(partner_type='FRANCHISE') & models.Q(vendor_type__isnull=True))
                ),
                name='franchise_cannot_have_vendor_type'
            ),
            # Franchise must be under ChargeGhar (parent_id = NULL)
            models.CheckConstraint(
                check=(
                    models.Q(partner_type='VENDOR') |
                    (models.Q(partner_type='FRANCHISE') & models.Q(parent__isnull=True))
                ),
                name='franchise_must_be_under_chargeghar'
            ),
            # Revenue share percent must be valid
            models.CheckConstraint(
                check=(
                    models.Q(revenue_share_percent__isnull=True) |
                    (models.Q(revenue_share_percent__gte=0) & models.Q(revenue_share_percent__lte=100))
                ),
                name='valid_revenue_share_percent'
            ),
        ]
        indexes = [
            models.Index(fields=['partner_type', 'status']),
            models.Index(fields=['parent']),
            models.Index(fields=['code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.code} - {self.business_name}"
    
    @property
    def is_franchise(self):
        """Check if partner is a Franchise"""
        return self.partner_type == self.PartnerType.FRANCHISE
    
    @property
    def is_vendor(self):
        """Check if partner is a Vendor"""
        return self.partner_type == self.PartnerType.VENDOR
    
    @property
    def is_revenue_vendor(self):
        """Check if partner is a Revenue Vendor (has dashboard access)"""
        return self.is_vendor and self.vendor_type == self.VendorType.REVENUE
    
    @property
    def is_non_revenue_vendor(self):
        """Check if partner is a Non-Revenue Vendor"""
        return self.is_vendor and self.vendor_type == self.VendorType.NON_REVENUE
    
    @property
    def is_chargeghar_level(self):
        """Check if partner is directly under ChargeGhar"""
        return self.parent is None
    
    @property
    def has_dashboard_access(self):
        """Check if partner has dashboard access (BR9.2, BR9.4)"""
        if self.is_franchise:
            return True
        if self.is_revenue_vendor:
            return True
        return False
    
    @property
    def owner_name(self):
        """Get the owner name for display"""
        if self.parent:
            return self.parent.business_name
        return "ChargeGhar"
    
    def save(self, *args, **kwargs):
        # Code generation is handled by PartnerRepository.create()
        # This ensures code is set before save
        if not self.code:
            raise ValueError("Partner code must be set before saving. Use PartnerRepository.create()")
        super().save(*args, **kwargs)
