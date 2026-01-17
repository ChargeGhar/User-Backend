"""
AdRequest Service
=================
Handles user-side ad request operations: create and list.
"""
from __future__ import annotations

from typing import Optional
from django.db import transaction
from django.utils import timezone

from api.common.services.base import BaseService, ServiceException
from api.user.advertisements.models import AdRequest, AdContent
from api.user.advertisements.repositories import (
    AdRequestRepository,
    AdContentRepository
)
from api.user.media.models import MediaUpload


class AdRequestService(BaseService):
    """Service for user ad request operations"""
    
    @transaction.atomic
    def create_ad_request(self, user, validated_data: dict) -> AdRequest:
        """
        Create new ad request with content.
        
        Business Rules:
        1. User must provide: full_name, contact_number, media_upload_id
        2. Media upload must exist and belong to user
        3. Media must be IMAGE or VIDEO type
        4. AdRequest created with status='SUBMITTED'
        5. AdContent created with default duration_seconds=5, display_order=0
        6. Content type determined from media file_type
        
        Args:
            user: User creating the ad request
            validated_data: Dict with full_name, contact_number, media_upload_id
            
        Returns:
            AdRequest: Created ad request with content
            
        Raises:
            ServiceException: If media not found or invalid type
        """
        try:
            # Get and validate media upload
            try:
                media_upload = MediaUpload.objects.get(
                    id=validated_data['media_upload_id'],
                    uploaded_by=user
                )
            except MediaUpload.DoesNotExist:
                raise ServiceException(
                    detail="Media upload not found or access denied",
                    code="media_not_found"
                )
            
            # Validate media type
            if media_upload.file_type not in ['IMAGE', 'VIDEO']:
                raise ServiceException(
                    detail="Only IMAGE or VIDEO files are allowed for advertisements",
                    code="invalid_media_type"
                )
            
            # Create AdRequest
            ad_request = AdRequestRepository.create(
                user=user,
                full_name=validated_data['full_name'],
                contact_number=validated_data['contact_number'],
                status='SUBMITTED',
                submitted_at=timezone.now()
            )
            
            # Create AdContent
            AdContentRepository.create(
                ad_request=ad_request,
                media_upload=media_upload,
                content_type=media_upload.file_type,  # IMAGE or VIDEO
                is_active=True,
                duration_seconds=5,  # default for images
                display_order=0
            )
            
            self.log_info(
                f"Ad request created: {ad_request.id} by user {user.username}"
            )
            
            return ad_request
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to create ad request")
    
    def get_user_ad_requests(self, user, filters: Optional[dict] = None):
        """
        Get user's ad requests with optional filtering.
        
        Business Rules:
        1. Only return ads belonging to the user
        2. Support status filter (optional)
        3. Return QuerySet for pagination support
        4. Include all related data (transaction, content, stations)
        
        Args:
            user: User whose ads to retrieve
            filters: Optional dict with 'status' key
            
        Returns:
            QuerySet: User's ad requests with relations
        """
        try:
            status = filters.get('status') if filters else None
            return AdRequestRepository.get_user_ad_requests(user, status)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get user ad requests")
    
    def get_user_ad_by_id(self, ad_id: str, user) -> AdRequest:
        """
        Get single ad request for user.
        
        Business Rules:
        1. Ad must belong to the user
        2. Include all related data
        
        Args:
            ad_id: Ad request ID
            user: User who owns the ad
            
        Returns:
            AdRequest: Ad request with relations
            
        Raises:
            ServiceException: If ad not found or access denied
        """
        try:
            ad_request = AdRequestRepository.get_by_id_for_user(ad_id, user)
            
            if not ad_request:
                raise ServiceException(
                    detail="Ad request not found or access denied",
                    code="ad_not_found"
                )
            
            return ad_request
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to get ad request")
