"""
Notification and broadcast management - send system-wide and targeted notifications
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminNotificationService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

notification_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@notification_router.register(r"admin/broadcast", name="admin-broadcast")
@extend_schema(
    tags=["Admin"],
    summary="Broadcast Message",
    description="Send broadcast message to users (Staff only)",
    request=serializers.BroadcastMessageSerializer,
    responses={200: BaseResponseSerializer}
)
class BroadcastMessageView(GenericAPIView, BaseAPIView):
    """Broadcast message to users"""
    serializer_class = serializers.BroadcastMessageSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def post(self, request: Request) -> Response:
        """Send broadcast message"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminNotificationService()
            result = service.send_broadcast_message(
                serializer.validated_data['title'],
                serializer.validated_data['message'],
                serializer.validated_data['target_audience'],
                serializer.validated_data['send_push'],
                serializer.validated_data['send_email'],
                request.user
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Broadcast message sent successfully",
            "Failed to send broadcast message"
        )