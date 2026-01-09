from __future__ import annotations

from django.apps import AppConfig


class PointsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.points"
    label = "points"  # CRITICAL: Keep original label for DB compatibility
