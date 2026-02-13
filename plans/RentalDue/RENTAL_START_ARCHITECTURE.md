# Rental Start Architecture Diagram

## Current vs New Architecture

### BEFORE (Current)

```
┌─────────────────────────────────────────────────────────────┐
│                     RentalStartView                         │
│  - Handles all response formatting inline                   │
│  - BUSINESS_BLOCKING_CODES logic                           │
│  - Returns HTTP 200 for payment_required                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              RentalStartMixin (core.py)                     │
│  - 250 lines (too large)                                    │
│  - Validation + Intent creation + Response building         │
│  - Mixed concerns                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          RentalPaymentFlowService                           │
│  - build_payment_required_context()                         │
│  - Returns nested structure: data.error.context             │
└─────────────────────────────────────────────────────────────┘
```

### AFTER (New)

```
┌─────────────────────────────────────────────────────────────┐
│                     RentalStartView                         │
│  - Clean exception handling                                 │
│  - Uses response_builder for formatting                     │
│  - Returns HTTP 402 for payment_required                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              RentalStartMixin (core.py)                     │
│  - 200 lines (optimized)                                    │
│  - Orchestrates flow only                                   │
│  - Delegates to specialized modules                         │
└───────┬─────────────┬─────────────┬──────────────┬──────────┘
        │             │             │              │
        ▼             ▼             ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  payment_    │ │  payment_    │ │  response_   │ │  Existing    │
│  validator   │ │  intent_     │ │  builder     │ │  Services    │
│              │ │  builder     │ │              │ │              │
│ ~150 lines   │ │ ~150 lines   │ │ ~200 lines   │ │ (reused)     │
│              │ │              │ │              │ │              │
│ - Validate   │ │ - Build      │ │ - Format     │ │ - validation │
│   payment    │ │   intent     │ │   success    │ │ - payment    │
│   mode       │ │   metadata   │ │ - Format     │ │ - device     │
│ - Check      │ │ - Create     │ │   payment_   │ │ - discount   │
│   sufficiency│ │   intent     │ │   required   │ │ - revenue    │
│ - Resolve    │ │ - Build      │ │ - Format     │ │ - vendor     │
│   resume     │ │   context    │ │   error      │ │              │
│   mode       │ │              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Module Responsibilities

### 1. payment_validator.py
```
┌─────────────────────────────────────────┐
│      Payment Validation Logic           │
├─────────────────────────────────────────┤
│ ✓ Validate payment mode                 │
│ ✓ Check PREPAID sufficiency             │
│ ✓ Check POSTPAID minimum                │
│ ✓ Resolve resume mode                   │
│ ✓ Resolve resume preferences            │
├─────────────────────────────────────────┤
│ Dependencies:                            │
│ • RentalPaymentFlowService              │
│ • AppConfigService                      │
└─────────────────────────────────────────┘
```

### 2. payment_intent_builder.py
```
┌─────────────────────────────────────────┐
│      Payment Intent Creation            │
├─────────────────────────────────────────┤
│ ✓ Build intent metadata                 │
│ ✓ Create payment intent                 │
│ ✓ Build payment_required data           │
│ ✓ Handle discount metadata              │
│ ✓ Handle resume preferences             │
├─────────────────────────────────────────┤
│ Dependencies:                            │
│ • RentalPaymentFlowService              │
│ • PaymentIntentService                  │
└─────────────────────────────────────────┘
```

### 3. response_builder.py
```
┌─────────────────────────────────────────┐
│      Response Formatting                │
├─────────────────────────────────────────┤
│ ✓ Build success response (HTTP 201)     │
│ ✓ Build payment_required (HTTP 402)     │
│ ✓ Build error response (HTTP 4xx/5xx)   │
│ ✓ Format pricing data                   │
│ ✓ Format payment data                   │
│ ✓ Format discount data                  │
├─────────────────────────────────────────┤
│ Dependencies:                            │
│ • None (pure formatting)                │
└─────────────────────────────────────────┘
```

### 4. core.py (Updated)
```
┌─────────────────────────────────────────┐
│      Orchestration Layer                │
├─────────────────────────────────────────┤
│ ✓ Validate prerequisites                │
│ ✓ Resolve pricing (discount)            │
│ ✓ Validate payment (use validator)      │
│ ✓ Create intent (use builder)           │
│ ✓ Create rental atomically              │
│ ✓ Handle device popup                   │
│ ✓ Trigger post-activation tasks         │
├─────────────────────────────────────────┤
│ Dependencies:                            │
│ • payment_validator                     │
│ • payment_intent_builder                │
│ • All existing services                 │
└─────────────────────────────────────────┘
```

---

## Data Flow

### Scenario: PREPAID + wallet + INSUFFICIENT

```
1. Request
   ↓
   {
     "station_sn": "STN001",
     "package_id": "pkg-123",
     "payment_mode": "wallet",
     "payment_method_id": "pm-khalti-123"
   }

2. RentalStartView.post()
   ↓
   Validates request data

3. RentalService.start_rental()
   ↓
   Orchestrates flow

4. payment_validator.check_prepaid_sufficiency()
   ↓
   Returns: (False, payment_options)

5. payment_intent_builder.create_payment_intent()
   ↓
   Creates PaymentIntent with metadata

6. payment_intent_builder.build_payment_required_data()
   ↓
   Builds response data

7. Raises ServiceException(code='payment_required', status_code=402)
   ↓
   Exception caught by view

8. response_builder.build_payment_required_response()
   ↓
   Formats final response

9. Response (HTTP 402)
   ↓
   {
     "success": false,
     "message": "Insufficient wallet balance...",
     "error_code": "payment_required",
     "data": {
       "intent_id": "...",
       "amount": "50.00",
       "shortfall": "30.00",
       ...
     }
   }
```

---

## File Size Breakdown

```
┌────────────────────────────────────────────────────────┐
│                  File Size Chart                       │
├────────────────────────────────────────────────────────┤
│                                                        │
│  payment_validator.py        ████████ 150 lines       │
│  payment_intent_builder.py   ████████ 150 lines       │
│  response_builder.py         ████████████ 200 lines   │
│  response_serializers.py     ████████████ 200 lines   │
│  core.py (updated)           ████████████ 200 lines   │
│  core_views.py (updated)     ██████ 120 lines         │
│  rental_payment_flow.py      ████████████ 200 lines   │
│                                                        │
│  ─────────────────────────────────────────────────    │
│  Target: < 300 lines per file                    ✅   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Testing Pyramid                      │
└─────────────────────────────────────────────────────────┘

                    ▲
                   ╱ ╲
                  ╱   ╲
                 ╱ E2E ╲              - 24 scenarios
                ╱───────╲             - Gateway flow
               ╱         ╲            - Rental resume
              ╱───────────╲
             ╱             ╲
            ╱  Integration  ╲        - Service layer
           ╱─────────────────╲       - Payment flow
          ╱                   ╲      - Intent creation
         ╱─────────────────────╲
        ╱                       ╲
       ╱      Unit Tests         ╲   - payment_validator
      ╱───────────────────────────╲  - payment_intent_builder
     ╱                             ╲ - response_builder
    ╱───────────────────────────────╲
   ╱                                 ╲
  ╱___________________________________╲
```

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────┐
│                  Service Dependencies                    │
└─────────────────────────────────────────────────────────┘

RentalStartView
    │
    └─→ RentalService (RentalStartMixin)
            │
            ├─→ payment_validator
            │       │
            │       └─→ RentalPaymentFlowService
            │               │
            │               └─→ PaymentCalculationService
            │
            ├─→ payment_intent_builder
            │       │
            │       └─→ RentalPaymentFlowService
            │               │
            │               ├─→ PaymentIntentService
            │               └─→ PaymentMethodRepository
            │
            ├─→ response_builder (no dependencies)
            │
            └─→ Existing Services (no changes)
                    ├─→ validation.py
                    ├─→ payment.py
                    ├─→ device.py
                    ├─→ discount.py
                    ├─→ revenue.py
                    └─→ vendor_ejection.py
```

---

## Implementation Phases

```
Phase 1: New Modules (Days 1-2)
┌────────────────────────────────────┐
│ ✓ payment_validator.py             │
│ ✓ payment_intent_builder.py        │
│ ✓ response_builder.py              │
│ ✓ response_serializers.py          │
│ ✓ Update rental_payment_flow.py    │
└────────────────────────────────────┘
         │
         │ No breaking changes yet
         ▼
Phase 2: Core Updates (Days 3-4)
┌────────────────────────────────────┐
│ ✓ Update core.py                   │
│ ✓ Update core_views.py             │
│ ✓ Update tests                     │
└────────────────────────────────────┘
         │
         │ Breaking changes introduced
         ▼
Phase 3: Testing (Days 5-6)
┌────────────────────────────────────┐
│ ✓ Integration tests (24 scenarios) │
│ ✓ API contract tests               │
│ ✓ Documentation updates            │
└────────────────────────────────────┘
```

---

## Success Metrics

```
┌─────────────────────────────────────────────────────────┐
│                   Success Criteria                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Code Quality                                           │
│  ├─ All files < 300 lines              ✅              │
│  ├─ No code duplication                ✅              │
│  ├─ Clear separation of concerns       ✅              │
│  └─ Reuse existing services            ✅              │
│                                                         │
│  Functionality                                          │
│  ├─ All 24 scenarios working           [ ]             │
│  ├─ Gateway integration working        [ ]             │
│  ├─ Rental resume working              [ ]             │
│  └─ Discount preservation working      [ ]             │
│                                                         │
│  Testing                                                │
│  ├─ Unit tests passing                 [ ]             │
│  ├─ Integration tests passing          [ ]             │
│  ├─ API contract tests passing         [ ]             │
│  └─ Coverage > 90%                     [ ]             │
│                                                         │
│  Documentation                                          │
│  ├─ API docs updated                   [ ]             │
│  ├─ Client migration guide             [ ]             │
│  └─ Code comments added                [ ]             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

**Ready to implement!** 🚀

See `plans/RENTAL_START_LAYER2_PLAN.md` for full details.

