from __future__ import annotations

from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.content"
    label = "content"  # CRITICAL: Keep original label for DB compatibility
