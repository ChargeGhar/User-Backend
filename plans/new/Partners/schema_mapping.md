# Partnership System - Schema Field Lifecycle Mapping

> **Version:** 1.1  
> **Last Updated:** 2026-01-24  
> **Status:** Cross-verified with schema.md v1.1 - READY FOR IMPLEMENTATION

---

## Purpose

This document maps how each schema table field gets:
1. **Created** - Which endpoint/system creates the record
2. **Updated** - Which endpoint/system modifies the field
3. **Read** - Which endpoints query this data

This helps identify gaps, redundancies, and ensures 100% accuracy before implementation.

---

## Table 1: partners

### Field Lifecycle

| Field | Created By | Updated By | Read By |
|-------|------------|------------|---------|
| `id` | System (auto) | Never | All endpoints |
| `created_at` | System (auto) | Never | All endpoints |
| `updated_at` | System (auto) | System (auto on update) | All endpoints |
| `user_id` | Admin/Franchise (POST partner) | Never (immutable) | All endpoints |
| `partner_type` | Admin/Franchise (POST partner) | Never (immutable) | All endpoints |
| `vendor_type` | Admin/Franchise (POST vendor) | Admin/Franchise (PATCH) | All endpoints |
| `parent_id` | System (based on creator) | Never (immutable) | Hierarchy queries |
| `code` | System (auto-generate) | Never | All endpoints |
| `business_name` | Admin/Franchise (POST) | Admin/Franchise/Self (PATCH profile) | All endpoints |
| `contact_phone` | Admin/Franchise (POST) | Admin/Franchise/Self (PATCH profile) | All endpoints |
| `contact_email` | Admin/Franchise (POST) | Admin/Franchise/Self (PATCH profile) | All endpoints |
| `address` | Admin/Franchise (POST) | Admin/Franchise/Self (PATCH profile) | All endpoints |
| `status` | System (default ACTIVE) | Admin/Franchise (PATCH status) | All endpoints |
| `upfront_amount` | Admin (POST franchise) | Admin (PATCH) | Admin, Franchise profile |
| `revenue_share_percent` | Admin (POST franchise) | Admin (PATCH) | Revenue calculations |
| `balance` | System (default 0) | System (revenue distribution + payout) | Dashboard endpoints |
| `total_earnings` | System (default 0) | System (revenue distribution) | Dashboard endpoints |
| `assigned_by_id` | System (current user) | Never | Admin audit |
| `assigned_at` | System (auto) | Never | Admin audit |
| `notes` | Admin/Franchise (POST) | Admin/Franchise (PATCH) | Admin/Franchise |

### Creation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/admin/partners/franchise/                             │
│ POST /api/admin/partners/vendor/                                │
│ POST /api/partner/franchise/vendors/                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Service Layer Validation:                                       │
│ 1. User exists and not already a partner                        │
│ 2. If VENDOR: parent is valid (NULL or Franchise)               │
│ 3. If VENDOR: station_id provided and available                 │
│ 4. If REVENUE vendor: revenue_model provided                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ INSERT partners:                                                │
│ - Generate code (FR-XXX or VN-XXX)                              │
│ - Set parent_id based on creator                                │
│ - Set assigned_by_id = current_user.id                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ If station assignment needed:                                   │
│ → Create station_distributions record                           │
│ → If REVENUE vendor: Create station_revenue_shares record       │
└─────────────────────────────────────────────────────────────────┘
```

### Balance Update Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Trigger: Transaction completed on partner's station             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ System creates revenue_distributions record                     │
│ Calculate shares based on hierarchy                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ UPDATE partners SET                                             │
│   balance = balance + partner_share,                            │
│   total_earnings = total_earnings + partner_share               │
│ WHERE id IN (franchise_id, vendor_id)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ When payout completed:                                          │
│ UPDATE partners SET balance = balance - payout_amount           │
│ WHERE id = partner_id                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table 2: station_distributions

### Field Lifecycle

| Field | Created By | Updated By | Read By |
|-------|------------|------------|---------|
| `id` | System (auto) | Never | All endpoints |
| `created_at` | System (auto) | Never | All endpoints |
| `updated_at` | System (auto) | System (auto) | All endpoints |
| `station_id` | Admin/Franchise (POST) | Never (create new record instead) | All endpoints |
| `partner_id` | Admin/Franchise (POST) | Never (create new record instead) | All endpoints |
| `distribution_type` | System (based on hierarchy) | Never | Queries |
| `effective_date` | Admin/Franchise (POST, default today) | Never | Queries |
| `expiry_date` | Never (on creation) | Admin/Franchise (on reassignment) | Queries |
| `is_active` | System (default TRUE) | System (on deactivation) | All active queries |
| `assigned_by_id` | System (current user) | Never | Audit |
| `notes` | Admin/Franchise (POST) | Admin/Franchise (PATCH) | Admin |

### Distribution Type Logic

```
┌─────────────────────────────────────────────────────────────────┐
│ Determine distribution_type automatically:                      │
├─────────────────────────────────────────────────────────────────┤
│ IF creator is Admin:                                            │
│   IF partner.partner_type == 'FRANCHISE':                       │
│     → distribution_type = 'CHARGEGHAR_TO_FRANCHISE'             │
│   ELSE IF partner.partner_type == 'VENDOR':                     │
│     → distribution_type = 'CHARGEGHAR_TO_VENDOR'                │
│                                                                 │
│ ELSE IF creator is Franchise:                                   │
│   IF partner.partner_type == 'VENDOR':                          │
│     → distribution_type = 'FRANCHISE_TO_VENDOR'                 │
└─────────────────────────────────────────────────────────────────┘
```

### Station Reassignment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ When station is reassigned to different partner:                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. UPDATE existing distribution:                                │
│    SET is_active = FALSE, expiry_date = TODAY                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. INSERT new distribution record                               │
│    (keeps history intact)                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table 3: station_revenue_shares

### Field Lifecycle

| Field | Created By | Updated By | Read By |
|-------|------------|------------|---------|
| `id` | System (auto) | Never | All endpoints |
| `created_at` | System (auto) | Never | All endpoints |
| `updated_at` | System (auto) | System (auto) | All endpoints |
| `distribution_id` | System (on partner creation) | Never (1:1 with distribution) | Revenue calc |
| `revenue_model` | Admin/Franchise (POST vendor) | Admin/Franchise (PATCH) | Revenue calc |
| `partner_percent` | Admin/Franchise (POST/PATCH) | Admin/Franchise (PATCH) | Revenue calc |
| `fixed_amount` | Admin/Franchise (POST/PATCH) | Admin/Franchise (PATCH) | Revenue calc |

### Creation Rules

```
┌─────────────────────────────────────────────────────────────────┐
│ station_revenue_shares is ONLY created when:                    │
│                                                                 │
│ 1. Partner is VENDOR with vendor_type = 'REVENUE'               │
│ 2. Station distribution is created                              │
│                                                                 │
│ NOT created for:                                                │
│ - FRANCHISE (uses partners.revenue_share_percent instead)       │
│ - NON_REVENUE vendors (no revenue model)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table 4: revenue_distributions

### Field Lifecycle

| Field | Created By | Updated By | Read By |
|-------|------------|------------|---------|
| `id` | System (auto) | Never | All endpoints |
| `created_at` | System (auto) | Never | All endpoints |
| `updated_at` | System (auto) | System (auto) | All endpoints |
| `transaction_id` | System (on rental complete) | Never | Transaction queries |
| `rental_id` | System (on rental complete) | Never | Transaction queries |
| `station_id` | System (from rental) | Never | Station queries |
| `gross_amount` | System (from transaction) | Never | Financial reports |
| `vat_amount` | System (calculated) | Never | Financial reports |
| `service_charge` | System (calculated) | Never | Financial reports |
| `net_amount` | System (calculated) | Never | Financial reports |
| `chargeghar_share` | System (calculated) | Never | Financial reports |
| `franchise_id` | System (from station lookup) | Never | Franchise queries |
| `franchise_share` | System (calculated) | Never | Financial reports |
| `vendor_id` | System (from station lookup) | Never | Vendor queries |
| `vendor_share` | System (calculated) | Never | Financial reports |
| `is_distributed` | System (default FALSE) | System (on balance update) | Pending distribution |
| `distributed_at` | Never (on creation) | System (on balance update) | Audit |
| `calculation_details` | System (JSON breakdown) | Never | Audit |
| `is_reversal` | System (default FALSE) | Never | Reversal queries |
| `reversed_distribution_id` | System (on reversal creation) | Never | Audit trail |
| `reversal_reason` | System (on reversal creation) | Never | Audit trail |

### System Trigger: On Transaction Complete

```
┌─────────────────────────────────────────────────────────────────┐
│ Trigger: POST /api/rentals/return OR rental auto-complete       │
│ When: Transaction status = COMPLETED                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Get station from rental                                      │
│ 2. Find active station_distribution for station                 │
│ 3. Get partner hierarchy:                                       │
│    - If CHARGEGHAR_TO_FRANCHISE: get franchise                  │
│    - If *_TO_VENDOR: get vendor + maybe franchise               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Calculate shares:                                            │
│    vat_amount = gross * VAT_PERCENT / 100                       │
│    service_charge = gross * SERVICE_CHARGE_PERCENT / 100        │
│    net_amount = gross - vat_amount - service_charge             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Apply hierarchy rules (see calculation scenarios below)      │
│ 6. INSERT revenue_distributions record                          │
│ 7. UPDATE partners.balance and partners.total_earnings          │
│ 8. SET is_distributed = TRUE, distributed_at = NOW()            │
└─────────────────────────────────────────────────────────────────┘
```

### Share Calculation Scenarios

**Scenario A: ChargeGhar Station (no partner)**
```
chargeghar_share = net_amount (100%)
franchise_share = 0
vendor_share = 0
```

**Scenario B: Franchise Station (Franchise operates)**
```
franchise_share = net_amount * franchise.revenue_share_percent / 100
chargeghar_share = net_amount - franchise_share
vendor_share = 0
```

**Scenario C: Franchise Station + Sub-Vendor (PERCENTAGE model)**
```
franchise_raw = net_amount * franchise.revenue_share_percent / 100
vendor_share = franchise_raw * vendor_revenue_share.partner_percent / 100
franchise_share = franchise_raw - vendor_share
chargeghar_share = net_amount - franchise_raw
```

**Scenario D: ChargeGhar Station + Direct Vendor (PERCENTAGE model)**
```
vendor_share = net_amount * vendor_revenue_share.partner_percent / 100
chargeghar_share = net_amount - vendor_share
franchise_share = 0
```

**Scenario E: FIXED model vendor**
```
# FIXED model: Vendor PAYS fixed amount to owner monthly
# Per-transaction: Vendor keeps all their share (no calculation)
vendor_share = 0  # Not calculated per-transaction
franchise_share = (calculated normally if franchise station)
chargeghar_share = (calculated normally)

# Monthly: Vendor creates payout request to PAY owner the fixed_amount
# This is vendor's EXPENSE, not income
```

---

## Table 5: payout_requests

### Field Lifecycle

| Field | Created By | Updated By | Read By |
|-------|------------|------------|---------|
| `id` | System (auto) | Never | All endpoints |
| `created_at` | System (auto) | Never | All endpoints |
| `updated_at` | System (auto) | System (auto) | All endpoints |
| `partner_id` | Partner (POST request) | Never | All endpoints |
| `payout_type` | System (determined by hierarchy) | Never | All endpoints |
| `amount` | Partner (POST request) | Never | All endpoints |
| `vat_deducted` | System (on approve/process) | Never | Financial |
| `service_charge_deducted` | System (on approve/process) | Never | Financial |
| `net_amount` | System (calculated) | Never | Financial |
| `bank_name` | Partner (POST request) | Never | Payout processing |
| `account_number` | Partner (POST request) | Never | Payout processing |
| `account_holder_name` | Partner (POST request) | Never | Payout processing |
| `status` | System (default PENDING) | Admin/Franchise (on action) | All endpoints |
| `reference_id` | System (auto-generate) | Never | All endpoints |
| `processed_by_id` | Never (on creation) | Admin/Franchise (on complete) | Audit |
| `processed_at` | Never (on creation) | Admin/Franchise (on complete) | Audit |
| `rejection_reason` | Never (on creation) | Admin/Franchise (on reject) | Partner notification |
| `admin_notes` | Never (on creation) | Admin/Franchise (on action) | Admin |

### Payout Type Determination

```
┌─────────────────────────────────────────────────────────────────┐
│ Determine payout_type automatically:                            │
├─────────────────────────────────────────────────────────────────┤
│ IF partner.partner_type == 'FRANCHISE':                         │
│   → payout_type = 'CHARGEGHAR_TO_FRANCHISE'                     │
│                                                                 │
│ ELSE IF partner.partner_type == 'VENDOR':                       │
│   IF partner.parent_id IS NULL:                                 │
│     → payout_type = 'CHARGEGHAR_TO_VENDOR'                      │
│   ELSE:                                                         │
│     → payout_type = 'FRANCHISE_TO_VENDOR'                       │
└─────────────────────────────────────────────────────────────────┘
```

### Deduction Rules - IMPORTANT

**VAT/Service Charge already deducted per-transaction in `revenue_distributions`.**

Partner `balance` contains already-net amounts. No re-deduction at payout.

```
┌─────────────────────────────────────────────────────────────────┐
│ ALL payout_types:                                               │
├─────────────────────────────────────────────────────────────────┤
│   vat_deducted = 0                                              │
│   service_charge_deducted = 0                                   │
│   net_amount = amount  (balance already net)                    │
│                                                                 │
│ Fields kept for audit trail / future flexibility only.          │
└─────────────────────────────────────────────────────────────────┘
```

### Status Transition Flow

```
         ┌──────────┐
         │ PENDING  │ ← Partner creates request
         └────┬─────┘
              │
    ┌─────────┼─────────┐
    ▼         │         ▼
┌────────┐    │    ┌──────────┐
│REJECTED│    │    │ APPROVED │ ← Admin/Franchise approves
└────────┘    │    └────┬─────┘
              │         │
              │         ▼
              │    ┌────────────┐
              │    │ PROCESSING │ ← Payment initiated
              │    └────┬───────┘
              │         │
              │         ▼
              │    ┌───────────┐
              │    │ COMPLETED │ ← Payment confirmed
              │    └───────────┘
              │         │
              │         ▼
              │    ┌───────────────────────────────┐
              │    │ UPDATE partners.balance       │
              │    │ SET balance = balance - amount│
              └────┴───────────────────────────────┘
```

---

## Table 6: partner_iot_history

### Field Lifecycle

| Field | Created By | Updated By | Read By |
|-------|------------|------------|---------|
| `id` | System (auto) | Never | History queries |
| `created_at` | System (auto) | Never | History queries |
| `partner_id` | System (from auth) | Never | History queries |
| `performed_by_id` | System (from auth) | Never | Audit |
| `station_id` | Partner (POST IoT action) | Never | History queries |
| `action_type` | Partner (POST IoT action) | Never | History queries |
| `performed_from` | System (detect source) | Never | Audit |
| `powerbank_sn` | System (for EJECT) | Never | History queries |
| `slot_number` | Partner (for EJECT) | Never | History queries |
| `rental_id` | System (for free eject) | Never | Link to rental |
| `is_free_ejection` | System (validation) | Never | Daily limit check |
| `is_successful` | System (from IoT response) | Never | History queries |
| `error_message` | System (from IoT response) | Never | History queries |
| `request_payload` | System (logged) | Never | Debug |
| `response_data` | System (from IoT) | Never | Debug |
| `ip_address` | System (from request) | Never | Audit |
| `user_agent` | System (from request) | Never | Audit |

### Free Ejection Check (Vendor)

```
┌─────────────────────────────────────────────────────────────────┐
│ Before allowing vendor free ejection (BR13.2):                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ SELECT COUNT(*) FROM partner_iot_history                        │
│ WHERE partner_id = :partner_id                                  │
│   AND action_type = 'EJECT'                                     │
│   AND is_free_ejection = TRUE                                   │
│   AND DATE(created_at) = CURRENT_DATE                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ IF count >= 1:                                                  │
│   → REJECT: "Daily free ejection limit reached"                 │
│ ELSE:                                                           │
│   → ALLOW and set is_free_ejection = TRUE                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Visibility Rules (BR12)

Query filter logic for each entity type:

### Admin (ChargeGhar)
```sql
-- Can view ALL data, no filters
SELECT * FROM partners;
SELECT * FROM station_distributions;
SELECT * FROM revenue_distributions;
SELECT * FROM payout_requests;
SELECT * FROM partner_iot_history;
```

### Franchise
```sql
-- Own profile
SELECT * FROM partners WHERE id = :franchise_id;

-- Own vendors only
SELECT * FROM partners WHERE parent_id = :franchise_id;

-- Own stations only (owned by this franchise)
SELECT sd.* FROM station_distributions sd
WHERE sd.partner_id = :franchise_id 
   OR sd.partner_id IN (SELECT id FROM partners WHERE parent_id = :franchise_id);

-- Own transactions only
SELECT rd.* FROM revenue_distributions rd
WHERE rd.franchise_id = :franchise_id;

-- Own payouts + vendor payouts under me
SELECT pr.* FROM payout_requests pr
WHERE pr.partner_id = :franchise_id
   OR pr.partner_id IN (SELECT id FROM partners WHERE parent_id = :franchise_id);

-- Own IoT history + vendor IoT history
SELECT pih.* FROM partner_iot_history pih
WHERE pih.partner_id = :franchise_id
   OR pih.partner_id IN (SELECT id FROM partners WHERE parent_id = :franchise_id);
```

### Revenue Vendor
```sql
-- Own profile only
SELECT * FROM partners WHERE id = :vendor_id;

-- Own station only
SELECT sd.* FROM station_distributions sd
WHERE sd.partner_id = :vendor_id AND sd.is_active = TRUE;

-- Own transactions only
SELECT rd.* FROM revenue_distributions rd
WHERE rd.vendor_id = :vendor_id;

-- Own payouts only
SELECT pr.* FROM payout_requests pr
WHERE pr.partner_id = :vendor_id;

-- Own IoT history only
SELECT pih.* FROM partner_iot_history pih
WHERE pih.partner_id = :vendor_id;
```

### Non-Revenue Vendor
```sql
-- NO dashboard access (login rejected)
-- NO query access to any partner tables
```

---

## Conclusion

**Schema Status: 100% ACCURATE** for all 13 Business Rules.

All issues resolved. Ready for implementation.
