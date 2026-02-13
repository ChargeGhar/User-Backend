# Pay Rental Due API Response Specification

**Version:** 1.0  
**Date:** 2026-02-13  
**Status:** Specification for Implementation

---

## Response Format Standards

### Type 1: Success Response (HTTP 200)

Rental dues successfully settled.

```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-XXXXX",
    "rental_id": "uuid",
    "rental_code": "RNT123456",
    "amount_paid": "100.00",
    "breakdown": {
      "wallet_amount": "50.00",
      "points_used": 500,
      "points_amount": "50.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

### Type 2: Payment Required (HTTP 402)

User needs to complete payment via gateway.

```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "uuid",
    "amount": "30.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "breakdown": {
      "wallet_amount": "20.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "gateway_url": "https://test-pay.khalti.com/?pidx=...",
    "form_fields": {...},
    "expires_at": "2026-02-13T16:17:55.279127+00:00"
  }
}
```

### Type 3: Error Response (HTTP 4xx/5xx)

Actual errors - invalid requests or system failures.

```json
{
  "success": false,
  "message": "Error description",
  "error_code": "specific_error_code",
  "context": {
    "additional": "error details"
  }
}
```

---

## Payment Modes

| Mode | Description | Supported |
|------|-------------|-----------|
| `wallet` | Wallet balance only | ✅ |
| `points` | Loyalty points only | ✅ |
| `wallet_points` | Wallet + points split | ✅ |
| `direct` | Force gateway payment | ✅ |

---

## Scenario Categories

1. **Wallet Mode** (Scenarios 1-2)
2. **Points Mode** (Scenarios 3-4)
3. **Wallet + Points Mode** (Scenarios 5-7)
4. **Direct Mode** (Scenario 8)
5. **Validation Errors** (Scenarios 9-15)

---

## WALLET MODE SCENARIOS

### Scenario 1: wallet + SUFFICIENT

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 150.00
- Points: 1000 (not used)

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 200
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-DUE-001",
    "rental_id": "550e8400-e29b-41d4-a716-446655440000",
    "rental_code": "RNT123456",
    "amount_paid": "100.00",
    "breakdown": {
      "wallet_amount": "100.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

**Database Changes:**
- Wallet: 150.00 → 50.00
- Points: 1000 (unchanged)
- Transaction created: type=RENTAL_DUE, status=SUCCESS, amount=100.00
- Rental: payment_status=PAID, status=COMPLETED

---

### Scenario 2: wallet + INSUFFICIENT

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 30.00
- Points: 1000 (not used)
- Payment method: Khalti

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet",
  "payment_method_id": "550e8400-e29b-41d4-a716-446655440301"
}
```

**Response:** HTTP 402
```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "25d11135-710c-46aa-8e3b-575b42ae217c",
    "amount": "70.00",
    "currency": "NPR",
    "shortfall": "70.00",
    "breakdown": {
      "wallet_amount": "30.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "gateway_url": "https://test-pay.khalti.com/?pidx=MVwM24Eys5L2Ev3BwxNPbV",
    "form_fields": {
      "return_url": "https://app.chargeghaar.com/payment/callback",
      "website_url": "https://chargeghaar.com"
    },
    "expires_at": "2026-02-13T16:17:55.279127+00:00"
  }
}
```

**Database Changes:**
- Wallet: 30.00 (unchanged - payment pending)
- Points: 1000 (unchanged)
- PaymentIntent created: amount=70.00, status=PENDING
- No transaction created yet
- Rental: payment_status=PENDING (unchanged)

---

## POINTS MODE SCENARIOS

### Scenario 3: points + SUFFICIENT

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 200.00 (not used)
- Points: 10000 (100 points = NPR 1)

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "points"
}
```

**Response:** HTTP 200
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-DUE-002",
    "rental_id": "550e8400-e29b-41d4-a716-446655440000",
    "rental_code": "RNT123456",
    "amount_paid": "100.00",
    "breakdown": {
      "wallet_amount": "0.00",
      "points_used": 10000,
      "points_amount": "100.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

**Database Changes:**
- Wallet: 200.00 (unchanged)
- Points: 10000 → 0
- Transaction created: type=RENTAL_DUE, status=SUCCESS, amount=100.00
- Rental: payment_status=PAID, status=COMPLETED

---

### Scenario 4: points + INSUFFICIENT

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 200.00 (not used)
- Points: 5000 (worth NPR 50.00)
- Payment method: eSewa

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "points",
  "payment_method_id": "550e8400-e29b-41d4-a716-446655440302"
}
```

**Response:** HTTP 402
```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "9d5219e5-ccf4-4373-9abc-c1a515b23ac4",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "50.00",
    "breakdown": {
      "wallet_amount": "0.00",
      "points_used": 5000,
      "points_amount": "50.00"
    },
    "gateway": "esewa",
    "payment_method_name": "eSewa",
    "gateway_url": "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
    "form_fields": {
      "amount": "50.00",
      "tax_amount": "0",
      "total_amount": "50.00",
      "transaction_uuid": "9d5219e5-ccf4-4373-9abc-c1a515b23ac4",
      "product_code": "EPAYTEST",
      "product_service_charge": "0",
      "product_delivery_charge": "0",
      "success_url": "https://app.chargeghaar.com/payment/callback",
      "failure_url": "https://app.chargeghaar.com/payment/callback"
    },
    "expires_at": "2026-02-13T16:17:55.578403+00:00"
  }
}
```

**Database Changes:**
- Wallet: 200.00 (unchanged)
- Points: 5000 (unchanged - payment pending)
- PaymentIntent created: amount=50.00, status=PENDING
- No transaction created yet
- Rental: payment_status=PENDING (unchanged)

---

## WALLET + POINTS MODE SCENARIOS

### Scenario 5: wallet_points + SUFFICIENT (auto-split)

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 60.00
- Points: 5000 (worth NPR 50.00)

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet_points"
}
```

**Response:** HTTP 200
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-DUE-003",
    "rental_id": "550e8400-e29b-41d4-a716-446655440000",
    "rental_code": "RNT123456",
    "amount_paid": "100.00",
    "breakdown": {
      "wallet_amount": "50.00",
      "points_used": 5000,
      "points_amount": "50.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

**Database Changes:**
- Wallet: 60.00 → 10.00
- Points: 5000 → 0
- Transaction created: type=RENTAL_DUE, status=SUCCESS, amount=100.00
- Rental: payment_status=PAID, status=COMPLETED

**Note:** System auto-calculates optimal split (points first, then wallet)

---

### Scenario 6: wallet_points + wallet short

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 20.00
- Points: 5000 (worth NPR 50.00)
- Payment method: Khalti

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet_points",
  "payment_method_id": "550e8400-e29b-41d4-a716-446655440301"
}
```

**Response:** HTTP 402
```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "bbb04f2a-0412-47d1-9221-e74cf20169dc",
    "amount": "30.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "breakdown": {
      "wallet_amount": "20.00",
      "points_used": 5000,
      "points_amount": "50.00"
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "gateway_url": "https://test-pay.khalti.com/?pidx=zhJZxB8nXm7JZFRGUtiEL3",
    "form_fields": {
      "return_url": "https://app.chargeghaar.com/payment/callback",
      "website_url": "https://chargeghaar.com"
    },
    "expires_at": "2026-02-13T16:17:55.279127+00:00"
  }
}
```

**Database Changes:**
- Wallet: 20.00 (unchanged - payment pending)
- Points: 5000 (unchanged - payment pending)
- PaymentIntent created: amount=30.00, status=PENDING
- Rental: payment_status=PENDING (unchanged)

---

### Scenario 7: wallet_points + points short

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 60.00
- Points: 2000 (worth NPR 20.00)
- Payment method: eSewa

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet_points",
  "payment_method_id": "550e8400-e29b-41d4-a716-446655440302"
}
```

**Response:** HTTP 402
```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "7c8d9e0f-1234-5678-9abc-def012345678",
    "amount": "20.00",
    "currency": "NPR",
    "shortfall": "20.00",
    "breakdown": {
      "wallet_amount": "60.00",
      "points_used": 2000,
      "points_amount": "20.00"
    },
    "gateway": "esewa",
    "payment_method_name": "eSewa",
    "gateway_url": "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
    "form_fields": {
      "amount": "20.00",
      "tax_amount": "0",
      "total_amount": "20.00",
      "transaction_uuid": "7c8d9e0f-1234-5678-9abc-def012345678",
      "product_code": "EPAYTEST",
      "product_service_charge": "0",
      "product_delivery_charge": "0",
      "success_url": "https://app.chargeghaar.com/payment/callback",
      "failure_url": "https://app.chargeghaar.com/payment/callback"
    },
    "expires_at": "2026-02-13T16:17:55.578403+00:00"
  }
}
```

**Database Changes:**
- Wallet: 60.00 (unchanged - payment pending)
- Points: 2000 (unchanged - payment pending)
- PaymentIntent created: amount=20.00, status=PENDING
- Rental: payment_status=PENDING (unchanged)

---

## DIRECT MODE SCENARIO

### Scenario 8: direct mode (force gateway)

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 200.00 (ignored)
- Points: 10000 (ignored)
- Payment method: Khalti

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "direct",
  "payment_method_id": "550e8400-e29b-41d4-a716-446655440301"
}
```

**Response:** HTTP 402
```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {
    "intent_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "amount": "100.00",
    "currency": "NPR",
    "shortfall": "100.00",
    "breakdown": {
      "wallet_amount": "0.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "gateway_url": "https://test-pay.khalti.com/?pidx=ABC123XYZ789",
    "form_fields": {
      "return_url": "https://app.chargeghaar.com/payment/callback",
      "website_url": "https://chargeghaar.com"
    },
    "expires_at": "2026-02-13T16:17:55.279127+00:00"
  }
}
```

**Database Changes:**
- Wallet: 200.00 (unchanged)
- Points: 10000 (unchanged)
- PaymentIntent created: amount=100.00, status=PENDING
- Rental: payment_status=PENDING (unchanged)

**Note:** Direct mode always requires gateway payment, ignoring wallet/points

---

## VALIDATION ERROR SCENARIOS

### Scenario 9: No dues pending

**Setup:**
- Rental: payment_status=PAID
- Rental due: NPR 0.00

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 400
```json
{
  "success": false,
  "message": "Rental dues have already been settled",
  "error_code": "dues_already_paid"
}
```

---

### Scenario 10: Rental not found

**Setup:**
- Invalid rental_id or rental belongs to different user

**Request:**
```json
POST /api/rentals/invalid-id/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 404
```json
{
  "success": false,
  "message": "Rental not found",
  "error_code": "rental_not_found"
}
```

---

### Scenario 11: direct mode without payment_method_id

**Setup:**
- Rental due: NPR 100.00
- No payment_method_id provided

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "direct"
}
```

**Response:** HTTP 400
```json
{
  "success": false,
  "message": "Payment method is required for direct payment mode",
  "error_code": "validation_error",
  "context": {
    "payment_method_id": [
      "Payment method is required for direct payment mode"
    ]
  }
}
```

---

### Scenario 12: Insufficient balance without payment_method_id

**Setup:**
- Rental due: NPR 100.00
- Wallet balance: NPR 30.00
- No payment_method_id provided

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 400
```json
{
  "success": false,
  "message": "Payment method is required when balance is insufficient",
  "error_code": "payment_method_required",
  "context": {
    "payment_mode": "wallet",
    "shortfall": "70.00",
    "required_due": "100.00"
  }
}
```

---

### Scenario 13: Invalid payment_mode

**Setup:**
- Invalid payment_mode value

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "invalid_mode"
}
```

**Response:** HTTP 400
```json
{
  "success": false,
  "message": "Validation error",
  "error_code": "validation_error",
  "context": {
    "payment_mode": [
      "\"invalid_mode\" is not a valid choice."
    ]
  }
}
```

---

### Scenario 14: Invalid payment_method_id

**Setup:**
- Invalid or non-existent payment_method_id

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet",
  "payment_method_id": "invalid-uuid"
}
```

**Response:** HTTP 400
```json
{
  "success": false,
  "message": "Payment method not found or inactive",
  "error_code": "payment_method_not_found"
}
```

---

### Scenario 15: Rental not started (popup failed)

**Setup:**
- Rental: started_at=NULL, payment_status=PAID
- Rental metadata: popup_failed=true

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 400
```json
{
  "success": false,
  "message": "Rental was not started due to popup timeout/failure. Due settlement is not applicable.",
  "error_code": "rental_not_started"
}
```

---

## Special Cases

### Case 1: OVERDUE rental - powerbank NOT returned

**Setup:**
- Rental: status=OVERDUE, ended_at=NULL
- Powerbank: Still with user (not in any station)
- Rental due: NPR 150.00 (base + late fees)

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 200
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-DUE-004",
    "rental_id": "550e8400-e29b-41d4-a716-446655440000",
    "rental_code": "RNT123456",
    "amount_paid": "150.00",
    "breakdown": {
      "wallet_amount": "150.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "payment_status": "PAID",
    "rental_status": "OVERDUE",
    "account_unblocked": true
  }
}
```

**Database Changes:**
- Wallet: Deducted 150.00
- Transaction created: type=RENTAL_DUE, status=SUCCESS
- Rental: payment_status=PAID, status=OVERDUE (NOT COMPLETED)
- Powerbank: Still with user

**Note:** Status stays OVERDUE because powerbank not returned

---

### Case 2: OVERDUE rental - powerbank returned

**Setup:**
- Rental: status=OVERDUE, ended_at=2026-02-13T10:00:00
- Powerbank: Returned to station
- Rental due: NPR 150.00 (base + late fees)

**Request:**
```json
POST /api/rentals/{rental_id}/pay-due
{
  "payment_mode": "wallet"
}
```

**Response:** HTTP 200
```json
{
  "success": true,
  "message": "Rental dues settled successfully",
  "data": {
    "transaction_id": "TXN-DUE-005",
    "rental_id": "550e8400-e29b-41d4-a716-446655440000",
    "rental_code": "RNT123456",
    "amount_paid": "150.00",
    "breakdown": {
      "wallet_amount": "150.00",
      "points_used": 0,
      "points_amount": "0.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

**Database Changes:**
- Wallet: Deducted 150.00
- Transaction created: type=RENTAL_DUE, status=SUCCESS
- Rental: payment_status=PAID, status=COMPLETED
- Powerbank: In station

**Note:** Status changes to COMPLETED because powerbank already returned

---

## Response Field Definitions

### Success Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | string | Unique transaction identifier |
| `rental_id` | string (UUID) | Rental identifier |
| `rental_code` | string | Human-readable rental code |
| `amount_paid` | string | Total amount paid (2 decimals) |
| `breakdown.wallet_amount` | string | Amount from wallet (2 decimals) |
| `breakdown.points_used` | integer | Points deducted |
| `breakdown.points_amount` | string | Points value in NPR (2 decimals) |
| `payment_status` | string | "PAID" |
| `rental_status` | string | "COMPLETED" or "OVERDUE" |
| `account_unblocked` | boolean | Always true on success |

### Payment Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `intent_id` | string (UUID) | Payment intent identifier |
| `amount` | string | Gateway payment amount (2 decimals) |
| `currency` | string | "NPR" |
| `shortfall` | string | Amount needed (2 decimals) |
| `breakdown.wallet_amount` | string | Wallet contribution (2 decimals) |
| `breakdown.points_used` | integer | Points contribution |
| `breakdown.points_amount` | string | Points value (2 decimals) |
| `gateway` | string | "khalti" or "esewa" |
| `payment_method_name` | string | Display name |
| `gateway_url` | string | Payment page URL |
| `form_fields` | object | Gateway-specific fields |
| `expires_at` | string (ISO 8601) | Intent expiration time |

---

## Summary Table

| Scenario | Payment Mode | Balance | HTTP | success | error_code |
|----------|--------------|---------|------|---------|------------|
| 1 | wallet | Sufficient | 200 | true | - |
| 2 | wallet | Insufficient | 402 | false | payment_required |
| 3 | points | Sufficient | 200 | true | - |
| 4 | points | Insufficient | 402 | false | payment_required |
| 5 | wallet_points | Sufficient | 200 | true | - |
| 6 | wallet_points | Wallet short | 402 | false | payment_required |
| 7 | wallet_points | Points short | 402 | false | payment_required |
| 8 | direct | Any | 402 | false | payment_required |
| 9 | any | Already paid | 400 | false | dues_already_paid |
| 10 | any | Not found | 404 | false | rental_not_found |
| 11 | direct | No method_id | 400 | false | validation_error |
| 12 | wallet | Insufficient + no method | 400 | false | payment_method_required |
| 13 | invalid | Any | 400 | false | validation_error |
| 14 | any | Invalid method | 400 | false | payment_method_not_found |
| 15 | any | Not started | 400 | false | rental_not_started |

---

## Key Differences from Rental Start

| Aspect | Rental Start | Pay Due |
|--------|--------------|---------|
| Success HTTP | 201 (Created) | 200 (OK) |
| Success status | PENDING_POPUP or ACTIVE | COMPLETED or OVERDUE |
| Transaction type | RENTAL | RENTAL_DUE |
| Creates rental | Yes | No (updates existing) |
| Powerbank check | Availability | Return status |
| Account unblocked | N/A | Always true on success |

---

## Testing Checklist

- [ ] Scenario 1: wallet + SUFFICIENT
- [ ] Scenario 2: wallet + INSUFFICIENT
- [ ] Scenario 3: points + SUFFICIENT
- [ ] Scenario 4: points + INSUFFICIENT
- [ ] Scenario 5: wallet_points + SUFFICIENT
- [ ] Scenario 6: wallet_points + wallet short
- [ ] Scenario 7: wallet_points + points short
- [ ] Scenario 8: direct mode
- [ ] Scenario 9: No dues pending
- [ ] Scenario 10: Rental not found
- [ ] Scenario 11: direct without payment_method_id
- [ ] Scenario 12: Insufficient without payment_method_id
- [ ] Scenario 13: Invalid payment_mode
- [ ] Scenario 14: Invalid payment_method_id
- [ ] Scenario 15: Rental not started
- [ ] Case 1: OVERDUE - powerbank NOT returned
- [ ] Case 2: OVERDUE - powerbank returned
- [ ] Test with Khalti gateway
- [ ] Test with eSewa gateway

---

**Total Scenarios:** 15 + 2 special cases = 17  
**Status:** Ready for Cross-Verification
