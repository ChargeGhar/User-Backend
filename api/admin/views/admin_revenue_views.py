"""
Admin Revenue Views
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
from api.admin.services.admin_revenue_service import AdminRevenueService


admin_revenue_router = CustomViewRouter()


@admin_revenue_router.register(r"admin/revenue", name="admin-revenue")
@extend_schema(
    tags=["Admin - Partners"],
    summary="Get All Revenue Distributions",
    description="View all revenue distributions across entire platform with complete transaction and rental details for full auditability",
    parameters=[
        OpenApiParameter('station_id', type=str, description='Filter by station UUID'),
        OpenApiParameter('franchise_id', type=str, description='Filter by franchise UUID'),
        OpenApiParameter('vendor_id', type=str, description='Filter by vendor UUID'),
        OpenApiParameter('chargeghar_only', type=bool, description='Show only ChargeGhar-owned stations'),
        OpenApiParameter('start_date', type=str, description='From date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='To date (YYYY-MM-DD)'),
        OpenApiParameter('is_distributed', type=bool, description='Filter by distribution status'),
        OpenApiParameter('transaction_status', type=str, description='Filter by transaction status (PENDING, SUCCESS, FAILED, REFUNDED)'),
        OpenApiParameter('is_reversal', type=bool, description='Filter reversals'),
        OpenApiParameter('page', type=int, description='Page number (default: 1)'),
        OpenApiParameter('page_size', type=int, description='Items per page (default: 20)'),
    ],
    responses={200: BaseResponseSerializer}
)
class AdminRevenueView(GenericAPIView, BaseAPIView):
    """Admin revenue view"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all revenue distributions"""
        def operation():
            filters = {
                'station_id': request.query_params.get('station_id'),
                'franchise_id': request.query_params.get('franchise_id'),
                'vendor_id': request.query_params.get('vendor_id'),
                'chargeghar_only': request.query_params.get('chargeghar_only'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'is_distributed': request.query_params.get('is_distributed'),
                'transaction_status': request.query_params.get('transaction_status'),
                'is_reversal': request.query_params.get('is_reversal'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = AdminRevenueService()
            return service.get_all_revenue(filters)
        
        return self.handle_service_operation(
            operation,
            "Revenue data retrieved successfully",
            "Failed to retrieve revenue data"
        )
