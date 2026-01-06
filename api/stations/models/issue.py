from django.db import models
from api.common.models import BaseModel
from .station import Station


class StationIssue(BaseModel):
    """
    StationIssue - Issues reported for stations
    """
    ISSUE_TYPE_CHOICES = [
        ('OFFLINE', 'Offline'),
        ('DAMAGED', 'Damaged'),
        ('DIRTY', 'Dirty'),
        ('LOCATION_WRONG', 'Location Wrong'),
        ('SLOT_ERROR', 'Slot Error'),
        ('AMENITY_ISSUE', 'Amenity Issue'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('REPORTED', 'Reported'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='issues')
    reported_by = models.ForeignKey('users.User', on_delete=models.CASCADE)
    assigned_to = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_station_issues')
    issue_type = models.CharField(max_length=50, choices=ISSUE_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    images = models.JSONField(default=list)  # List of image URLs
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='REPORTED')
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "station_issues"
        verbose_name = "Station Issue"
        verbose_name_plural = "Station Issues"

    def __str__(self):
        return f"{self.station.station_name} - {self.issue_type}"
