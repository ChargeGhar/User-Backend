"""
Rental history and user statistics
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call, cached_response
from api.common.serializers import BaseResponseSerializer
from api.user.rentals import serializers
from api.user.rentals.services import RentalService


history_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@history_router.register(r"rentals/history", name="rental-history")
@extend_schema(
    tags=["Rentals"],
    summary="Rental History",
    description="Get user's rental history with filtering and pagination",
    responses={200: BaseResponseSerializer}
)
class RentalHistoryView(GenericAPIView, BaseAPIView):
    # Return each history item in the same shape as the active rental response
    serializer_class = serializers.RentalDetailSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Rental History",
        description="Retrieve user's rental history with optional filtering",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by rental status",
                required=False
            ),
            OpenApiParameter(
                name="payment_status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by payment status",
                required=False
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter rentals from this date",
                required=False
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter rentals until this date",
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
                description="Number of items per page",
                required=False
            )
        ]
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get rental history"""
        def operation():
            # Validate query parameters
            filter_serializer = serializers.RentalHistoryFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = RentalService()
            result = service.get_user_rentals(request.user, filter_serializer.validated_data)
            
            # Serialize the rentals
            serializer = self.get_serializer(result['results'], many=True)
            
            return {
                'rentals': serializer.data,
                'pagination': result['pagination']
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Rental history retrieved successfully",
            error_message="Failed to get rental history"
        )



@history_router.register(r"rentals/stats", name="rental-stats")
@extend_schema(
    tags=["Rentals"],
    summary="Rental Statistics",
    description="Get user rental statistics",
    responses={200: BaseResponseSerializer}
)
class RentalStatsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalStatsSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get Rental Statistics",
        description="Get comprehensive rental statistics for the user",
        responses={200: BaseResponseSerializer}
    )
    @cached_response(timeout=300)  # Cache for 5 minutes - stats update periodically
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get rental statistics"""
        def operation():
            service = RentalService()
            stats = service.get_rental_stats(request.user)
            
            serializer = self.get_serializer(stats)
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Statistics retrieved successfully",
            error_message="Failed to get rental stats"
        )