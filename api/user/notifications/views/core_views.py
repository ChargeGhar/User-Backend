"""
Core notification operations - list and statistics
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
from api.common.decorators import log_api_call, cached_response
from api.user.notifications import serializers
from api.user.notifications.services.notification import NotificationService

core_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@core_router.register(r"notifications", name="notifications-list")
class NotificationListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.NotificationListSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Notifications"],
        summary="Get User Notifications",
        description="Retrieve user notifications with optional filtering by type, channel, read status, and date range",
        responses={200: serializers.NotificationListResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="notification_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by notification type (rental, payment, promotion, system, achievement)",
                required=False
            ),
            OpenApiParameter(
                name="channel",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by channel (in_app, push, sms, email)",
                required=False
            ),
            OpenApiParameter(
                name="is_read",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by read status (true/false)",
                required=False
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 20)",
                required=False
            )
        ]
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user notifications - REAL-TIME (user-specific data)"""
        def operation():
            service = NotificationService()
            
            # Build filters from query parameters
            filters = {}
            if request.query_params.get('notification_type'):
                filters['notification_type'] = request.query_params.get('notification_type')
            
            if request.query_params.get('channel'):
                filters['channel'] = request.query_params.get('channel')
            
            if request.query_params.get('is_read') is not None:
                filters['is_read'] = request.query_params.get('is_read').lower() == 'true'
            
            if request.query_params.get('page'):
                filters['page'] = int(request.query_params.get('page'))
            
            if request.query_params.get('page_size'):
                filters['page_size'] = int(request.query_params.get('page_size'))
            
            result = service.get_user_notifications(request.user, filters)
            
            # Use MVP list serializer for performance
            serializer = serializers.NotificationListSerializer(result['results'], many=True)
            
            return {
                'notifications': serializer.data,
                'pagination': result['pagination']
            }
        
        return self.handle_service_operation(
            operation,
            "Notifications retrieved successfully",
            "Failed to retrieve notifications"
        )


@core_router.register(r"notifications/stats", name="notifications-stats")
class NotificationStatsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.NotificationStatsSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Notifications"],
        summary="Get Notification Statistics",
        description="Retrieve notification statistics for the authenticated user",
        responses={200: serializers.NotificationStatsResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get notification statistics - REAL-TIME (updates immediately after user actions)"""
        def operation():
            service = NotificationService()
            stats = service.get_notification_stats(request.user)
            
            serializer = serializers.NotificationStatsSerializer(stats)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Notification statistics retrieved successfully",
            "Failed to retrieve notification statistics"
        )

