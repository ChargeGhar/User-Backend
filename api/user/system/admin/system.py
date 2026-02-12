from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.user.system.models.system import Country, AppConfig, AppVersion, AppUpdate

@admin.register(Country)
class CountryAdmin(ModelAdmin):
    list_display = ['name', 'code', 'dial_code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(AppConfig)
class AppConfigAdmin(ModelAdmin):
    list_display = ['key', 'value', 'is_public', 'is_active', 'description', 'updated_at']
    list_filter = ['is_public', 'is_active', 'updated_at']
    search_fields = ['key', 'value', 'description']
    ordering = ['key']
    list_editable = ['is_public', 'is_active']
    list_per_page = 50
    save_on_top = True
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Config', {
            'fields': ('id', 'key', 'value', 'description')
        }),
        ('Visibility', {
            'fields': ('is_public', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.key == 'cloud_storage_provider':
            from django.core.cache import cache
            cache.clear()
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.key == 'cloud_storage_provider':
            form.base_fields['value'].help_text = "Options: 'cloudinary' or 's3'"
        return form


@admin.register(AppVersion)
class AppVersionAdmin(ModelAdmin):
    list_display = ['version', 'platform', 'is_mandatory', 'released_at']
    list_filter = ['platform', 'is_mandatory', 'released_at']
    search_fields = ['version', 'release_notes']
    ordering = ['-released_at']


@admin.register(AppUpdate)
class AppUpdateAdmin(ModelAdmin):
    list_display = ['title', 'version', 'is_major', 'released_at']
    list_filter = ['is_major', 'released_at']
    search_fields = ['title', 'version', 'description']
    ordering = ['-released_at']
