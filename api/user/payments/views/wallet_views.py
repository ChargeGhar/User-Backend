"""
Wallet operations - topup, balance, verify, and cancel
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.payments import serializers
from api.user.payments.services import PaymentIntentService, WalletService

wallet_router = CustomViewRouter()

logger = logging.getLogger(__name__)

@wallet_router.register(r"payments/wallet/topup-intent", name="payment-topup-intent")
@extend_schema(
    tags=["Payments"],
    summary="Create Top-up Intent",
    description="Create payment intent for wallet top-up",
    responses={200: BaseResponseSerializer}
)
class TopupIntentCreateView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.TopupIntentCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Create Top-up Intent",
        description="Create a payment intent for wallet top-up with selected payment method",
        request=serializers.TopupIntentCreateSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create payment intent for wallet top-up with complete gateway data"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = PaymentIntentService()
            intent = service.create_topup_intent(
                user=request.user,
                amount=serializer.validated_data['amount'],
                payment_method_id=serializer.validated_data['payment_method_id']
            )
            
            # Get gateway data from intent metadata
            gateway_result = intent.intent_metadata.get('gateway_result', {})
            gateway = intent.intent_metadata.get('gateway')
            
            # Return complete payment data
            return {
                'intent_id': intent.intent_id,
                'amount': str(intent.amount),
                'currency': intent.currency,
                'gateway': gateway,
                'gateway_url': intent.gateway_url,
                'redirect_url': gateway_result.get('redirect_url'),
                'redirect_method': gateway_result.get('redirect_method', 'POST'),
                'form_fields': gateway_result.get('form_fields', {}),
                'payment_instructions': gateway_result.get('payment_instructions'),
                'expires_at': intent.expires_at.isoformat(),
                'status': intent.status
            }
        
        return self.handle_service_operation(
            operation,
            "Payment intent created successfully with gateway data",
            "Failed to create payment intent",
            status.HTTP_201_CREATED
        )


@wallet_router.register(r"payments/verify", name="payment-verify")
@extend_schema(
    tags=["Payments"],
    summary="Verify Payment",
    description="Verify and complete payment (supports both authenticated and public access)",
    responses={200: BaseResponseSerializer}
)
class PaymentVerifyView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.VerifyTopupSerializer
    permission_classes = [AllowAny]  # Allow both authenticated and public access
    
    @extend_schema(
        summary="Verify Payment",
        description="Verify payment with gateway and update wallet balance. Supports both web and mobile flows.",
        request=serializers.VerifyTopupSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Verify payment and update wallet"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = PaymentIntentService()
            result = service.verify_topup_payment(
                intent_id=serializer.validated_data['intent_id'],
                callback_data=serializer.validated_data.get('callback_data', {})
            )
            
            # Add user context if authenticated
            if request.user.is_authenticated:
                result['user_authenticated'] = True
                result['username'] = request.user.username
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Payment verified successfully",
            "Failed to verify payment"
        )

# testing part done

@wallet_router.register(r"payments/wallet/balance", name="wallet-balance")
@extend_schema(
    tags=["Payments"],
    summary="Get Wallet Balance",
    description="Get current user wallet balance",
    responses={200: BaseResponseSerializer}
)
class WalletBalanceView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Wallet Balance",
        description="Retrieve current user's wallet balance and recent transactions"
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get user wallet balance"""
        def operation():
            service = WalletService()
            wallet_data = service.get_wallet_balance(request.user)
            return wallet_data
        
        return self.handle_service_operation(
            operation,
            "Wallet balance retrieved successfully",
            "Failed to get wallet balance"
        )



@wallet_router.register(r"payments/cancel/<str:intent_id>", name="payment-cancel")
@extend_schema(
    tags=["Payments"],
    summary="Cancel Payment",
    description="Cancel a pending payment intent",
    responses={200: BaseResponseSerializer}
)
class PaymentCancelView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Cancel Payment Intent",
        description="Cancel a pending payment intent",
        parameters=[
            OpenApiParameter(
                name="intent_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Payment Intent ID",
                required=True
            )
        ],
        request=None,  # Explicitly tell Swagger there is no request body
        responses={200: serializers.PaymentStatusSerializer}
    )
    @log_api_call()
    def post(self, request: Request, intent_id: str) -> Response:
        """Cancel payment intent"""
        def operation():
            service = PaymentIntentService()
            result = service.cancel_payment_intent(intent_id, request.user)
            return result
        
        return self.handle_service_operation(
            operation,
            "Payment intent cancelled successfully",
            "Failed to cancel payment"
        )

