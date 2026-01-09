from __future__ import annotations

from typing import List
from django.db import transaction
from django.utils import timezone
from api.common.services.base import BaseService, ServiceException
from api.user.content.repositories.banner_repository import BannerRepository
from api.user.content.models import Banner

class BannerService(BaseService):
    """Service for banner operations"""
    
    def get_all(self):
        """Get all banners for admin"""
        try:
            return BannerRepository.get_all()
        except Exception as e:
            self.handle_service_error(e, "Failed to get all banners")
    
    def get_by_id(self, banner_id: str):
        """Get banner by ID"""
        banner = BannerRepository.get_by_id(banner_id)
        if not banner:
            raise ServiceException(
                detail="Banner not found",
                code="banner_not_found"
            )
        return banner
    
    def delete_by_id(self, banner_id: str):
        """Delete banner by ID"""
        try:
            banner = self.get_by_id(banner_id)
            BannerRepository.delete(banner)
            self.log_info(f"Banner deleted: {banner_id}")
            return True
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to delete banner")
    
    def get_active_banners(self) -> List:
        """Get currently active banners"""
        try:
            return BannerRepository.get_active_banners()
        except Exception as e:
            self.handle_service_error(e, "Failed to get active banners")
    
    @transaction.atomic
    def create_banner(self, title: str, description: str, image_url: str,
                       redirect_url: str, valid_from: timezone.datetime,
                       valid_until: timezone.datetime, admin_user) -> Banner:
        """Create new banner"""
        try:
            max_order = BannerRepository.get_max_display_order()
            
            banner = BannerRepository.create(
                title=title,
                description=description,
                image_url=image_url,
                redirect_url=redirect_url,
                display_order=max_order + 1,
                valid_from=valid_from,
                valid_until=valid_until
            )
            
            self.log_info(f"Banner created: {title}")
            return banner
            
        except Exception as e:
            self.handle_service_error(e, "Failed to create banner")
    
    @transaction.atomic
    def update_banner(self, banner_id: str, title: str, description: str, 
                       image_url: str, redirect_url: str, valid_from: timezone.datetime,
                       valid_until: timezone.datetime) -> Banner:
        """Update existing banner"""
        try:
            banner = self.get_by_id(banner_id)
            
            updated_banner = BannerRepository.update(
                banner,
                title=title,
                description=description,
                image_url=image_url,
                redirect_url=redirect_url,
                valid_from=valid_from,
                valid_until=valid_until
            )
            
            self.log_info(f"Banner updated: {banner_id}")
            return updated_banner
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to update banner")
