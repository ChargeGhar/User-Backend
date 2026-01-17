from django.db import models
from api.common.models import BaseModel


class NotificationTemplate(BaseModel):
    """
    NotificationTemplate - Templates for different notification types
    """
    
    class NotificationTypeChoices(models.TextChoices):
        RENTAL = 'rental', 'Rental'
        PAYMENT = 'payment', 'Payment'
        PROMOTION = 'promotion', 'Promotion'
        SYSTEM = 'system', 'System'
        ACHIEVEMENT = 'achievement', 'Achievement'
        SECURITY = 'security', 'Security'
        POINTS = 'points', 'Points'
        UPDATE = 'update', 'Update'
        ADMIN = 'admin', 'Admin'
        OTP_SMS = 'otp_sms', 'OTP SMS'
        OTP_EMAIL = 'otp_email', 'OTP Email'
        ADVERTISEMENT = 'advertisement', 'Advertisement'
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    title_template = models.CharField(max_length=255)
    message_template = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NotificationTypeChoices.choices)
    description = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "notification_templates"
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
    
    def __str__(self):
        return self.name
