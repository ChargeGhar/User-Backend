from django.db import models
from api.common.models import BaseModel


class StationDistribution(BaseModel):
    """
    StationDistribution - Links stations to partners.
    
    Distribution Types:
    - CHARGEGHAR_TO_FRANCHISE: ChargeGhar assigns station to Franchise (ownership + operation)
    - CHARGEGHAR_TO_VENDOR: ChargeGhar assigns station operation to Direct Vendor
    - FRANCHISE_TO_VENDOR: Franchise assigns their station operation to Sub-Vendor
    
    Business Rules:
    - BR2.1: ChargeGhar assigns to CG Vendors while creating them
    - BR2.2: Franchise assigns to F Vendors while creating them
    - BR2.3: Vendor can have ONLY ONE station (service layer validation)
    - BR2.4: Station can have only ONE operator at a time (unique index)
    """
    
    class DistributionType(models.TextChoices):
        CHARGEGHAR_TO_FRANCHISE = 'CHARGEGHAR_TO_FRANCHISE', 'ChargeGhar to Franchise'
        CHARGEGHAR_TO_VENDOR = 'CHARGEGHAR_TO_VENDOR', 'ChargeGhar to Vendor'
        FRANCHISE_TO_VENDOR = 'FRANCHISE_TO_VENDOR', 'Franchise to Vendor'
    
    # Station being assigned
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='partner_distributions'
    )
    
    # Partner receiving station
    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.CASCADE,
        related_name='station_distributions'
    )
    
    # Distribution type (determined by hierarchy)
    distribution_type = models.CharField(
        max_length=30,
        choices=DistributionType.choices
    )
    
    # Validity period
    effective_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Admin tracking
    assigned_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_station_distributions'
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'station_distributions'
        verbose_name = 'Station Distribution'
        verbose_name_plural = 'Station Distributions'
        constraints = [
            # Valid distribution type
            models.CheckConstraint(
                check=models.Q(
                    distribution_type__in=[
                        'CHARGEGHAR_TO_FRANCHISE',
                        'CHARGEGHAR_TO_VENDOR',
                        'FRANCHISE_TO_VENDOR'
                    ]
                ),
                name='valid_distribution_type'
            ),
        ]
        indexes = [
            models.Index(fields=['station', 'is_active']),
            models.Index(fields=['partner', 'is_active']),
            models.Index(fields=['distribution_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.station.station_name} -> {self.partner.business_name}"
    
    @property
    def is_ownership(self):
        """Check if this is ownership assignment (Franchise)"""
        return self.distribution_type == self.DistributionType.CHARGEGHAR_TO_FRANCHISE
    
    @property
    def is_operation(self):
        """Check if this is operation assignment (Vendor)"""
        return self.distribution_type in [
            self.DistributionType.CHARGEGHAR_TO_VENDOR,
            self.DistributionType.FRANCHISE_TO_VENDOR
        ]
    
    # NOTE: Query methods moved to StationDistributionRepository:
    # - get_station_operator() -> StationDistributionRepository.get_station_operator()
    # - get_station_franchise() -> StationDistributionRepository.get_station_franchise()
