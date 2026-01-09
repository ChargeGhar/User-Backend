from __future__ import annotations
from typing import Dict, Any
from django.db import transaction
from api.common.services.base import BaseService
from api.user.auth.models import User, UserDevice
from api.user.auth.repositories import DeviceRepository

class UserDeviceService(BaseService):
    """Service for device management"""
    
    def __init__(self):
        super().__init__()
        self.device_repo = DeviceRepository()
    
    @transaction.atomic
    def register_device(self, user: User, validated_data: Dict[str, Any]) -> UserDevice:
        """Register or update user device"""
        try:
            device = self.device_repo.create_or_update_device(
                user=user,
                device_id=validated_data['device_id'],
                **{k: v for k, v in validated_data.items() if k != 'device_id'}
            )
            
            self.log_info(f"Device registered for user: {user.username}")
            return device
            
        except Exception as e:
            self.handle_service_error(e, "Failed to register device")

    def get_user_devices(self, user: User):
        """Get all active devices for user"""
        return self.device_repo.get_user_devices(user.id)

    def deactivate_device(self, device_id: str) -> bool:
        """Deactivate a device"""
        return self.device_repo.deactivate_device(device_id)
