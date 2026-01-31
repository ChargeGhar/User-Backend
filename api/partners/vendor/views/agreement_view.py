"""
Vendor Agreement View

GET /api/partner/vendor/agreement/ - View revenue agreement
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
from api.partners.vendor.serializers.agreement_serializers import VendorAgreementSerializer
from api.partners.vendor.services.vendor_agreement_service import VendorAgreementService

vendor_agreement_router = CustomViewRouter()


@vendor_agreement_router.register(r"partner/vendor/agreement", name="vendor-agreement")
@extend_schema(
    tags=["Partner - Vendor"],
    summary="View Revenue Agreement",
    description="""
    View own revenue agreement details.
    
    Business Rules:
    - BR2.3: Single station
    - BR3.4: Revenue vendors only
    """,
    responses={200: BaseResponseSerializer}
)
class VendorAgreementView(GenericAPIView, BaseAPIView):
    """Vendor agreement"""
    permission_classes = [IsRevenueVendor]
    serializer_class = VendorAgreementSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get agreement"""
        def operation():
            vendor_id = str(request.user.partner_profile.id)
            return VendorAgreementService.get_agreement(vendor_id)
        
        return self.handle_service_operation(
            operation,
            "Agreement retrieved successfully",
            "Failed to retrieve agreement"
        )
