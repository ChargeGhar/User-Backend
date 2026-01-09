# Import services from their dedicated files
from .email import EmailService
from .fcm import FCMService
from .sms import SMSService
from .analytics import NotificationAnalyticsService

# Import the UNIVERSAL notification methods
from .notify import (
    NotifyService,
    notify,        # Universal sync/async notification
    notify_bulk,   # Universal bulk notification
    send_otp,      # Universal OTP sender
)

# Import legacy service for backward compatibility
from .notification import NotificationService

__all__ = [
    # Core services
    "NotifyService",
    "EmailService",
    "FCMService",
    "SMSService",
    "NotificationAnalyticsService",
    
    # Backward compatibility
    "NotificationService", 
    
    # UNIVERSAL METHODS - Just 3 methods for everything!
    "notify",       # notify(user, 'template', async_send=False, **context)
    "notify_bulk",  # notify_bulk(users, 'template', async_send=True, **context)
    "send_otp",     # send_otp(identifier, otp, purpose, async_send=True)
]