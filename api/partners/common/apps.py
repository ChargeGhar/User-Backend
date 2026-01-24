from django.apps import AppConfig


class PartnersCommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.partners.common'
    label = 'partners'
    verbose_name = 'Partners'
