# Exact Code Changes - Pay Due Implementation

**Date:** 2026-02-13 22:17

---

## Change 1: rental_due_service.py

**File:** `api/user/rentals/services/rental/rental_due_service.py`  
**Lines:** 83-98

### BEFORE (Current Code)
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

### AFTER (New Code)
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

### Changes Made
1. Line 86: `float(required_due)` → `str(required_due)`
2. Line 87: `"payment_breakdown"` → `"breakdown"`
3. Line 88: Reordered - `wallet_amount` first
4. Line 88: `float(...)` → `str(...)`
5. Line 89: Removed `"wallet_used"` (duplicate)
6. Line 90: Removed `"points_to_use"` (duplicate)
7. Line 91: `float(...)` → `str(...)`
8. Line 95: Added `"rental_status": rental.status,`

---

## Change 2: support_views.py

**File:** `api/user/rentals/views/support_views.py`  
**Lines:** 160-168

### BEFORE (Current Code)
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

### AFTER (New Code)
```python
            if error_code == "payment_required":
                # HTTP 402 with flat data structure (consistent with rental start)
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

### Changes Made
1. Line 160: Added special case for `payment_required`
2. Lines 161-168: New HTTP 402 response
3. Line 169: Changed to `elif` for other blocking codes
4. Import added: `from rest_framework.response import Response`

### Import Check
Verify this import exists at top of file:
```python
from rest_framework.response import Response
from rest_framework import status
```

---

## Summary

**Files Changed:** 2  
**Lines Changed:** ~25  
**New Files:** 0  
**Deleted Files:** 0  
**Imports Added:** 0 (already exists)

**Complexity:** LOW  
**Risk:** LOW  
**Time:** 15 minutes
