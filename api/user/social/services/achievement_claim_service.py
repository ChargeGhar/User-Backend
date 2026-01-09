"""
AchievementClaimService - Achievement Claiming Operations
==========================================================

Handles claiming of unlocked achievements.
Awards points and updates leaderboard on successful claim.

Created: 2025-01-16
Part of: Social App Real-Time Achievement Update
"""

from __future__ import annotations

from typing import List, Dict, Any
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from api.common.services.base import BaseService, ServiceException
from api.user.social.models import UserAchievement


class AchievementClaimService(BaseService):
    """Service for claiming achievements"""

    @transaction.atomic
    def claim_achievement(
        self, user, achievement_id: str, suppress_notification: bool = False
    ) -> UserAchievement:
        """
        Claim an unlocked achievement.
        Awards points and updates leaderboard.

        Args:
            user: User object
            achievement_id: UUID of the UserAchievement
            suppress_notification: If True, don't send notification (for bulk claims)

        Returns:
            Updated UserAchievement object

        Raises:
            ServiceException: If achievement not found, already claimed, or not unlocked
        """
        try:
            # Get UserAchievement
            try:
                user_achievement = UserAchievement.objects.select_related(
                    "achievement"
                ).get(id=achievement_id, user=user)
            except UserAchievement.DoesNotExist:
                exc = ServiceException(
                    detail="Achievement not found",
                    code="not_found",
                )
                exc.status_code = status.HTTP_404_NOT_FOUND
                raise exc

            # Validate: Must be unlocked
            if not user_achievement.is_unlocked:
                exc = ServiceException(
                    detail="Achievement not unlocked yet. Complete the criteria first.",
                    code="not_unlocked",
                )
                exc.status_code = status.HTTP_400_BAD_REQUEST
                raise exc

            # Validate: Must not be already claimed
            if user_achievement.is_claimed:
                exc = ServiceException(
                    detail="Achievement already claimed",
                    code="already_claimed",
                )
                exc.status_code = status.HTTP_409_CONFLICT
                raise exc

            # Mark as claimed
            user_achievement.is_claimed = True
            user_achievement.claimed_at = timezone.now()
            user_achievement.points_awarded = user_achievement.achievement.reward_value
            user_achievement.save(
                update_fields=["is_claimed", "claimed_at", "points_awarded"]
            )

            # Award points (synchronously to ensure consistency)
            from api.user.points.services import award_points

            award_points(
                user=user,
                points=user_achievement.achievement.reward_value,
                source="ACHIEVEMENT",
                description=f"Claimed achievement: {user_achievement.achievement.name}",
                async_send=False,  # Synchronous for immediate feedback
                achievement_id=str(user_achievement.achievement.id),
            )

            # Update leaderboard (synchronously for immediate rank update)
            from api.user.social.services.leaderboard_service import LeaderboardService

            leaderboard_service = LeaderboardService()
            leaderboard_service.update_user_leaderboard(user)

            # Recalculate ranks (async - can happen in background)
            from api.user.social.tasks import recalculate_leaderboard_ranks

            recalculate_leaderboard_ranks.delay()

            # Send notification (async) unless suppressed
            if not suppress_notification:
                from api.user.notifications.services import notify

                # Get user's total points after award
                try:
                    total_points = user.points.total_points
                except:
                    total_points = user_achievement.points_awarded

                notify(
                    user=user,
                    template_slug="achievement_claimed",
                    async_send=True,
                    achievement_name=user_achievement.achievement.name,
                    points=user_achievement.points_awarded,
                    total_points=total_points,
                )

            self.log_info(
                f"Achievement claimed: {user_achievement.achievement.name} by {user.username}"
            )
            return user_achievement

        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to claim achievement")

    def claim_multiple_achievements(
        self, user, achievement_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Claim multiple achievements at once with batched notification.
        Useful for bulk claiming.

        Returns:
            Dict with claimed achievements and error details
        """
        claimed_achievements = []
        failed_claims = []
        total_points = 0

        for achievement_id in achievement_ids:
            try:
                # Claim with suppressed notification
                claimed = self.claim_achievement(
                    user, achievement_id, suppress_notification=True
                )
                claimed_achievements.append(claimed)
                total_points += claimed.points_awarded or 0
            except ServiceException as e:
                # Log error but continue with other achievements
                failed_claims.append({
                    'achievement_id': achievement_id,
                    'error': e.detail,
                    'code': getattr(e, 'code', 'unknown_error')
                })
                self.log_warning(
                    f"Failed to claim achievement {achievement_id}: {e.detail}"
                )

        # Send ONE consolidated notification for all claims
        if claimed_achievements:
            from api.user.notifications.services import notify

            if len(claimed_achievements) == 1:
                # Single claim - use regular notification
                achievement = claimed_achievements[0]
                try:
                    user_total_points = user.points.total_points
                except:
                    user_total_points = total_points

                notify(
                    user=user,
                    template_slug="achievement_claimed",
                    async_send=True,
                    achievement_name=achievement.achievement.name,
                    points=achievement.points_awarded,
                    total_points=user_total_points,
                )
            else:
                # Multiple claims - use bulk notification
                achievement_names = ", ".join(
                    [c.achievement.name for c in claimed_achievements]
                )

                notify(
                    user=user,
                    template_slug="bulk_achievements_claimed",
                    async_send=True,
                    count=len(claimed_achievements),
                    achievement_names=achievement_names,
                    total_points=total_points,
                )

            self.log_info(
                f"Bulk claimed {len(claimed_achievements)} achievements for {user.username}"
            )

        # Return detailed results
        return {
            'claimed_achievements': claimed_achievements,
            'failed_claims': failed_claims,
            'total_points_awarded': total_points,
            'success_count': len(claimed_achievements),
            'failure_count': len(failed_claims)
        }
