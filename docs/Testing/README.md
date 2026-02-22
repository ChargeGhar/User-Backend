# Rental Testing Documentation

## Overview

This directory contains comprehensive testing documentation and tools for the ChargeGhar rental system, with a focus on **postpaid rental flows** and complete data integrity verification.

## 📁 Files in This Directory

### Core Documentation
1. **`TESTING_SUMMARY.md`** - Start here! Overview, action plan, and success criteria
2. **`QUICK_REFERENCE.md`** - Quick commands and common scenarios
3. **`MANUAL_CURL_TESTING_GUIDE.md`** - Detailed step-by-step CURL testing
4. **`POSTPAID_RENTAL_TESTING_PLAN.md`** - Complete postpaid scenarios with DB verification
5. **`DATABASE_QUERIES.sql`** - All SQL queries for verification
6. **`quick_test.sh`** - Automated testing script
7. **`TEST_RESULTS_TEMPLATE.md`** - Template for recording test results

## 🚀 Quick Start

### Option 1: Automated Testing (Recommended)
```bash
cd docs/Testing

# Make script executable (first time only)
chmod +x quick_test.sh

# Run a test scenario
./quick_test.sh postpaid
```

### Option 2: Manual Testing
```bash
# Follow the step-by-step guide
cat MANUAL_CURL_TESTING_GUIDE.md

# Or use quick reference
cat QUICK_REFERENCE.md
```

## 📋 Test Scenarios Available

### 1. Prepaid Rental Test
```bash
./quick_test.sh prepaid
```
Tests the prepaid rental flow (already working, for baseline verification).

### 2. Postpaid Rental Test (Normal)
```bash
./quick_test.sh postpaid
```
Tests postpaid rental with on-time return and auto-collection.

### 3. Postpaid Rental Test (Late Return)
```bash
./quick_test.sh postpaid-late
```
Tests postpaid rental with overdue charges and pay-due flow.

### 4. Rental Cancellation Test
```bash
./quick_test.sh cancel
```
Tests rental cancellation before return.

## 🎯 What Gets Tested

Each test scenario verifies:
- ✅ API endpoint responses (status codes, data structure)
- ✅ Rental table updates (status, payment_status, amounts)
- ✅ Transaction creation and status
- ✅ Wallet balance deductions
- ✅ Wallet transaction records
- ✅ Points deductions (if used)
- ✅ Point transaction records
- ✅ Points awarded (completion bonuses)
- ✅ Revenue distribution (if applicable)
- ✅ Rental history accuracy

## 📊 Current Focus

### Primary Goal
Test **postpaid rental flows** comprehensively to ensure:
1. No payment at rental start (amount_paid = 0)
2. Usage cost calculated correctly at return
3. Late fees calculated accurately for overdue returns
4. Auto-collection works when balance sufficient
5. Payment remains pending when balance insufficient
6. Pay-due endpoint functions correctly
7. History API shows accurate data

### Known Issues to Verify
1. **History API Accuracy** - After pay-due, does history show correct historical values?
2. **Active vs History Consistency** - Do active rental and history endpoints show consistent data?

## 🔧 Prerequisites

### Required Tools
- **Docker** - Containers must be running
- **curl** - For API testing
- **jq** - For JSON parsing (install: `sudo apt install jq` or `brew install jq`)
- **psql** - For database queries (included in Docker)
- **Python 3** - For IoT return simulation

### Environment Setup
```bash
# Verify Docker is running
docker ps

# Should see these containers:
# - cg-api-local
# - cg-db-local
# - cg-celery-local
# - cg-redis-local
# - cg-rabbitmq-local
# - cg-pgbouncer-local
```

### Admin Credentials
- **Email:** janak@powerbank.com
- **Password:** 5060
- **Base URL:** http://localhost:8010

## 📖 How to Use This Documentation

### For First-Time Testing
1. Read `TESTING_SUMMARY.md` - Understand the overall approach
2. Review `QUICK_REFERENCE.md` - Get familiar with commands
3. Run `./quick_test.sh postpaid` - Execute automated test
4. Review results and logs
5. Run database queries from `DATABASE_QUERIES.sql`

### For Manual Testing
1. Open `MANUAL_CURL_TESTING_GUIDE.md`
2. Follow step-by-step instructions
3. Record results in `TEST_RESULTS_TEMPLATE.md`
4. Use `DATABASE_QUERIES.sql` for verification

### For Deep Dive
1. Read `POSTPAID_RENTAL_TESTING_PLAN.md` - Detailed scenarios
2. Understand expected database states
3. Learn about data flow through all tables
4. Identify edge cases to test

## 🗄️ Database Access

### Connect to Database
```bash
docker exec -it cg-db-local psql -U postgres -d chargeGhar
```

### Run Verification Queries
```bash
# From host machine
docker exec -i cg-db-local psql -U postgres -d chargeGhar < DATABASE_QUERIES.sql

# Or copy file into container
docker cp DATABASE_QUERIES.sql cg-db-local:/tmp/
docker exec -it cg-db-local psql -U postgres -d chargeGhar -f /tmp/DATABASE_QUERIES.sql
```

### Quick Queries
```sql
-- Check rental
SELECT rental_code, status, payment_status, amount_paid, overdue_amount
FROM rentals WHERE rental_code = 'YOUR_CODE';

-- Check transactions
SELECT transaction_id, transaction_type, amount, status
FROM transactions WHERE related_rental_id = 'RENTAL_UUID';

-- Check wallet
SELECT balance FROM wallets WHERE user_id = 'USER_UUID';
```

## 📝 Recording Test Results

Use the provided template:
```bash
cp TEST_RESULTS_TEMPLATE.md test_results_$(date +%Y%m%d_%H%M%S).md
```

Fill in:
- Initial state (balances, active rentals)
- Each step's API response
- Database verification results
- Final state
- Issues found
- Pass/Fail status

## 🐛 Troubleshooting

### Common Issues

#### "No available powerbanks"
```sql
-- Check availability
SELECT s.station_name, COUNT(pb.id) as available
FROM stations s
LEFT JOIN power_banks pb ON pb.current_station_id = s.id
  AND pb.status = 'AVAILABLE'
WHERE s.status = 'ONLINE'
GROUP BY s.id, s.station_name;
```

#### "Insufficient balance"
```bash
docker exec -it cg-api-local python manage.py shell
>>> from api.user.auth.models import User
>>> from decimal import Decimal
>>> user = User.objects.get(email='janak@powerbank.com')
>>> user.wallet.balance += Decimal('1000.00')
>>> user.wallet.save()
>>> exit()
```

#### "Rental already active"
```sql
UPDATE rentals
SET status = 'COMPLETED', ended_at = NOW()
WHERE user_id = (SELECT id FROM users WHERE email = 'janak@powerbank.com')
  AND status IN ('ACTIVE', 'OVERDUE');
```

#### Script fails with "jq: command not found"
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Windows (Git Bash)
# Download from https://stedolan.github.io/jq/download/
```

### Viewing Logs
```bash
# API logs
docker logs -f cg-api-local

# Celery logs (async tasks)
docker logs -f cg-celery-local

# Database logs
docker logs -f cg-db-local

# All logs
docker-compose logs -f
```

## 📈 Test Results Tracking

### Create Test Log
```bash
# Create dated log file
./quick_test.sh postpaid 2>&1 | tee test_log_$(date +%Y%m%d_%H%M%S).txt
```

### Compare Results
Keep test logs to compare:
- Before and after code changes
- Different payment modes
- Different scenarios
- Edge cases

## 🔄 Testing Workflow

### Daily Testing
1. Run automated tests: `./quick_test.sh postpaid`
2. Review results
3. Check for regressions
4. Document any issues

### Before Deployment
1. Run all scenarios (prepaid, postpaid, postpaid-late, cancel)
2. Verify database integrity
3. Check all edge cases
4. Review logs for warnings
5. Confirm all tests pass

### After Bug Fixes
1. Run specific scenario that was broken
2. Verify fix in database
3. Run full test suite
4. Update documentation if needed

## 📚 Related Documentation

### API Documentation
- Swagger UI: http://localhost:8010/api/docs
- ReDoc: http://localhost:8010/api/redoc

### Admin Panel
- URL: http://localhost:8010/admin
- Credentials: janak@powerbank.com / 5060

### Old Test Scripts
- `tests/OLD/test_iot_return.py` - IoT return simulation
- `tests/OLD/test_rental_flows.py` - Legacy rental flow tests

## 🎓 Understanding the System

### Rental Flow (Postpaid)
1. **Start:** User selects postpaid package → Rental created with amount_paid=0
2. **Active:** User has powerbank → No payment yet
3. **Return:** Powerbank returned → Usage cost calculated
4. **Auto-collect:** System attempts payment from wallet/points
5. **Complete:** If paid → status=COMPLETED, payment_status=PAID
6. **Pending:** If insufficient → status=COMPLETED, payment_status=PENDING
7. **Pay-due:** User tops up and pays → payment_status=PAID

### Database Tables Flow
```
Rental Start:
  rentals ← New record (status=ACTIVE, payment_status=PENDING, amount_paid=0)

Rental Return:
  rentals ← Update (status=COMPLETED, amount_paid=calculated)
  transactions ← New record (if auto-collected)
  wallet_transactions ← New record (if wallet used)
  point_transactions ← New record (if points used)
  revenue_distributions ← New record (if paid)

Pay Due:
  rentals ← Update (payment_status=PAID, overdue_amount=0)
  transactions ← New record
  wallet_transactions ← New record
  point_transactions ← New record
  revenue_distributions ← New record
```

## 🚨 Important Notes

### Testing Best Practices
- Always record initial balances before testing
- Save rental codes and IDs for verification
- Run database queries after each step
- Keep logs of all test runs
- Document unexpected behavior immediately

### Data Safety
- Testing is done in local Docker environment
- Database can be reset if needed (backup first!)
- Use admin token for testing (has all permissions)
- Don't test in production!

### Timestamps
- All timestamps are in UTC
- Convert to local time for readability
- Be aware of timezone differences in calculations

### Amounts
- All amounts in NPR (Nepalese Rupees)
- Decimal precision: 2 places (0.00)
- Points conversion: 10 points = 1 NPR

## 🤝 Contributing

### Adding New Tests
1. Document the scenario in `POSTPAID_RENTAL_TESTING_PLAN.md`
2. Add CURL commands to `MANUAL_CURL_TESTING_GUIDE.md`
3. Update `quick_test.sh` with new function
4. Add verification queries to `DATABASE_QUERIES.sql`
5. Update this README

### Reporting Issues
When reporting issues found during testing:
1. Scenario being tested
2. Expected behavior
3. Actual behavior
4. API responses (full JSON)
5. Database state (query results)
6. Logs (relevant excerpts)
7. Steps to reproduce

## 📞 Support

For questions or issues:
1. Check troubleshooting section above
2. Review logs for error messages
3. Verify database state with queries
4. Check API documentation
5. Review related code in `api/user/rentals/`

## 🎯 Success Criteria

Testing is successful when:
- ✅ All automated tests pass
- ✅ Database state matches expectations
- ✅ Wallet/points deducted correctly
- ✅ Transaction records are accurate
- ✅ History API shows correct data
- ✅ No data integrity issues
- ✅ Logs show no errors

## 📅 Last Updated

**Date:** 2026-02-22
**Status:** Ready for testing
**Focus:** Postpaid rental flows

---

**Ready to start testing?** Run `./quick_test.sh postpaid` and let's verify the system! 🚀
