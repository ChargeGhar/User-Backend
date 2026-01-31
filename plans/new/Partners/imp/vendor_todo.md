# Vendor Dashboard Implementation - TODO

> **Version:** 1.0  
> **Created:** 2026-01-31  
> **Status:** Planning Phase  
> **Based On:** Endpoints.md Section 3 + Business Rules + Existing Implementation

---

## Overview

Implementation of Vendor Dashboard endpoints as defined in `Endpoints.md` Section 3.

**Base Path:** `/api/partner/vendor/`

**Authentication:** User must have `partner_type=VENDOR` AND `vendor_type=REVENUE` in `partners` table.

**Critical:** Non-Revenue vendors have NO dashboard access (BR9.4).

---

## Already Available (Common Endpoints) ✅

These endpoints work for BOTH Franchise and Vendor:

| # | Endpoint | Method | Description | Status |
|---|----------|--------|-------------|--------|
| ✅ | `/api/partners/auth/me` | GET | Own vendor profile | ✅ DONE (Common Auth) |
| ✅ | `/api/partner/iot/history` | GET | Own IoT History | ✅ DONE (Common) |
| ✅ | `/api/partner/stations/` | GET | Own station list | ✅ DONE (Common) |
| ✅ | `/api/partner/stations/{id}/` | GET | Station details | ✅ DONE (Common) |

**Note:** These are already implemented in `api/partners/common/` and work for vendors automatically through `HasDashboardAccess` permission.

---

## Implementation Order (Vendor-Specific)

### Phase 1: Dashboard & Profile
| # | Endpoint | Method | Description | Status |
|---|----------|--------|-------------|--------|
| 1 | `/api/partner/vendor/dashboard/` | GET | Summary stats (balance, earnings, station info) | ⏳ TODO |

**Response Structure:**
```json
{
  "balance": 5000.00,
  "total_earnings": 25000.00,
  "pending_payout": 0.00,
  "station": {
    "id": "uuid",
    "name": "Station Name",
    "code": "ST-001"
  },
  "today": { "transactions": 10, "revenue": 500.00, "my_share": 50.00 },
  "this_week": { "transactions": 60, "revenue": 3000.00, "my_share": 300.00 },
  "this_month": { "transactions": 250, "revenue": 12500.00, "my_share": 1250.00 }
}
```

**Business Logic:**
- Get vendor's single station (BR2.3 - vendor has ONLY ONE station)
- Calculate revenue share based on `station_revenue_shares` table
- Filter transactions by `vendor_id` in `revenue_distributions`
- Show pending payout requests

### Phase 2: Revenue & Transactions
| # | Endpoint | Method | Description | Status |
|---|----------|--------|-------------|--------|
| 2 | `/api/partner/vendor/revenue/` | GET | Own station transactions | ⏳ TODO |

**Query Parameters:**
```
?period=today|week|month|year|custom
?start_date=2026-01-01
?end_date=2026-01-31
?page=1&page_size=20
```

**Response Structure:**
```json
{
  "results": [
    {
      "id": "uuid",
      "rental_id": "uuid",
      "transaction_date": "2026-01-31T10:30:00Z",
      "gross_revenue": 150.00,
      "net_revenue": 135.00,
      "vat_amount": 10.00,
      "service_charge": 5.00,
      "vendor_share": 13.50,
      "vendor_share_percent": 10.00,
      "station": {
        "id": "uuid",
        "name": "Station Name"
      }
    }
  ],
  "count": 250,
  "page": 1,
  "page_size": 20,
  "total_pages": 13,
  "summary": {
    "total_transactions": 250,
    "total_gross_revenue": 37500.00,
    "total_net_revenue": 33750.00,
    "total_vendor_share": 3375.00
  }
}
```

**Business Logic:**
- Filter by `vendor_id` in `revenue_distributions` (BR12.3)
- Show only transactions from vendor's assigned station
- Calculate vendor share based on revenue model (Fixed or Percentage)
- Apply date filters

### Phase 3: Payout Management
| # | Endpoint | Method | Description | Status |
|---|----------|--------|-------------|--------|
| 3 | `/api/partner/vendor/payouts/` | GET | Own payout history | ⏳ TODO |
| 4 | `/api/partner/vendor/payouts/request/` | POST | Request payout | ⏳ TODO |

**GET /payouts/ Response:**
```json
{
  "results": [
    {
      "id": "uuid",
      "amount": 2000.00,
      "status": "COMPLETED",
      "payout_type": "FRANCHISE_TO_VENDOR",
      "requested_at": "2026-01-25T10:00:00Z",
      "approved_at": "2026-01-26T14:30:00Z",
      "completed_at": "2026-01-27T09:15:00Z",
      "bank_name": "Sunrise Bank",
      "account_number": "9876543210",
      "account_holder_name": "Vendor Name",
      "notes": "Monthly payout"
    }
  ],
  "count": 12,
  "pending_amount": 0.00,
  "total_paid": 24000.00
}
```

**POST /payouts/request/ Request:**
```json
{
  "amount": 2000.00,
  "bank_name": "Sunrise Bank",
  "account_number": "9876543210",
  "account_holder_name": "Vendor Name"
}
```

**Business Logic:**
- Vendor can request payout from their balance
- Payout type depends on vendor hierarchy:
  - CG-Vendor: `CHARGEGHAR_TO_VENDOR`
  - Franchise-Vendor: `FRANCHISE_TO_VENDOR`
- Validate: amount <= vendor.balance
- Validate: no pending payout exists
- Create payout request with status=PENDING
- Franchise or ChargeGhar approves/completes (not vendor)

### Phase 4: Agreement
| # | Endpoint | Method | Description | Status |
|---|----------|--------|-------------|--------|
| 5 | `/api/partner/vendor/agreement/` | GET | Own revenue agreement | ⏳ TODO |

**Response Structure:**
```json
{
  "vendor": {
    "id": "uuid",
    "code": "VN-003",
    "business_name": "Updated Vendor Shop",
    "vendor_type": "REVENUE",
    "status": "ACTIVE"
  },
  "parent": {
    "id": "uuid",
    "code": "FR-001",
    "business_name": "Pro Boy",
    "partner_type": "FRANCHISE"
  },
  "station": {
    "id": "uuid",
    "name": "Chitwan Mall Station",
    "code": "CTW001"
  },
  "revenue_model": {
    "model_type": "PERCENTAGE",
    "partner_percent": 10.00,
    "fixed_amount": null,
    "effective_date": "2026-01-31",
    "is_active": true
  },
  "distribution": {
    "distribution_type": "FRANCHISE_TO_VENDOR",
    "effective_date": "2026-01-31",
    "is_active": true
  }
}
```

**Business Logic:**
- Get vendor's station from `station_distributions`
- Get revenue share from `station_revenue_shares`
- Show parent (ChargeGhar or Franchise)
- Show revenue model (Fixed or Percentage)

---

## Existing Resources to Reuse

### Common Repositories (Already Implemented) ✅
- `PartnerRepository` - Partner CRUD operations
- `StationDistributionRepository` - Station assignment operations
- `StationRevenueShareRepository` - Revenue share configuration
- `RevenueDistributionRepository` - Transaction revenue data
- `PayoutRequestRepository` - Payout operations
- `PartnerIotHistoryRepository` - IoT action history

### Common Services (Already Implemented) ✅
- `PartnerStationService` - Station operations (list, detail)
- `PartnerIotService` - IoT operations (history, actions)

### Common Models (Already Implemented) ✅
All 6 models are complete and migrated:
- `Partner`
- `StationDistribution`
- `StationRevenueShare`
- `RevenueDistribution`
- `PayoutRequest`
- `PartnerIotHistory`

### Permissions (Already Implemented) ✅
- `IsVendor` - Validates partner_type == VENDOR
- `IsRevenueVendor` - Validates vendor_type == REVENUE
- `IsActivePartner` - Validates status == ACTIVE
- `HasDashboardAccess` - Validates dashboard access rights

---

## File Structure to Create

```
api/partners/vendor/
├── __init__.py              # Already exists
├── apps.py                  # Already exists
├── urls.py                  # Already exists (empty)
├── serializers/
│   ├── __init__.py          # Already exists (empty)
│   ├── dashboard_serializers.py    # To create
│   ├── revenue_serializers.py      # To create
│   ├── payout_serializers.py       # To create
│   └── agreement_serializers.py    # To create
├── services/
│   ├── __init__.py          # Already exists (empty)
│   └── vendor_service.py    # To create
└── views/
    ├── __init__.py          # Already exists (empty)
    ├── dashboard_view.py    # To create
    ├── revenue_view.py      # To create
    ├── payout_view.py       # To create
    └── agreement_view.py    # To create
```

---

## Critical Business Rules Reference

| BR# | Rule | Vendor Impact |
|-----|------|---------------|
| BR2.3 | Vendor can have ONLY ONE station | Dashboard shows single station |
| BR9.1-2 | Revenue Vendors have payment model & dashboard | Only Revenue vendors access |
| BR9.3-4 | Non-Revenue Vendors have NO payment & NO dashboard | Block non-revenue access |
| BR10.4 | Vendors can ONLY view own station | Read-only station access |
| BR10.5 | Vendors have NO control over station settings | No update/delete operations |
| BR12.3 | Vendors view ONLY own station transactions | Filter by vendor_id |
| BR12.7 | Vendors view only own earnings & payouts | Filter by vendor_id |
| BR13 | Vendor IoT permissions | REBOOT, CHECK, WIFI (no EJECT) |

---

## Visibility Rules (BR12 - Must Enforce)

All vendor endpoints MUST filter data to show ONLY:
1. Own profile (partners.id = vendor_id)
2. Own station (station_distributions where partner_id = vendor_id)
3. Own transactions (revenue_distributions where vendor_id = vendor_id)
4. Own payouts (payout_requests where partner_id = vendor_id)
5. Own IoT history (partner_iot_history where partner_id = vendor_id)
6. Own agreement (station_revenue_shares where partner_id = vendor_id)

---

## Differences from Franchise Dashboard

| Feature | Franchise | Vendor |
|---------|-----------|--------|
| Stations | Multiple stations | ONLY ONE station (BR2.3) |
| Vendors | Can create/manage vendors | Cannot create vendors |
| Station Control | Full control | Read-only (BR10.5) |
| Revenue View | All stations' revenue | Only own station revenue |
| Payout Requests | To ChargeGhar | To parent (CG or Franchise) |
| Payout Processing | Processes vendor payouts | Cannot process payouts |
| IoT Eject | Unlimited | 1 free/day via rental (BR13) |
| Agreements | Own + vendor agreements | Only own agreement |

---

## Implementation Strategy

### Step 1: Create Vendor Service
- Reuse common repositories
- Implement vendor-specific business logic
- Enforce single station rule (BR2.3)
- Calculate vendor share based on revenue model

### Step 2: Create Serializers
- Dashboard serializer (balance, earnings, station)
- Revenue serializer (transactions with vendor share)
- Payout serializer (request/history)
- Agreement serializer (revenue model details)

### Step 3: Create Views
- Dashboard view (GET)
- Revenue view (GET with filters)
- Payout views (GET list, POST request)
- Agreement view (GET)

### Step 4: Register URLs
- Update `api/partners/vendor/urls.py`
- Register vendor router in main URLs

### Step 5: Testing
- Test with VN-003 (Franchise-Vendor)
- Test with CG-Vendor (if exists)
- Verify single station enforcement
- Verify revenue calculations
- Verify payout flow
- Verify permissions

---

## Progress Tracking

- [ ] Analyze existing codebase ✅
- [ ] Create vendor_todo.md ✅
- [ ] Phase 1: Dashboard (1 endpoint)
- [ ] Phase 2: Revenue (1 endpoint)
- [ ] Phase 3: Payouts (2 endpoints)
- [ ] Phase 4: Agreement (1 endpoint)
- [ ] Integration testing
- [ ] Final review

---

## Current Status

**STATUS: NOT STARTED - 0/5 ENDPOINTS (0%)**

**Vendor-Specific Endpoints:**
- ⏳ Dashboard (1 endpoint)
- ⏳ Revenue (1 endpoint)
- ⏳ Payouts (2 endpoints)
- ⏳ Agreement (1 endpoint)

**Already Available (Common):**
- ✅ Profile (`/api/partners/auth/me`)
- ✅ IoT History (`/api/partner/iot/history`)
- ✅ Stations List (`/api/partner/stations/`)
- ✅ Station Detail (`/api/partner/stations/{id}/`)

**Total Vendor Access:** 4 common + 5 vendor-specific = 9 endpoints

---

## Notes

1. **Reuse Common Endpoints:** Vendors already have access to stations and IoT history through common endpoints. No need to duplicate.

2. **Single Station Rule:** Vendor dashboard is simpler than franchise because vendor has ONLY ONE station (BR2.3).

3. **Revenue Model:** Vendor's revenue share is calculated based on `station_revenue_shares.revenue_model`:
   - `FIXED`: Fixed monthly amount
   - `PERCENTAGE`: Percentage of net revenue

4. **Payout Hierarchy:**
   - CG-Vendor requests payout from ChargeGhar
   - Franchise-Vendor requests payout from Franchise
   - Payout type is auto-detected based on `parent_id`

5. **Non-Revenue Vendors:** Must block access with `IsRevenueVendor` permission. Non-revenue vendors should get 403 Forbidden.

6. **IoT Permissions:** Vendors can use IoT actions (REBOOT, CHECK, WIFI) but NOT EJECT (except 1 free/day via rental flow).

---

## Testing Checklist

- [ ] Revenue vendor can access dashboard
- [ ] Non-revenue vendor gets 403 Forbidden
- [ ] Dashboard shows single station only
- [ ] Revenue calculations correct (Fixed vs Percentage)
- [ ] Payout request validates balance
- [ ] Payout request blocks if pending exists
- [ ] Agreement shows correct revenue model
- [ ] Transactions filtered by vendor_id
- [ ] IoT history filtered by vendor_id
- [ ] Common endpoints work for vendor
- [ ] Permissions enforced correctly
