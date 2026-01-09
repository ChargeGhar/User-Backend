from __future__ import annotations

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.notifications"
    label = "notifications"  # CRITICAL: Keep original label for DB compatibility
