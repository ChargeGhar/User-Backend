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
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.rentals import serializers
from api.user.rentals.models import RentalPackage
from api.user.stations.models import Station
from api.user.promotions.services import DiscountService

package_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@package_router.register(r"rentals/packages", name="rental-packages")
@extend_schema(
    tags=["Rentals"],
    summary="Rental Packages",
    description="Get available rental packages with optional station-specific discounts",
    responses={200: BaseResponseSerializer}
)
class RentalPackageView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalPackageListSerializer
    
    @extend_schema(
        summary="Get Rental Packages",
        description="Get list of available rental packages with pagination. Include station_sn to see station-specific discounts.",
        responses={200: BaseResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="station_sn",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Station serial number to check for discounts",
                required=False
            ),
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
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get rental packages with optional discounts"""
        def operation():
            station_sn = request.query_params.get('station_sn')
            packages = RentalPackage.objects.filter(is_active=True).order_by('duration_minutes')
            
            # Get discounts if station_sn provided
            discounts = {}
            if station_sn:
                try:
                    station = Station.objects.get(serial_number=station_sn)
                    discounts = DiscountService.get_active_discounts_for_station(
                        station.id, request.user
                    )
                except Station.DoesNotExist:
                    logger.warning(f"Station not found: {station_sn}")
            
            # Manually paginate and serialize with custom context
            from api.common.utils.helpers import paginate_queryset
            pagination_params = self.get_pagination_params(request)
            result = paginate_queryset(
                packages, 
                page=pagination_params['page'],
                page_size=pagination_params['page_size']
            )
            
            # Serialize with custom context
            serializer = serializers.RentalPackageListSerializer(
                result['results'], 
                many=True, 
                context={'request': request, 'discounts': discounts}
            )
            result['results'] = serializer.data
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Packages retrieved successfully",
            error_message="Failed to get packages"
        )

