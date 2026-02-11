# Rental Start Payment - Verified Baseline and Delta (2026-02-11)

## Purpose
Document current code behavior and exact delta required to reach the finalized target contract:
- user-controlled `payment_mode`
- rental-start business responses as `success=true` with `data.error`

## Current Verified State (Code)
1. `POST /api/rentals/start` accepts optional `payment_method_id`.
- `api/user/rentals/serializers/action_serializers.py:32`
- `api/user/rentals/views/core_views.py:49`

2. PREPAID/POSTPAID insufficiency already creates top-up intent and raises `payment_required`.
- `api/user/rentals/services/rental/start/core.py:104`
- `api/user/rentals/services/rental/start/core.py:147`
- `api/user/rentals/services/rental/start/core.py:173`

3. `payment_required` context already contains gateway and intent data.
- `api/user/rentals/services/rental/start/core.py:259`

4. Verify flow already triggers resume task for `flow=RENTAL_START`.
- `api/user/payments/services/payment_intent.py:194`

5. Resume task already idempotent via `rental_id` guard.
- `api/user/rentals/tasks.py:477`

6. Current platform error format is `success=false,error={...}`.
- `api/common/mixins/response.py:29`

## Current Verified Gaps
1. No `payment_mode` in rental-start request.
- `api/user/rentals/serializers/action_serializers.py:13`

2. Calculator forces points-first; no mode control.
- `api/user/payments/services/payment_calculation.py:21`
- `api/user/payments/services/payment_calculation.py:190`

3. Calculator serializer lacks `amount` and `payment_mode` parity fields.
- `api/user/payments/serializers/rental_payment_serializer.py:27`

4. Rental-start view uses generic handler, so business errors return `success=false,error`.
- `api/user/rentals/views/core_views.py:60`

## Points Conversion Verification (No Assumptions)
1. Spending conversion is currently code-level fixed at `10 points = NPR 1`.
- `api/common/utils/currency.py:18`
- `api/user/payments/services/payment_calculation.py:127`

2. AppConfig fixture contains points award keys, but not a dedicated redemption ratio key.
- `api/user/system/fixtures/app_config.json`

3. Top-up reward points are currently hardcoded (`amount * 0.1`) and not using fixture keys.
- `api/user/payments/services/payment_intent.py:236`

## Finalized Target Delta
1. Add `payment_mode` support in start and calculator paths.
2. Add mode-aware deduction/top-up logic.
3. Convert rental-start business block responses to:

```json
{
  "success": true,
  "message": "...",
  "data": {
    "error": {
      "code": "...",
      "message": "...",
      "context": {}
    }
  }
}
```

4. Keep verify/resume architecture; only make mode behavior deterministic via metadata.

## Input Plan Docs Reviewed
- `docs/Rental Flow/plan.txt`
- `docs/Rental Flow/rental_payment_plan.md`
- `docs/Rental Flow/rental_payment_plan_Cycle.md`

## Conclusion
Core top-up/resume infrastructure is already in place. Remaining work is response-wrapper adaptation for rental-start business outcomes and full `payment_mode` control across calculation, start, and resume.
