from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.promotions.models import Coupon, CouponUsage


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ['code', 'name', 'points_value', 'status', 'valid_from', 'valid_until']
    list_filter = ['status', 'valid_from', 'valid_until']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CouponUsage)
class CouponUsageAdmin(ModelAdmin):
    list_display = ['user', 'coupon', 'points_awarded', 'used_at']
    list_filter = ['used_at', 'coupon']
    search_fields = ['user__username', 'coupon__code']
    readonly_fields = ['used_at', 'created_at']
