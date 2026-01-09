"""
Withdrawal operations - request, list, and cancel withdrawals
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.payments import serializers
from api.user.payments.services import WithdrawalService

withdrawal_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@withdrawal_router.register(r"payments/withdrawals/request", name="withdrawal-request")
@extend_schema(
    tags=["Payments"],
    summary="Request Withdrawal",
    description="Create a new withdrawal request",
    responses={201: BaseResponseSerializer}
)
class WithdrawalRequestView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Request Withdrawal",
        description="""Create a withdrawal request. Choose withdrawal method and provide required details:
        
        **eSewa/Khalti**: Only phone number required (98XXXXXXXX format)
        **Bank Transfer**: Bank name, account number, and account holder name required
        
        The system will validate account details based on the selected withdrawal method.""",
        request=serializers.WithdrawalRequestSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create withdrawal request"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = WithdrawalService()
            withdrawal = service.request_withdrawal(
                user=request.user,
                amount=serializer.validated_data['amount'],
                withdrawal_method=serializer.validated_data['withdrawal_method'],
                account_details=serializer.get_account_details()
            )
            
            # Return withdrawal details
            response_serializer = serializers.WithdrawalSerializer(withdrawal)
            return {
                'withdrawal': response_serializer.data,
                'message': 'Withdrawal request submitted successfully'
            }
        
        return self.handle_service_operation(
            operation,
            "Withdrawal request created successfully",
            "Failed to create withdrawal request",
            status.HTTP_201_CREATED
        )


@withdrawal_router.register(r"payments/withdrawals", name="withdrawal-list")
@extend_schema(
    tags=["Payments"],
    summary="User Withdrawals",
    description="Get user withdrawal history with filtering",
    responses={200: BaseResponseSerializer}
)
class WithdrawalListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.WithdrawalListSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Withdrawal History",
        description="Retrieve user's withdrawal history with optional filtering",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by status (REQUESTED, APPROVED, COMPLETED, REJECTED, CANCELLED)",
                required=False
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter withdrawals from this date",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter withdrawals until this date",
                required=False
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination",
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of items per page (default: 20)",
                required=False
            )
        ]
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user withdrawal history"""
        def operation():
            service = WithdrawalService()
            
            # Get pagination parameters
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Get user withdrawals
            result = service.get_user_withdrawals(request.user, page, page_size)
            
            # Serialize the withdrawals
            serializer = self.get_serializer(result['results'], many=True)
            
            return {
                'withdrawals': serializer.data,
                'pagination': {
                    'count': result['pagination']['total_count'],
                    'page': result['pagination']['current_page'],
                    'page_size': result['pagination']['page_size'],
                    'total_pages': result['pagination']['total_pages'],
                    'has_next': result['pagination']['has_next'],
                    'has_previous': result['pagination']['has_previous']
                }
            }
        
        return self.handle_service_operation(
            operation,
            "Withdrawals retrieved successfully",
            "Failed to get withdrawals"
        )


@withdrawal_router.register(r"payments/withdrawals/<str:withdrawal_id>/cancel", name="withdrawal-cancel")
@extend_schema(
    tags=["Payments"],
    summary="Cancel Withdrawal",
    description="Cancel a pending withdrawal request",
    responses={200: BaseResponseSerializer}
)
class WithdrawalCancelView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.WithdrawalCancelSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Cancel Withdrawal Request",
        description="Cancel a pending withdrawal request",
        parameters=[
            OpenApiParameter(
                name="withdrawal_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Withdrawal Request ID",
                required=True
            )
        ],
        request=serializers.WithdrawalCancelSerializer,
        responses={200: serializers.WithdrawalStatusSerializer}
    )
    @log_api_call()
    def post(self, request: Request, withdrawal_id: str) -> Response:
        """Cancel withdrawal request"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = WithdrawalService()
            withdrawal = service.cancel_withdrawal(withdrawal_id, request.user)
            
            return {
                'withdrawal_id': str(withdrawal.id),
                'internal_reference': withdrawal.internal_reference,
                'status': withdrawal.status,
                'message': 'Withdrawal request cancelled successfully'
            }
        
        return self.handle_service_operation(
            operation,
            "Withdrawal cancelled successfully",
            "Failed to cancel withdrawal"
        )


@withdrawal_router.register(r"payments/withdrawals/<str:withdrawal_id>", name="withdrawal-detail")
@extend_schema(
    tags=["Payments"],
    summary="Withdrawal Details",
    description="Get detailed information about a specific withdrawal",
    responses={200: BaseResponseSerializer}
)
class WithdrawalDetailView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.WithdrawalSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Withdrawal Details",
        description="Retrieve detailed information about a specific withdrawal request",
        parameters=[
            OpenApiParameter(
                name="withdrawal_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Withdrawal Request ID",
                required=True
            )
        ]
    )
    @log_api_call()
    def get(self, request: Request, withdrawal_id: str) -> Response:
        """Get withdrawal details"""
        def operation():
            service = WithdrawalService()
            
            # Get withdrawal by ID and verify ownership
            try:
                withdrawal = service.get_withdrawal_by_id(withdrawal_id)
                
                # Verify user owns this withdrawal
                if withdrawal.user != request.user:
                    from api.common.services.base import ServiceException
                    raise ServiceException(
                        detail="You are not authorized to view this withdrawal",
                        code="unauthorized_withdrawal"
                    )
                
                serializer = self.get_serializer(withdrawal)
                return {
                    'withdrawal': serializer.data
                }
                
            except Exception as e:
                if hasattr(e, 'code') and e.code == 'withdrawal_not_found':
                    raise e
                service.handle_service_error(e, "Failed to get withdrawal details")
        
        return self.handle_service_operation(
            operation,
            "Withdrawal details retrieved successfully",
            "Failed to get withdrawal details"
        )