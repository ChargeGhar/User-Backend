# Partnership System - Database Schema

> **Version:** 1.1  
> **Last Updated:** 2026-01-24  
> **Status:** Cross-verified with all Business Rules - READY FOR IMPLEMENTATION

---

## Overview

This document defines the database schema for ChargeGhar's Partnership System supporting:
- **Franchise** - Regional partners who own multiple stations
- **Vendor** (Revenue/Non-Revenue) - Station operators

**Key Principle:** Partners are existing Users in the system. No separate user creation.

---

## AppConfig Additions (Existing Table)

Add these keys to `app_configs` table:

```sql
INSERT INTO app_configs (id, key, value, description, is_active) VALUES
(uuid_generate_v4(), 'PLATFORM_VAT_PERCENT', '13', 'VAT % deducted at ChargeGhar level', true),
(uuid_generate_v4(), 'PLATFORM_SERVICE_CHARGE_PERCENT', '2.5', 'Service charge % at ChargeGhar level', true);
```

> **Note:** VAT & Service Charge are ONLY deducted at ChargeGhar-level payouts, NOT Franchise-level (BR5).

---

## Table 1: partners

Core partner entity representing both Franchises and Vendors.

```sql
CREATE TABLE partners (
    -- Base fields (from BaseModel)
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Link to existing user
    user_id BIGINT NOT NULL UNIQUE REFERENCES users_user(id) ON DELETE PROTECT,
    
    -- Partner classification
    partner_type VARCHAR(20) NOT NULL,  -- 'FRANCHISE' or 'VENDOR'
    vendor_type VARCHAR(20),             -- 'REVENUE' or 'NON_REVENUE' (only for VENDOR)
    
    -- Hierarchy: NULL = under ChargeGhar, FK = under that Franchise
    parent_id UUID REFERENCES partners(id) ON DELETE CASCADE,
    
    -- Business info
    code VARCHAR(20) NOT NULL UNIQUE,    -- e.g., 'FR-001', 'VN-001'
    business_name VARCHAR(100) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    contact_email VARCHAR(255),
    address TEXT,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, INACTIVE, SUSPENDED
    
    -- Franchise-specific fields
    upfront_amount DECIMAL(12,2) DEFAULT 0,           -- One-time payment received
    revenue_share_percent DECIMAL(5,2),               -- Franchise's % of station revenue
    
    -- Balances (denormalized for quick access)
    balance DECIMAL(12,2) NOT NULL DEFAULT 0,         -- Available for payout
    total_earnings DECIMAL(12,2) NOT NULL DEFAULT 0,  -- Lifetime earnings
    
    -- Admin tracking
    assigned_by_id BIGINT REFERENCES users_user(id) ON DELETE SET NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    
    -- Constraints
    CONSTRAINT partner_type_check CHECK (partner_type IN ('FRANCHISE', 'VENDOR')),
    CONSTRAINT vendor_type_check CHECK (
        (partner_type = 'FRANCHISE' AND vendor_type IS NULL) OR
        (partner_type = 'VENDOR' AND vendor_type IN ('REVENUE', 'NON_REVENUE'))
    ),
    CONSTRAINT hierarchy_check CHECK (
        (partner_type = 'FRANCHISE' AND parent_id IS NULL) OR  -- Franchise always under ChargeGhar
        (partner_type = 'VENDOR')                               -- Vendor can be under CG or Franchise
    ),
    CONSTRAINT revenue_share_check CHECK (
        revenue_share_percent IS NULL OR (revenue_share_percent >= 0 AND revenue_share_percent <= 100)
    )
);

-- Indexes
CREATE INDEX idx_partners_type_status ON partners(partner_type, status);
CREATE INDEX idx_partners_parent ON partners(parent_id);
CREATE INDEX idx_partners_code ON partners(code);
```

### Notes - partners

| Field | Business Rule |
|-------|---------------|
| `partner_type` | BR1.2-3: FRANCHISE or VENDOR |
| `vendor_type` | BR9.1-4: REVENUE gets dashboard & payouts, NON_REVENUE gets nothing |
| `parent_id` | BR1.3,5: NULL = ChargeGhar-level, FK = Franchise-level |
| `revenue_share_percent` | BR3.5: Franchise gets y% of their stations' net revenue |
| `balance` | Running balance for payout requests |

**Hierarchy Logic:**
- `parent_id IS NULL` + `partner_type='FRANCHISE'` → Franchise under ChargeGhar
- `parent_id IS NULL` + `partner_type='VENDOR'` → Direct Vendor under ChargeGhar
- `parent_id IS NOT NULL` + `partner_type='VENDOR'` → Sub-Vendor under Franchise

**Vendor Type Change Rules (BR9.6):**
When `vendor_type` changes:

- **REVENUE → NON_REVENUE:**
  1. Delete `station_revenue_shares` record for this vendor
  2. Invalidate dashboard access (logout active sessions)
  3. Future transactions: vendor_share = 0

- **NON_REVENUE → REVENUE:**
  1. Require revenue model input (PERCENTAGE or FIXED)
  2. Create `station_revenue_shares` record
  3. Enable dashboard access

---

## Table 2: station_distributions

Links stations to partners (who operates which station).

```sql
CREATE TABLE station_distributions (
    -- Base fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Station being assigned
    station_id UUID NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    
    -- Partner receiving station
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    
    -- Distribution details
    distribution_type VARCHAR(30) NOT NULL,  -- Who gave to whom
    
    -- Validity
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiry_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Admin tracking
    assigned_by_id BIGINT REFERENCES users_user(id) ON DELETE SET NULL,
    notes TEXT,
    
    -- Constraints
    CONSTRAINT distribution_type_check CHECK (
        distribution_type IN ('CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR')
    )
);

-- Indexes
CREATE INDEX idx_station_dist_station ON station_distributions(station_id, is_active);
CREATE INDEX idx_station_dist_partner ON station_distributions(partner_id, is_active);
CREATE INDEX idx_station_dist_type ON station_distributions(distribution_type);

-- Unique constraint: One active operator per station (BR2.4)
CREATE UNIQUE INDEX idx_station_single_operator 
ON station_distributions(station_id) 
WHERE is_active = TRUE AND distribution_type IN ('CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR');

-- Unique constraint: Vendor can only have ONE station (BR2.3)
-- Applied via service layer (need to check partner is VENDOR type)
```

### Notes - station_distributions

| Business Rule | Implementation |
|---------------|----------------|
| BR2.1 | `distribution_type='CHARGEGHAR_TO_VENDOR'` for ChargeGhar → CG Vendor |
| BR2.2 | `distribution_type='FRANCHISE_TO_VENDOR'` for Franchise → F Vendor |
| BR2.3 | Service layer validates vendor has only 1 active distribution |
| BR2.4 | Unique index ensures 1 operator per station |
| BR1.4 | `distribution_type='CHARGEGHAR_TO_FRANCHISE'` for station ownership |

**Distribution Types:**
- `CHARGEGHAR_TO_FRANCHISE` - ChargeGhar assigns station to Franchise (Franchise OWNS and OPERATES until vendor assigned)
- `CHARGEGHAR_TO_VENDOR` - ChargeGhar assigns station operation to Direct Vendor
- `FRANCHISE_TO_VENDOR` - Franchise assigns their station operation to Sub-Vendor

**Franchise Station Scenarios:**
1. **Franchise operates own station:** Only `CHARGEGHAR_TO_FRANCHISE` record exists
2. **Franchise assigns to vendor:** Both `CHARGEGHAR_TO_FRANCHISE` (ownership) AND `FRANCHISE_TO_VENDOR` (operation) records exist
3. **Revenue calculation:** System checks for active `FRANCHISE_TO_VENDOR` first; if none, Franchise is the operator

---

## Table 3: station_revenue_shares

Revenue model configuration per station distribution.

```sql
CREATE TABLE station_revenue_shares (
    -- Base fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Link to distribution
    distribution_id UUID NOT NULL UNIQUE REFERENCES station_distributions(id) ON DELETE CASCADE,
    
    -- Revenue model type
    revenue_model VARCHAR(20) NOT NULL,  -- 'PERCENTAGE' or 'FIXED'
    
    -- Percentage model fields
    partner_percent DECIMAL(5,2),  -- Partner's share %
    
    -- Fixed model fields
    fixed_amount DECIMAL(12,2),    -- Fixed monthly amount
    
    -- Constraints
    CONSTRAINT revenue_model_check CHECK (revenue_model IN ('PERCENTAGE', 'FIXED')),
    CONSTRAINT percentage_or_fixed CHECK (
        (revenue_model = 'PERCENTAGE' AND partner_percent IS NOT NULL AND partner_percent >= 0 AND partner_percent <= 100) OR
        (revenue_model = 'FIXED' AND fixed_amount IS NOT NULL AND fixed_amount >= 0)
    )
);

-- Index
CREATE INDEX idx_revenue_share_dist ON station_revenue_shares(distribution_id);
```

### Notes - station_revenue_shares

| Business Rule | Implementation |
|---------------|----------------|
| BR3.3 | `revenue_model` = 'PERCENTAGE' or 'FIXED' |
| BR3.4 | Non-Revenue vendors have NO record here (service layer) |
| BR6.2 | CG Vendor gets `partner_percent` of net revenue |
| BR7.4 | Franchise Vendor gets `partner_percent` from Franchise's share |
| BR11.4-5 | Fixed = same amount, Percentage = varies by performance |

**IMPORTANT - Revenue Model Storage:**
- **Franchise revenue model:** Stored in `partners.revenue_share_percent` (% of station net revenue from ChargeGhar)
- **Vendor revenue model:** Stored in `station_revenue_shares.partner_percent` or `fixed_amount`

**Revenue Calculation (What Partner PAYS to Owner):**
- `PERCENTAGE`: Vendor/Franchise pays `(their_share * partner_percent / 100)` to their owner
- `FIXED`: Vendor/Franchise pays `fixed_amount` monthly to their owner

**Example - Vendor under Franchise (PERCENTAGE 15%):**
- Franchise receives NPR 1000 from ChargeGhar
- Vendor pays Franchise: NPR 150 (15% of 1000)
- Vendor keeps: NPR 850

**Example - Vendor under ChargeGhar (FIXED NPR 5000/month):**
- Vendor pays ChargeGhar: NPR 5000 monthly
- Vendor keeps: All remaining transaction revenue

---

## Table 4: revenue_distributions

Per-transaction revenue calculation and allocation.

```sql
CREATE TABLE revenue_distributions (
    -- Base fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Source transaction
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    rental_id UUID REFERENCES rentals(id) ON DELETE SET NULL,
    station_id UUID NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    
    -- Revenue breakdown
    gross_amount DECIMAL(12,2) NOT NULL,           -- Total transaction amount
    vat_amount DECIMAL(12,2) NOT NULL DEFAULT 0,   -- VAT deducted (BR5.1)
    service_charge DECIMAL(12,2) NOT NULL DEFAULT 0, -- Service charge (BR5.2)
    net_amount DECIMAL(12,2) NOT NULL,             -- gross - vat - service_charge
    
    -- Share allocation
    chargeghar_share DECIMAL(12,2) NOT NULL DEFAULT 0,
    franchise_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    franchise_share DECIMAL(12,2) NOT NULL DEFAULT 0,
    vendor_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    vendor_share DECIMAL(12,2) NOT NULL DEFAULT 0,
    
    -- Distribution status
    is_distributed BOOLEAN NOT NULL DEFAULT FALSE,  -- Added to partner balances?
    distributed_at TIMESTAMP WITH TIME ZONE,
    
    -- Calculation metadata (for audit)
    calculation_details JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_rev_dist_transaction ON revenue_distributions(transaction_id);
CREATE INDEX idx_rev_dist_station ON revenue_distributions(station_id, created_at);
CREATE INDEX idx_rev_dist_franchise ON revenue_distributions(franchise_id, is_distributed);
CREATE INDEX idx_rev_dist_vendor ON revenue_distributions(vendor_id, is_distributed);
CREATE INDEX idx_rev_dist_undistributed ON revenue_distributions(is_distributed) WHERE is_distributed = FALSE;
```

### Notes - revenue_distributions

| Business Rule | Implementation |
|---------------|----------------|
| BR4.1-3 | `gross_amount` = full transaction, all collected by ChargeGhar |
| BR5.1-2 | `vat_amount`, `service_charge` deducted PER TRANSACTION at ChargeGhar level |
| BR5.4 | `net_amount = gross - vat - service_charge` |
| BR6.1-3 | ChargeGhar station shares calculated here |
| BR7.1-5 | Franchise station shares cascade to vendor |
| BR11.1-3 | All calculations use `net_amount` |

**VAT & Service Charge - DEFINITIVE RULE:**
- VAT and Service Charge are deducted **per transaction** when rental completes
- `net_amount` = `gross_amount` - `vat_amount` - `service_charge`
- ALL partner share calculations use `net_amount`
- Partner `balance` accumulates shares already calculated from net revenue
- `payout_requests` does NOT re-deduct VAT (already factored into shares)

**FIXED vs PERCENTAGE Revenue Model:**

For **PERCENTAGE** model:
- Per-transaction: Calculate vendor share from net_amount
- Update `partners.balance` per transaction

For **FIXED** model:
- Per-transaction: Do NOT calculate vendor share (vendor keeps all)
- Monthly: Vendor pays `fixed_amount` to owner via payout request
- `revenue_distributions.vendor_share` = 0 for FIXED model transactions
- Vendor's obligation tracked separately, paid monthly

**Share Calculation Examples:**

```
Scenario 1: ChargeGhar Station + Revenue Vendor (10%)
- gross_amount = 100
- vat_amount = 13 (13%)
- service_charge = 2.50 (2.5%)
- net_amount = 84.50
- vendor_share = 8.45 (10% of net)
- chargeghar_share = 76.05

Scenario 2: Franchise Station (20%) + Sub-Vendor (15%)
- gross_amount = 100
- net_amount = 84.50
- franchise_share_raw = 16.90 (20% of net)
- vendor_share = 2.54 (15% of franchise share)
- franchise_share = 14.36 (remaining)
- chargeghar_share = 67.60 (80% of net)
```

---

## Table 5: payout_requests

Payout workflow for partners.

```sql
CREATE TABLE payout_requests (
    -- Base fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Requester
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    
    -- Payout details
    payout_type VARCHAR(30) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    
    -- Deductions (calculated at processing from AppConfig)
    vat_deducted DECIMAL(12,2) NOT NULL DEFAULT 0,
    service_charge_deducted DECIMAL(12,2) NOT NULL DEFAULT 0,
    net_amount DECIMAL(12,2) NOT NULL,  -- amount - vat - service_charge
    
    -- Bank details (snapshot at request time)
    bank_name VARCHAR(100),
    account_number VARCHAR(50),
    account_holder_name VARCHAR(100),
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    reference_id VARCHAR(50) NOT NULL UNIQUE,  -- Internal reference
    
    -- Processing
    processed_by_id BIGINT REFERENCES users_user(id) ON DELETE SET NULL,
    processed_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    admin_notes TEXT,
    
    -- Constraints
    CONSTRAINT payout_type_check CHECK (
        payout_type IN ('CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR', 'FRANCHISE_TO_VENDOR')
    ),
    CONSTRAINT payout_status_check CHECK (
        status IN ('PENDING', 'APPROVED', 'PROCESSING', 'COMPLETED', 'REJECTED')
    ),
    CONSTRAINT amount_positive CHECK (amount > 0)
);

-- Indexes
CREATE INDEX idx_payout_partner ON payout_requests(partner_id, status);
CREATE INDEX idx_payout_type_status ON payout_requests(payout_type, status);
CREATE INDEX idx_payout_created ON payout_requests(created_at);
```

### Notes - payout_requests

| Business Rule | Implementation |
|---------------|----------------|
| BR8.1 | `payout_type='CHARGEGHAR_TO_FRANCHISE'` - CG pays Franchise |
| BR8.2 | `payout_type='CHARGEGHAR_TO_VENDOR'` - CG pays Direct Vendor |
| BR8.3 | `payout_type='FRANCHISE_TO_VENDOR'` - Franchise pays Sub-Vendor |
| BR8.4 | Non-Revenue vendors cannot create payout requests (service layer) |

**IMPORTANT - No VAT Deduction at Payout:**
- VAT/Service Charge already deducted per-transaction in `revenue_distributions`
- Partner `balance` already contains net share amounts
- `vat_deducted` and `service_charge_deducted` fields = 0 (kept for audit trail only)
- `net_amount` = `amount` (no further deductions)

**Payout Flow:**
1. Partner requests payout from their accumulated `balance`
2. System validates `amount <= partners.balance`
3. On completion: `UPDATE partners SET balance = balance - amount`

---

## Table 6: partner_iot_history

Audit log for IoT actions performed by partners.

```sql
CREATE TABLE partner_iot_history (
    -- Base fields
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Who performed
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    performed_by_id BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    
    -- Target
    station_id UUID NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    
    -- Action details
    action_type VARCHAR(20) NOT NULL,
    performed_from VARCHAR(20) NOT NULL,
    
    -- For EJECT actions
    powerbank_sn VARCHAR(100),
    slot_number INTEGER,
    rental_id UUID REFERENCES rentals(id) ON DELETE SET NULL,
    is_free_ejection BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Result
    is_successful BOOLEAN NOT NULL,
    error_message TEXT,
    request_payload JSONB DEFAULT '{}',
    response_data JSONB DEFAULT '{}',
    
    -- Client info
    ip_address INET,
    user_agent TEXT,
    
    -- Constraints
    CONSTRAINT action_type_check CHECK (
        action_type IN ('EJECT', 'REBOOT', 'CHECK', 'WIFI_SCAN', 'WIFI_CONNECT', 'VOLUME', 'MODE')
    ),
    CONSTRAINT performed_from_check CHECK (
        performed_from IN ('MOBILE_APP', 'DASHBOARD', 'ADMIN_PANEL')
    )
);

-- Indexes
CREATE INDEX idx_iot_history_partner ON partner_iot_history(partner_id, action_type, created_at);
CREATE INDEX idx_iot_history_station ON partner_iot_history(station_id, created_at);
CREATE INDEX idx_iot_history_free_eject ON partner_iot_history(partner_id, is_free_ejection, created_at) 
WHERE action_type = 'EJECT';
```

### Notes - partner_iot_history

| Business Rule | Implementation |
|---------------|----------------|
| BR13.1 | All IoT actions logged with `action_type` |
| BR13.2 | Vendor 1 free eject/day: check `is_free_ejection=TRUE` for today |
| BR13.3 | Franchise unlimited eject: no restriction in service layer |
| BR13.4 | Control rights validated in service layer by partner type |

**Action Permissions:**

| Partner Type | Allowed Actions |
|--------------|-----------------|
| FRANCHISE | EJECT, REBOOT, CHECK, WIFI_SCAN, WIFI_CONNECT, VOLUME, MODE |
| VENDOR (any) | REBOOT, CHECK, WIFI_SCAN, WIFI_CONNECT, VOLUME, MODE |
| VENDOR (free eject) | EJECT (1 per day via rental flow only) |

**Vendor Free Ejection - Integration with Rental Flow:**

Vendor free ejection happens via `POST /api/rentals/start` (not IoT endpoint).

**Modification needed in `api/user/rentals/services/rental/start.py`:**
```python
# In start_rental method, after _validate_rental_prerequisites:
def _check_vendor_free_ejection(self, user, station) -> bool:
    """Check if user is a vendor for this station with free ejection available"""
    if not hasattr(user, 'partner_profile'):
        return False
    
    partner = user.partner_profile
    if partner.partner_type != 'VENDOR':
        return False
    
    # Check if vendor operates this station
    from api.partners.common.models import StationDistribution
    distribution = StationDistribution.objects.filter(
        partner=partner,
        station=station,
        is_active=True
    ).first()
    
    if not distribution:
        return False
    
    # Check daily limit
    from api.partners.common.models import PartnerIotHistory
    from django.utils import timezone
    today = timezone.now().date()
    
    used_today = PartnerIotHistory.objects.filter(
        partner=partner,
        action_type='EJECT',
        is_free_ejection=True,
        created_at__date=today
    ).exists()
    
    return not used_today

# After successful rental start, if vendor free ejection:
def _log_vendor_free_ejection(self, user, station, rental, powerbank):
    """Log free ejection to partner_iot_history"""
    from api.partners.common.models import PartnerIotHistory
    
    PartnerIotHistory.objects.create(
        partner=user.partner_profile,
        performed_by=user,
        station=station,
        action_type='EJECT',
        performed_from='MOBILE_APP',
        powerbank_sn=powerbank.serial_number,
        slot_number=rental.slot.slot_number,
        rental=rental,
        is_free_ejection=True,
        is_successful=True
    )
```

---

## Business Rules Coverage Summary

| BR# | Rule | Table(s) | Field(s) |
|-----|------|----------|----------|
| BR1.2 | ChargeGhar creates Franchises | partners | `partner_type='FRANCHISE'`, `parent_id=NULL` |
| BR1.3 | ChargeGhar creates own Vendors | partners | `partner_type='VENDOR'`, `parent_id=NULL` |
| BR1.5 | Franchise creates own Vendors | partners | `partner_type='VENDOR'`, `parent_id=<franchise_id>` |
| BR1.6 | Vendors cannot create entities | - | Service layer |
| BR1.7 | Non-Revenue no dashboard | partners | `vendor_type='NON_REVENUE'` → service layer |
| BR2.1-2 | Station assignment | station_distributions | `distribution_type` |
| BR2.3 | Vendor = 1 station only | station_distributions | Service layer validation |
| BR2.4 | Station = 1 operator | station_distributions | Unique index |
| BR3.3 | Fixed OR Percentage model | station_revenue_shares | `revenue_model` |
| BR3.4 | Non-Revenue no model | station_revenue_shares | No record created |
| BR3.5 | Franchise % share | partners | `revenue_share_percent` |
| BR4.1-3 | All to ChargeGhar | revenue_distributions | `gross_amount` |
| BR5.1-5 | VAT & Service Charge | revenue_distributions, app_configs | `vat_amount`, `service_charge` |
| BR6-7 | Revenue distribution | revenue_distributions | Share fields |
| BR8.1-6 | Payout rules | payout_requests | `payout_type`, deduction fields |
| BR9.1-6 | Vendor types | partners | `vendor_type` |
| BR10.1-7 | Control & permissions | - | Service layer |
| BR11.1-5 | Financial calculations | revenue_distributions | All amounts use `net_amount` |
| BR12.1-7 | Reporting visibility | - | Service layer query filters |
| BR13.1-4 | IoT history | partner_iot_history | All fields |

---

## Critical Questions Answered

### Q1: How does system identify "Belongs to" of Entity?
**Answer:** `partners.parent_id`
- `parent_id IS NULL` → Under ChargeGhar
- `parent_id = <uuid>` → Under that Partner (must be Franchise)

### Q2: How does system identify "Belongs to" of payouts/transactions?
**Answer:** Chain lookup:
1. `payout_requests.partner_id` → Get Partner
2. `partners.parent_id` → Determine hierarchy
3. `payout_requests.payout_type` → Determine who processes

### Q3: How does system identify "Belongs to" of station?
**Answer:** `station_distributions` table
1. Find active distribution: `WHERE station_id=X AND is_active=TRUE`
2. Get `partner_id` → Station operator
3. Check `distribution_type` → Determine full hierarchy

---

## Migration Order

1. `partners` (depends on: users_user)
2. `station_distributions` (depends on: partners, stations)
3. `station_revenue_shares` (depends on: station_distributions)
4. `revenue_distributions` (depends on: transactions, rentals, stations, partners)
5. `payout_requests` (depends on: partners, users_user)
6. `partner_iot_history` (depends on: partners, stations, rentals, users_user)

---

## Next Steps

After schema approval:
1. Create Django models in `api/partners/`
2. Create migrations
3. Implement services layer
4. Implement API endpoints
