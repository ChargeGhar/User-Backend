"""
Internal app configuration
"""
from __future__ import annotations

from django.apps import AppConfig


class InternalConfig(AppConfig):
    """Configuration for Internal IoT Integration app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.internal'
    verbose_name = 'Internal IoT Integration'
