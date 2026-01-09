from django.db import models
from api.common.models import BaseModel
from .station import Station


class StationSlot(BaseModel):
    """
    StationSlot - Individual slot in a charging station
    """
    SLOT_STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('MAINTENANCE', 'Maintenance'),
        ('ERROR', 'Error'),
    ]

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='slots')
    slot_number = models.IntegerField()
    status = models.CharField(max_length=50, choices=SLOT_STATUS_CHOICES, default='AVAILABLE')
    battery_level = models.IntegerField(default=0)
    slot_metadata = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)
    current_rental = models.ForeignKey('rentals.Rental', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "station_slots"
        verbose_name = "Station Slot"
        verbose_name_plural = "Station Slots"
        unique_together = ['station', 'slot_number']

    def __str__(self):
        return f"{self.station.station_name} - Slot {self.slot_number}"
