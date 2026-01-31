# Rental Start Service Refactoring & Transaction/Revenue Integration Plan

> **Version:** 1.0  
> **Created:** 2026-01-30  
> **Status:** REVIEW REQUIRED - Awaiting approval before implementation

---

## Executive Summary

This plan addresses:
1. **Refactoring `start.py`** - Split the monolithic `RentalStartMixin` into manageable components
2. **Transaction Creation Gap** - Create RENTAL transaction when rental starts (currently only on payment)
3. **Revenue Distribution Integration** - Trigger revenue distribution after transaction completion
4. **Vendor Free Ejection** - Support BR13.2 (1 free powerbank ejection per day for vendors)

---

## Part 1: Current State Analysis

### 1.1 Current `start.py` Structure (341 lines)

**File:** `api/user/rentals/services/rental/start.py`

```
RentalStartMixin
├── start_rental()                    [Main entry - ~90 lines]
├── _trigger_device_popup()           [~55 lines]
├── _validate_rental_prerequisites()  [~25 lines]
├── _validate_station_availability()  [~7 lines]
├── _validate_postpaid_balance()      [~18 lines]
├── _get_available_power_bank_and_slot() [~18 lines]
└── _process_prepayment()             [~25 lines]
```

**Problems:**
- Single file doing too many things (validation, payment, device control, discount, notifications)
- Hard to test individual components
- Mixing concerns: business logic + payment + device communication

### 1.2 Current Transaction Flow

**Current Flow:**
```
start_rental() → _process_prepayment() → RentalPaymentService.process_rental_payment()
                                          └── TransactionRepository.create(type='RENTAL')
```

**Issues:**
1. Transaction is created ONLY in `_process_prepayment()` (PREPAID model only)
2. POSTPAID rentals don't create transaction at start - only at return via `pay_rental_due()`
3. No link between Transaction and RevenueDistribution at rental start

### 1.3 Current Revenue Distribution State

**RevenueDistribution Model:** Exists in `api/partners/common/models/revenue_distribution.py`
**Repository:** Exists in `api/partners/common/repositories/revenue_distribution_repository.py`

**Gap:** NO code currently creates RevenueDistribution records. The repository has `create()` method but it's never called.

---

## Part 2: Transaction Type Analysis

### 2.1 Transaction Types & When They Should Be Created

| Transaction Type | When Created | Current Status | Action Needed |
|------------------|--------------|----------------|---------------|
| `TOPUP` | User adds money to wallet | Working | None |
| `RENTAL` | Rental starts (prepayment) | Partial | Fix POSTPAID gap |
| `RENTAL_DUE` | Rental return with dues | Working | None |
| `REFUND` | Cancellation/dispute refund | Working | None |
| `FINE` | Policy violation | Working | None |
| `ADVERTISEMENT` | Ad-related payment | Working | None |

### 2.2 Transaction Status Flow for RENTAL

```
RENTAL Transaction Lifecycle:
┌─────────────────────────────────────────────────────────────────────────┐
│ PREPAID Model:                                                          │
│ start_rental() → Transaction(status=SUCCESS) → RevenueDistribution      │
│                                                                         │
│ POSTPAID Model:                                                         │
│ start_rental() → Transaction(status=PENDING)                            │
│ return_power_bank() → Update Transaction(status=SUCCESS)                │
│                    → Create RevenueDistribution                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Payment Method Types

| Type | Description | Used When |
|------|-------------|-----------|
| `WALLET` | Wallet balance only | Wallet payment without points |
| `POINTS` | Points only | Points-only payment |
| `COMBINATION` | Wallet + Points | Mixed payment |
| `GATEWAY` | External payment gateway | Future use (not implemented) |

---

## Part 3: Revenue Distribution Integration

### 3.1 Business Rules Summary (from Business Rules.md)

- **BR4.1-3:** ALL transactions collected by ChargeGhar
- **BR5.1-5:** VAT & Service Charge deducted ONLY at ChargeGhar level
- **BR6.1-3:** ChargeGhar station revenue distribution
- **BR7.1-5:** Franchise station revenue distribution
- **BR11.1-5:** All calculations use Net Revenue

### 3.2 Revenue Distribution Trigger Point

**When to create RevenueDistribution:**
- PREPAID: Immediately after successful `start_rental()` (transaction already SUCCESS)
- POSTPAID: After `return_power_bank()` when payment is collected (transaction becomes SUCCESS)

**Key Rule:** RevenueDistribution is created ONLY when Transaction.status = SUCCESS

### 3.3 Revenue Calculation Flow

```
Transaction SUCCESS
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. Get station from rental                                       │
│ 2. Look up StationDistribution for this station                  │
│ 3. Determine hierarchy:                                          │
│    - CHARGEGHAR_TO_FRANCHISE → franchise_id                      │
│    - *_TO_VENDOR → vendor_id (+ franchise_id if sub-vendor)      │
│ 4. Get revenue shares from:                                      │
│    - Franchise: partners.revenue_share_percent                   │
│    - Vendor: station_revenue_shares.partner_percent/fixed_amount │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. Calculate shares:                                             │
│    vat_amount = gross * VAT_PERCENT / 100                        │
│    service_charge = gross * SERVICE_CHARGE_PERCENT / 100         │
│    net_amount = gross - vat_amount - service_charge              │
│    [Apply scenario-specific share logic]                         │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. Create RevenueDistribution record                             │
│ 7. Update partners.balance and partners.total_earnings           │
│ 8. Mark is_distributed = TRUE                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Proposed File Structure (Refactoring)

### 4.1 New Directory Structure

```
api/user/rentals/services/rental/
├── __init__.py              # RentalService (unchanged - uses mixins)
├── start/                   # NEW: Split start operations
│   ├── __init__.py          # RentalStartMixin (simplified orchestrator)
│   ├── validation.py        # Validation logic
│   ├── payment.py           # Payment processing
│   ├── device.py            # Device popup operations
│   ├── discount.py          # Discount calculation
│   ├── vendor_ejection.py   # Vendor free ejection (BR13.2)
│   └── revenue.py           # Revenue distribution trigger
├── cancel.py                # (unchanged)
├── extend.py                # (unchanged)
├── return_powerbank.py      # Minor update for revenue distribution
├── queries.py               # (unchanged)
└── notifications.py         # (unchanged)
```

### 4.2 File Responsibilities

| File | Responsibility | Lines (est) |
|------|----------------|-------------|
| `start/__init__.py` | Orchestrator - calls other modules | ~80 |
| `start/validation.py` | User/station/balance validation | ~60 |
| `start/payment.py` | Transaction creation, payment processing | ~80 |
| `start/device.py` | Device popup, async verification | ~60 |
| `start/discount.py` | Discount lookup and calculation | ~40 |
| `start/vendor_ejection.py` | Vendor free ejection check (BR13.2) | ~50 |
| `start/revenue.py` | Revenue distribution creation | ~100 |

---

## Part 5: Detailed Implementation Plan

### 5.1 Phase 1: Create Revenue Distribution Service

**New File:** `api/partners/common/services/revenue_distribution_service.py`

**Purpose:** Centralize all revenue calculation and distribution logic

**Methods:**
```python
class RevenueDistributionService(BaseService):
    def create_revenue_distribution(
        self, 
        transaction: Transaction, 
        rental: Rental
    ) -> RevenueDistribution:
        """Main entry point - creates revenue distribution for a transaction"""
        
    def _get_station_hierarchy(self, station_id: str) -> dict:
        """Get franchise/vendor hierarchy for station"""
        
    def _calculate_shares(
        self, 
        gross_amount: Decimal, 
        franchise: Optional[Partner], 
        vendor: Optional[Partner]
    ) -> dict:
        """Calculate all share amounts"""
        
    def _update_partner_balances(
        self, 
        distribution: RevenueDistribution
    ) -> None:
        """Update franchise/vendor balances"""
```

### 5.2 Phase 2: Refactor start.py into Modules

**Step 2.1: Create `start/validation.py`**
- Move `_validate_rental_prerequisites()`
- Move `_validate_station_availability()`
- Move `_validate_postpaid_balance()`
- Move `_get_available_power_bank_and_slot()`

**Step 2.2: Create `start/payment.py`**
- Move `_process_prepayment()`
- Add `_create_rental_transaction()` for consistent transaction creation
- Handle both PREPAID and POSTPAID transaction creation

**Step 2.3: Create `start/device.py`**
- Move `_trigger_device_popup()`

**Step 2.4: Create `start/discount.py`**
- Move discount lookup and calculation logic from `start_rental()`

**Step 2.5: Create `start/vendor_ejection.py`**
- Add `check_vendor_free_ejection(user, station)` - BR13.2
- Add `log_vendor_free_ejection(user, station, rental, powerbank)` - BR13.2

**Step 2.6: Create `start/revenue.py`**
- Add `trigger_revenue_distribution(transaction, rental)` - wrapper for service

**Step 2.7: Create `start/__init__.py`**
- Simplified `RentalStartMixin` that orchestrates calls to other modules

### 5.3 Phase 3: Update Transaction Creation

**Current Problem:**
- PREPAID: Transaction created but not explicitly linked to revenue
- POSTPAID: No transaction at start

**Solution:**

```python
# In start/payment.py

def create_rental_transaction(
    self, 
    user, 
    rental: Rental, 
    amount: Decimal, 
    payment_model: str,  # 'PREPAID' or 'POSTPAID'
    payment_breakdown: Optional[dict] = None
) -> Transaction:
    """
    Create RENTAL transaction.
    
    PREPAID: status=SUCCESS, deduct payment immediately
    POSTPAID: status=PENDING, no payment deduction
    """
    if payment_model == 'PREPAID':
        status = 'SUCCESS'
        # Process actual payment
        self._deduct_payment(user, payment_breakdown)
    else:
        status = 'PENDING'
    
    payment_method = self._determine_payment_method(payment_breakdown)
    
    transaction = TransactionRepository.create(
        user=user,
        transaction_id=generate_transaction_id(),
        transaction_type='RENTAL',
        amount=amount,
        status=status,
        payment_method_type=payment_method,
        related_rental=rental
    )
    
    return transaction
```

### 5.4 Phase 4: Integrate Revenue Distribution

**In `start/__init__.py`:**

```python
# After successful rental activation (popup success)
if package.payment_model == 'PREPAID':
    # Transaction already SUCCESS, create revenue distribution
    from .revenue import trigger_revenue_distribution
    trigger_revenue_distribution(transaction, rental)
```

**In `return_powerbank.py`:**

```python
# After successful payment collection (POSTPAID or late fees)
if transaction.status == 'SUCCESS':
    from api.partners.common.services import RevenueDistributionService
    rev_service = RevenueDistributionService()
    rev_service.create_revenue_distribution(transaction, rental)
```

### 5.5 Phase 5: Vendor Free Ejection Integration (BR13.2)

**In `start/vendor_ejection.py`:**

```python
from api.partners.common.models import PartnerIotHistory
from api.partners.common.repositories import StationDistributionRepository

def check_vendor_free_ejection(user, station) -> bool:
    """
    Check if user is a vendor for this station with free ejection available.
    Returns True if vendor can use free ejection today.
    """
    if not hasattr(user, 'partner_profile'):
        return False
    
    partner = user.partner_profile
    if partner.partner_type != 'VENDOR':
        return False
    
    # Check if vendor operates this station
    distribution = StationDistributionRepository.get_station_vendor(str(station.id))
    if not distribution or distribution.id != partner.id:
        return False
    
    # Check daily limit
    today = timezone.now().date()
    used_today = PartnerIotHistory.objects.filter(
        partner=partner,
        action_type='EJECT',
        is_free_ejection=True,
        created_at__date=today
    ).exists()
    
    return not used_today


def log_vendor_free_ejection(user, station, rental, powerbank) -> PartnerIotHistory:
    """Log free ejection to partner_iot_history after successful rental start"""
    from api.partners.common.models import PartnerIotHistory
    
    return PartnerIotHistory.objects.create(
        partner=user.partner_profile,
        performed_by=user,
        station=station,
        action_type='EJECT',
        performed_from='MOBILE_APP',
        powerbank_sn=powerbank.serial_number,
        slot_number=rental.slot.slot_number if rental.slot else None,
        rental=rental,
        is_free_ejection=True,
        is_successful=True
    )
```

---

## Part 6: Data Flow Diagrams

### 6.1 PREPAID Rental Flow (Updated)

```
User Request: POST /api/user/rentals/start
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. VALIDATION (start/validation.py)                              │
│    ├── _validate_rental_prerequisites(user)                      │
│    ├── _validate_station_availability(station)                   │
│    └── _get_available_power_bank_and_slot(station)               │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. DISCOUNT (start/discount.py)                                  │
│    └── get_applicable_discount(station_sn, package_id, user)     │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. CREATE RENTAL (status=PENDING_POPUP)                          │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. PAYMENT (start/payment.py) - PREPAID                          │
│    ├── create_rental_transaction(status=SUCCESS)                 │
│    └── _deduct_payment(wallet, points)                           │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. DEVICE POPUP (start/device.py)                                │
│    └── _trigger_device_popup()                                   │
└──────────────────────────────────────────────────────────────────┘
       │
       ├─── SUCCESS ───┐
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 6. ACTIVATE RENTAL (status=ACTIVE)                    │
       │   │    ├── Update rental with actual powerbank            │
       │   │    ├── Record discount usage                          │
       │   │    └── Check vendor free ejection                     │
       │   └───────────────────────────────────────────────────────┘
       │               │
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 7. REVENUE DISTRIBUTION (start/revenue.py)            │
       │   │    └── trigger_revenue_distribution(transaction)      │
       │   │        ├── Calculate VAT, Service Charge              │
       │   │        ├── Calculate franchise/vendor shares          │
       │   │        ├── Create RevenueDistribution record          │
       │   │        └── Update partner balances                    │
       │   └───────────────────────────────────────────────────────┘
       │               │
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 8. NOTIFICATIONS                                      │
       │   │    ├── _send_rental_started_notification()            │
       │   │    └── _schedule_reminder_notification()              │
       │   └───────────────────────────────────────────────────────┘
       │
       └─── FAILURE ───┐
                       ▼
           ┌───────────────────────────────────────────────────────┐
           │ Schedule async verification task                      │
           │ Rental stays in PENDING_POPUP                         │
           └───────────────────────────────────────────────────────┘
```

### 6.2 POSTPAID Rental Flow (Updated)

```
START:
┌──────────────────────────────────────────────────────────────────┐
│ Same as PREPAID steps 1-3                                        │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. PAYMENT (start/payment.py) - POSTPAID                         │
│    └── create_rental_transaction(status=PENDING)                 │
│        [NO payment deduction at start]                           │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5-6. DEVICE POPUP + ACTIVATE (same as PREPAID)                   │
│      [NO revenue distribution yet - transaction is PENDING]      │
└──────────────────────────────────────────────────────────────────┘

RETURN:
┌──────────────────────────────────────────────────────────────────┐
│ return_power_bank()                                              │
│    ├── Calculate usage charges                                   │
│    ├── _auto_collect_payment()                                   │
│    │   └── pay_rental_due() → Transaction(status=SUCCESS)        │
│    └── trigger_revenue_distribution() [NEW]                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Files to Create/Modify

### 7.1 New Files to Create

| File | Purpose |
|------|---------|
| `api/user/rentals/services/rental/start/__init__.py` | Simplified orchestrator |
| `api/user/rentals/services/rental/start/validation.py` | Validation logic |
| `api/user/rentals/services/rental/start/payment.py` | Payment/transaction |
| `api/user/rentals/services/rental/start/device.py` | Device popup |
| `api/user/rentals/services/rental/start/discount.py` | Discount logic |
| `api/user/rentals/services/rental/start/vendor_ejection.py` | BR13.2 support |
| `api/user/rentals/services/rental/start/revenue.py` | Revenue trigger |
| `api/partners/common/services/__init__.py` | Services init |
| `api/partners/common/services/revenue_distribution_service.py` | Revenue calculation |

### 7.2 Files to Modify

| File | Changes |
|------|---------|
| `api/user/rentals/services/rental/__init__.py` | Update import from `start/` |
| `api/user/rentals/services/rental/return_powerbank.py` | Add revenue distribution trigger |
| `api/user/payments/services/rental_payment.py` | Return transaction from methods |

### 7.3 Files to Delete (after refactoring)

| File | Reason |
|------|--------|
| `api/user/rentals/services/rental/start.py` | Replaced by `start/` directory |

---

## Part 8: Testing Strategy

### 8.1 Unit Tests Required

| Test File | Coverage |
|-----------|----------|
| `test_rental_start_validation.py` | Validation module |
| `test_rental_start_payment.py` | Payment module |
| `test_rental_start_device.py` | Device popup |
| `test_rental_start_discount.py` | Discount calculation |
| `test_vendor_ejection.py` | BR13.2 free ejection |
| `test_revenue_distribution_service.py` | Share calculations |

### 8.2 Integration Tests

| Scenario | Expected Outcome |
|----------|------------------|
| PREPAID rental at CG station | Transaction SUCCESS, RevenueDistribution with chargeghar_share=100% |
| PREPAID rental at Franchise station | Transaction SUCCESS, RevenueDistribution with franchise_share |
| PREPAID rental at Vendor station | Transaction SUCCESS, RevenueDistribution with vendor_share |
| POSTPAID rental start | Transaction PENDING, NO RevenueDistribution |
| POSTPAID rental return | Transaction SUCCESS, RevenueDistribution created |
| Vendor starts rental at own station | Free ejection logged in partner_iot_history |

---

## Part 9: Rollback Plan

If issues occur after deployment:

1. **Quick Rollback:** Revert to original `start.py` file (git revert)
2. **Data Consistency:** RevenueDistribution records are additive - no data loss on rollback
3. **Partner Balances:** Can be recalculated from revenue_distributions if needed

---

## Part 10: Implementation Order

### Phase 1: Foundation (No Breaking Changes)
1. Create `RevenueDistributionService`
2. Create `start/` directory with empty files
3. Test revenue calculation logic in isolation

### Phase 2: Refactoring (Internal Changes)
4. Create `start/validation.py` - copy methods
5. Create `start/payment.py` - copy + enhance
6. Create `start/device.py` - copy methods
7. Create `start/discount.py` - extract logic
8. Create `start/vendor_ejection.py` - new feature
9. Create `start/revenue.py` - new integration
10. Create `start/__init__.py` - new orchestrator
11. Update `rental/__init__.py` import

### Phase 3: Integration
12. Update `return_powerbank.py` for POSTPAID revenue
13. Test full flow
14. Delete old `start.py`

---

## Part 11: Open Questions

Before proceeding, please confirm:

1. **POSTPAID Transaction at Start:** Should we create a PENDING transaction when POSTPAID rental starts, or continue creating it only at return?
   - **Recommendation:** Create PENDING transaction at start for consistent tracking

2. **Revenue Distribution Timing:** 
   - PREPAID: Create immediately after rental activates?
   - POSTPAID: Create after payment succeeds at return?
   - **Recommendation:** Yes to both

3. **Vendor Free Ejection Scope:**
   - Should vendor free ejection work ONLY at their assigned station?
   - Should it work at ANY station?
   - **Recommendation:** Only their assigned station (per BR13.2)

4. **Fixed Amount Vendors:**
   - For FIXED revenue model, should vendor_share in RevenueDistribution be 0?
   - **Recommendation:** Yes, vendor_share=0 for FIXED model (tracked separately monthly)

---

## Approval Checklist

Please confirm the following before implementation:

- [ ] File structure approach approved
- [ ] Transaction creation timing confirmed
- [ ] Revenue distribution trigger points confirmed
- [ ] Vendor free ejection scope confirmed
- [ ] Fixed amount vendor handling confirmed
- [ ] Testing strategy approved

---

## Next Steps After Approval

1. I will implement Phase 1 (RevenueDistributionService)
2. You review the service implementation
3. Proceed with Phase 2-3 incrementally
4. Test each phase before proceeding

---

**Awaiting your review and approval.**
