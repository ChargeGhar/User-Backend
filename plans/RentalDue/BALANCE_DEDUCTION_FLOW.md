# Balance Deduction Flow - Rental Start

**Date:** 2026-02-13 23:47  
**Question:** When are balances deducted - before or after popup?

---

## Answer: BEFORE POPUP ✅

**Balances are deducted BEFORE the powerbank popup happens**

---

## Complete Flow

### Step 1: Validation (No Deduction)
```
1. Validate user prerequisites
2. Validate station availability
3. Check balance sufficiency
4. Validate payment method (if needed)
```

### Step 2: Create Rental (No Deduction)
```
Rental.objects.create(
    status='PENDING_POPUP',
    amount_paid=0,
    payment_status='PENDING'
)
```

### Step 3: Process Payment (✅ DEDUCTION HAPPENS HERE)
```python
# PREPAID packages
if package.payment_model == 'PREPAID':
    process_prepayment(...)  # ✅ Deducts wallet/points HERE
    rental.amount_paid = actual_price
    rental.payment_status = 'PAID'
    rental.save()
```

**Inside `process_prepayment()`:**
```python
def process_prepayment(...):
    # Calculate payment options
    payment_options = calculate_payment_options(...)
    
    # Process payment (THIS DEDUCTS BALANCE)
    return payment_service.process_rental_payment(...)
```

**Inside `process_rental_payment()`:**
```python
def process_rental_payment(...):
    # Create transaction
    transaction = create_transaction(...)
    
    # ✅ DEDUCT POINTS
    if points_to_use > 0:
        deduct_points(user, points_to_use, ...)
    
    # ✅ DEDUCT WALLET
    if wallet_amount > 0:
        wallet_service.deduct_balance(user, wallet_amount, ...)
    
    return transaction
```

### Step 4: Trigger Popup (After Deduction)
```python
popup_success, popup_result_sn = trigger_device_popup(...)
```

### Step 5: Handle Popup Result

**If Popup Success:**
```python
rental.status = 'ACTIVE'
rental.started_at = now()
rental.save()
# Balances already deducted ✅
```

**If Popup Fails:**
```python
rental.status = 'PENDING_POPUP'
rental.rental_metadata['popup_message'] = 'timeout/failure'
rental.save()
# Balances already deducted ❌ (need refund)
```

---

## Timeline

```
Time    Action                          Balance Status
────────────────────────────────────────────────────────────
T0      User clicks "Start Rental"      Wallet: 100, Points: 0
T1      Validation passes               Wallet: 100, Points: 0
T2      Rental created (PENDING_POPUP)  Wallet: 100, Points: 0
T3      process_prepayment() called     
T4      ✅ DEDUCT WALLET/POINTS         Wallet: 50, Points: 0  ← DEDUCTED
T5      rental.payment_status = 'PAID'  Wallet: 50, Points: 0
T6      Trigger device popup            Wallet: 50, Points: 0
T7      Wait for popup response...      Wallet: 50, Points: 0
T8      Popup success                   Wallet: 50, Points: 0
T9      rental.status = 'ACTIVE'        Wallet: 50, Points: 0
```

---

## Code Evidence

### Location 1: core.py Line 283
```python
# Create rental
rental = Rental.objects.create(
    status='PENDING_POPUP',
    amount_paid=Decimal('0'),  # Not paid yet
    ...
)

# Process payment (DEDUCTION HAPPENS HERE)
if package.payment_model == 'PREPAID':
    process_prepayment(...)  # ✅ Deducts balance
    rental.amount_paid = actual_price
    rental.payment_status = 'PAID'
    rental.save()

# Trigger popup (AFTER deduction)
popup_success, popup_result_sn = trigger_device_popup(...)
```

### Location 2: payment.py Line 71
```python
def process_prepayment(...):
    # ...
    return payment_service.process_rental_payment(...)  # ✅ Deducts here
```

### Location 3: rental_payment.py Line 45-60
```python
def process_rental_payment(...):
    # Create transaction
    transaction_obj = create_transaction(...)
    
    # ✅ DEDUCT POINTS
    if points_to_use > 0:
        deduct_points(user, points_to_use, ...)
    
    # ✅ DEDUCT WALLET
    if wallet_amount > 0:
        wallet_service.deduct_balance(user, wallet_amount, ...)
```

---

## What This Means

### For Successful Rentals
1. Balance deducted BEFORE popup ✅
2. Popup succeeds
3. Rental becomes ACTIVE
4. User gets powerbank
5. **Everything works as expected**

### For Failed Popups
1. Balance deducted BEFORE popup ✅
2. Popup fails (timeout/no powerbank)
3. Rental stays PENDING_POPUP
4. User doesn't get powerbank
5. **Balance already deducted but no powerbank!** ❌

---

## Refund Mechanism

**Question:** What happens if popup fails?

**Current Behavior:**
- Rental status: PENDING_POPUP
- Payment status: PAID
- Balance: Already deducted
- Powerbank: Not ejected

**Expected:** Refund should happen

**Check:** Is there a refund mechanism?

Let me verify...

---

## Refund Check

### Scenario: Popup Timeout

**File:** `core.py` Line 298
```python
if popup_success:
    self._handle_popup_success(...)
else:
    self.log_warning(f"Rental {rental.rental_code} popup pending verification")
    # ❌ No refund logic here
```

**Finding:** No automatic refund on popup failure

**Implication:** 
- User's balance is deducted
- Rental stays in PENDING_POPUP
- Manual intervention may be needed

---

## Summary

### When Balances Are Deducted

**Answer:** BEFORE popup

**Sequence:**
1. Create rental (PENDING_POPUP)
2. ✅ **Deduct wallet/points** ← HERE
3. Set payment_status = 'PAID'
4. Trigger popup
5. Wait for result
6. Update status based on result

### Why This Design?

**Pros:**
- Ensures payment before service
- Prevents race conditions
- Simpler transaction flow

**Cons:**
- Balance deducted even if popup fails
- Requires refund mechanism for failures
- User charged without getting powerbank (if popup fails)

### Risk

**Medium:** If popup fails frequently, users lose money without getting service

**Mitigation:** 
- Robust popup mechanism
- Automatic refund on failure
- Manual refund process
- Monitoring popup success rate

---

## Recommendation

**Current Status:** ✅ Working as designed

**Potential Improvement:** Add automatic refund on popup failure

**Priority:** MEDIUM (depends on popup failure rate)

---

## Conclusion

**Balance Deduction Timing:** BEFORE popup ✅

**Flow:**
1. Validate
2. Create rental
3. **Deduct balance** ← BEFORE popup
4. Trigger popup
5. Handle result

**Risk:** Balance deducted even if popup fails

**Mitigation:** Refund mechanism (check if exists)
