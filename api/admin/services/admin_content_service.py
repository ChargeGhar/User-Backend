"""
Admin Content Service - Wrapper for content operations with admin audit
========================================================================

This service wraps content app services and adds admin-specific features:
- Audit logging for all admin actions
- Cache management
- Admin notifications

Follows the same pattern as AdminRefundService.
"""
import logging
from typing import Dict, Any, List

from django.db import transaction

from api.admin.models import AdminActionLog
from api.common.services.base import BaseService
from api.user.content.models import ContentPage, FAQ, ContactInfo, Banner
from api.user.content.services import (
    ContentPageService,
    FAQService,
    ContactInfoService,
    BannerService,
    ContentAnalyticsService
)

logger = logging.getLogger(__name__)


class AdminContentService(BaseService):
    """
    Wrapper service for admin content operations.
    Delegates to core content services and adds admin-specific features.
    Note: Uses BaseService instead of CRUDService since this is a wrapper, not CRUD.
    """
    
    def __init__(self):
        super().__init__()
        self.content_service = ContentPageService()
        self.faq_service = FAQService()
        self.contact_service = ContactInfoService()
        self.banner_service = BannerService()
        self.analytics_service = ContentAnalyticsService()
    
    # ==================== Content Pages ====================
    
    @transaction.atomic
    def update_content_page(
        self, page_type: str, title: str, content: str, admin_user
    ) -> ContentPage:
        """Update content page with admin logging"""
        try:
            # Delegate to core service
            page = self.content_service.update_page_content(
                page_type=page_type,
                title=title,
                content=content,
                admin_user=admin_user
            )
            
            # Admin-specific operations
            self._log_admin_action(
                admin_user, 'CONTENT_PAGE_UPDATE', 'ContentPage', 
                str(page.id), {'page_type': page_type, 'title': title}
            )
            
            logger.info(f"Admin {admin_user.username} updated content page: {page_type}")
            return page
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update content page")
    
    def get_content_analytics(self) -> Dict[str, Any]:
        """Get content analytics (direct delegation)"""
        try:
            return self.analytics_service.get_content_analytics()
        except Exception as e:
            self.handle_service_error(e, "Failed to get content analytics")
    
    # ==================== FAQs ====================
    
    @transaction.atomic
    def create_faq(
        self, question: str, answer: str, category: str, admin_user
    ) -> FAQ:
        """Create FAQ with admin logging"""
        try:
            faq = self.faq_service.create_faq(question, answer, category, admin_user)
            
            self._log_admin_action(
                admin_user, 'FAQ_CREATE', 'FAQ', str(faq.id),
                {'question': question[:50], 'category': category}
            )
            
            logger.info(f"Admin {admin_user.username} created FAQ: {faq.id}")
            return faq
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create FAQ")
    
    @transaction.atomic
    def update_faq(
        self, faq_id: str, question: str, answer: str, category: str, admin_user
    ) -> FAQ:
        """Update FAQ with admin logging"""
        try:
            faq = self.faq_service.update_faq(
                faq_id, question, answer, category, admin_user
            )
            
            self._log_admin_action(
                admin_user, 'FAQ_UPDATE', 'FAQ', str(faq.id),
                {'question': question[:50]}
            )
            
            logger.info(f"Admin {admin_user.username} updated FAQ: {faq_id}")
            return faq
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update FAQ")
    
    @transaction.atomic
    def delete_faq(self, faq_id: str, admin_user) -> None:
        """Delete FAQ with admin logging"""
        try:
            self.faq_service.delete_by_id(faq_id)
            
            self._log_admin_action(
                admin_user, 'FAQ_DELETE', 'FAQ', faq_id, {}
            )
            
            logger.info(f"Admin {admin_user.username} deleted FAQ: {faq_id}")
            
        except Exception as e:
            self.handle_service_error(e, "Failed to delete FAQ")
    
    def get_all_faqs(self) -> List[FAQ]:
        """Get all FAQs (direct delegation)"""
        try:
            return self.faq_service.get_all()
        except Exception as e:
            self.handle_service_error(e, "Failed to get FAQs")
    
    def get_faq_by_id(self, faq_id: str) -> FAQ:
        """Get FAQ by ID (direct delegation)"""
        try:
            return self.faq_service.get_by_id(faq_id)
        except Exception as e:
            self.handle_service_error(e, "Failed to get FAQ")
    
    # ==================== Contact Info ====================
    
    @transaction.atomic
    def update_contact_info(
        self, info_type: str, label: str, value: str, 
        description: str, admin_user
    ) -> ContactInfo:
        """Update contact info with admin logging"""
        try:
            contact = self.contact_service.update_contact_info(
                info_type, label, value, description, admin_user
            )
            
            self._log_admin_action(
                admin_user, 'CONTACT_UPDATE', 'ContactInfo',
                str(contact.id), {'info_type': info_type, 'label': label}
            )
            
            logger.info(f"Admin {admin_user.username} updated contact info: {info_type}")
            return contact
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update contact info")
    
    @transaction.atomic
    def delete_contact_info(self, contact_id: str, admin_user) -> None:
        """Delete contact info with admin logging"""
        try:
            self.contact_service.delete_by_id(contact_id)
            
            self._log_admin_action(
                admin_user, 'CONTACT_DELETE', 'ContactInfo', contact_id, {}
            )
            
            logger.info(f"Admin {admin_user.username} deleted contact info: {contact_id}")
            
        except Exception as e:
            self.handle_service_error(e, "Failed to delete contact info")
    
    def get_all_contact_info(self) -> List[ContactInfo]:
        """Get all contact info (direct delegation)"""
        try:
            return self.contact_service.get_all()
        except Exception as e:
            self.handle_service_error(e, "Failed to get contact info")
    
    def get_contact_info_by_id(self, contact_id: str) -> ContactInfo:
        """Get contact info by ID (direct delegation)"""
        try:
            return self.contact_service.get_by_id(contact_id)
        except Exception as e:
            self.handle_service_error(e, "Failed to get contact info")
    
    # ==================== Banners ====================
    
    @transaction.atomic
    def create_banner(
        self, title: str, description: str, image_url: str, redirect_url: str,
        valid_from, valid_until, admin_user
    ) -> Banner:
        """Create banner with admin logging"""
        try:
            banner = self.banner_service.create_banner(
                title=title,
                description=description,
                image_url=image_url,
                redirect_url=redirect_url,
                valid_from=valid_from,
                valid_until=valid_until,
                admin_user=admin_user
            )
            
            self._log_admin_action(
                admin_user, 'BANNER_CREATE', 'Banner', str(banner.id),
                {'title': title}
            )
            
            logger.info(f"Admin {admin_user.username} created banner: {banner.id}")
            return banner
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create banner")
    
    @transaction.atomic
    def update_banner(
        self, banner_id: str, title: str, description: str, image_url: str,
        redirect_url: str, valid_from, valid_until, admin_user
    ) -> Banner:
        """Update banner with admin logging"""
        try:
            banner = self.banner_service.update_banner(
                banner_id=banner_id,
                title=title,
                description=description,
                image_url=image_url,
                redirect_url=redirect_url,
                valid_from=valid_from,
                valid_until=valid_until
            )
            
            self._log_admin_action(
                admin_user, 'BANNER_UPDATE', 'Banner', str(banner.id),
                {'title': title}
            )
            
            logger.info(f"Admin {admin_user.username} updated banner: {banner_id}")
            return banner
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update banner")
    
    @transaction.atomic
    def delete_banner(self, banner_id: str, admin_user) -> None:
        """Delete banner with admin logging"""
        try:
            self.banner_service.delete_by_id(banner_id)
            
            self._log_admin_action(
                admin_user, 'BANNER_DELETE', 'Banner', banner_id, {}
            )
            
            logger.info(f"Admin {admin_user.username} deleted banner: {banner_id}")
            
        except Exception as e:
            self.handle_service_error(e, "Failed to delete banner")
    
    def get_all_banners(self) -> List[Banner]:
        """Get all banners (direct delegation)"""
        try:
            return self.banner_service.get_all()
        except Exception as e:
            self.handle_service_error(e, "Failed to get banners")
    
    def get_banner_by_id(self, banner_id: str) -> Banner:
        """Get banner by ID (direct delegation)"""
        try:
            return self.banner_service.get_by_id(banner_id)
        except Exception as e:
            self.handle_service_error(e, "Failed to get banner")
    
    # ==================== Helper Methods ====================
    
    def _log_admin_action(
        self, admin_user, action_type: str, target_model: str,
        target_id: str, changes: Dict[str, Any]
    ) -> None:
        """Log admin action for audit trail"""
        try:
            AdminActionLog.objects.create(
                admin_user=admin_user,
                action_type=action_type,
                target_model=target_model,
                target_id=target_id,
                changes=changes,
                description=f"{action_type} on {target_model}",
                ip_address="127.0.0.1",  # TODO: Get from request context
                user_agent="Admin Panel"  # TODO: Get from request context
            )
        except Exception as e:
            logger.warning(f"Failed to log admin action: {str(e)}")
