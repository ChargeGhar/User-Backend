"""
Rental packages and related information
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call, cached_response
from api.common.serializers import BaseResponseSerializer
from api.user.rentals import serializers
from api.user.rentals.models import RentalPackage

package_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@package_router.register(r"rentals/packages", name="rental-packages")
@extend_schema(
    tags=["Rentals"],
    summary="Rental Packages",
    description="Get available rental packages",
    responses={200: BaseResponseSerializer}
)
class RentalPackageView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalPackageListSerializer
    
    @extend_schema(
        summary="Get Rental Packages",
        description="Get list of available rental packages with pagination",
        responses={200: BaseResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number",
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Items per page",
                required=False
            )
        ]
    )
    @cached_response(timeout=3600)  # Cache for 1 hour - packages don't change frequently
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get rental packages"""
        def operation():
            packages = RentalPackage.objects.filter(is_active=True).order_by('duration_minutes')
            result = self.paginate_response(
                packages,
                request,
                serializer_class=serializers.RentalPackageListSerializer
            )
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Packages retrieved successfully",
            error_message="Failed to get packages"
        )

