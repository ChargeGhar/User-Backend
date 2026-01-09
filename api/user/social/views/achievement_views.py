"""
Achievement operations - user achievements, unlock, and bulk operations
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.social import serializers
from api.user.social.services import (
    AchievementRealtimeService,
    AchievementClaimService,
)

achievement_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@achievement_router.register(r"social/achievements", name="social-achievements")
class UserAchievementsView(GenericAPIView, BaseAPIView):
    """User achievements endpoint"""

    serializer_class = serializers.UserAchievementsResponseSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Social"],
        summary="Get user achievements (Real-Time)",
        description="Retrieve all achievements with real-time progress calculation. Unlocks achievements when criteria are met.",
        request=None,  # GET request - no body
        responses={200: serializers.UserAchievementsResponseSerializer},
    )
    @log_api_call()
    # NO CACHING - Real-time data required for achievement progress
    def get(self, request: Request) -> Response:
        """Get user achievements with real-time progress calculation"""

        def operation():
            service = AchievementRealtimeService()

            # Calculate and update progress in real-time
            user_achievements = service.update_all_progress_realtime(request.user)

            # Get unclaimed count
            unclaimed_count = service.get_unlocked_unclaimed_count(request.user)

            # Serialize
            serializer = serializers.UserAchievementSerializer(
                user_achievements, many=True
            )

            return {
                "achievements": serializer.data,
                "unclaimed_count": unclaimed_count,
                "total_achievements": len(user_achievements),
            }

        return self.handle_service_operation(
            operation,
            "User achievements retrieved successfully",
            "Failed to retrieve user achievements",
        )



@achievement_router.register(r"social/unlock/<uuid:achievement_id>", name="social-unlock-achievement")
class UnlockAchievementView(GenericAPIView, BaseAPIView):
    """Claim unlocked achievement"""

    serializer_class = serializers.ClaimAchievementResponseSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Social"],
        summary="Claim unlocked achievement",
        description="Claim an achievement that has been unlocked. Awards points and updates leaderboard.",
        request=None,  # No request body - achievement_id comes from URL
        responses={
            200: serializers.ClaimAchievementResponseSerializer,
            400: OpenApiResponse(description="Achievement not unlocked"),
            404: OpenApiResponse(description="Achievement not found"),
            409: OpenApiResponse(description="Achievement already claimed"),
        },
    )
    @log_api_call()
    def post(self, request: Request, achievement_id: str) -> Response:
        """Claim an unlocked achievement"""

        def operation():
            service = AchievementClaimService()

            # Claim achievement
            user_achievement = service.claim_achievement(request.user, achievement_id)

            # Get updated leaderboard position
            from api.user.social.models import UserLeaderboard

            try:
                leaderboard = UserLeaderboard.objects.get(user=request.user)
                rank = leaderboard.rank
                total_points = leaderboard.total_points_earned
            except UserLeaderboard.DoesNotExist:
                rank = None
                total_points = 0

            # Serialize response
            achievement_serializer = serializers.UserAchievementSerializer(
                user_achievement
            )

            return {
                "achievement": achievement_serializer.data,
                "points_awarded": user_achievement.points_awarded,
                "new_rank": rank,
                "total_points": total_points,
            }

        return self.handle_service_operation(
            operation, "Achievement claimed successfully", "Failed to claim achievement"
        )



@achievement_router.register(r"social/unlock/bulk", name="social-unlock-bulk")
class BulkUnlockAchievementView(GenericAPIView, BaseAPIView):
    """Claim multiple unlocked achievements"""

    serializer_class = serializers.BulkClaimSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Social"],
        summary="Claim multiple achievements",
        description="Claim multiple unlocked achievements at once",
        request=serializers.BulkClaimSerializer,
        responses={200: serializers.BulkClaimResponseSerializer},
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Claim multiple achievements"""

        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            service = AchievementClaimService()

            # Claim multiple
            result = service.claim_multiple_achievements(
                request.user, serializer.validated_data["achievement_ids"]
            )

            return {
                "claimed_count": result['success_count'],
                "failed_count": result['failure_count'],
                "total_points_awarded": result['total_points_awarded'],
                "achievements": serializers.UserAchievementSerializer(
                    result['claimed_achievements'], many=True
                ).data,
                "failed_claims": result['failed_claims'],
            }

        return self.handle_service_operation(
            operation,
            "Bulk claim operation completed",
            "Failed to process bulk claim",
        )

