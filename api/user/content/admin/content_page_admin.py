from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.user.content.models import ContentPage


@admin.register(ContentPage)
class ContentPageAdmin(ModelAdmin):
    list_display = ['page_type', 'title', 'is_active', 'updated_at']
    list_filter = ['page_type', 'is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
