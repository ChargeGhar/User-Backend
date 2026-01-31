"""
IoT Sync Log Model
"""
from django.db import models
from api.common.models import BaseModel


class IotSyncLog(BaseModel):
    """Log all IoT sync operations"""
    
    SYNC_TYPE_CHOICES = [
        ('STATUS', 'Status Update'),
        ('FULL', 'Full Sync'),
        ('RETURNED', 'Return Event'),
    ]
    
    DIRECTION_CHOICES = [
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
    ]
    
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('TIMEOUT', 'Timeout'),
    ]
    
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='iot_sync_logs'
    )
    device_uuid = models.CharField(max_length=100)
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'iot_sync_logs'
        verbose_name = 'IoT Sync Log'
        verbose_name_plural = 'IoT Sync Logs'
        indexes = [
            models.Index(fields=['station', 'sync_type', 'created_at']),
            models.Index(fields=['device_uuid', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.sync_type} - {self.station.serial_number} - {self.status}"
