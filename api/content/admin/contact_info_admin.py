from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from api.content.models import ContactInfo


@admin.register(ContactInfo)
class ContactInfoAdmin(ModelAdmin):
    list_display = ['info_type', 'label', 'value', 'is_active', 'updated_by']
    list_filter = ['info_type', 'is_active']
    search_fields = ['label', 'value']
    readonly_fields = ['updated_at']
