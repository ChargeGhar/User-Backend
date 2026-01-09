"""Verification token handler for managing 10-minute verification tokens"""
import uuid
from typing import Dict, Any
from django.core.cache import cache
from django.utils import timezone
from api.common.services.base import ServiceException


class VerificationTokenHandler:
    """Handles verification token generation and validation"""
    
    TOKEN_EXPIRY_MINUTES = 10
    
    @staticmethod
    def get_cache_key(token: str) -> str:
        """Get cache key for verification token"""
        return f"unified_verification:{token}"
    
    @classmethod
    def generate_token(cls, identifier: str, purpose: str) -> str:
        """Generate verification token"""
        verification_token = str(uuid.uuid4())
        token_key = cls.get_cache_key(verification_token)
        token_data = {
            'identifier': identifier,
            'purpose': purpose,
            'verified_at': timezone.now().isoformat()
        }
        cache.set(token_key, token_data, timeout=cls.TOKEN_EXPIRY_MINUTES * 60)
        return verification_token
    
    @classmethod
    def get_token_data(cls, token: str) -> Dict[str, Any]:
        """Get token data from cache"""
        token_key = cls.get_cache_key(token)
        token_data = cache.get(token_key)
        if not token_data:
            raise ServiceException(
                detail="Verification token expired or invalid",
                code="verification_token_expired",
                user_message="Verification session has expired. Please start over."
            )
        return token_data
    
    @classmethod
    def validate_token(cls, identifier: str, token: str) -> Dict[str, Any]:
        """Validate verification token and return token data"""
        token_data = cls.get_token_data(token)
        if token_data['identifier'] != identifier:
            raise ServiceException(
                detail="Identifier mismatch",
                code="identifier_mismatch",
                user_message="Invalid verification session. Please start over."
            )
        return token_data
    
    @classmethod
    def clear_token(cls, token: str) -> None:
        """Clear verification token from cache"""
        token_key = cls.get_cache_key(token)
        cache.delete(token_key)
