"""
Core points functionality - history, summary, and leaderboard
"""

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call, cached_response
from api.user.points import serializers
from api.user.points.services.points_service import PointsService
from api.user.points.services.points_leaderboard_service import PointsLeaderboardService

points_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@points_router.register(r"points/history", name="points-history")
class PointsHistoryView(GenericAPIView, BaseAPIView):
    """Points transaction history endpoint"""
    serializer_class = serializers.PointsTransactionListSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Points"],
        summary="Get user points transaction history",
        description="Retrieve paginated list of user's points transactions with optional filtering",
        parameters=[
            OpenApiParameter("transaction_type", str, description="Filter by transaction type"),
            OpenApiParameter("source", str, description="Filter by source"),
            OpenApiParameter("start_date", str, description="Filter from date (ISO format)"),
            OpenApiParameter("end_date", str, description="Filter to date (ISO format)"),
            OpenApiParameter("page", int, description="Page number"),
            OpenApiParameter("page_size", int, description="Items per page"),
        ],
        responses={200: serializers.PointsHistoryResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user points transaction history"""
        def operation():
            # Validate filters
            filter_serializer = serializers.PointsHistoryFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            filters = filter_serializer.validated_data

            # Get points history
            service = PointsService()
            history_data = service.get_points_history(request.user, filters)

            # Serialize transactions with MVP list serializer
            transactions_serializer = serializers.PointsTransactionListSerializer(
                history_data['results'], many=True
            )

            return {
                'results': transactions_serializer.data,
                'pagination': history_data['pagination']
            }

        return self.handle_service_operation(
            operation,
            "Points history retrieved successfully",
            "Failed to retrieve points history"
        )



@points_router.register(r"points/summary", name="points-summary")
class PointsSummaryView(GenericAPIView, BaseAPIView):
    """Points summary endpoint"""
    serializer_class = serializers.PointsSummarySerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Points"],
        summary="Get user points summary",
        description="Retrieve comprehensive points overview including current balance, earnings breakdown, and referral stats",
        responses={200: serializers.PointsSummaryResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get comprehensive points summary for user - REAL-TIME DATA (no caching)"""
        def operation():
            service = PointsService()
            summary_data = service.get_points_summary(request.user)
            
            serializer = serializers.PointsSummarySerializer(summary_data)
            return serializer.data

        return self.handle_service_operation(
            operation,
            "Points summary retrieved successfully",
            "Failed to retrieve points summary"
        )



@points_router.register(r"points/leaderboard", name="points-leaderboard")
class PointsLeaderboardView(GenericAPIView, BaseAPIView):
    """Points leaderboard endpoint"""
    serializer_class = serializers.PointsLeaderboardListSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Points"],
        summary="Get points leaderboard",
        description="Retrieve points leaderboard with optional user inclusion",
        parameters=[
            OpenApiParameter("limit", int, description="Number of top users to return (default: 10)"),
            OpenApiParameter("include_me", bool, description="Include authenticated user if not in top list"),
        ],
        responses={200: serializers.PointsLeaderboardResponseSerializer}
    )
    @log_api_call()
    @cached_response(timeout=300)  # Cache for 5 minutes - leaderboard changes slowly
    def get(self, request: Request) -> Response:
        """Get points leaderboard - CACHED for performance"""
        def operation():
            limit = int(request.query_params.get('limit', 10))
            include_me = request.query_params.get('include_me', 'false').lower() == 'true'

            service = PointsLeaderboardService()
            leaderboard = service.get_points_leaderboard(
                limit=limit,
                include_user=request.user if include_me else None
            )

            # Use MVP list serializer for better performance
            serializer = serializers.PointsLeaderboardListSerializer(leaderboard, many=True)
            return serializer.data

        return self.handle_service_operation(
            operation,
            "Points leaderboard retrieved successfully",
            "Failed to retrieve points leaderboard"
        )
