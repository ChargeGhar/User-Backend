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
    
    def update_battery_cycle(self, start_level: int, end_level: int, rental=None):
        """
        Update battery cycle stats and create log.
        
        Args:
            start_level: Battery level at rental start (0-100)
            end_level: Battery level at rental return (0-100)
            rental: Rental instance (optional, for logging)
        
        Returns:
            cycle_contribution: Decimal cycles added
        """
        from decimal import Decimal
        from api.user.rentals.models import BatteryCycleLog
        
        discharge = max(0, start_level - end_level)
        if discharge == 0:
            return Decimal('0.0000')
        
        cycle_contribution = (Decimal(discharge) / Decimal(100)).quantize(Decimal('0.0001'))
        
        # Create detailed log
        BatteryCycleLog.objects.create(
            powerbank=self,
            rental=rental,
            start_level=start_level,
            end_level=end_level,
            discharge_percent=Decimal(discharge),
            cycle_contribution=cycle_contribution
        )
        
        # Update cumulative stats
        self.total_cycles += cycle_contribution
        self.total_rentals += 1
        self.save(update_fields=['total_cycles', 'total_rentals', 'updated_at'])
        
        return cycle_contribution
    
    def get_lifecycle_stats(self):
        """
        Get battery lifecycle statistics.
        
        Returns:
            dict: Lifecycle stats including total cycles, rentals, and averages
        """
        from decimal import Decimal
        from django.db.models import Sum, Avg, Count
        
        stats = self.cycle_logs.aggregate(
            total_discharge=Sum('discharge_percent'),
            avg_discharge=Avg('discharge_percent'),
            log_count=Count('id')
        )
        
        avg_cycles_per_rental = (
            (self.total_cycles / Decimal(self.total_rentals))
            if self.total_rentals > 0 
            else Decimal('0')
        )
        
        return {
            'total_cycles': self.total_cycles,
            'total_rentals': self.total_rentals,
            'avg_cycles_per_rental': avg_cycles_per_rental,
            'total_discharge_percent': stats['total_discharge'] or Decimal('0'),
            'avg_discharge_per_rental': stats['avg_discharge'] or Decimal('0'),
            'cycle_log_count': stats['log_count'] or 0
        }
    
    def get_recent_cycle_logs(self, limit=10):
        """
        Get recent battery cycle logs.
        
        Args:
            limit: Number of recent logs to return (default: 10)
        
        Returns:
            QuerySet: Recent BatteryCycleLog instances
        """
        return self.cycle_logs.select_related('rental').order_by('-created_at')[:limit]
