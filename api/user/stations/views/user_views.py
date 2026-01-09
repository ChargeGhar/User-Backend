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
from api.user.stations.services import StationFavoriteService, StationIssueService

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

@user_router.register("stations/my-reports", name="user-station-reports")
@extend_schema(
    tags=["Stations"],
    summary="My Issue Reports",
    description="Get issues reported by the authenticated user",
    parameters=[
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page (max 50)"),
    ],
    responses={200: serializers.UserStationReportsResponseSerializer}
)
class UserStationReportsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.StationIssueSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user's reported issues"""
        def operation():
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 50)
            
            issue_service = StationIssueService()
            result = issue_service.get_user_reported_issues(request.user, page, page_size)
            
            serializer = self.get_serializer(
                result.get('results', []), 
                many=True, 
                context={'request': request}
            )
            
            return {
                'count': result['pagination']['total_count'],
                'next': result['pagination']['has_previous'],
                'previous': result['pagination']['has_previous'],
                'results': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Reports retrieved successfully",
            error_message="Failed to retrieve reports"
        )

