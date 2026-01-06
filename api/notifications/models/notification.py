from django.db import models
from api.common.models import BaseModel
from .template import NotificationTemplate


class Notification(BaseModel):
    """
    Notification - Individual notifications sent to users
    """
    
    class NotificationTypeChoices(models.TextChoices):
        RENTAL = 'rental', 'Rental'
        PAYMENT = 'payment', 'Payment'
        PROMOTION = 'promotion', 'Promotion'
        SYSTEM = 'system', 'System'
        ACHIEVEMENT = 'achievement', 'Achievement'
        POINTS = 'points', 'Points'
        UPDATE = 'update', 'Update'
        ADMIN = 'admin', 'Admin'
        OTP_SMS = 'otp_sms', 'OTP SMS'
        OTP_EMAIL = 'otp_email', 'OTP Email'
    
    class ChannelChoices(models.TextChoices):
        IN_APP = 'in_app', 'In App'
        PUSH = 'push', 'Push'
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='notifications')
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NotificationTypeChoices.choices)
    data = models.JSONField(default=dict)
    channel = models.CharField(max_length=50, choices=ChannelChoices.choices)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
            models.Index(fields=['user', '-created_at'], name='notif_user_created_idx'),
            models.Index(fields=['is_read', '-created_at'], name='notif_read_created_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
