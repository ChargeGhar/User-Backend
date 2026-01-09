from __future__ import annotations

from typing import Dict, Any
from django.utils import timezone
from django.conf import settings

from api.common.services.base import BaseService
from api.user.notifications.models import SMS_FCMLog

class SMSService(BaseService):
    """Service for SMS operations via Sparrow SMS"""
    
    def send_sms(self, phone_number: str, message: str, user=None) -> Dict[str, Any]:
        """Send SMS to phone number"""
        try:
            # Format phone number (remove spaces, ensure country code)
            formatted_phone = self._format_phone_number(phone_number)
            
            # Log SMS attempt
            sms_log = SMS_FCMLog.objects.create(
                user=user,
                title="SMS",
                message=message,
                notification_type='sms',
                recipient=formatted_phone,
                status='pending'
            )
            
            # Send SMS via Sparrow SMS
            success, response_text = self._send_sms_message(formatted_phone, message)
            
            if success:
                sms_log.status = 'sent'
                sms_log.sent_at = timezone.now()
                sms_log.response = response_text or 'SMS sent successfully'
            else:
                sms_log.status = 'failed'
                sms_log.response = response_text or 'SMS delivery failed'
            
            sms_log.save(update_fields=['status', 'sent_at', 'response'])
            
            return {
                'status': 'sent' if success else 'failed',
                'sms_log_id': str(sms_log.id),
                'formatted_phone': formatted_phone,
                'response': response_text
            }
            
        except Exception as e:
            self.handle_service_error(e, "Failed to send SMS")
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for Nepal (add +977 if needed)"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Handle Nepal phone numbers
        if digits_only.startswith('977'):
            return f"+{digits_only}"
        elif digits_only.startswith('98') and len(digits_only) == 10:
            return f"+977{digits_only}"
        elif len(digits_only) == 10 and digits_only.startswith('9'):
            return f"+977{digits_only}"
        else:
            # Return as is for international numbers
            return f"+{digits_only}" if not digits_only.startswith('+') else digits_only
    
    def _send_sms_message(self, phone_number: str, message: str) -> tuple[bool, str]:
        """Send SMS message via Sparrow SMS provider"""
        try:
            import requests
            
            # Check if Sparrow SMS is configured
            if not hasattr(settings, 'SPARROW_SMS_TOKEN') or not settings.SPARROW_SMS_TOKEN:
                self.log_warning("Sparrow SMS not configured, using mock SMS response")
                return True, "Mock SMS sent (no token configured)"
            
            # Prepare Sparrow SMS API request
            self.log_info(f"Sending SMS via Sparrow SMS to {phone_number}")
            url = getattr(settings, 'SPARROW_SMS_BASE_URL', 'http://api.sparrowsms.com/v2/sms/')
            
            # Debug: Log the exact payload being sent
            sender_id = getattr(settings, 'SPARROW_SMS_FROM', 'ChargeGhar')
            self.log_info(f"SMS Payload - From: {sender_id}, To: {phone_number}, Message Length: {len(message)}")
            self.log_info(f"SMS Message: {message}")
            
            payload = {
                'token': settings.SPARROW_SMS_TOKEN,
                'from': sender_id,
                'to': phone_number,
                'text': message
            }
            
            # Send SMS request
            response = requests.post(
                url,
                data=payload,
                timeout=30
            )
            
            # Check response
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get('response_code') == 200:
                    self.log_info(f"SMS sent successfully to {phone_number}")
                    return True, f"SMS sent: {response_json.get('message', 'Success')}"
                else:
                    error_msg = response_json.get('message', 'Unknown error')
                    self.log_error(f"SMS failed for {phone_number}: {error_msg}")
                    return False, f"SMS failed: {error_msg}"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.log_error(f"SMS API error for {phone_number}: {error_msg}")
                return False, error_msg
            
        except requests.exceptions.Timeout:
            error_msg = "SMS request timeout"
            self.log_error(f"SMS timeout for {phone_number}")
            return False, error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"SMS request failed: {str(e)}"
            self.log_error(f"SMS request error for {phone_number}: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"SMS send failed: {str(e)}"
            self.log_error(f"SMS error for {phone_number}: {error_msg}")
            return False, error_msg