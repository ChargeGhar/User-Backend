"""
Vendor Dashboard View

GET /api/partner/vendor/dashboard/
"""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import IsRevenueVendor
from api.partners.vendor.serializers import VendorDashboardSerializer
from api.partners.vendor.services import VendorDashboardService

vendor_dashboard_router = CustomViewRouter()


@vendor_dashboard_router.register(r"partner/vendor/dashboard", name="vendor-dashboard")
@extend_schema(
    tags=["Partner - Vendor"],
    summary="Get Vendor Dashboard Statistics",
    description="""
    Returns aggregated dashboard statistics for the logged-in revenue vendor.
    
    Business Rules Implemented:
    - BR2.3: Vendor has ONLY ONE station
    - BR9.2: Revenue Vendors have dashboard access
    - BR10.4: Vendors view ONLY own station
    - BR12.3: Vendors view ONLY own transactions
    - BR12.7: Vendors view only own earnings
    """,
    responses={200: BaseResponseSerializer}
)
class VendorDashboardView(GenericAPIView, BaseAPIView):
    """Vendor dashboard statistics"""
    permission_classes = [IsRevenueVendor]
    serializer_class = VendorDashboardSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get vendor dashboard stats"""
        def operation():
            vendor_id = str(request.user.partner_profile.id)
            return VendorDashboardService.get_dashboard_stats(vendor_id)
        
        return self.handle_service_operation(
            operation,
            "Vendor dashboard retrieved successfully",
            "Failed to retrieve vendor dashboard"
        )
