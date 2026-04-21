from typing import Optional, List
from django.utils import timezone
from api.user.auth.models import UserDevice

class DeviceRepository:
    """Repository for UserDevice data operations"""

    @staticmethod
    def get_by_device_id(device_id: str) -> Optional[UserDevice]:
        """
        Returns the currently-active UserDevice row for this physical device.
        Since device_id is now unique per-user (not globally), there may be
        multiple rows for the same device_id (one per user who ever used it),
        but only one should ever be active at a time.
        """
        try:
            return UserDevice.objects.get(device_id=device_id, is_active=True)
        except UserDevice.DoesNotExist:
            return None
        except UserDevice.MultipleObjectsReturned:
            # Defensive fallback — return the most recently used active record
            return UserDevice.objects.filter(
                device_id=device_id, is_active=True
            ).order_by('-last_used').first()

    @staticmethod
    def get_user_devices(user_id: str) -> List[UserDevice]:
        return UserDevice.objects.filter(user_id=user_id, is_active=True)

    @staticmethod
    def create_or_update_device(user, device_id: str, **kwargs) -> UserDevice:
        """
        Register or refresh a device for `user`.

        If the same physical device_id was previously registered to a DIFFERENT
        user, that old row is deactivated and its biometric credentials are
        cleared.  This handles the "shared / handed-over phone" scenario:

          - The previous user's JWT tokens remain valid (they expire naturally
            or when that user explicitly calls /auth/logout).
          - Push notifications (FCM) will now be routed only to the new active
            user on this device.
          - Biometric for the previous user on this device is disabled —
            they must re-enable it if they ever use this device again.
        """
        # Lock and deactivate any rows for this device_id owned by a different user.
        # Using select_for_update() + individual save() keeps everything on the same
        # DB connection, which is required under PgBouncer transaction-pooling mode.
        stale_rows = UserDevice.objects.select_for_update().filter(
            device_id=device_id
        ).exclude(user=user)
        for stale in stale_rows:
            stale.is_active = False
            stale.biometric_enabled = False
            stale.biometric_token = None
            stale.save(update_fields=['is_active', 'biometric_enabled', 'biometric_token'])

        device, created = UserDevice.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults={**kwargs, 'is_active': True}  # always re-activate on register
        )
        return device

    @staticmethod
    def deactivate_device(device_id: str) -> bool:
        """Deactivate the currently-active row for this device."""
        updated = UserDevice.objects.filter(
            device_id=device_id, is_active=True
        ).update(is_active=False)
        return updated > 0

    # ── Biometric authentication methods ──────────────────────────────────────

    @staticmethod
    def enable_biometric(device_id: str, biometric_token: str) -> UserDevice:
        """Enable biometric for the active device."""
        # Scoped to is_active=True — only the current active owner can enable biometric
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
        """Disable biometric for the active device."""
        device = UserDevice.objects.select_for_update().get(
            device_id=device_id, is_active=True
        )
        device.biometric_enabled = False
        device.biometric_token = None
        device.save(update_fields=['biometric_enabled', 'biometric_token'])
        return device

    @staticmethod
    def get_by_biometric_token(device_id: str, biometric_token: str) -> Optional[UserDevice]:
        """
        Get device by biometric credentials.
        biometric_token retains its own global unique=True constraint, so this
        lookup is inherently safe — the token alone uniquely identifies the row.
        """
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
        """Update biometric last used timestamp on the active device."""
        UserDevice.objects.filter(device_id=device_id, is_active=True).update(
            biometric_last_used_at=timezone.now(),
            last_used=timezone.now()
        )
