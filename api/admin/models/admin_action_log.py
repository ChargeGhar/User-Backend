from django.db import models
from api.common.models import BaseModel

class AdminActionLog(BaseModel):
    """
    AdminActionLog - PowerBank Table
    Logs all admin actions for audit trail
    """
    admin_user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='admin_actions')
    action_type = models.CharField(max_length=255)
    target_model = models.CharField(max_length=255)
    target_id = models.CharField(max_length=255)
    changes = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    ip_address = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "admin_action_logs"
        verbose_name = "Admin Action Log"
        verbose_name_plural = "Admin Action Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.action_type} on {self.target_model}"
