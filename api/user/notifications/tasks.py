"""
🚀 Celery Tasks for Async Notifications
========================================

Background tasks for sending notifications asynchronously using Celery.
This ensures notifications don't block your main application flow.

Usage:
    # Send notification asynchronously
    from api.user.notifications.tasks import send_notification_task

    send_notification_task.delay(
        user_id=user.id,
        template_slug='rental_started',
        context={'powerbank_id': 'PB123'}
    )
"""

from __future__ import annotations

import logging
from typing import Dict, Any
from celery import shared_task
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    name="notifications.send_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
)
def send_notification_task(
    self, user_id: str, template_slug: str, context: Dict[str, Any] = None
):
    """
    Send notification asynchronously using Celery

    Args:
        user_id: User ID (UUID string)
        template_slug: Template slug (e.g., 'rental_started')
        context: Template variables (e.g., {'powerbank_id': 'PB123'})

    Example:
        send_notification_task.delay(
            user_id=str(user.id),
            template_slug='rental_started',
            context={'powerbank_id': 'PB123', 'station_name': 'Mall Road'}
        )
    """
    try:
        from api.user.notifications.services.notify import NotifyService

        # Get user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return {"status": "failed", "error": "User not found"}

        # Send notification
        notify_service = NotifyService()
        notification = notify_service.send(user, template_slug, **(context or {}))

        logger.info(f"Notification sent async: {template_slug} to {user.username}")
        return {
            "status": "success",
            "notification_id": str(notification.id),
            "user_id": user_id,
            "template_slug": template_slug,
        }

    except Exception as e:
        logger.error(f"Failed to send notification async: {str(e)}", exc_info=True)

        error_str = str(e)
        if 'ServiceException' in error_str or 'Template not found' in error_str:
            logger.error(f"Non-retryable error for notification: {template_slug} - {error_str}")
            return {"status": "failed", "error": error_str, "retryable": False}

        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for notification: {template_slug}")
            return {"status": "failed", "error": error_str}


@shared_task(name="notifications.send_bulk_notifications", bind=True, max_retries=2)
def send_bulk_notifications_task(
    self, user_ids: list, template_slug: str, context: Dict[str, Any] = None
):
    """
    Send bulk notifications asynchronously

    Args:
        user_ids: List of user IDs (UUID strings)
        template_slug: Template slug
        context: Template variables (same for all users)

    Example:
        user_ids = [str(user1.id), str(user2.id), str(user3.id)]
        send_bulk_notifications_task.delay(
            user_ids=user_ids,
            template_slug='special_offer',
            context={'offer_title': '50% Off', 'expiry_date': '2025-12-31'}
        )
    """
    try:
        from api.user.notifications.services.notify import NotifyService

        logger.info(
            f"Starting bulk notification: {template_slug} to {len(user_ids)} users"
        )

        notify_service = NotifyService()
        success_count = 0
        failure_count = 0

        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                notify_service.send(user, template_slug, **(context or {}))
                success_count += 1
            except User.DoesNotExist:
                logger.warning(f"User not found: {user_id}")
                failure_count += 1
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {str(e)}")
                failure_count += 1

        logger.info(
            f"Bulk notification completed: {success_count} success, {failure_count} failed"
        )
        return {
            "status": "completed",
            "success_count": success_count,
            "failure_count": failure_count,
            "total": len(user_ids),
        }

    except Exception as e:
        logger.error(f"Bulk notification failed: {str(e)}", exc_info=True)
        return {"status": "failed", "error": str(e)}


@shared_task(name="notifications.send_otp", bind=True, max_retries=3)
def send_otp_task(
    self,
    identifier: str,
    otp: str,
    purpose: str = "verification",
    expiry_minutes: int = 5,
):
    """
    Send OTP asynchronously - handles both existing and non-existing users

    Args:
        identifier: User identifier (UUID, email, or phone number)
        otp: OTP code
        purpose: Purpose of OTP (e.g., 'register', 'login')
        expiry_minutes: OTP expiry time in minutes

    Example:
        # For existing user (UUID)
        send_otp_task.delay(
            identifier=str(user.id),
            otp='123456',
            purpose='login',
            expiry_minutes=5
        )

        # For non-existing user (email/phone)
        send_otp_task.delay(
            identifier='newuser@example.com',
            otp='123456',
            purpose='register',
            expiry_minutes=5
        )
    """
    try:
        from api.user.notifications.models import NotificationTemplate
        from django.template import Template, Context

        # Determine if identifier is email or phone
        is_email = "@" in identifier
        template_slug = "otp_email" if is_email else "otp_sms"

        # Try to find existing user
        user = None
        try:
            # First try UUID lookup
            user = User.objects.get(id=identifier)
        except (User.DoesNotExist, ValueError):
            # Then try email/phone lookup
            try:
                if is_email:
                    user = User.objects.get(email=identifier)
                else:
                    user = User.objects.get(phone_number=identifier)
            except User.DoesNotExist:
                pass  # User doesn't exist, will handle below

        # Prepare context for template
        context = {
            "otp": otp,
            "purpose": purpose.lower(),
            "expiry_minutes": expiry_minutes,
            "identifier": identifier,
        }

        # Get template for rendering
        try:
            template = NotificationTemplate.objects.get(slug=template_slug)
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_slug}")
            return {"status": "failed", "error": f"Template not found: {template_slug}"}

        # Render message
        title_template = Template(template.title_template)
        message_template = Template(template.message_template)
        rendered_title = title_template.render(Context(context))
        rendered_message = message_template.render(Context(context))

        if user:
            # User exists - use full notification system
            from api.user.notifications.services.notify import NotifyService

            notify_service = NotifyService()
            notification = notify_service.send(user, template_slug, **context)

            logger.info(f"OTP sent to existing user: {user.username}")
            return {
                "status": "success",
                "notification_id": str(notification.id),
                "user_type": "existing",
                "identifier": identifier,
            }
        else:
            # User doesn't exist - send directly via channel services
            if is_email:
                # Send via email service
                from api.user.notifications.services.email import EmailService

                email_service = EmailService()

                # Add rendered message to context for HTML template
                email_context = context.copy()
                email_context["message"] = rendered_message

                result = email_service.send_email(
                    subject=rendered_title,
                    recipient_list=[identifier],
                    template_name="otp_email.html",
                    context=email_context,
                )
            else:
                # Send via SMS service
                from api.user.notifications.services.sms import SMSService

                sms_service = SMSService()
                result = sms_service.send_sms(
                    phone_number=identifier, message=rendered_message, user=None
                )

            logger.info(f"OTP sent to non-existing user: {identifier}")
            return {
                "status": "success",
                "notification_id": "otp_direct",
                "user_type": "non_existing",
                "identifier": identifier,
            }

    except Exception as e:
        logger.error(f"Failed to send OTP: {str(e)}", exc_info=True)

        # Retry task
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for OTP send to {identifier}")
            return {"status": "failed", "error": str(e)}


@shared_task(name="notifications.send_scheduled_notification", bind=True)
def send_scheduled_notification_task(
    self,
    user_id: str,
    template_slug: str,
    context: Dict[str, Any] = None,
    schedule_time: str = None,
):
    """
    Send scheduled notification (use with Celery Beat)

    Args:
        user_id: User ID
        template_slug: Template slug
        context: Template variables
        schedule_time: ISO format time (for logging)

    Example:
        # In your Celery Beat schedule:
        send_scheduled_notification_task.apply_async(
            args=[str(user.id), 'rental_reminder', {'powerbank_id': 'PB123'}],
            eta=datetime.now() + timedelta(hours=2)
        )
    """
    try:
        from api.user.notifications.services.notify import NotifyService

        # Get user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return {"status": "failed", "error": "User not found"}

        # Send notification
        notify_service = NotifyService()
        notification = notify_service.send(user, template_slug, **(context or {}))

        logger.info(f"Scheduled notification sent: {template_slug} to {user.username}")
        return {
            "status": "success",
            "notification_id": str(notification.id),
            "schedule_time": schedule_time,
        }

    except Exception as e:
        logger.error(f"Scheduled notification failed: {str(e)}", exc_info=True)
        return {"status": "failed", "error": str(e)}


@shared_task(name="notifications.cleanup_old_notifications", bind=True)
def cleanup_old_notifications_task(self, days: int = 90):
    """
    Clean up old read notifications (use with Celery Beat)

    Args:
        days: Delete read notifications older than this many days

    Example:
        # Run daily to clean up 90+ day old read notifications
        cleanup_old_notifications_task.delay(days=90)
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        from api.user.notifications.models import Notification

        cutoff_date = timezone.now() - timedelta(days=days)

        # Delete old read notifications
        deleted_count, _ = Notification.objects.filter(
            is_read=True, created_at__lt=cutoff_date
        ).delete()

        logger.info(
            f"Cleaned up {deleted_count} old notifications (older than {days} days)"
        )
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
        return {"status": "failed", "error": str(e)}


# Export all tasks
__all__ = [
    "send_notification_task",
    "send_bulk_notifications_task",
    "send_otp_task",
    "send_scheduled_notification_task",
    "cleanup_old_notifications_task",
]
