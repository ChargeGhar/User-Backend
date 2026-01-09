from __future__ import annotations

from django.apps import AppConfig


class StationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.stations"
    label = "stations"  # CRITICAL: Keep original label for DB compatibility
