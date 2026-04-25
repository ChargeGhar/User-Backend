"""
AdDistribution Model
====================
Represents the distribution of ad content to specific stations.
"""
from django.db import models
from api.common.models import BaseModel


class AdDistribution(BaseModel):
    """
    AdDistribution - Links ad content to stations where it should be displayed
    """
    
    ad_content = models.ForeignKey(
        'advertisements.AdContent',
        on_delete=models.CASCADE,
        related_name='ad_distributions',
        help_text="Ad content to distribute"
    )
    station = models.ForeignKey(
        'stations.Station',
        on_delete=models.CASCADE,
        related_name='ad_distributions',
        help_text="Station where ad will be displayed"
    )
    
    class Meta:
        db_table = 'ad_distributions'
        verbose_name = 'Ad Distribution'
        verbose_name_plural = 'Ad Distributions'
        indexes = [
            models.Index(fields=['ad_content', 'station']),
            models.Index(fields=['station', 'created_at']),
        ]
        unique_together = [['ad_content', 'station']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ad_content.ad_request.title or 'Untitled'} -> {self.station.station_name}"
