"""
User Advertisement Views
=======================
Views for user ad operations: create, list, pay
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import rate_limit, log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.advertisements import serializers
from api.user.advertisements.services import AdRequestService, AdPaymentService

user_ads_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@user_ads_router.register(r"ads/request", name="ad-request-create")
@extend_schema(
    tags=["Advertisements"],
    summary="Submit Ad Request",
    description="Submit a new advertisement request with media"
)
class AdRequestCreateView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdRequestCreateSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Create New Ad Request",
        description="Submit advertisement request with advertiser details and media. "
                    "Media must be IMAGE or VIDEO type.",
        request=serializers.AdRequestCreateSerializer,
        responses={
            201: serializers.AdRequestDetailSerializer,
            400: BaseResponseSerializer
        }
    )
    @rate_limit(max_requests=5, window_seconds=3600)  # Max 5 ad submissions per hour
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Submit new ad request"""
        def operation():
            serializer = self.get_serializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            
            service = AdRequestService()
            ad_request = service.create_ad_request(
                user=request.user,
                validated_data=serializer.validated_data
            )
            
            response_serializer = serializers.AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad request submitted successfully",
            error_message="Failed to submit ad request",
            success_status=status.HTTP_201_CREATED
        )


@user_ads_router.register(r"ads/my-ads", name="ad-request-list")
@extend_schema(
    tags=["Advertisements"],
    summary="List My Ads",
    description="Get list of user's advertisement requests"
)
class AdRequestListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdRequestListSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get My Ad Requests",
        description="Returns list of user's ad requests with optional status filter",
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by status (SUBMITTED, UNDER_REVIEW, PENDING_PAYMENT, PAID, SCHEDULED, RUNNING, PAUSED, COMPLETED, REJECTED, CANCELLED)',
                required=False
            )
        ],
        responses={
            200: serializers.AdRequestListSerializer(many=True)
        }
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """List user's ad requests"""
        def operation():
            service = AdRequestService()
            
            # Get filters from query params
            filters = {}
            if request.query_params.get('status'):
                filters['status'] = request.query_params.get('status')
            
            ad_requests = service.get_user_ad_requests(
                user=request.user,
                filters=filters
            )
            
            serializer = self.get_serializer(ad_requests, many=True)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Ad requests retrieved successfully",
            error_message="Failed to retrieve ad requests"
        )


@user_ads_router.register(r"ads/<str:ad_id>/pay", name="ad-payment")
@extend_schema(
    tags=["Advertisements"],
    summary="Pay for Ad",
    description="Process payment for approved advertisement"
)
class AdPaymentView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.AdPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Pay for Advertisement",
        description="Process payment for approved ad using wallet balance. "
                    "Ad must be in PENDING_PAYMENT status. "
                    "Wallet balance must be sufficient.",
        request=serializers.AdPaymentSerializer,
        responses={
            200: serializers.AdRequestDetailSerializer,
            400: BaseResponseSerializer,
            402: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request, ad_id: str) -> Response:
        """Process ad payment"""
        def operation():
            service = AdPaymentService()
            ad_request = service.process_ad_payment(
                ad_request_id=ad_id,
                user=request.user
            )
            
            response_serializer = serializers.AdRequestDetailSerializer(ad_request)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Payment processed successfully",
            error_message="Failed to process payment"
        )
