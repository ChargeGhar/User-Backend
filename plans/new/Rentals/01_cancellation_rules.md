# Rental Cancellation Rules - Complete Plan

> **Version:** 1.0  
> **Created:** 2026-01-30  
> **Status:** REVIEW REQUIRED

---

## 1. Current State Analysis

### 1.1 Current Implementation Location

**File:** `api/user/rentals/services/rental/cancel.py`

### 1.2 Current Cancellation Logic (Verified)

```python
# Current flow in RentalCancelMixin.cancel_rental():
1. Get rental by ID for user
2. Check status in ['PENDING', 'PENDING_POPUP', 'ACTIVE']
3. _validate_cancellation_window() - Check if within time window
4. _validate_powerbank_returned() - Check powerbank is back in slot
5. Set status = 'CANCELLED', ended_at = now()
6. _release_powerbank_and_slot() - Release resources
7. _process_cancellation_refund() - Full refund if PAID
```

### 1.3 Current AppConfig Values

| Key | Current Value | Description |
|-----|---------------|-------------|
| `RENTAL_CANCELLATION_WINDOW_MINUTES` | `5` | Time window for free cancellation |

### 1.4 Current Gaps Identified

| Gap | Description |
|-----|-------------|
| **No POSTPAID handling** | Current logic only handles PREPAID refunds |
| **No late fee on cancellation** | After window, cancellation is blocked entirely (no partial charge option) |
| **No swapping distinction** | Swapping vs cancellation treated the same |
| **Single time window** | No differentiation between free/charged cancellation |

---

## 2. Your Requirements (Verified)

Based on your input:

1. **Free Cancellation Window:** User can cancel within `NO_CHARGE_RENTAL_CANCELLATION_TIME` with full refund
2. **Swapping Window:** User can swap within `SWAPPING_MAX_TIME` (separate from cancellation)
3. **Late Cancellation:** After free window, apply late fee configuration before cancellation
4. **Powerbank Return Requirement:** User MUST return powerbank before cancellation (current behavior - correct)
5. **POSTPAID Handling:** Need to define behavior for POSTPAID cancellations

---

## 3. Proposed Cancellation Rules

### 3.1 Time Windows

| Window | Config Key | Default | Description |
|--------|------------|---------|-------------|
| Free Cancellation | `NO_CHARGE_RENTAL_CANCELLATION_TIME` | `5` (minutes) | Full refund, no charges |
| Swapping | `SWAPPING_MAX_TIME` | `5` (minutes) | Swap to different powerbank (separate feature) |

### 3.2 PREPAID Cancellation Matrix

| Scenario | Time Since Start | Action | Payment Handling |
|----------|------------------|--------|------------------|
| Within free window | 0 - 5 min | Cancel allowed | Full refund (wallet + points) |
| After free window | > 5 min | Cancel with late fee | Refund = amount_paid - late_fee |
| Powerbank not returned | Any | Cancel blocked | Error: "Return powerbank first" |
| Rental already OVERDUE | Any | Cancel blocked | Must use pay-due instead |

### 3.3 POSTPAID Cancellation Matrix

| Scenario | Time Since Start | Action | Payment Handling |
|----------|------------------|--------|------------------|
| Within free window | 0 - 5 min | Cancel allowed | No charge (nothing paid) |
| After free window | > 5 min | Cancel with charge | Charge late_fee from wallet |
| Insufficient balance | > 5 min | Cancel blocked | Error: "Add balance to cover charges" |
| Powerbank not returned | Any | Cancel blocked | Error: "Return powerbank first" |

---

## 4. Late Fee Calculation for Cancellation

### 4.1 Using Existing LateFeeService

**Current Active Configuration (from fixtures):**
- Type: `MULTIPLIER`
- Multiplier: `2.0x` normal rate
- Grace Period: `15` minutes
- Max Daily: `NPR 1000`

### 4.2 Cancellation Late Fee Logic

```python
def calculate_cancellation_fee(rental: Rental) -> Decimal:
    """
    Calculate fee for cancellation after free window.
    Uses same late fee logic but based on usage time, not overdue time.
    """
    from api.user.rentals.services.late_fee_service import LateFeeService
    
    if not rental.started_at:
        return Decimal('0')
    
    # Get free window config
    free_window_minutes = int(AppConfig.get('NO_CHARGE_RENTAL_CANCELLATION_TIME', 5))
    
    # Calculate minutes used beyond free window
    usage_duration = timezone.now() - rental.started_at
    usage_minutes = int(usage_duration.total_seconds() / 60)
    
    if usage_minutes <= free_window_minutes:
        return Decimal('0')
    
    # Minutes beyond free window = chargeable minutes
    chargeable_minutes = usage_minutes - free_window_minutes
    
    # Use package rate
    normal_rate = rental.package.price / rental.package.duration_minutes
    
    # Get late fee config
    config = LateFeeService.get_active_configuration()
    
    # Calculate fee (uses same logic as overdue)
    return LateFeeService.calculate_late_fee(config, normal_rate, chargeable_minutes)
```

---

## 5. Updated Cancellation Flow

### 5.1 PREPAID Flow

```
POST /api/rentals/{rental_id}/cancel
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. VALIDATE                                                      │
│    ├── Rental exists and belongs to user                         │
│    ├── Status in ['PENDING', 'PENDING_POPUP', 'ACTIVE']          │
│    └── Powerbank is returned (in slot at station)                │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. CHECK CANCELLATION WINDOW                                     │
│    ├── Get NO_CHARGE_RENTAL_CANCELLATION_TIME from AppConfig     │
│    ├── Calculate time_since_start                                │
│    │                                                             │
│    ├── IF time_since_start <= free_window:                       │
│    │   └── is_free_cancellation = True                           │
│    │                                                             │
│    └── ELSE:                                                     │
│        ├── is_free_cancellation = False                          │
│        └── cancellation_fee = calculate_cancellation_fee()       │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. PROCESS CANCELLATION                                          │
│    ├── Set status = 'CANCELLED'                                  │
│    ├── Set ended_at = now()                                      │
│    ├── Store cancellation_reason in rental_metadata              │
│    └── Store is_free_cancellation, cancellation_fee in metadata  │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. PAYMENT HANDLING (PREPAID)                                    │
│                                                                  │
│    IF is_free_cancellation:                                      │
│    ├── Refund full amount_paid to wallet                         │
│    ├── Refund points if used (from transaction.gateway_response) │
│    └── Set payment_status = 'REFUNDED'                           │
│                                                                  │
│    ELSE (late cancellation):                                     │
│    ├── refund_amount = amount_paid - cancellation_fee            │
│    ├── IF refund_amount > 0:                                     │
│    │   └── Refund refund_amount to wallet                        │
│    ├── Create Transaction(type='FINE', amount=cancellation_fee)  │
│    └── Set payment_status = 'PAID' (retained portion)            │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. CLEANUP                                                       │
│    ├── _release_powerbank_and_slot()                             │
│    └── Send notification (rental_cancelled)                      │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 POSTPAID Flow

```
POST /api/rentals/{rental_id}/cancel
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1-3. SAME AS PREPAID                                             │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. PAYMENT HANDLING (POSTPAID)                                   │
│                                                                  │
│    IF is_free_cancellation:                                      │
│    └── No payment action (nothing was paid)                      │
│        Set payment_status = 'PAID' (no dues)                     │
│                                                                  │
│    ELSE (late cancellation):                                     │
│    ├── Check user wallet balance >= cancellation_fee             │
│    ├── IF insufficient:                                          │
│    │   └── BLOCK: "Add NPR {shortfall} to cancel"                │
│    ├── ELSE:                                                     │
│    │   ├── Deduct cancellation_fee from wallet                   │
│    │   ├── Create Transaction(type='FINE', amount=fee)           │
│    │   └── Set payment_status = 'PAID'                           │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. SAME AS PREPAID                                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Code Changes Required

### 6.1 Update `cancel.py`

**Method:** `_validate_cancellation_window()`

**Current:** Returns error if beyond window
**New:** Calculate fee instead of blocking

```python
def _check_cancellation_type(self, rental: Rental) -> Tuple[bool, Decimal]:
    """
    Check if cancellation is free or paid.
    
    Returns:
        Tuple[is_free_cancellation, cancellation_fee]
    """
    if not rental.started_at:
        return True, Decimal('0')
    
    from api.user.system.models import AppConfig
    
    free_window_minutes = int(AppConfig.objects.filter(
        key='NO_CHARGE_RENTAL_CANCELLATION_TIME', is_active=True
    ).values_list('value', flat=True).first() or 5)
    
    time_since_start = timezone.now() - rental.started_at
    usage_minutes = int(time_since_start.total_seconds() / 60)
    
    if usage_minutes <= free_window_minutes:
        return True, Decimal('0')
    
    # Calculate cancellation fee
    fee = self._calculate_cancellation_fee(rental, usage_minutes - free_window_minutes)
    return False, fee
```

### 6.2 Update `_process_cancellation_refund()`

**New Logic:**

```python
def _process_cancellation_payment(
    self, 
    rental: Rental, 
    user, 
    is_free: bool, 
    fee: Decimal
) -> None:
    """Process payment/refund for cancellation"""
    from api.user.payments.models import Transaction
    from api.user.payments.services import WalletService
    from api.user.payments.repositories import TransactionRepository
    from api.common.utils.helpers import generate_transaction_id
    
    wallet_service = WalletService()
    
    if rental.package.payment_model == 'PREPAID':
        self._handle_prepaid_cancellation(rental, user, is_free, fee, wallet_service)
    else:  # POSTPAID
        self._handle_postpaid_cancellation(rental, user, is_free, fee, wallet_service)


def _handle_prepaid_cancellation(self, rental, user, is_free, fee, wallet_service):
    """Handle PREPAID cancellation refunds"""
    original_txn = Transaction.objects.filter(
        related_rental=rental,
        transaction_type='RENTAL',
        status='SUCCESS'
    ).first()
    
    if is_free:
        # Full refund
        self._refund_full_amount(rental, user, original_txn, wallet_service)
    else:
        # Partial refund (amount - fee)
        refund_amount = rental.amount_paid - fee
        if refund_amount > 0:
            wallet_service.add_balance(
                user=user,
                amount=refund_amount,
                description=f"Partial refund for cancelled rental {rental.rental_code}"
            )
        
        # Create fine transaction
        self._create_fine_transaction(user, rental, fee, "Late cancellation fee")
        
        # Update original transaction
        if original_txn:
            original_txn.gateway_response['cancellation_fee'] = str(fee)
            original_txn.gateway_response['refund_amount'] = str(refund_amount)
            original_txn.save(update_fields=['gateway_response'])
        
        rental.payment_status = 'PAID'
        rental.save(update_fields=['payment_status'])


def _handle_postpaid_cancellation(self, rental, user, is_free, fee, wallet_service):
    """Handle POSTPAID cancellation charges"""
    if is_free:
        # No payment needed
        rental.payment_status = 'PAID'
        rental.save(update_fields=['payment_status'])
    else:
        # Check balance
        if not hasattr(user, 'wallet') or user.wallet.balance < fee:
            shortfall = fee - (user.wallet.balance if hasattr(user, 'wallet') else Decimal('0'))
            raise ServiceException(
                detail=f"Insufficient balance. Add NPR {shortfall} to cancel this rental.",
                code="insufficient_balance_for_cancellation"
            )
        
        # Deduct fee
        wallet_service.deduct_balance(
            user=user,
            amount=fee,
            description=f"Late cancellation fee for rental {rental.rental_code}"
        )
        
        # Create fine transaction
        self._create_fine_transaction(user, rental, fee, "Late cancellation fee")
        
        rental.amount_paid = fee
        rental.payment_status = 'PAID'
        rental.save(update_fields=['amount_paid', 'payment_status'])
```

---

## 7. Response Format

### 7.1 Successful Free Cancellation

```json
{
  "success": true,
  "message": "Rental cancelled successfully",
  "data": {
    "rental_id": "uuid",
    "rental_code": "RNT-XXXXX",
    "status": "CANCELLED",
    "cancellation_type": "FREE",
    "refund_amount": 100.00,
    "cancellation_fee": 0.00
  }
}
```

### 7.2 Successful Late Cancellation (PREPAID)

```json
{
  "success": true,
  "message": "Rental cancelled. Late cancellation fee applied.",
  "data": {
    "rental_id": "uuid",
    "rental_code": "RNT-XXXXX",
    "status": "CANCELLED",
    "cancellation_type": "LATE",
    "original_amount": 100.00,
    "cancellation_fee": 20.00,
    "refund_amount": 80.00
  }
}
```

### 7.3 Blocked - Powerbank Not Returned

```json
{
  "success": false,
  "message": "Cannot cancel rental. Please return powerbank to station first.",
  "error": {
    "code": "powerbank_not_returned",
    "detail": "Powerbank must be inserted back in slot before cancellation."
  }
}
```

---

## 8. Notification Templates Required

### 8.1 New Templates to Add

| Slug | Title | Message |
|------|-------|---------|
| `rental_cancelled_free` | Rental Cancelled | Your rental {{rental_code}} has been cancelled. Full refund of Rs. {{refund_amount}} processed. |
| `rental_cancelled_late` | Rental Cancelled - Late Fee Applied | Your rental {{rental_code}} has been cancelled. Late fee of Rs. {{cancellation_fee}} applied. Refund: Rs. {{refund_amount}}. |

---

## 9. Database/Metadata Updates

### 9.1 rental_metadata Structure for Cancellation

```json
{
  "cancellation_reason": "User requested cancellation",
  "cancellation_type": "FREE|LATE",
  "cancellation_fee": "0.00|20.00",
  "refund_amount": "100.00|80.00",
  "usage_minutes_at_cancel": 3,
  "cancelled_at": "2026-01-30T10:00:00Z"
}
```

---

## 10. Validation Summary

| Check | Current | New |
|-------|---------|-----|
| Rental status valid | Yes | Yes (unchanged) |
| Powerbank returned | Yes | Yes (unchanged) |
| Time window | Blocks after 5 min | Allows with fee after 5 min |
| PREPAID refund | Full only | Full or partial |
| POSTPAID handling | None | Charge fee from wallet |
| Late fee calculation | Not used | Uses LateFeeService |

---

## 11. Files to Modify

| File | Changes |
|------|---------|
| `api/user/rentals/services/rental/cancel.py` | Update cancellation logic |
| `api/user/system/fixtures/app_config.json` | Add `NO_CHARGE_RENTAL_CANCELLATION_TIME` |
| `api/user/notifications/fixtures/templates.json` | Add cancellation templates |

---

## Approval Required

Please confirm:
- [ ] Free cancellation window of 5 minutes is correct
- [ ] Late cancellation should apply late fee (not block entirely)
- [ ] POSTPAID cancellation should charge from wallet
- [ ] Fine transaction type should be used for cancellation fees

---
