"""
Vendor Revenue View

GET /api/partner/vendor/revenue - View own revenue transactions
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import IsRevenueVendor
from api.partners.vendor.serializers.revenue_serializers import VendorRevenueListSerializer
from api.partners.vendor.services.vendor_revenue_service import VendorRevenueService

vendor_revenue_router = CustomViewRouter()


@vendor_revenue_router.register(r"partner/vendor/revenue", name="vendor-revenue")
@extend_schema(
    tags=["Partner - Vendor"],
    summary="View Revenue Transactions",
    description="""
    View own revenue transactions with filters.
    
    Business Rules:
    - BR12.3: Only own transactions
    - BR12.7: Only own earnings
    """,
    parameters=[
        OpenApiParameter('period', type=str, description='today|week|month|year|custom'),
        OpenApiParameter('start_date', type=str, description='Custom period start (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='Custom period end (YYYY-MM-DD)'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class VendorRevenueView(GenericAPIView, BaseAPIView):
    """Vendor revenue transactions"""
    permission_classes = [IsRevenueVendor]
    serializer_class = VendorRevenueListSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get revenue transactions"""
        def operation():
            vendor_id = str(request.user.partner_profile.id)
            filters = {
                'period': request.query_params.get('period'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            return VendorRevenueService.get_revenue_list(vendor_id, filters)
        
        return self.handle_service_operation(
            operation,
            "Revenue retrieved successfully",
            "Failed to retrieve revenue"
        )
