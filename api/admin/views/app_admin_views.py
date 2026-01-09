"""
Admin app management views - versions and updates
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
from api.common.serializers import BaseResponseSerializer, PaginatedResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.system.services import AppVersionService
from api.user.system.serializers import AppVersionSerializer, AppUpdateSerializer

app_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)

# ============================================================================
# App Version Admin Views
# ============================================================================
@app_admin_router.register(r"admin/app/versions", name="admin-app-versions")
@extend_schema(
    tags=["Admin - App"],
    summary="Admin App Versions",
    description="CRUD operations for app versions (Admin only)",
    parameters=[
        OpenApiParameter("platform", OpenApiTypes.STR, description="Filter by platform"),
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page"),
    ],
    responses={200: PaginatedResponseSerializer}
)
class AdminAppVersionsView(GenericAPIView, BaseAPIView):
    """Admin app versions management"""
    serializer_class = AppVersionSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all app versions with filtering"""
        def operation():
            platform = request.query_params.get('platform')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            from api.user.system.models import AppVersion
            from api.common.utils.helpers import paginate_queryset
            
            queryset = AppVersion.objects.all()
            if platform:
                queryset = queryset.filter(platform=platform)
            
            queryset = queryset.order_by('-released_at')
            
            paginated_data = paginate_queryset(queryset, page, page_size)
            
            # Serialize versions
            versions_serializer = AppVersionSerializer(
                paginated_data['results'], many=True
            )
            
            return {
                'results': versions_serializer.data,
                'pagination': paginated_data['pagination'],
                'filters': {
                    'platform': platform
                }
            }
        
        return self.handle_service_operation(
            operation,
            success_message="App versions retrieved successfully",
            error_message="Failed to retrieve app versions"
        )
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new app version"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AppVersionService()
            version = service.create_version(
                serializer.validated_data,
                admin_user=request.user
            )
            
            response_serializer = AppVersionSerializer(version)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="App version created successfully",
            error_message="Failed to create app version",
            status_code=status.HTTP_201_CREATED
        )

@app_admin_router.register(r"admin/app/versions/<str:version_id>", name="admin-app-version-detail")
@extend_schema(
    tags=["Admin - App"],
    summary="Admin App Version Detail",
    description="Get, update, or delete specific app version (admin privileges)",
    parameters=[
        OpenApiParameter(
            name="version_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="App version ID",
            required=True
        )
    ],
    responses={200: BaseResponseSerializer}
)
class AdminAppVersionDetailView(GenericAPIView, BaseAPIView):
    """Admin app version detail management"""
    serializer_class = AppVersionSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request, version_id: str) -> Response:
        """Get specific app version details"""
        def operation():
            from api.user.system.models import AppVersion
            
            try:
                version = AppVersion.objects.get(id=version_id)
                serializer = AppVersionSerializer(version)
                return {
                    'version': serializer.data,
                    'admin_actions': [
                        'view_details',
                        'update_version',
                        'delete_version'
                    ]
                }
            except AppVersion.DoesNotExist:
                raise ValueError(f"App version with ID {version_id} not found")
        
        return self.handle_service_operation(
            operation,
            success_message="App version details retrieved successfully",
            error_message="Failed to retrieve app version details"
        )
    
    @log_api_call()
    def put(self, request: Request, version_id: str) -> Response:
        """Update app version"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = AppVersionService()
            version = service.update_version(
                version_id,
                serializer.validated_data,
                admin_user=request.user
            )
            
            response_serializer = AppVersionSerializer(version)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="App version updated successfully",
            error_message="Failed to update app version"
        )
    
    @log_api_call()
    def delete(self, request: Request, version_id: str) -> Response:
        """Delete app version"""
        def operation():
            from api.user.system.models import AppVersion
            
            try:
                version = AppVersion.objects.get(id=version_id)
                
                # Log admin action before deletion
                from api.admin.models import AdminActionLog
                AdminActionLog.objects.create(
                    admin_user=request.user,
                    action_type='DELETE_APP_VERSION',
                    target_model='AppVersion',
                    target_id=version_id,
                    changes={
                        'version': version.version,
                        'platform': version.platform,
                        'is_mandatory': version.is_mandatory
                    },
                    description=f"Deleted app version: {version.platform} v{version.version}",
                    ip_address="127.0.0.1",
                    user_agent="Admin Panel"
                )
                
                version.delete()
                
                return {
                    'version_id': version_id,
                    'message': 'App version deleted successfully'
                }
            except AppVersion.DoesNotExist:
                raise ValueError(f"App version with ID {version_id} not found")
        
        return self.handle_service_operation(
            operation,
            success_message="App version deleted successfully",
            error_message="Failed to delete app version"
        )

# ============================================================================
# App Update Admin Views
# ============================================================================
@app_admin_router.register(r"admin/app/updates", name="admin-app-updates")
@extend_schema(
    tags=["Admin - App"],
    summary="Admin App Updates",
    description="CRUD operations for app updates (Admin only)",
    parameters=[
        OpenApiParameter("is_major", OpenApiTypes.BOOL, description="Filter by major updates"),
        OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
        OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page"),
    ],
    responses={200: PaginatedResponseSerializer}
)
class AdminAppUpdatesView(GenericAPIView, BaseAPIView):
    """Admin app updates management"""
    serializer_class = AppUpdateSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all app updates with filtering"""
        def operation():
            is_major = request.query_params.get('is_major')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            from api.user.system.models import AppUpdate
            from api.common.utils.helpers import paginate_queryset
            
            queryset = AppUpdate.objects.all()
            if is_major is not None:
                queryset = queryset.filter(is_major=is_major.lower() == 'true')
            
            queryset = queryset.order_by('-released_at')
            
            paginated_data = paginate_queryset(queryset, page, page_size)
            
            # Serialize updates
            updates_serializer = AppUpdateSerializer(
                paginated_data['results'], many=True
            )
            
            return {
                'results': updates_serializer.data,
                'pagination': paginated_data['pagination'],
                'filters': {
                    'is_major': is_major
                }
            }
        
        return self.handle_service_operation(
            operation,
            success_message="App updates retrieved successfully",
            error_message="Failed to retrieve app updates"
        )
    
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Create new app update"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            from api.user.system.models import AppUpdate
            
            update = AppUpdate.objects.create(**serializer.validated_data)
            
            # Log admin action
            from api.admin.models import AdminActionLog
            AdminActionLog.objects.create(
                admin_user=request.user,
                action_type='CREATE_APP_UPDATE',
                target_model='AppUpdate',
                target_id=str(update.id),
                changes=serializer.validated_data,
                description=f"Created app update: {update.title} v{update.version}",
                ip_address="127.0.0.1",
                user_agent="Admin Panel"
            )
            
            response_serializer = AppUpdateSerializer(update)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="App update created successfully",
            error_message="Failed to create app update",
            status_code=status.HTTP_201_CREATED
        )