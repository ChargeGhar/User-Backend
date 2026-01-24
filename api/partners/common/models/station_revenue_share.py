from django.db import models
from api.common.models import BaseModel


class StationRevenueShare(BaseModel):
    """
    StationRevenueShare - Revenue model configuration per station distribution.
    
    IMPORTANT:
    - Franchise revenue model: Stored in partners.revenue_share_percent
    - Vendor revenue model: Stored in this table (partner_percent or fixed_amount)
    
    This table is ONLY created for REVENUE vendors, NOT for:
    - FRANCHISE (uses partners.revenue_share_percent)
    - NON_REVENUE vendors (no revenue model)
    
    Business Rules:
    - BR3.3: Revenue model options - Fixed OR Percentage
    - BR3.4: Non-Revenue vendors have NO revenue model
    - BR6.2: CG Vendor gets partner_percent of net revenue
    - BR7.4: Franchise Vendor gets partner_percent from Franchise's share
    - BR11.4-5: Fixed = same monthly, Percentage = varies by performance
    """
    
    class RevenueModel(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage of Net Revenue'
        FIXED = 'FIXED', 'Fixed Monthly Amount'
    
    # Link to distribution (1:1)
    distribution = models.OneToOneField(
        'partners.StationDistribution',
        on_delete=models.CASCADE,
        related_name='revenue_share'
    )
    
    # Revenue model type
    revenue_model = models.CharField(
        max_length=20,
        choices=RevenueModel.choices
    )
    
    # Percentage model fields
    partner_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Vendor share percentage (e.g., 10.00 for 10%)'
    )
    
    # Fixed model fields
    fixed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Fixed monthly amount vendor pays to owner'
    )

    class Meta:
        db_table = 'station_revenue_shares'
        verbose_name = 'Station Revenue Share'
        verbose_name_plural = 'Station Revenue Shares'
        constraints = [
            # Valid revenue model
            models.CheckConstraint(
                check=models.Q(revenue_model__in=['PERCENTAGE', 'FIXED']),
                name='valid_revenue_model'
            ),
            # Percentage model must have partner_percent
            models.CheckConstraint(
                check=(
                    models.Q(revenue_model='FIXED') |
                    (models.Q(revenue_model='PERCENTAGE') & models.Q(partner_percent__isnull=False))
                ),
                name='percentage_model_must_have_percent'
            ),
            # Fixed model must have fixed_amount
            models.CheckConstraint(
                check=(
                    models.Q(revenue_model='PERCENTAGE') |
                    (models.Q(revenue_model='FIXED') & models.Q(fixed_amount__isnull=False))
                ),
                name='fixed_model_must_have_amount'
            ),
            # Partner percent must be valid (0-100)
            models.CheckConstraint(
                check=(
                    models.Q(partner_percent__isnull=True) |
                    (models.Q(partner_percent__gte=0) & models.Q(partner_percent__lte=100))
                ),
                name='valid_partner_percent'
            ),
            # Fixed amount must be non-negative
            models.CheckConstraint(
                check=(
                    models.Q(fixed_amount__isnull=True) |
                    models.Q(fixed_amount__gte=0)
                ),
                name='valid_fixed_amount'
            ),
        ]
        indexes = [
            models.Index(fields=['distribution']),
            models.Index(fields=['revenue_model']),
        ]

    def __str__(self):
        if self.revenue_model == self.RevenueModel.PERCENTAGE:
            return f"{self.distribution.partner.business_name} - {self.partner_percent}%"
        return f"{self.distribution.partner.business_name} - Fixed NPR {self.fixed_amount}"
    
    @property
    def is_percentage_model(self):
        """Check if using percentage model"""
        return self.revenue_model == self.RevenueModel.PERCENTAGE
    
    @property
    def is_fixed_model(self):
        """Check if using fixed model"""
        return self.revenue_model == self.RevenueModel.FIXED
