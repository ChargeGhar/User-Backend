"""OTP generation, validation, and caching handler"""
from typing import Dict, Any
from django.core.cache import cache
from api.common.utils.helpers import generate_random_code
from api.common.services.base import ServiceException


class OTPHandler:
    """Handles OTP generation, validation, and caching"""
    
    OTP_EXPIRY_MINUTES = 5
    MAX_OTP_ATTEMPTS = 999
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP"""
        return generate_random_code(6, include_letters=False, include_numbers=True)
    
    @staticmethod
    def get_cache_key(identifier: str) -> str:
        """Get unified cache key for OTP"""
        return f"unified_otp:{identifier}"
    
    @staticmethod
    def get_attempts_key(identifier: str) -> str:
        """Get cache key for OTP attempts"""
        return f"otp_attempts:{identifier}"
    
    @classmethod
    def check_rate_limit(cls, identifier: str) -> None:
        """Check if rate limit exceeded"""
        attempts_key = cls.get_attempts_key(identifier)
        attempts = cache.get(attempts_key, 0)
        if attempts >= cls.MAX_OTP_ATTEMPTS:
            raise ServiceException(
                detail="Too many OTP requests. Please try again later.",
                code="rate_limit_exceeded",
                user_message="You've made too many OTP requests. Please wait before trying again."
            )
    
    @classmethod
    def store_otp(cls, identifier: str, otp: str, purpose: str) -> None:
        """Store OTP in cache"""
        cache_key = cls.get_cache_key(identifier)
        otp_data = {
            'otp': otp,
            'purpose': purpose,
            'identifier': identifier
        }
        cache.set(cache_key, otp_data, timeout=cls.OTP_EXPIRY_MINUTES * 60)
        
        # Increment attempts
        attempts_key = cls.get_attempts_key(identifier)
        attempts = cache.get(attempts_key, 0)
        cache.set(attempts_key, attempts + 1, timeout=3600)  # 1 hour
    
    @classmethod
    def get_otp_data(cls, identifier: str) -> Dict[str, Any]:
        """Get OTP data from cache"""
        cache_key = cls.get_cache_key(identifier)
        otp_data = cache.get(cache_key)
        if not otp_data:
            raise ServiceException(
                detail="OTP expired or not found",
                code="otp_expired",
                user_message="OTP has expired. Please request a new one."
            )
        return otp_data
    
    @classmethod
    def validate_otp(cls, identifier: str, otp: str) -> str:
        """Validate OTP and return purpose"""
        otp_data = cls.get_otp_data(identifier)
        if otp_data['otp'] != otp:
            raise ServiceException(
                detail="Invalid OTP",
                code="invalid_otp",
                user_message="The OTP you entered is incorrect. Please try again."
            )
        return otp_data['purpose']
    
    @classmethod
    def clear_otp(cls, identifier: str) -> None:
        """Clear OTP from cache"""
        cache_key = cls.get_cache_key(identifier)
        cache.delete(cache_key)
