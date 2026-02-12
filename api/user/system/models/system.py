from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from api.common.models.base import BaseModel


class Country(BaseModel):
    """
    Country - Countries with dialing codes
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # ISO country code
    dial_code = models.CharField(max_length=10)
    flag_url = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "countries"
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        ordering = ['name']

    def __str__(self):
        return self.name


class AppConfig(BaseModel):
    """
    AppConfig - Application configuration settings
    """
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(
        default=False,
        help_text="If true, this config is exposed by public app config endpoint.",
    )

    class Meta:
        db_table = "app_configs"
        verbose_name = "App Config"
        verbose_name_plural = "App Configs"

    def __str__(self):
        return self.key


class AppVersion(BaseModel):
    """
    AppVersion - App version management for updates
    """
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]
    
    version = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=255, choices=PLATFORM_CHOICES)
    is_mandatory = models.BooleanField(default=False)
    download_url = models.URLField()
    release_notes = models.TextField()
    released_at = models.DateTimeField()
    
    class Meta:
        db_table = "app_versions"
        verbose_name = "App Version"
        verbose_name_plural = "App Versions"
        ordering = ['-released_at']
    
    def __str__(self):
        return f"{self.platform} v{self.version}"


class AppUpdate(BaseModel):
    """
    AppUpdate - App update announcements and features
    """
    version = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField()
    features = models.JSONField(default=list)
    is_major = models.BooleanField(default=False)
    released_at = models.DateTimeField()
    
    class Meta:
        db_table = "app_updates"
        verbose_name = "App Update"
        verbose_name_plural = "App Updates"
        ordering = ['-released_at']
    
    def __str__(self):
        return f"{self.title} - v{self.version}"


@receiver(post_save, sender=AppConfig)
def clear_appconfig_cache_on_save(sender, instance, **kwargs):
    cache_key = f"app_config_{instance.key}"
    cache.delete(cache_key)


@receiver(post_delete, sender=AppConfig)
def clear_appconfig_cache_on_delete(sender, instance, **kwargs):
    cache_key = f"app_config_{instance.key}"
    cache.delete(cache_key)
