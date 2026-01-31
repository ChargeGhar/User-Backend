"""
Station Status History Model
"""
from django.db import models
from api.common.models import BaseModel


class StationStatusHistory(BaseModel):
    """Track station online/offline status changes"""
    
    STATUS_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    TRIGGERED_BY_CHOICES = [
        ('SYNC', 'IoT Sync'),
        ('HEARTBEAT', 'Heartbeat'),
        ('MANUAL', 'Manual Check'),
        ('TIMEOUT', 'Connection Timeout'),
    ]
    
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    previous_status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    changed_at = models.DateTimeField()
    duration_seconds = models.IntegerField(null=True, blank=True)
    triggered_by = models.CharField(max_length=20, choices=TRIGGERED_BY_CHOICES)
    
    class Meta:
        db_table = 'station_status_history'
        verbose_name = 'Station Status History'
        verbose_name_plural = 'Station Status Histories'
        indexes = [
            models.Index(fields=['station', 'changed_at']),
            models.Index(fields=['status', 'changed_at']),
        ]
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.station.serial_number} - {self.status} at {self.changed_at}"
