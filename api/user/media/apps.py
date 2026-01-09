from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.user.media'
    label = 'media'  # CRITICAL: Keep original label for DB compatibility
    verbose_name = 'Media Management'
    
    def ready(self):
        """Import signal handlers when app is ready"""
        pass
