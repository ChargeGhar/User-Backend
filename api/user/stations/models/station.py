from django.db import models
from api.common.models import BaseModel


class Station(BaseModel):
    """
    Station - PowerBank Charging Station
    """
    STATION_STATUS_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    station_name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=255, unique=True)
    imei = models.CharField(max_length=255, unique=True)
    latitude = models.DecimalField(max_digits=17, decimal_places=15)
    longitude = models.DecimalField(max_digits=18, decimal_places=15)
    address = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True, help_text="Station description and additional information")
    total_slots = models.IntegerField()
    status = models.CharField(max_length=50, choices=STATION_STATUS_CHOICES, default='OFFLINE')
    is_maintenance = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    hardware_info = models.JSONField(default=dict)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    opening_time = models.TimeField(null=True, blank=True, help_text="Station opening time (e.g., 09:00)")
    closing_time = models.TimeField(null=True, blank=True, help_text="Station closing time (e.g., 21:00)")

    class Meta:
        db_table = "stations"
        verbose_name = "Station"
        verbose_name_plural = "Stations"

    def __str__(self):
        return str(self.station_name)
