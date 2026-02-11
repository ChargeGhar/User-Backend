# Rental Start Payment - Final Execution Plan (2026-02-11)

## Final Goal
`POST /api/rentals/start` must support user-controlled payment flow with `payment_mode` and return business-blocking outcomes as `success=true` with `data.error`.

## Required Runtime Behavior (Locked)
1. `payment_mode=wallet`
- If wallet balance covers discounted package price, rental starts.
- If not, return payment details (`data.error.code=payment_required`) with shortfall intent.

2. `payment_mode=points`
- If points value covers discounted package price, rental starts.
- If not, return payment details (`data.error.code=payment_required`) for shortfall.
- Note: gateway top-up credits wallet; resume uses available points + wallet to satisfy final amount.

3. `payment_mode=wallet_points`
- User can pass preferred split amounts for both wallet and points.
- If discounted package price is satisfied by user balances per chosen split/policy, rental starts.
- If not, return payment details (`data.error.code=payment_required`) for shortfall.

4. `payment_mode=direct`
- Always return payment details (`data.error.code=payment_required`) for full discounted package price.

## Points/AppConfig Fact Check (Locked For This Phase)
1. Current spending conversion is fixed in code at `10 points = NPR 1`.
- `api/common/utils/currency.py:18`
- `api/user/payments/services/payment_calculation.py:127`

2. AppConfig fixture has points award keys, but no dedicated points-redemption ratio key.
- `api/user/system/fixtures/app_config.json`

3. To avoid extra complexity in this delivery, keep the existing redemption ratio behavior unchanged.
- Do not redesign points awarding scenarios.
- Implement only mode/split control and response contract changes required for rental start.

4. Optional follow-up (separate task):
- make top-up award points config-driven (`POINTS_TOPUP`, `POINTS_TOPUP_PER_NPR`), because current top-up award is hardcoded in service logic.

## API Contract (Rental Start)
### Request fields to add
File: `api/user/rentals/serializers/action_serializers.py`
- `payment_mode`: `wallet | points | wallet_points | direct` (default `wallet_points`)
- `wallet_amount`: optional decimal (used for `wallet_points` preference)
- `points_to_use`: optional integer (used for `wallet_points` preference)
- existing `payment_method_id` remains optional but required when intent creation is needed.

### Request validation rules
1. PREPAID accepts all four modes.
2. POSTPAID accepts `wallet` and `direct`; reject `points` and `wallet_points` with business error wrapped in `success=true`.
3. For `wallet_points`:
- if `wallet_amount` and `points_to_use` are provided, convert points to amount and validate total equals discounted price.
- if not provided, server computes split from policy.

## Response Contract (Rental Start business-blocking)
For `payment_required`, `payment_method_required`, and mode validation business blocks:
- HTTP `200`
- `success=true`
- `data.error = { code, message, context }`

Example shape:
```json
{
  "success": true,
  "message": "Payment required to start rental",
  "data": {
    "error": {
      "code": "payment_required",
      "message": "Payment required to start rental",
      "context": {
        "intent_id": "...",
        "amount": "...",
        "shortfall": "...",
        "gateway": "...",
        "gateway_url": "...",
        "redirect_url": "...",
        "redirect_method": "POST",
        "form_fields": {},
        "expires_at": "...",
        "status": "PENDING",
        "payment_mode": "wallet|points|wallet_points|direct"
      }
    }
  }
}
```

## Recursive Cross-Verification: Current State vs Required Delta
### Already available in code
1. Top-up intent creation and gateway context for rental-start precheck.
- `api/user/rentals/services/rental/start/core.py`

2. Verify flow and async resume path with idempotency guard.
- `api/user/payments/services/payment_intent.py`
- `api/user/rentals/tasks.py`

3. Actual price override support in payment calculation.
- `api/user/payments/services/payment_calculation.py`

### Missing and must be implemented
1. `payment_mode` and split-input contract in rental start serializer.
2. Mode-aware calculation logic (wallet-only, points-only, split, direct).
3. Mode-aware top-up amount policy in rental-start service.
4. Rental-start endpoint wrapper conversion to `success=true` + `data.error` for business blocks.
5. Resume metadata propagation for `payment_mode` and preferred split fields.
6. `payments/calculate-options` parity fields (`amount`, `payment_mode`, split inputs).

## Lifecycle Implementation Plan (Industry-Standard Sequence)
### Phase 1: API contract and validation
Files:
- `api/user/rentals/serializers/action_serializers.py`
- `api/user/payments/serializers/rental_payment_serializer.py`

### Phase 2: Calculation engine parity
Files:
- `api/user/payments/services/payment_calculation.py`
- `api/user/payments/views/core_views.py`

Outputs:
- deterministic breakdown
- shortfall, wallet shortfall, points shortfall
- applied split vs requested split

### Phase 3: Rental-start orchestration
Files:
- `api/user/rentals/services/rental/start/core.py`
- `api/user/rentals/services/rental/start/payment.py`

Outputs:
- mode-specific start/intent branch
- metadata persistence (`payment_mode`, requested split, applied split)

### Phase 4: Response wrapper conversion (rental start only)
File:
- `api/user/rentals/views/core_views.py`

Output:
- business blocking responses returned as `success=true` with `data.error`

### Phase 5: Resume determinism and idempotency
File:
- `api/user/rentals/tasks.py`

Output:
- resume uses stored mode/split policy
- duplicate verify/resume does not create duplicate rentals

### Phase 6: Tests and docs
- add targeted tests for all modes and wrapper contract
- update request/response examples in docs

## Update Checklist (What must be addressed)
1. Exact shortfall computation by selected mode.
2. Discount-first pricing consistency before split validation.
3. Payment method min/max amount constraints.
4. Clear behavior when preferred split cannot be honored.
5. Stable response schema for frontend consumption.
6. Race/idempotency safety on verify and resume.

## Done Criteria
1. All four mode behaviors match your required outcomes.
2. `wallet_points` supports explicit split input and validates against discounted price.
3. All insufficient/business-block branches return `success=true` with `data.error`.
4. `payments/calculate-options` and `rentals/start` produce consistent decisions.
5. End-to-end verify/resume passes without duplicate rental creation.
