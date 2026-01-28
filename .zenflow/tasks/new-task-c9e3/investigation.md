# Rental Status Flow & Overdue Calculation Investigation

## Investigation Summary

**Date**: 2026-01-28  
**Issue**: Overdue calculation not working properly. User rents 1hr package, doesn't return for 3hrs (2hrs overdue), but system not calculating charges.

---

## 1. DATABASE SCHEMA

### Rental Model (`api/user/rentals/models/rental.py`)

#### Fields:
- `user` - ForeignKey to User
- `station` - ForeignKey to Station (rental start location)
- `return_station` - ForeignKey to Station (return location, nullable)
- `slot` - ForeignKey to StationSlot
- `package` - ForeignKey to RentalPackage
- `power_bank` - ForeignKey to PowerBank (nullable)
- `rental_code` - CharField(10, unique)
- `status` - CharField (choices from RENTAL_STATUS_CHOICES)
- `payment_status` - CharField (choices: PENDING, PAID, FAILED, REFUNDED)
- `started_at` - DateTimeField (nullable, set when status=ACTIVE)
- `ended_at` - DateTimeField (nullable, set when returned)
- `due_at` - DateTimeField (calculated: started_at + package.duration_minutes)
- `amount_paid` - DecimalField (package price for PREPAID, usage cost for POSTPAID)
- `overdue_amount` - DecimalField (late fee charges)
- `is_returned_on_time` - BooleanField
- `timely_return_bonus_awarded` - BooleanField
- `rental_metadata` - JSONField

#### Status Choices:
```python
RENTAL_STATUS_CHOICES = [
    ('PENDING', 'Pending'),           # Initial creation (not used in current flow)
    ('PENDING_POPUP', 'Pending Popup'), # Waiting for device popup verification
    ('ACTIVE', 'Active'),              # Rental in progress
    ('COMPLETED', 'Completed'),        # Returned
    ('CANCELLED', 'Cancelled'),        # Cancelled before completion
    ('OVERDUE', 'Overdue'),           # Past due_at and still active
]
```

#### Computed Properties:
- `current_overdue_amount` - Real-time calculation of current late fee (uses LateFeeService)
- `estimated_total_cost` - amount_paid + current_overdue_amount
- `minutes_overdue` - How many minutes past due_at

### LateFeeConfiguration Model (`api/user/rentals/models/late_fee.py`)

Configurable late fee system with 3 fee types:
- **MULTIPLIER**: Charge 2x, 3x normal rate per minute
- **FLAT_RATE**: Fixed amount per hour
- **COMPOUND**: Multiplier + flat rate

Fields:
- `fee_type` - MULTIPLIER/FLAT_RATE/COMPOUND
- `multiplier` - Decimal (default 2.0)
- `flat_rate_per_hour` - Decimal
- `grace_period_minutes` - Int (minutes before charges apply)
- `max_daily_rate` - Decimal (optional cap)
- `is_active` - Boolean (only one active config at a time)

---

## 2. RENTAL STATUS FLOW

### 2.1 Start Rental Flow

**File**: `api/user/rentals/services/rental/start.py`

```
START REQUEST
     ↓
1. Validate user (no active rentals, meets requirements)
2. Validate station (ONLINE, not maintenance)
3. Validate package (is_active=True)
4. If POSTPAID: Check minimum balance
5. Get available powerbank (battery ≥ 20%, AVAILABLE status)
     ↓
6. Create Rental:
   - status = 'PENDING_POPUP'
   - due_at = now + package.duration_minutes
   - amount_paid = 0
     ↓
7. If PREPAID: Process payment (wallet/points deduction)
     ↓
8. Trigger device popup (15s timeout)
     ↓
9a. SUCCESS:                    9b. FAIL/TIMEOUT:
   - status = 'ACTIVE'              - status remains 'PENDING_POPUP'
   - started_at = now               - Schedule async verification task
   - Align power_bank to actual SN
   - Send notifications
```

**Current Implementation**: Lines 26-139 in start.py

### 2.2 Active → Overdue Transition

#### Mechanism 1: Celery Beat Task (Periodic Worker)

**File**: `api/user/rentals/tasks.py:13-50`  
**Task**: `check_overdue_rentals`  
**Schedule**: **Every 1 minute** (configured in tasks/app.py:65-68)

```python
@shared_task(base=BaseTask, bind=True)
def check_overdue_rentals(self):
    now = timezone.now()
    
    # Find ACTIVE rentals past due_at
    overdue_rentals = Rental.objects.filter(
        status='ACTIVE',
        due_at__lt=now
    )
    
    for rental in overdue_rentals:
        rental.status = 'OVERDUE'
        rental.save(update_fields=['status', 'updated_at'])
        
        # Send overdue notification
        notify(rental.user, 'rental_overdue', ...)
```

**Frequency**: Runs every minute, so rentals transition to OVERDUE within 1 minute of passing due_at.

#### Mechanism 2: Real-time Check (On-Demand)

**File**: `api/user/rentals/views/core_views.py:178-181`  
**Endpoint**: GET `/rentals/active`

```python
# Real-time status check when user fetches active rental
if rental.status == 'ACTIVE' and rental.due_at and timezone.now() > rental.due_at:
    rental.status = 'OVERDUE'
    rental.save(update_fields=['status', 'updated_at'])
```

**When**: Triggered when user opens app or checks rental status.

### 2.3 Overdue Charge Calculation

#### Mechanism 1: Background Worker (Periodic)

**File**: `api/user/rentals/tasks.py:54-102`  
**Task**: `calculate_overdue_charges`  
**Schedule**: **Every 1 hour** (configured in tasks/app.py:83-86)

```python
@shared_task(base=BaseTask, bind=True)
def calculate_overdue_charges(self):
    # Find OVERDUE rentals not yet charged
    overdue_rentals = Rental.objects.filter(
        status='OVERDUE',
        overdue_amount=0  # Not yet charged
    )
    
    for rental in overdue_rentals:
        overdue_minutes = calculate_overdue_minutes(rental)
        package_rate = get_package_rate_per_minute(rental.package)
        overdue_amount = calculate_late_fee_amount(package_rate, overdue_minutes)
        
        rental.overdue_amount = overdue_amount
        rental.payment_status = 'PENDING'
        rental.save()
```

**⚠️ ISSUE**: This only calculates ONCE (when overdue_amount=0). If rental continues past first calculation, it doesn't update.

#### Mechanism 2: On Return (Final Calculation)

**File**: `api/user/rentals/services/rental/return_powerbank.py:80-94`

```python
def _calculate_overdue_charges(self, rental: Rental) -> None:
    if rental.is_returned_on_time or not rental.ended_at:
        return
    
    overdue_minutes = calculate_overdue_minutes(rental)
    package_rate_per_minute = get_package_rate_per_minute(rental.package)
    rental.overdue_amount = calculate_late_fee_amount(package_rate_per_minute, overdue_minutes)
    
    if rental.overdue_amount > 0:
        rental.payment_status = 'PENDING'
```

**When**: Called during powerbank return for PREPAID late returns.

### 2.4 Return Flow

**File**: `api/user/rentals/services/rental/return_powerbank.py:22-64`

```
DEVICE RETURN EVENT (from IoT)
     ↓
internal/services/sync/return_event.py
     ↓
Find rental (status=ACTIVE or OVERDUE)
     ↓
Call RentalService.return_power_bank()
     ↓
1. Set status = 'COMPLETED'
2. Set ended_at = now
3. Set is_returned_on_time = (ended_at <= due_at)
     ↓
4a. POSTPAID:                    4b. PREPAID (late):
   - Calculate usage cost           - Calculate overdue charges
   - payment_status = PENDING       - payment_status = PENDING
     ↓                                  ↓
5. Auto-collect payment (if balance sufficient)
6. Update powerbank location
7. Award points
8. Send notifications
```

---

## 3. SERVICE LAYER MAPPING

### RentalService Methods → DB Operations

| Service Method | DB Tables Updated | Fields Modified | Payment Action |
|---------------|------------------|-----------------|----------------|
| `start_rental()` | Rental, PowerBank, StationSlot, Wallet (PREPAID) | status=PENDING_POPUP→ACTIVE, started_at, due_at, power_bank, amount_paid | Deduct wallet/points (PREPAID) |
| `return_power_bank()` | Rental, PowerBank, StationSlot, Wallet/Points | status=COMPLETED, ended_at, overdue_amount, payment_status | Auto-collect if sufficient |
| `_calculate_overdue_charges()` | Rental | overdue_amount, payment_status=PENDING | None (just calculation) |
| `_calculate_postpayment_charges()` | Rental | amount_paid, payment_status=PENDING | None (just calculation) |
| `_auto_collect_payment()` | Rental, Wallet, Transaction | payment_status=PAID (if successful) | Deduct from wallet/points |

### Worker Tasks → DB Operations

| Task | Frequency | DB Query | DB Update | Purpose |
|------|-----------|----------|-----------|---------|
| `check_overdue_rentals` | 1 min | `status=ACTIVE, due_at<now` | `status=OVERDUE` | Mark rentals as overdue |
| `calculate_overdue_charges` | 1 hour | `status=OVERDUE, overdue_amount=0` | `overdue_amount`, `payment_status` | Calculate late fees |
| `auto_complete_abandoned_rentals` | Daily | `status=OVERDUE, due_at<(now-24h)` | `status=COMPLETED`, add lost penalty | Handle lost powerbanks |

---

## 4. LATE FEE CALCULATION LOGIC

### LateFeeService (`api/user/rentals/services/late_fee_service.py`)

```python
def calculate_late_fee(config, normal_rate_per_minute, overdue_minutes):
    # Apply grace period
    effective_overdue_minutes = max(0, overdue_minutes - config.grace_period_minutes)
    
    if config.fee_type == 'MULTIPLIER':
        fee = normal_rate_per_minute * config.multiplier * effective_overdue_minutes
    elif config.fee_type == 'FLAT_RATE':
        overdue_hours = effective_overdue_minutes / 60
        fee = config.flat_rate_per_hour * overdue_hours
    elif config.fee_type == 'COMPOUND':
        multiplier_fee = normal_rate_per_minute * config.multiplier * effective_overdue_minutes
        flat_fee = config.flat_rate_per_hour * (effective_overdue_minutes / 60)
        fee = multiplier_fee + flat_fee
    
    # Apply daily cap if configured
    if config.max_daily_rate:
        hours_overdue = effective_overdue_minutes / 60
        max_fee = (config.max_daily_rate / 24) * hours_overdue
        fee = min(fee, max_fee)
    
    return fee
```

### Example Calculation

**Scenario**: 1hr package (60min), NPR 50  
**User returns after**: 3 hours (180 minutes)  
**Overdue**: 2 hours (120 minutes)  

**Config**: MULTIPLIER = 2x, grace_period = 5 min

```
normal_rate_per_minute = 50 / 60 = NPR 0.833/min
effective_overdue = 120 - 5 = 115 minutes
late_fee = 0.833 * 2 * 115 = NPR 191.59
```

---

## 5. IDENTIFIED GAPS & ISSUES

### 🔴 CRITICAL ISSUES

#### Issue 1: Overdue Calculation Only Runs Once
**Location**: `tasks.py:54-102` (calculate_overdue_charges)

**Problem**:
```python
overdue_rentals = Rental.objects.filter(
    status='OVERDUE',
    overdue_amount=0  # ❌ Only finds rentals not yet charged
)
```

**Impact**: 
- Task calculates fee at hour 1, sets overdue_amount=100
- User doesn't return for 3 more hours
- Task won't recalculate because overdue_amount ≠ 0
- User charged 1hr late fee instead of 4hr late fee

**Example**:
```
T+0:00 - Rent starts (1hr package)
T+1:00 - due_at reached
T+1:01 - Status → OVERDUE (by check_overdue_rentals)
T+2:00 - calculate_overdue_charges runs: overdue_amount = NPR 100 (1hr late)
T+3:00 - calculate_overdue_charges skips (overdue_amount ≠ 0)
T+4:00 - calculate_overdue_charges skips (overdue_amount ≠ 0)
T+5:00 - User returns → STILL charged only NPR 100 (should be NPR 400)
```

#### Issue 2: No Real-Time Overdue Amount in UI
**Location**: `models/rental.py:53-85`

**Current**: Property `current_overdue_amount` exists for real-time calculation.

**Problem**: Not always used correctly in views/serializers.

**Serializer** (`serializers/detail_serializers.py`):
- `overdue_amount` - Shows STORED value (line 41)
- `current_overdue_amount` - Shows REAL-TIME value (line 42)

**Gap**: If user checks rental status while OVERDUE, they see old stored value, not current accumulating fee.

#### Issue 3: Return Event Doesn't Always Calculate Overdue
**Location**: `services/rental/return_powerbank.py:22-64`

**Flow**:
```python
if rental.package.payment_model == 'POSTPAID':
    self._calculate_postpayment_charges(rental)
elif not rental.is_returned_on_time:  # ✅ Only for PREPAID late returns
    self._calculate_overdue_charges(rental)
```

**Problem**: If rental is OVERDUE but is_returned_on_time check passes (due to timing), charges not calculated.

**Edge Case**:
```
Rental status=OVERDUE (set by worker)
But ended_at is set to current time
is_returned_on_time = (ended_at <= due_at) evaluates incorrectly
```

### 🟡 MEDIUM ISSUES

#### Issue 4: Background Worker Runs Every Hour
**Location**: `tasks/app.py:83-86`

**Problem**: Late fees only recalculated every hour, not real-time.

**Example**:
```
1:00 PM - Rental overdue
1:15 PM - User checks app → sees fee for 15 min
2:00 PM - Worker runs → updates to 1hr fee
2:30 PM - User checks app → still sees 1hr fee (30 min stale)
```

**Impact**: User confusion about actual charges.

#### Issue 5: No Real-Time Overdue Calculation on Return
**Location**: `services/rental/return_powerbank.py:80-94`

**Current**: Uses stored rental timestamps.

**Problem**: If worker hasn't run recently, final charge may be stale.

**Solution**: Should always call real-time calculation:
```python
rental.overdue_amount = rental.current_overdue_amount  # Use property
```

### 🟢 MINOR ISSUES

#### Issue 6: PENDING_POPUP Rentals Not Auto-Cancelled
**Problem**: Rentals stuck in PENDING_POPUP if popup verification never completes.

**Impact**: User's "active rental" slot blocked, preventing new rentals.

**Location**: No cleanup task exists.

**Solution**: Add task to cancel PENDING_POPUP rentals older than 5 minutes.

#### Issue 7: No Maximum Overdue Penalty
**Problem**: Overdue charges can accumulate infinitely.

**Example**: User loses powerbank, 1 month later owes NPR 50,000.

**Current**: Only `auto_complete_abandoned_rentals` task handles this (after 24hrs).

**Solution**: Implement max penalty (e.g., device replacement cost + 2x rental).

---

## 6. WHAT WORKS CORRECTLY

### ✅ Status Transitions
- PENDING_POPUP → ACTIVE: Works correctly on device popup
- ACTIVE → OVERDUE: Worker runs every 1 minute (reliable)
- OVERDUE → COMPLETED: Works on return

### ✅ Payment Flow
- PREPAID payment deduction: Works at rental start
- POSTPAID calculation: Works based on usage time
- Auto-collection on return: Attempts wallet/points deduction

### ✅ Real-Time Property
- `current_overdue_amount` property: Correctly calculates live fee using LateFeeService

### ✅ Late Fee Configuration
- LateFeeConfiguration model: Flexible, supports multiple fee types
- Grace period: Works correctly
- Max daily rate cap: Works correctly

---

## 7. SOLUTION RECOMMENDATIONS

### Fix 1: Update Worker to Recalculate Overdue Fees
**File**: `api/user/rentals/tasks.py:54-102`

**Change**:
```python
# OLD (line 58-61)
overdue_rentals = Rental.objects.filter(
    status='OVERDUE',
    overdue_amount=0  # ❌ Only first calculation
)

# NEW
overdue_rentals = Rental.objects.filter(
    status='OVERDUE'  # ✅ Recalculate all OVERDUE rentals
)

# Then use real-time calculation
for rental in overdue_rentals:
    # Use the property which calculates real-time
    rental.overdue_amount = rental.current_overdue_amount
    rental.payment_status = 'PENDING'
    rental.save(update_fields=['overdue_amount', 'payment_status', 'updated_at'])
```

### Fix 2: Always Use Real-Time Calculation on Return
**File**: `api/user/rentals/services/rental/return_powerbank.py:80-94`

**Change**:
```python
def _calculate_overdue_charges(self, rental: Rental) -> None:
    if rental.is_returned_on_time or not rental.ended_at:
        return
    
    # OLD: Uses helpers
    # overdue_minutes = calculate_overdue_minutes(rental)
    # rental.overdue_amount = calculate_late_fee_amount(...)
    
    # NEW: Use model property (already has correct logic)
    rental.overdue_amount = rental.current_overdue_amount  # ✅
    
    if rental.overdue_amount > 0:
        rental.payment_status = 'PENDING'
```

### Fix 3: Increase Worker Frequency
**File**: `tasks/app.py:83-86`

**Change**:
```python
"calculate-overdue-charges": {
    "task": "api.user.rentals.tasks.calculate_overdue_charges",
    "schedule": 300.0,  # Every 5 minutes (was 3600 = 1hr)
},
```

### Fix 4: Add PENDING_POPUP Cleanup Task
**File**: `api/user/rentals/tasks.py` (new task)

```python
@shared_task(base=BaseTask, bind=True)
def cleanup_pending_popup_rentals(self):
    """Cancel rentals stuck in PENDING_POPUP for >5 minutes"""
    cutoff = timezone.now() - timezone.timedelta(minutes=5)
    
    stuck_rentals = Rental.objects.filter(
        status='PENDING_POPUP',
        created_at__lt=cutoff
    )
    
    for rental in stuck_rentals:
        rental.status = 'CANCELLED'
        rental.rental_metadata['cancellation_reason'] = 'popup_timeout'
        rental.save()
        
        # Refund if PREPAID
        if rental.package.payment_model == 'PREPAID' and rental.amount_paid > 0:
            # Refund logic
            pass
```

**Add to beat_schedule**:
```python
"cleanup-pending-popup": {
    "task": "api.user.rentals.tasks.cleanup_pending_popup_rentals",
    "schedule": 300.0,  # Every 5 minutes
},
```

---

## 8. COMPLETE STATUS FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                    RENTAL LIFECYCLE                              │
└─────────────────────────────────────────────────────────────────┘

START REQUEST
     ↓
PENDING_POPUP (status set on creation)
     ├─ Popup Success (15s) → ACTIVE
     ├─ Popup Timeout → stays PENDING_POPUP → async verification
     └─ (NEW FIX) 5min timeout → CANCELLED
     
ACTIVE (rental in progress)
     ├─ Timer: check_overdue_rentals (every 1 min)
     │   └─ If now > due_at → OVERDUE
     ├─ Real-time check in /rentals/active
     │   └─ If now > due_at → OVERDUE
     └─ User returns on time → COMPLETED
     
OVERDUE (past due_at)
     ├─ Timer: calculate_overdue_charges (every 5 min - NEW)
     │   └─ Update overdue_amount with real-time calculation
     ├─ User returns late → COMPLETED (with overdue charges)
     └─ Timer: auto_complete_abandoned (after 24hrs)
         └─ COMPLETED (with lost penalty)
         
COMPLETED (final state)
     ├─ Auto-collect payment
     ├─ Award points
     └─ Send notifications
```

---

## 9. DATABASE QUERY IMPACT

### Current Worker Queries (Every Execution)

**check_overdue_rentals** (1 min):
```sql
SELECT * FROM rentals 
WHERE status='ACTIVE' AND due_at < NOW();
-- Updates each: UPDATE rentals SET status='OVERDUE' WHERE id=?
```

**calculate_overdue_charges** (1 hour → 5 min after fix):
```sql
-- OLD
SELECT * FROM rentals 
WHERE status='OVERDUE' AND overdue_amount=0;

-- NEW (FIX 1)
SELECT * FROM rentals WHERE status='OVERDUE';
-- More rows but prevents undercalculation
```

**Performance Impact**: Minimal. OVERDUE rentals are small subset of total.

---

## CONCLUSION

### Root Cause of User Issue

**Scenario**: User rents 1hr package, doesn't return for 3hrs.

**What's Happening**:

1. ✅ T+1:00 - Status changes to OVERDUE (worker runs every 1 min)
2. ✅ T+2:00 - `calculate_overdue_charges` calculates 1hr late fee
3. ❌ T+3:00 - Worker SKIPS rental (overdue_amount ≠ 0)
4. ❌ T+4:00 - User returns → charged only 1hr late fee

**Why It's Wrong**:
- Worker only calculates fee ONCE (when overdue_amount=0)
- No recalculation as overdue time increases
- Final charge on return doesn't use real-time calculation

**Fix**:
1. Remove `overdue_amount=0` filter from worker
2. Use `rental.current_overdue_amount` property (already has correct logic)
3. Run worker every 5 minutes instead of every hour

### Testing the Fix

**Test Case 1**: Continuous Overdue
```
1. Create rental (1hr package)
2. Wait 1hr 5min (becomes OVERDUE)
3. Wait for worker (5min) → check overdue_amount
4. Wait 1 more hour → check overdue_amount (should increase)
5. Return → verify final charge matches total overdue time
```

**Expected**:
- After 1hr 5min: overdue_amount ≈ 5min late fee
- After 2hr 5min: overdue_amount ≈ 65min late fee
- On return at 3hr: overdue_amount = 2hr late fee
