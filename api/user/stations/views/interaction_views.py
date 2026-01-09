"""
User interactions - favorite toggle and issue reporting
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.stations import serializers
from api.user.stations.services import StationFavoriteService, StationIssueService

interaction_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@interaction_router.register("stations/<str:serial_number>/favorite", name="station-favorite")
@extend_schema(
    tags=["Stations"],
    summary="Toggle Station Favorite",
    description="Add or remove station from user's favorites",
    parameters=[
        OpenApiParameter("serial_number", OpenApiTypes.STR, OpenApiParameter.PATH, description="Station serial number", required=True)
    ],
    request=None,  # Explicitly no request body
    responses={200: serializers.StationFavoriteResponseSerializer}
)
class StationFavoriteView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    # Remove serializer_class to prevent request body in Swagger
    
    @log_api_call()
    def post(self, request: Request, serial_number: str) -> Response:
        """Toggle station favorite status"""
        def operation():
            favorite_service = StationFavoriteService()
            result = favorite_service.toggle_favorite(request.user, serial_number)
            return {
                'is_favorite': result['is_favorite'],
                'message': result['message']
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Favorite status updated successfully",
            error_message="Failed to update favorite status"
        )

# ===============================
# STATION ISSUE REPORTING ENDPOINTS
# ===============================

@interaction_router.register("stations/<str:serial_number>/report-issue", name="station-report-issue")
@extend_schema(
    tags=["Stations"],
    summary="Report Station Issue",
    description="Report problems with a charging station",
    parameters=[
        OpenApiParameter("serial_number", OpenApiTypes.STR, OpenApiParameter.PATH, description="Station serial number", required=True)
    ],
    request=serializers.StationIssueCreateSerializer,
    responses={201: serializers.StationIssueResponseSerializer}
)
class StationReportIssueView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.StationIssueCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @log_api_call()
    def post(self, request: Request, serial_number: str) -> Response:
        """Report station issue"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            issue_service = StationIssueService()
            issue = issue_service.report_issue(
                user=request.user,
                station_sn=serial_number,
                validated_data=serializer.validated_data
            )
            
            response_serializer = serializers.StationIssueSerializer(issue)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Issue reported successfully",
            error_message="Failed to report issue",
            success_status=status.HTTP_201_CREATED
        )