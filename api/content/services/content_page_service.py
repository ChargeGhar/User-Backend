from __future__ import annotations

from django.db import transaction
from django.core.cache import cache
from api.common.services.base import BaseService, ServiceException
from api.content.repositories.content_page_repository import ContentPageRepository
from api.content.models import ContentPage

class ContentPageService(BaseService):
    """Service for content page operations"""
    
    def get_page_by_type(self, page_type: str):
        """Get content page by type"""
        page = ContentPageRepository.get_by_type(page_type)
        if not page:
            raise ServiceException(
                detail=f"Content page '{page_type}' not found",
                code="page_not_found"
            )
        return page
    
    @transaction.atomic
    def update_page_content(self, page_type: str, title: str, content: str, admin_user) -> ContentPage:
        """Update content page"""
        try:
            page, created = ContentPageRepository.get_or_create(
                page_type=page_type,
                defaults={'title': title, 'content': content, 'is_active': True}
            )
            
            if not created:
                ContentPageRepository.update(
                    page,
                    title=title,
                    content=content
                )
            
            # Clear cache
            cache_key = f"content_page:{page_type}"
            cache.delete(cache_key)
            
            # Log admin action
            from api.admin.models import AdminActionLog
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type='UPDATE_CONTENT_PAGE',
                target_model='ContentPage',
                target_id=str(page.id),
                changes={'page_type': page_type, 'title': title},
                description=f"Updated content page: {page_type}",
                ip_address="127.0.0.1",
                user_agent="Admin Panel"
            )
            
            self.log_info(f"Content page updated: {page_type}")
            return page
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update content page")
