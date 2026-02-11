# Rental Payment Flow Cycle (Verified)

Last verified: 2026-02-11

This document is the working contract for rental payment lifecycle after payment-mode alignment across:
- rental start
- rental due settlement
- shared payment flow service
- callback/resume handling

## 1) API Response Contract

### 1.1 Standard success
```json
{
  "success": true,
  "message": "...",
  "data": {}
}
```

### 1.2 Standard error
```json
{
  "success": false,
  "error": {
    "code": "...",
    "message": "...",
    "context": {}
  }
}
```

### 1.3 Business-blocking payment responses (special contract)
For rental payment blockers, API intentionally returns:
- HTTP 200
- `success=true`
- blocking detail under `data.error`

```json
{
  "success": true,
  "message": "...",
  "data": {
    "error": {
      "code": "payment_required|payment_method_required|...",
      "message": "...",
      "context": {}
    }
  }
}
```

Business-blocking codes wrapped this way:
- `payment_required`
- `payment_method_required`
- `payment_mode_not_supported`
- `invalid_payment_mode`
- `invalid_wallet_points_split`
- `split_total_mismatch`

## 2) Rental Start Lifecycle (`POST /api/rentals/start`)

### 2.1 Request fields
```json
{
  "station_sn": "STATION_SN",
  "package_id": "PACKAGE_UUID",
  "powerbank_sn": "OPTIONAL",
  "payment_method_id": "OPTIONAL_UUID",
  "payment_mode": "wallet|points|wallet_points|direct",
  "wallet_amount": "OPTIONAL_DECIMAL",
  "points_to_use": "OPTIONAL_INT"
}
```

### 2.2 State lifecycle
1. Payment check runs first (by selected mode and package model).
2. On sufficient payment (PREPAID), rental is created with:
   - `status=PENDING_POPUP`
   - `payment_status=PAID`
   - `started_at=null` until popup success
3. On popup success, rental moves to:
   - `status=ACTIVE`
   - `started_at` is set
   - `due_at` recalculated from actual start time
4. On insufficient payment, endpoint returns wrapped business-block response.

### 2.3 Verified mode matrix (PREPAID, package price NPR 50)

| Mode | Balance condition | Expected behavior | Actual behavior (verified) |
|---|---|---|---|
| `wallet` | wallet sufficient | Rental starts | Rental started (`message=Rental started successfully`) |
| `wallet` | wallet insufficient | Block and ask payment method/gateway path | Wrapped `payment_method_required`, `context.shortfall` present |
| `points` | points sufficient | Rental starts from points | Rental started |
| `points` | points insufficient | Block and ask payment method/gateway path | Wrapped `payment_method_required`, `context.shortfall` present |
| `wallet_points` | combined sufficient | Rental starts from split/auto split | Rental started |
| `wallet_points` | combined insufficient | Block and ask payment method/gateway path | Wrapped `payment_method_required`, `context.shortfall` present |
| `direct` | any balance + `payment_method_id` | Always gateway intent | Wrapped `payment_required` with intent context |

### 2.4 Direct mode specifics
- `direct` without `payment_method_id` -> `payment_method_required`
- `direct` with `payment_method_id` -> `payment_required` with gateway context:
  - `intent_id`
  - `amount`
  - `gateway`, `gateway_url`
  - redirect data / form fields
  - `expires_at`, `status`

## 3) Rental Due Lifecycle (`POST /api/rentals/{rental_id}/pay-due`)

### 3.1 Request fields
```json
{
  "payment_method_id": "OPTIONAL_UUID",
  "payment_mode": "wallet|points|wallet_points|direct",
  "wallet_amount": "OPTIONAL_DECIMAL",
  "points_to_use": "OPTIONAL_INT"
}
```

### 3.2 Due amount rule
Required due is calculated by shared flow service:
- PREPAID rentals: collectible due is overdue amount
- POSTPAID rentals: usage/base + overdue
- Ongoing overdue rentals use realtime overdue for calculation

### 3.3 Verified mode matrix (test due amount NPR 75)

| Mode | Balance condition | Expected behavior | Actual behavior (verified) |
|---|---|---|---|
| `wallet` | wallet sufficient | Due settles from wallet | `Rental dues settled successfully`, transaction payload returned |
| `wallet` | wallet insufficient | Block and ask payment method/gateway path | Wrapped `payment_method_required`, includes `shortfall` + `required_due` |
| `points` | points sufficient | Due settles from points | Settled successfully, points used in breakdown |
| `points` | points insufficient | Block and ask payment method/gateway path | Wrapped `payment_method_required`, includes `shortfall` + `required_due` |
| `wallet_points` | combined sufficient | Due settles from combined balances | Settled successfully, wallet+points split in breakdown |
| `wallet_points` | combined insufficient | Block and ask payment method/gateway path | Wrapped `payment_method_required`, includes `shortfall` + `required_due` |
| `direct` | any balance + `payment_method_id` | Always gateway intent | Wrapped `payment_required` with intent context |

### 3.4 Due success payload shape
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "...",
    "rental_id": "...",
    "amount_paid": 75.0,
    "payment_breakdown": {
      "points_used": 550,
      "wallet_used": 20.0,
      "points_to_use": 550,
      "points_amount": 55.0,
      "wallet_amount": 20.0
    },
    "payment_status": "PAID",
    "account_unblocked": true
  }
}
```

Status note for ongoing overdue rentals:
- If `ended_at` is still `null` (powerbank not returned), due settlement is treated as interim.
- Rental remains `status=OVERDUE`.
- `payment_status` remains `PENDING` after settlement, because overdue can continue to accrue.
- Final `payment_status=PAID` is only guaranteed once return/final settlement is complete.

## 4) Insufficient Balance Branching Rules

For both start and due:
1. If insufficient and `payment_method_id` is missing:
   - wrapped `payment_method_required`
2. If insufficient and `payment_method_id` is provided:
   - wrapped `payment_required` with gateway intent context

Note on gateway minimum:
- If shortfall is below gateway minimum, intent amount is clamped to method minimum.
- Context still reports real shortfall.

## 5) POSTPAID Start Rules

Allowed modes:
- `wallet`
- `direct`

Rejected for POSTPAID:
- `points`
- `wallet_points`

Rejected modes return business-blocking payload with:
- `code=payment_mode_not_supported`

Minimum balance rule:
- Uses `POSTPAID_MINIMUM_BALANCE`
- If below minimum, top-up intent path is used
- If sufficient, rental starts with `payment_status=PENDING`

## 6) Verify + Resume Lifecycle

### 6.1 Intent verification
`POST /api/payments/verify` verifies gateway payment and credits wallet.

### 6.2 Resume on `flow=RENTAL_START`
After successful verification:
- async task resumes rental start using intent metadata
- keeps pricing override and selected resume mode
- idempotency guard prevents duplicate rental creation

### 6.3 Resume on `flow=RENTAL_DUE`
After successful verification:
- async task resumes due settlement
- uses stored due override metadata to avoid callback-time drift issues
- updates intent metadata with due status/transaction result

## 7) Payment Calculation Contract

### 7.1 Canonical payment breakdown keys
- `payment_breakdown.points_to_use`
- `payment_breakdown.points_amount`
- `payment_breakdown.wallet_amount`
- `payment_breakdown.direct_amount`
- `payment_breakdown.requested_split`

### 7.2 Backward-compatible keys (kept)
- `payment_breakdown.points_used`
- `payment_breakdown.wallet_used`
- top-level `topup_amount_required`

### 7.3 Points conversion
- Redemption conversion is config-driven via `POINTS_PER_NPR` (AppConfig)
- Current configured behavior remains `10 points = NPR 1`

### 7.4 Calculate Options API Request Contract
`POST /api/payments/calculate-options` now follows selector-based flow inference:
- Provide `package_id` for pre-payment calculation.
- Provide `rental_id` for due/post-payment calculation.
- Do not send `scenario`; it is inferred by selector.
- Do not send `amount`; payable amount is resolved from package/rental state.
- Exactly one selector is required (`package_id` xor `rental_id`).
- `wallet_amount` and `points_to_use` remain allowed only for `wallet_points`.
- Legacy input fields such as `scenario` and `amount` are rejected as unsupported.

## 8) Verified Alignment Scope

Primary aligned files:
- `api/user/payments/services/payment_calculation.py`
- `api/user/payments/services/rental_payment_flow.py`
- `api/user/rentals/services/rental/start/core.py`
- `api/user/rentals/services/rental/start/payment.py`
- `api/user/rentals/services/rental/rental_due_service.py`
- `api/user/rentals/views/core_views.py`
- `api/user/rentals/views/support_views.py`
- `api/user/payments/services/rental_payment.py`
- `api/user/rentals/tasks.py`

Regression tests used for alignment:
- `tests/user/payments/test_payment_calculation_modes.py`
- `tests/user/payments/test_rental_due_alignment.py`
- `tests/user/rentals/test_rental_due_view_payment_contract.py`
- `tests/user/rentals/test_rental_start_direct_amounts.py`
