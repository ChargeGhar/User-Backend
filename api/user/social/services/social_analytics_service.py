"""
SocialAnalyticsService - Individual Service File
============================================================

Service for social analytics

Created: 2025-01-16
Part of: Social App Real-Time Achievement Update
"""
from __future__ import annotations

from typing import Dict, Any, List
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.common.services.base import BaseService
from api.user.social.models import Achievement, UserAchievement, UserLeaderboard

User = get_user_model()

class SocialAnalyticsService(BaseService):
    """Service for social analytics"""

    def get_social_stats(self, user=None) -> Dict[str, Any]:
        """Get social statistics"""
        try:
            # General stats
            total_users = User.objects.filter(is_active=True).count()
            total_achievements = Achievement.objects.filter(is_active=True).count()
            unlocked_achievements = UserAchievement.objects.filter(
                is_unlocked=True
            ).count()

            # User-specific stats
            user_stats = {}
            if user:
                try:
                    user_leaderboard = UserLeaderboard.objects.get(user=user)
                    user_achievements = UserAchievement.objects.filter(user=user)

                    user_stats = {
                        "user_rank": user_leaderboard.rank,
                        "user_achievements_unlocked": user_achievements.filter(
                            is_unlocked=True
                        ).count(),
                        "user_achievements_total": user_achievements.count(),
                    }
                except UserLeaderboard.DoesNotExist:
                    user_stats = {
                        "user_rank": 0,
                        "user_achievements_unlocked": 0,
                        "user_achievements_total": 0,
                    }

            # Top performers
            top_performers = self._get_top_performers()

            # Recent achievements
            recent_achievements = self._get_recent_achievements()

            return {
                "total_users": total_users,
                "total_achievements": total_achievements,
                "unlocked_achievements": unlocked_achievements,
                **user_stats,
                **top_performers,
                "recent_achievements": recent_achievements,
            }

        except Exception as e:
            self.handle_service_error(e, "Failed to get social stats")

    def _get_top_performers(self) -> Dict[str, Any]:
        """Get top performers in different categories"""
        try:
            # Top rental user
            top_rental = UserLeaderboard.objects.order_by("-total_rentals").first()
            top_rental_user = {
                "username": top_rental.user.username if top_rental else None,
                "count": top_rental.total_rentals if top_rental else 0,
            }

            # Top points user
            top_points = UserLeaderboard.objects.order_by("-total_points_earned").first()
            top_points_user = {
                "username": top_points.user.username if top_points else None,
                "count": top_points.total_points_earned if top_points else 0,
            }

            # Top referral user
            top_referral = UserLeaderboard.objects.order_by("-referrals_count").first()
            top_referral_user = {
                "username": top_referral.user.username if top_referral else None,
                "count": top_referral.referrals_count if top_referral else 0,
            }

            return {
                "top_rental_user": top_rental_user,
                "top_points_user": top_points_user,
                "top_referral_user": top_referral_user,
            }

        except Exception as e:
            self.log_error(f"Failed to get top performers: {str(e)}")
            return {
                "top_rental_user": {"username": None, "count": 0},
                "top_points_user": {"username": None, "count": 0},
                "top_referral_user": {"username": None, "count": 0},
            }

    def _get_recent_achievements(self) -> List[Dict[str, Any]]:
        """Get recent achievement unlocks"""
        try:
            recent = (
                UserAchievement.objects.filter(
                    is_unlocked=True,
                    unlocked_at__gte=timezone.now() - timezone.timedelta(days=7),
                )
                .select_related("user", "achievement")
                .order_by("-unlocked_at")[:10]
            )

            return [
                {
                    "username": ua.user.username,
                    "achievement_name": ua.achievement.name,
                    "unlocked_at": ua.unlocked_at,
                    "points_awarded": ua.points_awarded,
                }
                for ua in recent
            ]

        except Exception as e:
            self.log_error(f"Failed to get recent achievements: {str(e)}")
            return []

    def get_achievement_analytics(self) -> Dict[str, Any]:
        """Get achievement analytics for admin"""
        try:
            achievements = Achievement.objects.all()
            total_achievements = achievements.count()
            active_achievements = achievements.filter(is_active=True).count()

            # Total unlocks
            total_unlocks = UserAchievement.objects.filter(is_unlocked=True).count()

            # Most/least unlocked achievements
            achievement_stats = achievements.annotate(
                unlock_count=Count(
                    "userachievement",
                    filter=Q(userachievement__is_unlocked=True),
                )
            ).order_by("-unlock_count")

            total_users = User.objects.count()

            most_unlocked = [
                {
                    "name": a.name,
                    "unlock_count": a.unlock_count,
                    "unlock_rate": (a.unlock_count / total_users * 100)
                    if total_users > 0
                    else 0,
                }
                for a in achievement_stats[:5]
            ]

            least_unlocked = [
                {
                    "name": a.name,
                    "unlock_count": a.unlock_count,
                    "unlock_rate": (a.unlock_count / total_users * 100)
                    if total_users > 0
                    else 0,
                }
                for a in reversed(list(achievement_stats)[-5:])
            ]

            # User engagement
            users_with_achievements = (
                UserAchievement.objects.filter(is_unlocked=True)
                .values("user")
                .distinct()
                .count()
            )

            avg_achievements = (
                UserAchievement.objects.filter(is_unlocked=True).count() / total_users
                if total_users > 0
                else 0
            )

            return {
                "total_achievements": total_achievements,
                "active_achievements": active_achievements,
                "total_unlocks": total_unlocks,
                "most_unlocked": most_unlocked,
                "least_unlocked": least_unlocked,
                "unlock_rate_by_achievement": most_unlocked,  # Same data, different view
                "users_with_achievements": users_with_achievements,
                "average_achievements_per_user": round(avg_achievements, 2),
                "last_updated": timezone.now(),
            }

        except Exception as e:
            self.handle_service_error(e, "Failed to get achievement analytics")
