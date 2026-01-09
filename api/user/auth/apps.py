from __future__ import annotations

from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.auth"
    label = "users"  # CRITICAL: Keep original label for DB compatibility
