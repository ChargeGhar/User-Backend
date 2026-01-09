"""
Signature generation and validation for IoT system integration
Uses HMAC-SHA256 algorithm matching Java implementation
"""
from __future__ import annotations

import hmac
import hashlib
import base64
import time
from typing import Tuple
from django.conf import settings

from api.common.services.base import BaseService


class SignChargeGharMain(BaseService):
    """
    HMAC-SHA256 signature utilities for ChargeGhar IoT integration
    Follows project patterns with proper error handling and logging
    """
    
    def __init__(self, secret_key: str = None):
        """
        Initialize with secret key
        
        Args:
            secret_key: Shared secret for HMAC. If None, uses Django settings
        """
        super().__init__()
        self.secret_key = secret_key or getattr(settings, 'IOT_SYSTEM_SIGNATURE_SECRET', None)
        
        if not self.secret_key:
            raise ValueError("IOT_SYSTEM_SIGNATURE_SECRET not configured in settings")
    
    def generate_signature(self, payload: str, timestamp: int) -> str:
        """
        Generate HMAC-SHA256 signature for request
        
        Args:
            payload: JSON request body as string
            timestamp: Unix timestamp in seconds
            
        Returns:
            Base64 encoded signature string
            
        Raises:
            ValueError: If payload or timestamp is invalid
        """
        try:
            if not payload:
                raise ValueError("Payload cannot be empty")
            
            if not isinstance(timestamp, int) or timestamp <= 0:
                raise ValueError("Timestamp must be a positive integer")
            
            message = f"{payload}{timestamp}"
            
            signature = hmac.new(
                key=self.secret_key.encode('utf-8'),
                msg=message.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            
            encoded_signature = base64.b64encode(signature).decode('utf-8')
            
            self.log_info(f"Generated signature for payload length: {len(payload)}, timestamp: {timestamp}")
            return encoded_signature
            
        except Exception as e:
            self.log_error(f"Error generating signature: {str(e)}")
            raise ValueError(f"Signature generation failed: {str(e)}")
    
    def validate_signature(
        self, 
        payload: str, 
        timestamp: int, 
        received_signature: str,
        time_tolerance: int = 300  # 5 minutes
    ) -> Tuple[bool, str]:
        """
        Validate signature from request
        
        Args:
            payload: JSON request body as string
            timestamp: Timestamp from request header
            received_signature: Signature from X-Signature header
            time_tolerance: Maximum age of request in seconds (default 300s = 5min)
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            # Input validation
            if not payload:
                return False, "Payload cannot be empty"
            
            if not received_signature:
                return False, "Signature cannot be empty"
            
            if not isinstance(timestamp, int):
                return False, "Timestamp must be an integer"
            
            # Check timestamp freshness
            current_time = int(time.time())
            time_diff = abs(current_time - timestamp)
            
            if time_diff > time_tolerance:
                self.log_warning(f"Request timestamp too old: {time_diff}s > {time_tolerance}s allowed")
                return False, f"Request timestamp too old ({time_diff}s > {time_tolerance}s allowed)"
            
            # Compute expected signature
            try:
                expected_signature = self.generate_signature(payload, timestamp)
            except Exception as e:
                self.log_error(f"Error computing expected signature: {str(e)}")
                return False, f"Signature generation error: {str(e)}"
            
            # Compare signatures (timing-safe comparison)
            if not hmac.compare_digest(expected_signature, received_signature):
                self.log_warning(f"Signature mismatch for timestamp {timestamp}")
                return False, "Signature mismatch"
            
            self.log_info(f"Signature validation successful for timestamp {timestamp}")
            return True, ""
            
        except Exception as e:
            self.log_error(f"Error validating signature: {str(e)}")
            return False, f"Signature validation error: {str(e)}"
    
    @staticmethod
    def get_current_timestamp() -> int:
        """Get current Unix timestamp in seconds"""
        return int(time.time())


# Singleton instance following project patterns
_signature_util = None


def get_signature_util() -> SignChargeGharMain:
    """
    Get singleton signature utility instance
    Following project patterns for singleton services
    """
    global _signature_util
    if _signature_util is None:
        _signature_util = SignChargeGharMain()
    return _signature_util