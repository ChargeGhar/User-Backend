"""
Admin withdrawal management - handle withdrawal requests and operations
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers as admin_serializers
from api.admin.services import AdminWithdrawalService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.payments.serializers import WithdrawalSerializer
from api.user.auth.permissions import IsStaffPermission

withdrawal_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@withdrawal_admin_router.register(r"admin/withdrawals/analytics", name="admin-withdrawal-analytics")
@extend_schema(
    tags=["Admin - Withdrawals"],
    summary="Withdrawal Analytics",
    description="Get withdrawal analytics for admin dashboard (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminWithdrawalAnalyticsView(GenericAPIView, BaseAPIView):
    """Get withdrawal analytics"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get withdrawal analytics"""
        def operation():
            service = AdminWithdrawalService()
            analytics = service.get_withdrawal_analytics()
            
            return {
                'analytics': analytics
            }
        
        return self.handle_service_operation(
            operation,
            "Withdrawal analytics retrieved successfully",
            "Failed to get withdrawal analytics"
        )


@withdrawal_admin_router.register(r"admin/withdrawals", name="admin-withdrawals")
@extend_schema(
    tags=["Admin - Withdrawals"],
    summary="All Withdrawals",
    description="Get list of all withdrawal requests with filters (Staff only)",
    parameters=[
        admin_serializers.WithdrawalFiltersSerializer
    ],
    responses={200: BaseResponseSerializer}
)
class AdminWithdrawalsView(GenericAPIView, BaseAPIView):
    """All withdrawals management"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all withdrawals"""
        def operation():
            filter_serializer = admin_serializers.WithdrawalFiltersSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminWithdrawalService()
            result = service.get_withdrawals(filter_serializer.validated_data)
            
            # Serialize the withdrawals in the results
            if result and 'results' in result:
                serialized_withdrawals = WithdrawalSerializer(result['results'], many=True).data
                result['results'] = serialized_withdrawals
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Withdrawals retrieved successfully",
            "Failed to retrieve withdrawals"
        )


@withdrawal_admin_router.register(r"admin/withdrawals/<str:withdrawal_id>/process", name="admin-process-withdrawal")
@extend_schema(
    tags=["Admin - Withdrawals"],
    summary="Process Withdrawal",
    description="Approve or reject withdrawal request (Staff only)",
    request=admin_serializers.ProcessWithdrawalSerializer,
    responses={200: BaseResponseSerializer}
)
class ProcessWithdrawalView(GenericAPIView, BaseAPIView):
    """Process withdrawal (approve/reject)"""
    serializer_class = admin_serializers.ProcessWithdrawalSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def post(self, request: Request, withdrawal_id: str) -> Response:
        """Process withdrawal request"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminWithdrawalService()
            withdrawal = service.process_withdrawal(
                withdrawal_id,
                serializer.validated_data['action'],
                serializer.validated_data.get('admin_notes', ''),
                request.user
            )
            
            return {
                'withdrawal_id': str(withdrawal.id),
                'internal_reference': withdrawal.internal_reference,
                'status': withdrawal.status,
                'message': f'Withdrawal {serializer.validated_data["action"].lower()}ed successfully'
            }
        
        return self.handle_service_operation(
            operation,
            "Withdrawal processed successfully",
            "Failed to process withdrawal"
        )


@withdrawal_admin_router.register(r"admin/withdrawals/<str:withdrawal_id>", name="admin-withdrawal-detail")
@extend_schema(
    tags=["Admin - Withdrawals"],
    summary="Withdrawal Details",
    description="Get detailed withdrawal information (Staff only)",
    responses={200: BaseResponseSerializer}
)
class AdminWithdrawalDetailView(GenericAPIView, BaseAPIView):
    """Get withdrawal details for admin"""
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def get(self, request: Request, withdrawal_id: str) -> Response:
        """Get withdrawal details"""
        def operation():
            service = AdminWithdrawalService()
            withdrawal = service.get_withdrawal_details(withdrawal_id)
            
            serializer = WithdrawalSerializer(withdrawal)
            return {
                'withdrawal': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            "Withdrawal details retrieved successfully",
            "Failed to get withdrawal details"
        )