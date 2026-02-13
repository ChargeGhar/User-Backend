# Pay Due Cross-Verification Plan

**Date:** 2026-02-13 21:49  
**Goal:** Verify DUE.md accuracy against actual implementation

---

## Verification Strategy

### Phase 1: Code Discovery (What exists?)
1. Find all files involved in pay-due flow
2. Map the complete execution path
3. Identify all response builders
4. Document actual field names used

### Phase 2: Response Format Analysis (What's returned?)
1. Extract actual response structure from code
2. Compare with DUE.md specifications
3. Identify mismatches in field names
4. Check HTTP status codes

### Phase 3: Business Logic Verification (What's the logic?)
1. Trace payment mode handling
2. Verify balance calculation logic
3. Check powerbank return detection
4. Validate status transitions

### Phase 4: Live Testing (What actually happens?)
1. Setup test data
2. Execute each scenario
3. Capture actual responses
4. Compare with DUE.md expectations

---

## Phase 1: Code Discovery

### Step 1.1: Find Entry Point
**File:** `api/user/rentals/views/support_views.py`
**Class:** `RentalPayDueView`
**Method:** `post()`

**Questions to Answer:**
- What serializer is used?
- What service is called?
- How are responses built?
- What HTTP status codes are returned?

### Step 1.2: Find Service Layer
**File:** `api/user/rentals/services/rental/rental_due_service.py`
**Class:** `RentalDuePaymentService`
**Method:** `pay_rental_due()`

**Questions to Answer:**
- What does the return dictionary contain?
- What field names are used?
- How is payment_required raised?
- What's in the exception context?

### Step 1.3: Find Payment Flow Service
**File:** `api/user/payments/services/rental_payment_flow.py`
**Class:** `RentalPaymentFlowService`

**Questions to Answer:**
- How is breakdown calculated?
- What field names in breakdown?
- How is payment intent created?
- What's in intent metadata?

### Step 1.4: Find Payment Service
**File:** `api/user/payments/services/rental_payment.py`
**Class:** `RentalPaymentService`
**Method:** `pay_rental_due()`

**Questions to Answer:**
- How is transaction created?
- What status transitions happen?
- How is powerbank return detected?
- What fields are updated?

---

## Phase 2: Response Format Analysis

### Step 2.1: Success Response Structure

**Extract from code:**
```python
# rental_due_service.py line ~96
return {
    "transaction_id": ...,
    "rental_id": ...,
    "rental_code": ...,
    "amount_paid": ...,
    "payment_breakdown": {  # ⚠️ Check actual name
        ...
    },
    ...
}
```

**Compare with DUE.md:**
```json
{
  "breakdown": {  // Expected name
    "wallet_amount": "50.00",
    "points_used": 500,
    "points_amount": "50.00"
  }
}
```

**Verification Points:**
- [ ] Field name: `payment_breakdown` or `breakdown`?
- [ ] Nested fields: What are actual names?
- [ ] Data types: strings or numbers?
- [ ] Decimal places: 2 decimals for amounts?

### Step 2.2: Payment Required Response

**Extract from code:**
```python
# support_views.py line ~165
if error_code in self.BUSINESS_BLOCKING_CODES:
    return self.success_response(  # ⚠️ Check status code
        data={"error": payload},  # ⚠️ Check structure
        status_code=status.HTTP_200_OK,  # ⚠️ Should be 402?
    )
```

**Compare with DUE.md:**
```json
{
  "success": false,
  "error_code": "payment_required",
  "data": {  // Flat, not nested in "error"
    "intent_id": "...",
    "shortfall": "...",
    ...
  }
}
```

**Verification Points:**
- [ ] HTTP status: 200 or 402?
- [ ] Structure: nested in "error" or flat?
- [ ] success field: true or false?
- [ ] Field names in data

### Step 2.3: Error Response Structure

**Extract from code:**
```python
# support_views.py
return self.error_response(
    message=...,
    status_code=...,
    error_code=...,
    context=...
)
```

**Verification Points:**
- [ ] HTTP status codes for each error
- [ ] Error code values
- [ ] Context structure

---

## Phase 3: Business Logic Verification

### Step 3.1: Payment Mode Handling

**Code to Check:**
```python
# rental_due_service.py
def pay_rental_due(
    self,
    payment_mode: str = "wallet_points",
    ...
):
```

**Verify:**
- [ ] Default mode is "wallet_points"
- [ ] All 4 modes supported: wallet, points, wallet_points, direct
- [ ] Mode validation logic
- [ ] Mode-specific behavior

### Step 3.2: Balance Calculation

**Code to Check:**
```python
# rental_payment_flow.py
def calculate_payment_options(...):
```

**Verify:**
- [ ] How wallet balance is checked
- [ ] How points are converted to amount
- [ ] How shortfall is calculated
- [ ] How breakdown is built

### Step 3.3: Powerbank Return Detection

**Code to Check:**
```python
# rental_payment.py
def pay_rental_due(
    self,
    is_powerbank_returned: bool = True,
    ...
):
```

**Verify:**
- [ ] How is_powerbank_returned is determined
- [ ] Status change logic based on return
- [ ] OVERDUE vs COMPLETED logic

### Step 3.4: Status Transitions

**Code to Check:**
```python
# rental_payment.py
if is_powerbank_returned:
    rental.status = 'COMPLETED'
else:
    # Keep current status
```

**Verify:**
- [ ] When status changes to COMPLETED
- [ ] When status stays OVERDUE
- [ ] payment_status transitions
- [ ] Other field updates

---

## Phase 4: Live Testing

### Step 4.1: Test Environment Setup

**Prerequisites:**
```bash
# 1. Create test rental with dues
# 2. Set user balance
# 3. Flush Redis
# 4. Get rental_id
```

### Step 4.2: Test Execution Matrix

| Test | Mode | Balance | Method ID | Expected HTTP | Expected success |
|------|------|---------|-----------|---------------|------------------|
| T1 | wallet | Sufficient | - | 200 | true |
| T2 | wallet | Insufficient | Yes | ? | ? |
| T3 | points | Sufficient | - | 200 | true |
| T4 | points | Insufficient | Yes | ? | ? |
| T5 | wallet_points | Sufficient | - | 200 | true |
| T6 | wallet_points | Insufficient | Yes | ? | ? |
| T7 | direct | Any | Yes | ? | ? |
| T8 | wallet | Insufficient | No | 400 | false |

**For each test, capture:**
- Actual HTTP status code
- Actual response JSON
- Actual database changes
- Compare with DUE.md

### Step 4.3: Response Field Verification

**For each response, check:**
```python
response = {...}

# Check top-level fields
assert "success" in response
assert "message" in response or "error_code" in response
assert "data" in response

# Check data structure
data = response["data"]

# If success:
if response["success"]:
    assert "transaction_id" in data
    assert "rental_id" in data
    assert "rental_code" in data
    assert "amount_paid" in data
    assert "breakdown" in data or "payment_breakdown" in data  # ⚠️ Which one?
    
    # Check breakdown fields
    breakdown = data.get("breakdown") or data.get("payment_breakdown")
    assert "wallet_amount" in breakdown
    assert "points_used" in breakdown
    assert "points_amount" in breakdown

# If payment_required:
if response.get("error_code") == "payment_required":
    assert "intent_id" in data
    assert "shortfall" in data
    assert "gateway" in data
    assert "gateway_url" in data
```

---

## Verification Checklist

### Code Structure
- [ ] Entry point identified (support_views.py)
- [ ] Service layer mapped (rental_due_service.py)
- [ ] Payment flow traced (rental_payment_flow.py)
- [ ] Transaction creation found (rental_payment.py)

### Response Format
- [ ] Success response structure extracted
- [ ] Payment required structure extracted
- [ ] Error response structure extracted
- [ ] Field names documented

### Field Naming
- [ ] `breakdown` vs `payment_breakdown`
- [ ] `wallet_amount` vs `wallet_used`
- [ ] `points_used` vs `points_to_use`
- [ ] `points_amount` field exists?

### HTTP Status Codes
- [ ] Success: 200 or 201?
- [ ] Payment required: 200 or 402?
- [ ] Validation errors: 400?
- [ ] Not found: 404?

### Business Logic
- [ ] Payment mode handling verified
- [ ] Balance calculation verified
- [ ] Powerbank return detection verified
- [ ] Status transitions verified

### Live Testing
- [ ] Test environment setup
- [ ] All 8 core scenarios tested
- [ ] Actual responses captured
- [ ] Compared with DUE.md

---

## Execution Plan

### Step-by-Step Process

**1. Extract Actual Response Format (30 min)**
```bash
# Read all relevant files
# Extract return statements
# Document actual field names
# Note HTTP status codes
```

**2. Compare with DUE.md (15 min)**
```bash
# Create comparison table
# Highlight mismatches
# Document differences
```

**3. Setup Test Environment (15 min)**
```bash
# Create rental with dues
# Set user balance
# Prepare test data
```

**4. Execute Live Tests (45 min)**
```bash
# Run 8 core scenarios
# Capture responses
# Verify database changes
# Document findings
```

**5. Create Verification Report (15 min)**
```bash
# Summary of findings
# List of mismatches
# Required changes
# Updated DUE.md if needed
```

**Total Time:** ~2 hours

---

## Output Documents

### 1. CODE_ANALYSIS.md
- Actual code structure
- Actual response formats
- Actual field names
- Actual HTTP status codes

### 2. COMPARISON.md
- DUE.md vs Actual side-by-side
- Mismatches highlighted
- Severity ratings

### 3. TEST_RESULTS.md
- Live test execution results
- Actual responses captured
- Database state verification
- Pass/Fail for each scenario

### 4. VERIFICATION_REPORT.md
- Executive summary
- Accuracy percentage
- Required changes
- Action items

---

## Success Criteria

**DUE.md is accurate if:**
- [ ] 100% of field names match actual code
- [ ] 100% of HTTP status codes match
- [ ] 100% of response structures match
- [ ] 100% of business logic matches
- [ ] 90%+ of live tests pass as expected

**If not accurate:**
- Document all mismatches
- Update DUE.md to reflect reality
- Create implementation plan for desired changes

---

**Status:** Ready to Execute  
**Next Action:** Start Phase 1 - Code Discovery
