"""
System monitoring, logs, analytics and health checks - centralized observability for platform health
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.models import AdminActionLog
from api.admin.services import AdminAnalyticsService, AdminSystemService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

monitoring_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@monitoring_router.register(r"admin/action-logs", name="admin-action-logs")
@extend_schema(
    tags=["Admin - Monitor"],
    summary="Admin Action Logs",
    description="View admin action audit logs (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminActionLogView(GenericAPIView, BaseAPIView):
    """Admin action logs for audit trail"""
    serializer_class = serializers.AdminActionLogSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get admin action logs"""
        def operation():
            logs = AdminActionLog.objects.select_related('admin_user').order_by('-created_at')[:100]
            serializer = self.get_serializer(logs, many=True)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            "Action logs retrieved successfully",
            "Failed to retrieve action logs"
        )

@monitoring_router.register(r"admin/system-logs", name="admin-system-logs")
@extend_schema(
    tags=["Admin - Monitor"],
    summary="System Logs",
    description="View system logs for debugging (Staff only)",
    request=serializers.SystemLogFiltersSerializer,
    responses={200: BaseResponseSerializer}
)
class SystemLogView(GenericAPIView, BaseAPIView):
    """System logs for debugging"""
    serializer_class = serializers.SystemLogSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get system logs with filters"""
        def operation():
            filter_serializer = serializers.SystemLogFiltersSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminSystemService()
            result = service.get_system_logs(filter_serializer.validated_data)
            
            # Serialize the logs in the results
            if result and 'results' in result:
                serialized_logs = serializers.SystemLogSerializer(result['results'], many=True).data
                result['results'] = serialized_logs
            
            return result
        
        return self.handle_service_operation(
            operation,
            "System logs retrieved successfully",
            "Failed to retrieve system logs"
        )


# ============================================================
# Dashboard & Analytics Views
# ============================================================
@monitoring_router.register(r"admin/dashboard", name="admin-dashboard")
@extend_schema(
    tags=["Admin - Monitor"],
    summary="Admin Dashboard Analytics",
    description="Get comprehensive dashboard analytics and metrics (Staff only)",
    responses={200: serializers.DashboardAnalyticsSerializer}
)
class AdminDashboardView(GenericAPIView, BaseAPIView):
    """Admin dashboard with analytics"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get dashboard analytics"""
        def operation():
            service = AdminAnalyticsService()
            analytics = service.get_dashboard_analytics()
            return analytics
        
        return self.handle_service_operation(
            operation,
            "Dashboard analytics retrieved successfully",
            "Failed to retrieve dashboard analytics"
        )

@monitoring_router.register(r"admin/system-health", name="admin-system-health")
@extend_schema(
    tags=["Admin - Monitor"],
    summary="System Health",
    description="Get comprehensive system health metrics (Staff only)",
    responses={200: serializers.SystemHealthSerializer}
)
class SystemHealthView(GenericAPIView, BaseAPIView):
    """System health monitoring"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get system health"""
        def operation():
            service = AdminSystemService()
            health = service.get_system_health()
            return health
        
        return self.handle_service_operation(
            operation,
            "System health retrieved successfully",
            "Failed to retrieve system health"
        )