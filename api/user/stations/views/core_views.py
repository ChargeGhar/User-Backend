"""
Core station operations - list, nearby, and detail views
"""
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.stations import serializers
from api.user.stations.models import Station
from api.user.stations.services import StationService
from api.common.services.base import ServiceException

core_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@core_router.register("stations", name="stations-list")
@extend_schema(
    tags=["Stations"],
    summary="List Stations",
    description="Get list of active charging stations with basic info and availability",
    parameters=[
        OpenApiParameter("lat", OpenApiTypes.FLOAT, description="User latitude for distance calculation"),
        OpenApiParameter("lng", OpenApiTypes.FLOAT, description="User longitude for distance calculation"),
        OpenApiParameter("search", OpenApiTypes.STR, description="Search by station name or address"),
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page (max 50)"),
    ],
    responses={200: serializers.StationListResponseSerializer}
)
class StationListView(GenericAPIView, BaseAPIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.StationListSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get paginated list of active stations"""
        def operation():
            # Build filters from query params
            filters = {
                'page': int(request.query_params.get('page', 1)),
                'page_size': min(int(request.query_params.get('page_size', 20)), 50),
            }
            
            # Add optional filters
            if request.query_params.get('search'):
                filters['search'] = request.query_params.get('search')
            
            if request.query_params.get('lat') and request.query_params.get('lng'):
                try:
                    filters['lat'] = float(request.query_params.get('lat'))
                    filters['lng'] = float(request.query_params.get('lng'))
                    filters['radius'] = 10.0  # Fixed 10km radius for list
                except (ValueError, TypeError):
                    raise ServiceException(
                        detail="Invalid coordinates",
                        code="invalid_coordinates"
                    )
            
            # Get stations from service
            service = StationService()
            result = service.get_stations_list(filters, request.user)
            
            # Serialize results
            serializer = self.get_serializer(
                result['results'], 
                many=True, 
                context={'request': request}
            )
            
            return {
                'count': result['pagination']['total_count'],
                'next': result['pagination']['has_next'],
                'previous': result['pagination']['has_previous'],
                'results': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Stations retrieved successfully",
            error_message="Failed to retrieve stations"
        )

@core_router.register("stations/nearby", name="stations-nearby")
@extend_schema(
    tags=["Stations"],
    summary="Nearby Stations",
    description="Get stations within specified radius for map display",
    parameters=[
        OpenApiParameter("lat", OpenApiTypes.FLOAT, description="Latitude", required=True),
        OpenApiParameter("lng", OpenApiTypes.FLOAT, description="Longitude", required=True),
        OpenApiParameter("radius", OpenApiTypes.FLOAT, description="Search radius in km (default: 5, max: 20)"),
    ],
    responses={200: serializers.StationListResponseSerializer}
)
class NearbyStationsView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.NearbyStationsSerializer
    permission_classes = [AllowAny]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get nearby stations for map display"""
        def operation():
            # Validate input
            input_serializer = self.get_serializer(data={
                'lat': request.query_params.get('lat'),
                'lng': request.query_params.get('lng'),
                'radius': request.query_params.get('radius', 5.0)
            })
            input_serializer.is_valid(raise_exception=True)
            
            # Get nearby stations
            station_service = StationService()
            nearby_stations = station_service.get_nearby_stations(
                lat=input_serializer.validated_data['lat'],
                lng=input_serializer.validated_data['lng'],
                radius=min(input_serializer.validated_data['radius'], 20.0)  # Max 20km
            )
            
            # Get full station objects
            station_ids = [station['id'] for station in nearby_stations]
            stations_qs = Station.objects.filter(id__in=station_ids).prefetch_related(
                'slots',
                'media__media_upload'
            )

            # Preserve nearest-to-farthest order from the service
            distance_map = {s['id']: s['distance'] for s in nearby_stations}
            stations = sorted(stations_qs, key=lambda s: distance_map[s.id])

            # Serialize results
            serializer = serializers.StationListSerializer(
                stations,
                many=True,
                context={'request': request}
            )
            
            return {
                'count': len(serializer.data),
                'results': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Nearby stations retrieved successfully",
            error_message="Failed to retrieve nearby stations"
        )

@core_router.register("stations/<str:serial_number>", name="station-detail")
class StationDetailView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.StationDetailSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        operation_id="stations_detail_retrieve",
        tags=["Stations"],
        summary="Get Station Detail",
        description="Get detailed station information including slots, amenities, and real-time status",
        parameters=[
            OpenApiParameter("serial_number", OpenApiTypes.STR, OpenApiParameter.PATH, description="Station serial number", required=True),
            OpenApiParameter("lat", OpenApiTypes.FLOAT, description="User latitude for distance calculation"),
            OpenApiParameter("lng", OpenApiTypes.FLOAT, description="User longitude for distance calculation"),
        ],
        responses={200: serializers.StationDetailResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, serial_number: str) -> Response:
        """Get detailed station information"""
        def operation():
            station_service = StationService()
            station = station_service.get_station_detail(serial_number, request.user)
            
            serializer = self.get_serializer(station, context={'request': request})
            return serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Station details retrieved successfully",
            error_message="Failed to retrieve station details"
        )