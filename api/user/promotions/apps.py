from __future__ import annotations

from django.apps import AppConfig


class PromotionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.user.promotions"
    label = "promotions"  # CRITICAL: Keep original label for DB compatibility
