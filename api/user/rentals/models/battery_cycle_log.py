from django.db import models
from api.common.models import BaseModel


class BatteryCycleLog(BaseModel):
    """
    Battery Cycle Log - Tracks battery discharge cycles per rental
    """
    powerbank = models.ForeignKey(
        'stations.PowerBank',
        on_delete=models.CASCADE,
        related_name='cycle_logs'
    )
    rental = models.ForeignKey(
        'Rental',
        on_delete=models.CASCADE,
        related_name='cycle_logs'
    )
    start_level = models.IntegerField()
    end_level = models.IntegerField()
    discharge_percent = models.DecimalField(max_digits=5, decimal_places=2)
    cycle_contribution = models.DecimalField(max_digits=5, decimal_places=4)
    
    class Meta:
        db_table = 'battery_cycle_logs'
        verbose_name = 'Battery Cycle Log'
        verbose_name_plural = 'Battery Cycle Logs'
        indexes = [
            models.Index(fields=['powerbank', 'created_at']),
            models.Index(fields=['rental']),
        ]
    
    def __str__(self):
        return f"Cycle Log {self.rental.rental_code} - {self.cycle_contribution} cycles"
