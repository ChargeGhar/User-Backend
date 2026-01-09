from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.common.services.base import ServiceException
from api.user.media.services import MediaUploadService
from api.user.media.serializers import (
    MediaUploadSerializer,
    MediaUploadCreateSerializer,
    MediaUploadResponseSerializer
)

router = CustomViewRouter()

@router.register(r"app/media/upload", name="media-upload")
class MediaUploadView(GenericAPIView, BaseAPIView):
    """Upload media files to cloud storage"""
    serializer_class = MediaUploadCreateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        tags=["App"],
        summary="Upload Media",
        description="Upload media files like images, videos to Cloudinary. Returns secure URLs for storage and CDN access.",
    )
    @log_api_call()
    def post(self, request: Request) -> Response:
        """Upload media files to cloud storage"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            file = serializer.validated_data['file']
            file_type = serializer.validated_data['file_type']
            
            service = MediaUploadService()
            media_upload = service.upload_file(file, file_type, request.user)
            
            response_serializer = MediaUploadResponseSerializer(media_upload)
            return response_serializer.data
        
        return self.handle_service_operation(
            operation,
            "Media uploaded successfully",
            "Failed to upload media",
            success_status=status.HTTP_201_CREATED
        )


