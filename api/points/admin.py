from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.points.models import PointsTransaction, Referral, UserPoints

@admin.register(PointsTransaction)
class PointsTransactionAdmin(ModelAdmin):
    list_display = ['user', 'transaction_type', 'source', 'points', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'source', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = ['inviter', 'invitee', 'referral_code', 'status', 'created_at']
    list_filter = ['status', 'first_rental_completed', 'created_at']
    search_fields = ['inviter__username', 'invitee__username', 'referral_code']
    readonly_fields = ['created_at', 'completed_at']


@admin.register(UserPoints)
class UserPointsAdmin(ModelAdmin):
    list_display = ['user', 'current_points', 'total_points', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at', 'last_updated']
