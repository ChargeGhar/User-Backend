from django.db import models
from api.common.models import BaseModel
from .user import User


class UserDevice(BaseModel):
    """
    UserDevice - User's registered devices for push notifications
    """
    DEVICE_TYPE_CHOICES = [
        ('ANDROID', 'Android'),
        ('IOS', 'iOS'),
        ('WEB', 'Web'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255, unique=True)
    fcm_token = models.TextField()
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES)
    device_name = models.CharField(max_length=255, null=True, blank=True)
    app_version = models.CharField(max_length=50, null=True, blank=True)
    os_version = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_devices"
        verbose_name = "User Device"
        verbose_name_plural = "User Devices"

    def __str__(self):
        return f"{self.user.username} - {self.device_type}"
