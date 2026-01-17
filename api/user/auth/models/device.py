from django.db import models
from api.common.models import BaseModel
from .user import User


class UserDevice(BaseModel):
    """
    UserDevice - User's registered devices for push notifications and biometric auth
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
    
    # Biometric authentication fields
    biometric_enabled = models.BooleanField(default=False)
    biometric_token = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Secure token for biometric authentication"
    )
    biometric_registered_at = models.DateTimeField(null=True, blank=True)
    biometric_last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_devices"
        verbose_name = "User Device"
        verbose_name_plural = "User Devices"

    def __str__(self):
        return f"{self.user.username} - {self.device_type}"
