# 🚀 Notification System - Quick Reference

## 💡 The Power of Simplicity: Just 2 Methods!

Instead of remembering dozens of methods, you only need **2 universal methods** that work for ALL scenarios:

1. **`notify()`** - Send to one user (sync or async)
2. **`notify_bulk()`** - Send to multiple users (sync or async)

---

## 📦 Import Statement

```python
from api.notifications.services import notify, notify_bulk
```

That's it! Just import these 2 methods and you're ready to send ANY notification.

---

## 🎯 Method 1: `notify()` - Universal Single Notification

### Signature
```python
notify(user, template_slug: str, async_send: bool = False, **context)
```

### Parameters
- **`user`**: User object (or user_id string for async)
- **`template_slug`**: Template name (e.g., 'rental_started', 'payment_success')
- **`async_send`**: `False` = immediate (sync), `True` = background (async via Celery)
- **`**context`**: Template variables as keyword arguments

---

## 📚 Real-World Examples

### Rental Notifications

```python
from api.notifications.services import notify

# Rental started (async - non-blocking)
notify(user, 'rental_started', async_send=True,
       powerbank_id='PB123',
       station_name='Mall Road Station',
       max_hours=24)

# Rental ending soon (sync - immediate)
notify(user, 'rental_ending_soon',
       powerbank_id='PB123',
       remaining_hours=2)

# Rental completed (async)
notify(user, 'rental_completed', async_send=True,
       powerbank_id='PB123',
       total_cost=150)
```

### Payment Notifications

```python
# Payment success (sync - immediate feedback)
notify(user, 'payment_success',
       amount=100,
       gateway='eSewa',
       transaction_id='TXN123456')

# Wallet recharged (async)
notify(user, 'wallet_recharged', async_send=True,
       amount=500,
       new_balance=1200)
```

### OTP Notifications

```python
# OTP via SMS (sync - must be immediate)
notify(user, 'otp_sms',
       otp='123456',
       purpose='login',
       expiry_minutes=5)

# OTP via Email (sync)
notify(user, 'otp_email',
       otp='123456',
       purpose='verification',
       expiry_minutes=10)
```

### Any Other Notification

```python
# Points earned
notify(user, 'points_earned', async_send=True,
       points=50, reason='Rental completed', total_points=150)

# KYC status
notify(user, 'kyc_status_update',
       kyc_status='approved')

# Account status
notify(user, 'account_status_update',
       new_status='active', reason='KYC verified')

# Special offer
notify(user, 'special_offer', async_send=True,
       offer_title='50% Off', expiry_date='2025-12-31', promo_code='WEEKEND50')
```

---

## 🎯 Method 2: `notify_bulk()` - Universal Bulk Notification

### Signature
```python
notify_bulk(users: list, template_slug: str, async_send: bool = True, **context)
```

### Examples

```python
from api.notifications.services import notify_bulk

# Marketing campaign (async - recommended)
active_users = User.objects.filter(is_active=True)
notify_bulk(active_users, 'special_offer', async_send=True,
           offer_title='Flash Sale - 70% Off',
           expiry_date='2025-10-18',
           promo_code='FLASH70')

# Maintenance notice
notify_bulk(all_users, 'maintenance_notice', async_send=True,
           maintenance_date='2025-10-20',
           start_time='2:00 AM',
           end_time='4:00 AM')
```

---

## ⚡ Sync vs Async - When to Use What?

### Use **Sync** (`async_send=False`) for:
- ✅ OTP notifications - Must be immediate
- ✅ Payment confirmations - User is waiting
- ✅ Critical alerts - Account suspended, security issues

```python
notify(user, 'otp_sms', otp='123456')  # Default is sync
notify(user, 'payment_success', amount=100, gateway='eSewa')
```

### Use **Async** (`async_send=True`) for:
- ✅ Marketing campaigns - Bulk notifications
- ✅ Non-critical updates - Promotions, achievements
- ✅ Large batches - 10+ users

```python
notify(user, 'rental_started', async_send=True, powerbank_id='PB123')
notify_bulk(users, 'special_offer', async_send=True, discount='50%')
```

---

## 🔧 Integration in Your Services

### Rental Service
```python
from api.notifications.services import notify

class RentalService(BaseService):
    def start_rental(self, user, powerbank, station):
        # ... rental logic ...
        
        # One line notification!
        notify(user, 'rental_started', async_send=True,
               powerbank_id=powerbank.id,
               station_name=station.name,
               max_hours=24)
        
        return rental
```

### Payment Service
```python
from api.notifications.services import notify

class PaymentService(BaseService):
    def process_payment(self, user, amount, gateway):
        # ... payment logic ...
        
        # Immediate feedback (sync)
        notify(user, 'payment_success',
               amount=amount,
               gateway=gateway,
               transaction_id=transaction.id)
        
        return transaction
```

### User Registration
```python
from api.notifications.services import notify

def register_user(username, email, phone):
    user = User.objects.create(...)
    
    # Welcome (async)
    notify(user, 'welcome_user', async_send=True,
           user_name=user.full_name)
    
    # OTP (sync - immediate)
    otp = generate_otp()
    notify(user, 'otp_sms', otp=otp, purpose='verification')
    
    return user
```

---

## 📋 Available Templates

| Template Slug | Variables |
|--------------|-----------|
| `rental_started` | powerbank_id, station_name, max_hours |
| `rental_ending_soon` | powerbank_id, remaining_hours |
| `rental_completed` | powerbank_id, total_cost |
| `payment_success` | amount, gateway, transaction_id |
| `payment_failed` | amount, gateway, failure_reason |
| `wallet_recharged` | amount, new_balance |
| `otp_sms` | otp, purpose, expiry_minutes |
| `otp_email` | otp, purpose, expiry_minutes |
| `welcome_user` | user_name |
| `kyc_status_update` | kyc_status, rejection_reason |
| `account_status_update` | new_status, reason |
| `special_offer` | offer_title, expiry_date, promo_code |
| `points_earned` | points, reason, total_points |
| `coupon_applied` | coupon_code, points |
| ... and 20+ more! | See `fixtures/notifications.json` |

---

## 💡 Pro Tips

### Tip 1: Use **kwargs
```python
context = {
    'powerbank_id': rental.powerbank_id,
    'station_name': rental.station.name,
    'max_hours': 24
}
notify(user, 'rental_started', async_send=True, **context)
```

### Tip 2: Default is sync
```python
# These are the same:
notify(user, 'payment_success', amount=100)
notify(user, 'payment_success', async_send=False, amount=100)
```

### Tip 3: Handle exceptions
```python
try:
    notify(user, 'rental_started', async_send=True, powerbank_id='PB123')
except Exception as e:
    logger.error(f"Notification failed: {e}")
    # Continue - notifications are non-critical
```

---

## 📊 Summary

### Just Remember This:

```python
from api.notifications.services import notify, notify_bulk

# Single notification
notify(user, 'template_slug', async_send=False, var1='value1', var2='value2')

# Bulk notification
notify_bulk(users, 'template_slug', async_send=True, var1='value1', var2='value2')
```

### That's it! 🎉

- **2 methods** for everything
- **`async_send` parameter** controls sync/async
- **`template_slug`** is any template from fixtures
- **`**context`** passes variables to template

---

**Print this and keep it handy! 📌**
