# Database Implementation Plan - Summary

**Version**: 2.1  
**Date**: 2026-01-12  
**Status**: Final - Gap Analysis Complete

---

## Overview

This folder contains modular database plans for all requirements. Each file covers one feature area.

---

## File Index

| File | Feature | App | Priority |
|------|---------|-----|----------|
| `01_partnership_request.md` | Partnership Request | `api/vendor/` | Phase 1 |
| `02_partner_models.md` | Partner, Franchise, Vendor | `api/vendor/` | Phase 1 |
| `03_station_distribution.md` | Station Distribution & Revenue | `api/vendor/` | Phase 1 |
| `04_payout_system.md` | Payout & Revenue Distribution | `api/vendor/` | Phase 1 |
| `05_partner_iot_history.md` | Partner IoT Actions | `api/vendor/` | Phase 1 |
| `06_advertisement.md` | Advertisement System | `api/user/advertisements/` | Phase 2 |
| `07_station_coupons.md` | Station-Specific Coupons | `api/user/promotions/` | Phase 2 |
| `08_station_package_discounts.md` | Station Package Discounts | `api/user/rentals/` | Phase 2 |
| `09_biometric_auth.md` | Biometric Authentication | `api/user/auth/` | Phase 2 |
| `10_rental_lifecycle.md` | Rental Enhancements | `api/user/rentals/` | Phase 2 |
| `11_iot_sync_log.md` | IoT Sync & Station Monitoring | `api/internal/` | Phase 2 |
| `GAP_ANALYSIS.md` | Gap Analysis Report | - | - |

---

## New Tables Summary

### Phase 1 - Partner System (api/vendor/)

| Table | Description |
|-------|-------------|
| `partnership_requests` | Partnership request submissions |
| `partners` | Base partner model |
| `franchises` | Franchise-specific data |
| `vendors` | Vendor-specific data |
| `station_distributions` | Station-partner assignments |
| `station_revenue_shares` | Revenue share configuration |
| `station_hierarchies` | Denormalized station ownership |
| `payout_requests` | Payout request tracking |
| `revenue_distributions` | Per-transaction revenue splits |
| `partner_iot_history` | IoT action logging |

### Phase 2 - User Features

| Table | Description |
|-------|-------------|
| `ad_requests` | Advertisement requests |
| `ad_contents` | Ad media content |
| `ad_stations` | Ad-station targeting |
| `ad_distributions` | IoT ad sync tracking |
| `coupon_stations` | Station-specific coupons |
| `station_package_discounts` | Station package discounts |
| `station_package_discount_usages` | Discount usage tracking |
| `battery_cycle_logs` | Battery lifecycle tracking |
| `iot_sync_logs` | IoT sync logging |
| `station_status_history` | Station online/offline tracking |

---

## Model Updates Summary

| Model | Updates |
|-------|---------|
| `Coupon` | Add `is_station_specific` |
| `CouponUsage` | Add `station` FK |
| `UserDevice` | Add biometric fields |
| `Rental` | Add battery tracking fields |
| `PowerBank` | Add `total_cycles`, `total_rentals` |

---

## Migration Order

1. **Phase 1A**: Create `api/vendor/` app with Partner, Franchise, Vendor
2. **Phase 1B**: Create StationDistribution, StationRevenueShare, StationHierarchy
3. **Phase 1C**: Create PayoutRequest, RevenueDistribution
4. **Phase 1D**: Create PartnershipRequest, PartnerIotHistory
5. **Phase 2A**: Create `api/user/advertisements/` app
6. **Phase 2B**: Update Coupon, create CouponStation
7. **Phase 2C**: Create StationPackageDiscount
8. **Phase 2D**: Update UserDevice with biometric fields
9. **Phase 2E**: Update Rental, PowerBank, create BatteryCycleLog
10. **Phase 2F**: Create IotSyncLog

---

## AppConfig Keys Required

Add to `api/user/system/fixtures/app_config.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `PLATFORM_VAT_PERCENT` | `13` | VAT % for Chargeghar-level payouts only |
| `PLATFORM_SERVICE_CHARGE_PERCENT` | `2.5` | Service charge % for Chargeghar-level payouts only |

**Rule**: These are ONLY applied to `CHARGEGHAR_TO_FRANCHISE` and `CHARGEGHAR_TO_VENDOR` payouts. NOT applied to `FRANCHISE_TO_VENDOR` payouts (internal distributions).

---

## Cross-Reference: Requirements.md

| Requirement | Covered In | Status |
|-------------|------------|--------|
| Partnership Request | `01_partnership_request.md` | ✅ |
| Franchise Model | `02_partner_models.md` | ✅ |
| Vendor Model | `02_partner_models.md` | ✅ |
| Payment Hierarchy | `03_station_distribution.md`, `04_payout_system.md` | ✅ |
| VAT/Service Charge | `04_payout_system.md` | ✅ |
| Vendor Free Ejection | `05_partner_iot_history.md` | ✅ |
| Franchise IoT Control | `05_partner_iot_history.md` | ✅ |
| Advertisement Workflow | `06_advertisement.md` | ✅ |
| Station Coupons | `07_station_coupons.md` | ✅ |
| Package Discounts | `08_station_package_discounts.md` | ✅ |
| Biometric Auth | `09_biometric_auth.md` | ✅ |
| 5-Minute Rule | `10_rental_lifecycle.md` | ✅ |
| Battery Cycle Tracking | `10_rental_lifecycle.md` | ✅ |
| powerbank_sn in rental | `10_rental_lifecycle.md` | ✅ |
| Swapping Rate Limit | `10_rental_lifecycle.md` | ✅ |
| IoT Sync Logging | `11_iot_sync_log.md` | ✅ |
| Station Monitoring | `11_iot_sync_log.md` | ✅ |

---

## Gap Analysis

See `GAP_ANALYSIS.md` for detailed cross-check report.

**Result**: All requirements from Requirements.md are now covered.
