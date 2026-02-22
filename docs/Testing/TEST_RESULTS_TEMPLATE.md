# Test Results Log

**Test Date:** _______________
**Test Time:** _______________
**Tester:** _______________
**Scenario:** _______________

---

## Test Environment

- **Base URL:** http://localhost:8010
- **Docker Status:** ☐ Running ☐ Not Running
- **Database Accessible:** ☐ Yes ☐ No
- **Admin Token:** ☐ Obtained ☐ Failed

---

## Initial State

### User Information
- **User ID:** _______________
- **Email:** _______________
- **Username:** _______________

### Balances (Before Test)
- **Wallet Balance:** _______ NPR
- **Points Balance:** _______ points
- **Active Rentals:** _______ (should be 0)

### Package Information
- **Package ID:** _______________
- **Package Name:** _______________
- **Payment Model:** ☐ PREPAID ☐ POSTPAID
- **Price:** _______ NPR
- **Duration:** _______ minutes

### Station Information
- **Station Serial:** _______________
- **Station Name:** _______________
- **Available Powerbanks:** _______

---

## Test Execution

### Step 1: Admin Login
- **Status:** ☐ Success ☐ Failed
- **Token Obtained:** ☐ Yes ☐ No
- **Response Code:** _______
- **Notes:**
  ```

  ```

### Step 2: Get User Info
- **Status:** ☐ Success ☐ Failed
- **Response Code:** _______
- **Wallet Balance Confirmed:** ☐ Yes ☐ No
- **Notes:**
  ```

  ```

### Step 3: Get Packages
- **Status:** ☐ Success ☐ Failed
- **Response Code:** _______
- **Postpaid Package Found:** ☐ Yes ☐ No
- **Prepaid Package Found:** ☐ Yes ☐ No
- **Notes:**
  ```

  ```

### Step 4: Get Stations
- **Status:** ☐ Success ☐ Failed
- **Response Code:** _______
- **Available Station Found:** ☐ Yes ☐ No
- **Notes:**
  ```

  ```

### Step 5: Start Rental
- **Status:** ☐ Success ☐ Failed
- **Response Code:** _______
- **Rental ID:** _______________
- **Rental Code:** _______________
- **Powerbank Serial:** _______________
- **Started At:** _______________
- **Due At:** _______________
- **Initial Status:** _______________
- **Initial Payment Status:** _______________
- **Initial Amount Paid:** _______ NPR
- **Initial Overdue Amount:** _______ NPR

**API Response:**
```json


```

**Database Verification:**
```sql
-- Rental record
SELECT rental_code, status, payment_status, amount_paid, overdue_amount
FROM rentals WHERE rental_code = 'RENTAL_CODE';

Result:


-- Transaction check (should be none for postpaid)
SELECT COUNT(*) FROM transactions
WHERE related_rental_id = 'RENTAL_ID';

Result:


-- Wallet balance (should be unchanged for postpaid)
SELECT balance FROM wallets WHERE user_id = 'USER_ID';

Result:

```

**Verification Status:** ☐ Pass ☐ Fail
**Notes:**
```


```

### Step 6: Get Active Rental
- **Status:** ☐ Success ☐ Failed
- **Response Code:** _______
- **Rental Status:** _______________
- **Payment Status:** _______________
- **Amount Paid:** _______ NPR
- **Overdue Amount:** _______ NPR
- **Current Overdue Amount:** _______ NPR
- **Estimated Total Cost:** _______ NPR
- **Minutes Overdue:** _______

**API Response:**
```json


```

**Verification Status:** ☐ Pass ☐ Fail
**Notes:**
```


```

### Step 7: Make Rental Overdue (If Testing Late Return)
- **Status:** ☐ Success ☐ Failed ☐ N/A
- **Overdue By:** _______ hours
- **New Due At:** _______________

**Database Verification:**
```sql
SELECT due_at, status FROM rentals WHERE rental_code = 'RENTAL_CODE';

Result:

```

**Verification Status:** ☐ Pass ☐ Fail ☐ N/A
**Notes:**
```


```

### Step 8: Return Rental
- **Status:** ☐ Success ☐ Failed
- **Return Method:** ☐ IoT Script ☐ Manual
- **Returned At:** _______________
- **Final Status:** _______________
- **Final Payment Status:** _______________
- **Final Amount Paid:** _______ NPR
- **Final Overdue Amount:** _______ NPR
- **Is Returned On Time:** ☐ Yes ☐ No

**IoT Script Output:**
```


```

**Database Verification:**
```sql
-- Rental record
SELECT rental_code, status, payment_status, amount_paid, overdue_amount,
       is_returned_on_time, ended_at
FROM rentals WHERE rental_code = 'RENTAL_CODE';

Result:


-- Transaction created?
SELECT transaction_id, transaction_type, amount, status, payment_method_type
FROM transactions
WHERE related_rental_id = 'RENTAL_ID'
ORDER BY created_at DESC;

Result:


-- Wallet balance
SELECT balance FROM wallets WHERE user_id = 'USER_ID';

Result:


-- Wallet transaction
SELECT transaction_type, amount, balance_after, description
FROM wallet_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC LIMIT 3;

Result:


-- Points balance
SELECT current_points FROM points WHERE user_id = 'USER_ID';

Result:


-- Point transactions (completion bonus)
SELECT transaction_type, points, description
FROM point_transactions
WHERE user_id = 'USER_ID'
ORDER BY created_at DESC LIMIT 5;

Result:

```

**Verification Status:** ☐ Pass ☐ Fail
**Notes:**
```


```

### Step 9: Pay Due (If Payment Pending)
- **Status:** ☐ Success ☐ Failed ☐ N/A
- **Response Code:** _______
- **Transaction ID:** _______________
- **Amount Paid:** _______ NPR
- **Payment Method:** _______________

**API Response:**
```json


```

**Database Verification:**
```sql
-- Rental updated
SELECT status, payment_status, overdue_amount
FROM rentals WHERE rental_code = 'RENTAL_CODE';

Result:


-- Transaction created
SELECT transaction_id, transaction_type, amount, status
FROM transactions
WHERE related_rental_id = 'RENTAL_ID'
ORDER BY created_at DESC;

Result:


-- Wallet balance
SELECT balance FROM wallets WHERE user_id = 'USER_ID';

Result:

```

**Verification Status:** ☐ Pass ☐ Fail ☐ N/A
**Notes:**
```


```

### Step 10: Get Rental History
- **Status:** ☐ Success ☐ Failed
- **Response Code:** _______
- **Rental Found in History:** ☐ Yes ☐ No
- **History Status:** _______________
- **History Payment Status:** _______________
- **History Amount Paid:** _______ NPR
- **History Overdue Amount:** _______ NPR
- **History Is Returned On Time:** ☐ Yes ☐ No

**API Response:**
```json


```

**Verification Status:** ☐ Pass ☐ Fail
**Notes:**
```


```

### Step 11: Cancel Rental (If Testing Cancellation)
- **Status:** ☐ Success ☐ Failed ☐ N/A
- **Response Code:** _______
- **Cancellation Reason:** _______________
- **Refund Amount:** _______ NPR

**API Response:**
```json


```

**Database Verification:**
```sql
-- Rental cancelled
SELECT status, payment_status, amount_paid, ended_at
FROM rentals WHERE rental_code = 'RENTAL_CODE';

Result:


-- Powerbank returned
SELECT status, current_station_id, current_rental_id
FROM power_banks WHERE serial_number = 'POWERBANK_SERIAL';

Result:

```

**Verification Status:** ☐ Pass ☐ Fail ☐ N/A
**Notes:**
```


```

---

## Final State

### Balances (After Test)
- **Wallet Balance:** _______ NPR
- **Points Balance:** _______ points
- **Active Rentals:** _______

### Balance Changes
- **Wallet Change:** _______ NPR (Expected: _______)
- **Points Change:** _______ points (Expected: _______)

### Calculations
- **Usage Duration:** _______ minutes
- **Usage Cost:** _______ NPR
- **Late Fee:** _______ NPR
- **Total Paid:** _______ NPR
- **Points Earned:** _______ points

---

## Data Integrity Checks

### Rental Table
- ☐ Status is correct
- ☐ Payment status is correct
- ☐ Amount paid matches calculation
- ☐ Overdue amount is correct (0 if paid)
- ☐ Timestamps are accurate
- ☐ is_returned_on_time is correct

### Transaction Table
- ☐ Transaction created (if payment made)
- ☐ Transaction type is correct
- ☐ Transaction amount matches
- ☐ Transaction status is SUCCESS
- ☐ Payment method type is correct

### Wallet Table
- ☐ Balance deducted correctly
- ☐ Wallet transaction logged
- ☐ Balance_after is accurate

### Points Table
- ☐ Points deducted correctly (if used)
- ☐ Points awarded correctly
- ☐ Point transactions logged
- ☐ Balance_after is accurate

### Revenue Distribution
- ☐ Distribution created (if applicable)
- ☐ Amounts calculated correctly
- ☐ Status is correct

---

## Issues Found

### Issue 1
- **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
- **Description:**
  ```

  ```
- **Expected Behavior:**
  ```

  ```
- **Actual Behavior:**
  ```

  ```
- **Steps to Reproduce:**
  ```
  1.
  2.
  3.
  ```
- **Logs/Screenshots:**
  ```

  ```

### Issue 2
- **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
- **Description:**
  ```

  ```

### Issue 3
- **Severity:** ☐ Critical ☐ High ☐ Medium ☐ Low
- **Description:**
  ```

  ```

---

## Test Result

### Overall Status
- **Result:** ☐ PASS ☐ FAIL ☐ PARTIAL

### Pass Criteria Met
- ☐ API endpoints responded correctly
- ☐ Rental status updated correctly
- ☐ Payment status updated correctly
- ☐ Amounts calculated correctly
- ☐ Wallet/Points deducted correctly
- ☐ Transactions created correctly
- ☐ History shows accurate data
- ☐ No data integrity issues

### Summary
```




```

### Recommendations
```




```

---

## Logs

### API Logs (Relevant Excerpts)
```


```

### Celery Logs (Relevant Excerpts)
```


```

### Database Logs (Relevant Excerpts)
```


```

---

## Additional Notes

```




```

---

**Test Completed:** _______________
**Reviewed By:** _______________
**Sign-off:** _______________
