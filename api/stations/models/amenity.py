from django.db import models
from api.common.models import BaseModel
from .station import Station


class StationAmenity(BaseModel):
    """
    StationAmenity - Amenities available at stations (WiFi, Parking, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=255)  # Icon name or URL
    description = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "station_amenities"
        verbose_name = "Station Amenity"
        verbose_name_plural = "Station Amenities"

    def __str__(self):
        return str(self.name)


class StationAmenityMapping(BaseModel):
    """
    StationAmenityMapping - Maps amenities to stations
    """
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='amenity_mappings')
    amenity = models.ForeignKey(StationAmenity, on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "station_amenity_mappings"
        verbose_name = "Station Amenity Mapping"
        verbose_name_plural = "Station Amenity Mappings"
        unique_together = ['station', 'amenity']

    def __str__(self):
        return f"{self.station.station_name} - {self.amenity.name}"
