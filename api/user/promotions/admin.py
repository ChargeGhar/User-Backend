from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.promotions.models import Coupon, CouponUsage, StationPackageDiscount


@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ['code', 'name', 'points_value', 'is_public', 'status', 'valid_from', 'valid_until']
    list_filter = ['is_public', 'status', 'valid_from', 'valid_until']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CouponUsage)
class CouponUsageAdmin(ModelAdmin):
    list_display = ['user', 'coupon', 'points_awarded', 'used_at']
    list_filter = ['used_at', 'coupon']
    search_fields = ['user__username', 'coupon__code']
    readonly_fields = ['used_at', 'created_at']


@admin.register(StationPackageDiscount)
class StationPackageDiscountAdmin(ModelAdmin):
    list_display = ['station', 'package', 'discount_percent', 'status', 'current_usage_count', 'is_valid_now']
    list_filter = ['status', 'valid_from', 'valid_until']
    search_fields = ['station__station_name', 'package__name']
    readonly_fields = ['current_usage_count', 'created_at', 'updated_at']
    
    def is_valid_now(self, obj):
        return obj.is_valid()
    is_valid_now.boolean = True
    is_valid_now.short_description = 'Valid Now'
