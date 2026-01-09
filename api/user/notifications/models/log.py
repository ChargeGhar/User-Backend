from django.db import models
from api.common.models import BaseModel


class SMS_FCMLog(BaseModel):
    """
    SMS_FCMLog - Log of SMS and FCM notifications sent
    """
    
    class TypeChoices(models.TextChoices):
        FCM = 'fcm', 'FCM'
        SMS = 'sms', 'SMS'
    
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
    
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True, related_name='sms_fcm_logs')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TypeChoices.choices)
    recipient = models.CharField(max_length=255)  # phone number or FCM token
    status = models.CharField(max_length=50, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    response = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "sms_fcm_logs"
        verbose_name = "SMS/FCM Log"
        verbose_name_plural = "SMS/FCM Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient} - {self.status}"
