from __future__ import annotations

import os
import json
import base64
from typing import Dict, Any
from django.utils import timezone
from django.conf import settings

from api.common.services.base import BaseService
from api.user.notifications.models import SMS_FCMLog

class FCMService(BaseService):
    """Service for FCM (Firebase Cloud Messaging) operations"""
    
    def __init__(self):
        super().__init__()
        self._firebase_app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            import firebase_admin
            from firebase_admin import credentials
            
            # Check if Firebase is already initialized
            if firebase_admin._apps:
                self._firebase_app = firebase_admin.get_app()
                return
            
            # Initialize from credentials file
            if hasattr(settings, 'FIREBASE_CREDENTIALS_PATH') and settings.FIREBASE_CREDENTIALS_PATH:
                if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    self._firebase_app = firebase_admin.initialize_app(cred)
                    self.log_info("Firebase initialized from credentials file")
                    return
            
            # Initialize from base64 encoded credentials
            if hasattr(settings, 'FIREBASE_CREDENTIALS_BASE64') and settings.FIREBASE_CREDENTIALS_BASE64:
                try:
                    decoded_creds = base64.b64decode(settings.FIREBASE_CREDENTIALS_BASE64)
                    cred_dict = json.loads(decoded_creds)
                    cred = credentials.Certificate(cred_dict)
                    self._firebase_app = firebase_admin.initialize_app(cred)
                    self.log_info("Firebase initialized from base64 credentials")
                    return
                except Exception as e:
                    self.log_error(f"Failed to initialize Firebase from base64: {str(e)}")
            
            # Fallback: Log warning if no credentials found
            self.log_warning("No Firebase credentials found, FCM will not work in production")
            
        except ImportError:
            self.log_error("firebase-admin package not installed. Run: pip install firebase-admin")
        except Exception as e:
            self.log_error(f"Failed to initialize Firebase: {str(e)}")
    
    def send_push_notification(self, user, title: str, message: str, 
                             data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send push notification to user"""
        try:
            # Get user's active FCM tokens
            from api.user.auth.models import UserDevice
            
            devices = UserDevice.objects.filter(
                user=user,
                is_active=True,
                fcm_token__isnull=False
            )
            
            if not devices.exists():
                return {
                    'status': 'no_devices',
                    'message': 'No active devices found for user'
                }
            
            sent_count = 0
            failed_count = 0
            
            for device in devices:
                try:
                    # Log FCM attempt
                    fcm_log = SMS_FCMLog.objects.create(
                        user=user,
                        title=title,
                        message=message,
                        notification_type='fcm',
                        recipient=device.fcm_token,
                        status='pending'
                    )
                    
                    # Send FCM notification
                    success = self._send_fcm_message(device.fcm_token, title, message, data)
                    
                    if success:
                        fcm_log.status = 'sent'
                        fcm_log.sent_at = timezone.now()
                        fcm_log.response = 'FCM delivered successfully'
                        sent_count += 1
                    else:
                        fcm_log.status = 'failed'
                        fcm_log.response = 'FCM delivery failed'
                        failed_count += 1
                    
                    fcm_log.save(update_fields=['status', 'sent_at', 'response'])
                    
                except Exception as e:
                    failed_count += 1
                    self.log_error(f"FCM send failed for device {device.id}: {str(e)}")
            
            return {
                'status': 'sent',
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_devices': devices.count()
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to send push notification")
    
    def _send_fcm_message(self, fcm_token: str, title: str, message: str, 
                         data: Dict[str, Any] = None) -> bool:
        """Send FCM message to specific token"""
        try:
            if not self._firebase_app:
                self.log_warning("Firebase not initialized, using mock FCM response")
                return True  # Mock success for development
            
            from firebase_admin import messaging
            
            # Prepare data payload (FCM requires string values)
            string_data = {}
            if data:
                for key, value in data.items():
                    string_data[key] = str(value)
            
            # Create FCM message
            fcm_message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=message,
                ),
                data=string_data,
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#FF5722',
                        sound='default'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1
                        )
                    )
                )
            )
            
            # Send message
            response = messaging.send(fcm_message)
            self.log_info(f"FCM sent successfully: {response}")
            return True
            
        except Exception as e:
            self.log_error(f"FCM message send failed: {str(e)}")
            return False