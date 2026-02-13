# Before vs After Comparison

## File Structure

### BEFORE
```
api/user/rentals/
├── views/
│   └── core_views.py (304 lines) ❌ TOO LARGE
│       ├── RentalStartView
│       ├── RentalCancelView
│       ├── RentalExtendView
│       ├── RentalActiveView
│       └── RentalSwapView
│
├── serializers/
│   ├── action_serializers.py
│   └── detail_serializers.py
│       └── RentalDetailSerializer (flat structure)
│
└── services/rental/start/
    └── core.py (379 lines) ❌ TOO LARGE
        ├── start_rental()
        ├── _resolve_pricing()
        ├── _validate_and_check_payment() [LARGE]
        ├── _raise_payment_required() [LARGE]
        ├── _get_resume_mode()
        ├── _get_resume_preferences()
        └── _start_rental_atomic()
```

### AFTER
```
api/user/rentals/
├── views/
│   ├── core_views.py (150 lines) ✅
│   │   └── RentalStartView
│   ├── cancel_views.py (80 lines) ✅
│   │   └── RentalCancelView
│   ├── extend_views.py (80 lines) ✅
│   │   └── RentalExtendView
│   ├── active_views.py (80 lines) ✅
│   │   └── RentalActiveView
│   └── swap_views.py (80 lines) ✅
│       └── RentalSwapView
│
├── serializers/
│   ├── action_serializers.py
│   ├── detail_serializers.py
│   └── rental_response_serializer.py (250 lines) ✅ NEW
│       ├── PackageResponseSerializer
│       ├── PricingResponseSerializer
│       ├── PaymentBreakdownSerializer
│       ├── PaymentResponseSerializer
│       ├── DiscountResponseSerializer
│       └── RentalStartSuccessSerializer
│
└── services/rental/start/
    ├── core.py (250 lines) ✅
    │   ├── start_rental()
    │   ├── _resolve_pricing()
    │   └── _start_rental_atomic()
    ├── payment_validator.py (150 lines) ✅ NEW
    │   ├── validate_payment_mode()
    │   ├── check_prepaid_sufficiency()
    │   ├── check_postpaid_minimum()
    │   ├── resolve_resume_mode()
    │   └── resolve_resume_preferences()
    ├── payment_intent_builder.py (150 lines) ✅ NEW
    │   ├── build_intent_metadata()
    │   ├── create_payment_intent()
    │   └── raise_payment_required()
    ├── response_builder.py (200 lines) ✅ NEW
    │   ├── build_rental_success_data()
    │   ├── build_payment_breakdown()
    │   └── build_discount_data()
    └── payment_required_response.py (100 lines) ✅ NEW
        └── build_payment_required_response()
```

---

## Response Format

### BEFORE (Current)

**Success:**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "id": "...",
    "rental_code": "...",
    "status": "ACTIVE",
    "amount_paid": "50.00",
    "station_name": "...",
    "package_name": "..."
  }
}
```

**Payment Required (HTTP 200):**
```json
{
  "success": true,
  "message": "Payment required to start rental",
  "data": {
    "error": {
      "code": "payment_required",
      "context": {
        "intent_id": "...",
        "amount": "50.00",
        "payment_breakdown": {...}
      }
    }
  }
}
```

### AFTER (New)

**Success:**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "...",
    "rental_code": "...",
    "status": "ACTIVE",
    "package": {
      "id": "...",
      "name": "...",
      "price": "50.00",
      "payment_model": "PREPAID"
    },
    "pricing": {
      "original_price": "50.00",
      "discount_amount": "0.00",
      "actual_price": "50.00",
      "amount_paid": "50.00"
    },
    "payment": {
      "payment_model": "PREPAID",
      "payment_mode": "wallet",
      "payment_status": "PAID",
      "breakdown": {
        "wallet_amount": "50.00",
        "points_used": 0,
        "points_amount": "0.00"
      }
    }
  }
}
```

**Payment Required (HTTP 402):**
```json
{
  "success": false,
  "message": "Insufficient wallet balance. Please top-up to continue.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "...",
    "amount": "50.00",
    "shortfall": "30.00",
    "breakdown": {
      "wallet_amount": "20.00",
      "points_used": 0,
      "points_amount": "0.00"
    }
  }
}
```

---

## Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| **HTTP Status** | 200 | 402 |
| **success Flag** | true | false |
| **Structure** | Nested error | Flat data |
| **Field Name** | payment_breakdown | breakdown |
| **Response** | Flat | Nested |
| **Files** | 2 large files | 8 modular files |
| **Lines/File** | 304, 379 | All <300 |

---

## Breaking Changes

1. ❌ HTTP 200 → HTTP 402
2. ❌ success: true → success: false
3. ❌ data.error.context → data (flat)
4. ❌ payment_breakdown → breakdown
5. ❌ Flat response → Nested response
6. ❌ points_to_use → points_used

**Impact:** Mobile app and frontend must update

---

## Migration Path

### Option 1: Feature Flag
```python
if settings.USE_NEW_RENTAL_RESPONSE_FORMAT:
    # New format
else:
    # Old format
```

### Option 2: API Versioning
```
/api/v2/rentals/start  # New format
/api/v1/rentals/start  # Old format (deprecated)
```

### Option 3: Hard Cutover
- Deploy backend
- Deploy clients immediately
- Monitor errors

**Recommendation:** Option 2 (API Versioning)

---

## Metrics

### Code Quality
- ✅ All files <300 lines
- ✅ Clear separation of concerns
- ✅ No code duplication
- ✅ Reusable services

### Effort
- Original: 6 days
- Corrected: 9 days
- Increase: +50%

### Risk
- Breaking changes: HIGH
- Complexity: MEDIUM
- Testing effort: HIGH

---

**Status:** ✅ Plan Corrected & Ready
