"""
AchievementRealtimeService - Real-time Achievement Calculation
================================================================

Handles real-time calculation of achievement progress for users.
Optimized for performance with bulk queries and aggregations.

Created: 2025-01-16
Part of: Social App Real-Time Achievement Update
"""

from __future__ import annotations

from typing import Dict, List
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.common.services.base import BaseService
from api.user.social.models import Achievement, UserAchievement

User = get_user_model()

class AchievementRealtimeService(BaseService):
    """Service for real-time achievement calculation"""

    def calculate_user_progress(self, user) -> Dict[str, int]:
        """
        Calculate current progress for all achievement criteria types.
        Optimized to run within 10 seconds.

        Returns:
            Dict with keys: rental_count, timely_return_count, referral_count
        """
        try:
            from api.user.rentals.models import Rental
            from api.user.points.models import Referral

            # Single query for all rental stats (optimized)
            rental_stats = Rental.objects.filter(user=user).aggregate(
                total=Count("id"),
                timely=Count("id", filter=Q(is_returned_on_time=True)),
            )

            # Single query for referral count
            referral_count = Referral.objects.filter(
                inviter=user, status="COMPLETED"
            ).count()

            progress = {
                "rental_count": rental_stats["total"] or 0,
                "timely_return_count": rental_stats["timely"] or 0,
                "referral_count": referral_count,
            }

            self.log_info(f"Calculated progress for user {user.username}: {progress}")
            return progress

        except Exception as e:
            self.handle_service_error(e, "Failed to calculate user progress")

    def update_all_progress_realtime(self, user) -> List[UserAchievement]:
        """
        Update ALL achievement progress for a user in real-time.
        Unlocks achievements but doesn't claim them.

        Returns:
            List of UserAchievement objects (both locked and unlocked)
        """
        try:
            # Calculate current progress
            progress = self.calculate_user_progress(user)

            # Get all active achievements
            achievements = Achievement.objects.filter(is_active=True).order_by(
                "criteria_value"
            )

            # Get or create user achievements
            user_achievements = []
            newly_unlocked = []

            for achievement in achievements:
                # Get current progress value for this criteria type
                current_value = progress.get(achievement.criteria_type.lower(), 0)

                # Get or create UserAchievement
                user_achievement, created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={
                        "current_progress": current_value,
                        "is_unlocked": False,
                        "is_claimed": False,
                    },
                )

                # Update progress
                user_achievement.current_progress
                user_achievement.current_progress = current_value

                # Check if should be unlocked (criteria met + not already unlocked)
                should_unlock = (
                    current_value >= achievement.criteria_value
                    and not user_achievement.is_unlocked
                )

                if should_unlock:
                    user_achievement.is_unlocked = True
                    user_achievement.unlocked_at = timezone.now()
                    newly_unlocked.append(user_achievement)
                    self.log_info(
                        f"Achievement unlocked: {achievement.name} for user {user.username}"
                    )

                user_achievement.save(
                    update_fields=["current_progress", "is_unlocked", "unlocked_at"]
                )
                user_achievements.append(user_achievement)

            # Send notifications for newly unlocked achievements (async)
            if newly_unlocked:
                from api.user.notifications.services import notify

                # Send individual notifications for better UX
                for user_achievement in newly_unlocked:
                    notify(
                        user=user,
                        template_slug="achievement_unlocked",
                        async_send=True,
                        achievement_name=user_achievement.achievement.name,
                        reward_points=user_achievement.achievement.reward_value,  # Fixed variable name
                    )

                self.log_info(
                    f"Sent {len(newly_unlocked)} unlock notifications to {user.username}"
                )

            return user_achievements

        except Exception as e:
            self.handle_service_error(e, "Failed to update user progress")

    def get_unlocked_unclaimed_count(self, user) -> int:
        """Get count of achievements that are unlocked but not claimed"""
        try:
            return UserAchievement.objects.filter(
                user=user, is_unlocked=True, is_claimed=False
            ).count()
        except Exception as e:
            self.handle_service_error(e, "Failed to get unclaimed count")

    def get_unlocked_unclaimed_achievements(self, user) -> List[UserAchievement]:
        """Get all achievements that are unlocked but not claimed"""
        try:
            return (
                UserAchievement.objects.filter(
                    user=user, is_unlocked=True, is_claimed=False
                )
                .select_related("achievement")
                .order_by("-unlocked_at")
            )
        except Exception as e:
            self.handle_service_error(e, "Failed to get unlocked unclaimed achievements")
