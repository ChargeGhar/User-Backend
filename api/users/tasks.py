from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from api.common.tasks.base import BaseTask, NotificationTask
from api.system.models.audit import AuditLog as UserAuditLog

User = get_user_model()


@shared_task(base=BaseTask, bind=True)
def cleanup_expired_audit_logs(self):
    """
    Clean up old audit logs (older than 1 year).

    SCHEDULED: Runs daily via Celery Beat.
    Removes audit logs to maintain database hygiene.

    Returns:
        dict: Number of deleted records
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=365)
        deleted_count, _ = UserAuditLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        self.logger.info(f"Cleaned up {deleted_count} expired audit logs")
        return {"deleted_count": deleted_count}

    except Exception as e:
        self.logger.error(f"Failed to cleanup audit logs: {str(e)}")
        raise


@shared_task(base=BaseTask, bind=True)
def deactivate_inactive_users(self):
    """
    Deactivate users who haven't logged in for 6 months.

    SCHEDULED: Runs daily via Celery Beat.
    Sets user status to INACTIVE and sends notification.

    Returns:
        dict: Number of deactivated users
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=180)

        inactive_users = User.objects.filter(last_login__lt=cutoff_date, status="ACTIVE")

        updated_count = 0
        for user in inactive_users:
            user.status = "INACTIVE"
            user.save(update_fields=["status"])
            updated_count += 1

            # Send notification about account deactivation
            try:
                from api.notifications.services import notify

                notify(
                    user,
                    "account_deactivated",
                    async_send=True,
                    inactive_days=180,
                    reactivation_url="/reactivate",
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to send deactivation notification to {user.id}: {str(e)}"
                )

        self.logger.info(f"Deactivated {updated_count} inactive users")
        return {"deactivated_count": updated_count}

    except Exception as e:
        self.logger.error(f"Failed to deactivate inactive users: {str(e)}")
        raise


@shared_task(base=NotificationTask, bind=True)
def send_social_auth_welcome_message(self, user_id: str, provider: str):
    """
    Send welcome message for social auth users.

    ACTIVELY USED: Called when user signs up via Google/Apple.

    Args:
        user_id: UUID of the user
        provider: Social provider (google, apple, etc.)

    Returns:
        dict: Status of notification sent
    """
    try:
        user = User.objects.get(id=user_id)

        # Send welcome notification using notify service
        from api.notifications.services import notify

        notify(
            user,
            "social_auth_welcome",
            async_send=False,  # Send immediately
            provider=provider.title(),
            signup_method="social",
        )

        self.logger.info(
            f"Social auth welcome message sent to user: {user.username} via {provider}"
        )
        return {"status": "welcome_sent", "user_id": user_id, "provider": provider}

    except User.DoesNotExist:
        self.logger.error(f"User not found: {user_id}")
        raise
    except Exception as e:
        self.logger.error(f"Failed to send social auth welcome message: {str(e)}")
        raise
