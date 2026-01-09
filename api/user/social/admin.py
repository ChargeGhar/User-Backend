from __future__ import annotations

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from api.user.social.models import (
    Achievement, UserAchievement, UserLeaderboard
)

@admin.register(Achievement)
class AchievementAdmin(ModelAdmin):
    list_display = ['name', 'criteria_type', 'criteria_value', 'reward_value', 'is_active']
    list_filter = ['criteria_type', 'reward_type', 'is_active']
    search_fields = ['name', 'description']


@admin.register(UserAchievement)
class UserAchievementAdmin(ModelAdmin):
    list_display = ['user', 'achievement', 'current_progress', 'is_unlocked', 'unlocked_at']
    list_filter = ['is_unlocked', 'achievement', 'unlocked_at']
    search_fields = ['user__username', 'achievement__name']
    readonly_fields = ['created_at', 'unlocked_at']


@admin.register(UserLeaderboard)
class UserLeaderboardAdmin(ModelAdmin):
    list_display = ['rank', 'user', 'total_rentals', 'total_points_earned', 'referrals_count', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'last_updated']
    ordering = ['rank']
