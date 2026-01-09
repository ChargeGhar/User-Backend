from django.db import models
from api.common.models.base import BaseModel

class LateFeeConfiguration(BaseModel):
    """
    LateFeeConfiguration - Configurable late return charges for power bank rentals.
    Data model only. Business logic moved to LateFeeService.
    """

    FEE_TYPE_CHOICES = [
        ('MULTIPLIER', 'Multiplier (e.g., 2x normal rate)'),
        ('FLAT_RATE', 'Flat rate per hour'),
        ('COMPOUND', 'Compound (multiplier + flat rate)'),
    ]

    name = models.CharField(
        max_length=100,
        help_text="Choose a clear name for this fee setting (e.g., 'Standard Late Fee' or 'Holiday Double Rate')"
    )

    fee_type = models.CharField(
        max_length=50,
        choices=FEE_TYPE_CHOICES,
        default='MULTIPLIER',
        help_text="Choose how to calculate late fees."
    )

    multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        help_text="If using MULTIPLIER or COMPOUND fee type."
    )

    flat_rate_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="If using FLAT_RATE or COMPOUND fee type."
    )

    grace_period_minutes = models.IntegerField(
        default=0,
        help_text="How many minutes late before charges start applying."
    )

    max_daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum late fee per day (optional safety limit)."
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Only ONE late fee configuration can be active at a time."
    )

    applicable_package_types = models.JSONField(
        default=list,
        help_text="Advanced: Limit this configuration to specific rental package types."
    )

    metadata = models.JSONField(
        default=dict,
        help_text="Advanced system information. Usually leave empty."
    )

    class Meta:
        db_table = "late_fee_configurations"
        verbose_name = "Late Fee Configuration"
        verbose_name_plural = "Late Fee Configurations"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_fee_type_display()}"

    def calculate_late_fee(self, normal_rate_per_minute, overdue_minutes):
        """Proxy to LateFeeService for backward compatibility"""
        from api.user.rentals.services.late_fee_service import LateFeeService
        return LateFeeService.calculate_late_fee(self, normal_rate_per_minute, overdue_minutes)

    def get_description(self):
        """Proxy to LateFeeService for backward compatibility"""
        from api.user.rentals.services.late_fee_service import LateFeeService
        return LateFeeService.get_description(self)
