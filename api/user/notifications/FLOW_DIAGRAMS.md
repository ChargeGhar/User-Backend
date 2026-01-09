# 🔄 NOTIFICATION SYSTEM - VISUAL FLOW DIAGRAMS
## Complete Implementation Flow Analysis

**Date:** October 15, 2025  
**Version:** 2.0 (Simplified Universal API)

---

## 📊 ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION CODE                         │
│  (Views, APIs, Services, Business Logic)                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Import & Call
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              UNIVERSAL NOTIFICATION API                          │
│                                                                  │
│  from api.notifications.services import notify, notify_bulk     │
│                                                                  │
│  notify(user, 'template_slug', async_send=False, **context)    │
│  notify_bulk(users, 'template_slug', async_send=True, **ctx)   │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    async_send=False        async_send=True
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────────┐
│  SYNC FLOW      │    │   ASYNC FLOW         │
│  (Immediate)    │    │   (Celery Queue)     │
└────────┬────────┘    └──────────┬───────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────────┐
│         NotifyService (Core Engine)             │
│                                                 │
│  • Template lookup & rendering                  │
│  • Database notification creation               │
│  • Multi-channel distribution                   │
└────────────┬────────────────────────────────────┘
             │
             ├──────────┬──────────┬──────────┐
             ▼          ▼          ▼          ▼
      ┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
      │ In-App   │ │  Push  │ │  SMS   │ │  Email  │
      │ (Always) │ │ (FCM)  │ │(Sparrow)│ │ (SMTP) │
      └──────────┘ └────────┘ └────────┘ └─────────┘
           │            │          │           │
           ▼            ▼          ▼           ▼
      ┌──────────────────────────────────────────┐
      │         User Receives Notification        │
      └──────────────────────────────────────────┘
```

---

## 🔄 FLOW 1: SYNCHRONOUS NOTIFICATION (Immediate)

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 1: Your Code Calls notify()                               │
└──────────────────────────────────────────────────────────────────┘

from api.notifications.services import notify

notify(
    user=user,
    template_slug='payment_success',
    async_send=False,  # ⚡ Immediate execution
    amount=1000,
    gateway='eSewa'
)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 2: notify() Function Checks async_send                     │
└──────────────────────────────────────────────────────────────────┘

def notify(user, template_slug: str, async_send: bool = False, **context):
    if async_send:
        # Not this path ❌
    else:
        # ✅ This path - Execute immediately
        return _notify_service.send(user, template_slug, **context)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 3: NotifyService.send() - Core Processing                 │
└──────────────────────────────────────────────────────────────────┘

@transaction.atomic
def send(self, user, template_slug: str, **context):
    
    [3a] Get Template from Database
         ↓
         NotificationTemplate.objects.get(
             slug='payment_success',
             is_active=True
         )
         ↓
         Returns: NotificationTemplate {
             title_template: "Payment Successful - ₹{{ amount }}",
             message_template: "Your payment via {{ gateway }}...",
             notification_type: "payment"
         }
    
    [3b] Render Template with Context
         ↓
         _render_template("Payment Successful - ₹{{ amount }}", {
             amount: 1000,
             gateway: 'eSewa'
         })
         ↓
         Returns: "Payment Successful - ₹1000"
    
    [3c] Create In-App Notification (Atomic Transaction)
         ↓
         Notification.objects.create(
             user=user,
             template=template,
             title="Payment Successful - ₹1000",
             message="Your payment via eSewa...",
             notification_type='payment',
             data={'amount': 1000, 'gateway': 'eSewa'},
             channel='in_app',
             is_read=False
         )
         ↓
         ✅ Committed to database immediately
    
    [3d] Distribute to Other Channels
         ↓
         _distribute_channels(user, title, message, 'payment', context)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 4: Channel Distribution (_distribute_channels)            │
└──────────────────────────────────────────────────────────────────┘

[4a] Get Notification Rules
     ↓
     NotificationRule.objects.get(notification_type='payment')
     ↓
     Returns: NotificationRule {
         send_push: True,  ✅
         send_sms: False,  ❌
         send_email: True, ✅
         send_in_app: True ✅
     }

[4b] Send Push Notification (if send_push=True)
     ↓
     _send_push(user, title, message, data)
     ↓
     FCMService.send_push_notification()
     ↓
     ┌─────────────────────────────────────┐
     │  - Query: UserDevice.objects.filter()│
     │  - Get active FCM tokens             │
     │  - Send via Firebase Admin SDK       │
     │  - Create SMS_FCMLog entry           │
     └─────────────────────────────────────┘

[4c] Send Email (if send_email=True)
     ↓
     _send_email(user, title, message, data)
     ↓
     EmailService.send_email()
     ↓
     ┌─────────────────────────────────────┐
     │  - Render HTML template              │
     │  - Create EmailMultiAlternatives     │
     │  - Send via SMTP                     │
     └─────────────────────────────────────┘

[4d] Skip SMS (send_sms=False)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 5: Return Notification Object                             │
└──────────────────────────────────────────────────────────────────┘

notification = Notification {
    id: UUID('...'),
    user: user,
    title: "Payment Successful - ₹1000",
    message: "Your payment via eSewa...",
    is_read: False,
    created_at: datetime.now()
}

✅ User can immediately query this notification!

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Result: User Receives Notification                             │
└──────────────────────────────────────────────────────────────────┘

✅ In-App: Visible in user's notification list
✅ Push: Delivered to user's device (if FCM token exists)
✅ Email: Sent to user's email (if email exists)
❌ SMS: Not sent (per rule configuration)

⏱️ Total Time: ~200-500ms (synchronous)
```

---

## 🚀 FLOW 2: ASYNCHRONOUS NOTIFICATION (Background)

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 1: Your Code Calls notify() with async_send=True          │
└──────────────────────────────────────────────────────────────────┘

from api.notifications.services import notify

notify(
    user=user,
    template_slug='rental_started',
    async_send=True,  # 🚀 Background processing
    powerbank_id='PB123',
    station_name='Mall Road',
    rental_time='10:30 AM'
)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 2: notify() Function Queues Celery Task                   │
└──────────────────────────────────────────────────────────────────┘

def notify(user, template_slug: str, async_send: bool = False, **context):
    if async_send:
        # ✅ This path - Queue for background processing
        from api.notifications.tasks import send_notification_task
        
        # Convert user object to ID string
        user_id = str(user.id)
        
        # Queue Celery task
        return send_notification_task.delay(
            user_id=user_id,
            template_slug='rental_started',
            context={'powerbank_id': 'PB123', 'station_name': 'Mall Road'}
        )

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 3: Task Queued in Redis/RabbitMQ                          │
└──────────────────────────────────────────────────────────────────┘

Celery Broker (Redis):
┌─────────────────────────────────────────┐
│  Queue: celery                          │
│  ┌───────────────────────────────────┐  │
│  │ Task: send_notification_task      │  │
│  │ Args: [user_id, 'rental_started'] │  │
│  │ Status: PENDING                   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘

⏱️ Your code continues immediately! (non-blocking)
✅ Return: AsyncResult object

                           ↓
                    [Time passes...]
                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 4: Celery Worker Picks Up Task                            │
└──────────────────────────────────────────────────────────────────┘

Celery Worker Process:
┌─────────────────────────────────────────────────────────┐
│  Worker: celery@worker1                                │
│  Task ID: abc-123-def-456                              │
│  Status: STARTED                                        │
└─────────────────────────────────────────────────────────┘

@shared_task(bind=True, max_retries=3)
def send_notification_task(self, user_id, template_slug, context):
    
    [4a] Retrieve User from Database
         ↓
         User.objects.get(id=user_id)
         ↓
         If not found → Log error → Return failed
    
    [4b] Create NotifyService instance
         ↓
         notify_service = NotifyService()
    
    [4c] Execute Same Flow as Sync
         ↓
         notify_service.send(user, template_slug, **context)
         ↓
         [Follows FLOW 1: Steps 3-5]
         ↓
         Returns: Notification object
    
    [4d] Return Task Result
         ↓
         {
             'status': 'success',
             'notification_id': 'uuid-string',
             'user_id': user_id,
             'template_slug': 'rental_started'
         }

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 5: Error Handling & Retry                                 │
└──────────────────────────────────────────────────────────────────┘

If exception occurs:
    ↓
    try:
        raise self.retry(exc=e)  # Retry after 60 seconds
    except self.MaxRetriesExceededError:
        return {'status': 'failed', 'error': str(e)}

Retry Schedule:
┌────────────────────────────────────────┐
│  Attempt 1: Immediate                  │
│  Attempt 2: +60 seconds (if failed)    │
│  Attempt 3: +120 seconds (if failed)   │
│  Attempt 4: +180 seconds (if failed)   │
│  Final: Give up, log error             │
└────────────────────────────────────────┘

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Result: Notification Sent in Background                        │
└──────────────────────────────────────────────────────────────────┘

✅ In-App: Created and visible
✅ Push/SMS/Email: Sent based on rules
⏱️ Total Time: 1-5 seconds (async, non-blocking for your code)
```

---

## 📦 FLOW 3: BULK NOTIFICATION (Multiple Users)

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 1: Your Code Calls notify_bulk()                          │
└──────────────────────────────────────────────────────────────────┘

from api.notifications.services import notify_bulk

# Get 1000 active users
users = User.objects.filter(is_active=True)

notify_bulk(
    users=users,
    template_slug='special_offer',
    async_send=True,  # ✅ Recommended for bulk
    offer_title='50% Weekend Discount',
    offer_code='WEEKEND50',
    expiry_date='2025-10-20'
)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 2: notify_bulk() Converts Users to IDs                    │
└──────────────────────────────────────────────────────────────────┘

def notify_bulk(users: list, template_slug: str, async_send=True, **ctx):
    if async_send:
        # Convert all users to ID strings
        user_ids = [str(u.id) if hasattr(u, 'id') else str(u) for u in users]
        # Result: ['uuid-1', 'uuid-2', ..., 'uuid-1000']
        
        # Queue bulk task
        return send_bulk_notifications_task.delay(
            user_ids=user_ids,
            template_slug='special_offer',
            context=context
        )

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 3: Bulk Task Queued in Celery                             │
└──────────────────────────────────────────────────────────────────┘

Celery Broker:
┌─────────────────────────────────────────────┐
│  Queue: celery                              │
│  ┌───────────────────────────────────────┐  │
│  │ Task: send_bulk_notifications_task    │  │
│  │ Args: [1000 user_ids, 'special_offer']│  │
│  │ Status: PENDING                       │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘

⏱️ Your code returns immediately!

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 4: Celery Worker Processes Bulk Task                      │
└──────────────────────────────────────────────────────────────────┘

@shared_task(bind=True, max_retries=2)
def send_bulk_notifications_task(self, user_ids, template_slug, ctx):
    
    notify_service = NotifyService()
    success_count = 0
    failure_count = 0
    
    # Loop through all 1000 users
    for user_id in user_ids:
        try:
            [4a] Get user
                 user = User.objects.get(id=user_id)
            
            [4b] Send notification
                 notify_service.send(user, template_slug, **context)
            
            [4c] Increment success
                 success_count += 1
        
        except User.DoesNotExist:
            failure_count += 1
            logger.warning(f"User not found: {user_id}")
        
        except Exception as e:
            failure_count += 1
            logger.error(f"Failed to send to {user_id}: {e}")
    
    # Return bulk result
    return {
        'status': 'completed',
        'success_count': 998,
        'failure_count': 2,
        'total': 1000
    }

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Step 5: Processing Timeline                                    │
└──────────────────────────────────────────────────────────────────┘

Time: 0s      - Task queued
Time: 1s      - Worker picks up task
Time: 2s      - First 10 users processed
Time: 5s      - 50 users processed
Time: 30s     - 500 users processed
Time: 60s     - 1000 users processed ✅
Time: 61s     - Task complete, result logged

⏱️ Total Processing: ~60 seconds
⏱️ Your Code Blocking: ~10ms (just queuing)

                           ↓

┌──────────────────────────────────────────────────────────────────┐
│  Result: 1000 Notifications Sent                                │
└──────────────────────────────────────────────────────────────────┘

✅ Success: 998 users notified
❌ Failed: 2 users (not found or error)
📊 All results logged
```

---

## 🔀 DECISION TREE: When to Use What

```
                  Start: Need to Send Notification
                              │
                              ▼
                    ┌─────────────────────┐
                    │  How many users?    │
                    └─────────┬───────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         Single User                    Multiple Users
              │                               │
              ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │  Is it critical? │            │  Use notify_bulk │
    │  (OTP, Payment)  │            │  async_send=True │
    └────────┬─────────┘            └──────────────────┘
             │
      ┌──────┴──────┐
      │             │
    Yes            No
      │             │
      ▼             ▼
notify()      notify()
async_send    async_send
= False       = True
(Immediate)   (Background)

Examples:

✅ Critical (Sync):
   notify(user, 'otp_sms', async_send=False, otp='123456')
   notify(user, 'payment_success', async_send=False, amount=100)

✅ Non-Critical (Async):
   notify(user, 'rental_started', async_send=True, powerbank='PB123')
   notify(user, 'special_offer', async_send=True, discount='50%')

✅ Bulk (Always Async):
   notify_bulk(users, 'maintenance_notice', async_send=True, date='...')
```

---

## 🔄 CHANNEL DISTRIBUTION LOGIC

```
                    Notification Created (In-App)
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Get Notification   │
                    │  Rule for Type      │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Rule Exists?       │
                    └─────────┬───────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                   Yes                 No
                    │                   │
                    ▼                   ▼
            Apply Rule Config    Only In-App
            ┌───────────────┐    (Graceful
            │               │     Degradation)
            ▼               ▼
    ┌───────────┐   ┌───────────┐
    │send_push? │   │send_sms?  │
    │  True     │   │  False    │
    └─────┬─────┘   └─────┬─────┘
          │               │
          ▼               ▼
    Send Push        Skip SMS
    to FCM
          │
          ▼
    ┌───────────┐
    │send_email?│
    │  True     │
    └─────┬─────┘
          │
          ▼
    Send Email
    via SMTP

Example Rules:

rental_started:
  ✅ in_app  ✅ push  ❌ sms  ❌ email

payment_success:
  ✅ in_app  ✅ push  ✅ sms  ✅ email

special_offer:
  ✅ in_app  ✅ push  ❌ sms  ❌ email

otp_verification:
  ✅ in_app  ❌ push  ✅ sms  ❌ email
```

---

## 🎯 ERROR HANDLING LAYERS

```
Layer 1: notify() Function Level
┌────────────────────────────────────┐
│  try:                              │
│      _notify_service.send()        │
│  except Exception as e:            │
│      handle_service_error(e)       │
│      ↓                              │
│      Log error + Raise exception   │
└────────────────────────────────────┘
         │
         ▼ Exception propagates to caller

Layer 2: NotifyService.send() Method
┌────────────────────────────────────┐
│  try:                              │
│      template = _get_template()    │
│      notification = create()       │
│      _distribute_channels()        │
│  except Exception as e:            │
│      handle_service_error(e)       │
└────────────────────────────────────┘
         │
         ▼ Transaction rolled back if in atomic block

Layer 3: Channel Distribution
┌────────────────────────────────────┐
│  try:                              │
│      if rule.send_push:            │
│          _send_push()              │
│  except Exception as e:            │
│      log_error(e)                  │
│      ↓                              │
│      Continue (don't raise)        │
└────────────────────────────────────┘
         │
         ▼ Other channels still execute

Layer 4: Individual Channel
┌────────────────────────────────────┐
│  def _send_push():                 │
│      try:                          │
│          fcm_service.send()        │
│      except Exception as e:        │
│          log_error(e)              │
│          ↓                          │
│          Don't raise - graceful    │
└────────────────────────────────────┘

Layer 5: Celery Task Retry
┌────────────────────────────────────┐
│  @shared_task(max_retries=3)       │
│  def send_notification_task():     │
│      try:                          │
│          notify_service.send()     │
│      except Exception as e:        │
│          raise self.retry(exc=e)   │
│          ↓                          │
│          Retry after 60s           │
└────────────────────────────────────┘

Result: Defense-in-depth error isolation
```

---

## 📊 DATABASE QUERIES ANALYSIS

### Single Notification (Sync)
```
Query 1: SELECT * FROM notification_templates 
         WHERE slug='rental_started' AND is_active=True
         
Query 2: INSERT INTO notifications (user_id, title, message, ...)
         
Query 3: SELECT * FROM notification_rules 
         WHERE notification_type='rental'
         
Query 4: SELECT * FROM user_devices 
         WHERE user_id=? AND is_active=True
         
Query 5: INSERT INTO sms_fcm_logs (user_id, type, status, ...)

Total: 5 queries per notification ✅
Time: ~50-100ms
```

### Bulk Notification (1000 users)
```
Query 1: SELECT * FROM notification_templates (1x) ✅
Query 2: SELECT * FROM notification_rules (1x) ✅

For each user (1000x):
  Query 3: INSERT INTO notifications
  Query 4: SELECT * FROM user_devices
  Query 5: INSERT INTO sms_fcm_logs

Total: 2 + (1000 × 3) = 3002 queries ⚠️
Time: ~30-60 seconds

💡 Optimization potential:
- Bulk INSERT notifications (1 query instead of 1000)
- Prefetch user_devices (1 query instead of 1000)
- Result: ~10 queries instead of 3002! 🚀
```

---

## 🎯 PERFORMANCE CHARACTERISTICS

| Operation | Queries | Time | Recommended Use |
|-----------|---------|------|-----------------|
| Single Sync | 5 | 50-200ms | Critical notifications (OTP, payments) |
| Single Async | 5 | 1-5s | Non-critical notifications |
| Bulk Sync | 3000+ | 30-60s | Small lists (<10 users) |
| Bulk Async | 3000+ | 30-60s | Large lists (background) |

---

**Created by:** GitHub Copilot  
**Last Updated:** October 15, 2025  
**Version:** 2.0 (Simplified Universal API)
