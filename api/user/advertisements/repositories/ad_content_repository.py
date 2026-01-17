"""
AdContent Repository
====================
Data access layer for AdContent model.
"""
from typing import Optional, List
from django.db.models import QuerySet
from api.user.advertisements.models import AdContent


class AdContentRepository:
    """Repository for AdContent data operations"""
    
    @staticmethod
    def get_by_id(content_id: str) -> Optional[AdContent]:
        """Get ad content by ID"""
        try:
            return AdContent.objects.select_related(
                'ad_request',
                'media_upload'
            ).prefetch_related(
                'ad_distributions__station'
            ).get(id=content_id)
        except AdContent.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_ad_request(ad_request_id: str) -> Optional[AdContent]:
        """Get active ad content by ad request ID"""
        return AdContent.objects.filter(
            ad_request_id=ad_request_id,
            is_active=True
        ).select_related('media_upload').first()
    
    @staticmethod
    def get_all_by_ad_request(ad_request_id: str) -> List[AdContent]:
        """Get all ad contents for an ad request"""
        return list(AdContent.objects.filter(
            ad_request_id=ad_request_id
        ).select_related('media_upload').order_by('display_order', '-created_at'))
    
    @staticmethod
    def get_active_contents_by_ad_request(ad_request_id: str) -> List[AdContent]:
        """Get all active ad contents for an ad request"""
        return list(AdContent.objects.filter(
            ad_request_id=ad_request_id,
            is_active=True
        ).select_related('media_upload').order_by('display_order', '-created_at'))
    
    @staticmethod
    def create(ad_request, **kwargs) -> AdContent:
        """Create new ad content"""
        return AdContent.objects.create(ad_request=ad_request, **kwargs)
    
    @staticmethod
    def update(ad_content: AdContent, **kwargs) -> AdContent:
        """Update existing ad content"""
        for field, value in kwargs.items():
            setattr(ad_content, field, value)
        ad_content.save()
        return ad_content
    
    @staticmethod
    def deactivate_all_for_ad_request(ad_request_id: str) -> int:
        """Deactivate all ad contents for an ad request"""
        return AdContent.objects.filter(
            ad_request_id=ad_request_id
        ).update(is_active=False)
    
    @staticmethod
    def delete(ad_content: AdContent) -> None:
        """Delete ad content"""
        ad_content.delete()
    
    @staticmethod
    def count_by_ad_request(ad_request_id: str) -> int:
        """Count ad contents for an ad request"""
        return AdContent.objects.filter(ad_request_id=ad_request_id).count()
    
    @staticmethod
    def count_active_by_ad_request(ad_request_id: str) -> int:
        """Count active ad contents for an ad request"""
        return AdContent.objects.filter(
            ad_request_id=ad_request_id,
            is_active=True
        ).count()
