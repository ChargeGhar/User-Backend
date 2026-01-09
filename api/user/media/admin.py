from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.media.models import MediaUpload


@admin.register(MediaUpload)
class MediaUploadAdmin(ModelAdmin):
    list_display = ['original_name', 'file_type', 'cloud_provider', 'file_size', 'uploaded_by', 'created_at']
    list_filter = ['file_type', 'cloud_provider', 'created_at']
    search_fields = ['original_name', 'public_id']
    readonly_fields = ['file_size', 'file_url', 'public_id', 'cloud_provider', 'metadata', 'created_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('original_name', 'file_type', 'file_size', 'uploaded_by')
        }),
        ('Cloud Storage', {
            'fields': ('cloud_provider', 'file_url', 'public_id', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
