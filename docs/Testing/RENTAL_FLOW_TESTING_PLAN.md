# Rental Flow Testing Plan - Postpaid Focus

**Date:** 2026-02-22
**Priority:** Postpaid rentals (Prepaid working as expected)

---

## Current Issues Identified

1. **After Pay Due:**
   - Active rental GET not showing accurate values
   - Rental history GET not showing accurate values
   - Old values about history (how much, what) cannot be explained

2. **Need to Track:**
   - All DB table changes
   - Deductions from wallet/points
   - Refunds
   - Complete data flow verification

---

## Database Tables to Monitor

### Core Tables
1. **rentals** - Main rental record
2. **payments** - Payment transactions
3. **wallet_transactions** - Wallet deductions/refunds
4. **points_transactions** - Points usage/awards
5. **power_banks** - Powerbank status
6. **station_slots** - Slot availability
7. **late_fee_charges** - Overdue charges (if exists)

---

## Test Scenarios - Postpaid Rentals

### Scenario 1: Normal Postpaid Rental (On-Time Return)
**Steps:**
1. Start postpaid rental
2. Check DB state (rental, wallet, points)
3. Return on time (before due_at)
4. Verify payment deduction
5. Verify refund (if any)
6. Check rental history

**Expected:**
- No upfront payment
- Payment deducted on return
- Accurate history display

---

### Scenario 2: Postpaid Rental with Overdue (Late Return)
**Steps:**
1. Start postpaid rental
2. Simulate time passing (rental becomes overdue)
3. Check overdue calculation
4. Return late
5. Verify payment + late fee deduction
6. Check rental history

**Expected:**
- Base package price + late fee charged
- Accurate overdue amount calculation
- History shows breakdown

---

### Scenario 3: Postpaid Rental - Pay Due Before Return
**Steps:**
1. Start postpaid rental
2. Rental becomes overdue
3. User pays due amount via API
4. Check DB state after payment
5. Return powerbank
6. Verify no double charging
7. Check rental history

**Expected:**
- Due payment recorded correctly
- Return doesn't charge again
- History shows payment timeline

---

### Scenario 4: Postpaid Rental - Insufficient Balance on Return
**Steps:**
1. Start postpaid rental
2. Reduce user wallet balance
3. Attempt return
4. Check what happens

**Expected:**
- System handles insufficient balance
- Rental marked appropriately
- User notified

---

### Scenario 5: Postpaid Rental - Cancel Before Return
**Steps:**
1. Start postpaid rental
2. User cancels rental
3. Check cancellation logic
4. Verify charges/refunds

**Expected:**
- Cancellation fee (if applicable)
- Proper status updates

---

## API Endpoints to Test

### 1. Start Rental
```
POST /api/rentals/start
```

### 2. Get Active Rental
```
GET /api/rentals/active
```

### 3. Pay Due
```
POST /api/rentals/{rental_code}/pay-due
```

### 4. Return (IoT Trigger)
```
POST /api/iot/stations/sync
```

### 5. Get Rental History
```
GET /api/rentals/history
```

### 6. Get Rental Details
```
GET /api/rentals/{rental_code}
```

### 7. Cancel Rental
```
POST /api/rentals/{rental_code}/cancel
```

---

## Testing Approach

### Phase 1: Setup
1. Identify test user with sufficient balance
2. Find available station with powerbank
3. Get postpaid package details
4. Document initial state

### Phase 2: Execute Each Scenario
For each scenario:
1. **Before:** Capture DB state
2. **Execute:** Run API calls via curl
3. **After:** Capture DB state
4. **Compare:** Verify changes
5. **Document:** Record findings

### Phase 3: Verify Business Logic
- Payment calculations correct
- Refunds processed properly
- Status transitions valid
- History accurate

---

## SQL Queries for Verification

### Check Rental State
```sql
SELECT id, rental_code, status, payment_status,
       amount_paid, overdue_amount,
       started_at, ended_at, due_at
FROM rentals
WHERE rental_code = '<CODE>';
```

### Check Payments
```sql
SELECT id, payment_type, amount, status, created_at
FROM payments
WHERE rental_id = '<RENTAL_ID>'
ORDER BY created_at DESC;
```

### Check Wallet Transactions
```sql
SELECT id, transaction_type, amount, balance_after, created_at
FROM wallet_transactions
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC
LIMIT 10;
```

### Check Points Transactions
```sql
SELECT id, transaction_type, points, balance_after, created_at
FROM points_transactions
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Success Criteria

✅ All payment calculations accurate
✅ No double charging
✅ Refunds processed correctly
✅ History displays accurate information
✅ Status transitions logical
✅ Overdue calculations correct
✅ Pay due functionality works properly

---

## Next Steps

1. Start with Scenario 1 (Normal postpaid)
2. Document all findings
3. Fix issues found
4. Move to next scenario
5. Repeat until all scenarios pass

