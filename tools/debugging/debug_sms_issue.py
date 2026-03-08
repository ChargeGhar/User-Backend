#!/usr/bin/env python3
"""
Debug SMS Issue - Test exact Sparrow SMS API call
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.template import Template, Context
from api.notifications.models import NotificationTemplate
import requests

def debug_sms_issue():
    """Debug the exact SMS issue with Sparrow SMS"""
    
    print("🔍 DEBUGGING SMS ISSUE")
    print("=" * 50)
    
    # 1. Check SMS Settings
    print("📋 Current SMS Configuration:")
    token = getattr(settings, 'SPARROW_SMS_TOKEN', 'NOT SET')
    sender = getattr(settings, 'SPARROW_SMS_FROM', 'NOT SET')
    url = getattr(settings, 'SPARROW_SMS_BASE_URL', 'NOT SET')
    
    print(f"   Token: {token[:15]}..." if token != 'NOT SET' else "   Token: NOT SET")
    print(f"   From: {sender}")
    print(f"   URL: {url}")
    print()
    
    # 2. Check Template
    try:
        template = NotificationTemplate.objects.get(slug='otp_sms')
        print("📝 Template Found:")
        print(f"   Name: {template.name}")
        print(f"   Message: {template.message_template}")
        print()
        
        # 3. Render Test Message
        context = {
            'otp': '123456',
            'purpose': 'register',
            'expiry_minutes': 5,
            'identifier': '9866214494'
        }
        
        message_template = Template(template.message_template)
        rendered_message = message_template.render(Context(context))
        
        print("📄 Rendered Message:")
        print(f"   Text: '{rendered_message}'")
        print(f"   Length: {len(rendered_message)} chars")
        print()
        
        # 4. Test Phone Number Formatting
        from api.notifications.services.sms import SMSService
        sms_service = SMSService()
        
        test_numbers = [
            '9866214494',
            '+9779866214494', 
            '9779866214494',
            '01-9866214494'
        ]
        
        print(f"📱 Phone Formatting Tests:")
        for test_num in test_numbers:
            formatted = sms_service._format_phone_number(test_num)
            print(f"   Input: {test_num} → Output: {formatted}")
        print()
        
        # Test what format to actually send
        formatted_phone = sms_service._format_phone_number('9866214494')
        
        # According to docs: "10-digit mobile numbers"
        # Let's test both formats
        phone_formats_to_test = [
            formatted_phone,  # Our current format: +9779866214494
            '9866214494',     # Just 10 digits as per docs
            '9779866214494'   # 13 digits with country code but no +
        ]
        
        print(f"📋 Phone formats to test against API:")
        for i, phone in enumerate(phone_formats_to_test, 1):
            print(f"   Format {i}: {phone} ({len(phone)} chars)")
        print()
        
        # 5. Test Different Phone Number Formats
        if token != 'NOT SET' and sender != 'NOT SET':
            print("🚀 Testing Different Phone Number Formats:")
            
            for i, phone_format in enumerate(phone_formats_to_test, 1):
                print(f"\n   📞 Test {i}: {phone_format}")
                
                payload = {
                    'token': token,
                    'from': sender,
                    'to': phone_format,
                    'text': rendered_message
                }
                
                try:
                    response = requests.post(url, data=payload, timeout=10)
                    print(f"      Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            response_json = response.json()
                            response_code = response_json.get('response_code')
                            response_msg = response_json.get('response', 'Unknown')
                            
                            if response_code == 200:
                                print(f"      ✅ SUCCESS: {response_msg}")
                                break  # Found working format
                            else:
                                print(f"      ❌ Error {response_code}: {response_msg}")
                        except:
                            print(f"      ⚠️ Non-JSON response: {response.text}")
                    else:
                        print(f"      ❌ HTTP {response.status_code}: {response.text}")
                        
                except requests.exceptions.Timeout:
                    print("      ❌ Request timeout")
                except requests.exceptions.RequestException as e:
                    print(f"      ❌ Request failed: {e}")
                except Exception as e:
                    print(f"      ❌ Unexpected error: {e}")
        else:
            print("⚠️ SMS not configured - skipping API test")
        
    except NotificationTemplate.DoesNotExist:
        print("❌ otp_sms template not found in database!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sms_issue()