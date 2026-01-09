from __future__ import annotations

from typing import List

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from api.common.tasks.base import BaseTask, NotificationTask
from api.user.social.models import UserAchievement, UserLeaderboard

User = get_user_model()


@shared_task(base=BaseTask, bind=True)
def update_user_leaderboard_stats(self, user_id: str = None):
    """
    Update leaderboard statistics for a user or all users.

    ADMIN UTILITY: Use for batch recalculation after data migrations or fixes.
    Can be called manually via Django shell or admin interface.

    Args:
        user_id: Optional UUID string. If provided, updates specific user.
                 If None, updates all active users.

    Example:
        # Update specific user
        update_user_leaderboard_stats.delay(user_id="123e4567-e89b-12d3-a456-426614174000")

        # Update all users
        update_user_leaderboard_stats.delay()
    """
    try:
        from api.user.social.services import LeaderboardService

        service = LeaderboardService()

        if user_id:
            # Update specific user
            user = User.objects.get(id=user_id)
            service.update_user_leaderboard(user)
            updated_count = 1
        else:
            # Update all users
            users = User.objects.filter(is_active=True)
            updated_count = 0

            for user in users:
                try:
                    service.update_user_leaderboard(user)
                    updated_count += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to update leaderboard for user {user.id}: {str(e)}"
                    )

        self.logger.info(f"Updated leaderboard stats for {updated_count} users")
        return {"updated_users": updated_count}

    except User.DoesNotExist:
        self.logger.error(f"User not found: {user_id}")
        raise
    except Exception as e:
        self.logger.error(f"Failed to update leaderboard stats: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def recalculate_leaderboard_ranks(self):
    """
    Recalculate all leaderboard ranks based on user scores.

    ACTIVELY USED: Called automatically after achievement claims to update rankings.
    This task runs asynchronously to avoid blocking the claim operation.

    Formula: (points * 0.4) + (rentals * 0.3) + (referrals * 20) + (timely_returns * 0.3)

    Example:
        # Called automatically by AchievementClaimService
        recalculate_leaderboard_ranks.delay()
    """
    try:
        from api.user.social.services import LeaderboardService

        service = LeaderboardService()
        updated_count = service.recalculate_ranks()

        self.logger.info(f"Recalculated ranks for {updated_count} users")
        return {"updated_ranks": updated_count}

    except Exception as e:
        self.logger.error(f"Failed to recalculate leaderboard ranks: {str(e)}")
        raise


@shared_task(base=NotificationTask, bind=True)
def send_achievement_unlock_notifications(
    self, user_id: str, user_achievement_ids: List[str]
):
    """
    Send notifications when achievements are unlocked.

    LEGACY COMPATIBILITY: This task is called by the legacy AchievementService.update_user_progress()
    method for backward compatibility with background batch processing.

    NEW FLOW: The new real-time flow (AchievementRealtimeService) sends notifications directly
    using the notify() function, which is more efficient.

    Args:
        user_id: User UUID string
        user_achievement_ids: List of UserAchievement UUID strings

    Example:
        send_achievement_unlock_notifications.delay(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            user_achievement_ids=["uuid1", "uuid2"]
        )
    """
    try:
        user = User.objects.get(id=user_id)
        user_achievements = UserAchievement.objects.filter(
            id__in=user_achievement_ids
        ).select_related("achievement")

        from api.user.notifications.services import notify

        for user_achievement in user_achievements:
            # Send achievement unlock notification
            # Uses reward_points (not points) to match template variables
            notify(
                user,
                "achievement_unlocked",
                async_send=True,
                achievement_name=user_achievement.achievement.name,
                reward_points=user_achievement.achievement.reward_value,
            )

        self.logger.info(
            f"Sent achievement notifications for {len(user_achievements)} achievements to user {user.username}"
        )
        return {"user_id": user_id, "notifications_sent": len(user_achievements)}

    except User.DoesNotExist:
        self.logger.error(f"User not found: {user_id}")
        raise
    except Exception as e:
        self.logger.error(f"Failed to send achievement notifications: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def cleanup_inactive_user_achievements(self):
    """
    Clean up leaderboard entries for inactive users (6+ months).

    SCHEDULED TASK: Should be run monthly via Celery Beat to maintain database hygiene.
    Removes leaderboard entries for users who haven't logged in for 6 months AND are inactive.

    NOTE: Achievement records are preserved for audit purposes - only leaderboard entries are removed.

    Recommended schedule (in celery.py):
        beat_schedule = {
            'cleanup-inactive-achievements': {
                'task': 'api.social.tasks.cleanup_inactive_user_achievements',
                'schedule': crontab(day_of_month='1', hour='3', minute='0'),
            },
        }

    Example:
        # Manual trigger
        cleanup_inactive_user_achievements.delay()
    """
    try:
        # Get inactive users (not logged in for 6 months)
        six_months_ago = timezone.now() - timezone.timedelta(days=180)

        inactive_users = User.objects.filter(
            Q(last_login__lt=six_months_ago) | Q(last_login__isnull=True),
            is_active=False,
        )

        # Remove their leaderboard entries
        deleted_leaderboard = UserLeaderboard.objects.filter(
            user__in=inactive_users
        ).delete()[0]

        # Keep achievement records for audit purposes
        # (Don't delete UserAchievement records)

        self.logger.info(
            f"Cleaned up {deleted_leaderboard} leaderboard entries for inactive users"
        )
        return {
            "deleted_leaderboard_entries": deleted_leaderboard,
            "inactive_users_count": inactive_users.count(),
        }

    except Exception as e:
        self.logger.error(f"Failed to cleanup inactive user achievements: {str(e)}")
        raise
