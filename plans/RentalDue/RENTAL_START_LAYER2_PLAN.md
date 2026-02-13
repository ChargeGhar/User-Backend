# Rental Start Refactoring - Layer 2 Implementation Plan

**Version:** 2.0  
**Date:** 2026-02-13  
**Status:** Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Existing Architecture Analysis](#existing-architecture-analysis)
3. [Modular File Structure](#modular-file-structure)
4. [Service Layer Changes](#service-layer-changes)
5. [View Layer Changes](#view-layer-changes)
6. [Serializer Changes](#serializer-changes)
7. [Implementation Sequence](#implementation-sequence)
8. [File Size Constraints](#file-size-constraints)

---

## Overview

### Goals
- ✅ Implement response format from `plans/Rental.md`
- ✅ Keep all files under 300 lines
- ✅ Maintain existing business logic
- ✅ No code duplication
- ✅ Reuse existing services
- ✅ Modular, testable architecture

### Key Changes
1. Remove nested `error` object in payment_required responses
2. Change HTTP 200 → HTTP 402 for payment_required
3. Fix `success` flag logic
4. Rename `payment_breakdown` → `breakdown`
5. Rename `points_to_use` → `points_used` in responses

---

## Existing Architecture Analysis

### Current Service Structure

```
api/user/rentals/services/rental/
├── __init__.py (RentalService - combines all mixins)
├── start/
│   ├── __init__.py
│   ├── core.py (RentalStartMixin - 250 lines) ✅
│   ├── validation.py (validation functions)
│   ├── payment.py (payment processing)
│   ├── device.py (device popup)
│   ├── discount.py (discount logic)
│   ├── revenue.py (revenue distribution)
│   └── vendor_ejection.py (vendor free ejection)
├── cancel.py (RentalCancelMixin)
├── extend.py (RentalExtendMixin)
├── return_powerbank.py (RentalReturnMixin)
├── swap.py (RentalSwapMixin)
├── queries.py (RentalQueryMixin)
├── notifications.py (RentalNotificationMixin)
└── rental_due_service.py (RentalDuePaymentService)
```

### Existing Payment Services (Reusable)

```
api/user/payments/services/
├── rental_payment_flow.py (RentalPaymentFlowService) ✅
│   ├── calculate_payment_options()
│   ├── normalize_breakdown()
│   ├── create_topup_intent()
│   ├── resolve_gateway_topup_amount()
│   ├── build_payment_required_context() ⚠️ NEEDS UPDATE
│   └── serialize_for_metadata()
├── rental_payment.py (RentalPaymentService) ✅
│   ├── process_rental_payment()
│   └── create_rental_transaction()
├── payment_calculation.py (PaymentCalculationService) ✅
│   └── calculate_payment_options()
└── payment_intent.py (PaymentIntentService) ✅
    ├── create_topup_intent()
    └── verify_topup_payment()
```

### Models (No Changes Needed)

```
api/user/rentals/models/rental.py
├── Rental ✅
├── RentalPackage ✅
├── RentalExtension ✅
└── RentalSwap ✅

api/user/payments/models/
├── PaymentIntent ✅
├── PaymentMethod ✅
└── Transaction ✅
```

---

## Modular File Structure

### New/Modified Files

```
api/user/rentals/services/rental/start/
├── core.py (UPDATE - main orchestrator, ~200 lines)
├── payment_validator.py (NEW - payment validation logic, ~150 lines)
├── payment_intent_builder.py (NEW - intent creation, ~150 lines)
├── response_builder.py (NEW - response formatting, ~200 lines)
├── validation.py (KEEP - existing validations)
├── payment.py (KEEP - payment processing)
├── device.py (KEEP - device popup)
├── discount.py (KEEP - discount logic)
├── revenue.py (KEEP - revenue distribution)
└── vendor_ejection.py (KEEP - vendor free ejection)

api/user/rentals/views/
├── core_views.py (UPDATE - RentalStartView, ~250 lines)

api/user/rentals/serializers/
├── action_serializers.py (UPDATE - RentalStartSerializer)
├── response_serializers.py (NEW - response serializers, ~200 lines)

api/user/payments/services/
├── rental_payment_flow.py (UPDATE - context builder)
```

---

## Service Layer Changes

### 1. New File: `payment_validator.py`

**Purpose:** Validate payment requirements and determine if gateway is needed

**Size:** ~150 lines

**Functions:**
```python
def validate_payment_mode(payment_mode: str, payment_model: str) -> None:
    """Validate payment mode is supported for payment model"""
    
def check_prepaid_sufficiency(
    user, actual_price: Decimal, payment_mode: str,
    wallet_amount: Optional[Decimal], points_to_use: Optional[int]
) -> Tuple[bool, Dict]:
    """Check if user has sufficient balance for PREPAID"""
    
def check_postpaid_minimum(user) -> Tuple[bool, Decimal, Decimal]:
    """Check if user meets POSTPAID minimum balance"""
    
def resolve_resume_mode(
    requested_mode: str, points_short: bool
) -> str:
    """Determine payment mode after gateway top-up"""
    
def resolve_resume_preferences(
    payment_mode: str, wallet_amount: Optional[Decimal],
    points_to_use: Optional[int], payment_options: Dict
) -> Tuple[str, Optional[Decimal], Optional[int]]:
    """Build resume preferences for async rental continuation"""
```

**Dependencies:**
- `RentalPaymentFlowService.calculate_payment_options()`
- `AppConfigService.get_config_cached()`

---

### 2. New File: `payment_intent_builder.py`

**Purpose:** Build payment intent and metadata for gateway payment

**Size:** ~150 lines

**Functions:**
```python
def build_intent_metadata(
    station_sn: str, package_id: str, powerbank_sn: Optional[str],
    actual_price: Decimal, discount, discount_amount: Decimal,
    rental_metadata: Dict, payment_model: str, payment_mode: str,
    wallet_amount: Optional[Decimal], points_to_use: Optional[int],
    topup_amount: Decimal, shortfall: Decimal
) -> Dict:
    """Build intent metadata for rental resume"""
    
def create_payment_intent(
    user, payment_method_id: str, topup_amount: Decimal,
    metadata: Dict
) -> PaymentIntent:
    """Create payment intent via RentalPaymentFlowService"""
    
def build_payment_required_data(
    intent: PaymentIntent, shortfall: Decimal, payment_mode: str,
    payment_options: Optional[Dict], postpaid_min_balance: Optional[Decimal],
    current_balance: Optional[Decimal], discount, discount_amount: Decimal,
    actual_price: Decimal
) -> Dict:
    """Build payment_required response data"""
```

**Dependencies:**
- `RentalPaymentFlowService.create_topup_intent()`
- `RentalPaymentFlowService.resolve_gateway_topup_amount()`

---

### 3. New File: `response_builder.py`

**Purpose:** Build standardized API responses

**Size:** ~200 lines

**Functions:**
```python
def build_success_response(rental: Rental) -> Dict:
    """Build HTTP 201 success response"""
    
def build_payment_required_response(
    message: str, data: Dict
) -> Dict:
    """Build HTTP 402 payment_required response"""
    
def build_error_response(
    message: str, error_code: str, context: Optional[Dict] = None
) -> Dict:
    """Build HTTP 4xx/5xx error response"""
    
def format_pricing_data(
    original_price: Decimal, discount_amount: Decimal,
    actual_price: Decimal, amount_paid: Decimal
) -> Dict:
    """Format pricing section"""
    
def format_payment_data(
    payment_model: str, payment_mode: str, payment_status: str,
    breakdown: Optional[Dict], pending_transaction_id: Optional[str] = None
) -> Dict:
    """Format payment section"""
    
def format_discount_data(discount, discount_amount: Decimal) -> Optional[Dict]:
    """Format discount section"""
```

**Dependencies:**
- None (pure formatting functions)

---

### 4. Update: `core.py` (RentalStartMixin)

**Current:** 250 lines  
**Target:** ~200 lines (extract validation logic)

**Changes:**
```python
class RentalStartMixin:
    def start_rental(...) -> Rental:
        """Main orchestrator - simplified"""
        # 1. Validate prerequisites
        # 2. Resolve pricing (discount)
        # 3. Validate payment mode
        # 4. Check payment sufficiency
        # 5. If insufficient → raise payment_required (HTTP 402)
        # 6. If sufficient → create rental atomically
        
    def _validate_payment_requirements(...):
        """Use payment_validator functions"""
        
    def _raise_payment_required(...):
        """Use payment_intent_builder functions"""
        
    def _start_rental_atomic(...):
        """Existing logic - no changes"""
```

**Extracted to:**
- `payment_validator.py` - validation logic
- `payment_intent_builder.py` - intent creation

---

### 5. Update: `rental_payment_flow.py`

**Current:** 190 lines  
**Target:** ~200 lines (update context builder)

**Changes:**
```python
def build_payment_required_context(...) -> Dict:
    """
    UPDATED: Return flat structure (not nested in 'error')
    
    Returns:
        {
            'intent_id': '...',
            'amount': '...',
            'shortfall': '...',
            'payment_mode': '...',
            'wallet_shortfall': '...',
            'points_shortfall': ...,  # Optional
            'postpaid_min_balance': '...',  # Optional
            'discount_applied': {...},  # Optional
            'resume_preferences': {...},  # Optional
            'gateway': '...',
            'gateway_url': '...',
            ...
        }
    """
```

---

## View Layer Changes

### Update: `core_views.py` (RentalStartView)

**Current:** ~100 lines  
**Target:** ~120 lines

**Changes:**
```python
class RentalStartView(GenericAPIView, BaseAPIView):
    serializer_class = serializers.RentalStartSerializer
    permission_classes = [IsAuthenticated]
    
    # REMOVE: BUSINESS_BLOCKING_CODES
    
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = RentalService()
        try:
            rental = service.start_rental(
                user=request.user,
                **serializer.validated_data
            )
            
            # SUCCESS: HTTP 201
            from .response_builder import build_success_response
            response_data = build_success_response(rental)
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except ServiceException as exc:
            error_code = getattr(exc, 'default_code', 'service_error')
            error_context = getattr(exc, 'context', None)
            error_message = str(exc)
            status_code = getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST)
            
            # PAYMENT REQUIRED: HTTP 402
            if error_code == 'payment_required':
                from .response_builder import build_payment_required_response
                response_data = build_payment_required_response(
                    message=error_message,
                    data=error_context
                )
                return Response(response_data, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # ERROR: HTTP 4xx/5xx
            from .response_builder import build_error_response
            response_data = build_error_response(
                message=error_message,
                error_code=error_code,
                context=error_context
            )
            return Response(response_data, status=status_code)
```

---

## Serializer Changes

### 1. Update: `action_serializers.py` (RentalStartSerializer)

**No changes needed** - already has all required fields

```python
class RentalStartSerializer(serializers.Serializer):
    station_sn = serializers.CharField(...)
    package_id = serializers.UUIDField(...)
    powerbank_sn = serializers.CharField(..., required=False)
    payment_mode = serializers.ChoiceField(..., default='wallet_points')
    payment_method_id = serializers.UUIDField(..., required=False)
    wallet_amount = serializers.DecimalField(..., required=False)
    points_to_use = serializers.IntegerField(..., required=False)
```

### 2. New: `response_serializers.py`

**Purpose:** Response serializers for documentation and validation

**Size:** ~200 lines

```python
class PaymentBreakdownSerializer(serializers.Serializer):
    wallet_amount = serializers.DecimalField(...)
    points_used = serializers.IntegerField()  # NOT points_to_use
    points_amount = serializers.DecimalField(...)

class PricingSerializer(serializers.Serializer):
    original_price = serializers.DecimalField(...)
    discount_amount = serializers.DecimalField(...)
    actual_price = serializers.DecimalField(...)
    amount_paid = serializers.DecimalField(...)

class PaymentSerializer(serializers.Serializer):
    payment_model = serializers.CharField(...)
    payment_mode = serializers.CharField(...)
    payment_status = serializers.CharField(...)
    breakdown = PaymentBreakdownSerializer(required=False, allow_null=True)
    pending_transaction_id = serializers.UUIDField(required=False, allow_null=True)

class DiscountSerializer(serializers.Serializer):
    id = serializers.UUIDField(...)
    code = serializers.CharField(...)
    discount_percent = serializers.DecimalField(...)
    discount_amount = serializers.DecimalField(...)
    description = serializers.CharField(...)

class RentalSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(...)
    data = serializers.DictField(...)  # Full rental details

class PaymentRequiredResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField(...)
    error_code = serializers.CharField(default='payment_required')
    data = serializers.DictField(...)  # Payment intent details

class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField(...)
    error_code = serializers.CharField(...)
    context = serializers.DictField(required=False, allow_null=True)
```

---

## Implementation Sequence

### Phase 1: Create New Modules (No Breaking Changes)

**Day 1:**
1. ✅ Create `payment_validator.py`
   - Extract validation logic from `core.py`
   - Add unit tests
   
2. ✅ Create `payment_intent_builder.py`
   - Extract intent creation logic
   - Add unit tests

3. ✅ Create `response_builder.py`
   - Implement response formatting functions
   - Add unit tests

**Day 2:**
4. ✅ Create `response_serializers.py`
   - Define response serializers
   - Add to OpenAPI schema

5. ✅ Update `rental_payment_flow.py`
   - Fix `build_payment_required_context()`
   - Add unit tests

### Phase 2: Update Core Logic (Breaking Changes)

**Day 3:**
6. ✅ Update `core.py` (RentalStartMixin)
   - Use new validator functions
   - Use new intent builder functions
   - Change HTTP 402 for payment_required
   - Update tests

**Day 4:**
7. ✅ Update `core_views.py` (RentalStartView)
   - Remove BUSINESS_BLOCKING_CODES
   - Use response_builder functions
   - Handle HTTP 402
   - Update tests

### Phase 3: Integration & Testing

**Day 5:**
8. ✅ Integration tests
   - Test all 24 scenarios from `plans/Rental.md`
   - Test gateway flow
   - Test rental resume

9. ✅ API contract tests
   - Validate response schemas
   - Test backward compatibility

**Day 6:**
10. ✅ Documentation
    - Update API docs
    - Update client integration guide
    - Migration notes

---

## File Size Constraints

### Target File Sizes

| File | Current | Target | Status |
|------|---------|--------|--------|
| `core.py` | 250 | ~200 | ✅ Extract logic |
| `payment_validator.py` | 0 | ~150 | ✅ New file |
| `payment_intent_builder.py` | 0 | ~150 | ✅ New file |
| `response_builder.py` | 0 | ~200 | ✅ New file |
| `response_serializers.py` | 0 | ~200 | ✅ New file |
| `rental_payment_flow.py` | 190 | ~200 | ✅ Minor update |
| `core_views.py` | ~100 | ~120 | ✅ Minor update |

**All files under 300 lines ✅**

---

## Reusable Services (No Changes)

### Payment Services ✅
- `RentalPaymentFlowService` - payment options, intent creation
- `PaymentCalculationService` - balance calculations
- `RentalPaymentService` - payment processing
- `PaymentIntentService` - intent management

### Rental Services ✅
- `validation.py` - prerequisite validations
- `payment.py` - prepayment/postpaid processing
- `device.py` - device popup
- `discount.py` - discount logic
- `revenue.py` - revenue distribution
- `vendor_ejection.py` - vendor free ejection

### System Services ✅
- `AppConfigService` - config management
- `NotificationService` - push notifications

---

## Testing Strategy

### Unit Tests

**New Files:**
- `test_payment_validator.py` (~100 lines)
- `test_payment_intent_builder.py` (~100 lines)
- `test_response_builder.py` (~150 lines)

**Updated Files:**
- `test_rental_start.py` (update existing tests)
- `test_rental_payment_flow.py` (update context tests)

### Integration Tests

**Scenarios (from plans/Rental.md):**
- [ ] PREPAID scenarios (1-8)
- [ ] POSTPAID scenarios (9-14)
- [ ] Discount scenarios (15-16)
- [ ] Error scenarios (17-24)

### API Contract Tests

- [ ] Response schema validation
- [ ] Field type validation
- [ ] Required field presence
- [ ] HTTP status codes

---

## Migration Notes

### Breaking Changes

1. **Response Structure:**
   - `data.error.context` → `data` (flat structure)
   - `success: true` → `success: false` for payment_required

2. **HTTP Status:**
   - HTTP 200 → HTTP 402 for payment_required

3. **Field Names:**
   - `payment_breakdown` → `breakdown`
   - `points_to_use` → `points_used` (in responses)

### Client Updates Required

Mobile app and frontend must:
1. Check `error_code === 'payment_required'` instead of `data.error.code`
2. Handle HTTP 402 status
3. Access payment data from `data` directly
4. Update field names in payment breakdown

---

## Dependencies

### No New Dependencies ✅

All changes use existing:
- Django REST Framework
- Existing service classes
- Existing models
- Existing utilities

---

## Rollback Plan

### If Issues Arise:

1. **Phase 1 (New modules):** No rollback needed (no breaking changes)
2. **Phase 2 (Core updates):** Revert commits for `core.py` and `core_views.py`
3. **Phase 3 (Integration):** Fix issues, don't rollback

### Feature Flag (Optional):

```python
# settings.py
USE_NEW_RENTAL_RESPONSE_FORMAT = env.bool('USE_NEW_RENTAL_RESPONSE_FORMAT', default=False)

# core_views.py
if settings.USE_NEW_RENTAL_RESPONSE_FORMAT:
    # New format
else:
    # Old format
```

---

## Success Criteria

✅ All files under 300 lines  
✅ No code duplication  
✅ All 24 scenarios working  
✅ All tests passing  
✅ API docs updated  
✅ No breaking changes to other endpoints  
✅ Performance maintained  

---

## Next Steps

1. Review this plan with team
2. Get approval for breaking changes
3. Create feature branch: `feature/rental-start-response-v2`
4. Start Phase 1 implementation
5. Daily progress updates

---

**Status:** Ready for Implementation  
**Estimated Effort:** 6 days  
**Risk Level:** Medium (breaking changes to client contract)

