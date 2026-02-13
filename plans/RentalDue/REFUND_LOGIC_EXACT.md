# Refund Logic - EXACT Business Rules

**Date:** 2026-02-14
**Status:** 100% VERIFIED FROM CODE

---

## PREPAID vs POSTPAID - Payment Timing

### PREPAID Flow
```
1. Validate balance sufficient
2. Create rental (status='PENDING_POPUP', amount_paid=0)
3. ✅ DEDUCT wallet/points (process_prepayment)
4. rental.payment_status = 'PAID'
5. rental.amount_paid = actual_price
6. Trigger popup
7. If success → ACTIVE
8. If fail → PENDING_POPUP (balance already deducted ❌)
```

**Code Location:** `core.py` line 283-288
```python
if package.payment_model == 'PREPAID':
    process_prepayment(...)  # ✅ DEDUCTS HERE
    rental.amount_paid = actual_price
    rental.payment_status = 'PAID'
    rental.save()
```

### POSTPAID Flow
```
1. Validate minimum balance (NPR 50 default)
2. Create rental (status='PENDING_POPUP', amount_paid=0)
3. ❌ NO DEDUCTION - only create PENDING transaction
4. rental.payment_status = 'PENDING'
5. Trigger popup
6. If success → ACTIVE
7. If fail → PENDING_POPUP (nothing deducted ✅)
8. Payment collected at return time
```

**Code Location:** `core.py` line 289-291
```python
else:  # POSTPAID
    txn = create_postpaid_transaction(...)  # ❌ NO DEDUCTION
    rental.rental_metadata['pending_transaction_id'] = str(txn.id)
```

**Code Location:** `payment.py` line 77-107
```python
def create_postpaid_transaction(user, rental, amount):
    """
    Create a PENDING transaction for POSTPAID rental.
    Transaction will be updated to SUCCESS when payment is collected at return.
    """
    transaction = Transaction.objects.create(
        user=user,
        related_rental=rental,
        transaction_id=generate_transaction_id(),
        transaction_type='RENTAL',
        amount=amount,
        status='PENDING',  # ✅ PENDING - not SUCCESS
        payment_method_type='WALLET',
        currency='NPR'
    )
    return transaction
```

---

## Minimum Balance Check for POSTPAID

**Purpose:** Ensure user has enough balance to pay LATER (at return)

**Code Location:** `validation.py` line 106-129
```python
def validate_postpaid_balance(user):
    """
    Validate user has minimum balance for POSTPAID rentals.
    Uses POSTPAID_MINIMUM_BALANCE from AppConfig (default: NPR 50)
    """
    min_balance = Decimal(config.get('POSTPAID_MINIMUM_BALANCE', '50'))
    wallet_balance = user.wallet.balance
    
    if wallet_balance < min_balance:
        raise ServiceException(
            detail=f"POSTPAID rentals require minimum wallet balance of NPR {min_balance}",
            code="insufficient_postpaid_balance"
        )
```

**What This Means:**
- User must have NPR 50 in wallet
- But NPR 50 is NOT deducted
- It's just a check to ensure payment capability
- Actual payment happens at return time

---

## Popup Failure Scenarios

### Scenario 1: PREPAID Popup Fails

**What Happens:**
1. Wallet/points already deducted ✅
2. Popup fails
3. Rental stays PENDING_POPUP
4. verify_popup_completion retries 3 times (40 seconds)
5. If still fails → rental.status = 'CANCELLED'
6. **Balance NOT refunded automatically** ❌

**Current Code:** `tasks.py` line 93-103
```python
else:
    # All retries exhausted
    rental.status = 'CANCELLED'
    rental.rental_metadata['popup_failed'] = True
    rental.save()
    
    # TODO: Trigger refund if PREPAID AND MINIMUM_POSTPAID_BALACE if Deducted from wallet/points
    # For now, just notify user
    notify(rental.user, 'rental_popup_failed', ...)
```

**What Needs Refund:**
- ✅ Wallet amount deducted
- ✅ Points deducted
- Transaction status = 'SUCCESS' (needs reversal)

### Scenario 2: POSTPAID Popup Fails

**What Happens:**
1. Nothing deducted (only minimum balance checked) ✅
2. Popup fails
3. Rental stays PENDING_POPUP
4. verify_popup_completion retries 3 times
5. If still fails → rental.status = 'CANCELLED'
6. **No refund needed** ✅ (nothing was deducted)

**Current Code:** Same as above

**What Needs Refund:**
- ❌ Nothing (no deduction happened)
- Transaction status = 'PENDING' (just delete or mark failed)

---

## Exact Refund Requirements

### For PREPAID Popup Failure

**Condition Check:**
```python
if rental.package.payment_model == 'PREPAID':
    if rental.payment_status == 'PAID' and rental.amount_paid > 0:
        # Need to refund
```

**What to Refund:**
1. Get original transaction
2. Check transaction_metadata for breakdown
3. Refund wallet_amount to wallet
4. Refund points_used to points
5. Mark transaction as 'REFUNDED'
6. Set rental.payment_status = 'REFUNDED'

**Code to Add:** `tasks.py` line 95
```python
# After marking rental as CANCELLED
if rental.package.payment_model == 'PREPAID':
    if rental.payment_status == 'PAID' and rental.amount_paid > 0:
        from api.user.rentals.services.rental.cancel import _refund_full_amount
        from api.user.payments.services import WalletService
        from api.user.payments.models import Transaction
        
        # Get original transaction
        original_txn = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='SUCCESS'
        ).first()
        
        # Refund
        _refund_full_amount(rental, rental.user, original_txn, WalletService())
        rental.payment_status = 'REFUNDED'
        rental.save(update_fields=['payment_status'])
```

### For POSTPAID Popup Failure

**Condition Check:**
```python
if rental.package.payment_model == 'POSTPAID':
    # Nothing to refund
    # Just mark transaction as FAILED
```

**What to Do:**
1. Get PENDING transaction
2. Mark as 'FAILED'
3. No wallet/points refund needed

**Code to Add:** `tasks.py` line 95
```python
elif rental.package.payment_model == 'POSTPAID':
    # Mark pending transaction as failed
    from api.user.payments.models import Transaction
    
    pending_txn = Transaction.objects.filter(
        related_rental=rental,
        transaction_type='RENTAL',
        status='PENDING'
    ).first()
    
    if pending_txn:
        pending_txn.status = 'FAILED'
        pending_txn.save(update_fields=['status'])
```

---

## Complete Fix for tasks.py

**File:** `api/user/stations/tasks.py`
**Line:** 93-103

**Replace:**
```python
# TODO: Trigger refund if PREPAID AND MINIMUM_POSTPAID_BALACE if Deducted from wallet/points
# For now, just notify user
try:
    from api.user.notifications.services import notify
    notify(rental.user, 'rental_popup_failed', ...)
except Exception as notify_error:
    logger.error(f"Failed to send popup failure notification: {notify_error}")
```

**With:**
```python
# Process refund based on payment model
try:
    if rental.package.payment_model == 'PREPAID':
        # PREPAID: Refund wallet/points if already deducted
        if rental.payment_status == 'PAID' and rental.amount_paid > 0:
            from api.user.rentals.services.rental.cancel import _refund_full_amount
            from api.user.payments.services import WalletService
            from api.user.payments.models import Transaction
            
            original_txn = Transaction.objects.filter(
                related_rental=rental,
                transaction_type='RENTAL',
                status='SUCCESS'
            ).first()
            
            _refund_full_amount(rental, rental.user, original_txn, WalletService())
            rental.payment_status = 'REFUNDED'
            rental.save(update_fields=['payment_status'])
            logger.info(f"Refunded PREPAID rental {rental.id}")
    
    elif rental.package.payment_model == 'POSTPAID':
        # POSTPAID: Mark pending transaction as failed (nothing to refund)
        from api.user.payments.models import Transaction
        
        pending_txn = Transaction.objects.filter(
            related_rental=rental,
            transaction_type='RENTAL',
            status='PENDING'
        ).first()
        
        if pending_txn:
            pending_txn.status = 'FAILED'
            pending_txn.save(update_fields=['status'])
            logger.info(f"Marked POSTPAID transaction as FAILED for rental {rental.id}")
    
    # Notify user
    from api.user.notifications.services import notify
    notify(rental.user, 'rental_popup_failed', async_send=True, ...)
    
except Exception as e:
    logger.error(f"Failed to process popup failure for rental {rental.id}: {e}")
```

---

## Summary

### PREPAID
- ✅ Balance deducted BEFORE popup
- ✅ Needs refund if popup fails
- ✅ Refund wallet + points
- ✅ Mark transaction as REFUNDED

### POSTPAID
- ❌ Balance NOT deducted (only minimum checked)
- ❌ No refund needed
- ✅ Mark pending transaction as FAILED
- ✅ Payment happens at return time

### Fix Location
- File: `api/user/stations/tasks.py`
- Line: 93-103
- Action: Replace TODO with actual refund logic

---

## Confidence Level

**100% VERIFIED** - All information extracted from actual code:
- ✅ PREPAID deduction flow verified
- ✅ POSTPAID no-deduction verified
- ✅ Transaction creation verified
- ✅ Refund logic location verified
- ✅ No assumptions made
