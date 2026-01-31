# Partnership System - API Endpoints

> **Version:** 3.0  
> **Last Updated:** 2026-01-31  
> **Status:** Core dashboard COMPLETE (44/44) ✅ | Admin revenue + IoT actions PENDING (9)

---

## Implementation Progress

| Category | Implemented | Total | Progress |
|----------|-------------|-------|----------|
| Admin | 16 | 17 | 94% ⚠️ |
| Franchise | 19 | 19 | 100% ✅ |
| Vendor | 9 | 9 | 100% ✅ |
| IoT | 1 | 8 | 13% ⚠️ |
| **TOTAL** | **45** | **53** | **85%** |

**Pending:**
- 1 Admin revenue endpoint
- 7 IoT action endpoints (hardware control)
- 1 Admin IoT history endpoint

---

## Overview

Three dashboard types with distinct access levels:
- **Admin Dashboard** (ChargeGhar) - Full system control
- **Franchise Dashboard** - Own stations + own vendors  
- **Vendor Dashboard** - Own station only (Revenue vendors only)

---

## 1. Admin Dashboard Endpoints - 16/17 ⚠️

Base Path: `/api/admin/partners/`

### 1.1 Partner Management - 8/8 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/` | List all partners | ✅ |
| GET | `/api/admin/partners/{id}/` | Partner details | ✅ |
| POST | `/api/admin/partners/franchise/` | Create franchise | ✅ |
| POST | `/api/admin/partners/vendor/` | Create vendor | ✅ |
| PATCH | `/api/admin/partners/{id}/` | Update partner | ✅ |
| PATCH | `/api/admin/partners/{id}/status/` | Update status | ✅ |
| PATCH | `/api/admin/partners/{id}/reset-password/` | Reset password | ✅ |
| PATCH | `/api/admin/partners/{id}/vendor-type/` | Change vendor type | ✅ |

### 1.2 Station Distribution - 3/3 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/stations/` | List distributions | ✅ |
| GET | `/api/admin/partners/stations/available/` | Available stations | ✅ |
| DELETE | `/api/admin/partners/stations/{id}/` | Deactivate distribution | ✅ |

### 1.3 Revenue - 0/1 ⏳

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/revenue/` | All partner transactions | ⏳ PENDING |

**Query Parameters:**
- `station_id`, `franchise_id`, `vendor_id`
- `chargeghar_only=true` (stations with no partner)
- `period`, `start_date`, `end_date`
- `page`, `page_size`

### 1.4 Payout Management - 6/6 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/admin/partners/payouts/` | List payouts | ✅ |
| GET | `/api/admin/partners/payouts/{id}/` | Payout details | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/approve/` | Approve | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/process/` | Process | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/complete/` | Complete | ✅ |
| PATCH | `/api/admin/partners/payouts/{id}/reject/` | Reject | ✅ |

---

## 2. Franchise Dashboard Endpoints - 19/19 ✅

Base Path: `/api/partner/franchise/`

### 2.1 Common - 4/4 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partners/auth/me` | Profile | ✅ |
| GET | `/api/partner/iot/history` | IoT history | ✅ |
| GET | `/api/partner/stations/` | Stations list | ✅ |
| GET | `/api/partner/stations/{id}/` | Station detail | ✅ |

### 2.2 Dashboard - 1/1 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partner/franchise/dashboard/` | Dashboard stats | ✅ |

### 2.3 Vendor Management - 6/6 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partner/franchise/vendors/` | List vendors | ✅ |
| GET | `/api/partner/franchise/vendors/{id}/` | Vendor details | ✅ |
| POST | `/api/partner/franchise/vendors/` | Create vendor | ✅ |
| PATCH | `/api/partner/franchise/vendors/{id}/` | Update vendor | ✅ |
| PATCH | `/api/partner/franchise/vendors/{id}/status/` | Update status | ✅ |
| GET | `/api/partner/franchise/users/search/` | Search users | ✅ |

### 2.4 Revenue & Payouts - 7/7 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partner/franchise/revenue/` | Revenue transactions | ✅ |
| GET | `/api/partner/franchise/payouts/` | Own payouts | ✅ |
| POST | `/api/partner/franchise/payouts/request/` | Request payout | ✅ |
| GET | `/api/partner/franchise/payouts/vendors/` | Vendor payouts | ✅ |
| PATCH | `/api/partner/franchise/payouts/vendors/{id}/approve/` | Approve | ✅ |
| PATCH | `/api/partner/franchise/payouts/vendors/{id}/complete/` | Complete | ✅ |
| PATCH | `/api/partner/franchise/payouts/vendors/{id}/reject/` | Reject | ✅ |

### 2.5 Agreements - 1/1 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partner/franchise/agreements/` | View agreements | ✅ |

---

## 3. Vendor Dashboard Endpoints - 9/9 ✅

Base Path: `/api/partner/vendor/`

### 3.1 Common - 4/4 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partners/auth/me` | Profile | ✅ |
| GET | `/api/partner/iot/history` | IoT history | ✅ |
| GET | `/api/partner/stations/` | Stations list | ✅ |
| GET | `/api/partner/stations/{id}/` | Station detail | ✅ |

### 3.2 Vendor-Specific - 5/5 ✅

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/api/partner/vendor/dashboard/` | Dashboard stats | ✅ |
| GET | `/api/partner/vendor/revenue/` | Revenue transactions | ✅ |
| GET | `/api/partner/vendor/payouts/` | Payout history | ✅ |
| POST | `/api/partner/vendor/payouts/request/` | Request payout | ✅ |
| GET | `/api/partner/vendor/agreement/` | View agreement | ✅ |

---

## 4. IoT Endpoints - 1/8 ⚠️

### 4.1 IoT History - 1/1 ✅

| Method | Endpoint | Description | Who | Status |
|--------|----------|-------------|-----|--------|
| GET | `/api/partner/iot/history` | Partner IoT history | Franchise/Vendor | ✅ |
| GET | `/api/admin/iot/history` | All IoT history | Admin | ⏳ PENDING |

### 4.2 IoT Actions - 0/7 ⏳

Base Path: `/api/internal/iot/`

| Method | Endpoint | Description | Permission | Status |
|--------|----------|-------------|------------|--------|
| POST | `/api/internal/iot/reboot/` | Reboot station | All | ⏳ |
| POST | `/api/internal/iot/check/` | Check status | All | ⏳ |
| POST | `/api/internal/iot/wifi/scan/` | Scan WiFi | All | ⏳ |
| POST | `/api/internal/iot/wifi/connect/` | Connect WiFi | All | ⏳ |
| POST | `/api/internal/iot/volume/` | Adjust volume | All | ⏳ |
| POST | `/api/internal/iot/mode/` | Switch mode | All | ⏳ |
| POST | `/api/internal/iot/eject/` | Eject powerbank | Franchise only | ⏳ |

---

## Summary

**Implemented:** 45/53 endpoints (85%)

**Core Dashboard:** 44/44 (100%) ✅
- All partner management complete
- All payout workflows working
- All revenue tracking functional

**Pending:** 9 endpoints
- 1 Admin revenue reporting
- 1 Admin IoT history
- 7 IoT hardware actions
**Status:** Core functionality production-ready ✅
