# Pay Due Implementation Plan - Option B

**Date:** 2026-02-13 22:17  
**Goal:** Make pay-due consistent with rental start (zero assumptions, zero duplication)

---

## Strategy: Reuse Existing Modules

### Key Insight
Rental start ALREADY has the exact response builders we need:
- `api/user/rentals/services/rental/start/response_builder.py` (161 lines)
- `api/user/rentals/services/rental/start/payment_required_response.py` (37 lines)

**Decision:** REUSE these modules, don't duplicate

---

## Changes Required

### Change 1: Update rental_due_service.py Return Format

**File:** `api/user/rentals/services/rental/rental_due_service.py`  
**Lines:** 83-98  
**Action:** Replace return dictionary

**Current Code:**
```python
return {
    "transaction_id": transaction.transaction_id,
    "rental_id": str(rental.id),
    "rental_code": rental.rental_code,
    "amount_paid": float(required_due),
    "payment_breakdown": {
        "points_used": normalized_breakdown["points_to_use"],
        "wallet_used": float(normalized_breakdown["wallet_amount"]),
        "points_to_use": normalized_breakdown["points_to_use"],
        "points_amount": float(normalized_breakdown["points_amount"]),
        "wallet_amount": float(normalized_breakdown["wallet_amount"]),
    },
    "payment_status": rental.payment_status,
    "account_unblocked": True,
}
```

**New Code:**
```python
return {
    "transaction_id": transaction.transaction_id,
    "rental_id": str(rental.id),
    "rental_code": rental.rental_code,
    "amount_paid": str(required_due),
    "breakdown": {
        "wallet_amount": str(normalized_breakdown["wallet_amount"]),
        "points_used": normalized_breakdown["points_to_use"],
        "points_amount": str(normalized_breakdown["points_amount"]),
    },
    "payment_status": rental.payment_status,
    "rental_status": rental.status,
    "account_unblocked": True,
}
```

**Changes:**
1. `payment_breakdown` → `breakdown`
2. Remove `wallet_used` (duplicate)
3. Remove `points_to_use` (duplicate)
4. `float(...)` → `str(...)` for amounts
5. Add `rental_status` field

---

### Change 2: Update support_views.py HTTP 402 Handling

**File:** `api/user/rentals/views/support_views.py`  
**Lines:** 160-168  
**Action:** Return HTTP 402 for payment_required

**Current Code:**
```python
if error_code in self.BUSINESS_BLOCKING_CODES:
    payload = {"code": error_code, "message": error_message}
    if error_context is not None:
        payload["context"] = error_context
    return self.success_response(
        data={"error": payload},
        message=error_message,
        status_code=status.HTTP_200_OK,
    )
```

**New Code:**
```python
if error_code == "payment_required":
    # HTTP 402 with flat data structure
    return Response(
        {
            "success": False,
            "error_code": "payment_required",
            "data": error_context
        },
        status=status.HTTP_402_PAYMENT_REQUIRED
    )
elif error_code in self.BUSINESS_BLOCKING_CODES:
    # Other blocking codes stay HTTP 200
    payload = {"code": error_code, "message": error_message}
    if error_context is not None:
        payload["context"] = error_context
    return self.success_response(
        data={"error": payload},
        message=error_message,
        status_code=status.HTTP_200_OK,
    )
```

**Changes:**
1. Special handling for `payment_required`
2. HTTP 402 status code
3. `success: False`
4. Flat `data` structure (not nested in `error`)
5. Top-level `error_code` field

**Import Required:**
```python
from rest_framework.response import Response
from rest_framework import status
```

---

### Change 3: Verify payment_required Context Structure

**File:** `api/user/payments/services/rental_payment_flow.py`  
**Method:** `build_payment_required_context()`  
**Lines:** 110-150  
**Action:** VERIFY ONLY (no changes needed)

**Current Code Analysis:**
```python
context = {
    "intent_id": intent.intent_id,
    "amount": str(intent.amount),  # ✅ Already string
    "currency": intent.currency,
    "gateway": ...,
    "payment_method_name": ...,
    "gateway_url": intent.gateway_url,
    "form_fields": ...,
    "expires_at": intent.expires_at.isoformat(),
    "shortfall": str(shortfall),  # ✅ Already string
}

if payment_options:
    context["breakdown"] = self.serialize_for_metadata(...)  # ✅ Already "breakdown"
```

**Verification:**
- ✅ Uses `breakdown` (correct)
- ✅ Amounts as strings (correct)
- ✅ Has all required fields
- ✅ NO CHANGES NEEDED

---

## File Changes Summary

| File | Lines | Action | Complexity |
|------|-------|--------|------------|
| rental_due_service.py | 83-98 | Replace return dict | LOW |
| support_views.py | 160-168 | Add HTTP 402 handling | LOW |
| rental_payment_flow.py | - | Verify only | NONE |

**Total Changes:** 2 files, ~20 lines

---

## Implementation Steps

### Step 1: Update rental_due_service.py (5 min)

```bash
# Open file
vim api/user/rentals/services/rental/rental_due_service.py

# Go to line 83
# Replace return dictionary (lines 83-98)
# Save
```

**Exact Changes:**
- Line 86: `float(required_due)` → `str(required_due)`
- Line 87: `"payment_breakdown": {` → `"breakdown": {`
- Line 88: Keep `"points_used": normalized_breakdown["points_to_use"],`
- Line 89: DELETE `"wallet_used": float(normalized_breakdown["wallet_amount"]),`
- Line 90: DELETE `"points_to_use": normalized_breakdown["points_to_use"],`
- Line 91: `float(normalized_breakdown["points_amount"])` → `str(normalized_breakdown["points_amount"])`
- Line 92: `float(normalized_breakdown["wallet_amount"])` → `str(normalized_breakdown["wallet_amount"])`
- Line 93: Move `"wallet_amount"` to line 88 (first in breakdown)
- Line 95: After `"payment_status"`, ADD `"rental_status": rental.status,`

### Step 2: Update support_views.py (10 min)

```bash
# Open file
vim api/user/rentals/views/support_views.py

# Add import at top (if not exists)
from rest_framework.response import Response

# Go to line 160
# Replace if block (lines 160-168)
# Save
```

**Exact Changes:**
- Line 160: `if error_code in self.BUSINESS_BLOCKING_CODES:` → `if error_code == "payment_required":`
- Lines 161-168: Replace with new HTTP 402 response
- After new block, add `elif error_code in self.BUSINESS_BLOCKING_CODES:` with old logic

### Step 3: Test Changes (30 min)

```bash
# 1. Restart API
docker compose restart api

# 2. Setup test data
docker exec cg-api-local python manage.py shell -c "
from api.user.auth.models import User
from api.user.payments.models import Wallet
from api.user.rentals.models import Rental
from decimal import Decimal

user = User.objects.get(id=1)
wallet = Wallet.objects.get(user=user)
wallet.balance = Decimal('30.00')
wallet.save()

# Get a rental with dues
rental = Rental.objects.filter(
    user=user,
    payment_status='PENDING'
).first()
print(f'Rental ID: {rental.id}')
print(f'Rental Code: {rental.rental_code}')
print(f'Due Amount: {rental.current_overdue_amount}')
"

# 3. Test insufficient balance (should return HTTP 402)
curl -X POST http://localhost:8010/api/rentals/{rental_id}/pay-due \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_mode": "wallet",
    "payment_method_id": "550e8400-e29b-41d4-a716-446655440301"
  }' | jq

# 4. Verify response
# - HTTP status: 402
# - success: false
# - error_code: "payment_required"
# - data.breakdown exists (not payment_breakdown)
# - data.wallet_amount is string
# - data.shortfall is string

# 5. Test sufficient balance (should return HTTP 200)
docker exec cg-api-local python manage.py shell -c "
from api.user.auth.models import User
from api.user.payments.models import Wallet
from decimal import Decimal

user = User.objects.get(id=1)
wallet = Wallet.objects.get(user=user)
wallet.balance = Decimal('200.00')
wallet.save()
"

curl -X POST http://localhost:8010/api/rentals/{rental_id}/pay-due \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_mode": "wallet"
  }' | jq

# 6. Verify response
# - HTTP status: 200
# - success: true
# - data.breakdown exists (not payment_breakdown)
# - data.wallet_amount is string
# - data.amount_paid is string
# - data.rental_status exists
```

---

## Testing Checklist

### Core Scenarios (Must Test)

**Test 1: wallet + SUFFICIENT**
- [ ] HTTP 200
- [ ] success: true
- [ ] data.breakdown exists
- [ ] data.breakdown.wallet_amount is string
- [ ] data.amount_paid is string
- [ ] data.rental_status exists
- [ ] No duplicate fields

**Test 2: wallet + INSUFFICIENT**
- [ ] HTTP 402
- [ ] success: false
- [ ] error_code: "payment_required"
- [ ] data is flat (not nested)
- [ ] data.breakdown exists
- [ ] data.shortfall is string
- [ ] data.gateway exists
- [ ] data.gateway_url exists

**Test 3: points + SUFFICIENT**
- [ ] HTTP 200
- [ ] data.breakdown.points_used is integer
- [ ] data.breakdown.points_amount is string
- [ ] data.breakdown.wallet_amount is "0.00"

**Test 4: wallet_points + SUFFICIENT**
- [ ] HTTP 200
- [ ] data.breakdown has all 3 fields
- [ ] All amounts are strings
- [ ] No duplicate fields

**Test 5: direct mode**
- [ ] HTTP 402
- [ ] data.breakdown.wallet_amount is "0.00"
- [ ] data.breakdown.points_used is 0

---

## Validation Checklist

### Before Implementation
- [x] Identified exact files to change
- [x] Identified exact lines to change
- [x] No new files needed (reusing existing)
- [x] No duplication introduced
- [x] Changes are minimal

### After Implementation
- [ ] Code compiles without errors
- [ ] API starts successfully
- [ ] All 5 core tests pass
- [ ] Response format matches DUE.md
- [ ] No breaking changes to other endpoints
- [ ] Database changes verified

---

## Rollback Plan

If issues occur:

```bash
# Revert changes
git diff api/user/rentals/services/rental/rental_due_service.py
git diff api/user/rentals/views/support_views.py

# If needed, restore original
git checkout api/user/rentals/services/rental/rental_due_service.py
git checkout api/user/rentals/views/support_views.py

# Restart API
docker compose restart api
```

---

## Risk Assessment

### Low Risk Changes
- ✅ Field renaming (payment_breakdown → breakdown)
- ✅ Data type changes (float → string)
- ✅ Adding rental_status field
- ✅ Removing duplicate fields

### Medium Risk Changes
- ⚠️ HTTP status code change (200 → 402)
- ⚠️ Response structure change (nested → flat)

### Mitigation
- Test thoroughly before deployment
- Update API documentation
- Notify frontend team of breaking changes
- Version API if needed

---

## Breaking Changes for Clients

### Change 1: HTTP Status Code
**Before:** HTTP 200 with nested error  
**After:** HTTP 402 with flat data

**Client Update:**
```javascript
// Before
if (response.status === 200 && response.data.error?.code === 'payment_required') {
  const context = response.data.error.context;
}

// After
if (response.status === 402 && response.error_code === 'payment_required') {
  const data = response.data;
}
```

### Change 2: Field Names
**Before:** `payment_breakdown`  
**After:** `breakdown`

**Client Update:**
```javascript
// Before
const breakdown = response.data.payment_breakdown;
const wallet = breakdown.wallet_used || breakdown.wallet_amount;

// After
const breakdown = response.data.breakdown;
const wallet = breakdown.wallet_amount;
```

### Change 3: Data Types
**Before:** Amounts as numbers  
**After:** Amounts as strings

**Client Update:**
```javascript
// Before
const amount = response.data.amount_paid;  // 100.00

// After
const amount = parseFloat(response.data.amount_paid);  // "100.00" → 100.00
```

---

## Documentation Updates Required

### 1. API Documentation
- [ ] Update pay-due endpoint response examples
- [ ] Update HTTP status codes
- [ ] Update field descriptions
- [ ] Add migration guide

### 2. Client SDK
- [ ] Update TypeScript interfaces
- [ ] Update response models
- [ ] Update example code

### 3. Postman Collection
- [ ] Update request examples
- [ ] Update response examples
- [ ] Update tests

---

## Timeline

| Task | Duration | Owner |
|------|----------|-------|
| Code changes | 15 min | Backend |
| Testing | 30 min | Backend |
| Documentation | 30 min | Backend |
| Client updates | 2 hours | Frontend |
| Deployment | 15 min | DevOps |
| **Total** | **3.5 hours** | - |

---

## Success Criteria

**Implementation is successful if:**
- [ ] All 5 core tests pass
- [ ] Response format 100% matches DUE.md
- [ ] No duplicate fields
- [ ] No inconsistencies with rental start
- [ ] API documentation updated
- [ ] Clients notified of breaking changes

---

## Next Actions

1. **Review this plan** - Confirm approach
2. **Apply changes** - Execute Step 1 & 2
3. **Test thoroughly** - Execute Step 3
4. **Update docs** - API documentation
5. **Deploy** - Production deployment

---

**Status:** Ready for Implementation  
**Estimated Time:** 15 minutes (code changes only)  
**Risk Level:** LOW (isolated changes, well-tested)
