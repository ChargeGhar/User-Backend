from typing import Optional, List
from django.utils import timezone
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
    
    # Biometric authentication methods
    
    @staticmethod
    def enable_biometric(device_id: str, biometric_token: str) -> UserDevice:
        """Enable biometric for device"""
        device = UserDevice.objects.select_for_update().get(
            device_id=device_id,
            is_active=True
        )
        device.biometric_enabled = True
        device.biometric_token = biometric_token
        device.biometric_registered_at = timezone.now()
        device.save(update_fields=[
            'biometric_enabled',
            'biometric_token',
            'biometric_registered_at'
        ])
        return device
    
    @staticmethod
    def disable_biometric(device_id: str) -> UserDevice:
        """Disable biometric for device"""
        device = UserDevice.objects.select_for_update().get(device_id=device_id)
        device.biometric_enabled = False
        device.biometric_token = None
        device.save(update_fields=['biometric_enabled', 'biometric_token'])
        return device
    
    @staticmethod
    def get_by_biometric_token(device_id: str, biometric_token: str) -> Optional[UserDevice]:
        """Get device by biometric credentials"""
        try:
            return UserDevice.objects.select_related('user').get(
                device_id=device_id,
                biometric_token=biometric_token,
                biometric_enabled=True,
                is_active=True
            )
        except UserDevice.DoesNotExist:
            return None
    
    @staticmethod
    def update_biometric_last_used(device_id: str):
        """Update biometric last used timestamp"""
        UserDevice.objects.filter(device_id=device_id).update(
            biometric_last_used_at=timezone.now(),
            last_used=timezone.now()
        )
