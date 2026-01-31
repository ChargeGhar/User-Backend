"""
Franchise Payout View

GET /api/partner/franchise/payouts/ - Own payout history
POST /api/partner/franchise/payouts/request/ - Request payout from ChargeGhar
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
from api.partners.franchise.services import FranchisePayoutService

franchise_payout_router = CustomViewRouter()


class PayoutRequestSerializer(serializers.Serializer):
    """Payout request input"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    bank_name = serializers.CharField(max_length=100)
    account_number = serializers.CharField(max_length=50)
    account_holder_name = serializers.CharField(max_length=100)


@franchise_payout_router.register(r"partner/franchise/payouts", name="franchise-payouts")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Manage Own Payouts",
    description="""
    List own payout requests from ChargeGhar.
    
    Business Rules:
    - BR8.1: ChargeGhar pays Franchises
    """,
    parameters=[
        OpenApiParameter('status', type=str, description='Filter by status'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class FranchisePayoutsView(GenericAPIView, BaseAPIView):
    """Franchise own payouts"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """List own payouts"""
        def operation():
            franchise = request.user.partner_profile
            filters = {
                'status': request.query_params.get('status'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = FranchisePayoutService()
            return service.get_payouts_list(franchise, filters)
        
        return self.handle_service_operation(
            operation,
            "Payouts retrieved successfully",
            "Failed to retrieve payouts"
        )


@franchise_payout_router.register(r"partner/franchise/payouts/request", name="franchise-payout-request")
@extend_schema(
    tags=["Partner - Franchise"],
    summary="Request Payout",
    description="""
    Request payout from ChargeGhar.
    
    Business Rules:
    - BR8.1: ChargeGhar pays Franchises
    - Amount must be <= balance
    - No pending payout exists
    """,
    request=PayoutRequestSerializer,
    responses={200: BaseResponseSerializer}
)
class FranchisePayoutRequestView(GenericAPIView, BaseAPIView):
    """Request payout"""
    permission_classes = [IsFranchise]
    serializer_class = PayoutRequestSerializer
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Request payout"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            franchise = request.user.partner_profile
            service = FranchisePayoutService()
            payout = service.request_payout(
                franchise=franchise,
                amount=serializer.validated_data['amount'],
                bank_name=serializer.validated_data['bank_name'],
                account_number=serializer.validated_data['account_number'],
                account_holder_name=serializer.validated_data['account_holder_name']
            )
            
            return {
                'id': payout.id,
                'reference_id': payout.reference_id,
                'amount': payout.amount,
                'status': payout.status,
            }
        
        return self.handle_service_operation(
            operation,
            "Payout requested successfully",
            "Failed to request payout"
        )
