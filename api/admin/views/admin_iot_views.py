"""
Admin IoT Views
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
from api.admin.services.admin_iot_service import AdminIoTService


admin_iot_router = CustomViewRouter()


@admin_iot_router.register(r"admin/iot/history", name="admin-iot-history")
@extend_schema(
    tags=["Admin - Partners"],
    summary="Get All IoT History",
    description="View all IoT actions across all partners (franchise and vendor)",
    parameters=[
        OpenApiParameter('partner_id', type=str, description='Filter by partner UUID'),
        OpenApiParameter('station_id', type=str, description='Filter by station UUID'),
        OpenApiParameter('action_type', type=str, description='Filter by action type (EJECT, REBOOT, CHECK, etc.)'),
        OpenApiParameter('performed_from', type=str, description='Filter by source (MOBILE_APP, DASHBOARD, ADMIN_PANEL)'),
        OpenApiParameter('is_successful', type=bool, description='Filter by success status'),
        OpenApiParameter('start_date', type=str, description='From date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='To date (YYYY-MM-DD)'),
        OpenApiParameter('page', type=int, description='Page number (default: 1)'),
        OpenApiParameter('page_size', type=int, description='Items per page (default: 20)'),
    ],
    responses={200: BaseResponseSerializer}
)
class AdminIoTHistoryView(GenericAPIView, BaseAPIView):
    """Admin IoT history view"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all IoT history"""
        def operation():
            filters = {
                'partner_id': request.query_params.get('partner_id'),
                'station_id': request.query_params.get('station_id'),
                'action_type': request.query_params.get('action_type'),
                'performed_from': request.query_params.get('performed_from'),
                'is_successful': request.query_params.get('is_successful'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = AdminIoTService()
            return service.get_all_iot_history(filters)
        
        return self.handle_service_operation(
            operation,
            "IoT history retrieved successfully",
            "Failed to retrieve IoT history"
        )
