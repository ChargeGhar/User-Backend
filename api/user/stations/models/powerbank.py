from django.db import models
from api.common.models import BaseModel
from .station import Station
from .slot import StationSlot


class PowerBank(BaseModel):
    """
    PowerBank - Physical power bank device
    """
    POWERBANK_STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('RENTED', 'Rented'),
        ('MAINTENANCE', 'Maintenance'),
        ('DAMAGED', 'Damaged'),
    ]

    serial_number = models.CharField(max_length=255, unique=True)
    model = models.CharField(max_length=255)
    capacity_mah = models.IntegerField()
    status = models.CharField(max_length=50, choices=POWERBANK_STATUS_CHOICES, default='AVAILABLE')
    battery_level = models.IntegerField(default=100)
    hardware_info = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)

    # Battery lifecycle stats
    total_cycles = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    total_rentals = models.IntegerField(default=0)
    
    current_station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True)
    current_slot = models.ForeignKey(StationSlot, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "power_banks"
        verbose_name = "Power Bank"
        verbose_name_plural = "Power Banks"

    def __str__(self):
        return f"PowerBank {self.serial_number}"
