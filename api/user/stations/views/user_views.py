"""
User-specific operations - favorites and reports listing
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.stations import serializers
from api.user.stations.services import (
    StationFavoriteService,
    UserIssueReportService,
)

user_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@user_router.register("stations/favorites", name="user-favorite-stations")
@extend_schema(
    tags=["Stations"],
    summary="My Favorite Stations",
    description="Get user's favorite stations list",
    parameters=[
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page (max 50)"),
    ],
    responses={200: serializers.UserFavoriteStationsResponseSerializer}
)
class UserFavoriteStationsView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user's favorite stations"""
        def operation():
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 50)
            
            favorite_service = StationFavoriteService()
            result = favorite_service.get_user_favorites(request.user, page, page_size)
            
            # Serialize stations
            serializer = serializers.StationListSerializer(
                result.get('results', []), 
                many=True, 
                context={'request': request}
            )
            
            return {
                'count': result['pagination']['total_count'],
                'next': result['pagination']['has_next'],
                'previous': result['pagination']['has_previous'],
                'results': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Favorite stations retrieved successfully",
            error_message="Failed to retrieve favorite stations"
        )

# ===============================
# USER STATION REPORTS (must be before <str:serial_number> route)
# ===============================

@user_router.register("issues/my-reports", name="user-issue-reports")
@extend_schema(
    tags=["Stations"],
    summary="My Issue Reports",
    description="Get station and rental issues reported by the authenticated user",
    parameters=[
        OpenApiParameter("issue_scope", OpenApiTypes.STR, description="all | station | rental"),
        OpenApiParameter("start_date", OpenApiTypes.DATE, description="Filter from reported date (YYYY-MM-DD)"),
        OpenApiParameter("end_date", OpenApiTypes.DATE, description="Filter to reported date (YYYY-MM-DD)"),
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page (max 50)"),
    ],
    responses={200: serializers.UserIssueReportsResponseSerializer}
)
class UserIssueReportsView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get unified issue reports for authenticated user."""

        def operation():
            query_serializer = serializers.UserIssueReportsQuerySerializer(data=request.query_params)
            query_serializer.is_valid(raise_exception=True)

            issue_scope = query_serializer.validated_data.get('issue_scope', 'all')
            page = query_serializer.validated_data.get('page', 1)
            page_size = query_serializer.validated_data.get('page_size', 20)
            start_date, end_date = query_serializer.get_reported_at_range()

            issue_service = UserIssueReportService()
            result = issue_service.get_user_issue_reports(
                user=request.user,
                issue_scope=issue_scope,
                page=page,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
            )

            payload_serializer = serializers.UserIssueReportSerializer(
                result.get('results', []), many=True, context={'request': request}
            )

            return {
                'count': result['pagination']['total_count'],
                'next': result['pagination']['has_next'],
                'previous': result['pagination']['has_previous'],
                'results': payload_serializer.data,
            }

        return self.handle_service_operation(
            operation,
            success_message="Reports retrieved successfully",
            error_message="Failed to retrieve reports",
        )

