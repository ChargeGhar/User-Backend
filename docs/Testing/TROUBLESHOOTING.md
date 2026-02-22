# Troubleshooting Guide for Rental Testing

**Last Updated:** 2026-02-22

## Table of Contents
1. [Environment Issues](#environment-issues)
2. [API Issues](#api-issues)
3. [Database Issues](#database-issues)
4. [Payment Issues](#payment-issues)
5. [Data Integrity Issues](#data-integrity-issues)
6. [Script Issues](#script-issues)

---

## Environment Issues

### Docker Containers Not Running

**Symptom:** `docker ps` shows no containers or missing containers

**Solution:**
```bash
# Check Docker daemon
docker info

# Start containers
cd E:\Companies\DEVALAYA\Deva_ChargeGhar\ChargeGhar
docker-compose up -d

# Verify all containers are running
docker ps

# Expected containers:
# - cg-api-local
# - cg-db-local
# - cg-celery-local
# - cg-redis-local
# - cg-rabbitmq-local
# - cg-pgbouncer-local
```

### Container Keeps Restarting

**Symptom:** Container status shows "Restarting"

**Solution:**
```bash
# Check logs for errors
docker logs cg-api-local

# Common issues:
# 1. Database connection failed
# 2. Missing environment variables
# 3. Port already in use

# Restart specific container
docker restart cg-api-local

# If persistent, rebuild
docker-compose down
docker-compose up -d --build
```

### Cannot Connect to Database

**Symptom:** `psql: could not connect to server`

**Solution:**
```bash
# Check if database container is running
docker ps | grep cg-db-local

# Check database logs
docker logs cg-db-local

# Try connecting with explicit host
docker exec -it cg-db-local psql -U postgres -d chargeGhar -h localhost

# Reset database connection
docker restart cg-db-local
docker restart cg-pgbouncer-local
```

### Port Already in Use

**Symptom:** `Error: bind: address already in use`

**Solution:**
```bash
# Find process using port 8010
netstat -ano | findstr :8010  # Windows
lsof -i :8010                 # Linux/Mac

# Kill the process or change port in docker-compose.yml
```

---

## API Issues

### 401 Unauthorized

**Symptom:** API returns `{"detail": "Authentication credentials were not provided"}`

**Solution:**
```bash
# Verify token is set
echo $TOKEN

# If empty, login again
curl -X 'POST' \
  'http://localhost:8010/api/admin/login' \
  -H 'Content-Type: multipart/form-data' \
  -F 'email=janak@powerbank.com' \
  -F 'password=5060'

# Set token
export TOKEN="your_token_here"

# Verify token works
curl -X 'GET' \
  'http://localhost:8010/api/auth/me' \
  -H "Authorization: Bearer $TOKEN"
```

### 403 Forbidden

**Symptom:** API returns `{"detail": "You do not have permission to perform this action"}`

**Solution:**
```bash
# Check user role
curl -X 'GET' \
  'http://localhost:8010/api/auth/me' \
  -H "Authorization: Bearer $TOKEN" | jq '.data.role'

# Should be "super_admin" or "admin"

# If not, use admin login endpoint instead of user login
```

### 404 Not Found

**Symptom:** API returns `{"detail": "Not found"}`

**Solution:**
```bash
# Verify endpoint URL
# Correct: /api/rentals/active
# Wrong: /api/rental/active (missing 's')

# Check API documentation
# http://localhost:8010/api/docs

# Verify resource exists
# For rental: Check rental_id is correct UUID
# For station: Check station_sn exists
```

### 500 Internal Server Error

**Symptom:** API returns `{"detail": "Internal server error"}`

**Solution:**
```bash
# Check API logs immediately
docker logs --tail 100 cg-api-local

# Common causes:
# 1. Database connection lost
# 2. Missing required field
# 3. Data type mismatch
# 4. Null reference error

# Check Celery logs if async task related
docker logs --tail 100 cg-celery-local

# Restart API if needed
docker restart cg-api-local
```

### Connection Refused

**Symptom:** `curl: (7) Failed to connect to localhost port 8010`

**Solution:**
```bash
# Check if API container is running
docker ps | grep cg-api-local

# Check if port is exposed
docker port cg-api-local

# Should show: 80/tcp -> 0.0.0.0:8010

# Try with explicit IP
curl http://127.0.0.1:8010/api/auth/me

# Check firewall settings
```

---

## Database Issues

### No Available Powerbanks

**Symptom:** API returns `"No available powerbanks at this station"`

**Solution:**
```sql
-- Check powerbank availability
SELECT
    s.station_name,
    s.serial_number,
    COUNT(CASE WHEN pb.status = 'AVAILABLE' THEN 1 END) as available,
    COUNT(CASE WHEN pb.status = 'RENTED' THEN 1 END) as rented,
    COUNT(CASE WHEN pb.status = 'CHARGING' THEN 1 END) as charging,
    COUNT(pb.id) as total
FROM stations s
LEFT JOIN power_banks pb ON pb.current_station_id = s.id
WHERE s.status = 'ONLINE'
GROUP BY s.id, s.station_name, s.serial_number;

-- If no available powerbanks, free one up
UPDATE power_banks
SET status = 'AVAILABLE',
    current_rental_id = NULL
WHERE id = (
    SELECT id FROM power_banks
    WHERE status = 'RENTED'
    LIMIT 1
);
```

### Rental Already Active

**Symptom:** API returns `"User already has an active rental"`

**Solution:**
```sql
-- Find active rental
SELECT rental_code, status, started_at, due_at
FROM rentals
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND status IN ('ACTIVE', 'OVERDUE');

-- Option 1: Complete the rental properly
-- Use IoT return script: python tests/OLD/test_iot_return.py RENTAL_CODE

-- Option 2: Force complete (testing only!)
UPDATE rentals
SET status = 'COMPLETED',
    ended_at = NOW(),
    payment_status = 'PAID'
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND status IN ('ACTIVE', 'OVERDUE');

-- Also free up the powerbank
UPDATE power_banks
SET status = 'AVAILABLE',
    current_rental_id = NULL
WHERE current_rental_id IN (
    SELECT id FROM rentals
    WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
);
```

### Insufficient Balance

**Symptom:** API returns `"Insufficient balance"` or `"payment_required"`

**Solution:**
```bash
# Check current balance
docker exec -it cg-db-local psql -U postgres -d chargeGhar -c "
SELECT
    u.email,
    w.balance as wallet,
    p.current_points as points
FROM users u
LEFT JOIN wallets w ON w.user_id = u.id
LEFT JOIN points p ON p.user_id = u.id
WHERE u.email = 'janak@powerbank.com';
"

# Add wallet balance
docker exec -it cg-api-local python manage.py shell <<EOF
from api.user.auth.models import User
from decimal import Decimal

user = User.objects.get(email='janak@powerbank.com')
user.wallet.balance += Decimal('1000.00')
user.wallet.save()
print(f"New balance: {user.wallet.balance}")
EOF

# Add points
docker exec -it cg-api-local python manage.py shell <<EOF
from api.user.auth.models import User

user = User.objects.get(email='janak@powerbank.com')
user.points.current_points += 1000
user.points.lifetime_earned += 1000
user.points.save()
print(f"New points: {user.points.current_points}")
EOF
```

### Transaction Not Created

**Symptom:** Expected transaction missing from database

**Solution:**
```sql
-- Check if transaction exists
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.status,
    t.created_at,
    r.rental_code
FROM transactions t
LEFT JOIN rentals r ON t.related_rental_id = r.id
WHERE t.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
ORDER BY t.created_at DESC
LIMIT 10;

-- For postpaid, transaction should only exist AFTER return
-- Check rental status
SELECT rental_code, status, payment_status, ended_at
FROM rentals
WHERE rental_code = 'YOUR_RENTAL_CODE';

-- If rental is COMPLETED but no transaction:
-- 1. Check if auto-collection failed (insufficient balance)
-- 2. Check Celery logs for errors
-- 3. Manually trigger payment via pay-due endpoint
```

### Data Mismatch

**Symptom:** Database values don't match API responses

**Solution:**
```sql
-- Compare rental data
SELECT
    rental_code,
    status,
    payment_status,
    amount_paid,
    overdue_amount,
    updated_at
FROM rentals
WHERE rental_code = 'YOUR_RENTAL_CODE';

-- Check if there's a pending update
-- Refresh the API call and compare again

-- Check for race conditions
-- Look for multiple transactions at same timestamp
SELECT * FROM transactions
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC;
```

---

## Payment Issues

### Auto-Collection Failed

**Symptom:** Rental completed but payment_status is PENDING

**Solution:**
```bash
# Check why auto-collection failed
docker logs --tail 50 cg-api-local | grep -i "auto-collect"

# Common reasons:
# 1. Insufficient balance
# 2. Payment calculation error
# 3. Transaction creation failed

# Verify balance was sufficient
docker exec -it cg-db-local psql -U postgres -d chargeGhar -c "
SELECT
    w.balance,
    (SELECT amount_paid + overdue_amount FROM rentals WHERE rental_code = 'YOUR_CODE') as required
FROM wallets w
WHERE w.user_id = (SELECT user_id FROM rentals WHERE rental_code = 'YOUR_CODE');
"

# Manually trigger payment
curl -X 'POST' \
  "http://localhost:8010/api/rentals/RENTAL_ID/pay-due" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"payment_mode": "wallet_points"}'
```

### Late Fee Calculation Wrong

**Symptom:** Overdue amount doesn't match expected calculation

**Solution:**
```sql
-- Check late fee configuration
SELECT
    name,
    grace_period_minutes,
    initial_rate_multiplier,
    escalation_rate_multiplier,
    escalation_threshold_minutes,
    max_late_fee_cap,
    is_active
FROM late_fee_configurations
WHERE is_active = true
ORDER BY effective_from DESC
LIMIT 1;

-- Calculate expected late fee manually
SELECT
    r.rental_code,
    r.due_at,
    r.ended_at,
    EXTRACT(EPOCH FROM (r.ended_at - r.due_at))/60 as overdue_minutes,
    rp.price / rp.duration_minutes as rate_per_minute,
    r.overdue_amount as actual_late_fee
FROM rentals r
JOIN rental_packages rp ON r.package_id = rp.id
WHERE r.rental_code = 'YOUR_CODE';

-- Compare with expected calculation
-- Late fee = overdue_minutes * rate_per_minute * multiplier
```

### Payment Breakdown Mismatch

**Symptom:** Wallet/points deduction doesn't match transaction amount

**Solution:**
```sql
-- Check transaction details
SELECT
    t.transaction_id,
    t.amount as transaction_amount,
    t.payment_method_type,
    t.gateway_response
FROM transactions t
WHERE t.related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'YOUR_CODE');

-- Check wallet transaction
SELECT
    wt.amount as wallet_deducted,
    wt.balance_after
FROM wallet_transactions wt
WHERE wt.transaction_id = (
    SELECT id FROM transactions
    WHERE related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'YOUR_CODE')
);

-- Check point transaction
SELECT
    pt.points as points_deducted,
    pt.points * 0.1 as points_amount_npr
FROM point_transactions pt
WHERE pt.description LIKE '%YOUR_CODE%'
  AND pt.transaction_type = 'RENTAL_PAYMENT';

-- Verify: transaction_amount = wallet_deducted + points_amount_npr
```

---

## Data Integrity Issues

### Orphaned Transactions

**Symptom:** Transactions exist without corresponding wallet/point deductions

**Solution:**
```sql
-- Find orphaned transactions
SELECT
    t.transaction_id,
    t.transaction_type,
    t.amount,
    t.payment_method_type,
    r.rental_code,
    CASE
        WHEN t.payment_method_type IN ('WALLET', 'COMBINATION')
             AND NOT EXISTS (SELECT 1 FROM wallet_transactions wt WHERE wt.transaction_id = t.id)
        THEN 'MISSING: Wallet transaction'
        WHEN t.payment_method_type IN ('POINTS', 'COMBINATION')
             AND NOT EXISTS (SELECT 1 FROM point_transactions pt WHERE pt.description LIKE '%' || r.rental_code || '%')
        THEN 'MISSING: Point transaction'
        ELSE 'OK'
    END as status
FROM transactions t
LEFT JOIN rentals r ON t.related_rental_id = r.id
WHERE t.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND t.status = 'SUCCESS'
ORDER BY t.created_at DESC;

-- If found, investigate logs and potentially recreate missing records
```

### Balance Mismatch

**Symptom:** Wallet balance doesn't match sum of transactions

**Solution:**
```sql
-- Calculate expected balance
WITH transaction_sum AS (
    SELECT
        user_id,
        SUM(CASE WHEN transaction_type = 'CREDIT' THEN amount ELSE -amount END) as calculated_balance
    FROM wallet_transactions
    WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
    GROUP BY user_id
)
SELECT
    w.balance as current_balance,
    ts.calculated_balance,
    w.balance - ts.calculated_balance as difference
FROM wallets w
JOIN transaction_sum ts ON ts.user_id = w.user_id
WHERE w.user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com');

-- If mismatch found, review wallet_transactions for errors
-- May need to recalculate balance
```

### Rental Status Inconsistency

**Symptom:** Rental status doesn't match actual state

**Solution:**
```sql
-- Find inconsistent rentals
SELECT
    rental_code,
    status,
    payment_status,
    started_at,
    ended_at,
    due_at,
    amount_paid,
    overdue_amount,
    CASE
        WHEN status = 'ACTIVE' AND ended_at IS NOT NULL THEN 'ERROR: Active but has end time'
        WHEN status = 'COMPLETED' AND ended_at IS NULL THEN 'ERROR: Completed but no end time'
        WHEN payment_status = 'PAID' AND overdue_amount > 0 THEN 'ERROR: Paid but has overdue'
        WHEN status = 'COMPLETED' AND payment_status = 'PENDING' AND overdue_amount = 0 THEN 'ERROR: Pending but no overdue'
        ELSE 'OK'
    END as issue
FROM rentals
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND status IN ('ACTIVE', 'COMPLETED', 'OVERDUE')
ORDER BY created_at DESC;

-- Fix inconsistencies based on actual state
```

---

## Script Issues

### quick_test.sh: jq Not Found

**Symptom:** `jq: command not found`

**Solution:**
```bash
# Install jq
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y jq

# macOS
brew install jq

# Windows (Git Bash)
# Download from https://stedolan.github.io/jq/download/
# Place jq.exe in C:\Program Files\Git\usr\bin\
```

### quick_test.sh: Permission Denied

**Symptom:** `bash: ./quick_test.sh: Permission denied`

**Solution:**
```bash
# Make script executable
chmod +x docs/Testing/quick_test.sh

# Or run with bash
bash docs/Testing/quick_test.sh postpaid
```

### IoT Return Script Fails

**Symptom:** `python tests/OLD/test_iot_return.py` fails

**Solution:**
```bash
# Check Python environment
python --version

# Should be Python 3.x

# Check if Django is accessible
docker exec -it cg-api-local python manage.py shell -c "print('OK')"

# Run script inside container instead
docker exec -it cg-api-local python tests/OLD/test_iot_return.py RENTAL_CODE

# Or use Django shell directly
docker exec -it cg-api-local python manage.py shell
>>> from api.user.rentals.models import Rental
>>> rental = Rental.objects.get(rental_code='YOUR_CODE')
>>> # Manually trigger return logic
```

### Script Hangs

**Symptom:** Script runs but never completes

**Solution:**
```bash
# Check if waiting for user input
# Press Ctrl+C to cancel

# Check if API is responding
curl -X 'GET' 'http://localhost:8010/api/auth/me' -H "Authorization: Bearer $TOKEN"

# Check if database is locked
docker exec -it cg-db-local psql -U postgres -d chargeGhar -c "
SELECT pid, state, query
FROM pg_stat_activity
WHERE state = 'active';
"

# Kill long-running queries if needed
-- SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <pid>;
```

---

## General Debugging Tips

### Enable Verbose Logging

```bash
# API logs with more detail
docker logs -f cg-api-local --tail 100

# Database query logs
docker exec -it cg-db-local psql -U postgres -d chargeGhar -c "
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();
"

# Then check logs
docker logs -f cg-db-local | grep -i "statement"
```

### Reset Test Environment

```bash
# Complete reset (WARNING: Deletes all data!)
docker-compose down -v
docker-compose up -d

# Wait for services to start
sleep 10

# Run migrations
docker exec -it cg-api-local python manage.py migrate

# Create superuser
docker exec -it cg-api-local python manage.py createsuperuser

# Load test data if available
docker exec -it cg-api-local python manage.py loaddata fixtures/test_data.json
```

### Capture Full Request/Response

```bash
# Use curl with verbose output
curl -v -X 'POST' \
  'http://localhost:8010/api/rentals/start' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"station_sn": "STATION001", "package_id": "UUID"}' \
  2>&1 | tee request_log.txt

# Save response to file
curl -X 'GET' \
  'http://localhost:8010/api/rentals/active' \
  -H "Authorization: Bearer $TOKEN" \
  -o response.json

# Pretty print JSON
cat response.json | jq '.'
```

### Check System Resources

```bash
# Check Docker resource usage
docker stats

# Check disk space
df -h

# Check memory
free -h  # Linux
vm_stat  # macOS

# If resources low, restart Docker or increase limits
```

---

## Getting Help

If issues persist after trying these solutions:

1. **Collect Information:**
   - Error message (exact text)
   - API request (full curl command)
   - API response (full JSON)
   - Database state (query results)
   - Logs (relevant excerpts)
   - Steps to reproduce

2. **Check Documentation:**
   - API docs: http://localhost:8010/api/docs
   - Testing docs: `docs/Testing/README.md`
   - Code: `api/user/rentals/`

3. **Review Logs:**
   - API: `docker logs cg-api-local`
   - Celery: `docker logs cg-celery-local`
   - Database: `docker logs cg-db-local`

4. **Test in Isolation:**
   - Test single endpoint
   - Use minimal data
   - Check each step

5. **Document the Issue:**
   - Use TEST_RESULTS_TEMPLATE.md
   - Include all collected information
   - Note what was tried

---

**Last Resort:** Reset everything and start fresh with a clean environment.
