"""
User refund operations - list and request refunds
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.payments import serializers
from api.user.payments.services import RefundService

refund_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@refund_router.register(r"payments/refunds", name="payment-refunds")
@extend_schema(
    tags=["Payments"],
    summary="Refund Requests",
    description="Manage refund requests",
    responses={200: BaseResponseSerializer}
)
class RefundListView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RefundSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get User Refunds",
        description="Retrieve user's refund requests",
        parameters=[
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
        """Get user refund requests"""
        def operation():
            service = RefundService()
            
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            result = service.get_user_refunds(request.user, page, page_size)
            
            serializer = self.get_serializer(result['results'], many=True)
            
            return {
                'refunds': serializer.data,
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
            "Refunds retrieved successfully",
            "Failed to get refunds"
        )
    
    @extend_schema(
        summary="Request Refund",
        description="Request a refund for a transaction",
        request=serializers.RefundRequestSerializer
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Request refund for a transaction"""
        def operation():
            # Validate request data
            serializer = serializers.RefundRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Process refund request
            service = RefundService()
            refund = service.request_refund(
                user=request.user,
                transaction_id=serializer.validated_data['transaction_id'],
                reason=serializer.validated_data['reason']
            )
            
            # Prepare success response
            response_serializer = self.get_serializer(refund)
            return {
                'refund': response_serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            "Refund request submitted successfully",
            "Failed to process refund request",
            status.HTTP_201_CREATED
        )

