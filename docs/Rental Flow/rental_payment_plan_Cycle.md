# Rental Payment Flow Cycle (Verified)

Last verified: 2026-02-11

This file is the final cycle contract for rental start + rental dues after the `payment_mode` update and backward-compatible payment breakdown keys.

## 1) Response Contracts

Normal success:
```json
{
  "success": true,
  "message": "...",
  "data": {}
}
```

Normal error:
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

Rental start business-blocking (special contract):
- HTTP 200
- `success=true`
- error moved under `data.error`

```json
{
  "success": true,
  "message": "Payment required to start rental",
  "data": {
    "error": {
      "code": "payment_required",
      "message": "Payment required to start rental",
      "context": {
        "intent_id": "INTENT_UUID",
        "amount": "TOPUP_AMOUNT",
        "shortfall": "SHORTFALL",
        "payment_mode": "wallet|points|wallet_points|direct",
        "gateway": "khalti|esewa",
        "gateway_url": "...",
        "redirect_url": "...",
        "redirect_method": "POST",
        "form_fields": {},
        "expires_at": "...",
        "status": "PENDING"
      }
    }
  }
}
```

Business-blocking codes currently wrapped this way:
- `payment_required`
- `payment_method_required`
- `payment_mode_not_supported`
- `invalid_payment_mode`
- `invalid_wallet_points_split`
- `split_total_mismatch`

## 2) Rental Start Modes (PREPAID)

Request fields:
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

Behavior:
1. `wallet`
- Sufficient wallet: rental starts.
- Insufficient wallet: business-blocking payment-required response with shortfall intent.

2. `points`
- Sufficient points value: rental starts.
- Insufficient points: business-blocking payment-required response.
- Resume mode after successful top-up is `wallet_points` (gateway adds wallet, not points).
- Points are redeemed in current system granularity (`10 points = NPR 1`, i.e., 1 point = NPR 0.10). Any remaining fractional amount is handled via shortfall/wallet path.

3. `wallet_points`
- If explicit split provided (`wallet_amount` + `points_to_use`), split total must exactly match payable amount.
- If split is affordable, rental starts with that split.
- If not affordable, business-blocking payment-required response.
- Resume behavior is deterministic:
  - if shortfall includes points deficit, resume clears strict split and uses feasible `wallet_points` auto split;
  - if only wallet is short, requested split is preserved for resume.

4. `direct`
- Always returns business-blocking payment-required response (gateway intent).
- Resume mode after top-up is `wallet` to avoid direct-mode recursion.

## 3) POSTPAID Start Rules

Allowed start modes:
- `wallet`
- `direct`

Rejected for POSTPAID:
- `points`
- `wallet_points`

Rejected modes return business-blocking response with:
- `code=payment_mode_not_supported`

Minimum-balance logic:
- If wallet balance is below `POSTPAID_MINIMUM_BALANCE`, top-up intent is returned.
- If sufficient, rental starts with `payment_status=PENDING` (dues are settled later).

## 4) Verify + Resume Lifecycle

1. Client completes gateway payment from intent details.
2. Client verifies:
```json
POST /api/payments/verify
{
  "intent_id": "INTENT_UUID",
  "callback_data": { "...": "gateway payload" }
}
```
3. Verify flow credits wallet and enqueues rental resume when `flow=RENTAL_START`.
4. Resume task reuses stored rental metadata:
- pricing override (actual discounted price)
- resume payment mode
- optional split preferences
- idempotency guard (`rental_id` already set => no duplicate rental)

## 5) Backward-Compatible Payment Breakdown Keys

Returned by `PaymentCalculationService`:

Legacy keys (kept for compatibility):
- `payment_breakdown.points_used`
- `payment_breakdown.wallet_used`

Canonical keys (new/primary):
- `payment_breakdown.points_to_use`
- `payment_breakdown.points_amount`
- `payment_breakdown.wallet_amount`
- `payment_breakdown.direct_amount`
- `payment_breakdown.requested_split`

This ensures older callers still work while newer flows can rely on canonical names.

## 6) Recursive Alignment Verification (Code)

Verified aligned files:
- `api/user/payments/services/payment_calculation.py`
- `api/user/payments/views/core_views.py`
- `api/user/payments/serializers/rental_payment_serializer.py`
- `api/user/rentals/serializers/action_serializers.py`
- `api/user/rentals/services/rental/start/core.py`
- `api/user/rentals/services/rental/start/payment.py`
- `api/user/rentals/views/core_views.py`
- `api/user/rentals/tasks.py`
- `api/user/rentals/views/support_views.py` (legacy breakdown keys still consumed)

## 7) Non-Changed Scope (intentional)

- Points earning scenarios remain unchanged.
- Points redemption conversion remains current system behavior (`10 points = NPR 1`).
