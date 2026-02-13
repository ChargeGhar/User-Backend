# Rental Start Refactoring - Quick Reference

## 📋 Documents

1. **`plans/Rental.md`** - Complete API specification with all 24 scenarios
2. **`plans/RENTAL_START_LAYER2_PLAN.md`** - Detailed implementation plan (THIS DOCUMENT)

---

## 🎯 What We're Doing

### Problem
Current response format has inconsistencies:
- ❌ Nested `data.error.context` structure
- ❌ `success: true` for payment_required (should be `false`)
- ❌ HTTP 200 for payment_required (should be 402)
- ❌ Mixed field naming (`payment_breakdown` vs `breakdown`)

### Solution
Clean, professional response format:
- ✅ Flat `data` structure
- ✅ `success: false` for payment_required
- ✅ HTTP 402 for payment_required
- ✅ Consistent field naming

---

## 📁 New Files to Create

```
api/user/rentals/services/rental/start/
├── payment_validator.py        (~150 lines) - Payment validation logic
├── payment_intent_builder.py   (~150 lines) - Intent creation
└── response_builder.py          (~200 lines) - Response formatting

api/user/rentals/serializers/
└── response_serializers.py      (~200 lines) - Response schemas
```

---

## 🔧 Files to Update

```
api/user/rentals/services/rental/start/
└── core.py                      (250 → 200 lines) - Use new modules

api/user/rentals/views/
└── core_views.py                (100 → 120 lines) - Handle HTTP 402

api/user/payments/services/
└── rental_payment_flow.py       (190 → 200 lines) - Fix context builder
```

---

## 🚀 Implementation Sequence

### Day 1-2: Create New Modules (No Breaking Changes)
1. Create `payment_validator.py`
2. Create `payment_intent_builder.py`
3. Create `response_builder.py`
4. Create `response_serializers.py`
5. Update `rental_payment_flow.py`

### Day 3-4: Update Core Logic (Breaking Changes)
6. Update `core.py` (RentalStartMixin)
7. Update `core_views.py` (RentalStartView)

### Day 5-6: Testing & Documentation
8. Integration tests (24 scenarios)
9. API contract tests
10. Documentation updates

---

## 📊 Key Changes Summary

| Aspect | Before | After |
|--------|--------|-------|
| **HTTP Status** | 200 | 402 |
| **success Flag** | `true` | `false` |
| **Data Structure** | `data.error.context` | `data` (flat) |
| **Field Name** | `payment_breakdown` | `breakdown` |
| **Field Name** | `points_to_use` | `points_used` |

---

## ✅ All Files Under 300 Lines

| File | Lines | Status |
|------|-------|--------|
| payment_validator.py | ~150 | ✅ |
| payment_intent_builder.py | ~150 | ✅ |
| response_builder.py | ~200 | ✅ |
| response_serializers.py | ~200 | ✅ |
| core.py | ~200 | ✅ |
| core_views.py | ~120 | ✅ |
| rental_payment_flow.py | ~200 | ✅ |

---

## 🔄 No Code Duplication

### Reusing Existing Services:
- ✅ `RentalPaymentFlowService` - payment calculations
- ✅ `PaymentCalculationService` - balance checks
- ✅ `RentalPaymentService` - payment processing
- ✅ `PaymentIntentService` - intent management
- ✅ `AppConfigService` - config values
- ✅ All validation, device, discount, revenue services

---

## 🧪 Testing Coverage

### 24 Scenarios from plans/Rental.md:
- PREPAID: 8 scenarios (wallet, points, wallet_points, direct)
- POSTPAID: 6 scenarios (wallet, direct, unsupported modes)
- Discounts: 2 scenarios (sufficient, insufficient)
- Errors: 8 scenarios (validation, not found, offline, etc.)

---

## 📝 Response Format Examples

### Success (HTTP 201)
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "...",
    "status": "ACTIVE",
    ...
  }
}
```

### Payment Required (HTTP 402)
```json
{
  "success": false,
  "message": "Insufficient wallet balance. Please top-up to continue.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "...",
    "amount": "50.00",
    "shortfall": "30.00",
    "gateway_url": "...",
    ...
  }
}
```

### Error (HTTP 4xx/5xx)
```json
{
  "success": false,
  "message": "Station not found",
  "error_code": "station_not_found",
  "context": {
    "station_sn": "INVALID"
  }
}
```

---

## 🎯 Success Criteria

- [x] All files under 300 lines
- [x] No code duplication
- [x] Modular architecture
- [x] Reuse existing services
- [x] Clear separation of concerns
- [ ] All 24 scenarios implemented
- [ ] All tests passing
- [ ] API docs updated

---

## 🚦 Ready to Start?

1. Review `plans/RENTAL_START_LAYER2_PLAN.md` for full details
2. Create feature branch: `feature/rental-start-response-v2`
3. Start with Phase 1 (new modules)
4. No breaking changes until Phase 2

---

**Estimated Time:** 6 days  
**Risk Level:** Medium (client contract changes)  
**Status:** ✅ Ready for Implementation

