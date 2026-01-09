"""
🚀 NotifyService - Modern, Clean Notification System
====================================================

Simple, powerful notification system with:
- Template-based notifications
- Auto channel distribution based on rules
- Django template engine support
- Clean, one-line API

Example Usage:
    from api.user.notifications.services import notify
    
    # Simple one-liner
    notify(user, 'rental_started', powerbank_id='PB123', station_name='Mall Road')
    
    # That's it! The system handles:
    # - Template lookup
    # - Variable substitution
    # - Channel distribution (in-app, push, SMS, email)
    # - Rule-based delivery
"""
from __future__ import annotations

from typing import Dict, Any
from django.template import Template, Context
from django.db import transaction
from django.contrib.auth import get_user_model

from api.common.services.base import BaseService, ServiceException
from api.user.notifications.models import (
    Notification, NotificationTemplate, NotificationRule
)

User = get_user_model()


class NotifyService(BaseService):
    """
    Clean notification service with template support
    
    This is the core service that powers all notifications.
    Use the helper functions below for even cleaner code.
    """
    
    def __init__(self):
        super().__init__()
        self._email_service = None
        self._fcm_service = None
        self._sms_service = None
    
    @property
    def email_service(self):
        """Lazy load email service"""
        if self._email_service is None:
            from api.user.notifications.services.email import EmailService
            self._email_service = EmailService()
        return self._email_service
    
    @property
    def fcm_service(self):
        """Lazy load FCM service"""
        if self._fcm_service is None:
            from api.user.notifications.services.fcm import FCMService
            self._fcm_service = FCMService()
        return self._fcm_service
    
    @property
    def sms_service(self):
        """Lazy load SMS service"""
        if self._sms_service is None:
            from api.user.notifications.services.sms import SMSService
            self._sms_service = SMSService()
        return self._sms_service
    
    @transaction.atomic
    def send(self, user, template_slug: str, **context) -> Notification:
        """
        Send notification using template
        
        Args:
            user: User object to send notification to
            template_slug: Template slug (e.g., 'rental_started')
            **context: Template variables (e.g., powerbank_id='PB123')
        
        Returns:
            Notification object
        
        Example:
            notify_service.send(user, 'rental_started', 
                               powerbank_id='PB123', 
                               station_name='Mall Road')
        """
        try:
            # Get template
            template = self._get_template(template_slug)
            
            # Render title and message
            title = self._render_template(template.title_template, context)
            message = self._render_template(template.message_template, context)
            
            # Create in-app notification
            notification = Notification.objects.create(
                user=user,
                template=template,
                title=title,
                message=message,
                notification_type=template.notification_type,
                data=context,
                channel='in_app'
            )
            
            # Get notification rules and distribute to channels
            self._distribute_channels(user, title, message, template.notification_type, context)
            
            self.log_info(f"Notification sent to {user.username}: {template_slug}")
            return notification
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to send notification: {template_slug}")
    
    def send_bulk(self, users: list, template_slug: str, **context) -> Dict[str, Any]:
        """
        Send notification to multiple users
        
        Args:
            users: List of User objects
            template_slug: Template slug
            **context: Template variables
        
        Returns:
            Dict with success/failure counts
        
        Example:
            notify_service.send_bulk([user1, user2], 'special_offer', 
                                    offer_title='50% Off!')
        """
        try:
            success_count = 0
            failure_count = 0
            
            for user in users:
                try:
                    self.send(user, template_slug, **context)
                    success_count += 1
                except Exception as e:
                    failure_count += 1
                    self.log_error(f"Failed to send to {user.username}: {str(e)}")
            
            return {
                'success_count': success_count,
                'failure_count': failure_count,
                'total': len(users)
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to send bulk notifications")
    
    def send_otp(self, user, otp: str, purpose: str = 'verification', 
                 channel: str = 'sms', expiry_minutes: int = 5) -> Dict[str, Any]:
        """
        Send OTP via SMS or Email
        
        Args:
            user: User object
            otp: OTP code
            purpose: Purpose of OTP (verification, login, etc.)
            channel: 'sms' or 'email'
            expiry_minutes: OTP validity in minutes
        
        Returns:
            Dict with status
        
        Example:
            notify_service.send_otp(user, '123456', purpose='login', channel='sms')
        """
        try:
            template_slug = 'otp_sms' if channel == 'sms' else 'otp_email'
            
            # Get template
            template = self._get_template(template_slug)
            
            # Render message
            context = {
                'otp': otp,
                'purpose': purpose,
                'expiry_minutes': expiry_minutes
            }
            title = self._render_template(template.title_template, context)
            message = self._render_template(template.message_template, context)
            
            # Send via appropriate channel
            if channel == 'sms':
                phone_number = getattr(user, 'phone_number', None)
                if not phone_number:
                    raise ServiceException("User has no phone number")
                
                result = self.sms_service.send_sms(phone_number, message, user)
                return result
            
            elif channel == 'email':
                email = getattr(user, 'email', None)
                if not email:
                    raise ServiceException("User has no email")
                
                # Use OTP email template
                self.email_service.send_email(
                    subject=title,
                    recipient_list=[email],
                    template_name='otp_email.html',
                    context=context
                )
                return {'status': 'sent', 'channel': 'email'}
            
            else:
                raise ServiceException(f"Invalid OTP channel: {channel}")
            
        except Exception as e:
            self.handle_service_error(e, f"Failed to send OTP via {channel}")
    
    def send_custom(self, user, title: str, message: str, 
                   notification_type: str = 'system', 
                   channels: list = None) -> Notification:
        """
        Send custom notification without template
        
        Args:
            user: User object
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            channels: List of channels to send to (e.g., ['in_app', 'push'])
        
        Returns:
            Notification object
        
        Example:
            notify_service.send_custom(user, 
                                      'Alert', 
                                      'Your account needs attention',
                                      channels=['in_app', 'push'])
        """
        try:
            # Create in-app notification
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                data={},
                channel='in_app'
            )
            
            # Send to additional channels if specified
            if channels:
                for channel in channels:
                    if channel == 'push':
                        self._send_push(user, title, message, {})
                    elif channel == 'sms':
                        self._send_sms(user, message)
                    elif channel == 'email':
                        self._send_email(user, title, message, {})
            else:
                # Use rules for channel distribution
                self._distribute_channels(user, title, message, notification_type, {})
            
            return notification
            
        except Exception as e:
            self.handle_service_error(e, "Failed to send custom notification")
    
    # ===================================================================
    # PRIVATE HELPER METHODS
    # ===================================================================
    
    def _get_template(self, template_slug: str) -> NotificationTemplate:
        """Get notification template by slug"""
        try:
            template = NotificationTemplate.objects.get(
                slug=template_slug,
                is_active=True
            )
            return template
        except NotificationTemplate.DoesNotExist:
            raise ServiceException(f"Template not found: {template_slug}")
    
    def _render_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render Django template string with context"""
        try:
            template = Template(template_string)
            rendered = template.render(Context(context))
            return rendered.strip()
        except Exception as e:
            self.log_error(f"Template rendering failed: {str(e)}")
            return template_string  # Return unrendered template as fallback
    
    def _distribute_channels(self, user, title: str, message: str, 
                            notification_type: str, data: Dict[str, Any]):
        """Distribute notification to channels based on rules"""
        try:
            # Get notification rule for this type
            try:
                rule = NotificationRule.objects.get(notification_type=notification_type)
            except NotificationRule.DoesNotExist:
                # No rule found, only send in-app (already created)
                self.log_warning(f"No rule found for {notification_type}, only in-app sent")
                return
            
            # Send to channels based on rules
            if rule.send_push:
                self._send_push(user, title, message, data)
            
            if rule.send_sms:
                self._send_sms(user, message)
            
            if rule.send_email:
                self._send_email(user, title, message, data)
            
        except Exception as e:
            self.log_error(f"Channel distribution failed: {str(e)}")
    
    def _send_push(self, user, title: str, message: str, data: Dict[str, Any]):
        """Send push notification via FCM"""
        try:
            self.fcm_service.send_push_notification(user, title, message, data)
        except Exception as e:
            self.log_error(f"Push notification failed: {str(e)}")
    
    def _send_sms(self, user, message: str):
        """Send SMS notification"""
        try:
            phone_number = getattr(user, 'phone_number', None)
            if phone_number:
                self.sms_service.send_sms(phone_number, message, user)
            else:
                self.log_warning(f"User {user.username} has no phone number")
        except Exception as e:
            self.log_error(f"SMS notification failed: {str(e)}")
    
    def _send_email(self, user, title: str, message: str, data: Dict[str, Any]):
        """Send email notification"""
        try:
            email = getattr(user, 'email', None)
            if email:
                self.email_service.send_email(
                    subject=title,
                    recipient_list=[email],
                    template_name='notifications/generic_notification_email.html',
                    context={'title': title, 'message': message, **data}
                )
            else:
                self.log_warning(f"User {user.username} has no email")
        except Exception as e:
            self.log_error(f"Email notification failed: {str(e)}")


# ===================================================================
# UNIVERSAL NOTIFICATION API - TWO METHODS FOR ALL SCENARIOS
# ===================================================================

# Initialize service instance
_notify_service = NotifyService()

def notify(user, template_slug: str, async_send: bool = False, **context):
    """
    🚀 Universal notification sender - Works for ALL scenarios
    
    Args:
        user: User object or user_id (str) for async
        template_slug: Template slug (e.g., 'rental_started', 'payment_success')
        async_send: If True, sends via Celery (non-blocking). If False, sends immediately.
        **context: Template variables (e.g., powerbank_id='PB123', amount=100)
    
    Returns:
        - If async_send=False: Returns Notification object
        - If async_send=True: Returns Celery task result
    
    Examples:
        # Sync (immediate, blocking) - Use for critical notifications
        notify(user, 'payment_success', amount=100, gateway='eSewa')
        notify(user, 'otp_sms', otp='123456', purpose='login')
        
        # Async (background, non-blocking) - Use for non-critical notifications
        notify(user, 'rental_started', async_send=True, 
               powerbank_id='PB123', station_name='Mall Road')
        notify(user, 'special_offer', async_send=True, discount='50%')
        
        # Works for ALL templates - rental, payment, system, promotion, etc.
        notify(user, 'points_earned', points=50, reason='Completed rental')
        notify(user, 'kyc_status_update', kyc_status='approved')
        notify(user, 'wallet_recharged', amount=500, new_balance=1200)
    """
    if async_send:
        # Import here to avoid circular imports
        from api.user.notifications.tasks import send_notification_task
        
        # Convert user to user_id if needed
        user_id = str(user.id) if hasattr(user, 'id') else str(user)
        
        # Send async via Celery
        return send_notification_task.delay(
            user_id=user_id,
            template_slug=template_slug,
            context=context
        )
    else:
        # Send sync (immediate)
        return _notify_service.send(user, template_slug, **context)

def notify_bulk(users: list, template_slug: str, async_send: bool = True, **context):
    """
    🚀 Universal bulk notification sender - Send to multiple users
    
    Args:
        users: List of User objects or user IDs
        template_slug: Template slug
        async_send: If True (recommended), sends via Celery. If False, sends sync.
        **context: Template variables (same for all users)
    
    Returns:
        - If async_send=False: Dict with success/failure counts
        - If async_send=True: Celery task result
    
    Examples:
        # Async bulk (recommended for large lists)
        users = User.objects.filter(is_active=True)
        notify_bulk(users, 'special_offer', async_send=True, 
                   offer_title='50% Off', code='WEEKEND50')
        
        # Sync bulk (for small lists or immediate confirmation)
        notify_bulk([user1, user2, user3], 'maintenance_notice',
                   async_send=False, maintenance_date='2025-10-20')
    """
    if async_send:
        # Import here to avoid circular imports
        from api.user.notifications.tasks import send_bulk_notifications_task
        
        # Convert users to user_ids
        user_ids = [str(u.id) if hasattr(u, 'id') else str(u) for u in users]
        
        # Send async via Celery
        return send_bulk_notifications_task.delay(
            user_ids=user_ids,
            template_slug=template_slug,
            context=context
        )
    else:
        # Send sync (immediate)
        return _notify_service.send_bulk(users, template_slug, **context)


def send_otp(identifier: str, otp: str, purpose: str = 'verification', 
             expiry_minutes: int = 5, async_send: bool = True):
    """
    🚀 Universal OTP sender - Handles both existing and non-existing users
    
    Args:
        identifier: User identifier (UUID, email, or phone number)
        otp: OTP code
        purpose: Purpose of OTP (e.g., 'register', 'login')
        expiry_minutes: OTP expiry time in minutes
        async_send: If True (recommended), sends via Celery. If False, sends sync.
    
    Returns:
        - If async_send=False: Dict with status and details
        - If async_send=True: Celery task result
    
    Examples:
        # For registration (user doesn't exist yet)
        send_otp('newuser@example.com', '123456', 'register', async_send=True)
        send_otp('+1234567890', '654321', 'register', async_send=True)
        
        # For login (user exists)
        send_otp(str(user.id), '789012', 'login', async_send=True)
        send_otp('existing@example.com', '345678', 'login', async_send=True)
        
        # Sync sending (immediate, blocking)
        result = send_otp('user@example.com', '111222', 'login', async_send=False)
    """
    if async_send:
        # Import here to avoid circular imports
        from api.user.notifications.tasks import send_otp_task
        
        # Send async via Celery
        return send_otp_task.delay(
            identifier=identifier,
            otp=otp,
            purpose=purpose,
            expiry_minutes=expiry_minutes
        )
    else:
        # Send sync (immediate) - call the task function directly
        from api.user.notifications.tasks import send_otp_task
        
        # Create a mock task instance for sync execution
        class MockTask:
            def retry(self, exc):
                raise exc
            
            class MaxRetriesExceededError(Exception):
                pass
        
        mock_task = MockTask()
        return send_otp_task(mock_task, identifier, otp, purpose, expiry_minutes)


# Export the universal methods
__all__ = [
    'NotifyService',
    'notify',        # Universal sync/async notification
    'notify_bulk',   # Universal bulk notification
    'send_otp',      # Universal OTP sender
]
