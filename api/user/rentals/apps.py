from __future__ import annotations

from django.apps import AppConfig


class RentalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.rentals"
    label = "rentals"  # CRITICAL: Keep original label for DB compatibility
