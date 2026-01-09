"""
Late Fee Configuration Admin Views
============================================================

Admin endpoints for managing late fee configurations.
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
from api.admin.services.late_fee_service import LateFeeConfigurationService
from api.admin.serializers.late_fee_serializers import (
    LateFeeConfigurationSerializer,
    CreateLateFeeConfigurationSerializer,
    UpdateLateFeeConfigurationSerializer,
    ActivateLateFeeConfigurationSerializer,
    LateFeeCalculationTestSerializer
)

late_fee_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)


@late_fee_admin_router.register(r"admin/late-fee-configs", name="admin-late-fee-configs")
class LateFeeConfigurationListView(GenericAPIView, BaseAPIView):
    """Admin endpoints for late fee configuration management"""
    
    permission_classes = [IsStaffPermission]
    serializer_class = LateFeeConfigurationSerializer
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Get All Late Fee Configurations",
        description="Get all late fee configurations with filtering and pagination (Admin only)",
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by active status (true/false)",
                required=False
            ),
            OpenApiParameter(
                name="fee_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by fee type (MULTIPLIER, FLAT_RATE, COMPOUND)",
                required=False
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search in configuration name",
                required=False
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number (default: 1)",
                required=False
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Items per page (default: 20)",
                required=False
            )
        ],
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all late fee configurations"""
        def operation():
            # Build filters from query params
            filters = {
                'page': 1,
                'page_size': 20
            }
            
            if 'is_active' in request.query_params:
                is_active_str = request.query_params['is_active'].lower()
                filters['is_active'] = is_active_str in ('true', '1', 'yes')
            
            if request.query_params.get('fee_type'):
                filters['fee_type'] = request.query_params['fee_type'].upper()
            
            if request.query_params.get('search'):
                filters['search'] = request.query_params['search']
            
            if request.query_params.get('page'):
                try:
                    filters['page'] = int(request.query_params['page'])
                except ValueError:
                    filters['page'] = 1
            
            if request.query_params.get('page_size'):
                try:
                    filters['page_size'] = int(request.query_params['page_size'])
                except ValueError:
                    filters['page_size'] = 20
            
            # Get configurations
            service = LateFeeConfigurationService()
            result = service.get_all_configurations(filters)
            
            # Serialize configurations
            serializer = LateFeeConfigurationSerializer(result['results'], many=True)
            
            return {
                'configurations': serializer.data,
                'pagination': result['pagination'],
                'summary': result.get('summary', {})
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Late fee configurations retrieved successfully",
            error_message="Failed to retrieve configurations",
            operation_context="Admin late fee config list"
        )
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Create Late Fee Configuration",
        description="Create a new late fee configuration",
        request=CreateLateFeeConfigurationSerializer,
        responses={
            201: BaseResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new late fee configuration"""
        def operation():
            # Validate request data
            serializer = CreateLateFeeConfigurationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Create configuration
            service = LateFeeConfigurationService()
            config = service.create_configuration(
                name=serializer.validated_data['name'],
                fee_type=serializer.validated_data['fee_type'],
                multiplier=serializer.validated_data.get('multiplier'),
                flat_rate_per_hour=serializer.validated_data.get('flat_rate_per_hour'),
                grace_period_minutes=serializer.validated_data.get('grace_period_minutes', 0),
                max_daily_rate=serializer.validated_data.get('max_daily_rate'),
                is_active=serializer.validated_data.get('is_active', True),
                applicable_package_types=serializer.validated_data.get('applicable_package_types', []),
                metadata=serializer.validated_data.get('metadata', {}),
                admin_user=request.user
            )
            
            # Serialize result
            result_serializer = LateFeeConfigurationSerializer(config)
            
            return {
                'configuration': result_serializer.data,
                'message': f'Late fee configuration "{config.name}" created successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Late fee configuration created successfully",
            error_message="Failed to create configuration",
            success_status=status.HTTP_201_CREATED,
            operation_context="Admin late fee config creation"
        )


@late_fee_admin_router.register(
    r"admin/late-fee-configs/<uuid:config_id>",
    name="admin-late-fee-config-detail"
)
class LateFeeConfigurationDetailView(GenericAPIView, BaseAPIView):
    """Admin endpoints for specific late fee configuration"""
    
    permission_classes = [IsStaffPermission]
    serializer_class = LateFeeConfigurationSerializer
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Get Late Fee Configuration",
        description="Get details of a specific late fee configuration",
        responses={
            200: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def get(self, request: Request, config_id: str) -> Response:
        """Get configuration details"""
        def operation():
            service = LateFeeConfigurationService()
            config = service.get_configuration_by_id(config_id)
            
            serializer = LateFeeConfigurationSerializer(config)
            
            return {
                'configuration': serializer.data
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration retrieved successfully",
            error_message="Failed to retrieve configuration",
            operation_context="Admin late fee config detail"
        )
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Update Late Fee Configuration",
        description="Update an existing late fee configuration",
        request=UpdateLateFeeConfigurationSerializer,
        responses={
            200: BaseResponseSerializer,
            400: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def put(self, request: Request, config_id: str) -> Response:
        """Update configuration"""
        def operation():
            # Validate request data
            serializer = UpdateLateFeeConfigurationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Update configuration
            service = LateFeeConfigurationService()
            config = service.update_configuration(
                config_id=config_id,
                admin_user=request.user,
                **serializer.validated_data
            )
            
            # Serialize result
            result_serializer = LateFeeConfigurationSerializer(config)
            
            return {
                'configuration': result_serializer.data,
                'message': f'Configuration "{config.name}" updated successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration updated successfully",
            error_message="Failed to update configuration",
            operation_context="Admin late fee config update"
        )
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Delete Late Fee Configuration",
        description="Delete a late fee configuration (cannot delete active configuration)",
        responses={
            200: BaseResponseSerializer,
            400: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def delete(self, request: Request, config_id: str) -> Response:
        """Delete configuration"""
        def operation():
            service = LateFeeConfigurationService()
            config_name = service.delete_configuration(
                config_id=config_id,
                admin_user=request.user
            )
            
            return {
                'deleted_configuration': config_name,
                'message': f'Configuration "{config_name}" deleted successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration deleted successfully",
            error_message="Failed to delete configuration",
            operation_context="Admin late fee config deletion"
        )


@late_fee_admin_router.register(
    r"admin/late-fee-configs/<uuid:config_id>/activate",
    name="admin-late-fee-config-activate"
)
class LateFeeConfigurationActivateView(GenericAPIView, BaseAPIView):
    """Activate a late fee configuration"""
    
    permission_classes = [IsStaffPermission]
    serializer_class = ActivateLateFeeConfigurationSerializer
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Activate Late Fee Configuration",
        description="Activate a late fee configuration (optionally deactivates others)",
        request=ActivateLateFeeConfigurationSerializer,
        responses={
            200: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request, config_id: str) -> Response:
        """Activate configuration"""
        def operation():
            # Validate request data
            serializer = ActivateLateFeeConfigurationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Activate configuration
            service = LateFeeConfigurationService()
            config = service.activate_configuration(
                config_id=config_id,
                deactivate_others=serializer.validated_data.get('deactivate_others', True),
                admin_user=request.user
            )
            
            # Serialize result
            result_serializer = LateFeeConfigurationSerializer(config)
            
            return {
                'configuration': result_serializer.data,
                'message': f'Configuration "{config.name}" activated successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration activated successfully",
            error_message="Failed to activate configuration",
            operation_context="Admin late fee config activation"
        )


@late_fee_admin_router.register(
    r"admin/late-fee-configs/<uuid:config_id>/deactivate",
    name="admin-late-fee-config-deactivate"
)
class LateFeeConfigurationDeactivateView(GenericAPIView, BaseAPIView):
    """Deactivate a late fee configuration"""
    
    permission_classes = [IsStaffPermission]
    serializer_class = None
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Deactivate Late Fee Configuration",
        description="Deactivate a late fee configuration",
        request=None,
        responses={
            200: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request, config_id: str) -> Response:
        """Deactivate configuration"""
        def operation():
            service = LateFeeConfigurationService()
            config = service.deactivate_configuration(
                config_id=config_id,
                admin_user=request.user
            )
            
            # Serialize result
            result_serializer = LateFeeConfigurationSerializer(config)
            
            return {
                'configuration': result_serializer.data,
                'message': f'Configuration "{config.name}" deactivated successfully',
                'warning': 'No active late fee configuration. Late fees will not be calculated!'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Configuration deactivated successfully",
            error_message="Failed to deactivate configuration",
            operation_context="Admin late fee config deactivation"
        )


@late_fee_admin_router.register(
    r"admin/late-fee-configs/test-calculation",
    name="admin-late-fee-config-test"
)
class LateFeeCalculationTestView(GenericAPIView, BaseAPIView):
    """Test late fee calculation"""
    
    permission_classes = [IsStaffPermission]
    serializer_class = LateFeeCalculationTestSerializer
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Test Late Fee Calculation",
        description="Test how a late fee configuration would calculate fees for given parameters",
        request=LateFeeCalculationTestSerializer,
        responses={
            200: BaseResponseSerializer,
            400: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Test late fee calculation"""
        def operation():
            # Validate request data
            serializer = LateFeeCalculationTestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Run test calculation
            service = LateFeeConfigurationService()
            result = service.test_calculation(
                config_id=str(serializer.validated_data['configuration_id']),
                normal_rate_per_minute=serializer.validated_data['normal_rate_per_minute'],
                overdue_minutes=serializer.validated_data['overdue_minutes']
            )
            
            return {
                'test_result': result,
                'message': 'Calculation test completed successfully'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Calculation test completed successfully",
            error_message="Failed to test calculation",
            operation_context="Admin late fee config test"
        )


@late_fee_admin_router.register(
    r"admin/late-fee-configs/active",
    name="admin-late-fee-config-active"
)
class ActiveLateFeeConfigurationView(GenericAPIView, BaseAPIView):
    """Get currently active late fee configuration"""
    
    permission_classes = [IsStaffPermission]
    serializer_class = LateFeeConfigurationSerializer
    
    @extend_schema(
        tags=["Admin - Late Fee Configuration"],
        summary="Get Active Configuration",
        description="Get the currently active late fee configuration",
        responses={
            200: BaseResponseSerializer,
            404: BaseResponseSerializer
        }
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get active configuration"""
        def operation():
            service = LateFeeConfigurationService()
            config = service.get_active_configuration()
            
            if config:
                serializer = LateFeeConfigurationSerializer(config)
                return {
                    'configuration': serializer.data,
                    'message': 'Active configuration found'
                }
            else:
                return {
                    'configuration': None,
                    'message': 'No active late fee configuration found',
                    'warning': 'Late fees will not be calculated without an active configuration'
                }
        
        return self.handle_service_operation(
            operation,
            success_message="Active configuration retrieved",
            error_message="Failed to retrieve active configuration",
            operation_context="Admin late fee config active"
        )
