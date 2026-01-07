from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.content.models import Banner


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ['title', 'is_active', 'valid_from', 'valid_until', 'display_order']
    list_filter = ['is_active', 'valid_from', 'valid_until']
    search_fields = ['title', 'description']
    ordering = ['display_order', '-created_at']
    readonly_fields = ['created_at', 'updated_at']
