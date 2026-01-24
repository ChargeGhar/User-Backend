from django.db import models
from api.common.models import BaseModel


class PartnerIotHistory(BaseModel):
    """
    PartnerIotHistory - Audit log for IoT actions performed by partners.
    
    Action Permissions:
    - FRANCHISE: EJECT, REBOOT, CHECK, WIFI_SCAN, WIFI_CONNECT, VOLUME, MODE
    - VENDOR (any): REBOOT, CHECK, WIFI_SCAN, WIFI_CONNECT, VOLUME, MODE
    - VENDOR (free eject): EJECT (1 per day via rental flow only)
    
    Business Rules:
    - BR13.1: Track all IoT actions with action_type
    - BR13.2: Vendor 1 free eject/day (is_free_ejection check)
    - BR13.3: Franchise unlimited eject from Dashboard
    - BR13.4: Control rights validated by partner type
    """
    
    class ActionType(models.TextChoices):
        EJECT = 'EJECT', 'Eject Powerbank'
        REBOOT = 'REBOOT', 'Reboot Station'
        CHECK = 'CHECK', 'Check Status'
        WIFI_SCAN = 'WIFI_SCAN', 'WiFi Scan'
        WIFI_CONNECT = 'WIFI_CONNECT', 'WiFi Connect'
        VOLUME = 'VOLUME', 'Volume Control'
        MODE = 'MODE', 'SIM/WiFi Mode'
    
    class PerformedFrom(models.TextChoices):
        MOBILE_APP = 'MOBILE_APP', 'Mobile App'
        DASHBOARD = 'DASHBOARD', 'Dashboard'
        ADMIN_PANEL = 'ADMIN_PANEL', 'Admin Panel'
    
    # Who performed
    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.CASCADE,
        related_name='iot_history'
    )
    performed_by = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='partner_iot_actions'
    )
    
    # Target station
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='partner_iot_history'
    )
    
    # Action details
    action_type = models.CharField(
        max_length=20,
        choices=ActionType.choices
    )
    performed_from = models.CharField(
        max_length=20,
        choices=PerformedFrom.choices
    )
    
    # For EJECT actions
    powerbank_sn = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Powerbank serial number (for EJECT)'
    )
    slot_number = models.IntegerField(
        null=True,
        blank=True,
        help_text='Slot number (for EJECT)'
    )
    rental = models.ForeignKey(
        'rentals.Rental',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_iot_actions',
        help_text='Related rental (for free ejection)'
    )
    is_free_ejection = models.BooleanField(
        default=False,
        help_text='True if vendor free daily ejection'
    )
    
    # Result
    is_successful = models.BooleanField(
        help_text='Whether the action was successful'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if action failed'
    )
    request_payload = models.JSONField(
        default=dict,
        help_text='Request payload sent to IoT'
    )
    response_data = models.JSONField(
        default=dict,
        help_text='Response data from IoT'
    )
    
    # Client info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'partner_iot_history'
        verbose_name = 'Partner IoT History'
        verbose_name_plural = 'Partner IoT Histories'
        constraints = [
            # Valid action type
            models.CheckConstraint(
                check=models.Q(
                    action_type__in=[
                        'EJECT', 'REBOOT', 'CHECK', 
                        'WIFI_SCAN', 'WIFI_CONNECT', 'VOLUME', 'MODE'
                    ]
                ),
                name='valid_iot_action_type'
            ),
            # Valid performed_from
            models.CheckConstraint(
                check=models.Q(
                    performed_from__in=['MOBILE_APP', 'DASHBOARD', 'ADMIN_PANEL']
                ),
                name='valid_performed_from'
            ),
        ]
        indexes = [
            models.Index(fields=['partner', 'action_type', 'created_at']),
            models.Index(fields=['station', 'created_at']),
            models.Index(fields=['action_type', 'is_successful']),
            models.Index(fields=['created_at']),
        ]
        # Index for free ejection check (partial index in PostgreSQL)
        # Note: Django doesn't directly support partial indexes in Meta,
        # but this can be added via migration

    def __str__(self):
        return f"{self.partner.business_name} - {self.action_type} - {self.station.station_name}"
    
    @property
    def is_eject_action(self):
        """Check if this is an eject action"""
        return self.action_type == self.ActionType.EJECT
    
    @classmethod
    def check_vendor_free_ejection_available(cls, partner):
        """
        Check if vendor has free ejection available today.
        
        Returns True if vendor hasn't used their free ejection today.
        Returns False if already used.
        
        Note: This only applies to VENDOR partners.
        Franchise has unlimited ejections.
        """
        from django.utils import timezone
        
        if not partner.is_vendor:
            # Franchise has unlimited ejections
            return True
        
        today = timezone.now().date()
        
        used_today = cls.objects.filter(
            partner=partner,
            action_type=cls.ActionType.EJECT,
            is_free_ejection=True,
            created_at__date=today
        ).exists()
        
        return not used_today
    
    @classmethod
    def get_vendor_free_ejection_count_today(cls, partner):
        """Get the count of free ejections used today by vendor"""
        from django.utils import timezone
        
        today = timezone.now().date()
        
        return cls.objects.filter(
            partner=partner,
            action_type=cls.ActionType.EJECT,
            is_free_ejection=True,
            created_at__date=today
        ).count()
    
    @classmethod
    def can_partner_perform_action(cls, partner, action_type):
        """
        Check if partner can perform the given action type.
        
        Franchise: All actions allowed
        Vendor: All except EJECT (EJECT only via rental flow)
        """
        # Franchise can do everything
        if partner.is_franchise:
            return True
        
        # Vendor cannot perform EJECT through IoT endpoints
        # (must use rental flow for free ejection)
        if action_type == cls.ActionType.EJECT:
            return False
        
        # Vendor can perform other actions
        return True
