from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.user.system.models.audit import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ['user', 'admin', 'action', 'entity_type', 'entity_id', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['user__username', 'admin__username', 'entity_id']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
