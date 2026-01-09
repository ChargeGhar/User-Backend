from django.db import models
from api.common.models import BaseModel

class Banner(BaseModel):
    """
    Banner - Promotional banners for the app
    """
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
    image_url = models.URLField()
    redirect_url = models.URLField(null=True, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    class Meta:
        db_table = "banners"
        verbose_name = "Banner"
        verbose_name_plural = "Banners"
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title
