# Rental Testing Summary & Action Plan
**Date:** 2026-02-22
**Status:** Ready for Testing

## Overview

We have prepared comprehensive testing documentation for the rental system, with a focus on **postpaid rentals** and complete data flow verification.

## Documents Created

### 1. **POSTPAID_RENTAL_TESTING_PLAN.md**
Complete testing scenarios for postpaid rentals including:
- Normal on-time return flow
- Late return with overdue charges
- Insufficient balance handling
- Cancellation flow
- Database verification queries for each scenario

### 2. **MANUAL_CURL_TESTING_GUIDE.md**
Step-by-step CURL commands for manual API testing:
- Admin login and token setup
- Balance checking
- Package selection
- Rental start/return/cancel
- Payment due settlement
- History verification
- Troubleshooting common issues

### 3. **DATABASE_QUERIES.sql**
Comprehensive SQL queries organized by category:
- User balance queries
- Rental queries (all statuses)
- Transaction verification
- Wallet/Points transaction history
- Revenue distribution
- Data integrity checks
- Performance metrics

## Current Issues Identified

### Issue 1: History API Accuracy After Pay-Due
**Problem:** After paying rental dues, the rental history may not accurately reflect:
- What amount was originally owed
- When the payment was made
- Historical overdue amounts

**Impact:** Users cannot see complete payment history

**Testing Priority:** HIGH

### Issue 2: Active Rental vs History Consistency
**Problem:** Values shown in active rental GET endpoint may differ from history GET endpoint

**Impact:** Inconsistent user experience

**Testing Priority:** MEDIUM

## Testing Approach

### Phase 1: Prepaid Verification (Already Working)
✅ Prepaid rentals are reportedly working as expected
- Quick smoke test to confirm
- Document baseline behavior

### Phase 2: Postpaid Testing (CURRENT FOCUS)
Focus on all postpaid scenarios:

1. **Normal Flow**
   - Start postpaid rental
   - Return on time
   - Verify auto-collection
   - Check all DB tables

2. **Overdue Flow**
   - Start postpaid rental
   - Make it overdue (manual DB update)
   - Return late
   - Verify late fee calculation
   - Test pay-due endpoint

3. **Insufficient Balance**
   - Reduce user balance
   - Return rental
   - Verify payment stays pending
   - Top up and retry payment

4. **Cancellation**
   - Start rental
   - Cancel before return
   - Verify no charges

### Phase 3: Data Flow Verification
For each scenario, verify:
- ✓ Rental table updates correctly
- ✓ Transaction records created
- ✓ Wallet balance deducted
- ✓ Wallet transactions logged
- ✓ Points deducted (if used)
- ✓ Point transactions logged
- ✓ Points awarded (completion bonus)
- ✓ Revenue distribution created
- ✓ History API shows correct data

### Phase 4: Edge Cases
- Exactly at due time return
- Multiple extensions
- Swap during rental
- Different payment modes
- Very long overdue periods

## How to Execute Testing

### Setup
```bash
# 1. Ensure Docker is running
docker ps

# 2. Set admin token
export TOKEN="YOUR_ADMIN_TOKEN"

# 3. Connect to database (separate terminal)
docker exec -it cg-db-local psql -U postgres -d chargeGhar
```

### Execute Test Scenario
```bash
# 1. Follow MANUAL_CURL_TESTING_GUIDE.md step by step
# 2. Record all values in a test log
# 3. Run DATABASE_QUERIES.sql after each step
# 4. Compare expected vs actual results
```

### Test Log Template
```
Test: Postpaid Normal Flow
Date: 2026-02-22
Time: 12:42

Initial State:
- Wallet Balance: 1000.00 NPR
- Points Balance: 500 points
- Active Rentals: 0

Step 1: Start Rental
- API Response: ✓ 201 Created
- Rental Code: ABCD1234
- Status: ACTIVE
- Payment Status: PENDING
- Amount Paid: 0.00
- DB Check: ✓ Rental created, no transaction

Step 2: Return On-Time
- API Response: ✓ (via IoT script)
- Status: COMPLETED
- Payment Status: PAID
- Amount Paid: 50.00
- Overdue Amount: 0.00
- DB Check: ✓ Transaction created, wallet deducted

Final State:
- Wallet Balance: 950.00 NPR (✓ -50.00)
- Points Balance: 555 points (✓ +55 bonus)
- Transactions: 1 RENTAL_DUE (✓)

Result: ✅ PASS
Issues: None
```

## Database Monitoring

### Real-time Monitoring
```sql
-- Watch rentals table
SELECT rental_code, status, payment_status, amount_paid, overdue_amount, updated_at
FROM rentals
WHERE user_id = 'USER_ID'
ORDER BY updated_at DESC
LIMIT 5;

-- Watch transactions
SELECT transaction_id, transaction_type, amount, status, created_at
FROM transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC
LIMIT 5;

-- Watch wallet
SELECT balance, updated_at
FROM wallets
WHERE user_id = 'USER_ID';
```

### After Each Test
Run the complete verification script:
```bash
# Replace rental code in the SQL file
sed -i "s/RENTAL_CODE_HERE/ABCD1234/g" docs/Testing/DATABASE_QUERIES.sql

# Run verification
docker exec -it cg-db-local psql -U postgres -d chargeGhar -f /path/to/DATABASE_QUERIES.sql
```

## Expected Outcomes

### Postpaid Rental (On-Time)
| Metric | Expected Value |
|--------|----------------|
| Initial amount_paid | 0.00 |
| Initial payment_status | PENDING |
| Transaction at start | None |
| Final status | COMPLETED |
| Final payment_status | PAID |
| Final amount_paid | Calculated usage cost |
| Final overdue_amount | 0.00 |
| Transaction created | Yes (RENTAL_DUE) |
| Wallet deducted | Yes |
| Points awarded | Yes (completion + on-time) |

### Postpaid Rental (Late)
| Metric | Expected Value |
|--------|----------------|
| Initial amount_paid | 0.00 |
| Initial payment_status | PENDING |
| Status when overdue | OVERDUE |
| Final status | COMPLETED |
| Final payment_status | PAID (if sufficient) or PENDING |
| Final amount_paid | Calculated usage cost |
| Final overdue_amount | Calculated late fee (or 0 if paid) |
| Transaction created | Yes (if paid) |
| Wallet deducted | Yes (if paid) |
| Points awarded | Yes (completion only, no on-time bonus) |

## Success Criteria

### Must Pass
- [ ] All postpaid scenarios complete successfully
- [ ] Database tables update correctly
- [ ] Wallet/Points deducted accurately
- [ ] Transaction records match deductions
- [ ] History API shows accurate data
- [ ] No data integrity issues

### Should Pass
- [ ] Auto-collection works when balance sufficient
- [ ] Payment pending when balance insufficient
- [ ] Pay-due endpoint works correctly
- [ ] Late fee calculation is accurate
- [ ] Points awarded correctly

### Nice to Have
- [ ] Revenue distribution calculated
- [ ] Notifications sent
- [ ] Logs are clear and helpful

## Next Actions

### Immediate (Today)
1. ✅ Review testing documentation
2. ⏳ Run prepaid smoke test (quick verification)
3. ⏳ Execute Postpaid Scenario 1 (normal flow)
4. ⏳ Execute Postpaid Scenario 2 (late return)
5. ⏳ Document any issues found

### Short-term (This Week)
1. Complete all postpaid scenarios
2. Test edge cases
3. Fix any issues discovered
4. Re-test after fixes
5. Update old test scripts if needed

### Medium-term
1. Automate these tests
2. Add to CI/CD pipeline
3. Create monitoring dashboards
4. Document business logic clearly

## Tools & Resources

### Testing Tools
- **CURL** - Manual API testing
- **Python Scripts** - IoT return simulation
- **PostgreSQL** - Database verification
- **Docker** - Environment management

### Documentation
- API Swagger: http://localhost:8010/api/docs
- Admin Panel: http://localhost:8010/admin
- Database: cg-db-local container

### Logs
```bash
# API logs
docker logs -f cg-api-local

# Celery logs (async tasks)
docker logs -f cg-celery-local

# Database logs
docker logs -f cg-db-local
```

## Contact & Support

If you encounter issues during testing:
1. Check the troubleshooting section in MANUAL_CURL_TESTING_GUIDE.md
2. Review Docker logs for errors
3. Verify database state with queries
4. Document the issue with full context

## Notes

- All testing is done in local Docker environment
- Database can be reset if needed (backup first!)
- Use admin token for testing (has all permissions)
- Timestamps are in UTC
- Amounts are in NPR with 2 decimal places
- Test data can be created via Django shell if needed

---

**Ready to begin testing!** Start with MANUAL_CURL_TESTING_GUIDE.md and follow step-by-step.
