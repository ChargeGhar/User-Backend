# Rental Payment Flow Plan (Non-Blocking, No Frontend Callback)

## Scope
This document defines how `rentals/start` should work when wallet/points are insufficient, while reusing the existing payment services and flows. The goal is to keep behavior consistent with current PREPAID/POSTPAID flows and avoid breaking existing clients.

## Current Behavior (Verified from Code)
- Start rental is orchestrated by `RentalStartMixin.start_rental`.
- For PREPAID packages:
  - `process_prepayment()` uses `PaymentCalculationService.calculate_payment_options`.
  - If sufficient, `RentalPaymentService.process_rental_payment` deducts points + wallet and creates a `RENTAL` transaction.
  - Rental is created before payment and device popup; rental is activated on popup success.
- For POSTPAID packages:
  - `validate_postpaid_balance()` enforces `POSTPAID_MINIMUM_BALANCE`.
  - A `PENDING` `RENTAL` transaction is created at start.
- Top-up flow exists:
  - `PaymentIntentService.create_topup_intent()` creates `WALLET_TOPUP` intent and returns gateway data.
  - `PaymentIntentService.verify_topup_payment()` verifies and credits wallet.
- Note: `PaymentCalculationService` currently ignores `amount` overrides for `pre_payment`
  and always uses the package price. This must be updated to respect `actual_price`
  when discounts apply.
 - `handle_service_operation()` drops `ServiceException.context`; error responses currently
   cannot carry gateway data unless this is fixed or bypassed.
 - `start_rental()` is wrapped in `@transaction.atomic`, so creating a top-up intent and
   raising an exception would rollback the intent.

## Requirement
- If PREPAID payment is insufficient, the rental start should not fail outright.
- Instead, return a non-blocking response that includes payment intent data so the client can pay.
- No dependency on gateway callback URLs. Resume rental start after `verify_topup_payment` is called.
- If POSTPAID minimum balance is not met, allow gateway top-up instead of failing.

## Proposed Flow (Minimal Change)
### Pre-check stage (before any transaction lock)
1. Validate user + station + package.
2. Calculate discount and `actual_price`.
3. For PREPAID: compute payment options using `amount=actual_price`.
4. For POSTPAID: check wallet balance against `POSTPAID_MINIMUM_BALANCE`.
5. If payment is required, create top-up intent and return `payment_required`
   without entering the atomic rental creation path.

### A) PREPAID with sufficient balance (unchanged)
1. Validate user + station + package.
2. Calculate discount and `actual_price`.
3. Create rental in `PENDING_POPUP`.
4. `process_prepayment()` -> `RENTAL` transaction + wallet/points deductions.
5. Device popup -> on success, activate rental and trigger revenue distribution.

### B) PREPAID with insufficient balance (new branch)
1. Validate user + station + package.
2. Calculate discount and `actual_price`.
3. Run payment calculation:
   - `PaymentCalculationService.calculate_payment_options(user, scenario='pre_payment', package_id, amount=actual_price)`
4. If insufficient:
   - Create top-up intent using existing `PaymentIntentService.create_topup_intent`.
   - Top-up amount = `actual_price` after discount (if any).
   - Store resume metadata in `intent_metadata`:
     - `intent_type = WALLET_TOPUP`
     - `flow = 'RENTAL_START'`
     - `station_sn`, `package_id`, `powerbank_sn`, `actual_price`, `discount_id` (if any)
     - `user_id`
   - Return a `payment_required` response including `intent_id`, gateway data, and `shortfall`.
   - Do NOT create rental yet.

### B2) POSTPAID with insufficient minimum balance (new branch)
1. Validate user + station + package.
2. If wallet balance < `POSTPAID_MINIMUM_BALANCE`:
   - Create top-up intent using existing `PaymentIntentService.create_topup_intent`.
   - Top-up amount = (`POSTPAID_MINIMUM_BALANCE` - current wallet balance).
   - Store resume metadata in `intent_metadata`:
     - `intent_type = WALLET_TOPUP`
     - `flow = 'RENTAL_START'`
     - `station_sn`, `package_id`, `powerbank_sn`
     - `user_id`
   - Return `payment_required` response with intent + gateway data.
   - Do NOT create rental yet.

### C) Verify top-up (existing endpoint, extended)
1. Client calls `POST /api/payments/verify` with `intent_id` and gateway data.
2. `PaymentIntentService.verify_topup_payment()`:
   - Verifies and credits wallet.
   - If intent metadata indicates `flow = 'RENTAL_START'`, enqueue async task to resume rental start.
3. Response includes additive fields:
   - `rental_start_status: 'PENDING' | 'SUCCESS' | 'FAILED'`
   - `rental_id` if started
   - `rental_error` if failed

### D) Async resume task
1. Load intent metadata.
2. Call `RentalService.start_rental(...)` with stored args.
3. Update intent metadata with `rental_id` or failure reason.
4. Idempotency: if `intent_metadata.rental_id` already exists, return early.

## API Contract (Additive)
### `POST /api/rentals/start`
- **Success (current):** returns rental detail.
- **New non-blocking case:**
  - `success: false` with error code `payment_required`
  - Contains:
    - `intent_id`
    - `amount` (top-up amount)
    - `shortfall`
    - gateway data (`gateway_url`, `redirect_url`, `form_fields`, `expires_at`)

### `POST /api/payments/verify`
- Existing response is unchanged.
- New additive fields:
  - `rental_start_status`
  - `rental_id`
  - `rental_error`

## Data Fields to Add
- `RentalStartSerializer`:
  - Optional `payment_method_id` (required only when insufficient funds).

## Failure/Edge Cases
- Top-up intent expired: verification fails, no rental start.
- Duplicate verify requests: idempotent via intent status + stored `rental_id`.
- Popup failure: rental remains `PENDING_POPUP` per current logic.
- POSTPAID: top-up amount is tied to minimum balance shortfall; if payment method min
  amount exceeds shortfall, verification may still leave balance below minimum unless
  the client chooses a larger top-up.

## Implementation Checklist
1. Add optional `payment_method_id` to `RentalStartSerializer`.
2. Introduce a pre-check path that runs before any atomic rental creation:
   - PREPAID: compute `actual_price`, check sufficiency with `amount=actual_price`.
   - POSTPAID: if wallet < `POSTPAID_MINIMUM_BALANCE`, create top-up intent.
3. Fix `ServiceHandlerMixin` to include `ServiceException.context` in error responses,
   or return a custom error response directly from the view for `payment_required`.
4. Update `PaymentCalculationService` to respect `amount` override for `pre_payment` so
   discount-based `actual_price` is used when calculating sufficiency.
5. Ensure discount consistency on resume: store `discount_id` and `actual_price` in intent
   metadata, and honor that in the resume start flow.
6. Extend `PaymentIntentService.verify_topup_payment` to enqueue rental-start task for intents tagged as `RENTAL_START`.
7. Add new Celery task to resume rental start from intent metadata (idempotent).
8. Add minimal tests for:
   - PREPAID insufficient -> `payment_required` response
   - verify top-up -> rental start scheduled
   - discounted PREPAID uses `actual_price`
   - POSTPAID min-balance top-up path

## Recursive Verification Checklist (No Assumptions)
1. PREPAID + sufficient balance:
   - `process_prepayment` runs and creates `RENTAL` transaction (SUCCESS).
   - Wallet/points are deducted correctly.
   - Rental is created and moves to `ACTIVE` on popup success.
2. PREPAID + insufficient balance:
   - No rental is created.
   - Top-up intent is created with `amount = actual_price` (discount applied).
   - `intent_metadata.flow = RENTAL_START` and contains required fields.
   - Response includes gateway data and `intent_id`.
3. Verify top-up (PREPAID path):
   - Wallet balance is credited.
   - Resume task is scheduled and starts rental successfully.
   - On success, `intent_metadata.rental_id` is populated.
4. POSTPAID + sufficient balance:
   - Minimum balance check passes.
   - PENDING `RENTAL` transaction is created.
   - Rental is created and continues with popup flow.
5. POSTPAID + insufficient balance:
   - No rental is created.
   - Top-up intent is created with `amount = (min_balance - current balance)`.
   - After verify, resume task starts rental and passes min balance check.
   - If top-up amount < payment method minimum, client must top-up more.
6. Intent expiry:
   - Expired intent fails verify, no resume task runs.
7. Idempotency:
   - Re-verify does not create duplicate rentals if `intent_metadata.rental_id` exists.
8. `PENDING_POPUP`:
   - If device popup fails, rental remains `PENDING_POPUP` and async verification handles it.

## Confirmed Decisions
- PREPAID top-up amount equals `actual_price` after discount.
- POSTPAID: top-up is allowed only when balance is below `POSTPAID_MINIMUM_BALANCE`.
- For `payment_required`, use `success: false` with error code `payment_required` and include
  gateway data in the error context (no new success payload).
