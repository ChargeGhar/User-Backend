"""
Admin media management views
"""
from __future__ import annotations
import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework.request import Request
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from django.utils import timezone

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.serializers import BaseResponseSerializer, PaginatedResponseSerializer
from api.user.auth.permissions import IsStaffPermission
from api.user.media.services import MediaUploadService
from api.user.media.serializers import MediaUploadSerializer, MediaUploadCreateSerializer, MediaUploadResponseSerializer

media_admin_router = CustomViewRouter()
logger = logging.getLogger(__name__)

@media_admin_router.register(r"admin/media/uploads", name="admin-media-uploads")
class AdminMediaUploadsView(GenericAPIView, BaseAPIView):
    """Admin view for all media uploads"""
    serializer_class = MediaUploadSerializer
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=["Admin - Media"],
        summary="List Media Uploads",
        description="Get all media uploads with admin privileges (can see all users' uploads)",
        parameters=[
            OpenApiParameter("type", OpenApiTypes.STR, description="Filter by file type"),
            OpenApiParameter("user_id", OpenApiTypes.STR, description="Filter by user ID"),
            OpenApiParameter("page", OpenApiTypes.INT, description="Page number"),
            OpenApiParameter("page_size", OpenApiTypes.INT, description="Items per page"),
        ],
        responses={200: PaginatedResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all media uploads (admin can see all users' uploads)"""
        def operation():
            file_type = request.query_params.get('type')
            user_id = request.query_params.get('user_id')
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            service = MediaUploadService()
            uploads_data = service.get_all_uploads_admin(
                file_type=file_type,
                user_id=user_id,
                page=page,
                page_size=page_size
            )
            
            # Serialize uploads
            uploads_serializer = MediaUploadSerializer(
                uploads_data['results'], many=True
            )
            
            return {
                'results': uploads_serializer.data,
                'pagination': uploads_data['pagination'],
                'filters': {
                    'file_type': file_type,
                    'user_id': user_id
                }
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Media uploads retrieved successfully",
            error_message="Failed to retrieve media uploads"
        )
    
    @extend_schema(
        tags=["Admin - Media"],
        summary="Upload Media File",
        description="Upload new media file (images, videos, documents) to Cloudinary",
        request=MediaUploadCreateSerializer,
        responses={
            201: MediaUploadResponseSerializer,
            400: BaseResponseSerializer
        }
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Upload new media file (admin upload)"""
        def operation():
            # Validate request data
            serializer = MediaUploadCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            file = serializer.validated_data['file']
            file_type = serializer.validated_data['file_type']
            
            # Upload file
            service = MediaUploadService()
            media_upload = service.upload_file(
                file=file,
                file_type=file_type,
                user=request.user
            )
            
            # Return response
            response_serializer = MediaUploadResponseSerializer(media_upload)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            success_message="Media uploaded successfully",
            error_message="Failed to upload media"
        )

@media_admin_router.register(r"admin/media/uploads/<str:upload_id>", name="admin-media-upload-detail")
@extend_schema(
    tags=["Admin - Media"],
    summary="Admin Media Upload Detail",
    description="Get, update, or delete specific media upload (admin privileges)",
    parameters=[
        OpenApiParameter(
            name="upload_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Media upload ID",
            required=True
        )
    ],
    responses={200: BaseResponseSerializer}
)
class AdminMediaUploadDetailView(GenericAPIView, BaseAPIView):
    """Admin view for specific media upload"""
    serializer_class = MediaUploadSerializer
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request, upload_id: str) -> Response:
        """Get specific media upload details"""
        def operation():
            service = MediaUploadService()
            upload = service.get_upload_admin(upload_id)
            
            serializer = MediaUploadSerializer(upload)
            return {
                'upload': serializer.data,
                'admin_actions': [
                    'view_details',
                    'delete_upload',
                    'view_user_uploads'
                ]
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Media upload details retrieved successfully",
            error_message="Failed to retrieve media upload details"
        )
    
    @log_api_call()
    def delete(self, request: Request, upload_id: str) -> Response:
        """Delete specific media upload (admin can delete any upload)"""
        def operation():
            service = MediaUploadService()
            success = service.delete_upload_admin(upload_id, request.user)
            
            if not success:
                raise ValueError("Failed to delete media upload")
            
            return {
                'upload_id': upload_id,
                'message': 'Media upload deleted successfully by admin'
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Media upload deleted successfully",
            error_message="Failed to delete media upload"
        )

@media_admin_router.register(r"admin/media/analytics", name="admin-media-analytics")
@extend_schema(
    tags=["Admin - Media"],
    summary="Media Analytics",
    description="Get media upload analytics and statistics",
    responses={200: BaseResponseSerializer}
)
class AdminMediaAnalyticsView(GenericAPIView, BaseAPIView):
    """Admin media analytics"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get media upload analytics"""
        def operation():
            service = MediaUploadService()
            analytics = service.get_media_analytics()
            
            return {
                'analytics': analytics,
                'generated_at': timezone.now()
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Media analytics retrieved successfully",
            error_message="Failed to retrieve media analytics"
        )