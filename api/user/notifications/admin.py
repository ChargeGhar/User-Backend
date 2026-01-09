from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.notifications.models import (
    Notification, SMS_FCMLog, NotificationTemplate, NotificationRule
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active', 'created_at']
    list_filter = ['notification_type', 'is_active']
    search_fields = ['name', 'slug', 'title_template']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(NotificationRule)
class NotificationRuleAdmin(ModelAdmin):
    list_display = ['notification_type', 'send_in_app', 'send_push', 'send_sms', 'send_email', 'is_critical']
    list_filter = ['send_in_app', 'send_push', 'send_sms', 'send_email', 'is_critical']
    search_fields = ['notification_type']


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'channel', 'is_read', 'created_at']
    list_filter = ['notification_type', 'channel', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']


@admin.register(SMS_FCMLog)
class SMS_FCMLogAdmin(ModelAdmin):
    list_display = ['user', 'notification_type', 'recipient', 'status', 'sent_at', 'created_at']
    list_filter = ['notification_type', 'status', 'sent_at']
    search_fields = ['user__username', 'recipient']
    readonly_fields = ['created_at', 'sent_at']
