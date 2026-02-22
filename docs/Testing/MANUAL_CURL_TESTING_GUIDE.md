# Manual CURL Testing Guide - Rental Flow
**Date:** 2026-02-22
**Environment:** Local Docker (http://localhost:8010)

## Setup

### 1. Admin Login (Get Token)
```bash
curl -X 'POST' \
  'http://localhost:8010/api/admin/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'email=janak@powerbank.com' \
  -F 'password=5060'
```

**Save the access_token from response:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 2. Get User Info
```bash
curl -X 'GET' \
  'http://localhost:8010/api/auth/me' \
  -H "Authorization: Bearer $TOKEN"
```

**Note:** Save `user_id` for database queries.

---

## Step-by-Step Testing Flow

### STEP 1: Check Initial Balances

#### Get Wallet Balance
```bash
curl -X 'GET' \
  'http://localhost:8010/api/users/wallet' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "balance": "1000.00",
    "currency": "NPR"
  }
}
```

#### Get Points Balance
```bash
curl -X 'GET' \
  'http://localhost:8010/api/points/history' \
  -H "Authorization: Bearer $TOKEN"
```

**Record:**
- Initial Wallet: `_______ NPR`
- Initial Points: `_______ points`

---

### STEP 2: Get Available Packages

```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/packages' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "packages": [
      {
        "id": "uuid-here",
        "name": "1 Hour Postpaid",
        "payment_model": "POSTPAID",
        "price": "50.00",
        "duration_minutes": 60
      },
      {
        "id": "uuid-here",
        "name": "1 Hour Prepaid",
        "payment_model": "PREPAID",
        "price": "50.00",
        "duration_minutes": 60
      }
    ]
  }
}
```

**Record Package IDs:**
- Postpaid Package ID: `_______________________`
- Prepaid Package ID: `_______________________`

---

### STEP 3: Get Available Stations

```bash
curl -X 'GET' \
  'http://localhost:8010/api/stations' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "stations": [
      {
        "id": "uuid",
        "serial_number": "STATION001",
        "station_name": "Test Station",
        "status": "ONLINE",
        "available_powerbanks": 5
      }
    ]
  }
}
```

**Record:**
- Station Serial: `_______________________`

---

### STEP 4: Start Postpaid Rental

```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/start' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "station_sn": "STATION001",
    "package_id": "POSTPAID_PACKAGE_UUID",
    "payment_mode": "wallet_points"
  }'
```

**Expected Response (201):**
```json
{
  "success": true,
  "message": "Rental started successfully",
  "data": {
    "rental_id": "uuid",
    "rental_code": "ABCD1234",
    "status": "ACTIVE",
    "payment_status": "PENDING",
    "amount_paid": "0.00",
    "overdue_amount": "0.00",
    "due_at": "2026-02-22T13:40:00Z",
    "powerbank": {
      "serial_number": "PB001",
      "battery_level": 85
    }
  }
}
```

**Record:**
- Rental ID: `_______________________`
- Rental Code: `_______________________`
- Powerbank Serial: `_______________________`
- Due At: `_______________________`

**Verify in Database:**
```sql
-- Connect to database
docker exec -it cg-db-local psql -U postgres -d chargeGhar

-- Check rental
SELECT rental_code, status, payment_status, amount_paid, overdue_amount,
       started_at, due_at, ended_at
FROM rentals
WHERE rental_code = 'ABCD1234';

-- Expected: status=ACTIVE, payment_status=PENDING, amount_paid=0.00

-- Check NO transaction created yet
SELECT * FROM transactions
WHERE related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'ABCD1234');

-- Expected: No rows (postpaid - payment at return)

-- Check wallet unchanged
SELECT balance FROM wallets WHERE user_id = 'USER_ID';

-- Expected: Same as initial balance
```

---

### STEP 5: Get Active Rental

```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/active' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "rental_id": "uuid",
    "rental_code": "ABCD1234",
    "status": "ACTIVE",
    "payment_status": "PENDING",
    "amount_paid": "0.00",
    "overdue_amount": "0.00",
    "current_overdue_amount": "0.00",
    "estimated_total_cost": "0.00",
    "minutes_overdue": 0,
    "is_returned_on_time": false,
    "package": {
      "name": "1 Hour Postpaid",
      "payment_model": "POSTPAID",
      "price": "50.00"
    },
    "started_at": "2026-02-22T12:40:00Z",
    "due_at": "2026-02-22T13:40:00Z"
  }
}
```

**Verify:**
- ✓ Status is ACTIVE
- ✓ Payment status is PENDING
- ✓ Amount paid is 0.00
- ✓ No overdue amount yet

---

### STEP 6A: Test On-Time Return (Normal Flow)

#### Simulate Return via IoT Script
```bash
cd E:\Companies\DEVALAYA\Deva_ChargeGhar\ChargeGhar
python tests/OLD/test_iot_return.py ABCD1234
```

**Expected Output:**
```
================================================================================
  🚀 IoT RETURN FLOW TEST: ABCD1234
================================================================================

📦 Rental: ABCD1234
   User: janak@powerbank.com
   Package: 1 Hour Postpaid (NPR 50.00)
   Started: 2026-02-22 12:40
   Due: 2026-02-22 13:40
   ✅ On time

🏢 Returning to: Test Station
   Slot: #1

💰 User Balance:
   Wallet: NPR 1000.00
   Points: 100

🔄 Processing IoT return event...

✅ RETURN COMPLETE!

📊 Results:
   Status: COMPLETED
   Payment: PAID
   On Time: True
   Package: NPR 50.00
   Late Fee: NPR 0.00
   Total: NPR 50.00

🔋 Powerbank:
   Status: AVAILABLE
   Location: Test Station

✅ Test Complete!
```

**Verify in Database:**
```sql
-- Check rental completed
SELECT rental_code, status, payment_status, amount_paid, overdue_amount,
       is_returned_on_time, ended_at
FROM rentals
WHERE rental_code = 'ABCD1234';

-- Expected:
-- status = COMPLETED
-- payment_status = PAID (if auto-collected)
-- amount_paid = calculated usage cost (e.g., 50.00 for full hour)
-- overdue_amount = 0.00
-- is_returned_on_time = true

-- Check transaction created
SELECT transaction_id, transaction_type, amount, status, payment_method_type,
       created_at
FROM transactions
WHERE related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'ABCD1234')
ORDER BY created_at DESC;

-- Expected:
-- transaction_type = RENTAL_DUE
-- status = SUCCESS
-- amount = usage cost

-- Check wallet deduction
SELECT balance FROM wallets WHERE user_id = 'USER_ID';

-- Expected: Initial balance - usage cost

-- Check wallet transaction
SELECT transaction_type, amount, balance_after, description, created_at
FROM wallet_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC LIMIT 3;

-- Expected: DEBIT entry for rental payment

-- Check points awarded
SELECT transaction_type, points, description, created_at
FROM point_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC LIMIT 5;

-- Expected:
-- RENTAL transaction (completion bonus)
-- ON_TIME_RETURN transaction (on-time bonus)
```

**Calculate Expected Values:**
- Usage Duration: `_______ minutes`
- Usage Cost: `_______ NPR`
- Late Fee: `0.00 NPR`
- Total Paid: `_______ NPR`
- New Wallet Balance: `_______ NPR`
- Points Earned: `_______ points`

---

### STEP 6B: Test Late Return (Overdue Flow)

#### First, Make Rental Overdue
```bash
# Access Django shell
docker exec -it cg-api-local python manage.py shell

# Run this in shell:
from api.user.rentals.models import Rental
from django.utils import timezone
from datetime import timedelta

rental = Rental.objects.get(rental_code='ABCD1234')
rental.due_at = timezone.now() - timedelta(hours=2)  # 2 hours overdue
rental.save()
print(f"Rental {rental.rental_code} is now overdue by 2 hours")
exit()
```

#### Check Active Rental (Should Show Overdue)
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/active' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "rental_code": "ABCD1234",
    "status": "OVERDUE",
    "payment_status": "PENDING",
    "amount_paid": "0.00",
    "overdue_amount": "100.00",
    "current_overdue_amount": "100.00",
    "estimated_total_cost": "100.00",
    "minutes_overdue": 120,
    "is_returned_on_time": false
  }
}
```

**Verify:**
- ✓ Status changed to OVERDUE
- ✓ current_overdue_amount shows live late fee
- ✓ minutes_overdue shows 120

**Database Check:**
```sql
SELECT status, payment_status, overdue_amount, due_at
FROM rentals
WHERE rental_code = 'ABCD1234';

-- Expected: status may still be ACTIVE (updated on next API call)
```

#### Return Overdue Rental
```bash
python tests/OLD/test_iot_return.py ABCD1234
```

**Expected Output:**
```
⚠️  OVERDUE: 0 days, 2 hours

📊 Results:
   Status: COMPLETED
   Payment: PAID (or PENDING if insufficient balance)
   On Time: False
   Package: NPR 50.00
   Late Fee: NPR 100.00
   Total: NPR 150.00
```

**Verify in Database:**
```sql
-- Check rental with late fees
SELECT rental_code, status, payment_status, amount_paid, overdue_amount,
       is_returned_on_time, ended_at
FROM rentals
WHERE rental_code = 'ABCD1234';

-- If balance sufficient:
-- status = COMPLETED
-- payment_status = PAID
-- amount_paid = usage cost (50.00)
-- overdue_amount = 0.00 (paid and cleared)
-- is_returned_on_time = false

-- If balance insufficient:
-- status = COMPLETED
-- payment_status = PENDING
-- amount_paid = usage cost (50.00)
-- overdue_amount = late fee (100.00)
-- is_returned_on_time = false

-- Check transaction
SELECT transaction_id, transaction_type, amount, status
FROM transactions
WHERE related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'ABCD1234')
ORDER BY created_at DESC;

-- If paid: transaction_type = RENTAL_DUE, amount = 150.00, status = SUCCESS
-- If pending: No transaction yet
```

---

### STEP 7: Pay Outstanding Due (If Payment Pending)

#### Check if Payment Needed
```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/active' \
  -H "Authorization: Bearer $TOKEN"
```

If `payment_status: "PENDING"`, proceed with payment:

#### Pay Due
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/RENTAL_ID/pay-due' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "payment_mode": "wallet_points"
  }'
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Rental dues paid successfully",
  "data": {
    "transaction_id": "TXN123456",
    "rental_id": "uuid",
    "rental_code": "ABCD1234",
    "amount_paid": "150.00",
    "breakdown": {
      "wallet_amount": "100.00",
      "points_used": 500,
      "points_amount": "50.00"
    },
    "payment_status": "PAID",
    "rental_status": "COMPLETED",
    "account_unblocked": true
  }
}
```

**Expected Response (402 - Insufficient Balance):**
```json
{
  "success": false,
  "message": "Payment required to settle rental dues",
  "error_code": "payment_required",
  "data": {
    "shortfall": "50.00",
    "required_due": "150.00",
    "payment_intent": {
      "intent_id": "uuid",
      "amount": "50.00"
    },
    "payment_options": {
      "is_sufficient": false,
      "total_amount": "150.00",
      "available_wallet": "80.00",
      "available_points": 200
    }
  }
}
```

**Verify in Database:**
```sql
-- Check payment completed
SELECT status, payment_status, overdue_amount
FROM rentals
WHERE rental_code = 'ABCD1234';

-- Expected:
-- status = COMPLETED
-- payment_status = PAID
-- overdue_amount = 0.00

-- Check transaction
SELECT transaction_id, transaction_type, amount, status, payment_method_type
FROM transactions
WHERE related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'ABCD1234')
ORDER BY created_at DESC;

-- Expected: RENTAL_DUE transaction with SUCCESS status

-- Check wallet balance
SELECT balance FROM wallets WHERE user_id = 'USER_ID';

-- Expected: Reduced by payment amount

-- Check points balance
SELECT current_points FROM points WHERE user_id = 'USER_ID';

-- Expected: Reduced if points used
```

---

### STEP 8: Get Rental History

```bash
curl -X 'GET' \
  'http://localhost:8010/api/rentals/history' \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "rentals": [
      {
        "rental_id": "uuid",
        "rental_code": "ABCD1234",
        "status": "COMPLETED",
        "payment_status": "PAID",
        "amount_paid": "50.00",
        "overdue_amount": "0.00",
        "is_returned_on_time": false,
        "package": {
          "name": "1 Hour Postpaid",
          "payment_model": "POSTPAID",
          "price": "50.00"
        },
        "started_at": "2026-02-22T12:40:00Z",
        "ended_at": "2026-02-22T14:45:00Z",
        "due_at": "2026-02-22T13:40:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total_pages": 1,
      "total_count": 1
    }
  }
}
```

**Verify:**
- ✓ Rental appears in history
- ✓ Shows COMPLETED status
- ✓ Shows PAID payment status
- ✓ amount_paid reflects usage cost
- ✓ overdue_amount is 0 (after payment)
- ✓ is_returned_on_time shows false (was late)
- ✓ Timestamps are accurate

---

### STEP 9: Cancel Active Rental (Alternative Flow)

#### Start a New Rental First
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/start' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "station_sn": "STATION001",
    "package_id": "POSTPAID_PACKAGE_UUID",
    "payment_mode": "wallet_points"
  }'
```

**Record new rental_code:** `_______________________`

#### Cancel the Rental
```bash
curl -X 'POST' \
  'http://localhost:8010/api/rentals/RENTAL_ID/cancel' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "reason": "Testing cancellation flow"
  }'
```

**Expected Response (200):**
```json
{
  "success": true,
  "message": "Rental cancelled successfully",
  "data": {
    "rental_id": "uuid",
    "rental_code": "EFGH5678",
    "status": "CANCELLED",
    "payment_status": "PAID",
    "refund_amount": "0.00"
  }
}
```

**Verify in Database:**
```sql
-- Check cancellation
SELECT rental_code, status, payment_status, amount_paid, ended_at
FROM rentals
WHERE rental_code = 'EFGH5678';

-- Expected:
-- status = CANCELLED
-- payment_status = PAID (nothing to pay for postpaid cancellation)
-- amount_paid = 0.00

-- Check powerbank returned
SELECT status, current_station_id, current_rental_id
FROM power_banks
WHERE serial_number = 'POWERBANK_SERIAL';

-- Expected: status = AVAILABLE, current_rental_id = NULL
```

---

## Complete Database Verification Script

Save this as `verify_rental.sql`:

```sql
-- Set your rental code
\set rental_code 'ABCD1234'

-- 1. Rental Details
SELECT
    r.rental_code,
    r.status,
    r.payment_status,
    r.amount_paid,
    r.overdue_amount,
    r.is_returned_on_time,
    rp.name as package_name,
    rp.payment_model,
    rp.price as package_price,
    r.started_at,
    r.ended_at,
    r.due_at,
    EXTRACT(EPOCH FROM (r.ended_at - r.started_at))/60 as usage_minutes,
    EXTRACT(EPOCH FROM (r.ended_at - r.due_at))/60 as overdue_minutes
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
WHERE r.rental_code = :'rental_code';

-- 2. Transactions
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.status,
    t.payment_method_type,
    t.created_at
FROM transactions t
JOIN rentals r ON t.related_rental_id = r.id
WHERE r.rental_code = :'rental_code'
ORDER BY t.created_at;

-- 3. Wallet Transactions
SELECT
    wt.transaction_type,
    wt.amount,
    wt.balance_after,
    wt.description,
    wt.created_at
FROM wallet_transactions wt
JOIN rentals r ON wt.description LIKE '%' || r.rental_code || '%'
WHERE r.rental_code = :'rental_code'
ORDER BY wt.created_at;

-- 4. Point Transactions
SELECT
    pt.transaction_type,
    pt.points,
    pt.balance_after,
    pt.description,
    pt.created_at
FROM point_transactions pt
WHERE pt.description LIKE '%' || :'rental_code' || '%'
ORDER BY pt.created_at;

-- 5. Revenue Distribution
SELECT
    rd.total_amount,
    rd.platform_amount,
    rd.vendor_amount,
    rd.status,
    rd.created_at
FROM revenue_distributions rd
JOIN rentals r ON rd.rental_id = r.id
WHERE r.rental_code = :'rental_code';
```

**Run it:**
```bash
docker exec -it cg-db-local psql -U postgres -d chargeGhar -f verify_rental.sql
```

---

## Testing Checklist

### Before Each Test:
- [ ] Record initial wallet balance
- [ ] Record initial points balance
- [ ] Note current timestamp
- [ ] Clear any active rentals

### During Test:
- [ ] Verify API response status codes
- [ ] Check response data structure
- [ ] Verify amounts are correct
- [ ] Check timestamps are accurate

### After Each Test:
- [ ] Run database verification queries
- [ ] Verify wallet balance changed correctly
- [ ] Verify points balance changed correctly
- [ ] Check transaction records created
- [ ] Verify rental status updated
- [ ] Check powerbank status updated

### Key Validations:
- [ ] Postpaid starts with amount_paid=0
- [ ] No transaction at rental start
- [ ] Usage cost calculated at return
- [ ] Late fees calculated correctly
- [ ] Auto-collection works when sufficient balance
- [ ] Payment pending when insufficient balance
- [ ] Pay-due endpoint works
- [ ] History shows accurate data
- [ ] Points awarded correctly

---

## Common Issues & Troubleshooting

### Issue: "No available powerbanks"
**Solution:** Check station has available powerbanks
```sql
SELECT s.station_name, COUNT(pb.id) as available_count
FROM stations s
LEFT JOIN power_banks pb ON pb.current_station_id = s.id AND pb.status = 'AVAILABLE'
WHERE s.status = 'ONLINE'
GROUP BY s.id, s.station_name;
```

### Issue: "Insufficient balance"
**Solution:** Top up wallet or add points
```bash
# Via Django shell
docker exec -it cg-api-local python manage.py shell

from api.user.auth.models import User
from decimal import Decimal

user = User.objects.get(email='janak@powerbank.com')
user.wallet.balance += Decimal('1000.00')
user.wallet.save()
print(f"New balance: {user.wallet.balance}")
```

### Issue: "Rental already active"
**Solution:** Cancel or complete existing rental first
```sql
-- Find active rental
SELECT rental_code, status FROM rentals
WHERE user_id = 'USER_ID' AND status IN ('ACTIVE', 'OVERDUE');

-- Force complete it (for testing only)
UPDATE rentals
SET status = 'COMPLETED', ended_at = NOW()
WHERE rental_code = 'RENTAL_CODE';
```

### Issue: Transaction not created
**Check Celery logs:**
```bash
docker logs -f cg-celery-local
```

**Check API logs:**
```bash
docker logs -f cg-api-local
```

---

## Next Steps

1. Run through all scenarios systematically
2. Document any discrepancies found
3. Compare prepaid vs postpaid behavior
4. Test edge cases (exactly at due time, multiple extensions, etc.)
5. Verify revenue distribution calculations
6. Test with different payment modes (wallet only, points only, combination)
