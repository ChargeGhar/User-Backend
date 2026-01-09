from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.user.content.models import FAQ


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ['question', 'category', 'is_active', 'sort_order', 'created_by']
    list_filter = ['category', 'is_active', 'created_by']
    search_fields = ['question', 'answer']
    ordering = ['category', 'sort_order']
    readonly_fields = ['created_at', 'updated_at']
