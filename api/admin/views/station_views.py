"""
Station operations and management - control station maintenance, commands and configurations
"""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from api.admin import serializers
from api.admin.services import AdminStationService
from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission

station_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@station_router.register(r"admin/stations", name="admin-stations")
class AdminStationListView(GenericAPIView, BaseAPIView):
    """Station list and creation management"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Stations"],
        summary="List All Stations",
        description="Get paginated list of all stations with filters and statistics (Staff only)",
        parameters=[
            serializers.AdminStationListSerializer
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get stations list with statistics"""
        def operation():
            filter_serializer = serializers.AdminStationListSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)
            
            service = AdminStationService()
            result = service.get_stations_list(filter_serializer.validated_data)
            
            # Serialize the stations in the results
            if result and 'results' in result:
                serialized_stations = serializers.AdminStationSerializer(
                    result['results'], 
                    many=True
                ).data
                result['results'] = serialized_stations
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Stations retrieved successfully",
            "Failed to retrieve stations"
        )
    
    @extend_schema(
        tags=["Admin - Stations"],
        summary="Create New Station",
        description="Create a new charging station with slots, amenities, and media (Staff only)",
        request=serializers.CreateStationSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new station with amenities, media, and powerbank assignments"""
        def operation():
            serializer = serializers.CreateStationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            validated_data = serializer.validated_data
            
            # Extract amenities, media, and powerbank assignments for separate processing
            amenity_ids = validated_data.pop('amenity_ids', [])
            media_uploads = validated_data.pop('media_uploads', [])
            powerbank_assignments = validated_data.pop('powerbank_assignments', [])
            
            # Use service to create station
            service = AdminStationService()
            station = service.create_station_with_amenities_and_media(
                station_data=validated_data,
                amenity_ids=amenity_ids,
                media_uploads=media_uploads,
                powerbank_assignments=powerbank_assignments,
                admin_user=request.user,
                request=request
            )
            
            return serializers.AdminStationDetailSerializer(station).data
        
        return self.handle_service_operation(
            operation,
            "Station created successfully",
            "Failed to create station"
        )


@station_router.register(r"admin/stations/<str:station_sn>", name="admin-station-detail")
class AdminStationDetailView(GenericAPIView, BaseAPIView):
    """Station detail, update and delete operations"""
    permission_classes = [IsStaffPermission]

    @extend_schema(
        tags=["Admin - Stations"],
        summary="Get Station Details",
        description="Get detailed station information including slots, powerbanks, issues, and statistics (Staff only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request, station_sn: str) -> Response:
        """Get station detail"""
        def operation():
            service = AdminStationService()
            station = service.get_station_detail(station_sn)
            
            return serializers.AdminStationDetailSerializer(station).data
        
        return self.handle_service_operation(
            operation,
            "Station details retrieved successfully",
            "Failed to retrieve station details"
        )
    
    @extend_schema(
        tags=["Admin - Stations"],
        summary="Update Station",
        description="Update station details including amenities, media, and powerbank assignments (Staff only)",
        request=serializers.UpdateStationSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def patch(self, request: Request, station_sn: str) -> Response:
        """Update station details with amenities, media, and powerbank assignments"""
        def operation():
            serializer = serializers.UpdateStationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            validated_data = serializer.validated_data
            
            # Extract amenities, media, and powerbank assignments for separate processing
            amenity_ids = validated_data.pop('amenity_ids', None)
            media_uploads = validated_data.pop('media_uploads', None)
            powerbank_assignments = validated_data.pop('powerbank_assignments', None)
            
            service = AdminStationService()
            station = service.update_station_with_amenities_and_media(
                station_sn=station_sn,
                station_data=validated_data,
                amenity_ids=amenity_ids,
                media_uploads=media_uploads,
                powerbank_assignments=powerbank_assignments,
                admin_user=request.user,
                request=request
            )
            
            return serializers.AdminStationDetailSerializer(station).data
        
        return self.handle_service_operation(
            operation,
            "Station updated successfully",
            "Failed to update station"
        )
    
    @extend_schema(
        tags=["Admin - Stations"],
        summary="Delete Station",
        description="Soft delete station (set inactive) - only if no active rentals (Staff only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def delete(self, request: Request, station_sn: str) -> Response:
        """Soft delete station"""
        def operation():
            service = AdminStationService()
            result = service.delete_station(
                station_sn=station_sn,
                admin_user=request.user,
                request=request
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Station deleted successfully",
            "Failed to delete station"
        )


@station_router.register(r"admin/stations/<str:station_sn>/maintenance", name="admin-station-maintenance")
@extend_schema(
    tags=["Admin - Stations"],
    summary="Toggle Maintenance Mode",
    description="Enable/disable station maintenance mode (Staff only)",
    request=serializers.ToggleMaintenanceSerializer,
    responses={200: BaseResponseSerializer}
)
class ToggleMaintenanceView(GenericAPIView, BaseAPIView):
    """Toggle station maintenance mode"""
    serializer_class = serializers.ToggleMaintenanceSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def post(self, request: Request, station_sn: str) -> Response:
        """Toggle maintenance mode"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminStationService()
            station = service.toggle_maintenance_mode(
                station_sn,
                serializer.validated_data['is_maintenance'],
                serializer.validated_data['reason'],
                request.user
            )
            
            return {
                'station_id': str(station.id),
                'station_name': station.station_name,
                'is_maintenance': station.is_maintenance,
                'message': f'Maintenance mode {"enabled" if station.is_maintenance else "disabled"}'
            }
        
        return self.handle_service_operation(
            operation,
            "Maintenance mode toggled successfully",
            "Failed to toggle maintenance mode"
        )

@station_router.register(r"admin/stations/<str:station_sn>/command", name="admin-station-command")
@extend_schema(
    tags=["Admin - Stations"],
    summary="Send Remote Command",
    description="Send remote command to station (Staff only)",
    request=serializers.RemoteCommandSerializer,
    responses={200: BaseResponseSerializer}
)
class SendRemoteCommandView(GenericAPIView, BaseAPIView):
    """Send remote command to station"""
    serializer_class = serializers.RemoteCommandSerializer
    permission_classes = [IsStaffPermission]

    @log_api_call()
    def post(self, request: Request, station_sn: str) -> Response:
        """Send remote command"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AdminStationService()
            result = service.send_remote_command(
                station_sn,
                serializer.validated_data['command'],
                serializer.validated_data.get('parameters', {}),
                request.user
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            "Command sent successfully",
            "Failed to send command"
        )