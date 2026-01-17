"""
Advertisements App Configuration
=================================
"""
from django.apps import AppConfig


class AdvertisementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.user.advertisements'
    label = 'advertisements'
    verbose_name = 'Advertisements'
