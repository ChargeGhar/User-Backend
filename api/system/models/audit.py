from django.db import models
from api.common.models.base import BaseModel

class AuditLog(BaseModel):
    """
    AuditLog - Generic audit trail for actions across the system.
    """
    ACTION_CHOICES = [
        ('CREATE', 'Create'), 
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]

    ENTITY_TYPE_CHOICES = [
        ('USER', 'User'),
        ('STATION', 'Station'),
        ('RENTAL', 'Rental'),
        ('TRANSACTION', 'Transaction'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    admin = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True, related_name='admin_audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.CharField(max_length=255)
    old_values = models.JSONField(default=dict, null=True, blank=True)
    new_values = models.JSONField(default=dict, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    session_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "user_audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.entity_type} by {self.user or self.admin}"
