"""
Station Package Discount Model
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q, F

from api.common.models import BaseModel


class StationPackageDiscount(BaseModel):
    """
    Station-specific package discounts.
    Allows admins to create discounts for specific station-package combinations.
    """
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('EXPIRED', 'Expired'),
    ]
    
    # Relationships
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='package_discounts'
    )
    package = models.ForeignKey(
        'rentals.RentalPackage',
        on_delete=models.CASCADE,
        related_name='station_discounts'
    )
    
    # Discount Configuration
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0-100)"
    )
    
    # Usage Limits
    max_total_uses = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum total uses across all users. NULL = unlimited"
    )
    max_uses_per_user = models.IntegerField(
        default=1,
        help_text="Maximum uses per user"
    )
    current_usage_count = models.IntegerField(
        default=0,
        help_text="Current total usage count"
    )
    
    # Validity Period
    valid_from = models.DateTimeField(help_text="Discount valid from this date/time")
    valid_until = models.DateTimeField(help_text="Discount valid until this date/time")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    
    # Audit
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_discounts'
    )
    
    class Meta:
        db_table = 'station_package_discounts'
        verbose_name = 'Station Package Discount'
        verbose_name_plural = 'Station Package Discounts'
        unique_together = [['station', 'package']]
        indexes = [
            models.Index(fields=['station', 'status']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(discount_percent__gte=0, discount_percent__lte=100),
                name='discount_percent_range'
            ),
            models.CheckConstraint(
                check=Q(valid_until__gt=F('valid_from')),
                name='valid_date_range'
            ),
        ]
    
    def is_valid(self) -> bool:
        """Check if discount is currently valid"""
        now = timezone.now()
        return (
            self.status == 'ACTIVE' and
            self.valid_from <= now <= self.valid_until and
            (self.max_total_uses is None or self.current_usage_count < self.max_total_uses)
        )
    
    def can_user_use(self, user) -> bool:
        """Check if user can use this discount"""
        if not self.is_valid():
            return False
        
        # Import here to avoid circular dependency
        from api.user.rentals.models import Rental
        
        # Count user's usage of this discount
        user_usage_count = Rental.objects.filter(
            user=user,
            rental_metadata__discount__discount_id=str(self.id)
        ).count()
        
        return user_usage_count < self.max_uses_per_user
    
    def __str__(self):
        return f"{self.station.station_name} - {self.package.name} ({self.discount_percent}%)"
