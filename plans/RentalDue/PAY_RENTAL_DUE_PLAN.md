# Pay Rental Due - Implementation Plan

**Version:** 1.0  
**Date:** 2026-02-13  
**Status:** Planning

---

## 1. Executive Summary

### Current State Analysis

**Existing Implementation:** ✅ ALREADY IMPLEMENTED (rental_due_service.py)
- Uses same payment-mode flow as rental start
- Supports: wallet, points, wallet_points, direct
- Returns HTTP 402 for payment_required
- Creates payment intents for insufficient balance
- Handles gateway top-up flow

**What's Working:**
- ✅ All 4 payment modes supported
- ✅ HTTP 402 for payment_required
- ✅ Payment intent creation
- ✅ Gateway integration (Khalti, eSewa)
- ✅ Wallet + Points calculation
- ✅ Transaction creation
- ✅ Powerbank return detection

**What Needs Verification:**
- Response format consistency with rental start
- Field naming (breakdown vs payment_breakdown)
- HTTP status codes alignment
- Error handling consistency

---

## 2. Rental Start vs Pay Due Comparison

### 2.1 Rental Start Implementation (REFERENCE)

**Files:**
```
api/user/rentals/services/rental/start/
├── core.py (336 lines) - Main orchestrator
├── payment_validator.py (149 lines) - Payment validation
├── payment_intent_builder.py (224 lines) - Intent creation
├── response_builder.py (161 lines) - Response formatting
└── payment_required_response.py (37 lines) - HTTP 402 builder
```

**Response Format:**
```json
// Success (HTTP 201)
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "...",
    "payment": {
      "breakdown": {
        "wallet_amount": "50.00",
        "points_used": 0,
        "points_amount": "0.00"
      }
    }
  }
}

// Payment Required (HTTP 402)
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "...",
    "shortfall": "30.00",
    "breakdown": {...},
    "gateway": "khalti",
    "gateway_url": "..."
  }
}
```

### 2.2 Pay Due Current Implementation

**Files:**
```
api/user/rentals/services/rental/
└── rental_due_service.py (262 lines) - Due payment orchestrator

api/user/rentals/views/
└── support_views.py (RentalPayDueView) - View handler
```

**Current Response Format:**
```json
// Success (HTTP 200) ⚠️ Should be 200, not 201
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-XXXXX",
    "rental_id": "uuid",
    "rental_code": "RNT-XXXXX",
    "amount_paid": 100.00,
    "payment_breakdown": {  // ⚠️ Should be "breakdown"
      "points_used": 50,
      "wallet_used": 50.00,
      "points_to_use": 50,  // ⚠️ Duplicate
      "points_amount": 50.00,
      "wallet_amount": 50.00  // ⚠️ Duplicate
    },
    "payment_status": "PAID",
    "account_unblocked": true
  }
}

// Payment Required (HTTP 200) ⚠️ Should be 402
{
  "success": true,  // ⚠️ Should be false
  "message": "...",
  "data": {
    "error": {  // ⚠️ Should be flat, not nested
      "code": "payment_required",
      "message": "...",
      "context": {...}
    }
  }
}
```

---

## 3. Issues Found

### Issue 1: HTTP Status Code for payment_required

**Current:** HTTP 200 with nested error object
```python
# In support_views.py line 165
if error_code in self.BUSINESS_BLOCKING_CODES:
    return self.success_response(
        data={"error": payload},
        status_code=status.HTTP_200_OK,  # ❌ WRONG
    )
```

**Expected:** HTTP 402 with flat data
```python
if error_code == "payment_required":
    return Response(
        {
            "success": False,
            "error_code": "payment_required",
            "data": context  # Flat structure
        },
        status=status.HTTP_402_PAYMENT_REQUIRED
    )
```

### Issue 2: Field Naming Inconsistency

**Current:** `payment_breakdown` (in rental_due_service.py line 96)
```python
"payment_breakdown": {
    "points_used": ...,
    "wallet_used": ...,
    "points_to_use": ...,  # Duplicate
    "points_amount": ...,
    "wallet_amount": ...   # Duplicate
}
```

**Expected:** `breakdown` (consistent with rental start)
```python
"breakdown": {
    "wallet_amount": "50.00",
    "points_used": 50,
    "points_amount": "50.00"
}
```

### Issue 3: Duplicate Fields

**Current:** Both `wallet_used` AND `wallet_amount`, `points_used` AND `points_to_use`

**Expected:** Single field per value
- `wallet_amount` (string with 2 decimals)
- `points_used` (integer)
- `points_amount` (string with 2 decimals)

### Issue 4: success: true for payment_required

**Current:** `success: true` even when payment is required

**Expected:** `success: false` for payment_required (it's a blocking condition)

---

## 4. Implementation Plan

### Phase 1: Response Format Alignment (CRITICAL)

**Goal:** Make pay-due responses identical to rental start format

#### Step 1.1: Create Response Builder Module

**File:** `api/user/rentals/services/rental/due/response_builder.py`

```python
"""Response builders for pay rental due endpoint."""

from decimal import Decimal
from typing import Any, Dict

def build_success_response(
    transaction,
    rental,
    breakdown: Dict[str, Any]
) -> Dict[str, Any]:
    """Build success response for due payment."""
    return {
        "transaction_id": transaction.transaction_id,
        "rental_id": str(rental.id),
        "rental_code": rental.rental_code,
        "amount_paid": str(transaction.amount),
        "breakdown": {
            "wallet_amount": str(breakdown["wallet_amount"]),
            "points_used": breakdown["points_to_use"],
            "points_amount": str(breakdown["points_amount"])
        },
        "payment_status": rental.payment_status,
        "rental_status": rental.status,
        "account_unblocked": True
    }

def build_payment_required_response(
    intent,
    shortfall: Decimal,
    breakdown: Dict[str, Any],
    payment_method
) -> Dict[str, Any]:
    """Build HTTP 402 payment required response."""
    return {
        "intent_id": str(intent.id),
        "amount": str(intent.amount),
        "currency": intent.currency,
        "shortfall": str(shortfall),
        "breakdown": {
            "wallet_amount": str(breakdown.get("wallet_amount", "0.00")),
            "points_used": breakdown.get("points_to_use", 0),
            "points_amount": str(breakdown.get("points_amount", "0.00"))
        },
        "gateway": payment_method.gateway.lower(),
        "payment_method_name": payment_method.name,
        "gateway_url": intent.gateway_url,
        "form_fields": intent.form_fields,
        "expires_at": intent.expires_at.isoformat()
    }
```

#### Step 1.2: Update rental_due_service.py

**Changes:**
1. Import response builder
2. Update return format in `pay_rental_due()`
3. Update `_raise_payment_gateway_required()` to use new format

**File:** `api/user/rentals/services/rental/rental_due_service.py`

```python
# Line 96 - Update return statement
from api.user.rentals.services.rental.due.response_builder import (
    build_success_response
)

return build_success_response(
    transaction=transaction,
    rental=rental,
    breakdown=normalized_breakdown
)
```

#### Step 1.3: Update support_views.py

**Changes:**
1. Return HTTP 402 for payment_required
2. Flat data structure (not nested in error object)
3. success: false for payment_required

**File:** `api/user/rentals/views/support_views.py`

```python
# Line 165 - Replace business blocking handler
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
    return self.success_response(
        data={"error": payload},
        status_code=status.HTTP_200_OK,
    )
```

### Phase 2: Serializer Validation (OPTIONAL)

**Goal:** Add same validations as rental start

**File:** `api/user/rentals/serializers/action_serializers.py`

**Current Serializer:** RentalPayDueSerializer (line 142-188)

**Add Validations:**
1. direct mode requires payment_method_id
2. Validate payment_mode choices

```python
def validate(self, attrs):
    payment_mode = attrs.get('payment_mode', 'wallet_points')
    payment_method_id = attrs.get('payment_method_id')
    
    # Validate direct mode
    if payment_mode == 'direct' and not payment_method_id:
        raise serializers.ValidationError({
            "payment_method_id": "Payment method is required for direct payment mode"
        })
    
    return attrs
```

### Phase 3: Testing

**Test Scenarios:**

| Scenario | Payment Mode | Balance | Expected Response |
|----------|--------------|---------|-------------------|
| 1 | wallet | Sufficient | HTTP 200, success: true |
| 2 | wallet | Insufficient | HTTP 402, success: false |
| 3 | points | Sufficient | HTTP 200, success: true |
| 4 | points | Insufficient | HTTP 402, success: false |
| 5 | wallet_points | Sufficient | HTTP 200, success: true |
| 6 | wallet_points | Insufficient | HTTP 402, success: false |
| 7 | direct | Any | HTTP 402, success: false |
| 8 | wallet | Insufficient + no payment_method_id | HTTP 400, payment_method_required |

---

## 5. File Structure (After Implementation)

```
api/user/rentals/services/rental/
├── start/
│   ├── core.py
│   ├── payment_validator.py
│   ├── payment_intent_builder.py
│   ├── response_builder.py
│   └── payment_required_response.py
├── due/
│   └── response_builder.py (NEW)
└── rental_due_service.py (UPDATE)

api/user/rentals/views/
└── support_views.py (UPDATE)

api/user/rentals/serializers/
└── action_serializers.py (UPDATE - optional)
```

---

## 6. Response Format Specification

### 6.1 Success Response (HTTP 200)

```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-XXXXX",
    "rental_id": "uuid",
    "rental_code": "RNT-XXXXX",
    "amount_paid": "100.00",
    "breakdown": {
      "wallet_amount": "50.00",
      "points_used": 500,
      "points_amount": "50.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

### 6.2 Payment Required (HTTP 402)

```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "uuid",
    "amount": "30.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "breakdown": {
      "wallet_amount": "20.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "gateway_url": "https://test-pay.khalti.com/?pidx=...",
    "form_fields": {...},
    "expires_at": "2026-02-13T16:17:55.279127+00:00"
  }
}
```

### 6.3 Error Response (HTTP 400/404/500)

```json
{
  "success": false,
  "message": "Error description",
  "error_code": "specific_error_code",
  "context": {
    "additional": "details"
  }
}
```

---

## 7. Breaking Changes

### For API Clients

**Changed Fields:**
- `payment_breakdown` → `breakdown`
- Removed duplicate fields: `wallet_used`, `points_to_use`
- All amounts now strings with 2 decimals

**Changed Status Codes:**
- payment_required: HTTP 200 → HTTP 402

**Changed Structure:**
- payment_required: nested `data.error.context` → flat `data`

### Migration Guide

**Before:**
```javascript
if (response.status === 200 && response.data.error?.code === 'payment_required') {
  const context = response.data.error.context;
  const breakdown = context.payment_breakdown;
}
```

**After:**
```javascript
if (response.status === 402 && response.error_code === 'payment_required') {
  const data = response.data;
  const breakdown = data.breakdown;
}
```

---

## 8. Implementation Checklist

### Phase 1: Response Format (CRITICAL)
- [ ] Create `due/response_builder.py`
- [ ] Update `rental_due_service.py` return format
- [ ] Update `support_views.py` HTTP 402 handling
- [ ] Test all 8 scenarios
- [ ] Verify field naming consistency

### Phase 2: Serializer (OPTIONAL)
- [ ] Add direct mode validation
- [ ] Test validation errors

### Phase 3: Documentation
- [ ] Update API documentation
- [ ] Create migration guide for clients
- [ ] Document breaking changes

---

## 9. Testing Script

```python
# test_pay_due.py
import requests

API_URL = "http://localhost:8010"
TOKEN = "..."

def test_pay_due(rental_id, payment_mode, payment_method_id=None):
    response = requests.post(
        f"{API_URL}/api/rentals/{rental_id}/pay-due",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "payment_mode": payment_mode,
            "payment_method_id": payment_method_id
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Verify format
    data = response.json()
    if response.status_code == 402:
        assert data["success"] == False
        assert data["error_code"] == "payment_required"
        assert "breakdown" in data["data"]
        assert "wallet_amount" in data["data"]["breakdown"]
    elif response.status_code == 200:
        assert data["success"] == True
        assert "breakdown" in data["data"]
        assert "wallet_amount" in data["data"]["breakdown"]

# Run tests
test_pay_due("rental-id", "wallet")
test_pay_due("rental-id", "direct", "payment-method-id")
```

---

## 10. Summary

### Current State
- ✅ All payment modes working
- ✅ Gateway integration working
- ⚠️ Response format inconsistent with rental start
- ⚠️ HTTP status codes inconsistent

### Required Changes
1. **Response format** - Use `breakdown` instead of `payment_breakdown`
2. **HTTP 402** - For payment_required scenarios
3. **Flat structure** - No nested error object
4. **Field cleanup** - Remove duplicate fields

### Estimated Effort
- **Phase 1 (Critical):** 2-3 hours
- **Phase 2 (Optional):** 1 hour
- **Phase 3 (Testing):** 2 hours
- **Total:** 5-6 hours

### Risk Level
- **LOW** - Changes are isolated to response formatting
- No business logic changes
- Existing functionality preserved

---

**Status:** Ready for Implementation  
**Priority:** HIGH (Consistency with rental start)  
**Breaking Changes:** YES (API clients need updates)
