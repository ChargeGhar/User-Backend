# api/partners/auth/services/token_service.py
"""
Partner Token Service

Handles JWT token operations for partners:
- Token generation
- Token refresh with partner status validation
- Token blacklisting (logout)
- Setup token for initial password (admin-initiated)
"""
from __future__ import annotations

import uuid
import logging
from typing import Dict

from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from api.common.services.base import BaseService, ServiceException
from api.partners.common.models import Partner


logger = logging.getLogger(__name__)


class PartnerTokenService(BaseService):
    """
    Service for partner token operations.
    """
    
    # Token TTLs (in seconds)
    SETUP_TOKEN_TTL = 86400   # 24 hours
    
    # Redis key prefixes
    SETUP_TOKEN_PREFIX = "partner:setup:"
    
    def generate_jwt_tokens(self, user) -> Dict[str, str]:
        """
        Generate JWT access and refresh tokens for user.
        
        Args:
            user: User instance
            
        Returns:
            Dict with access_token and refresh_token
        """
        refresh = RefreshToken.for_user(user)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }
    
    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh JWT tokens with partner status check.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            Dict with new access_token and refresh_token
            
        Raises:
            ServiceException: If token invalid or partner not active
        """
        from api.user.auth.models import User
        
        try:
            old_refresh = RefreshToken(refresh_token)
            user_id = old_refresh['user_id']
        except TokenError:
            raise ServiceException(
                detail="Invalid refresh token",
                code="INVALID_TOKEN"
            )
        
        # Check user status
        user = User.objects.filter(
            id=user_id,
            is_partner=True,
            is_active=True
        ).first()
        
        if not user:
            raise ServiceException(
                detail="User not found or inactive",
                code="USER_INACTIVE"
            )
        
        # Check partner status
        partner = Partner.objects.filter(
            user=user,
            status=Partner.Status.ACTIVE
        ).first()
        
        if not partner:
            raise ServiceException(
                detail="Partner not active",
                code="PARTNER_NOT_ACTIVE"
            )
        
        # Generate new tokens
        new_refresh = RefreshToken.for_user(user)
        
        # Blacklist old token
        try:
            old_refresh.blacklist()
        except Exception:
            pass  # Token might already be blacklisted
        
        return {
            "access_token": str(new_refresh.access_token),
            "refresh_token": str(new_refresh)
        }
    
    def blacklist_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Blacklist refresh token (logout).
        
        Args:
            refresh_token: Token to blacklist
            
        Returns:
            Dict with success message
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass  # Token already invalid/blacklisted
        
        return {"message": "Logged out successfully"}
    
    def generate_setup_token(self, partner: Partner) -> str:
        """
        Generate password setup token for new partner.
        
        Called when admin creates a new partner. The partner receives
        an invitation email with this token to set their initial password.
        
        Args:
            partner: Partner instance
            
        Returns:
            UUID token string
        """
        token = str(uuid.uuid4())
        token_key = f"{self.SETUP_TOKEN_PREFIX}{token}"
        
        cache.set(
            token_key,
            {
                "partner_id": str(partner.id),
                "user_id": partner.user_id,
                "email": partner.contact_email or partner.user.email
            },
            timeout=self.SETUP_TOKEN_TTL
        )
        
        self.log_info(f"Setup token generated for partner: {partner.code}")
        return token
    
    def validate_setup_token(self, token: str) -> Dict:
        """
        Validate setup token and return token data.
        
        Args:
            token: UUID token string
            
        Returns:
            Token data dict
            
        Raises:
            ServiceException: If token invalid/expired
        """
        token_key = f"{self.SETUP_TOKEN_PREFIX}{token}"
        token_data = cache.get(token_key)
        
        if not token_data:
            raise ServiceException(
                detail="Invalid or expired setup token",
                code="INVALID_TOKEN"
            )
        
        return token_data
    
    def clear_setup_token(self, token: str) -> None:
        """Clear setup token after use."""
        token_key = f"{self.SETUP_TOKEN_PREFIX}{token}"
        cache.delete(token_key)
