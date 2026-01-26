from __future__ import annotations
from typing import Dict, Any, List
from django.db import transaction
from api.common.services.base import BaseService
from api.user.auth.models import User, UserDevice
from api.user.auth.repositories import DeviceRepository

class UserDeviceService(BaseService):
    """Service for device management"""
    
    def __init__(self):
        super().__init__()
        self.device_repo = DeviceRepository()
    
    def _serialize_device(self, device: UserDevice) -> Dict[str, Any]:
        """Serialize device model to dictionary"""
        return {
            'id': str(device.id),
            'device_id': device.device_id,
            'fcm_token': device.fcm_token,
            'device_type': device.device_type,
            'device_name': device.device_name,
            'app_version': device.app_version,
            'os_version': device.os_version,
            'is_active': device.is_active,
            'last_used': device.last_used.isoformat() if device.last_used else None,
            'biometric_enabled': device.biometric_enabled,
        }
    
    @transaction.atomic
    def register_device(self, user: User, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register or update user device"""
        try:
            device = self.device_repo.create_or_update_device(
                user=user,
                device_id=validated_data['device_id'],
                **{k: v for k, v in validated_data.items() if k != 'device_id'}
            )
            
            self.log_info(f"Device registered for user: {user.username}")
            return self._serialize_device(device)
            
        except Exception as e:
            self.handle_service_error(e, "Failed to register device")

    def get_user_devices(self, user: User) -> List[Dict[str, Any]]:
        """Get all active devices for user"""
        devices = self.device_repo.get_user_devices(user.id)
        return [self._serialize_device(device) for device in devices]

    def deactivate_device(self, device_id: str) -> bool:
        """Deactivate a device"""
        return self.device_repo.deactivate_device(device_id)
