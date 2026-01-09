from __future__ import annotations

from typing import List
from django.db import transaction
from api.common.services.base import BaseService, ServiceException
from api.user.content.repositories.contact_info_repository import ContactInfoRepository
from api.user.content.models import ContactInfo

class ContactInfoService(BaseService):
    """Service for contact information operations"""
    
    def get_all(self):
        """Get all contact info for admin"""
        try:
            return ContactInfoRepository.get_all()
        except Exception as e:
            self.handle_service_error(e, "Failed to get all contact info")
    
    def get_by_id(self, contact_id: str):
        """Get contact info by ID"""
        contact = ContactInfoRepository.get_by_id(contact_id)
        if not contact:
            raise ServiceException(
                detail="Contact info not found",
                code="contact_not_found"
            )
        return contact
    
    def delete_by_id(self, contact_id: str):
        """Delete contact info by ID"""
        try:
            contact_info = self.get_by_id(contact_id)
            ContactInfoRepository.delete(contact_info)
            self.log_info(f"Contact info deleted: {contact_id}")
            return True
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to delete contact info")
    
    def get_all_contact_info(self) -> List:
        """Get all active contact information"""
        try:
            contact_info = ContactInfoRepository.get_all_active()
            self.logger.debug(f"Found {len(contact_info)} active contact info records")
            return contact_info
        except Exception as e:
            self.handle_service_error(e, "Failed to get contact information")
    
    @transaction.atomic
    def update_contact_info(self, info_type: str, label: str, value: str, 
                          description: str, admin_user) -> ContactInfo:
        """Update contact information"""
        try:
            contact_info, created = ContactInfoRepository.get_or_create(
                info_type=info_type,
                defaults={
                    'label': label,
                    'value': value,
                    'description': description,
                    'updated_by': admin_user
                }
            )
            
            if not created:
                ContactInfoRepository.update(
                    contact_info,
                    label=label,
                    value=value,
                    description=description,
                    updated_by=admin_user
                )
            
            self.log_info(f"Contact info updated: {info_type}")
            return contact_info
            
        except Exception as e:
            self.handle_service_error(e, "Failed to update contact information")
