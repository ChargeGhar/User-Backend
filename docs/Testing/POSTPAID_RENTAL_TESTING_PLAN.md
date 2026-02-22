# Postpaid Rental Testing Plan
**Date:** 2026-02-22
**Focus:** Complete postpaid rental flow testing with database verification

## Overview
This document outlines the systematic testing approach for postpaid rentals, including all scenarios, database table tracking, and API endpoint verification.

## Test Environment
- **Base URL:** http://localhost:8010
- **Admin Token:** (from admin login)
- **Test User:** Create/use existing user with sufficient balance

## Database Tables to Monitor

### Core Tables
1. **rentals** - Rental records
   - `status`, `payment_status`, `amount_paid`, `overdue_amount`
   - `started_at`, `ended_at`, `due_at`
   - `is_returned_on_time`, `package_id`

2. **transactions** - All financial transactions
   - `transaction_type` (RENTAL, RENTAL_DUE)
   - `amount`, `status`, `payment_method_type`
   - `related_rental_id`

3. **wallets** - User wallet balance
   - `balance` (before/after operations)

4. **wallet_transactions** - Wallet deductions/credits
   - `transaction_type`, `amount`, `balance_after`

5. **points** - User points balance
   - `current_points`, `lifetime_earned`, `lifetime_spent`

6. **point_transactions** - Points usage history
   - `transaction_type`, `points`, `balance_after`

7. **rental_packages** - Package details
   - `payment_model` (POSTPAID/PREPAID)
   - `price`, `duration_minutes`

8. **revenue_distributions** - Revenue sharing (if applicable)
   - `transaction_id`, `rental_id`, `amounts`

---

## Test Scenarios

### Scenario 1: Normal Postpaid Rental (On-Time Return)

**Objective:** Test standard postpaid flow with timely return

#### Step 1: Get User Info & Balance
```bash
curl -X 'GET' \
  'http://localhost:8010/api/auth/me' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

**Verify:**
- Current wallet balance
- Current points balance

#### Step 2: Get Postpaid Packages
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/packages' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

**Verify:**
- Find package with `payment_model: "POSTPAID"`
- Note `package_id`, `price`, `duration_minutes`

#### Step 3: Start Postpaid Rental
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/start' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "station_sn": "STATION_SERIAL",
    "package_id": "POSTPAID_PACKAGE_UUID",
    "payment_mode": "wallet_points"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "...",
    "rental_code": "...",
    "status": "ACTIVE",
    "payment_status": "PENDING",
    "amount_paid": "0.00",
    "overdue_amount": "0.00"
  }
}
```

**Database Checks:**
```sql
-- Check rental record
SELECT id, rental_code, status, payment_status, amount_paid, overdue_amount,
       started_at, due_at, ended_at
FROM rentals
WHERE rental_code = 'RENTAL_CODE';

-- Check NO transaction created yet (postpaid)
SELECT * FROM transactions
WHERE related_rental_id = 'RENTAL_ID';

-- Wallet/Points should be UNCHANGED
SELECT balance FROM wallets WHERE user_id = 'USER_ID';
SELECT current_points FROM points WHERE user_id = 'USER_ID';
```

**Expected DB State:**
- Rental: `status=ACTIVE`, `payment_status=PENDING`, `amount_paid=0`
- Transactions: NONE (payment happens at return)
- Wallet/Points: UNCHANGED

#### Step 4: Get Active Rental
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/active' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

**Verify:**
- Shows active rental with PENDING payment
- `estimated_total_cost` shows projected cost
- `minutes_overdue: 0` (if on time)

#### Step 5: Simulate Return (On-Time)
Use the IoT return test script:
```bash
cd E:\Companies\DEVALAYA\Deva_ChargeGhar\ChargeGhar
python tests/OLD/test_iot_return.py RENTAL_CODE
```

**Expected Behavior:**
- Rental status → `COMPLETED`
- `amount_paid` calculated based on actual usage
- `overdue_amount = 0` (on-time)
- Auto-collection attempts payment from wallet/points

**Database Checks:**
```sql
-- Check rental updated
SELECT status, payment_status, amount_paid, overdue_amount,
       ended_at, is_returned_on_time
FROM rentals
WHERE rental_code = 'RENTAL_CODE';

-- Check transaction created
SELECT transaction_id, transaction_type, amount, status, payment_method_type
FROM transactions
WHERE related_rental_id = 'RENTAL_ID'
ORDER BY created_at DESC;

-- Check wallet deduction
SELECT transaction_type, amount, balance_after, description
FROM wallet_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC LIMIT 5;

-- Check points deduction (if used)
SELECT transaction_type, points, balance_after, description
FROM point_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC LIMIT 5;

-- Check points awarded for completion
SELECT transaction_type, points, description
FROM point_transactions
WHERE user_id = 'USER_ID'
  AND transaction_type IN ('RENTAL', 'ON_TIME_RETURN')
ORDER BY created_at DESC LIMIT 5;
```

**Expected DB State:**
- Rental: `status=COMPLETED`, `payment_status=PAID`, `amount_paid=[calculated]`, `is_returned_on_time=true`
- Transaction: `transaction_type=RENTAL_DUE`, `status=SUCCESS`, `amount=[calculated]`
- Wallet: Balance reduced by payment amount
- Points: Awarded for completion + on-time bonus

#### Step 6: Get Rental History
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/history' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

**Verify:**
- Completed rental appears in history
- Shows correct `amount_paid`, `overdue_amount=0`
- `is_returned_on_time: true`

---

### Scenario 2: Postpaid Rental with Late Return

**Objective:** Test postpaid with overdue charges

#### Steps 1-3: Same as Scenario 1
Start a postpaid rental normally.

#### Step 4: Manually Set Rental to Overdue (for testing)
```bash
# Access Django shell in container
docker exec -it cg-api-local bash
python manage.py shell

# In shell:
from api.user.rentals.models import Rental
from django.utils import timezone
from datetime import timedelta

rental = Rental.objects.get(rental_code='YOUR_RENTAL_CODE')
rental.due_at = timezone.now() - timedelta(hours=2)  # 2 hours overdue
rental.save()
exit()
```

#### Step 5: Check Active Rental (Overdue)
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/active' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

**Verify:**
- `status: "OVERDUE"`
- `current_overdue_amount` shows live late fee
- `estimated_total_cost` includes late fees

**Database Check:**
```sql
SELECT status, payment_status, overdue_amount, current_overdue_amount,
       due_at, started_at
FROM rentals
WHERE rental_code = 'RENTAL_CODE';
```

#### Step 6: Return Overdue Rental
```bash
python tests/OLD/test_iot_return.py RENTAL_CODE
```

**Expected Behavior:**
- Rental status → `COMPLETED`
- `amount_paid` = usage cost (postpaid calculation)
- `overdue_amount` = late fee calculated
- `payment_status = PENDING` (if insufficient balance)
- Auto-collection attempts payment

**Database Checks:**
```sql
-- Check rental with late fees
SELECT status, payment_status, amount_paid, overdue_amount,
       is_returned_on_time, ended_at
FROM rentals
WHERE rental_code = 'RENTAL_CODE';

-- Check if transaction created (if auto-collected)
SELECT transaction_id, transaction_type, amount, status
FROM transactions
WHERE related_rental_id = 'RENTAL_ID'
ORDER BY created_at DESC;
```

**Expected DB State (Sufficient Balance):**
- Rental: `status=COMPLETED`, `payment_status=PAID`, `overdue_amount=0`
- Transaction: Created with total amount (usage + late fee)
- Wallet/Points: Deducted

**Expected DB State (Insufficient Balance):**
- Rental: `status=COMPLETED`, `payment_status=PENDING`, `overdue_amount=[calculated]`
- Transaction: NONE (payment pending)
- Wallet/Points: UNCHANGED

#### Step 7: Pay Outstanding Due (if pending)
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/RENTAL_ID/pay-due' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "payment_mode": "wallet_points"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Rental dues paid successfully",
  "data": {
    "transaction_id": "...",
    "amount_paid": "...",
    "payment_status": "PAID",
    "rental_status": "COMPLETED"
  }
}
```

**Database Checks:**
```sql
-- Verify payment
SELECT status, payment_status, overdue_amount
FROM rentals
WHERE rental_code = 'RENTAL_CODE';

-- Check transaction
SELECT transaction_id, transaction_type, amount, status
FROM transactions
WHERE related_rental_id = 'RENTAL_ID'
ORDER BY created_at DESC;

-- Verify wallet/points deduction
SELECT balance FROM wallets WHERE user_id = 'USER_ID';
SELECT current_points FROM points WHERE user_id = 'USER_ID';
```

**Expected DB State:**
- Rental: `payment_status=PAID`, `overdue_amount=0`
- Transaction: `transaction_type=RENTAL_DUE`, `status=SUCCESS`
- Wallet/Points: Deducted

#### Step 8: Verify History Shows Correct Data
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/history' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

**Verify:**
- Shows completed rental with correct amounts
- `amount_paid` reflects usage cost
- Late fee information visible
- `is_returned_on_time: false`

---

### Scenario 3: Postpaid with Insufficient Balance

**Objective:** Test payment failure handling

#### Steps 1-3: Start Postpaid Rental
Same as Scenario 1

#### Step 4: Reduce User Balance
```bash
# Django shell
docker exec -it cg-api-local python manage.py shell

from api.user.auth.models import User
from decimal import Decimal

user = User.objects.get(email='test@example.com')
user.wallet.balance = Decimal('1.00')  # Very low balance
user.wallet.save()

user.points.current_points = 0  # No points
user.points.save()
exit()
```

#### Step 5: Return Rental
```bash
python tests/OLD/test_iot_return.py RENTAL_CODE
```

**Expected Behavior:**
- Rental marked `COMPLETED`
- `payment_status = PENDING` (auto-collection failed)
- User notified of payment required

**Database Checks:**
```sql
-- Rental should be completed but unpaid
SELECT status, payment_status, amount_paid, overdue_amount
FROM rentals
WHERE rental_code = 'RENTAL_CODE';

-- No successful transaction
SELECT * FROM transactions
WHERE related_rental_id = 'RENTAL_ID';

-- Balance unchanged
SELECT balance FROM wallets WHERE user_id = 'USER_ID';
```

#### Step 6: Attempt Pay Due (Insufficient)
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/RENTAL_ID/pay-due' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "payment_mode": "wallet_points"
  }'
```

**Expected Response (402):**
```json
{
  "success": false,
  "message": "Payment required to settle rental dues",
  "error_code": "payment_required",
  "data": {
    "shortfall": "...",
    "payment_intent": {...}
  }
}
```

#### Step 7: Top Up Wallet
```bash
# Add balance via admin or payment gateway
# Then retry pay-due
```

---

### Scenario 4: Postpaid Rental Cancellation

**Objective:** Test cancellation before return

#### Step 1-3: Start Postpaid Rental
Same as Scenario 1

#### Step 4: Cancel Active Rental
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/RENTAL_ID/cancel' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "reason": "Testing cancellation"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Rental cancelled successfully",
  "data": {
    "rental_id": "...",
    "status": "CANCELLED",
    "refund_amount": "0.00"
  }
}
```

**Database Checks:**
```sql
-- Check rental cancelled
SELECT status, payment_status, amount_paid, ended_at
FROM rentals
WHERE rental_code = 'RENTAL_CODE';

-- Check powerbank returned to station
SELECT status, current_station_id, current_rental_id
FROM power_banks
WHERE id = 'POWERBANK_ID';
```

**Expected DB State:**
- Rental: `status=CANCELLED`, `payment_status=PAID` (nothing to pay)
- Powerbank: Returned to station, available

---

## Complete Database Verification Queries

### After Each Test, Run These Queries:

```sql
-- 1. Rental Summary
SELECT
    r.rental_code,
    r.status,
    r.payment_status,
    r.amount_paid,
    r.overdue_amount,
    r.is_returned_on_time,
    rp.payment_model,
    rp.price as package_price,
    rp.duration_minutes,
    r.started_at,
    r.ended_at,
    r.due_at
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
WHERE r.user_id = 'USER_ID'
ORDER BY r.created_at DESC
LIMIT 10;

-- 2. Transaction History
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.status,
    t.payment_method_type,
    r.rental_code,
    t.created_at
FROM transactions t
LEFT JOIN rentals r ON t.related_rental_id = r.id
WHERE t.user_id = 'USER_ID'
ORDER BY t.created_at DESC
LIMIT 10;

-- 3. Wallet Balance & Transactions
SELECT
    w.balance as current_balance,
    (SELECT COUNT(*) FROM wallet_transactions WHERE user_id = 'USER_ID') as total_transactions,
    (SELECT SUM(amount) FROM wallet_transactions WHERE user_id = 'USER_ID' AND transaction_type = 'DEBIT') as total_debits,
    (SELECT SUM(amount) FROM wallet_transactions WHERE user_id = 'USER_ID' AND transaction_type = 'CREDIT') as total_credits
FROM wallets w
WHERE w.user_id = 'USER_ID';

-- Recent wallet transactions
SELECT
    transaction_type,
    amount,
    balance_after,
    description,
    created_at
FROM wallet_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC
LIMIT 10;

-- 4. Points Balance & Transactions
SELECT
    p.current_points,
    p.lifetime_earned,
    p.lifetime_spent,
    (SELECT COUNT(*) FROM point_transactions WHERE user_id = 'USER_ID') as total_transactions
FROM points p
WHERE p.user_id = 'USER_ID';

-- Recent point transactions
SELECT
    transaction_type,
    points,
    balance_after,
    description,
    created_at
FROM point_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC
LIMIT 10;

-- 5. Revenue Distribution (if applicable)
SELECT
    rd.id,
    rd.transaction_id,
    rd.rental_id,
    rd.total_amount,
    rd.platform_amount,
    rd.vendor_amount,
    rd.status
FROM revenue_distributions rd
WHERE rd.rental_id IN (
    SELECT id FROM rentals WHERE user_id = 'USER_ID'
)
ORDER BY rd.created_at DESC
LIMIT 10;
```

---

## Testing Checklist

### For Each Scenario:
- [ ] Record initial wallet balance
- [ ] Record initial points balance
- [ ] Start rental and verify DB state
- [ ] Check active rental API response
- [ ] Perform action (return/cancel/pay-due)
- [ ] Verify final DB state
- [ ] Verify wallet/points deductions
- [ ] Verify transaction records
- [ ] Check rental history API
- [ ] Verify revenue distribution (if applicable)

### Key Validations:
- [ ] Postpaid rentals start with `amount_paid=0`, `payment_status=PENDING`
- [ ] No transaction created at rental start (postpaid)
- [ ] Usage cost calculated correctly at return
- [ ] Late fees calculated correctly for overdue returns
- [ ] Auto-collection works when balance sufficient
- [ ] Payment remains pending when balance insufficient
- [ ] Pay-due endpoint works correctly
- [ ] Wallet/points deducted accurately
- [ ] Transaction records match actual deductions
- [ ] Rental history shows accurate information
- [ ] Points awarded for completion and on-time return

---

## Known Issues to Track

### Issue 1: History API Accuracy After Pay-Due
**Description:** After paying due, rental history may not show accurate historical values about what was owed and when.

**Test:**
1. Create overdue rental
2. Pay due
3. Check history API
4. Verify it shows:
   - Original amount owed
   - Late fee amount
   - Payment date
   - Total paid

### Issue 2: Active Rental vs History Consistency
**Description:** Values shown in active rental GET vs history GET may differ.

**Test:**
1. Get active rental (with overdue)
2. Pay due
3. Get history
4. Compare values - should be consistent

---

## Next Steps

1. **Run Prepaid Tests First** (already working)
2. **Run All Postpaid Scenarios** (this document)
3. **Compare Prepaid vs Postpaid** behavior
4. **Document Any Discrepancies**
5. **Fix Issues Found**
6. **Re-test After Fixes**

---

## Notes
- Use Docker logs to monitor background processes: `docker logs -f cg-api-local`
- Check Celery logs for async tasks: `docker logs -f cg-celery-local`
- Database access: Connect to `cg-db-local` container
- All timestamps in UTC
- Amounts in NPR (Decimal with 2 decimal places)
