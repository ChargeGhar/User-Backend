"""
AchievementService - Individual Service File
============================================================

Service for achievement operations (existing functionality preserved)

Created: 2025-01-16
Part of: Social App Real-Time Achievement Update
"""

from __future__ import annotations

from typing import List
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.common.services.base import CRUDService
from api.user.social.models import Achievement, UserAchievement

User = get_user_model()

class AchievementService(CRUDService):
    """Service for achievement operations (legacy/existing)"""

    model = Achievement

    def get_user_achievements(self, user) -> List[UserAchievement]:
        """Get all achievements for a user with progress"""
        try:
            # Get all active achievements
            achievements = Achievement.objects.filter(is_active=True)

            # Get user's achievement progress
            user_achievements = {}
            for ua in UserAchievement.objects.filter(user=user):
                user_achievements[ua.achievement_id] = ua

            # Create missing user achievements
            missing_achievements = []
            for achievement in achievements:
                if achievement.id not in user_achievements:
                    missing_achievements.append(
                        UserAchievement(
                            user=user, achievement=achievement, current_progress=0
                        )
                    )

            if missing_achievements:
                UserAchievement.objects.bulk_create(missing_achievements)

            # Return all user achievements
            return (
                UserAchievement.objects.filter(user=user, achievement__is_active=True)
                .select_related("achievement")
                .order_by("-is_unlocked", "achievement__name")
            )

        except Exception as e:
            self.handle_service_error(e, "Failed to get user achievements")

    def get_unlocked_achievements(self, user) -> List[UserAchievement]:
        """Get user's unlocked achievements"""
        try:
            return (
                UserAchievement.objects.filter(user=user, is_unlocked=True)
                .select_related("achievement")
                .order_by("-unlocked_at")
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get unlocked achievements")

    @transaction.atomic
    def update_user_progress(
        self, user, criteria_type: str, new_value: int
    ) -> List[UserAchievement]:
        """
        Update user's progress for achievements of a specific criteria type.

        NOTE: This is legacy method used by background tasks.
        For real-time updates, use AchievementRealtimeService instead.
        """
        try:
            # Get relevant achievements
            achievements = Achievement.objects.filter(
                criteria_type=criteria_type, is_active=True
            )

            unlocked_achievements = []

            for achievement in achievements:
                user_achievement, created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={"current_progress": new_value},
                )

                if not created:
                    user_achievement.current_progress = new_value

                # Check if achievement should be unlocked
                if (
                    not user_achievement.is_unlocked
                    and user_achievement.current_progress >= achievement.criteria_value
                ):
                    user_achievement.is_unlocked = True
                    user_achievement.unlocked_at = timezone.now()
                    user_achievement.points_awarded = achievement.reward_value

                    # Award points to user (OLD FLOW - awards immediately)
                    from api.user.points.services import award_points

                    award_points(
                        user=user,
                        points=achievement.reward_value,
                        source="ACHIEVEMENT",
                        description=f"Achievement unlocked: {achievement.name}",
                        async_send=True,
                        achievement_id=str(achievement.id),
                    )

                    unlocked_achievements.append(user_achievement)

                user_achievement.save(
                    update_fields=[
                        "current_progress",
                        "is_unlocked",
                        "unlocked_at",
                        "points_awarded",
                    ]
                )

            # Send notifications for unlocked achievements
            if unlocked_achievements:
                from api.user.notifications.tasks import send_achievement_unlock_notifications

                send_achievement_unlock_notifications.delay(
                    str(user.id), [str(ua.id) for ua in unlocked_achievements]
                )

            return unlocked_achievements

        except Exception as e:
            self.handle_service_error(e, "Failed to update user progress")

    @transaction.atomic
    def create_achievement(
        self,
        name: str,
        description: str,
        criteria_type: str,
        criteria_value: int,
        reward_type: str,
        reward_value: int,
        admin_user,
    ) -> Achievement:
        """Create new achievement (Admin)"""
        try:
            achievement = Achievement.objects.create(
                name=name,
                description=description,
                criteria_type=criteria_type,
                criteria_value=criteria_value,
                reward_type=reward_type,
                reward_value=reward_value,
            )

            # Log admin action
            from api.admin.models import AdminActionLog

            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type="CREATE_ACHIEVEMENT",
                target_model="Achievement",
                target_id=str(achievement.id),
                changes={
                    "name": name,
                    "criteria_type": criteria_type,
                    "criteria_value": criteria_value,
                    "reward_value": reward_value,
                },
                description=f"Created achievement: {name}",
                ip_address="127.0.0.1",
                user_agent="Admin Panel",
            )

            self.log_info(f"Achievement created: {name}")
            return achievement

        except Exception as e:
            self.handle_service_error(e, "Failed to create achievement")
