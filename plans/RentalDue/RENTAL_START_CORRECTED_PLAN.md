# Rental Start Refactoring - CORRECTED Layer 2 Plan

**Version:** 2.1 (Corrected)
**Date:** 2026-02-13  
**Status:** Ready for Implementation

---

## Summary of Corrections

Based on cross-verification with existing codebase:

1. ✅ **Actual file sizes identified:** core.py=379 lines, core_views.py=304 lines
2. ✅ **Response format mismatch resolved:** Need separate payment_required response
3. ✅ **View extraction required:** Split core_views.py into multiple files
4. ✅ **New response serializer needed:** Current RentalDetailSerializer doesn't match spec
5. ✅ **Effort corrected:** 9 days (not 6)

---

## Files to Create (8 files)

### 1. `payment_required_response.py` (~100 lines)
**Location:** `api/user/rentals/services/rental/start/`

```python
from rest_framework import status
from rest_framework.response import Response
from typing import Dict

def build_payment_required_response(
    message: str,
    error_code: str,
    data: Dict
) -> Response:
    """Build HTTP 402 payment_required response"""
    return Response({
        'success': False,
        'message': message,
        'error_code': error_code,
        'data': data
    }, status=status.HTTP_402_PAYMENT_REQUIRED)
```

### 2. `rental_response_serializer.py` (~250 lines)
**Location:** `api/user/rentals/serializers/`

Nested response structure with:
- PackageResponseSerializer
- PricingResponseSerializer  
- PaymentBreakdownSerializer
- PaymentResponseSerializer
- DiscountResponseSerializer
- RentalStartSuccessSerializer

### 3. `response_builder.py` (~200 lines)
**Location:** `api/user/rentals/services/rental/start/`

Functions:
- build_rental_success_data()
- build_payment_breakdown()
- build_discount_data()

### 4. `payment_validator.py` (~150 lines)
**Location:** `api/user/rentals/services/rental/start/`

Extracted from core.py:
- validate_payment_mode()
- check_prepaid_sufficiency()
- check_postpaid_minimum()
- resolve_resume_mode()
- resolve_resume_preferences()

### 5. `payment_intent_builder.py` (~150 lines)
**Location:** `api/user/rentals/services/rental/start/`

Extracted from core.py:
- build_intent_metadata()
- create_payment_intent()
- raise_payment_required()

### 6-9. View Files (80 lines each)
**Location:** `api/user/rentals/views/`

- `cancel_views.py` - RentalCancelView
- `extend_views.py` - RentalExtendView
- `active_views.py` - RentalActiveView
- `swap_views.py` - RentalSwapView

---

## Files to Update (3 files)

### 1. `core.py` (379 → 250 lines)
Extract 129 lines to payment_validator.py and payment_intent_builder.py

### 2. `core_views.py` (304 → 150 lines)
Extract 154 lines to separate view files

### 3. `rental_payment_flow.py` (190 → 200 lines)
Rename payment_breakdown → breakdown

---

## Implementation Sequence (9 Days)

### Days 1-2: Infrastructure
- Create payment_required_response.py
- Create rental_response_serializer.py
- Create response_builder.py
- Create payment_validator.py
- Create payment_intent_builder.py
- Unit tests

### Days 3-4: View Extraction
- Create cancel_views.py
- Create extend_views.py
- Create active_views.py
- Create swap_views.py
- Update URL routing
- Update imports

### Days 5-6: Core Updates
- Update core.py
- Update core_views.py
- Update rental_payment_flow.py
- Update tests

### Days 7-8: Integration Testing
- Test all 24 scenarios
- Gateway flow testing
- Rental resume testing

### Day 9: Documentation
- API docs
- Migration guide
- Code review

---

## All Files Under 300 Lines ✅

| File | Lines | Status |
|------|-------|--------|
| payment_required_response.py | 100 | ✅ |
| rental_response_serializer.py | 250 | ✅ |
| response_builder.py | 200 | ✅ |
| payment_validator.py | 150 | ✅ |
| payment_intent_builder.py | 150 | ✅ |
| cancel_views.py | 80 | ✅ |
| extend_views.py | 80 | ✅ |
| active_views.py | 80 | ✅ |
| swap_views.py | 80 | ✅ |
| core.py (updated) | 250 | ✅ |
| core_views.py (updated) | 150 | ✅ |
| rental_payment_flow.py (updated) | 200 | ✅ |

---

See RENTAL_START_CROSS_VERIFICATION.md for detailed analysis.
