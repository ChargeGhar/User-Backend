# Gap Analysis Report: Requirements.md vs Plans

**Date**: 2026-01-13  
**Status**: Cross-Checked & Verified

---

## Summary

| Category | Status | Issues |
|----------|--------|--------|
| Partnership Request | ✅ COMPLETE | None |
| Partner Models | ✅ COMPLETE | None |
| Station Distribution | ✅ COMPLETE | None |
| Payout System | ✅ COMPLETE | AppConfig keys added |
| Partner IoT History | ✅ COMPLETE | None |
| Advertisement System | ✅ COMPLETE | None |
| Station Coupons | ✅ COMPLETE | None |
| Package Discounts | ✅ COMPLETE | None |
| Biometric Auth | ✅ COMPLETE | None |
| Rental Lifecycle | ✅ COMPLETE | powerbank_sn added |
| IoT Sync Log | ✅ COMPLETE | Station monitoring added |
| Station Monitoring | ✅ COMPLETE | Added to 11_iot_sync_log.md |
| Swapping Rate Limit | ✅ COMPLETE | Added to 10_rental_lifecycle.md |

---

## AppConfig Keys Required

Add to `api/user/system/fixtures/app_config.json`:

| Key | Value | Description | Used In |
|-----|-------|-------------|---------|
| `PLATFORM_VAT_PERCENT` | `13` | VAT % for Chargeghar-level payouts | `04_payout_system.md` |
| `PLATFORM_SERVICE_CHARGE_PERCENT` | `2.5` | Service charge % for Chargeghar-level payouts | `04_payout_system.md` |

**Important**: These are ONLY applied to Chargeghar-level payouts (to Franchise/Direct Vendor), NOT Franchise-level payouts (to Sub-Vendors).

---

## Detailed Gap Analysis

### 1. Partnership Request (01_partnership_request.md)
**Requirement**: Mobile app sends (Full Name, Contact Number, Subject, Message)  
**Plan**: ✅ All fields covered  
**Verdict**: COMPLETE

---

### 2. Partner Models (02_partner_models.md)
**Requirement**: Franchise (upfront, quota, revenue %), Vendor (Revenue/Non-Revenue, under Franchise or direct)  
**Plan**: ✅ All covered with proper FK relationships  
**Verdict**: COMPLETE

---

### 3. Station Distribution (03_station_distribution.md)
**Requirement**: Chargeghar→Franchise, Chargeghar→Vendor, Franchise→SubVendor  
**Plan**: ✅ StationDistribution + StationRevenueShare + StationHierarchy  
**Verdict**: COMPLETE

---

### 4. Payout System (04_payout_system.md)
**Requirement**: VAT/Service deduction for CG-level, NO deduction for Franchise-level  
**Plan**: ✅ PayoutRequest with payout_type logic, RevenueDistribution for tracing  
**AppConfig**: ✅ `PLATFORM_VAT_PERCENT`, `PLATFORM_SERVICE_CHARGE_PERCENT`  
**Logic**:
- `CHARGEGHAR_TO_FRANCHISE` → DEDUCT VAT & Service Charge
- `CHARGEGHAR_TO_VENDOR` → DEDUCT VAT & Service Charge  
- `FRANCHISE_TO_VENDOR` → NO deductions (internal distribution)
**Verdict**: COMPLETE

---

### 5. Partner IoT History (05_partner_iot_history.md)
**Requirement**: Track EJECT/REBOOT/CHECK/WIFI_SETTINGS for both partner types  
**Plan**: ✅ PartnerIotHistory with all action types, free ejection tracking  
**Verdict**: COMPLETE

---

### 6. Advertisement System (06_advertisement.md)
**Requirement**: User submits → Admin sets price → User pays → Ad runs → Sync to Java API  
**Plan**: ✅ AdRequest (workflow), AdContent (media), AdStation (targeting), AdDistribution (sync)  
**IoT Response Format**: ✅ Matches manufacturer spec (url1, url2, playTime, etc.)  
**Verdict**: COMPLETE

---

### 7. Station Coupons (07_station_coupons.md)
**Requirement**: Coupons can be global OR station-specific  
**Plan**: ✅ CouponStation junction table, is_station_specific flag  
**API Updates**: ✅ POST /api/promotions/coupons/apply, GET /api/promotions/coupons/active  
**Verdict**: COMPLETE

---

### 8. Package Discounts (08_station_package_discounts.md)
**Requirement**: Station-specific discounts on packages  
**Plan**: ✅ StationPackageDiscount + StationPackageDiscountUsage  
**API Updates**: ✅ GET /api/rentals/packages, POST /api/rentals/start  
**Verdict**: COMPLETE

---

### 9. Biometric Auth (09_biometric_auth.md)
**Requirement**: POST /auth/biometric/enable, POST /auth/biometric/login  
**Plan**: ✅ Device-bound token approach, UserDevice updates  
**Fields**: biometric_enabled, biometric_token, biometric_registered_at, biometric_last_used_at  
**Verdict**: COMPLETE

---

### 10. Rental Lifecycle (10_rental_lifecycle.md)
**Requirement**: 5-min rule, battery cycle tracking, powerbank_sn in rental start  
**Plan**: ✅ is_under_5_min, BatteryCycleLog, PowerBank.total_cycles, powerbank_sn param  
**Verdict**: COMPLETE

---

### 11. IoT Sync Log (11_iot_sync_log.md)
**Requirement**: Track sync operations, Station Online/Offline history  
**Plan**: ✅ IotSyncLog + StationStatusHistory  
**Verdict**: COMPLETE

---

## API Endpoint Updates Summary

| Endpoint | Update Needed | Plan File |
|----------|---------------|-----------|
| `POST /api/rentals/start` | Add powerbank_sn, vendor check, discount check | 05, 08, 10 |
| `GET /api/rentals/packages` | Add station_sn param, return discounts | 08 |
| `POST /api/promotions/coupons/apply` | Add station_sn validation | 07 |
| `GET /api/promotions/coupons/active` | Add station_sn filter | 07 |
| `POST /api/auth/biometric/enable` | New endpoint | 09 |
| `POST /api/auth/biometric/login` | New endpoint | 09 |
| `GET /api/internal/ads/distribute` | New IoT endpoint | 06 |

---

## Model Updates Summary

| Model | Field | Type | Plan |
|-------|-------|------|------|
| Coupon | is_station_specific | BooleanField | 07 |
| CouponUsage | station | FK(Station) | 07 |
| UserDevice | biometric_enabled | BooleanField | 09 |
| UserDevice | biometric_token | CharField(512) | 09 |
| UserDevice | biometric_registered_at | DateTimeField | 09 |
| UserDevice | biometric_last_used_at | DateTimeField | 09 |
| Rental | return_battery_level | IntegerField | 10 |
| Rental | start_battery_level | IntegerField | 10 |
| Rental | is_under_5_min | BooleanField | 10 |
| Rental | hardware_issue_reported | BooleanField | 10 |
| PowerBank | total_cycles | DecimalField | 10 |
| PowerBank | total_rentals | IntegerField | 10 |

---

## Fixture Updates Required

### `api/user/system/fixtures/app_config.json`

Add these entries:

```json
{
  "model": "system.appconfig",
  "fields": {
    "key": "PLATFORM_VAT_PERCENT",
    "value": "13",
    "description": "VAT percentage deducted from Chargeghar-level payouts (to Franchise/Direct Vendor). NOT applied to Franchise-level payouts.",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
},
{
  "model": "system.appconfig",
  "fields": {
    "key": "PLATFORM_SERVICE_CHARGE_PERCENT",
    "value": "2.5",
    "description": "Service charge percentage deducted from Chargeghar-level payouts. NOT applied to Franchise-level payouts.",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

---

## Conclusion

**Plans are 100% complete.** All requirements from Requirements.md are covered:

- VAT & Service Charge logic properly documented with AppConfig integration
- Deduction rules clearly defined per payout type
- All gaps identified in previous analysis have been fixed

Ready for implementation.
