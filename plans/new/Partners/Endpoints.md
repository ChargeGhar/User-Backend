# Partnership System - API Endpoints

> **Version:** 2.0  
> **Last Updated:** 2026-01-24  
> **Status:** Admin endpoints IMPLEMENTED - Franchise/Vendor dashboard endpoints PENDING

---

## Overview

Three dashboard types with distinct access levels:
- **Admin Dashboard** (ChargeGhar) - Full system control
- **Franchise Dashboard** - Own stations + own vendors
- **Vendor Dashboard** - Own station only (Revenue vendors only)

---

## 1. Admin Dashboard Endpoints (ChargeGhar) ✅ IMPLEMENTED

Base Path: `/api/admin/partners/`

**Implementation:** `api/admin/views/partner_views.py`, `api/admin/services/admin_partner_service.py`

### 1.1 Partner Management ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/` | List all partners with filters | ✅ |
| GET | `/api/admin/partners/{id}/` | Get partner details | ✅ |
| POST | `/api/admin/partners/franchise/` | Create franchise | ✅ |
| POST | `/api/admin/partners/vendor/` | Create CG-level vendor | ✅ |
| PATCH | `/api/admin/partners/{id}/` | Update partner | ✅ |
| PATCH | `/api/admin/partners/{id}/status/` | Activate/Suspend partner | ✅ |

**Query Parameters for GET list:**
```
?partner_type=FRANCHISE|VENDOR
?vendor_type=REVENUE|NON_REVENUE
?status=ACTIVE|INACTIVE|SUSPENDED
?parent_id={uuid}           # Filter by hierarchy
?search={name|code|phone}
?page=1&page_size=20
```

**POST /api/admin/partners/franchise/ Request:**
```json
{
  "user_id": 123,
  "business_name": "Kathmandu Franchise",
  "contact_phone": "9801234567",
  "contact_email": "ktm@example.com",
  "address": "Kathmandu",
  "upfront_amount": 50000.00,
  "revenue_share_percent": 20.00,
  "station_ids": ["uuid1", "uuid2"],
  "notes": "Optional notes"
}
```

**POST /api/admin/partners/vendor/ Request:**
```json
{
  "user_id": 456,
  "vendor_type": "REVENUE",
  "business_name": "Station Operator",
  "contact_phone": "9807654321",
  "station_id": "uuid",
  "revenue_model": "PERCENTAGE",
  "partner_percent": 10.00,
  "notes": "Optional"
}
```

### 1.2 Station Distribution ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/stations/` | List station assignments | ✅ |
| GET | `/api/admin/partners/stations/available/` | Unassigned stations | ✅ |
| DELETE | `/api/admin/partners/stations/{dist_id}/` | Deactivate assignment | ✅ |

**Note:** Station assignment happens ONLY during partner creation (BR2.1-2). No separate `POST /assign` endpoint.
- Franchise creation: Include `station_ids[]` in POST body
- Vendor creation: Include `station_id` in POST body (single station only)

### 1.3 Transactions & Revenue ⏳ PENDING

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/revenue` | All partner transactions | ⏳ |

**Query Parameters:**
```
?station_id={uuid}
?franchise_id={uuid}
?vendor_id={uuid}
?chargeghar_only=true       # Stations with NO partner assigned (100% CG revenue)
?period=today|week|month|year|custom
?start_date=2026-01-01
?end_date=2026-01-31
?is_distributed=true|false
```

**Filter Logic:**
- `chargeghar_only=true`: Returns transactions where `franchise_id IS NULL AND vendor_id IS NULL`
- `franchise_id={uuid}`: Returns transactions for that franchise's stations
- `vendor_id={uuid}`: Returns transactions for that vendor's station

### 1.4 Payouts ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/payouts/` | List all payout requests | ✅ |
| GET | `/api/admin/partners/payouts/{id}/` | Payout details | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/approve/` | Approve payout | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/process/` | Mark as processing | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/complete/` | Complete payout | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/reject/` | Reject payout | ✅ |

**Query Parameters:**
```
?payout_type=CHARGEGHAR_TO_FRANCHISE|CHARGEGHAR_TO_VENDOR|FRANCHISE_TO_VENDOR
?status=PENDING|APPROVED|PROCESSING|COMPLETED|REJECTED
?partner_id={uuid}
?period=today|week|month
```

**Note:** Admin processes ONLY `CHARGEGHAR_TO_FRANCHISE` and `CHARGEGHAR_TO_VENDOR` payouts.

### 1.5 Analytics Dashboard ⏳ PENDING

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/analytics/overview/` | Total partners, revenue, payouts | ⏳ |
| GET | `/api/admin/partners/analytics/revenue/` | Revenue breakdown by hierarchy | ⏳ |
| GET | `/api/admin/partners/analytics/top-performers/` | Top stations/partners | ⏳ |

---

## 2. Franchise Dashboard Endpoints

Base Path: `/api/partner/franchise/`

**Authentication:** User must have `partner_type=FRANCHISE` in `partners` table.

### 2.1 Dashboard & Profile

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partners/auth/me` | Own franchise/vendor profile | `partners` | Already impleneted
| GET    | `/api/partner/iot/history` Get own IoT History | `partner_iot_history` |
| GET | `/api/partner/franchise/dashboard/` | Summary stats | `partners`, `revenue_distributions` |

**GET /dashboard/ Response:**
```json
{
  "balance": 15000.00,
  "total_earnings": 150000.00,
  "pending_payout": 5000.00,
  "stations_count": 5,
  "vendors_count": 3,
  "today": { "transactions": 25, "revenue": 2500.00 },
  "this_week": { "transactions": 150, "revenue": 15000.00 },
  "this_month": { "transactions": 600, "revenue": 60000.00 }
}
```

### 2.2 Vendor Management (Franchise's own vendors)

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/franchise/vendors/` | List own vendors | `partners` |
| GET | `/api/partner/franchise/vendors/{id}/` | Vendor details | `partners`, `station_distributions` |
| POST | `/api/partner/franchise/vendors/` | Create sub-vendor | `partners`, `station_distributions`, `station_revenue_shares` |
| PATCH | `/api/partner/franchise/vendors/{id}/` | Update vendor | `partners` |
| PATCH | `/api/partner/franchise/vendors/{id}/status/` | Activate/Suspend | `partners` |

**POST Request:**
```json
{
  "user_id": 789,
  "vendor_type": "REVENUE",
  "business_name": "Sub Operator",
  "contact_phone": "9812345678",
  "station_id": "uuid",
  "revenue_model": "PERCENTAGE",
  "partner_percent": 15.00
}
```

### 2.3 Stations

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/franchise/stations/` | Own stations list | `station_distributions`, `stations` |
| GET | `/api/partner/franchise/stations/{id}/` | Station details | `stations`, `station_distributions` |
| GET | `/api/partner/franchise/stations/unassigned/` | Stations without vendor assigned | `station_distributions` |

**Note:** Franchise assigns stations to vendors during vendor creation only.

### 2.4 Transactions

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/franchise/revenue/` | Own stations' transactions | `revenue_distributions` |

**Query Parameters:**
```
?station_id={uuid}
?vendor_id={uuid}
?period=today|week|month|year|custom
?start_date=2026-01-01
?end_date=2026-01-31
```

### 2.5 Payouts

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/franchise/payouts/` | Own payout history | `payout_requests` |
| POST | `/api/partner/franchise/payouts/request/` | Request payout from CG | `payout_requests` |
| GET | `/api/partner/franchise/payouts/vendors/` | Sub-vendor payout requests | `payout_requests` |
| PATCH | `/api/partner/franchise/payouts/vendors/{id}/approve/` | Approve vendor payout | `payout_requests` |
| PATCH | `/api/partner/franchise/payouts/vendors/{id}/complete/` | Complete vendor payout | `payout_requests`, `partners.balance` |
| PATCH | `/api/partner/franchise/payouts/vendors/{id}/reject/` | Reject vendor payout | `payout_requests` |

**POST /payouts/request/ Request:**
```json
{
  "amount": 10000.00,
  "bank_name": "NIC Asia",
  "account_number": "1234567890",
  "account_holder_name": "Franchise Name"
}
```

**Note:** Franchise processes ONLY `FRANCHISE_TO_VENDOR` payouts (their own sub-vendors).

### 2.6 Agreements

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/franchise/agreements/` | Own agreement + vendor agreements | `partners`, `station_revenue_shares` |

---

## 3. Vendor Dashboard Endpoints

Base Path: `/api/partner/vendor/`

**Authentication:** User must have `partner_type=VENDOR` AND `vendor_type=REVENUE` in `partners` table.

**Note:** Non-Revenue vendors have NO dashboard access (BR9.4).

### 3.1 Dashboard & Profile

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partners/auth/me` | Own franchise/vendor profile | `partners` | Already impleneted
| GET    | `/api/partner/iot/history` Get own IoT History | `partner_iot_history` |
| GET | `/api/partner/vendor/dashboard/` | Summary stats | `partners`, `revenue_distributions` |

**GET /dashboard/ Response:**
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

### 3.2 Station

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/vendor/station/` | Own station details | `station_distributions`, `stations` |

**Note:** Vendor can only view, NOT modify station settings (BR10.5).

### 3.3 Transactions

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/vendor/revenue/` | Own station transactions | `revenue_distributions` |

**Query Parameters:**
```
?period=today|week|month|year|custom
?start_date=2026-01-01
?end_date=2026-01-31
```

### 3.4 Payouts

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/vendor/payouts/` | Own payout history | `payout_requests` |
| POST | `/api/partner/vendor/payouts/request/` | Request payout | `payout_requests` |

**POST Request:**
```json
{
  "amount": 2000.00,
  "bank_name": "Sunrise Bank",
  "account_number": "9876543210",
  "account_holder_name": "Vendor Name"
}
```

### 3.5 Agreement

| Method | Endpoint | Description | Tables Affected |
|--------|----------|-------------|-----------------|
| GET | `/api/partner/vendor/agreement/` | Own revenue agreement | `station_revenue_shares` |

---

## 4. IoT Endpoints (Shared)

Base Path: `/api/internal/iot/`

**Authentication:** Any partner (Franchise or Vendor) with valid station access.

| Method | Endpoint | Description | Tables Affected | Permission |
|--------|----------|-------------|-----------------|------------|
| GET | `/api/internal/iot/history/` | Own IoT action history | `partner_iot_history` | All |
| POST | `/api/internal/iot/reboot/` | Reboot station | `partner_iot_history` | All |
| POST | `/api/internal/iot/check/` | Check station status | `partner_iot_history` | All |
| POST | `/api/internal/iot/wifi/scan/` | Scan WiFi networks | `partner_iot_history` | All |
| POST | `/api/internal/iot/wifi/connect/` | Connect to WiFi | `partner_iot_history` | All |
| POST | `/api/internal/iot/volume/` | Adjust volume | `partner_iot_history` | All |
| POST | `/api/internal/iot/mode/` | Switch SIM/WiFi mode | `partner_iot_history` | All |
| POST | `/api/internal/iot/eject/` | Eject powerbank | `partner_iot_history` | Franchise only |

**IoT Request (all actions):**
```json
{
  "station_id": "uuid",
  "slot_number": 3,       // Only for eject
  "wifi_ssid": "network", // Only for wifi/connect
  "wifi_password": "***"  // Only for wifi/connect
}
```

**Permission Matrix (BR13):**

| Action | ChargeGhar | Franchise | Vendor |
|--------|------------|-----------|--------|
| EJECT | ✅ Unlimited | ✅ Unlimited | ❌ (except 1 free/day via rental) |
| REBOOT | ✅ | ✅ | ✅ |
| CHECK | ✅ | ✅ | ✅ |
| WIFI_SCAN | ✅ | ✅ | ✅ |
| WIFI_CONNECT | ✅ | ✅ | ✅ |
| VOLUME | ✅ | ✅ | ✅ |
| MODE | ✅ | ✅ | ✅ |

---

## 5. User Search Endpoint (For Partner Creation)

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| GET | `/api/admin/users/` | Search users | Admin |
| GET | `/api/partner/franchise/users/search/` | Search users for vendor creation | Franchise |

**Query Parameters:**
```
?search={email|phone|name}
?exclude_partners=true   # Exclude users already partners
```

---

## 6. Existing Endpoints (Reused)

These existing admin endpoints are reused:

| Endpoint | Usage |
|----------|-------|
| `GET /api/admin/stations/` | List stations for assignment |
| `GET /api/admin/users/` | Search users for partner creation |

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized |
| 403 | Forbidden (no permission) |
| 404 | Not Found |
| 409 | Conflict (e.g., station already assigned) |

---

## Endpoint Summary Count

| Dashboard | Endpoints | Status |
|-----------|-----------|--------|
| Admin Partner Management | 6 | ✅ Implemented |
| Admin Station Distribution | 3 | ✅ Implemented |
| Admin Transactions | 2 | ⏳ Pending |
| Admin Payouts | 6 | ✅ Implemented |
| Admin Analytics | 3 | ⏳ Pending |
| **Admin Subtotal** | **20** | **15 Done / 5 Pending** |
| Franchise | 17 | ⏳ Pending |
| Vendor | 9 | ⏳ Pending |
| IoT (shared) | 8 | ⏳ Pending |
| **Total** | **54** | |

## Implementation Files

### Admin Partner Endpoints (Implemented)
- **Views:** `api/admin/views/partner_views.py`
- **Service:** `api/admin/services/admin_partner_service.py`
- **Serializers:** `api/admin/serializers/partner_serializers.py`

### Partner Auth (Implemented)
- **Views:** `api/partners/auth/views/`
- **Services:** `api/partners/auth/services/`
- **Serializers:** `api/partners/auth/serializers/`
