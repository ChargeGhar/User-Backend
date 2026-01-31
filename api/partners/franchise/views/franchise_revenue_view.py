"""
Franchise Revenue View

GET /api/partner/franchise/revenue/ - View own stations' revenue transactions
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import IsFranchise
from api.partners.franchise.services import FranchiseRevenueService

franchise_revenue_router = CustomViewRouter()


@franchise_revenue_router.register(r"partner/franchise/revenue", name="franchise-revenue")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="View Revenue Transactions",
    description="""
    View own stations' revenue transactions with filters.
    
    Business Rules:
    - BR12.2: Only own stations' transactions
    """,
    parameters=[
        OpenApiParameter('station_id', type=str, description='Filter by station UUID'),
        OpenApiParameter('vendor_id', type=str, description='Filter by vendor UUID'),
        OpenApiParameter('period', type=str, description='today|week|month|year|custom'),
        OpenApiParameter('start_date', type=str, description='Custom period start (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='Custom period end (YYYY-MM-DD)'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class FranchiseRevenueView(GenericAPIView, BaseAPIView):
    """Franchise revenue transactions"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get revenue transactions"""
        def operation():
            franchise = request.user.partner_profile
            filters = {
                'station_id': request.query_params.get('station_id'),
                'vendor_id': request.query_params.get('vendor_id'),
                'period': request.query_params.get('period'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = FranchiseRevenueService()
            return service.get_revenue_list(franchise, filters)
        
        return self.handle_service_operation(
            operation,
            "Revenue retrieved successfully",
            "Failed to retrieve revenue"
        )
