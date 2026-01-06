from __future__ import annotations

from typing import Any

from django.contrib import admin

from api.users.models import User, UserProfile, UserKYC, UserDevice


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    filter_horizontal = ("groups", "user_permissions")

    list_display = (
        "username",
        "email",
        "phone_number",
        "status",
        "email_verified",
        "phone_verified",
        "is_active",
        "is_staff",
    )
    
    list_filter = (
        "status",
        "email_verified", 
        "phone_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined"
    )
    
    search_fields = ("username", "email", "phone_number", "referral_code")
    readonly_fields = ("date_joined", "last_login")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'is_profile_complete', 'created_at']
    list_filter = ['is_profile_complete', 'created_at']
    search_fields = ['user__username', 'full_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserKYC)
class UserKYCAdmin(admin.ModelAdmin):
    list_display = ['user', 'document_type', 'status', 'verified_at', 'verified_by']
    list_filter = ['status', 'document_type', 'verified_at']
    search_fields = ['user__username', 'document_number']
    readonly_fields = ['created_at', 'verified_at']


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'device_name', 'is_active', 'last_used']
    list_filter = ['device_type', 'is_active', 'last_used']
    search_fields = ['user__username', 'device_name', 'device_id']
    readonly_fields = ['created_at', 'last_used']
