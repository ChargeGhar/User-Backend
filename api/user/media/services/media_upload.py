from __future__ import annotations

import logging
from typing import Optional
from django.db import models
from django.core.files.uploadedfile import InMemoryUploadedFile

from api.common.services.base import CRUDService
from api.user.media.services.cloud_storage import CloudStorageFactory
from api.user.media.models import MediaUpload

logger = logging.getLogger(__name__)

class MediaUploadService(CRUDService):
    """Service for media upload operations"""
    model = MediaUpload
    
    def upload_file(self, file: InMemoryUploadedFile, file_type: str, user=None) -> MediaUpload:
        """Upload file to cloud storage and create database record"""
        try:
            # Get cloud storage service
            storage_service = CloudStorageFactory.get_storage_service()
            
            # Upload to cloud storage
            upload_result = storage_service.upload_file(file, folder=file_type.lower())
            
            # Create database record
            media_upload = self.model.objects.create(
                original_name=file.name,
                file_url=upload_result['file_url'],
                file_type=file_type,
                file_size=file.size,
                uploaded_by=user,
                cloud_provider=upload_result['provider'],
                public_id=upload_result['public_id'],
                metadata=upload_result.get('upload_result', {})
            )
            
            self.log_info(f"File uploaded successfully: {file.name}")
            return media_upload
            
        except Exception as e:
            self.handle_service_error(e, "Failed to upload file")
    
    def _upload_to_cloud_storage(self, file: InMemoryUploadedFile) -> str:
        """Upload file to cloud storage (Cloudinary/AWS S3)"""
        # This method is deprecated - use upload_file instead
        storage_service = CloudStorageFactory.get_storage_service()
        result = storage_service.upload_file(file)
        return result['file_url']
    
    def get_user_uploads(self, user, file_type: Optional[str] = None) -> models.QuerySet:
        """Get user's uploaded files"""
        try:
            if not user.is_authenticated:
                return self.model.objects.none()
            queryset = self.model.objects.filter(uploaded_by=user)
            
            if file_type:
                queryset = queryset.filter(file_type=file_type)
            
            return queryset.order_by('-created_at')
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get user uploads")
    
    def delete_upload(self, upload_id: str, user) -> bool:
        """Delete user's uploaded file"""
        try:
            upload = self.model.objects.get(
                id=upload_id,
                uploaded_by=user
            )
            
            # Delete from cloud storage
            self._delete_from_cloud_storage(upload)
            
            upload.delete()
            self.log_info(f"File deleted successfully: {upload.original_name}")
            return True
            
        except self.model.DoesNotExist:
            return False
        except Exception as e:
            self.handle_service_error(e, "Failed to delete upload")
            return False
    
    def _delete_from_cloud_storage(self, upload: MediaUpload) -> None:
        """Delete file from cloud storage"""
        try:
            storage_service = CloudStorageFactory.get_storage_service()
            storage_service.delete_file(upload.public_id or upload.file_url)
        except Exception as e:
            self.log_error(f"Failed to delete from cloud storage: {str(e)}")
    
    # Admin methods
    def get_all_uploads_admin(self, file_type: Optional[str] = None, user_id: Optional[str] = None, 
                             page: int = 1, page_size: int = 20) -> dict:
        """Get all uploads with admin privileges"""
        try:
            from api.common.utils.helpers import paginate_queryset
            
            queryset = self.model.objects.select_related('uploaded_by').all()
            
            if file_type:
                queryset = queryset.filter(file_type=file_type)
            
            if user_id:
                queryset = queryset.filter(uploaded_by_id=user_id)
            
            queryset = queryset.order_by('-created_at')
            
            return paginate_queryset(queryset, page, page_size)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get all uploads")
    
    def get_upload_admin(self, upload_id: str) -> MediaUpload:
        """Get specific upload with admin privileges"""
        try:
            return self.model.objects.select_related('uploaded_by').get(id=upload_id)
        except self.model.DoesNotExist:
            raise ValueError(f"Upload with ID {upload_id} not found")
        except Exception as e:
            self.handle_service_error(e, "Failed to get upload")
    
    def delete_upload_admin(self, upload_id: str, admin_user) -> bool:
        """Delete any upload with admin privileges"""
        try:
            upload = self.model.objects.get(id=upload_id)
            
            # Delete from cloud storage
            self._delete_from_cloud_storage(upload)
            
            # Log admin action
            from api.admin.models import AdminActionLog
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type='DELETE_MEDIA',
                target_model='MediaUpload',
                target_id=upload_id,
                changes={
                    'original_name': upload.original_name,
                    'uploaded_by': upload.uploaded_by.username if upload.uploaded_by else None,
                    'file_type': upload.file_type
                },
                description=f"Deleted media upload: {upload.original_name}",
                ip_address="127.0.0.1",
                user_agent="Admin Panel"
            )
            
            upload.delete()
            self.log_info(f"File deleted by admin: {upload.original_name}")
            return True
            
        except self.model.DoesNotExist:
            return False
        except Exception as e:
            self.handle_service_error(e, "Failed to delete upload")
            return False
    
    def get_media_analytics(self) -> dict:
        """Get media upload analytics"""
        try:
            from django.db.models import Count, Sum
            from django.utils import timezone
            from datetime import timedelta
            
            total_uploads = self.model.objects.count()
            total_size = self.model.objects.aggregate(total=Sum('file_size'))['total'] or 0
            
            # Recent uploads (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_uploads = self.model.objects.filter(created_at__gte=thirty_days_ago).count()
            
            # By file type
            by_type = self.model.objects.values('file_type').annotate(
                count=Count('id'),
                total_size=Sum('file_size')
            ).order_by('-count')
            
            # Top uploaders
            top_uploaders = self.model.objects.values(
                'uploaded_by__username'
            ).annotate(
                upload_count=Count('id')
            ).filter(uploaded_by__isnull=False).order_by('-upload_count')[:10]
            
            return {
                'total_uploads': total_uploads,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2) if total_size else 0,
                'recent_uploads_30_days': recent_uploads,
                'uploads_by_type': list(by_type),
                'top_uploaders': list(top_uploaders)
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get media analytics")
