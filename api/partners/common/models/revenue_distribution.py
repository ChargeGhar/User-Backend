from django.db import models
from api.common.models import BaseModel


class RevenueDistribution(BaseModel):
    """
    RevenueDistribution - Per-transaction revenue calculation and allocation.
    
    Created when a rental transaction is completed. Calculates and stores
    the revenue split between ChargeGhar, Franchise, and Vendor.
    
    VAT & Service Charge - DEFINITIVE RULE:
    - VAT and Service Charge are deducted PER TRANSACTION when rental completes
    - net_amount = gross_amount - vat_amount - service_charge
    - ALL partner share calculations use net_amount
    - Partner balance accumulates shares already calculated from net revenue
    
    Business Rules:
    - BR4.1-3: All transactions collected by ChargeGhar
    - BR5.1-5: VAT & Service Charge rules
    - BR6.1-3: ChargeGhar station revenue distribution
    - BR7.1-5: Franchise station revenue distribution
    - BR11.1-5: Financial calculation rules
    """
    
    # Source transaction
    transaction = models.ForeignKey(
        'payments.Transaction',
        on_delete=models.CASCADE,
        related_name='revenue_distributions'
    )
    rental = models.ForeignKey(
        'rentals.Rental',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revenue_distributions'
    )
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='revenue_distributions'
    )
    
    # Revenue breakdown
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Total transaction amount'
    )
    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='VAT deducted at ChargeGhar level'
    )
    service_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Service charge deducted at ChargeGhar level'
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='gross - vat - service_charge'
    )
    
    # Share allocation
    chargeghar_share = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='ChargeGhar retains this amount'
    )
    
    # Franchise share (if franchise station)
    franchise = models.ForeignKey(
        'partners.Partner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='franchise_revenue_distributions',
        help_text='Franchise partner (if station owned by franchise)'
    )
    franchise_share = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Franchise share amount'
    )
    
    # Vendor share (if vendor operates station)
    vendor = models.ForeignKey(
        'partners.Partner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_revenue_distributions',
        help_text='Vendor partner (if station operated by vendor)'
    )
    vendor_share = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Vendor share amount'
    )
    
    # Distribution status
    is_distributed = models.BooleanField(
        default=False,
        help_text='Has this been added to partner balances?'
    )
    distributed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When partner balances were updated'
    )
    
    # Calculation metadata (for audit)
    calculation_details = models.JSONField(
        default=dict,
        help_text='Detailed breakdown of calculation for audit'
    )
    
    # Reversal tracking
    is_reversal = models.BooleanField(
        default=False,
        help_text='Is this a reversal distribution (negative amounts for refunds)?'
    )
    reversed_distribution = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reversals',
        help_text='Original distribution being reversed (for refunds)'
    )
    reversal_reason = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('FULL_REFUND', 'Full Refund'),
            ('PARTIAL_REFUND', 'Partial Refund'),
        ],
        help_text='Reason for reversal'
    )
    class Meta:
        db_table = 'revenue_distributions'
        verbose_name = 'Revenue Distribution'
        verbose_name_plural = 'Revenue Distributions'
        indexes = [
            models.Index(fields=['transaction']),
            models.Index(fields=['station', 'created_at']),
            models.Index(fields=['franchise', 'is_distributed']),
            models.Index(fields=['vendor', 'is_distributed']),
            models.Index(fields=['is_distributed']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Rev Dist {self.id} - NPR {self.gross_amount}"
    
    @property
    def has_franchise(self):
        """Check if this distribution involves a franchise"""
        return self.franchise is not None
    
    @property
    def has_vendor(self):
        """Check if this distribution involves a vendor"""
        return self.vendor is not None
    
    # NOTE: Business logic methods moved to RevenueDistributionService:
    # - calculate_shares() -> RevenueDistributionService.calculate_shares()
    # - distribute_to_balances() -> RevenueDistributionService.distribute_to_balances()
