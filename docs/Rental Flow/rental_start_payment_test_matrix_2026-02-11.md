# Rental Start Payment - Recursive Test Matrix (Final Contract, 2026-02-11)

## Scope
Validate:
- `POST /api/rentals/start`
- `POST /api/payments/calculate-options`
- `POST /api/payments/verify`
- async resume task

with user-controlled `payment_mode` and rental-start business blocks returned as `success=true` + `data.error`.

## Preconditions
1. API and celery containers are running.
2. ONLINE station with available powerbank exists.
3. Active PREPAID and POSTPAID package exist.
4. Active payment method exists.
5. Test user wallet and points can be controlled.

## Mode Scenario Matrix
| ID | Package | Mode | Input Split | Balance State | Expected Start |
|---|---|---|---|---|---|
| M01 | PREPAID | wallet | none | wallet >= discounted price | `201`, rental starts |
| M02 | PREPAID | wallet | none | wallet < discounted price + method | `200`, `success=true`, `data.error.code=payment_required` |
| M03 | PREPAID | points | none | points value >= discounted price | `201`, rental starts |
| M04 | PREPAID | points | none | points value < discounted price + method | `200`, `success=true`, `data.error.code=payment_required` |
| M05 | PREPAID | wallet_points | valid split | wallet+points satisfy split | `201`, rental starts |
| M06 | PREPAID | wallet_points | valid split | wallet/points insufficient + method | `200`, `success=true`, `data.error.code=payment_required` |
| M07 | PREPAID | wallet_points | invalid split sum | any | `200`, `success=true`, `data.error.code=invalid_split_amount` |
| M08 | PREPAID | direct | none | any + method | `200`, `success=true`, `data.error.code=payment_required` |
| M09 | PREPAID | direct | none | missing method | `200`, `success=true`, `data.error.code=payment_method_required` |
| M10 | POSTPAID | wallet | none | wallet >= min balance | `201`, rental starts |
| M11 | POSTPAID | wallet | none | wallet < min + method | `200`, `success=true`, `data.error.code=payment_required` |
| M12 | POSTPAID | direct | none | any + method when top-up needed | `200`, `success=true`, `data.error.code=payment_required` |
| M13 | POSTPAID | points/wallet_points | any | any | `200`, `success=true`, `data.error.code=invalid_payment_mode_for_postpaid` |

## Response Contract Assertions
### A) Start success
1. HTTP `201`
2. `success=true`
3. `data.id` (rental id) exists

### B) Start business block
1. HTTP `200`
2. `success=true`
3. `data.error.code` exists
4. `data.error.message` exists
5. `data.error.context` exists

### C) `payment_required` context fields
- `intent_id`
- `amount`
- `shortfall`
- `gateway`
- `gateway_url`
- `redirect_url`
- `redirect_method`
- `form_fields`
- `expires_at`
- `status`
- `payment_mode`

## Split-Specific Assertions (`wallet_points`)
1. If client sends `wallet_amount` + `points_to_use`:
- converted points amount + wallet amount must equal discounted price.
2. If valid and sufficient:
- applied deduction should match selected split.
3. If valid but insufficient:
- shortfall and intent amount must match missing amount.
4. If invalid sum:
- return `invalid_split_amount` in `data.error.code`.

## Calculator Parity Assertions
Endpoint: `POST /api/payments/calculate-options`
1. Accepts `amount`, `payment_mode`, `wallet_amount`, `points_to_use`.
2. Decision parity with `rentals/start` for same inputs.
3. Returns both requested split and applied split.

## Verify/Resume Assertions
1. `POST /api/payments/verify` success:
- `success=true`
- `data.status=SUCCESS`
- `rental_start_status` present for rental-start intents.

2. Idempotency:
- verify same intent twice -> no duplicate rental.
- rerun resume task -> no duplicate rental.

3. Metadata lifecycle:
- `PENDING -> PROCESSING -> SUCCESS|FAILED`
- on failure, `rental_error` is stored.

## Data Integrity Assertions
1. Discount is always applied before sufficiency/split checks.
2. Transaction types are correct (`RENTAL`, `TOPUP`).
3. Single active rental invariant remains enforced.
4. No negative wallet or negative points after settlement.

## Points/AppConfig Assertions
1. For this phase, redemption uses existing fixed ratio behavior (`10 points = NPR 1`).
2. No behavioral regression in points award scenarios (signup/referral/kyc/profile/rental completion/top-up reward).
3. If top-up reward config migration is taken later, verify `POINTS_TOPUP` and `POINTS_TOPUP_PER_NPR` parity separately.

## Automation Targets
1. Unit tests:
- mode allocation and shortfall logic
- split validation logic
- top-up amount calculation per mode

2. API tests:
- wrapper shape (`success=true`, `data.error`)
- all mode branches
- split-input branches

3. Task tests:
- resume idempotency
- metadata state transitions
