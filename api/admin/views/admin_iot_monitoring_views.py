"""
Admin IoT Monitoring Views
"""
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.serializers import BaseResponseSerializer
from api.common.decorators import log_api_call
from api.user.auth.permissions import IsStaffPermission
from api.admin.services.admin_iot_monitoring_service import AdminIoTMonitoringService


admin_iot_monitoring_router = CustomViewRouter()


@admin_iot_monitoring_router.register(r"admin/iot/logs", name="admin-iot-logs")
@extend_schema(
    tags=["Admin - Monitor"],
    summary="Get IoT Logs",
    description="View IoT sync logs or station status history based on type parameter",
    parameters=[
        OpenApiParameter('type', type=str, required=True, description='Log type: "sync" or "history"'),
        OpenApiParameter('station_id', type=str, description='Filter by station UUID'),
        OpenApiParameter('sync_type', type=str, description='Filter by sync type (STATUS, FULL, RETURNED) - only for type=sync'),
        OpenApiParameter('status', type=str, description='Filter by status (SUCCESS, FAILED, TIMEOUT for sync; ONLINE, OFFLINE, MAINTENANCE for history)'),
        OpenApiParameter('start_date', type=str, description='From date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='To date (YYYY-MM-DD)'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class AdminIoTLogsView(GenericAPIView, BaseAPIView):
    """Admin IoT logs view - unified endpoint for sync logs and status history"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get IoT logs based on type parameter"""
        def operation():
            log_type = request.query_params.get('type')
            
            if not log_type:
                raise ValueError("Missing required parameter 'type'. Must be 'sync' or 'history'")
            
            filters = {
                'station_id': request.query_params.get('station_id'),
                'sync_type': request.query_params.get('sync_type'),
                'status': request.query_params.get('status'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            
            service = AdminIoTMonitoringService()
            return service.get_iot_logs(log_type, filters)
        
        return self.handle_service_operation(
            operation,
            "IoT logs retrieved successfully",
            "Failed to retrieve IoT logs"
        )
