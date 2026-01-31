# Pay-Due Endpoint Verification & Gap Analysis

> **Version:** 1.0  
> **Created:** 2026-01-30  
> **Status:** REVIEW REQUIRED

---

## 1. Current Implementation Analysis

### 1.1 Endpoint Location

**File:** `api/user/rentals/views/support_views.py`  
**Endpoint:** `POST /api/rentals/{rental_id}/pay-due`  
**Class:** `RentalPayDueView`

### 1.2 Current Flow (Verified from Code)

```python
# Current implementation in RentalPayDueView.post():

1. Get rental by ID for user
2. Check if payment_status == 'PAID' → Block: "dues_already_paid"
3. Calculate payment options using PaymentCalculationService
4. Check is_sufficient → Block if insufficient balance
5. Call RentalPaymentService.pay_rental_due()
6. Return transaction details
```

### 1.3 Current `pay_rental_due()` Logic (from rental_payment.py)

```python
def pay_rental_due(self, user, rental, payment_breakdown):
    # Creates Transaction(type='RENTAL_DUE', status='SUCCESS')
    # Deducts points if used
    # Deducts wallet if used
    # Sets rental.overdue_amount = 0
    # Sets rental.payment_status = 'PAID'
    # Sets rental.status = 'COMPLETED'  ← THIS IS A GAP
```

---

## 2. Gap Analysis

### 2.1 Critical Gaps Identified

| Gap ID | Description | Severity |
|--------|-------------|----------|
| **GAP-1** | Status change to COMPLETED assumes powerbank returned | HIGH |
| **GAP-2** | No validation that rental is actually returnable | HIGH |
| **GAP-3** | No check for rental status (could pay on CANCELLED) | MEDIUM |
| **GAP-4** | No notification sent after payment | LOW |
| **GAP-5** | No revenue distribution trigger after payment | HIGH |

### 2.2 Gap Details

#### GAP-1: Status Change to COMPLETED

**Problem:** `pay_rental_due()` sets `rental.status = 'COMPLETED'` unconditionally.

**Scenario:**
1. User has OVERDUE rental (powerbank still out)
2. User calls pay-due endpoint
3. Payment succeeds, status becomes COMPLETED
4. But powerbank is NOT returned - inconsistent state

**Expected:** 
- If powerbank NOT returned: Clear dues but keep status as ACTIVE/OVERDUE
- If powerbank already returned: Set status to COMPLETED

#### GAP-2: No Rental Status Validation

**Problem:** Endpoint doesn't check current rental status.

**Valid States for pay-due:**
- `OVERDUE` - Yes, pay late fees
- `COMPLETED` with `payment_status='PENDING'` - Yes, pay remaining
- `ACTIVE` with `payment_status='PENDING'` (POSTPAID) - Yes, pay usage

**Invalid States:**
- `CANCELLED` - No, rental already ended
- `PENDING` / `PENDING_POPUP` - No, rental not started

#### GAP-3: POSTPAID vs Overdue Confusion

**Problem:** Current code treats all pay-due as same scenario.

**Two Different Scenarios:**
1. **POSTPAID Payment:** Rental returned, need to pay usage charges
2. **Overdue Payment:** Rental may or may not be returned, need to pay late fees

---

## 3. Current vs Expected Behavior

### 3.1 Scenario Matrix

| Scenario | Rental Status | Powerbank | Current Behavior | Expected Behavior |
|----------|---------------|-----------|------------------|-------------------|
| POSTPAID returned normally | COMPLETED | Returned | Set COMPLETED (correct) | Set COMPLETED |
| POSTPAID with late fees | COMPLETED | Returned | Set COMPLETED (correct) | Set COMPLETED |
| OVERDUE - powerbank out | OVERDUE | NOT Returned | Set COMPLETED (WRONG) | Keep OVERDUE, clear dues only |
| OVERDUE - powerbank returned | OVERDUE | Returned | Set COMPLETED (correct) | Set COMPLETED |
| ACTIVE POSTPAID - user wants to pay early | ACTIVE | NOT Returned | Set COMPLETED (WRONG) | Keep ACTIVE, record payment |

### 3.2 Payment Status vs Rental Status

| rental.status | payment_status | Action Allowed |
|---------------|----------------|----------------|
| ACTIVE | PENDING | Pay-due allowed (POSTPAID partial) |
| ACTIVE | PAID | Pay-due blocked |
| OVERDUE | PENDING | Pay-due allowed |
| OVERDUE | PAID | Pay-due blocked |
| COMPLETED | PENDING | Pay-due allowed |
| COMPLETED | PAID | Pay-due blocked |
| CANCELLED | * | Pay-due blocked |
| PENDING | * | Pay-due blocked |
| PENDING_POPUP | * | Pay-due blocked |

---

## 4. Proposed Fix

### 4.1 Updated Endpoint Validation

```python
# In RentalPayDueView.post():

def operation():
    rental = Rental.objects.get(id=rental_id, user=request.user)
    
    # 1. Validate rental status
    if rental.status in ['PENDING', 'PENDING_POPUP', 'CANCELLED']:
        raise ServiceException(
            detail="Cannot pay dues for this rental",
            code="invalid_rental_status"
        )
    
    # 2. Check if dues already paid
    if rental.payment_status == 'PAID':
        raise ServiceException(
            detail="Rental dues have already been settled",
            code="dues_already_paid"
        )
    
    # 3. Calculate total dues
    total_due = rental.amount_paid + rental.current_overdue_amount
    if total_due <= 0:
        raise ServiceException(
            detail="No outstanding dues for this rental",
            code="no_dues_pending"
        )
    
    # 4. Check if powerbank returned (for status determination)
    is_powerbank_returned = (
        rental.ended_at is not None or 
        (rental.power_bank and rental.power_bank.current_station is not None)
    )
    
    # Continue with payment...
```

### 4.2 Updated `pay_rental_due()` Service

```python
def pay_rental_due(
    self, 
    user, 
    rental, 
    payment_breakdown: Dict[str, Any],
    is_powerbank_returned: bool = True  # NEW PARAMETER
) -> Transaction:
    """Pay outstanding rental dues"""
    try:
        # ... existing payment logic ...
        
        # Clear rental dues
        rental.overdue_amount = Decimal('0')
        rental.payment_status = 'PAID'
        
        # NEW: Only set COMPLETED if powerbank is returned
        if is_powerbank_returned:
            rental.status = 'COMPLETED'
            update_fields = ['overdue_amount', 'payment_status', 'status', 'updated_at']
        else:
            # Keep current status (ACTIVE or OVERDUE), just clear payment dues
            update_fields = ['overdue_amount', 'payment_status', 'updated_at']
        
        rental.save(update_fields=update_fields)
        
        # NEW: Trigger revenue distribution if transaction succeeded
        if transaction_obj.status == 'SUCCESS':
            from api.partners.common.services import RevenueDistributionService
            rev_service = RevenueDistributionService()
            rev_service.create_revenue_distribution(transaction_obj, rental)
        
        # NEW: Send notification
        from api.user.notifications.services import notify
        notify(
            user,
            'payment_due_settled',
            rental_code=rental.rental_code,
            amount=float(total_amount)
        )
        
        return transaction_obj
```

---

## 5. Edge Cases

### 5.1 POSTPAID Early Payment

**Scenario:** User with POSTPAID rental wants to pay before returning.

**Current:** Not possible (no dues until return)
**Expected:** 
- If rental is ACTIVE with POSTPAID, calculate current usage
- Allow payment of current usage amount
- Keep rental ACTIVE until powerbank returned

**Implementation Decision Needed:**
- Should early payment be allowed?
- If yes, how to calculate partial usage?

### 5.2 Multiple Payment Attempts

**Scenario:** User tries to pay but has only partial balance.

**Current:** Blocked with "insufficient balance"
**Expected:** Same (correct behavior)

### 5.3 Wallet vs Points Priority

**Current:** Uses `PaymentCalculationService.calculate_payment_options()` which has existing priority logic.

**Verified:** Points used first, then wallet (existing behavior is correct).

---

## 6. Response Format Updates

### 6.1 Current Response

```json
{
  "transaction_id": "TXN-XXXXX",
  "rental_id": "uuid",
  "amount_paid": 100.00,
  "payment_breakdown": {
    "points_used": 50,
    "points_amount": 50.00,
    "wallet_used": 50.00
  },
  "payment_status": "PAID",
  "account_unblocked": true
}
```

### 6.2 Proposed Response (Enhanced)

```json
{
  "transaction_id": "TXN-XXXXX",
  "rental_id": "uuid",
  "rental_code": "RNT-XXXXX",
  "amount_paid": 100.00,
  "payment_breakdown": {
    "points_used": 50,
    "points_amount": 50.00,
    "wallet_used": 50.00
  },
  "dues_breakdown": {
    "usage_charge": 80.00,
    "late_fee": 20.00,
    "total": 100.00
  },
  "rental_status": "COMPLETED",
  "payment_status": "PAID",
  "powerbank_returned": true,
  "account_unblocked": true
}
```

---

## 7. Notification Template Required

### 7.1 New Template

| Slug | Title | Message |
|------|-------|---------|
| `payment_due_settled` | Payment Successful | Your outstanding dues of Rs. {{amount}} for rental {{rental_code}} have been settled. Thank you! |

---

## 8. Integration with Revenue Distribution

### 8.1 Current State

- `pay_rental_due()` creates Transaction with `type='RENTAL_DUE'`
- NO revenue distribution is triggered

### 8.2 Required Integration

When pay-due transaction succeeds:
1. Get rental's station
2. Look up station hierarchy (franchise/vendor)
3. Calculate revenue shares
4. Create RevenueDistribution record
5. Update partner balances

**Note:** This uses the same `RevenueDistributionService` planned in the refactoring document.

---

## 9. Files to Modify

| File | Changes |
|------|---------|
| `api/user/rentals/views/support_views.py` | Add status validation, pass return flag |
| `api/user/payments/services/rental_payment.py` | Conditional status change, revenue trigger |
| `api/user/notifications/fixtures/templates.json` | Add payment_due_settled template |

---

## 10. Testing Scenarios

| Test | Input | Expected Output |
|------|-------|-----------------|
| Pay OVERDUE with powerbank out | OVERDUE rental, PB not in slot | Payment success, status stays OVERDUE |
| Pay OVERDUE with powerbank returned | OVERDUE rental, PB in slot | Payment success, status COMPLETED |
| Pay COMPLETED pending | COMPLETED with payment_status=PENDING | Payment success, status COMPLETED |
| Pay already paid | payment_status=PAID | Error: dues_already_paid |
| Pay cancelled | status=CANCELLED | Error: invalid_rental_status |
| Pay with insufficient balance | balance < dues | Error: insufficient_funds |

---

## Approval Required

Please confirm:
- [ ] Pay-due should NOT auto-complete rental if powerbank not returned
- [ ] Early payment for POSTPAID (while rental active) - allowed or blocked?
- [ ] Revenue distribution should trigger on pay-due success
- [ ] Notification template for payment settled

---
