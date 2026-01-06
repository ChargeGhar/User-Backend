from django.db import models
from api.common.models import BaseModel

class SystemLog(BaseModel):
    """
    SystemLog - PowerBank Table
    System-wide logging for debugging and monitoring
    """
    
    class LogLevelChoices(models.TextChoices):
        DEBUG = 'debug', 'Debug'
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        CRITICAL = 'critical', 'Critical'
    
    level = models.CharField(max_length=50, choices=LogLevelChoices.choices)
    module = models.CharField(max_length=255)
    message = models.TextField()
    context = models.JSONField(default=dict)
    trace_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "system_logs"
        verbose_name = "System Log"
        verbose_name_plural = "System Logs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_level_display()} - {self.module}: {self.message[:50]}"
