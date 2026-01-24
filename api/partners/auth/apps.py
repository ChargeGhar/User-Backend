# api/partners/auth/apps.py
"""Partner Auth App Configuration."""
from __future__ import annotations

from django.apps import AppConfig


class PartnersAuthConfig(AppConfig):
    """Configuration for the partners auth app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.partners.auth"
    label = "partners_auth"
