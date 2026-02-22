# Postpaid Rental Testing - Live Session Results

**Date:** 2026-02-22
**Rental Code:** 6VF7ZO72
**Test User:** janak@powerbank.com (ID: 1)

---

## Test Setup

**Package:** Test Postpaid 1H
- ID: `75deede1-a812-4f22-be8a-9642821ed9e2`
- Payment Model: POSTPAID
- Price: NPR 100.00
- Duration: 60 minutes

**Station:** DUMMY-SN-d2ac3931
**PowerBank:** TEST-PB-001 (Battery: 95%)

---

## Step 1: Start Postpaid Rental ✅

### API Call
```bash
POST /api/rentals/start
{
  "station_sn": "DUMMY-SN-d2ac3931",
  "package_id": "75deede1-a812-4f22-be8a-9642821ed9e2",
  "powerbank_sn": "TEST-PB-002",
  "payment_mode": "wallet"
}
```

### Response
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_code": "6VF7ZO72",
    "status": "PENDING_POPUP",
    "payment_status": "PENDING",
    "pricing": {
      "actual_price": "100.00",
      "amount_paid": "0"
    },
    "payment": {
      "payment_model": "POSTPAID",
      "payment_mode": "wallet",
      "payment_status": "PENDING"
    }
  }
}
```

### Database State After Start

**Rental:**
- Code: 6VF7ZO72
- Status: PENDING_POPUP
- Payment Status: PENDING
- Amount Paid: NPR 0.00 ✅
- Overdue Amount: NPR 0.00
- Started: None (waiting for popup)
- Due: 2026-02-22 12:55:31 UTC

**User Balance:**
- Wallet: NPR 500.00 ✅ (Unchanged - no upfront payment)
- Points: 1094 ✅ (Unchanged)

### ✅ Verification
- No upfront payment deducted ✅
- Rental created with PENDING status ✅
- Payment status is PENDING ✅
- User balance unchanged ✅

---

## Next Steps

### Step 2: Simulate IoT Popup Confirmation
The rental is in `PENDING_POPUP` status, waiting for hardware to confirm the powerbank was dispensed.

**Need to:**
1. Simulate IoT popup event to move rental to ACTIVE
2. Check if `started_at` timestamp is set
3. Verify status changes to ACTIVE

### Step 3: Test Return Flow
Once rental is ACTIVE, we'll test the return process:
1. Simulate IoT return event
2. Check payment deduction (NPR 100.00 from wallet)
3. Verify rental status changes to COMPLETED
4. Check payment status changes to PAID
5. Verify wallet balance decreases by NPR 100.00

### Step 4: Test Overdue Scenario
Create another postpaid rental and:
1. Simulate time passing (rental becomes overdue)
2. Check overdue amount calculation
3. Test return with late fee
4. Verify total payment (base + late fee)

### Step 5: Test Pay Due Before Return
1. Create overdue postpaid rental
2. Call pay-due endpoint
3. Verify payment recorded
4. Return powerbank
5. Ensure no double charging

---

## Commands for Next Steps

### Simulate IoT Popup (Move to ACTIVE)
```bash
# Need to find the IoT sync endpoint or update rental status directly
```

### Check Active Rental
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8010/api/rentals/active
```

### Simulate Return
```bash
# Use test_iot_return.py script
python tests/OLD/test_iot_return.py 6VF7ZO72
```

### Check Rental History
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8010/api/rentals/history
```

---

## Issues to Investigate

1. **Active Rental API Response:**
   - API returned `success: true` with message "Active rental retrieved" even when no active rental exists
   - Should return `success: false` or empty data when no active rental

2. **Payment Model Import:**
   - Cannot import `Payment` from `api.user.payments.models`
   - Need to check correct model name/location

---

## Status: IN PROGRESS

Rental successfully created in POSTPAID mode with no upfront payment. Ready to test popup confirmation and return flow.

