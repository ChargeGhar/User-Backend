"""
LeaderboardService - Individual Service File
============================================================

Service for leaderboard operations

Created: 2025-01-16
Part of: Social App Real-Time Achievement Update
"""
from __future__ import annotations

from typing import Dict, Any
from django.db import transaction
from django.db.models import F
from django.contrib.auth import get_user_model

from api.common.services.base import CRUDService
from api.user.social.models import UserLeaderboard

User = get_user_model()

class LeaderboardService(CRUDService):
    """Service for leaderboard operations"""

    model = UserLeaderboard

    def get_leaderboard(
        self,
        category: str = "overall",
        period: str = "all_time",
        limit: int = 10,
        include_user: User = None,
    ) -> Dict[str, Any]:
        """Get leaderboard with filtering"""
        try:
            # Caching is now handled by view decorators

            # Get base queryset
            queryset = UserLeaderboard.objects.select_related("user")

            # Apply period filtering (for now, just all_time)
            # In a real implementation, you'd filter by date ranges

            # Apply category sorting
            if category == "rentals":
                queryset = queryset.order_by("-total_rentals", "-total_points_earned")
            elif category == "points":
                queryset = queryset.order_by("-total_points_earned", "-total_rentals")
            elif category == "referrals":
                queryset = queryset.order_by("-referrals_count", "-total_points_earned")
            elif category == "timely_returns":
                queryset = queryset.order_by("-timely_returns", "-total_rentals")
            else:  # overall
                queryset = queryset.order_by("rank")

            # Get top entries
            top_entries = list(queryset[:limit])

            # Include specific user if requested and not in top list
            user_entry = None
            if include_user:
                try:
                    user_leaderboard = UserLeaderboard.objects.get(user=include_user)
                    user_in_top = any(
                        entry.user_id == include_user.id for entry in top_entries
                    )

                    if not user_in_top:
                        user_entry = user_leaderboard
                except UserLeaderboard.DoesNotExist:
                    pass

            result = {
                "leaderboard": top_entries,
                "user_entry": user_entry,
                "category": category,
                "period": period,
                "total_users": UserLeaderboard.objects.count(),
            }

            # Caching is now handled by view decorators

            return result

        except Exception as e:
            self.handle_service_error(e, "Failed to get leaderboard")

    @transaction.atomic
    def update_user_leaderboard(self, user) -> UserLeaderboard:
        """Update user's leaderboard statistics"""
        try:
            # Calculate user statistics
            from api.user.rentals.models import Rental
            from api.user.points.models import Referral

            rentals = Rental.objects.filter(user=user)
            total_rentals = rentals.count()
            timely_returns = rentals.filter(is_returned_on_time=True).count()

            # Get points from user points model
            try:
                total_points_earned = user.points.total_points
            except:
                total_points_earned = 0

            # Get referrals count
            referrals_count = Referral.objects.filter(
                inviter=user, status="COMPLETED"
            ).count()

            # Update or create leaderboard entry
            leaderboard, created = UserLeaderboard.objects.get_or_create(
                user=user,
                defaults={
                    "rank": 999999,  # Will be updated in rank calculation
                    "total_rentals": total_rentals,
                    "total_points_earned": total_points_earned,
                    "referrals_count": referrals_count,
                    "timely_returns": timely_returns,
                },
            )

            if not created:
                leaderboard.total_rentals = total_rentals
                leaderboard.total_points_earned = total_points_earned
                leaderboard.referrals_count = referrals_count
                leaderboard.timely_returns = timely_returns
                leaderboard.save(
                    update_fields=[
                        "total_rentals",
                        "total_points_earned",
                        "referrals_count",
                        "timely_returns",
                        "last_updated",
                    ]
                )

            return leaderboard

        except Exception as e:
            self.handle_service_error(e, "Failed to update user leaderboard")

    @transaction.atomic
    def update_after_achievement_claim(self, user) -> UserLeaderboard:
        """
        Update leaderboard after achievement claim.
        Optimized for immediate feedback.

        Returns:
            Updated UserLeaderboard object
        """
        try:
            # Update user's leaderboard stats
            leaderboard = self.update_user_leaderboard(user)

            # Don't recalculate all ranks here (too slow)
            # Let background task handle it

            self.log_info(
                f"Leaderboard updated for user {user.username} after achievement claim"
            )
            return leaderboard

        except Exception as e:
            self.handle_service_error(e, "Failed to update leaderboard after claim")

    def recalculate_ranks(self) -> int:
        """Recalculate all user ranks"""
        try:
            # Calculate overall score for ranking
            # Formula: (points * 0.4) + (rentals * 0.3) + (referrals * 20) + (timely_returns * 0.3)
            leaderboards = UserLeaderboard.objects.annotate(
                score=F("total_points_earned") * 0.4
                + F("total_rentals") * 0.3
                + F("referrals_count") * 20
                + F("timely_returns") * 0.3
            ).order_by("-score")

            # Update ranks
            updated_count = 0
            for rank, leaderboard in enumerate(leaderboards, 1):
                if leaderboard.rank != rank:
                    leaderboard.rank = rank
                    leaderboard.save(update_fields=["rank", "last_updated"])
                    updated_count += 1

            # Cache clearing is now handled by view decorators

            self.log_info(f"Recalculated ranks for {updated_count} users")
            return updated_count

        except Exception as e:
            self.handle_service_error(e, "Failed to recalculate ranks")
