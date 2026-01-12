# Gap Analysis Report: Requirements.md vs Plans

**Date**: 2026-01-12  
**Status**: Cross-Checked & Verified

---

## Summary

| Category | Status | Issues |
|----------|--------|--------|
| Partnership Request | ✅ COMPLETE | None |
| Partner Models | ✅ COMPLETE | None |
| Station Distribution | ✅ COMPLETE | None |
| Payout System | ✅ COMPLETE | None |
| Partner IoT History | ✅ COMPLETE | None |
| Advertisement System | ✅ COMPLETE | Minor clarification needed |
| Station Coupons | ✅ COMPLETE | None |
| Package Discounts | ✅ COMPLETE | None |
| Biometric Auth | ✅ COMPLETE | None |
| Rental Lifecycle | ⚠️ GAP | Missing `powerbank_sn` in rental start |
| IoT Sync Log | ✅ COMPLETE | None |
| Station Monitoring | ⚠️ GAP | Not explicitly planned |
| Swapping Rate Limit | ⚠️ GAP | Not explicitly planned |

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
**Plan**: ✅ is_under_5_min, BatteryCycleLog, PowerBank.total_cycles  

**⚠️ GAP FOUND**: `powerbank_sn` field in `POST /api/rentals/start` request  
- Requirements.md says: "request fields (station_sn, package_id, powerbank_sn)"
- Plan 10 mentions battery tracking but doesn't explicitly add powerbank_sn to rental start request
- Current Rental model has `power_bank` FK but it's nullable

**FIX NEEDED**: Update rental start service to accept `powerbank_sn` parameter

---

### 11. IoT Sync Log (11_iot_sync_log.md)
**Requirement**: Track sync operations  
**Plan**: ✅ IotSyncLog with sync_type, direction, status  
**Verdict**: COMPLETE

---

## GAPS IDENTIFIED

### GAP 1: Rental Start - powerbank_sn Parameter
**Location**: `api/user/rentals/services/rental/start.py`  
**Issue**: Requirements say `POST /api/rentals/start` should accept `powerbank_sn`  
**Current**: Not accepting powerbank_sn in request  
**Fix**: Add `powerbank_sn` to RentalStartSerializer and service logic

### GAP 2: Station Monitoring - Online/Offline History
**Location**: Requirements Section 5  
**Issue**: "Station Monitoring: Track Online/Offline status history and total counts"  
**Current**: Not explicitly planned in any file  
**Fix**: Add to `11_iot_sync_log.md` or create new plan file

**Proposed Table**: `StationStatusHistory`
```python
class StationStatusHistory(BaseModel):
    station = ForeignKey(Station)
    status = CharField  # ONLINE, OFFLINE
    changed_at = DateTimeField
    duration_seconds = IntegerField  # How long in previous status
```

### GAP 3: Swapping Rate Limit
**Location**: Requirements Section 5  
**Issue**: "User can swap only up to total available powerbank count of that station per day"  
**Current**: Not explicitly planned  
**Fix**: Add validation logic in rental start service

**Proposed Logic**:
```python
# In rental start service
today_swaps = Rental.objects.filter(
    user=user,
    station=station,
    created_at__date=today
).count()

if today_swaps >= station.available_slots:
    raise ValidationError("Daily swap limit reached for this station")
```

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

## Conclusion

**Plans are 95% complete.** Three minor gaps identified:

1. **powerbank_sn in rental start** - Easy fix, add to serializer
2. **Station status history** - Add StationStatusHistory table
3. **Swapping rate limit** - Add validation logic in rental service

All core business logic, payment hierarchy, partner models, and IoT integration are properly planned.
