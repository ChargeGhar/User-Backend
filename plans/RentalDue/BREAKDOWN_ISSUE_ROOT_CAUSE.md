# Breakdown Display Issue - Root Cause Analysis

**Date:** 2026-02-13 23:38  
**Status:** ✅ ROOT CAUSE IDENTIFIED

---

## Issue Summary

**Problem:** Response `breakdown.points_used` shows 0 instead of actual points deducted

**Example:**
```json
// Response
{
  "breakdown": {
    "wallet_amount": "0.00",
    "points_used": 0,           // ❌ Shows 0
    "points_amount": "50.00"
  }
}

// Actual Deduction
{
  "wallet": 0,
  "points": 500                 // ✅ Actually deducted 500
}
```

---

## Root Cause Investigation

### Step 1: Check Response Builder

**File:** `api/user/rentals/services/rental/start/response_builder.py`  
**Function:** `build_payment_breakdown()`  
**Lines:** 77-120

**Code:**
```python
def build_payment_breakdown(rental):
    # Try to get from transaction
    txn = Transaction.objects.filter(
        rental=rental,
        transaction_type='RENTAL',
        status='SUCCESS'
    ).first()
    
    if txn and txn.transaction_metadata:
        breakdown = txn.transaction_metadata.get('payment_breakdown', {})
        return {
            'wallet_amount': str(breakdown.get('wallet_amount', '0.00')),
            'points_used': int(breakdown.get('points_used', 0)),
            'points_amount': str(breakdown.get('points_amount', '0.00'))
        }
```

**Finding:** Response builder tries to get breakdown from `transaction.transaction_metadata`

---

### Step 2: Check Transaction Creation

**File:** `api/user/payments/services/rental_payment.py`  
**Function:** `process_rental_payment()`  
**Lines:** 20-80

**Code:**
```python
def process_rental_payment(self, user, rental, payment_breakdown):
    # ...
    transaction_obj = TransactionRepository.create(
        user=user,
        transaction_id=generate_transaction_id(),
        transaction_type='RENTAL',
        amount=total_amount,
        status='SUCCESS',
        payment_method_type='...',
        related_rental=rental
        # ❌ NO transaction_metadata parameter
    )
```

**Finding:** Transaction is created WITHOUT `transaction_metadata`

---

### Step 3: Check Actual Transaction

**Query:**
```sql
SELECT transaction_metadata FROM transactions 
WHERE transaction_type='RENTAL' 
ORDER BY created_at DESC LIMIT 1;
```

**Result:** `{}` (empty dict)

**Confirmation:** Transaction metadata is NOT being saved

---

## Root Cause

**Issue:** `payment_breakdown` is NOT saved to `transaction.transaction_metadata`

**Location:** `api/user/payments/services/rental_payment.py` line ~35

**Current Code:**
```python
transaction_obj = TransactionRepository.create(
    user=user,
    transaction_id=generate_transaction_id(),
    transaction_type='RENTAL',
    amount=total_amount,
    status='SUCCESS',
    payment_method_type='...',
    related_rental=rental
    # Missing: transaction_metadata
)
```

**Should Be:**
```python
transaction_obj = TransactionRepository.create(
    user=user,
    transaction_id=generate_transaction_id(),
    transaction_type='RENTAL',
    amount=total_amount,
    status='SUCCESS',
    payment_method_type='...',
    related_rental=rental,
    transaction_metadata={
        'payment_breakdown': {
            'wallet_amount': str(wallet_amount),
            'points_used': points_to_use,
            'points_amount': str(points_amount)
        }
    }
)
```

---

## Why Response Shows Incorrect Values

### Current Flow

1. **Transaction created** without metadata ❌
2. **Response builder** tries to read from transaction metadata
3. **Metadata is empty** → falls back to rental metadata
4. **Rental metadata** doesn't have payment_breakdown
5. **Fallback logic** infers from payment_mode
6. **Inference is wrong** for wallet_points mode

### Fallback Logic Issue

**File:** `response_builder.py` lines 115-120

**Code:**
```python
# Fallback: infer from payment mode
if payment_mode == 'wallet':
    return {
        'wallet_amount': str(rental.amount_paid),
        'points_used': 0,
        'points_amount': '0.00'
    }
elif payment_mode == 'points':
    return {
        'wallet_amount': '0.00',
        'points_used': 0,  # ❌ Should calculate from amount_paid
        'points_amount': str(rental.amount_paid)
    }
```

**Issue:** Fallback logic sets `points_used: 0` instead of calculating actual points

---

## Impact Analysis

### What's Affected

1. **Response breakdown** - Shows incorrect points_used
2. **User-facing display** - Misleading information
3. **API clients** - Receive wrong data

### What's NOT Affected

1. **Actual deductions** - ✅ Correct (500 points deducted)
2. **Database records** - ✅ Accurate
3. **Balance updates** - ✅ Working
4. **Transaction amount** - ✅ Correct (NPR 50.00)
5. **Payment processing** - ✅ Functional

---

## Fix Required

### Option 1: Save Metadata to Transaction (RECOMMENDED)

**File:** `api/user/payments/services/rental_payment.py`  
**Location:** Line ~35

**Change:**
```python
transaction_obj = TransactionRepository.create(
    user=user,
    transaction_id=generate_transaction_id(),
    transaction_type='RENTAL',
    amount=total_amount,
    status='SUCCESS',
    payment_method_type=payment_method_type,
    related_rental=rental,
    transaction_metadata={  # ADD THIS
        'payment_breakdown': {
            'wallet_amount': str(wallet_amount),
            'points_used': points_to_use,
            'points_amount': str(points_amount)
        }
    }
)
```

**Benefits:**
- Accurate breakdown in response
- Historical record of payment split
- No fallback logic needed

---

### Option 2: Fix Fallback Logic

**File:** `response_builder.py`  
**Location:** Lines 115-120

**Change:**
```python
elif payment_mode == 'points':
    # Calculate actual points used
    points_used = int(rental.amount_paid * 10)  # 10 points = NPR 1
    return {
        'wallet_amount': '0.00',
        'points_used': points_used,
        'points_amount': str(rental.amount_paid)
    }
```

**Benefits:**
- Quick fix
- No database changes

**Drawbacks:**
- Still relies on inference
- Less accurate for complex scenarios

---

## Recommendation

**Implement Option 1** (Save metadata to transaction)

**Reasons:**
1. More accurate
2. Creates historical record
3. Consistent with pay-due implementation
4. Better for auditing
5. Eliminates need for fallback logic

**Effort:** 5 minutes  
**Risk:** LOW  
**Impact:** HIGH (fixes display issue completely)

---

## Verification Steps

After fix:

1. Create rental with wallet_points mode
2. Check transaction.transaction_metadata
3. Verify breakdown in response
4. Confirm points_used shows correct value
5. Test all payment modes

---

## Conclusion

**Root Cause:** Transaction created without `transaction_metadata`

**Impact:** Display issue only (actual deductions correct)

**Fix:** Add `transaction_metadata` when creating transaction

**Priority:** MEDIUM (functional but misleading)

**Estimated Fix Time:** 5 minutes
