"""
Vendor Payout Views

GET /api/partner/vendor/payouts/ - List own payouts
POST /api/partner/vendor/payouts/request/ - Request payout
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
from api.partners.vendor.serializers.payout_serializers import (
    VendorPayoutListSerializer,
    VendorPayoutRequestSerializer,
    VendorPayoutRequestResponseSerializer
)
from api.partners.vendor.services.vendor_payout_service import VendorPayoutService

vendor_payout_router = CustomViewRouter()


@vendor_payout_router.register(r"partner/vendor/payouts", name="vendor-payouts")
@extend_schema(
    tags=["Partner - Vendor"],
    summary="List Own Payouts",
    description="""
    View own payout history.
    
    Business Rules:
    - BR12.7: Only own payouts
    """,
    parameters=[
        OpenApiParameter('status', type=str, description='PENDING|APPROVED|PROCESSING|COMPLETED|REJECTED'),
        OpenApiParameter('start_date', type=str, description='Start date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='End date (YYYY-MM-DD)'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class VendorPayoutListView(GenericAPIView, BaseAPIView):
    """Vendor payout list"""
    permission_classes = [IsRevenueVendor]
    serializer_class = VendorPayoutListSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get payout list"""
        def operation():
            vendor_id = str(request.user.partner_profile.id)
            filters = {
                'status': request.query_params.get('status'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            return VendorPayoutService.get_payout_list(vendor_id, filters)
        
        return self.handle_service_operation(
            operation,
            "Payouts retrieved successfully",
            "Failed to retrieve payouts"
        )


@vendor_payout_router.register(r"partner/vendor/payouts/request", name="vendor-payout-request")
@extend_schema(
    tags=["Partner - Vendor"],
    summary="Request Payout",
    description="""
    Request new payout from balance.
    
    Business Rules:
    - BR8.4: Revenue vendors only
    - BR12.7: Own balance only
    
    Validations:
    - amount > 0
    - amount <= vendor.balance
    - No pending payout exists
    - Bank details required
    """,
    request=VendorPayoutRequestSerializer,
    responses={200: BaseResponseSerializer}
)
class VendorPayoutRequestView(GenericAPIView, BaseAPIView):
    """Vendor payout request"""
    permission_classes = [IsRevenueVendor]
    serializer_class = VendorPayoutRequestResponseSerializer
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Request payout"""
        def operation():
            vendor_id = str(request.user.partner_profile.id)
            return VendorPayoutService.request_payout(vendor_id, request.data)
        
        return self.handle_service_operation(
            operation,
            "Payout request created successfully",
            "Failed to create payout request"
        )
