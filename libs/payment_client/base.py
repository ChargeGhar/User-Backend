"""
Base Client for Payment Gateways
=================================

Provides core functionality:
- Configuration loading from Django settings
- Shared exception classes
- Amount conversion utilities

Designed for use with nepal-gateways package.
Date: 2026-01-10
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from decimal import Decimal

logger = logging.getLogger(__name__)


# ==========================================
# EXCEPTIONS
# ==========================================

class GatewayException(Exception):
    """Base exception for payment gateway errors"""
    
    def __init__(self, message: str, code: str = "gateway_error", context: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.context = context or {}
        super().__init__(message)


class ConfigurationError(GatewayException):
    """Raised when gateway configuration is invalid"""
    
    def __init__(self, message: str, gateway: str = ""):
        super().__init__(
            message, 
            code=f"{gateway}_config_error" if gateway else "config_error",
            context={'gateway': gateway}
        )


class InitiationError(GatewayException):
    """Raised when payment initiation fails"""
    
    def __init__(self, message: str, gateway: str = ""):
        super().__init__(
            message,
            code=f"{gateway}_initiation_error" if gateway else "initiation_error",
            context={'gateway': gateway}
        )


class VerificationError(GatewayException):
    """Raised when payment verification fails"""
    
    def __init__(self, message: str, gateway: str = ""):
        super().__init__(
            message,
            code=f"{gateway}_verification_error" if gateway else "verification_error",
            context={'gateway': gateway}
        )


class InvalidSignatureError(VerificationError):
    """Raised when payment signature validation fails"""
    
    def __init__(self, gateway: str = ""):
        super().__init__(
            "Payment signature validation failed",
            gateway=gateway
        )
        self.code = f"{gateway}_invalid_signature" if gateway else "invalid_signature"


# ==========================================
# BASE CLIENT
# ==========================================

class BaseGatewayClient(ABC):
    """
    Abstract base class for payment gateway clients
    
    Configuration:
        Can be configured via Django settings or constructor parameters.
        
        Django settings (NEPAL_GATEWAYS_CONFIG dict):
        - esewa: Dict with eSewa configuration
        - khalti: Dict with Khalti configuration
    
    Subclasses must implement:
        - gateway_name: Property returning gateway identifier
        - _get_client: Method to get underlying gateway client
        - initiate_payment: Method to initiate payment
        - verify_payment: Method to verify payment
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize gateway client
        
        Args:
            config: Gateway-specific configuration dict. If None, loads from Django settings.
        """
        self._config = config
        self._client = None
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    @property
    @abstractmethod
    def gateway_name(self) -> str:
        """Return gateway identifier (e.g., 'esewa', 'khalti')"""
        pass
    
    @abstractmethod
    def _get_client(self):
        """Get or create the underlying gateway client"""
        pass
    
    def _load_django_config(self) -> Dict[str, Any]:
        """Load configuration from Django settings if available"""
        try:
            from django.conf import settings
            full_config = getattr(settings, 'NEPAL_GATEWAYS_CONFIG', {})
            return full_config.get(self.gateway_name, {})
        except (ImportError, Exception):
            return {}
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get gateway configuration"""
        if self._config is None:
            self._config = self._load_django_config()
        return self._config
    
    @staticmethod
    def convert_to_paisa(amount: Decimal) -> int:
        """Convert NPR amount to paisa (for Khalti)"""
        return int(amount * 100)
    
    @staticmethod
    def convert_from_paisa(paisa: Union[int, float]) -> Decimal:
        """Convert paisa to NPR Decimal (for Khalti)"""
        return Decimal(str(paisa)) / 100
    
    @staticmethod
    def convert_to_npr_float(amount: Decimal) -> float:
        """Convert Decimal to float NPR (for eSewa)"""
        return float(amount)
    
    @staticmethod
    def convert_from_npr(amount: Union[float, int, str]) -> Decimal:
        """Convert NPR to Decimal (for eSewa)"""
        return Decimal(str(amount))


# ==========================================
# EXPORTS
# ==========================================

__all__ = [
    # Exceptions
    'GatewayException',
    'ConfigurationError',
    'InitiationError',
    'VerificationError',
    'InvalidSignatureError',
    # Base client
    'BaseGatewayClient',
]
