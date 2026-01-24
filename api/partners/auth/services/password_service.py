# api/partners/auth/services/password_service.py
"""
Partner Password Service

Handles password change for authenticated partners.
"""
from __future__ import annotations

import logging
from typing import Dict

from api.common.services.base import BaseService, ServiceException
from api.partners.common.repositories import PartnerRepository


logger = logging.getLogger(__name__)


class PartnerPasswordService(BaseService):
    """
    Service for partner password operations.
    """
    
    def change_password(self, user, current_password: str, new_password: str) -> Dict:
        """
        Change password for logged-in partner.
        
        Args:
            user: Current authenticated user
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            Dict with success message
            
        Raises:
            ServiceException: If current password is wrong
        """
        if not user.check_password(current_password):
            raise ServiceException(
                detail="Current password is incorrect",
                code="WRONG_PASSWORD"
            )
        
        user.set_password(new_password)
        user.save()
        
        partner = PartnerRepository.get_by_user_id(user.id)
        self.log_info(f"Password changed for partner: {partner.code if partner else user.id}")
        
        return {"message": "Password changed successfully"}
