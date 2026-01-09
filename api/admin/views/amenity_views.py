"""
Admin station amenity management views
"""
from __future__ import annotations
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer, PaginatedResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.admin.services.admin_amenity_service import AdminAmenityService
from api.admin.serializers import (
    AdminStationAmenitySerializer,
    CreateStationAmenitySerializer,
    UpdateStationAmenitySerializer
)

amenity_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@amenity_admin_router.register(r"admin/amenities", name="admin-amenities")
@extend_schema(
    tags=["Admin - Amenity"],
    summary="Admin Station Amenities",
    description="List all station amenities or create new amenity",
    parameters=[
        OpenApiParameter("is_active", OpenApiTypes.BOOL, description="Filter by active status"),
        OpenApiParameter("search", OpenApiTypes.STR, description="Search by name or description"),
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page"),
    ],
    responses={200: PaginatedResponseSerializer}
)
class AdminAmenityListView(GenericAPIView, BaseAPIView):
    """Admin view for station amenities list and creation"""
    serializer_class = AdminStationAmenitySerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all station amenities with filters"""
        def operation():
            # Parse filters
            filters = {
                'page': int(request.query_params.get('page', 1)),
                'page_size': int(request.query_params.get('page_size', 20)),
                'search': request.query_params.get('search'),
            }
            
            # Handle is_active filter
            is_active = request.query_params.get('is_active')
            if is_active is not None:
                filters['is_active'] = is_active.lower() == 'true'
            
            # Get amenities
            service = AdminAmenityService()
            amenities_data = service.get_amenities_list(filters)
            
            # Serialize amenities
            serializer = AdminStationAmenitySerializer(
                amenities_data['results'], many=True
            )
            
            return {
                'results': serializer.data,
                'pagination': amenities_data['pagination']
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Amenities retrieved successfully",
            error_message="Failed to retrieve amenities"
        )
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new station amenity"""
        def operation():
            # Validate request data
            serializer = CreateStationAmenitySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create amenity
            service = AdminAmenityService()
            amenity = service.create_amenity(
                amenity_data=serializer.validated_data,
                admin_user=request.user,
                request=request
            )
            
            # Return created amenity
            response_serializer = AdminStationAmenitySerializer(amenity)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Amenity created successfully",
            error_message="Failed to create amenity"
        )


@amenity_admin_router.register(r"admin/amenities/<str:amenity_id>", name="admin-amenity-detail")
@extend_schema(
    tags=["Admin - Amenity"],
    summary="Admin Station Amenity Detail",
    description="Get, update, or delete specific station amenity",
    parameters=[
        OpenApiParameter(
            name="amenity_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Amenity ID (UUID)",
            required=True
        )
    ],
    responses={200: BaseResponseSerializer}
)
class AdminAmenityDetailView(GenericAPIView, BaseAPIView):
    """Admin view for specific station amenity"""
    serializer_class = AdminStationAmenitySerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request, amenity_id: str) -> Response:
        """Get specific amenity details"""
        def operation():
            service = AdminAmenityService()
            amenity = service.get_amenity_detail(amenity_id)
            
            serializer = AdminStationAmenitySerializer(amenity)
            
            # Add usage count
            data = serializer.data
            data['stations_count'] = amenity.stations_count if hasattr(amenity, 'stations_count') else 0
            
            return data
        
        return self.handle_service_operation(
            operation,
            success_message="Amenity details retrieved successfully",
            error_message="Failed to retrieve amenity details"
        )
    
    @log_api_call()
    def patch(self, request: Request, amenity_id: str) -> Response:
        """Update station amenity"""
        def operation():
            # Validate request data
            serializer = UpdateStationAmenitySerializer(
                data=request.data,
                context={'amenity_id': amenity_id}
            )
            serializer.is_valid(raise_exception=True)
            
            # Update amenity
            service = AdminAmenityService()
            amenity = service.update_amenity(
                amenity_id=amenity_id,
                update_data=serializer.validated_data,
                admin_user=request.user,
                request=request
            )
            
            # Return updated amenity
            response_serializer = AdminStationAmenitySerializer(amenity)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Amenity updated successfully",
            error_message="Failed to update amenity"
        )
    
    @log_api_call()
    def delete(self, request: Request, amenity_id: str) -> Response:
        """Delete station amenity"""
        def operation():
            service = AdminAmenityService()
            result = service.delete_amenity(
                amenity_id=amenity_id,
                admin_user=request.user,
                request=request
            )
            
            return result
        
        return self.handle_service_operation(
            operation,
            success_message="Amenity deleted successfully",
            error_message="Failed to delete amenity"
        )
