# Fixtures Updates - AppConfig & Notification Templates

> **Version:** 1.0  
> **Created:** 2026-01-30  
> **Status:** REVIEW REQUIRED

---

## 1. Overview

This document consolidates ALL fixture updates required for:
1. Cancellation rules (from 01_cancellation_rules.md)
2. Pay-due endpoint (from 02_pay_due_endpoint.md)
3. Swapping support (from 03_swapping_support.md)
4. Revenue distribution (from rental_start_refactoring_plan.md)

---

## 2. AppConfig Additions

### 2.1 File Location

`api/user/system/fixtures/app_config.json`

### 2.2 New Entries to Add

```json
[
  {
    "model": "system.appconfig",
    "fields": {
      "key": "NO_CHARGE_RENTAL_CANCELLATION_TIME",
      "value": "5",
      "description": "Time window in minutes within which a rental can be cancelled with FULL refund (no charges). After this window, late cancellation fee applies.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  },
  {
    "model": "system.appconfig",
    "fields": {
      "key": "SWAPPING_MAX_TIME",
      "value": "5",
      "description": "Time window in minutes from rental start within which user can swap to a different powerbank at the same station.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  },
  {
    "model": "system.appconfig",
    "fields": {
      "key": "PLATFORM_VAT_PERCENT",
      "value": "13",
      "description": "VAT percentage deducted at ChargeGhar level for revenue distribution. Applied to all rental transactions before partner share calculations.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  },
  {
    "model": "system.appconfig",
    "fields": {
      "key": "PLATFORM_SERVICE_CHARGE_PERCENT",
      "value": "2.5",
      "description": "Service charge percentage deducted at ChargeGhar level for revenue distribution. Applied after VAT deduction.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  }
]
```

### 2.3 Complete AppConfig Table After Updates

| Key | Value | Description | Source Plan |
|-----|-------|-------------|-------------|
| `RENTAL_CANCELLATION_WINDOW_MINUTES` | `5` | **EXISTING** - Keep as fallback | Existing |
| `NO_CHARGE_RENTAL_CANCELLATION_TIME` | `5` | Free cancellation window | 01_cancellation |
| `SWAPPING_MAX_TIME` | `5` | Swap time window | 03_swapping |
| `PLATFORM_VAT_PERCENT` | `13` | VAT for revenue calc | rental_start_refactoring |
| `PLATFORM_SERVICE_CHARGE_PERCENT` | `2.5` | Service charge for revenue | rental_start_refactoring |

---

## 3. Notification Template Additions

### 3.1 File Location

`api/user/notifications/fixtures/templates.json`

### 3.2 New Templates to Add

```json
[
  {
    "model": "notifications.notificationtemplate",
    "pk": 51,
    "fields": {
      "name": "Rental Cancelled Free",
      "slug": "rental_cancelled_free",
      "notification_type": "rental",
      "title_template": "Rental Cancelled",
      "message_template": "Your rental {{rental_code}} has been cancelled. Full refund of Rs. {{refund_amount}} processed to your wallet.",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 52,
    "fields": {
      "name": "Rental Cancelled Late",
      "slug": "rental_cancelled_late",
      "notification_type": "rental",
      "title_template": "Rental Cancelled - Late Fee Applied",
      "message_template": "Your rental {{rental_code}} has been cancelled. Late cancellation fee of Rs. {{cancellation_fee}} applied. Refund amount: Rs. {{refund_amount}}.",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 53,
    "fields": {
      "name": "Payment Due Settled",
      "slug": "payment_due_settled",
      "notification_type": "payment",
      "title_template": "Payment Successful",
      "message_template": "Your outstanding dues of Rs. {{amount}} for rental {{rental_code}} have been settled. Thank you for using ChargeGhar!",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 54,
    "fields": {
      "name": "Rental Swapped",
      "slug": "rental_swapped",
      "notification_type": "rental",
      "title_template": "Powerbank Swapped Successfully",
      "message_template": "Your powerbank for rental {{rental_code}} has been swapped. Old: {{old_powerbank}}, New: {{new_powerbank}} ({{new_battery_level}}% battery). Enjoy your rental!",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 55,
    "fields": {
      "name": "Rental Cancelled POSTPAID",
      "slug": "rental_cancelled_postpaid",
      "notification_type": "rental",
      "title_template": "Rental Cancelled",
      "message_template": "Your rental {{rental_code}} has been cancelled. {{#cancellation_fee}}Late cancellation fee of Rs. {{cancellation_fee}} has been charged.{{/cancellation_fee}}{{^cancellation_fee}}No charges applied.{{/cancellation_fee}}",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  }
]
```

### 3.3 Complete New Notification Templates Summary

| PK | Slug | Type | Purpose | Source Plan |
|----|------|------|---------|-------------|
| 51 | `rental_cancelled_free` | rental | Free cancellation with full refund | 01_cancellation |
| 52 | `rental_cancelled_late` | rental | Late cancellation with fee | 01_cancellation |
| 53 | `payment_due_settled` | payment | Dues payment confirmation | 02_pay_due |
| 54 | `rental_swapped` | rental | Powerbank swap confirmation | 03_swapping |
| 55 | `rental_cancelled_postpaid` | rental | POSTPAID cancellation | 01_cancellation |

---

## 4. Notification Rules (If Needed)

### 4.1 File Location

`api/user/notifications/fixtures/rules.json`

### 4.2 Verify Existing Rules Cover New Templates

Check if rules for these notification_types exist:
- `rental` - Should exist
- `payment` - Should exist

If rules don't cover new templates, they will use default notification behavior.

---

## 5. Existing Templates That May Need Updates

### 5.1 Current Templates to Review

| PK | Slug | Current Message | Issue |
|----|------|-----------------|-------|
| 3 | `rental_completed` | "Total cost: Rs. {{total_cost}}" | Should include breakdown if late fees applied |
| 4 | `rental_overdue` | "Additional charges of Rs. {{penalty_amount}}" | Consistent with late fee terminology |

### 5.2 Recommended Updates

**Template PK 3 - rental_completed (Optional Enhancement):**

```json
{
  "message_template": "Thank you! Your powerbank {{powerbank_id}} has been returned. {{#late_fee}}Late fee: Rs. {{late_fee}}. {{/late_fee}}Total cost: Rs. {{total_cost}}"
}
```

---

## 6. Implementation Steps

### Step 1: Add AppConfig Entries

```bash
# Add to app_config.json and reload fixtures
docker compose exec api python manage.py loaddata api/user/system/fixtures/app_config.json
```

### Step 2: Add Notification Templates

```bash
# Add to templates.json and reload fixtures
docker compose exec api python manage.py loaddata api/user/notifications/fixtures/templates.json
```

### Step 3: Verify Loading

```bash
# Check AppConfig loaded
docker compose exec api python manage.py shell -c "
from api.user.system.models import AppConfig
configs = AppConfig.objects.filter(key__in=[
    'NO_CHARGE_RENTAL_CANCELLATION_TIME',
    'SWAPPING_MAX_TIME',
    'PLATFORM_VAT_PERCENT',
    'PLATFORM_SERVICE_CHARGE_PERCENT'
])
for c in configs:
    print(f'{c.key}: {c.value}')
"
```

---

## 7. Usage Examples

### 7.1 Reading AppConfig in Code

```python
from api.user.system.models import AppConfig

# Get free cancellation window
free_window = int(AppConfig.objects.filter(
    key='NO_CHARGE_RENTAL_CANCELLATION_TIME', 
    is_active=True
).values_list('value', flat=True).first() or 5)

# Get swap window
swap_window = int(AppConfig.objects.filter(
    key='SWAPPING_MAX_TIME', 
    is_active=True
).values_list('value', flat=True).first() or 5)

# Get VAT percent
vat_percent = Decimal(AppConfig.objects.filter(
    key='PLATFORM_VAT_PERCENT', 
    is_active=True
).values_list('value', flat=True).first() or '13')
```

### 7.2 Sending Notifications

```python
from api.user.notifications.services import notify

# Free cancellation
notify(
    user,
    'rental_cancelled_free',
    rental_code=rental.rental_code,
    refund_amount=float(rental.amount_paid)
)

# Late cancellation
notify(
    user,
    'rental_cancelled_late',
    rental_code=rental.rental_code,
    cancellation_fee=float(fee),
    refund_amount=float(refund_amount)
)

# Swap
notify(
    user,
    'rental_swapped',
    rental_code=rental.rental_code,
    old_powerbank=old_pb.serial_number,
    new_powerbank=new_pb.serial_number,
    new_battery_level=new_pb.battery_level
)

# Payment settled
notify(
    user,
    'payment_due_settled',
    rental_code=rental.rental_code,
    amount=float(total_amount)
)
```

---

## 8. Cross-Reference with Plans

| Plan File | AppConfig Keys | Notification Templates |
|-----------|----------------|------------------------|
| 01_cancellation_rules.md | `NO_CHARGE_RENTAL_CANCELLATION_TIME` | `rental_cancelled_free`, `rental_cancelled_late`, `rental_cancelled_postpaid` |
| 02_pay_due_endpoint.md | - | `payment_due_settled` |
| 03_swapping_support.md | `SWAPPING_MAX_TIME` | `rental_swapped` |
| rental_start_refactoring_plan.md | `PLATFORM_VAT_PERCENT`, `PLATFORM_SERVICE_CHARGE_PERCENT` | - |

---

## 9. Fixture File Diffs

### 9.1 app_config.json - Add After Line 263

```json
,
  {
    "model": "system.appconfig",
    "fields": {
      "key": "NO_CHARGE_RENTAL_CANCELLATION_TIME",
      "value": "5",
      "description": "Time window in minutes within which a rental can be cancelled with FULL refund (no charges). After this window, late cancellation fee applies.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  },
  {
    "model": "system.appconfig",
    "fields": {
      "key": "SWAPPING_MAX_TIME",
      "value": "5",
      "description": "Time window in minutes from rental start within which user can swap to a different powerbank at the same station.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  },
  {
    "model": "system.appconfig",
    "fields": {
      "key": "PLATFORM_VAT_PERCENT",
      "value": "13",
      "description": "VAT percentage deducted at ChargeGhar level for revenue distribution.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  },
  {
    "model": "system.appconfig",
    "fields": {
      "key": "PLATFORM_SERVICE_CHARGE_PERCENT",
      "value": "2.5",
      "description": "Service charge percentage deducted at ChargeGhar level for revenue distribution.",
      "is_active": true,
      "created_at": "2026-01-30T00:00:00Z",
      "updated_at": "2026-01-30T00:00:00Z"
    }
  }
```

### 9.2 templates.json - Add After Last Entry (Before Closing `]`)

```json
,
  {
    "model": "notifications.notificationtemplate",
    "pk": 51,
    "fields": {
      "name": "Rental Cancelled Free",
      "slug": "rental_cancelled_free",
      "notification_type": "rental",
      "title_template": "Rental Cancelled",
      "message_template": "Your rental {{rental_code}} has been cancelled. Full refund of Rs. {{refund_amount}} processed to your wallet.",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 52,
    "fields": {
      "name": "Rental Cancelled Late",
      "slug": "rental_cancelled_late",
      "notification_type": "rental",
      "title_template": "Rental Cancelled - Late Fee Applied",
      "message_template": "Your rental {{rental_code}} has been cancelled. Late cancellation fee of Rs. {{cancellation_fee}} applied. Refund amount: Rs. {{refund_amount}}.",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 53,
    "fields": {
      "name": "Payment Due Settled",
      "slug": "payment_due_settled",
      "notification_type": "payment",
      "title_template": "Payment Successful",
      "message_template": "Your outstanding dues of Rs. {{amount}} for rental {{rental_code}} have been settled. Thank you for using ChargeGhar!",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 54,
    "fields": {
      "name": "Rental Swapped",
      "slug": "rental_swapped",
      "notification_type": "rental",
      "title_template": "Powerbank Swapped Successfully",
      "message_template": "Your powerbank for rental {{rental_code}} has been swapped. Old: {{old_powerbank}}, New: {{new_powerbank}} ({{new_battery_level}}% battery). Enjoy your rental!",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  },
  {
    "model": "notifications.notificationtemplate",
    "pk": 55,
    "fields": {
      "name": "Rental Cancelled POSTPAID",
      "slug": "rental_cancelled_postpaid",
      "notification_type": "rental",
      "title_template": "Rental Cancelled",
      "message_template": "Your rental {{rental_code}} has been cancelled. {{#cancellation_fee}}Late cancellation fee of Rs. {{cancellation_fee}} has been charged.{{/cancellation_fee}}{{^cancellation_fee}}No charges applied.{{/cancellation_fee}}",
      "is_active": true,
      "created_at": "2026-01-30T10:00:00Z",
      "updated_at": "2026-01-30T10:00:00Z"
    }
  }
```

---

## Approval Required

Please confirm:
- [ ] AppConfig key names are correct
- [ ] Default values are correct (5 min windows, 13% VAT, 2.5% service charge)
- [ ] Notification template messages are appropriate
- [ ] Template variable names match expected data

---
