"""
Biometric Authentication Service
=================================
Service for biometric authentication operations
"""
from __future__ import annotations
import logging
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from api.common.services.base import BaseService, ServiceException
from api.user.auth.models import User
from api.user.auth.repositories import DeviceRepository
from api.user.auth.services.account_service import AccountService

logger = logging.getLogger(__name__)


class BiometricAuthService(BaseService):
    """Service for biometric authentication operations"""
    
    def __init__(self):
        super().__init__()
        self.device_repo = DeviceRepository()
        self.account_service = AccountService()
    
    @transaction.atomic
    def enable_biometric(self, user: User, device_id: str, biometric_token: str) -> Dict[str, Any]:
        """Enable biometric authentication for device"""
        try:
            # Validate device belongs to user
            device = self.device_repo.get_by_device_id(device_id)
            if not device or device.user_id != user.id:
                raise ServiceException(
                    detail="Device not found or access denied",
                    code="device_not_found"
                )
            
            # Check if token already exists (uniqueness check)
            from api.user.auth.models import UserDevice
            if UserDevice.objects.filter(biometric_token=biometric_token).exists():
                raise ServiceException(
                    detail="Invalid biometric token",
                    code="invalid_token"
                )
            
            # Enable biometric
            device = self.device_repo.enable_biometric(device_id, biometric_token)
            
            self.log_info(
                f"Biometric enabled for user {user.username} on device {device_id}",
                extra={'user_id': str(user.id), 'device_id': device_id}
            )
            
            return {
                'message': 'Biometric authentication enabled successfully',
                'device_id': device.device_id,
                'enabled_at': device.biometric_registered_at.isoformat()
            }
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to enable biometric")

    
    @transaction.atomic
    def biometric_login(self, device_id: str, biometric_token: str, request=None) -> Dict[str, Any]:
        """Login using biometric authentication"""
        try:
            # Validate biometric credentials
            device = self.device_repo.get_by_biometric_token(device_id, biometric_token)
            if not device:
                raise ServiceException(
                    detail="Invalid biometric credentials",
                    code="invalid_biometric_credentials"
                )
            
            user = device.user
            
            # Check user status
            if not user.is_active or user.status != 'ACTIVE':
                raise ServiceException(
                    detail="Account is not active",
                    code="account_inactive"
                )
            
            # Update timestamps
            self.device_repo.update_biometric_last_used(device_id)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Log auth action
            if request:
                self.account_service.log_auth_action(user, 'BIOMETRIC_LOGIN', request)
            
            self.log_info(
                f"Biometric login successful for user {user.username}",
                extra={'user_id': str(user.id), 'device_id': device_id}
            )
            
            return {
                'message': 'Biometric login successful',
                'user': {
                    'id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'is_active': user.is_active
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Biometric login failed")
    
    @transaction.atomic
    def disable_biometric(self, user: User, device_id: str) -> Dict[str, Any]:
        """Disable biometric authentication for device"""
        try:
            # Validate device belongs to user
            device = self.device_repo.get_by_device_id(device_id)
            if not device or device.user_id != user.id:
                raise ServiceException(
                    detail="Device not found or access denied",
                    code="device_not_found"
                )
            
            # Disable biometric
            device = self.device_repo.disable_biometric(device_id)
            
            self.log_info(
                f"Biometric disabled for user {user.username} on device {device_id}",
                extra={'user_id': str(user.id), 'device_id': device_id}
            )
            
            return {
                'message': 'Biometric authentication disabled successfully',
                'device_id': device.device_id
            }
            
        except ServiceException:
            raise
        except Exception as e:
            self.handle_service_error(e, "Failed to disable biometric")
    
    def get_biometric_status(self, user: User, device_id: str) -> Dict[str, Any]:
        """Get biometric status for device"""
        try:
            device = self.device_repo.get_by_device_id(device_id)
            if not device or device.user_id != user.id:
                return {
                    'enabled': False,
                    'device_id': device_id,
                    'message': 'Device not found'
                }
            
            return {
                'enabled': device.biometric_enabled,
                'device_id': device.device_id,
                'registered_at': device.biometric_registered_at.isoformat() if device.biometric_registered_at else None,
                'last_used_at': device.biometric_last_used_at.isoformat() if device.biometric_last_used_at else None
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to get biometric status")
