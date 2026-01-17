"""
AdContent Model
===============
Represents the media content for an advertisement.
"""
from django.db import models
from api.common.models import BaseModel


class AdContent(BaseModel):
    """
    AdContent - Media content for advertisement
    """
    
    CONTENT_TYPE_CHOICES = [
        ('IMAGE', 'Image'),   # jpg, png
        ('VIDEO', 'Video'),   # mp4
    ]
    
    ad_request = models.ForeignKey(
        'advertisements.AdRequest',
        on_delete=models.CASCADE,
        related_name='ad_contents',
        help_text="Parent ad request"
    )
    content_type = models.CharField(
        max_length=10,
        choices=CONTENT_TYPE_CHOICES,
        help_text="Type of content (IMAGE or VIDEO)"
    )
    media_upload = models.ForeignKey(
        'media.MediaUpload',
        on_delete=models.PROTECT,
        related_name='ad_contents',
        help_text="Uploaded media file"
    )
    duration_seconds = models.IntegerField(
        default=5,
        help_text="Display duration for images (in seconds)"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Order in rotation (lower = higher priority)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this content is active"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    
    class Meta:
        db_table = 'ad_contents'
        verbose_name = 'Ad Content'
        verbose_name_plural = 'Ad Contents'
        indexes = [
            models.Index(fields=['ad_request', 'is_active']),
            models.Index(fields=['content_type', 'is_active']),
        ]
        ordering = ['display_order', '-created_at']
    
    def __str__(self):
        return f"{self.content_type} - {self.ad_request.title or 'Untitled'}"
