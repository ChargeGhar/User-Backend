from typing import Optional, List
from api.user.auth.models import UserDevice

class DeviceRepository:
    """Repository for UserDevice data operations"""
    
    @staticmethod
    def get_by_device_id(device_id: str) -> Optional[UserDevice]:
        try:
            return UserDevice.objects.get(device_id=device_id)
        except UserDevice.DoesNotExist:
            return None

    @staticmethod
    def get_user_devices(user_id: str) -> List[UserDevice]:
        return UserDevice.objects.filter(user_id=user_id, is_active=True)

    @staticmethod
    def create_or_update_device(user, device_id: str, **kwargs) -> UserDevice:
        device, created = UserDevice.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults=kwargs
        )
        return device

    @staticmethod
    def deactivate_device(device_id: str) -> bool:
        device = DeviceRepository.get_by_device_id(device_id)
        if device:
            device.is_active = False
            device.save(update_fields=['is_active'])
            return True
        return False
