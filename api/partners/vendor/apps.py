from django.apps import AppConfig


class VendorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.partners.vendor'
    label = 'partners_vendor'
    verbose_name = 'Partners - Vendor'
