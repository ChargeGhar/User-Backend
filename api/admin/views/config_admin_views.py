"""
Admin configuration management views
"""
from __future__ import annotations
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.system.services import AppConfigService
from api.user.system.serializers import (
    AppConfigAdminSerializer,
    CreateAppConfigSerializer,
    UpdateAppConfigSerializer
)

config_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@config_admin_router.register(r"admin/config", name="admin-config")
class AdminConfigView(GenericAPIView, BaseAPIView):
    """Admin configuration management with CRUD operations"""
    permission_classes = [IsStaffPermission]
    serializer_class = AppConfigAdminSerializer
    
    @extend_schema(
        tags=["Admin - Config"],
        summary="Get All Configurations",
        description="Get all app configurations including sensitive ones (Admin only)",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all configurations (including sensitive ones)"""
        def operation():
            service = AppConfigService()
            all_configs = service.get_all_configs()  # Admin can see all configs
            
            return {
                'configs': all_configs,
                'total_count': len(all_configs)
            }
        
        return self.handle_service_operation(
            operation,
            success_message="All configurations retrieved successfully",
            error_message="Failed to retrieve configurations",
            operation_context="Admin config retrieval"
        )
    
    @extend_schema(
        tags=["Admin - Config"],
        summary="Create Configuration",
        description="Create a new app configuration",
        request=CreateAppConfigSerializer,
        responses={
            201: BaseResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new configuration"""
        def operation():
            # Validate request data
            serializer = CreateAppConfigSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create config with validated data
            service = AppConfigService()
            config = service.create_config(
                key=serializer.validated_data['key'],
                value=serializer.validated_data['value'],
                description=serializer.validated_data.get('description', ''),
                is_active=serializer.validated_data.get('is_active', True),
                is_public=serializer.validated_data.get('is_public', False),
                admin_user=request.user
            )
            
            return {
                'config_id': str(config.id),
                'key': config.key,
                'value': config.value,
                'is_active': config.is_active,
                'is_public': config.is_public,
                'message': f'Configuration {config.key} created successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration created successfully",
            error_message="Failed to create configuration",
            success_status=status.HTTP_201_CREATED,
            operation_context="Admin config creation"
        )
    
    @extend_schema(
        tags=["Admin - Config"],
        summary="Update Configuration",
        description="Update an existing app configuration by ID or key",
        request=UpdateAppConfigSerializer,
        responses={
            200: BaseResponseSerializer,
            400: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def put(self, request: Request) -> Response:
        """Update configuration"""
        def operation():
            serializer = UpdateAppConfigSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            config_id = serializer.validated_data.get('config_id')
            key = serializer.validated_data.get('key')
            value = serializer.validated_data.get('value')
            description = serializer.validated_data.get('description')
            is_active = serializer.validated_data.get('is_active')
            is_public = serializer.validated_data.get('is_public')
            
            service = AppConfigService()
            config = service.update_config(
                config_id=config_id,
                key=key,
                value=value,
                description=description,
                is_active=is_active,
                is_public=is_public,
                admin_user=request.user
            )
            
            return {
                'config_id': str(config.id),
                'key': config.key,
                'value': config.value,
                'is_active': config.is_active,
                'is_public': config.is_public,
                'message': f'Configuration {config.key} updated successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration updated successfully",
            error_message="Failed to update configuration",
            operation_context="Admin config update"
        )
    
    @extend_schema(
        tags=["Admin - Config"],
        summary="Delete Configuration",
        description="Delete an app configuration by ID or key (provide as query parameter)",
        parameters=[
            OpenApiParameter(
                name="config_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Configuration ID (use either config_id or key)",
                required=False
            ),
            OpenApiParameter(
                name="key",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Configuration key (use either config_id or key)",
                required=False
            )
        ],
        responses={
            200: BaseResponseSerializer,
            400: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def delete(self, request: Request) -> Response:
        """Delete configuration"""
        def operation():
            # Get from query params for DELETE
            config_id = request.query_params.get('config_id')
            key = request.query_params.get('key')
            
            if not config_id and not key:
                raise ValueError("Either config_id or key query parameter is required")
            
            service = AppConfigService()
            deleted_key = service.delete_config(
                config_id=config_id,
                key=key,
                admin_user=request.user
            )
            
            return {
                'deleted_key': deleted_key,
                'message': f'Configuration {deleted_key} deleted successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration deleted successfully",
            error_message="Failed to delete configuration",
            operation_context="Admin config deletion"
        )
