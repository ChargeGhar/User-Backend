"""
Bulk notification actions - mark all read
"""
import logging
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call, rate_limit
from api.user.notifications import serializers
from api.user.notifications.services.notification import NotificationService

action_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@action_router.register(r"notifications/mark-all-read", name="notifications-mark-all-read")
class NotificationMarkAllReadView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.NotificationStatsSerializer
    
    @extend_schema(
        tags=["Notifications"],
        summary="Mark All Notifications as Read",
        description="Mark all user notifications as read and return count of updated notifications",
        responses={200: serializers.NotificationMarkAllReadResponseSerializer}
    )
    @rate_limit(max_requests=10, window_seconds=60)
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Mark all notifications as read - REAL-TIME (user action)"""
        def operation():
            service = NotificationService()
            updated_count = service.mark_all_as_read(request.user)
            
            return {
                'message': 'All notifications marked as read',
                'updated_count': updated_count
            }
        
        return self.handle_service_operation(
            operation,
            "All notifications marked as read successfully",
            "Failed to mark all notifications as read"
        )


