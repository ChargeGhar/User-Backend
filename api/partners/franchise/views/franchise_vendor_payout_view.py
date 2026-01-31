"""
Franchise Vendor Payout Management View

GET /api/partner/franchise/payouts/vendors/ - Sub-vendor payout requests
PATCH /api/partner/franchise/payouts/vendors/{id}/approve/ - Approve vendor payout
PATCH /api/partner/franchise/payouts/vendors/{id}/complete/ - Complete vendor payout
PATCH /api/partner/franchise/payouts/vendors/{id}/reject/ - Reject vendor payout
"""

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import serializers

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.partners.auth.permissions import IsFranchise
from api.partners.franchise.services import FranchiseVendorPayoutService

franchise_vendor_payout_router = CustomViewRouter()


class RejectPayoutSerializer(serializers.Serializer):
    """Reject payout input"""
    reason = serializers.CharField(max_length=500)


@franchise_vendor_payout_router.register(r"partner/franchise/payouts/vendors", name="franchise-vendor-payouts")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="View Vendor Payout Requests",
    description="""
    List vendor payout requests.
    
    Business Rules:
    - BR8.3: Franchise pays Franchise-level Vendors
    - BR10.2: Only own vendors
    """,
    parameters=[
        OpenApiParameter('status', type=str, description='Filter by status'),
        OpenApiParameter('vendor_id', type=str, description='Filter by vendor UUID'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class FranchiseVendorPayoutsView(GenericAPIView, BaseAPIView):
    """Vendor payout requests"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """List vendor payouts"""
        def operation():
            franchise = request.user.partner_profile
            filters = {
                'status': request.query_params.get('status'),
                'vendor_id': request.query_params.get('vendor_id'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = FranchiseVendorPayoutService()
            return service.get_vendor_payouts_list(franchise, filters)
        
        return self.handle_service_operation(
            operation,
            "Vendor payouts retrieved successfully",
            "Failed to retrieve vendor payouts"
        )


@franchise_vendor_payout_router.register(
    r"partner/franchise/payouts/vendors/<uuid:payout_id>/approve",
    name="franchise-vendor-payout-approve"
)
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Approve Vendor Payout",
    description="""
    Approve vendor payout request.
    
    Business Rules:
    - BR10.2: Only own vendors
    - Status must be PENDING
    """,
    responses={200: BaseResponseSerializer}
)
class FranchiseVendorPayoutApproveView(GenericAPIView, BaseAPIView):
    """Approve vendor payout"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Approve payout"""
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseVendorPayoutService()
            payout = service.approve_vendor_payout(franchise, payout_id)
            
            return {
                'id': payout.id,
                'reference_id': payout.reference_id,
                'status': payout.status,
            }
        
        return self.handle_service_operation(
            operation,
            "Vendor payout approved successfully",
            "Failed to approve vendor payout"
        )


@franchise_vendor_payout_router.register(
    r"partner/franchise/payouts/vendors/<uuid:payout_id>/complete",
    name="franchise-vendor-payout-complete"
)
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Complete Vendor Payout",
    description="""
    Complete vendor payout - deduct from both balances.
    
    Business Rules:
    - BR8.3: Franchise pays Franchise-level Vendors
    - BR8.5: Franchise receives payout BEFORE paying vendors
    - Status must be APPROVED
    - Deducts from BOTH vendor.balance AND franchise.balance
    """,
    responses={200: BaseResponseSerializer}
)
class FranchiseVendorPayoutCompleteView(GenericAPIView, BaseAPIView):
    """Complete vendor payout"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Complete payout"""
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseVendorPayoutService()
            payout = service.complete_vendor_payout(franchise, payout_id)
            
            return {
                'id': payout.id,
                'reference_id': payout.reference_id,
                'status': payout.status,
            }
        
        return self.handle_service_operation(
            operation,
            "Vendor payout completed successfully",
            "Failed to complete vendor payout"
        )


@franchise_vendor_payout_router.register(
    r"partner/franchise/payouts/vendors/<uuid:payout_id>/reject",
    name="franchise-vendor-payout-reject"
)
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Reject Vendor Payout",
    description="""
    Reject vendor payout request.
    
    Business Rules:
    - BR10.2: Only own vendors
    - Status must be PENDING
    """,
    request=RejectPayoutSerializer,
    responses={200: BaseResponseSerializer}
)
class FranchiseVendorPayoutRejectView(GenericAPIView, BaseAPIView):
    """Reject vendor payout"""
    permission_classes = [IsFranchise]
    serializer_class = RejectPayoutSerializer
    
    @log_api_call()
    def patch(self, request: Request, payout_id: str) -> Response:
        """Reject payout"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            franchise = request.user.partner_profile
            service = FranchiseVendorPayoutService()
            payout = service.reject_vendor_payout(
                franchise,
                payout_id,
                serializer.validated_data['reason']
            )
            
            return {
                'id': payout.id,
                'reference_id': payout.reference_id,
                'status': payout.status,
                'rejection_reason': payout.rejection_reason,
            }
        
        return self.handle_service_operation(
            operation,
            "Vendor payout rejected successfully",
            "Failed to reject vendor payout"
        )
