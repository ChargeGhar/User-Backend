# api/partners/auth/services/auth_service.py
"""
Partner Authentication Service

Main authentication service that orchestrates:
- Login
- Token operations (delegates to TokenService)
- Profile retrieval

Based on partners_auth.md specification.
"""
from __future__ import annotations

import logging
from typing import Dict

from django.utils import timezone
from django.conf import settings

from api.common.services.base import BaseService, ServiceException
from api.partners.common.models import Partner
from api.partners.common.repositories import PartnerRepository
from .token_service import PartnerTokenService


logger = logging.getLogger(__name__)


class PartnerAuthService(BaseService):
    """
    Partner authentication service.
    
    Handles password-based authentication for Partner Dashboard
    (Franchise & Revenue Vendor).
    """
    
    def __init__(self):
        super().__init__()
        self.token_service = PartnerTokenService()
    
    def login(self, email: str, password: str) -> Dict:
        """
        Authenticate partner and return JWT tokens.
        
        Args:
            email: Partner's email address
            password: Partner's password
            
        Returns:
            Dict with access_token, refresh_token, and partner profile
            
        Raises:
            ServiceException: If credentials invalid or partner not active
        """
        from api.user.auth.models import User
        
        # Get user by email + is_partner flag
        user = User.objects.filter(
            email__iexact=email,
            is_partner=True,
            is_active=True
        ).first()
        
        if not user:
            raise ServiceException(
                detail="Invalid credentials",
                code="INVALID_CREDENTIALS"
            )
        
        # Get partner profile
        partner = PartnerRepository.get_by_user_id(user.id)
        if not partner:
            raise ServiceException(
                detail="Partner profile not found",
                code="NO_PARTNER_PROFILE"
            )
        
        # Check partner status
        if partner.status != Partner.Status.ACTIVE:
            raise ServiceException(
                detail=f"Partner account is {partner.status.lower()}",
                code="PARTNER_NOT_ACTIVE"
            )
        
        # Check dashboard access (BR9)
        if partner.partner_type == Partner.PartnerType.VENDOR:
            if partner.vendor_type == Partner.VendorType.NON_REVENUE:
                raise ServiceException(
                    detail="Non-revenue vendors do not have dashboard access",
                    code="NO_DASHBOARD_ACCESS"
                )
        
        # Verify password
        if not user.check_password(password):
            raise ServiceException(
                detail="Invalid credentials",
                code="INVALID_CREDENTIALS"
            )
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens
        tokens = self.token_service.generate_jwt_tokens(user)
        
        self.log_info(f"Partner login successful: {partner.code}")
        
        return {
            **tokens,
            "partner": self._serialize_partner(partner)
        }
    
    # Token operations - delegate to TokenService
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """Refresh JWT tokens."""
        return self.token_service.refresh_token(refresh_token)
    
    def logout(self, refresh_token: str) -> Dict:
        """Logout and blacklist token."""
        return self.token_service.blacklist_token(refresh_token)
    
    def generate_setup_token(self, partner: Partner) -> str:
        """Generate password setup token for new partner."""
        return self.token_service.generate_setup_token(partner)
    
    # Profile operations
    
    def get_current_partner(self, user) -> Dict:
        """
        Get current partner profile.
        
        Args:
            user: Authenticated user
            
        Returns:
            Dict with partner profile
            
        Raises:
            ServiceException: If partner not found
        """
        partner = PartnerRepository.get_by_user_id(user.id)
        if not partner:
            raise ServiceException(
                detail="Partner profile not found",
                code="PARTNER_NOT_FOUND"
            )
        return self._serialize_partner(partner)
    
    def send_invitation_email(self, partner: Partner, token: str) -> None:
        """
        Send invitation email with setup link.
        
        Args:
            partner: Partner instance
            token: Setup token
        """
        self._send_setup_email(partner, token)
    
    def _serialize_partner(self, partner: Partner) -> Dict:
        """Serialize partner for API response."""
        return {
            "id": str(partner.id),
            "partner_type": partner.partner_type,
            "vendor_type": partner.vendor_type,
            "code": partner.code,
            "business_name": partner.business_name,
            "contact_phone": partner.contact_phone,
            "contact_email": partner.contact_email,
            "status": partner.status,
            "balance": str(partner.balance),
            "total_earnings": str(partner.total_earnings),
        }
    
    def _send_setup_email(self, partner: Partner, token: str) -> None:
        """Send invitation email with password setup link."""
        try:
            from api.user.notifications.services import notify
            
            dashboard_url = getattr(settings, 'PARTNER_DASHBOARD_URL', 'https://partners.chargeghar.com')
            setup_url = f"{dashboard_url}/auth/setup/{token}"
            
            notify(
                user=partner.user,
                template_slug='partner_invitation',
                async_send=True,
                partner_name=partner.business_name,
                partner_type=partner.partner_type,
                partner_code=partner.code,
                setup_url=setup_url
            )
            
            self.log_info(f"Invitation email sent to partner: {partner.code}")
        except Exception as e:
            self.log_error(f"Failed to send invitation email: {str(e)}")
