from django.db import models
from api.common.models import BaseModel


class NotificationRule(BaseModel):
    """
    NotificationRule - Rules for which channels to send notifications
    """
    notification_type = models.CharField(max_length=255, unique=True)
    send_in_app = models.BooleanField(default=True)
    send_push = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    send_email = models.BooleanField(default=False)
    is_critical = models.BooleanField(default=False)
    
    class Meta:
        db_table = "notification_rules"
        verbose_name = "Notification Rule"
        verbose_name_plural = "Notification Rules"
    
    def __str__(self):
        return f"Rule for {self.notification_type}"
