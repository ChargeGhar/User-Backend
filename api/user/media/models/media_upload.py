from __future__ import annotations
from django.db import models
from api.common.models import BaseModel

class MediaUpload(BaseModel):
    """
    MediaUpload - Uploaded media files
    """
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('DOCUMENT', 'Document'),
    ]

    file_url = models.URLField()
    file_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES)
    original_name = models.CharField(max_length=255)
    file_size = models.IntegerField()
    uploaded_by = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True)
    
    # Cloud storage metadata
    cloud_provider = models.CharField(max_length=50, default='cloudinary')
    public_id = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "media_uploads"  # ⚠️ CRITICAL: Keep same table name for zero-downtime migration
        verbose_name = "Media Upload"
        verbose_name_plural = "Media Uploads"

    def __str__(self):
        return self.original_name
