# Rental + Payment Cross Verification Report (2026-02-11)

## Purpose
Code-verified audit of existing rental/payment lifecycle against the target behavior, with no assumptions.

## Scope Audited
### Rental flow files
- `api/user/rentals/views/core_views.py`
- `api/user/rentals/serializers/action_serializers.py`
- `api/user/rentals/services/rental/start/core.py`
- `api/user/rentals/services/rental/start/payment.py`
- `api/user/rentals/services/rental/extend.py`
- `api/user/rentals/views/support_views.py`
- `api/user/rentals/services/rental/return_powerbank.py`
- `api/user/rentals/services/rental/cancel.py`
- `api/user/rentals/tasks.py`

### Payment flow files
- `api/user/payments/views/core_views.py`
- `api/user/payments/serializers/rental_payment_serializer.py`
- `api/user/payments/views/wallet_views.py`
- `api/user/payments/services/payment_calculation.py`
- `api/user/payments/services/payment_intent.py`
- `api/user/payments/services/rental_payment.py`
- `api/user/payments/models/transaction.py`
- `api/user/payments/repositories/transaction_repository.py`

### Points/config files
- `api/common/utils/currency.py`
- `api/user/system/fixtures/app_config.json`
- `api/user/auth/services/auth_service.py`
- `api/user/points/services/referral_service.py`
- `api/user/auth/services/user_kyc_service.py`
- `api/user/auth/services/user_profile_service.py`
- `api/user/rentals/services/rental/return_powerbank.py`

## Lifecycle Verification (Current System)
1. Rental start (PREPAID)
- Uses `PaymentCalculationService` pre-check before atomic create.
- If insufficient and `payment_method_id` exists, creates top-up intent and raises `payment_required`.
- If sufficient, creates rental and processes prepayment (points first then wallet).
- Sources:
- `api/user/rentals/services/rental/start/core.py:94`
- `api/user/rentals/services/rental/start/core.py:104`
- `api/user/rentals/services/rental/start/payment.py:48`
- `api/user/payments/services/payment_calculation.py:21`

2. Rental start (POSTPAID)
- Checks `POSTPAID_MINIMUM_BALANCE` from AppConfig.
- If below minimum and payment method provided, creates top-up intent and raises `payment_required`.
- Sources:
- `api/user/rentals/services/rental/start/core.py:140`
- `api/user/rentals/services/rental/start/core.py:147`

3. Verify and resume
- `/payments/verify` credits wallet and enqueues resume task when `flow=RENTAL_START`.
- Resume task idempotent (`rental_id` guard) and tracks status in intent metadata.
- Sources:
- `api/user/payments/services/payment_intent.py:194`
- `api/user/rentals/tasks.py:477`

4. Other buying/payment paths
- Rental extension uses same pre-payment calculation and payment service.
- Rental due payment endpoint uses post-payment calculation and settlement.
- Auto-collection on return uses same calculation/service.
- Sources:
- `api/user/rentals/services/rental/extend.py:113`
- `api/user/rentals/views/support_views.py:68`
- `api/user/rentals/services/rental/return_powerbank.py:141`

## Critical Gaps Against Target Behavior
1. No `payment_mode` in rental start request contract.
- `api/user/rentals/serializers/action_serializers.py:13`

2. No explicit split input (`wallet_amount`, `points_to_use`) in rental start.
- `api/user/rentals/serializers/action_serializers.py:13`

3. Calculation engine is hardwired to points-first then wallet.
- `api/user/payments/services/payment_calculation.py:21`
- `api/user/payments/services/payment_calculation.py:190`

4. `payments/calculate-options` serializer lacks `amount` and mode/split fields, while view already tries to pass `amount`.
- `api/user/payments/serializers/rental_payment_serializer.py:27`
- `api/user/payments/views/core_views.py:217`

5. Rental start view currently returns business errors via standard error wrapper (`success=false,error`).
- `api/user/rentals/views/core_views.py:60`
- `api/common/mixins/response.py:29`

## Points Conversion + AppConfig Verification (Exact)
1. Points-to-money conversion for spending is currently hardcoded in utility defaults:
- `convert_points_to_amount(points, points_per_unit=10, unit_amount=1)` => `10 points = NPR 1`
- Source: `api/common/utils/currency.py:18`

2. Payment calculation also hardcodes/displays the same rate:
- `points_to_npr_rate: 10.0`
- `points_to_use = int(amount * 10)` when fully points-funded.
- Source: `api/user/payments/services/payment_calculation.py:127`
- Source: `api/user/payments/services/payment_calculation.py:198`

3. AppConfig fixture contains points award keys, but does not contain a dedicated redemption ratio key like `POINTS_PER_NPR_REDEEM`.
- Source: `api/user/system/fixtures/app_config.json`

4. AppConfig keys for awards are present and used in several flows:
- Signup: `POINTS_SIGNUP`
- Referral: `POINTS_REFERRAL_INVITER`, `POINTS_REFERRAL_INVITEE`
- KYC/Profile: `POINTS_KYC`, `POINTS_PROFILE`
- Rental completion: `POINTS_RENTAL_COMPLETE`, `POINTS_TIMELY_RETURN`
- Sources:
- `api/user/auth/services/auth_service.py:214`
- `api/user/points/services/referral_service.py:107`
- `api/user/auth/services/user_kyc_service.py:82`
- `api/user/auth/services/user_profile_service.py:193`
- `api/user/rentals/services/rental/return_powerbank.py:231`

5. Top-up points award currently uses hardcoded formula, not AppConfig values:
- `int(float(intent.amount) * 0.1)`
- Source: `api/user/payments/services/payment_intent.py:236`

6. `POINTS_TOPUP` and `POINTS_TOPUP_PER_NPR` exist in fixture but are not used in top-up reward calculation.
- Source: `api/user/system/fixtures/app_config.json:102`
- Source: `api/user/system/fixtures/app_config.json:135`
- Source (usage search): no runtime usage found outside fixture.

## Exact Implementation Impact (No Assumptions)
### Mandatory for your target behavior
1. Add `payment_mode`, `wallet_amount`, `points_to_use` in rental start request serializer.
2. Add mode-aware and split-aware logic in payment calculation service.
3. Wire rental-start precheck to mode-aware shortfall and intent amount.
4. Convert rental-start business-block responses to `success=true` with `data.error`.
5. Persist mode/split in intent metadata and use it in resume.
6. Add parity fields to `payments/calculate-options` serializer and service call.

### Not mandatory for this change (to avoid extra complexity)
1. Do not redesign points awarding scenarios.
2. Keep existing award flows as-is unless explicitly requested.

### Optional cleanup (recommended but separate)
1. Make top-up points award config-driven using `POINTS_TOPUP` + `POINTS_TOPUP_PER_NPR`.
2. Add explicit AppConfig key for points redemption ratio if admin-level configurability is needed.

## Final Conclusion
Core top-up + verify + resume lifecycle is already in place. The remaining work is focused and bounded: add `payment_mode` contract + split handling + wrapper shape change for rental-start business blocks, while keeping existing points awarding mechanisms unchanged.
