# Rental Payment Flow Cycle (Request/Response)

This document shows full rental cycles for PREPAID and POSTPAID packages, with request/response formats based on the current API response wrappers (`success`, `message`, `data` or `error`).

## Common Response Wrapper
Success:
```json
{
  "success": true,
  "message": "...",
  "data": {}
}
```
Error:
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

## PREPAID Cycle (Sufficient Wallet/Points)
1. Start rental
Request:
```json
POST /api/rentals/start
{
  "station_sn": "STATION_SN",
  "package_id": "PACKAGE_UUID",
  "powerbank_sn": "OPTIONAL"
}
```
Response (201):
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "id": "RENTAL_UUID",
    "rental_code": "RNTXXXX",
    "status": "ACTIVE | PENDING_POPUP",
    "payment_status": "PAID",
    "started_at": "...",
    "due_at": "...",
    "amount_paid": "...",
    "station_name": "...",
    "package_name": "..."
  }
}
```
2. During rental (optional polling)
Request:
```json
GET /api/rentals/active
```
Response:
```json
{
  "success": true,
  "message": "Active rental retrieved",
  "data": { "...": "RentalDetailSerializer fields" }
}
```
3. Return power bank
Return is triggered by hardware (internal). No public API call required.
If late fees are applied, `payment_status` may become `PENDING`.
Auto-collection may run if wallet/points are sufficient.
4. If dues are still pending after auto-collection, user pays via:
```json
POST /api/rentals/{rental_id}/pay-due
```
Response:
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN_...",
    "rental_id": "RENTAL_UUID",
    "amount_paid": 100.0,
    "payment_breakdown": {
      "points_used": 0,
      "points_amount": 0.0,
      "wallet_used": 100.0
    },
    "payment_status": "PAID",
    "account_unblocked": true
  }
}
```

## PREPAID Cycle (Insufficient Wallet/Points)
1. Start rental (insufficient funds)
Request:
```json
POST /api/rentals/start
{
  "station_sn": "STATION_SN",
  "package_id": "PACKAGE_UUID",
  "payment_method_id": "PAYMENT_METHOD_UUID",
  "powerbank_sn": "OPTIONAL"
}
```
Response (payment required):
```json
{
  "success": false,
  "error": {
    "code": "payment_required",
    "message": "Payment required to start rental",
    "context": {
      "intent_id": "INTENT_UUID",
      "amount": "ACTUAL_PRICE_AFTER_DISCOUNT",
      "shortfall": "...",
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
```
2. Client completes gateway payment using returned gateway data.
3. Verify top-up
Request:
```json
POST /api/payments/verify
{
  "intent_id": "INTENT_UUID",
  "callback_data": { "...": "gateway payload" }
}
```
Response:
```json
{
  "success": true,
  "message": "Payment verified successfully",
  "data": {
    "status": "SUCCESS",
    "transaction_id": "TXN_...",
    "amount": "...",
    "new_balance": "...",
    "rental_start_status": "PENDING|SUCCESS|FAILED",
    "rental_id": "RENTAL_UUID",
    "rental_error": "..."
  }
}
```
4. Poll active rental if `rental_start_status` is `PENDING`:
```json
GET /api/rentals/active
```

## POSTPAID Cycle (Sufficient Minimum Balance)
1. Start rental
Request:
```json
POST /api/rentals/start
{
  "station_sn": "STATION_SN",
  "package_id": "PACKAGE_UUID",
  "powerbank_sn": "OPTIONAL"
}
```
Response (201):
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "id": "RENTAL_UUID",
    "rental_code": "RNTXXXX",
    "status": "ACTIVE | PENDING_POPUP",
    "payment_status": "PENDING",
    "started_at": "...",
    "due_at": "..."
  }
}
```
2. Return power bank (hardware-triggered).
Auto-collection may run if wallet/points are sufficient.
3. Pay dues after return (if still pending):
```json
POST /api/rentals/{rental_id}/pay-due
```
Response (same as PREPAID pay-due response).

## POSTPAID Cycle (Insufficient Minimum Balance)
1. Start rental (balance below `POSTPAID_MINIMUM_BALANCE`)
Request:
```json
POST /api/rentals/start
{
  "station_sn": "STATION_SN",
  "package_id": "PACKAGE_UUID",
  "payment_method_id": "PAYMENT_METHOD_UUID",
  "powerbank_sn": "OPTIONAL"
}
```
Response (payment required):
```json
{
  "success": false,
  "error": {
    "code": "payment_required",
    "message": "Payment required to start rental",
    "context": {
      "intent_id": "INTENT_UUID",
    "amount": "MIN_BALANCE_SHORTFALL",
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
```
2. Client completes gateway payment and verifies top-up (same as PREPAID flow).
3. Async rental start resumes after verification and will pass minimum balance check.

## Notes (Accuracy Rules)
- PREPAID top-up amount = `actual_price` after discount.
- POSTPAID top-up only triggers if balance < `POSTPAID_MINIMUM_BALANCE`.
- If payment method minimum amount is higher than shortfall, client must top-up more.
- Return is hardware-triggered; auto-collection may settle dues. If not, user pays via `/api/rentals/{id}/pay-due`.
- If device popup fails, rental may be `PENDING_POPUP` until async verification updates it.
