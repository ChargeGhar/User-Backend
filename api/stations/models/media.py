from django.db import models
from api.common.models import BaseModel
from .station import Station


class StationMedia(BaseModel):
    """
    StationMedia - Media files associated with stations
    """
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('360_VIEW', '360 View'),
        ('FLOOR_PLAN', 'Floor Plan'),
    ]

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='media')
    media_upload = models.ForeignKey('media.MediaUpload', on_delete=models.CASCADE)
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES)
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "station_media"
        verbose_name = "Station Media"
        verbose_name_plural = "Station Media"

    def __str__(self):
        return f"{self.station.station_name} - {self.media_type}"
