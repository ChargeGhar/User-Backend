from __future__ import annotations

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.payments"
    label = "payments"  # CRITICAL: Keep original label for DB compatibility
