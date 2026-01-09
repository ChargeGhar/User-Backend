"""
Social features - leaderboard and user statistics
"""

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call, cached_response
from api.user.social import serializers
from api.user.social.services import (
    AchievementRealtimeService,
    LeaderboardService,
    SocialAnalyticsService,
)

social_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@social_router.register(r"social/leaderboard", name="social-leaderboard")
class LeaderboardView(GenericAPIView, BaseAPIView):
    """Leaderboard endpoint"""

    serializer_class = serializers.LeaderboardResponseSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Social"],
        summary="Get leaderboard",
        description="Retrieve leaderboard with filtering options",
        request=None,  # GET request - no body
        parameters=[
            OpenApiParameter(
                "category",
                str,
                description="Leaderboard category (overall, rentals, points, referrals, timely_returns)",
            ),
            OpenApiParameter(
                "period", str, description="Time period (all_time, monthly, weekly)"
            ),
            OpenApiParameter(
                "limit", int, description="Number of entries to return (5-100)"
            ),
            OpenApiParameter(
                "include_me",
                bool,
                description="Include authenticated user if not in top list",
            ),
        ],
        responses={200: serializers.LeaderboardResponseSerializer},
    )
    @log_api_call()
    @cached_response(timeout=300)  # Cache for 5 minutes - leaderboard changes slowly
    def get(self, request: Request) -> Response:
        """Get leaderboard with filtering - CACHED for performance"""

        def operation():
            # Validate filters
            filter_serializer = serializers.LeaderboardFilterSerializer(
                data=request.query_params
            )
            filter_serializer.is_valid(raise_exception=True)
            filters = filter_serializer.validated_data

            include_me = request.query_params.get("include_me", "false").lower() == "true"

            # Get leaderboard
            service = LeaderboardService()
            leaderboard_data = service.get_leaderboard(
                category=filters["category"],
                period=filters["period"],
                limit=filters["limit"],
                include_user=request.user if include_me else None,
            )

            # Serialize leaderboard entries with MVP list serializer
            leaderboard_serializer = serializers.LeaderboardEntryListSerializer(
                leaderboard_data["leaderboard"], many=True
            )

            # Serialize user entry if included
            user_entry_data = None
            if leaderboard_data["user_entry"]:
                user_entry_serializer = serializers.UserLeaderboardSerializer(
                    leaderboard_data["user_entry"]
                )
                user_entry_data = user_entry_serializer.data

            # Get user's unclaimed achievements count
            realtime_service = AchievementRealtimeService()
            unclaimed_count = realtime_service.get_unlocked_unclaimed_count(request.user)

            return {
                "leaderboard": leaderboard_serializer.data,
                "user_entry": user_entry_data,
                "category": leaderboard_data["category"],
                "period": leaderboard_data["period"],
                "total_users": leaderboard_data["total_users"],
                "unclaimed_achievements": unclaimed_count,
            }

        return self.handle_service_operation(
            operation,
            "Leaderboard retrieved successfully",
            "Failed to retrieve leaderboard",
        )

@social_router.register(r"social/stats", name="social-stats")
class SocialStatsView(GenericAPIView, BaseAPIView):
    """Social statistics endpoint"""

    serializer_class = serializers.SocialStatsResponseSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Social"],
        summary="Get social statistics",
        description="Retrieve comprehensive social statistics for the user",
        request=None,  # GET request - no body
        responses={200: serializers.SocialStatsResponseSerializer},
    )
    @log_api_call()
    # NO CACHING - Real-time data required for user stats accuracy
    def get(self, request: Request) -> Response:
        """Get social statistics - Real-time for accuracy"""

        def operation():
            service = SocialAnalyticsService()
            stats = service.get_social_stats(request.user)

            serializer = serializers.SocialStatsSerializer(stats)
            return serializer.data

        return self.handle_service_operation(
            operation,
            "Social statistics retrieved successfully",
            "Failed to retrieve social statistics",
        )
