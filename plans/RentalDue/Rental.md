# Rental Start API Response Specification

**Version:** 2.0  
**Date:** 2026-02-13  
**Status:** Draft for Implementation

---

## Response Format Standards

### Type 1: Success Response (HTTP 201)

Rental successfully started and activated.

```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    ...
  }
}
```

### Type 2: Payment Required (HTTP 402)

User needs to complete payment via gateway. **NOT an error** - it's a business flow requirement.

```json
{
  "success": false,
  "message": "Payment required to start rental",
  "error_code": "payment_required",
  "data": {
    "intent_id": "uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "gateway": "khalti",
    "gateway_url": "https://...",
    "form_fields": {...},
    ...
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

## Payment Modes & Models

### Payment Modes

| Mode | Description | PREPAID | POSTPAID |
|------|-------------|---------|----------|
| `wallet` | Wallet balance only | ✅ | ✅ |
| `points` | Loyalty points only | ✅ | ❌ |
| `wallet_points` | Wallet + points split | ✅ | ❌ |
| `direct` | Force gateway payment | ✅ | ✅ |

### Payment Models

| Model | Payment Timing | Balance Check |
|-------|----------------|---------------|
| `PREPAID` | Before rental starts | Must cover rental price |
| `POSTPAID` | After rental ends | Must meet minimum balance (e.g., NPR 50) |

---

## PREPAID Scenarios


### Scenario 1: PREPAID + wallet + SUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    "package": {
      "id": "pkg-123",
      "name": "2 Hour Package",
      "price": "50.00",
      "payment_model": "PREPAID"
    },
    "pricing": {
      "original_price": "50.00",
      "discount_amount": "0.00",
      "actual_price": "50.00",
      "amount_paid": "50.00"
    },
    "payment": {
      "payment_model": "PREPAID",
      "payment_mode": "wallet",
      "payment_status": "PAID",
      "breakdown": {
        "wallet_amount": "50.00",
        "points_used": 0,
        "points_amount": "0.00"
      }
    }
  }
}
```

---

### Scenario 2: PREPAID + wallet + INSUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Insufficient wallet balance. Please top-up to continue.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "payment_mode": "wallet",
    "wallet_shortfall": "30.00",
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 5000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Complete payment via Khalti to top-up your wallet",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

---

### Scenario 3: PREPAID + points + SUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "points"
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    "package": {
      "id": "pkg-123",
      "name": "2 Hour Package",
      "price": "50.00",
      "payment_model": "PREPAID"
    },
    "pricing": {
      "original_price": "50.00",
      "discount_amount": "0.00",
      "actual_price": "50.00",
      "amount_paid": "50.00"
    },
    "payment": {
      "payment_model": "PREPAID",
      "payment_mode": "points",
      "payment_status": "PAID",
      "breakdown": {
        "wallet_amount": "0.00",
        "points_used": 500,
        "points_amount": "50.00"
      }
    }
  }
}
```

---

### Scenario 4: PREPAID + points + INSUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "points",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Insufficient points. Wallet top-up required.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "50.00",
    "payment_mode": "wallet",
    "wallet_shortfall": "50.00",
    "points_shortfall": 500,
    "points_shortfall_amount": "50.00",
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 5000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Points cannot be purchased. Please top-up wallet instead.",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

**Note:** Points cannot be purchased via gateway. System switches to wallet mode.

---

### Scenario 5: PREPAID + wallet_points + SUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet_points",
  "wallet_amount": "30.00",
  "points_to_use": 200
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    "package": {
      "id": "pkg-123",
      "name": "2 Hour Package",
      "price": "50.00",
      "payment_model": "PREPAID"
    },
    "pricing": {
      "original_price": "50.00",
      "discount_amount": "0.00",
      "actual_price": "50.00",
      "amount_paid": "50.00"
    },
    "payment": {
      "payment_model": "PREPAID",
      "payment_mode": "wallet_points",
      "payment_status": "PAID",
      "breakdown": {
        "wallet_amount": "30.00",
        "points_used": 200,
        "points_amount": "20.00"
      }
    }
  }
}
```

---

### Scenario 6: PREPAID + wallet_points + INSUFFICIENT (Wallet Short)

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet_points",
  "wallet_amount": "30.00",
  "points_to_use": 200,
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Insufficient wallet balance. Please top-up to continue.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "15.00",
    "payment_mode": "wallet_points",
    "wallet_shortfall": "15.00",
    "points_shortfall": 0,
    "points_shortfall_amount": "0.00",
    "resume_preferences": {
      "wallet_amount": "30.00",
      "points_to_use": 200
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 1500,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Top-up wallet to complete your rental with points",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

**Note:** Points are sufficient, only wallet needs top-up. Split preferences are preserved.

---

### Scenario 7: PREPAID + wallet_points + INSUFFICIENT (Points Short)

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet_points",
  "wallet_amount": "30.00",
  "points_to_use": 200,
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Insufficient points. Wallet top-up required.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "50.00",
    "payment_mode": "wallet_points",
    "wallet_shortfall": "30.00",
    "points_shortfall": 200,
    "points_shortfall_amount": "20.00",
    "resume_preferences": null,
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 5000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Points cannot be purchased. Please top-up wallet instead.",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

**Note:** Points insufficient. Split preferences are cleared, full wallet payment required.

---

### Scenario 8: PREPAID + direct

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "direct",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Payment via gateway required",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "50.00",
    "payment_mode": "wallet",
    "wallet_shortfall": "50.00",
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 5000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Complete payment via Khalti",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

**Note:** Direct mode always requires gateway payment, regardless of balance.

---

## POSTPAID Scenarios

### Scenario 9: POSTPAID + wallet + SUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-456",
  "payment_mode": "wallet"
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    "package": {
      "id": "pkg-456",
      "name": "4 Hour Package",
      "price": "80.00",
      "payment_model": "POSTPAID"
    },
    "pricing": {
      "original_price": "80.00",
      "discount_amount": "0.00",
      "actual_price": "80.00",
      "amount_paid": "0.00"
    },
    "payment": {
      "payment_model": "POSTPAID",
      "payment_mode": "wallet",
      "payment_status": "PENDING",
      "breakdown": null,
      "pending_transaction_id": "txn-uuid"
    }
  }
}
```

**Note:** No payment deducted at start. Wallet balance meets minimum requirement (e.g., NPR 50).

---

### Scenario 10: POSTPAID + wallet + INSUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-456",
  "payment_mode": "wallet",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Minimum wallet balance required for POSTPAID rental",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "payment_mode": "wallet",
    "wallet_shortfall": "30.00",
    "postpaid_min_balance": "50.00",
    "current_balance": "20.00",
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 3000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Top-up wallet to meet minimum balance requirement",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

---

### Scenario 11: POSTPAID + points (NOT SUPPORTED)

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-456",
  "payment_mode": "points"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "Payment mode 'points' is not supported for POSTPAID packages",
  "error_code": "payment_mode_not_supported",
  "context": {
    "payment_mode": "points",
    "payment_model": "POSTPAID",
    "supported_modes": ["wallet", "direct"]
  }
}
```

---

### Scenario 12: POSTPAID + wallet_points (NOT SUPPORTED)

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-456",
  "payment_mode": "wallet_points"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "Payment mode 'wallet_points' is not supported for POSTPAID packages",
  "error_code": "payment_mode_not_supported",
  "context": {
    "payment_mode": "wallet_points",
    "payment_model": "POSTPAID",
    "supported_modes": ["wallet", "direct"]
  }
}
```

---

### Scenario 13: POSTPAID + direct + SUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-456",
  "payment_mode": "direct",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    "package": {
      "id": "pkg-456",
      "name": "4 Hour Package",
      "price": "80.00",
      "payment_model": "POSTPAID"
    },
    "pricing": {
      "original_price": "80.00",
      "discount_amount": "0.00",
      "actual_price": "80.00",
      "amount_paid": "0.00"
    },
    "payment": {
      "payment_model": "POSTPAID",
      "payment_mode": "wallet",
      "payment_status": "PENDING",
      "breakdown": null,
      "pending_transaction_id": "txn-uuid"
    }
  }
}
```

**Note:** If minimum balance already met, rental starts without gateway payment.

---

### Scenario 14: POSTPAID + direct + INSUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-456",
  "payment_mode": "direct",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Minimum wallet balance required for POSTPAID rental",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "50.00",
    "currency": "NPR",
    "shortfall": "30.00",
    "payment_mode": "wallet",
    "wallet_shortfall": "30.00",
    "postpaid_min_balance": "50.00",
    "current_balance": "20.00",
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 3000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Top-up wallet to meet minimum balance requirement",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

---

## Discount Scenarios

### Scenario 15: PREPAID + Discount + SUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental started successfully with 20% discount applied",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "ACTIVE",
    "package": {
      "id": "pkg-123",
      "name": "2 Hour Package",
      "price": "50.00",
      "payment_model": "PREPAID"
    },
    "pricing": {
      "original_price": "50.00",
      "discount_amount": "10.00",
      "actual_price": "40.00",
      "amount_paid": "40.00"
    },
    "payment": {
      "payment_model": "PREPAID",
      "payment_mode": "wallet",
      "payment_status": "PAID",
      "breakdown": {
        "wallet_amount": "40.00",
        "points_used": 0,
        "points_amount": "0.00"
      }
    },
    "discount": {
      "id": "discount-uuid",
      "code": "FIRST20",
      "discount_percent": "20.00",
      "discount_amount": "10.00",
      "description": "20% off first rental"
    }
  }
}
```

---

### Scenario 16: PREPAID + Discount + INSUFFICIENT

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet",
  "payment_method_id": "pm-khalti-123"
}
```

**Response: HTTP 402**
```json
{
  "success": false,
  "message": "Insufficient wallet balance. Discount will be applied after payment.",
  "error_code": "payment_required",
  "data": {
    "intent_id": "intent-uuid",
    "amount": "40.00",
    "currency": "NPR",
    "shortfall": "40.00",
    "payment_mode": "wallet",
    "wallet_shortfall": "40.00",
    "discount_applied": {
      "discount_id": "discount-uuid",
      "discount_code": "FIRST20",
      "discount_percent": "20.00",
      "original_price": "50.00",
      "discount_amount": "10.00",
      "actual_price": "40.00"
    },
    "gateway": "khalti",
    "payment_method_name": "Khalti",
    "payment_method_icon": "https://cdn.example.com/khalti.png",
    "gateway_url": "https://khalti.com/payment",
    "redirect_url": "https://khalti.com/payment/redirect",
    "redirect_method": "POST",
    "form_fields": {
      "public_key": "test_public_key",
      "amount": 4000,
      "product_identity": "intent-uuid",
      "product_name": "Wallet Top-up"
    },
    "payment_instructions": "Top-up wallet. Your 20% discount will be applied automatically.",
    "expires_at": "2026-02-13T13:00:00Z",
    "status": "PENDING"
  }
}
```

**Note:** Top-up amount is based on discounted price (NPR 40), not original price (NPR 50).

---

## Error Scenarios

### Scenario 17: Missing Payment Method

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "Payment method is required when balance is insufficient",
  "error_code": "payment_method_required",
  "context": {
    "payment_mode": "wallet",
    "shortfall": "30.00",
    "current_balance": "20.00",
    "required_amount": "50.00"
  }
}
```

---

### Scenario 18: Invalid Payment Mode

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "crypto"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "Invalid payment mode",
  "error_code": "invalid_payment_mode",
  "context": {
    "payment_mode": "crypto",
    "valid_modes": ["wallet", "points", "wallet_points", "direct"]
  }
}
```

---

### Scenario 19: Station Not Found

**Request:**
```json
{
  "station_sn": "INVALID",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 404**
```json
{
  "success": false,
  "message": "Station not found",
  "error_code": "station_not_found",
  "context": {
    "station_sn": "INVALID"
  }
}
```

---

### Scenario 20: Package Not Found

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "invalid-pkg",
  "payment_mode": "wallet"
}
```

**Response: HTTP 404**
```json
{
  "success": false,
  "message": "Package not found or inactive",
  "error_code": "package_not_found",
  "context": {
    "package_id": "invalid-pkg"
  }
}
```

---

### Scenario 21: Station Offline

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "Station is currently offline",
  "error_code": "station_offline",
  "context": {
    "station_sn": "STN001",
    "station_name": "Station Alpha",
    "last_seen": "2026-02-13T10:00:00Z"
  }
}
```

---

### Scenario 22: No Power Banks Available

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "No power banks available at this station",
  "error_code": "no_powerbanks_available",
  "context": {
    "station_sn": "STN001",
    "station_name": "Station Alpha",
    "available_count": 0,
    "total_slots": 8
  }
}
```

---

### Scenario 23: Active Rental Exists

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 400**
```json
{
  "success": false,
  "message": "You already have an active rental",
  "error_code": "active_rental_exists",
  "context": {
    "active_rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "started_at": "2026-02-13T11:00:00Z",
    "due_at": "2026-02-13T13:00:00Z"
  }
}
```

---

### Scenario 24: Device Popup Timeout

**Request:**
```json
{
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "payment_mode": "wallet"
}
```

**Response: HTTP 201**
```json
{
  "success": true,
  "message": "Rental created. Device popup is being verified.",
  "data": {
    "rental_id": "rental-uuid",
    "rental_code": "RNT123456",
    "status": "PENDING_POPUP",
    "package": {
      "id": "pkg-123",
      "name": "2 Hour Package",
      "price": "50.00",
      "payment_model": "PREPAID"
    },
    "pricing": {
      "original_price": "50.00",
      "discount_amount": "0.00",
      "actual_price": "50.00",
      "amount_paid": "50.00"
    },
    "payment": {
      "payment_model": "PREPAID",
      "payment_mode": "wallet",
      "payment_status": "PAID",
      "breakdown": {
        "wallet_amount": "50.00",
        "points_used": 0,
        "points_amount": "0.00"
      }
    },
    "verification": {
      "status": "PENDING",
      "message": "Device popup is being verified. You will be notified once confirmed.",
      "estimated_completion": "2026-02-13T12:35:00Z"
    }
  }
}
```

**Note:** Payment already processed. Async verification will activate rental or refund if popup fails.

---

## Implementation Guidelines

### 1. Response Consistency Rules

✅ **DO:**
- Use `"success": true` only for HTTP 2xx responses
- Use `"success": false` for HTTP 4xx/5xx and payment_required (402)
- Always use decimal strings for money: `"50.00"` not `50`
- Always use integers for points: `500` not `"500"`
- Always include `error_code` when `success: false`
- Always include timestamps in ISO 8601 format with timezone
- Always include currency code (`"NPR"`)

❌ **DON'T:**
- Don't wrap `payment_required` in nested `error` object
- Don't use `success: true` for payment_required responses
- Don't mix number types (decimals for money, integers for points)
- Don't omit `error_code` in error responses
- Don't return HTTP 200 for errors

### 2. HTTP Status Code Mapping

| Status | Use Case | success |
|--------|----------|---------|
| 201 | Rental started successfully | `true` |
| 402 | Payment required | `false` |
| 400 | Bad request / validation error | `false` |
| 404 | Resource not found | `false` |
| 500 | Internal server error | `false` |

### 3. Payment Mode Resolution Logic

```python
def resolve_resume_mode(requested_mode, points_short):
    """Determine payment mode after gateway top-up"""
    if requested_mode == 'direct':
        return 'wallet'
    elif requested_mode == 'points' and points_short:
        return 'wallet'  # Points can't be bought
    elif requested_mode == 'wallet_points' and points_short:
        return 'wallet_points'  # But clear split preferences
    else:
        return requested_mode
```

### 4. Shortfall Calculation

**PREPAID:**
```python
shortfall = actual_price - (wallet_balance + points_value)
wallet_shortfall = max(0, actual_price - points_value - wallet_balance)
points_shortfall = max(0, points_needed - available_points)
```

**POSTPAID:**
```python
shortfall = POSTPAID_MIN_BALANCE - wallet_balance
wallet_shortfall = shortfall
points_shortfall = 0  # Not applicable
```

### 5. Gateway Amount Resolution

```python
def resolve_gateway_amount(shortfall, payment_method):
    """Clamp to gateway minimum"""
    min_amount = payment_method.min_amount or Decimal('0.00')
    return max(shortfall, min_amount).quantize(Decimal('0.01'))
```

### 6. Discount Application

- Calculate discount **before** payment validation
- Top-up amount = `actual_price` (after discount)
- Store discount details in intent metadata
- Apply discount on rental resume after payment
- Record discount usage only after rental activation

### 7. Intent Metadata Structure

```json
{
  "flow": "RENTAL_START",
  "station_sn": "STN001",
  "package_id": "pkg-123",
  "powerbank_sn": "PB001",
  "actual_price": "40.00",
  "discount_id": "discount-uuid",
  "discount_amount": "10.00",
  "discount_metadata": {...},
  "payment_model": "PREPAID",
  "payment_mode_requested": "wallet_points",
  "payment_mode": "wallet_points",
  "wallet_amount": "30.00",
  "points_to_use": 100,
  "topup_amount_required": "50.00",
  "shortfall": "10.00"
}
```

### 8. Error Context Guidelines

Always include relevant context:

```python
# Good
{
  "error_code": "station_offline",
  "context": {
    "station_sn": "STN001",
    "station_name": "Station Alpha",
    "last_seen": "2026-02-13T10:00:00Z"
  }
}

# Bad
{
  "error_code": "station_offline",
  "context": {}
}
```

---

## Testing Checklist

### PREPAID Tests

- [ ] **Scenario 1:** wallet + sufficient → HTTP 201, rental ACTIVE
- [ ] **Scenario 2:** wallet + insufficient → HTTP 402, payment_required
- [ ] **Scenario 3:** points + sufficient → HTTP 201, rental ACTIVE
- [ ] **Scenario 4:** points + insufficient → HTTP 402, wallet mode
- [ ] **Scenario 5:** wallet_points + sufficient → HTTP 201, rental ACTIVE
- [ ] **Scenario 6:** wallet_points + wallet short → HTTP 402, keep split
- [ ] **Scenario 7:** wallet_points + points short → HTTP 402, clear split
- [ ] **Scenario 8:** direct → HTTP 402, forced gateway
- [ ] **Scenario 15:** discount + sufficient → HTTP 201, discounted price
- [ ] **Scenario 16:** discount + insufficient → HTTP 402, discounted amount

### POSTPAID Tests

- [ ] **Scenario 9:** wallet + sufficient → HTTP 201, rental ACTIVE
- [ ] **Scenario 10:** wallet + insufficient → HTTP 402, min balance
- [ ] **Scenario 11:** points → HTTP 400, not supported
- [ ] **Scenario 12:** wallet_points → HTTP 400, not supported
- [ ] **Scenario 13:** direct + sufficient → HTTP 201, rental ACTIVE
- [ ] **Scenario 14:** direct + insufficient → HTTP 402, min balance

### Error Tests

- [ ] **Scenario 17:** Missing payment_method_id → HTTP 400
- [ ] **Scenario 18:** Invalid payment_mode → HTTP 400
- [ ] **Scenario 19:** Station not found → HTTP 404
- [ ] **Scenario 20:** Package not found → HTTP 404
- [ ] **Scenario 21:** Station offline → HTTP 400
- [ ] **Scenario 22:** No power banks → HTTP 400
- [ ] **Scenario 23:** Active rental exists → HTTP 400
- [ ] **Scenario 24:** Device popup timeout → HTTP 201, PENDING_POPUP

### Gateway Integration Tests

- [ ] Intent creation with correct metadata
- [ ] Gateway minimum amount enforcement
- [ ] Intent expiration handling
- [ ] Successful payment verification
- [ ] Failed payment verification
- [ ] Rental resume after payment
- [ ] Idempotency on duplicate verify
- [ ] Discount preservation across payment flow

### Edge Cases

- [ ] Gateway min > shortfall → top-up = gateway min
- [ ] Discount expires during payment → handle gracefully
- [ ] Station goes offline during payment → refund
- [ ] Power bank unavailable after payment → refund
- [ ] User starts another rental during payment → reject
- [ ] Intent expires before verification → reject

---

## API Contract Summary

### Request Schema

```typescript
interface RentalStartRequest {
  station_sn: string;                    // Required
  package_id: string;                    // Required
  powerbank_sn?: string;                 // Optional
  payment_mode?: 'wallet' | 'points' | 'wallet_points' | 'direct';  // Default: wallet_points
  payment_method_id?: string;            // Required when insufficient
  wallet_amount?: string;                // Optional, for wallet_points
  points_to_use?: number;                // Optional, for wallet_points
}
```

### Success Response Schema

```typescript
interface RentalStartSuccess {
  success: true;
  message: string;
  data: {
    rental_id: string;
    rental_code: string;
    status: 'ACTIVE' | 'PENDING_POPUP';
    package: PackageDetails;
    pricing: PricingDetails;
    payment: PaymentDetails;
    discount?: DiscountDetails;
    verification?: VerificationDetails;  // Only for PENDING_POPUP
  };
}
```

### Payment Required Schema

```typescript
interface PaymentRequiredResponse {
  success: false;
  message: string;
  error_code: 'payment_required';
  data: {
    intent_id: string;
    amount: string;
    currency: string;
    shortfall: string;
    payment_mode: string;
    wallet_shortfall: string;
    points_shortfall?: number;
    points_shortfall_amount?: string;
    postpaid_min_balance?: string;
    current_balance?: string;
    discount_applied?: DiscountDetails;
    resume_preferences?: {
      wallet_amount: string;
      points_to_use: number;
    };
    gateway: string;
    payment_method_name: string;
    payment_method_icon: string;
    gateway_url: string;
    redirect_url: string;
    redirect_method: 'POST' | 'GET';
    form_fields: Record<string, any>;
    payment_instructions: string;
    expires_at: string;
    status: string;
  };
}
```

### Error Response Schema

```typescript
interface ErrorResponse {
  success: false;
  message: string;
  error_code: string;
  context?: Record<string, any>;
}
```

---

## Summary Tables

### Payment Mode Support

| Mode | PREPAID | POSTPAID | Gateway Fallback |
|------|---------|----------|------------------|
| `wallet` | ✅ | ✅ | Wallet top-up |
| `points` | ✅ | ❌ | Wallet top-up (points can't be bought) |
| `wallet_points` | ✅ | ❌ | Wallet top-up (preserve or clear split) |
| `direct` | ✅ | ✅ | Always gateway |

### Response Type Matrix

| Scenario | HTTP | success | error_code | Has data |
|----------|------|---------|------------|----------|
| Rental started | 201 | `true` | - | ✅ Rental details |
| Payment required | 402 | `false` | `payment_required` | ✅ Intent details |
| Validation error | 400 | `false` | Specific code | ✅ Error context |
| Not found | 404 | `false` | Specific code | ✅ Error context |
| Server error | 500 | `false` | `internal_error` | ❌ |

### Payment Required Fields

| Field | PREPAID | POSTPAID | Always Present |
|-------|---------|----------|----------------|
| `intent_id` | ✅ | ✅ | ✅ |
| `amount` | ✅ | ✅ | ✅ |
| `shortfall` | ✅ | ✅ | ✅ |
| `wallet_shortfall` | ✅ | ✅ | ✅ |
| `points_shortfall` | ✅ | ❌ | ❌ |
| `postpaid_min_balance` | ❌ | ✅ | ❌ |
| `discount_applied` | ✅ | ❌ | ❌ |
| `resume_preferences` | ✅ | ❌ | ❌ |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-13 | System | Complete redesign: removed nested error object, fixed success flags, added comprehensive scenarios |
| 1.0 | 2026-02-11 | System | Initial draft |

---

**END OF SPECIFICATION**

