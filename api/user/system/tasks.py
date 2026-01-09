from __future__ import annotations

from celery import shared_task

from api.common.tasks.base import BaseTask


@shared_task(base=BaseTask, bind=True)
def send_app_update_notifications(self, version_id: str):
    """
    Send notifications about new app updates.

    Args:
        version_id: UUID of the AppVersion to notify about

    Returns:
        dict: Notification status and version details

    Example:
        send_app_update_notifications.delay(str(version.id))
    """
    try:
        from api.user.system.models import AppVersion
        from api.user.notifications.services import notify
        from django.contrib.auth import get_user_model

        User = get_user_model()
        version = AppVersion.objects.get(id=version_id)

        # Get active users for this platform
        # You might want to add device tracking to target specific platforms
        active_users = User.objects.filter(is_active=True)[
            :1000
        ]  # Limit to avoid overwhelming system

        notification_count = 0
        for user in active_users:
            try:
                # Send notification about app update
                notify(
                    user,
                    "app_update_available",
                    async_send=True,
                    version=version.version,
                    platform=version.platform,
                    is_mandatory=version.is_mandatory,
                )
                notification_count += 1
            except Exception as e:
                self.logger.error(f"Failed to notify user {user.id}: {str(e)}")

        self.logger.info(
            f"App update notifications sent for version {version.version} "
            f"({notification_count} users notified)"
        )

        return {
            "notifications_sent": notification_count,
            "version": version.version,
            "platform": version.platform,
            "is_mandatory": version.is_mandatory,
        }

    except AppVersion.DoesNotExist:
        self.logger.error(f"App version {version_id} not found")
        raise
    except Exception as e:
        self.logger.error(f"Failed to send app update notifications: {str(e)}")
        raise
