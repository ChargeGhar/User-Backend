"""
Core payment functionality - transactions, packages, and methods
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.payments import serializers
from api.user.payments.models import PaymentMethod
from api.user.rentals.models import RentalPackage
from api.user.payments.services import TransactionService, PaymentCalculationService

core_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@core_router.register(r"payments/transactions", name="payment-transactions")
@extend_schema(
    tags=["Payments"],
    summary="User Transactions",
    description="Get user transaction history with filtering",
    responses={200: BaseResponseSerializer}
)
class TransactionListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.TransactionListSerializer  # Use List serializer for MVP
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Transaction History",
        description="Retrieve user's transaction history with optional filtering",
        parameters=[
            OpenApiParameter(
                name="transaction_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by transaction type (TOPUP, RENTAL, REFUND, etc.)",
                required=False
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by status (PENDING, SUCCESS, FAILED, REFUNDED)",
                required=False
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter transactions from this date",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter transactions until this date",
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
        """Get user transaction history"""
        def operation():
            service = TransactionService()
            
            # Build filters from query parameters
            filters = {}
            if request.query_params.get('transaction_type'):
                filters['transaction_type'] = request.query_params.get('transaction_type')
            
            if request.query_params.get('status'):
                filters['status'] = request.query_params.get('status')
            
            # Use FilterMixin for date filtering
            queryset = service.get_user_transactions_queryset(request.user)
            queryset = self.apply_date_filters(queryset, request)
            queryset = self.apply_status_filter(queryset, request)
            
            # Use PaginationMixin for pagination
            result = self.paginate_response(queryset, request, self.serializer_class)
            return result
        
        return self.handle_service_operation(
            operation,
            "Transactions retrieved successfully",
            "Failed to get transactions"
        )



@core_router.register(r"payments/packages", name="payment-packages")
@extend_schema(
    tags=["Payments"],
    summary="Rental Packages",
    description="Get available rental packages",
    responses={200: BaseResponseSerializer}
)
class RentalPackageListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalPackageSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get Rental Packages",
        description="Retrieve all active rental packages with pricing"
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get available rental packages"""
        def operation():
            packages = RentalPackage.objects.filter(is_active=True).order_by('duration_minutes')
            serializer = self.get_serializer(packages, many=True)
            
            return {
                'packages': serializer.data,
                'count': packages.count()
            }
        
        return self.handle_service_operation(
            operation,
            "Packages retrieved successfully",
            "Failed to get packages"
        )

# done the testing for fetching the payment method

from api.user.payments.repositories import PaymentMethodRepository

@core_router.register(r"payments/methods", name="payment-methods")
@extend_schema(
    tags=["Payments"],
    summary="Payment Methods",
    description="Get available payment gateways",
    responses={200: BaseResponseSerializer}
)
class PaymentMethodListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.PaymentMethodListSerializer  # Use List serializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get Payment Methods",
        description="Retrieve all active payment gateways and their configurations"
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get available payment methods"""
        def operation():
            repository = PaymentMethodRepository()
            methods = repository.get_active_methods()
            serializer = self.get_serializer(methods, many=True)
            return {
                'payment_methods': serializer.data,
                'count': methods.count()
            }
        
        return self.handle_service_operation(
            operation,
            "Payment methods retrieved successfully",
            "Failed to get payment methods"
        )

# done the testing part


@core_router.register(r"payments/calculate-options", name="payment-calculate-options")
@extend_schema(
    tags=["Payments"],
    summary="Calculate Rental Payment Options",
    description="Calculate payment options for rental scenarios (pre-payment and settling dues)",
    responses={200: BaseResponseSerializer}
)
class CalculatePaymentOptionsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.CalculatePaymentOptionsSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Calculate Rental Payment Options",
        description="Calculate available payment options (wallet, points, combination) for rental scenarios only",
        request=serializers.CalculatePaymentOptionsSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Calculate payment options for rental scenarios"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            service = PaymentCalculationService()
            options = service.calculate_payment_options(
                user=request.user,
                scenario=serializer.validated_data['scenario'],
                package_id=serializer.validated_data.get('package_id'),
                rental_id=serializer.validated_data.get('rental_id'),
                amount=serializer.validated_data.get('amount'),
                payment_mode=serializer.validated_data.get('payment_mode'),
                wallet_amount=serializer.validated_data.get('wallet_amount'),
                points_to_use=serializer.validated_data.get('points_to_use')
            )

            return options
        
        return self.handle_service_operation(
            operation,
            "Payment options calculated successfully",
            "Failed to calculate payment options"
        )
