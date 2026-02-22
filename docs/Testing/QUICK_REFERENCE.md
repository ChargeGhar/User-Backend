# Testing Quick Reference
**Last Updated:** 2026-02-22

## Quick Commands

### Start Testing (Automated)
```bash
cd docs/Testing

# Make script executable
chmod +x quick_test.sh

# Run prepaid test
./quick_test.sh prepaid

# Run postpaid test (on-time)
./quick_test.sh postpaid

# Run postpaid test (late return)
./quick_test.sh postpaid-late

# Run cancellation test
./quick_test.sh cancel
```

### Manual Testing (Step by Step)
```bash
# 1. Login and get token
curl -X 'POST' 'http://localhost:8010/api/admin/login' \
  -H 'Content-Type: multipart/form-data' \
  -F 'email=janak@powerbank.com' \
  -F 'password=5060'

# Save token
export TOKEN="your_token_here"

# 2. Get packages
curl -X 'GET' 'http://localhost:8010/api/rentals/packages' \
  -H "Authorization: Bearer $TOKEN"

# 3. Start rental
curl -X 'POST' 'http://localhost:8010/api/rentals/start' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "station_sn": "STATION_SN",
    "package_id": "PACKAGE_UUID",
    "payment_mode": "wallet_points"
  }'

# 4. Return rental
python tests/OLD/test_iot_return.py RENTAL_CODE
```

### Database Queries
```bash
# Connect to database
docker exec -it cg-db-local psql -U postgres -d chargeGhar

# Quick rental check
SELECT rental_code, status, payment_status, amount_paid, overdue_amount
FROM rentals
WHERE rental_code = 'YOUR_CODE';

# Check transactions
SELECT transaction_id, transaction_type, amount, status
FROM transactions
WHERE related_rental_id = (SELECT id FROM rentals WHERE rental_code = 'YOUR_CODE');

# Check wallet balance
SELECT balance FROM wallets
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com');
```

## File Reference

| File | Purpose |
|------|---------|
| `TESTING_SUMMARY.md` | Overview and action plan |
| `MANUAL_CURL_TESTING_GUIDE.md` | Step-by-step CURL commands |
| `POSTPAID_RENTAL_TESTING_PLAN.md` | Detailed postpaid scenarios |
| `DATABASE_QUERIES.sql` | All verification queries |
| `quick_test.sh` | Automated test script |
| `QUICK_REFERENCE.md` | This file |

## Common Scenarios

### Scenario 1: Test Postpaid Normal Flow
```bash
./quick_test.sh postpaid
```
**Verifies:**
- Rental starts with amount_paid=0
- No transaction at start
- Usage cost calculated at return
- Auto-collection works
- History shows correct data

### Scenario 2: Test Postpaid Late Return
```bash
./quick_test.sh postpaid-late
```
**Verifies:**
- Late fee calculation
- Overdue status handling
- Pay-due endpoint
- Transaction creation

### Scenario 3: Test Cancellation
```bash
./quick_test.sh cancel
```
**Verifies:**
- Cancellation before return
- No charges for postpaid
- Powerbank returned to station

## Troubleshooting

### Issue: "No available powerbanks"
```sql
-- Check powerbank availability
SELECT s.station_name, COUNT(pb.id) as available
FROM stations s
LEFT JOIN power_banks pb ON pb.current_station_id = s.id AND pb.status = 'AVAILABLE'
WHERE s.status = 'ONLINE'
GROUP BY s.id, s.station_name;
```

### Issue: "Insufficient balance"
```bash
# Add balance via Django shell
docker exec -it cg-api-local python manage.py shell

from api.user.auth.models import User
from decimal import Decimal
user = User.objects.get(email='janak@powerbank.com')
user.wallet.balance += Decimal('1000.00')
user.wallet.save()
exit()
```

### Issue: "Rental already active"
```sql
-- Force complete existing rental
UPDATE rentals
SET status = 'COMPLETED', ended_at = NOW()
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND status IN ('ACTIVE', 'OVERDUE');
```

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/login` | POST | Get admin token |
| `/api/auth/me` | GET | Get user info |
| `/api/users/wallet` | GET | Get wallet balance |
| `/api/rentals/packages` | GET | List packages |
| `/api/rentals/start` | POST | Start rental |
| `/api/rentals/active` | GET | Get active rental |
| `/api/rentals/{id}/pay-due` | POST | Pay outstanding dues |
| `/api/rentals/{id}/cancel` | POST | Cancel rental |
| `/api/rentals/history` | GET | Get rental history |

## Database Tables

| Table | Key Fields |
|-------|------------|
| `rentals` | status, payment_status, amount_paid, overdue_amount |
| `transactions` | transaction_type, amount, status |
| `wallets` | balance |
| `wallet_transactions` | amount, balance_after |
| `points` | current_points |
| `point_transactions` | points, balance_after |

## Expected Values

### Postpaid Rental Start
- `status`: ACTIVE
- `payment_status`: PENDING
- `amount_paid`: 0.00
- `overdue_amount`: 0.00
- Transactions: 0

### Postpaid Rental Return (On-Time)
- `status`: COMPLETED
- `payment_status`: PAID
- `amount_paid`: [calculated]
- `overdue_amount`: 0.00
- Transactions: 1 (RENTAL_DUE)

### Postpaid Rental Return (Late)
- `status`: COMPLETED
- `payment_status`: PAID or PENDING
- `amount_paid`: [calculated]
- `overdue_amount`: [calculated] or 0.00 if paid
- Transactions: 1 if paid, 0 if pending

## Logs

```bash
# API logs
docker logs -f cg-api-local

# Celery logs
docker logs -f cg-celery-local

# Database logs
docker logs -f cg-db-local

# All logs
docker-compose logs -f
```

## Test Checklist

Before testing:
- [ ] Docker containers running
- [ ] Database accessible
- [ ] Admin credentials working
- [ ] Test user has balance

During testing:
- [ ] Record initial balances
- [ ] Save rental codes
- [ ] Note timestamps
- [ ] Check API responses

After testing:
- [ ] Verify database state
- [ ] Check transaction records
- [ ] Confirm balance changes
- [ ] Review logs for errors

## Next Steps

1. Run automated tests: `./quick_test.sh postpaid`
2. Review results and logs
3. Run database verification queries
4. Document any issues found
5. Proceed to next scenario

## Support

- Documentation: `docs/Testing/`
- API Docs: http://localhost:8010/api/docs
- Admin Panel: http://localhost:8010/admin
