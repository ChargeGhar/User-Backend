# ChargeGhar Platform - Requirements & Business Rules

> **Document Version:** 4.0  
> **Last Updated:** January 2026  
> **Status:** Aligned with Current Implementation + Future Roadmap

---

## Document Structure

This document is organized into:
1. **IMPLEMENTED** - Features that exist in the current codebase
2. **PARTIALLY IMPLEMENTED** - Features with partial support
3. **NOT IMPLEMENTED (ROADMAP)** - Features planned for future development

---

## 1. User Management

### 1.1 Authentication (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| OTP-based Login/Register | ✅ | `api/user/auth/views/auth_views.py` |
| Google OAuth | ✅ | `api/user/auth/views/social_auth_views.py` |
| Apple OAuth | ✅ | `api/user/auth/views/social_auth_views.py` |
| JWT Token Management | ✅ | SimpleJWT integration |
| Device Registration (FCM) | ✅ | `UserDevice` model |
| Referral Code System | ✅ | `User.referral_code` field |

### 1.2 User Profile (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Profile Management | ✅ | `UserProfile` model |
| KYC Verification | ✅ | `UserKYC` model with document upload |
| Avatar/Profile Picture | ✅ | `User.profile_picture` field |

### 1.3 Biometric Authentication (❌ NOT IMPLEMENTED)

| Feature | Status | Notes |
|---------|--------|-------|
| Fingerprint Login | ❌ | Requires device-generated token API |
| Face ID Login | ❌ | Requires device-generated token API |

**Implementation Requirement:**
- Add `biometric_token` field to `UserDevice` model
- Create `/api/auth/biometric/verify` endpoint
- Token generated on device, validated server-side

---

## 2. Station Management

### 2.1 Station Core (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Station CRUD | ✅ | `Station` model |
| Station Status (Online/Offline/Maintenance) | ✅ | `Station.status` field |
| GPS Location | ✅ | `latitude`, `longitude` fields |
| Operating Hours | ✅ | `opening_time`, `closing_time` fields |
| Hardware Info | ✅ | `hardware_info` JSONField |
| Heartbeat Tracking | ✅ | `last_heartbeat` field |

### 2.2 Station Slots (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Slot Management | ✅ | `StationSlot` model |
| Slot Status Tracking | ✅ | `status`, `battery_level` fields |
| Slot Metadata | ✅ | `slot_metadata` JSONField |

### 2.3 Station Amenities (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Amenity Types | ✅ | `StationAmenity` model |
| Station-Amenity Mapping | ✅ | `StationAmenityMapping` model |

### 2.4 Station Issues (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Issue Reporting | ✅ | `StationIssue` model |
| Issue Assignment | ✅ | `assigned_to` FK to User |
| Issue Status Tracking | ✅ | `status`, `priority` fields |

### 2.5 Station Monitoring (⚠️ PARTIAL)

| Feature | Status | Notes |
|---------|--------|-------|
| Online/Offline Status | ✅ | Via `status` field |
| Status History Tracking | ❌ | Need `StationStatusHistory` model |
| Rental Counts (Rented/Overdue/Cancelled/Ongoing) | ⚠️ | Calculated via queries, not cached |

**Implementation Requirement:**
```python
class StationStatusHistory(BaseModel):
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True, blank=True)
```

---

## 3. PowerBank Management

### 3.1 PowerBank Core (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| PowerBank CRUD | ✅ | `PowerBank` model |
| Status Tracking | ✅ | `status` field (Available/Rented/Maintenance/Damaged) |
| Battery Level | ✅ | `battery_level` field |
| Current Location | ✅ | `current_station`, `current_slot` FKs |

### 3.2 Battery Lifecycle Tracking (❌ NOT IMPLEMENTED)

| Feature | Status | Notes |
|---------|--------|-------|
| Charge Cycle Count | ❌ | Need `total_cycles` field |
| Battery Health % | ❌ | Need `battery_health` field |
| Return Battery Level Logging | ❌ | Need to log in rental metadata |

**Business Rule:** 1 Cycle = 100% to 0% discharge

**Implementation Requirement:**
```python
# Add to PowerBank model:
total_cycles = models.IntegerField(default=0)
battery_health = models.IntegerField(default=100)  # Percentage

# Add to Rental model or rental_metadata:
battery_level_at_start = models.IntegerField(null=True)
battery_level_at_return = models.IntegerField(null=True)
```

---

## 4. Rental System

### 4.1 Rental Core (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Rental CRUD | ✅ | `Rental` model |
| Rental Status | ✅ | `status` field (Pending/Active/Completed/Cancelled/Overdue) |
| Payment Status | ✅ | `payment_status` field |
| Rental Packages | ✅ | `RentalPackage` model |
| Rental Extensions | ✅ | `RentalExtension` model |
| Rental Issues | ✅ | `RentalIssue` model |
| GPS Tracking | ✅ | `RentalLocation` model |

### 4.2 Late Fee System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Late Fee Configuration | ✅ | `LateFeeConfiguration` model |
| Grace Period | ✅ | `grace_period_minutes` field |
| Fee Calculation | ✅ | `LateFeeService` |
| Max Daily Rate Cap | ✅ | `max_daily_rate` field |

### 4.3 5-Minute Return Rule (❌ NOT IMPLEMENTED)

| Feature | Status | Notes |
|---------|--------|-------|
| Quick Return Detection | ❌ | Need service logic |
| Faulty Bank Flagging | ❌ | Need notification trigger |
| Payment Adjustment | ❌ | Need refund logic |

**Business Rule:** If powerbank returned within 5 minutes, flag as potential issue.

**Implementation Requirement:**
```python
# In RentalService.end_rental():
if (ended_at - started_at).total_seconds() < 300:  # 5 minutes
    # Flag rental as quick_return
    rental.rental_metadata['quick_return'] = True
    # Trigger notification to admin
    # Consider automatic refund
```

### 4.4 Swap Rate Limiting (❌ NOT IMPLEMENTED)

| Feature | Status | Notes |
|---------|--------|-------|
| Daily Swap Limit per Station | ❌ | Need tracking model |

**Business Rule:** User can swap up to `station.total_slots` times per day at each station.

**Implementation Requirement:**
```python
class UserStationSwapLimit(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    date = models.DateField()
    swap_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'station', 'date']
```

---

## 5. Payment System

### 5.1 Payment Core (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Transactions | ✅ | `Transaction` model |
| Payment Methods | ✅ | `PaymentMethod` model |
| Payment Intents | ✅ | `PaymentIntent` model |
| Refunds | ✅ | `Refund` model |

### 5.2 Wallet System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| User Wallet | ✅ | `Wallet` model |
| Wallet Transactions | ✅ | `WalletTransaction` model |
| Top-up | ✅ | Via payment gateway |

### 5.3 Withdrawal System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Withdrawal Requests | ✅ | `WithdrawalRequest` model |
| Withdrawal Limits | ✅ | `WithdrawalLimit` model |
| Processing Fee | ✅ | `processing_fee` field |

---

## 6. Points & Rewards

### 6.1 Points System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| User Points | ✅ | `UserPoints` model |
| Points Transactions | ✅ | `PointsTransaction` model |
| Timely Return Bonus | ✅ | `timely_return_bonus_awarded` field |

### 6.2 Referral System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Referral Tracking | ✅ | `Referral` model |
| Referral Code | ✅ | `User.referral_code` field |
| Points Award | ✅ | `inviter_points_awarded`, `invitee_points_awarded` |

### 6.3 Achievements (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Achievement Definitions | ✅ | `Achievement` model |
| User Achievements | ✅ | `UserAchievement` model |
| Leaderboard | ✅ | `UserLeaderboard` model |

---

## 7. Promotions & Coupons

### 7.1 Coupon System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Coupon CRUD | ✅ | `Coupon` model |
| Coupon Usage Tracking | ✅ | `CouponUsage` model |
| Usage Limits | ✅ | `max_uses_per_user` field |
| Validity Period | ✅ | `valid_from`, `valid_until` fields |

### 7.2 Station-Specific Coupons (❌ NOT IMPLEMENTED)

| Feature | Status | Notes |
|---------|--------|-------|
| Station-Coupon Mapping | ❌ | Need junction table |

**Implementation Requirement:**
```python
class CouponStationRestriction(BaseModel):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['coupon', 'station']
```

### 7.3 Package Discounts (❌ NOT IMPLEMENTED)

| Feature | Status | Notes |
|---------|--------|-------|
| Station-Package Discounts | ❌ | Need discount model |

**Implementation Requirement:**
```python
class StationPackageDiscount(BaseModel):
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    package = models.ForeignKey(RentalPackage, on_delete=models.CASCADE)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_uses = models.IntegerField(null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
```

---

## 8. Content Management

### 8.1 Static Content (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Content Pages | ✅ | `ContentPage` model |
| FAQs | ✅ | `FAQ` model |
| Contact Info | ✅ | `ContactInfo` model |
| Banners | ✅ | `Banner` model |

### 8.2 App Management (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| App Config | ✅ | `AppConfig` model |
| App Versions | ✅ | `AppVersion` model |
| App Updates | ✅ | `AppUpdate` model |

---

## 9. Notifications

### 9.1 Notification System (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Notification Templates | ✅ | `NotificationTemplate` model |
| Notification Rules | ✅ | `NotificationRule` model |
| User Notifications | ✅ | `Notification` model |
| SMS/FCM Logs | ✅ | `SMS_FCMLog` model |

---

## 10. Admin System

### 10.1 Admin Core (✅ IMPLEMENTED)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Admin Profiles | ✅ | `AdminProfile` model |
| Admin Action Logs | ✅ | `AdminActionLog` model |
| System Logs | ✅ | `SystemLog` model |
| Audit Logs | ✅ | `AuditLog` model |

---

## 11. Vendor & Franchise System (❌ NOT IMPLEMENTED)

> **Note:** This is a major feature requiring new models and business logic.

### 11.1 Franchise Model

**Business Rules:**
- Franchise pays upfront amount for X stations
- Franchise pays percentage of earnings to ChargeGhar
- Franchise can request payouts when balance is sufficient
- VAT & Service Charges deducted at ChargeGhar level

**Required Models:**
```python
class Franchise(BaseModel):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    upfront_amount = models.DecimalField(max_digits=12, decimal_places=2)
    station_quota = models.IntegerField()
    revenue_share_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    agreement_start = models.DateField()
    agreement_end = models.DateField()
    status = models.CharField(max_length=50)  # ACTIVE, EXPIRED, SUSPENDED
    
class FranchiseStation(BaseModel):
    franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

class FranchiseBalance(BaseModel):
    franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    chargeghar_share = models.DecimalField(max_digits=12, decimal_places=2)
    available_balance = models.DecimalField(max_digits=12, decimal_places=2)
    
class FranchisePayoutRequest(BaseModel):
    franchise = models.ForeignKey(Franchise, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    vat_deducted = models.DecimalField(max_digits=12, decimal_places=2)
    service_charge = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50)  # PENDING, APPROVED, REJECTED, PAID
```

### 11.2 Vendor Model

**Business Rules:**
- Vendors never pay upfront
- Assigned by Admin or Franchise
- Revenue options: Share % OR Fixed Rent %
- Revenue Vendor: Has dashboard + payout features
- Non-Revenue Vendor: Physical presence only, no dashboard

**Required Models:**
```python
class Vendor(BaseModel):
    class VendorType(models.TextChoices):
        REVENUE = 'revenue', 'Revenue Vendor'
        NON_REVENUE = 'non_revenue', 'Non-Revenue Vendor'
    
    class RevenueModel(models.TextChoices):
        SHARE_PERCENTAGE = 'share', 'Share Percentage'
        FIXED_RENT = 'fixed', 'Fixed Rent'
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    franchise = models.ForeignKey(Franchise, on_delete=models.SET_NULL, null=True, blank=True)
    vendor_type = models.CharField(max_length=50, choices=VendorType.choices)
    revenue_model = models.CharField(max_length=50, choices=RevenueModel.choices, null=True)
    revenue_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    is_direct_vendor = models.BooleanField(default=False)  # Reports to ChargeGhar directly
    
class VendorStation(BaseModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

class VendorBalance(BaseModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    available_balance = models.DecimalField(max_digits=12, decimal_places=2)

class VendorPayoutRequest(BaseModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # No VAT deduction for franchise->vendor payouts
    status = models.CharField(max_length=50)
```

### 11.3 Vendor Powerbank Ejection Perk

**Business Rule:** Every vendor can eject 1 powerbank for free, 1 at a time, per day.

**Required Model:**
```python
class VendorDailyEjection(BaseModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    date = models.DateField()
    ejected_at = models.DateTimeField(null=True)
    powerbank = models.ForeignKey(PowerBank, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ['vendor', 'date']
```

### 11.4 Payment Distribution Flow

```
User Payment
    │
    ▼
ChargeGhar Main Account
    │
    ├──► Direct Vendor (VAT + Service Charge deducted)
    │
    └──► Franchise (VAT + Service Charge deducted)
              │
              └──► Sub-Vendor (NO VAT deduction - internal distribution)
```

---

## 12. Advertisement System (❌ NOT IMPLEMENTED)

### 12.1 Ad Request Workflow

**Business Rules:**
1. User submits ad request in app
2. Admin verifies and coordinates manually
3. Admin inserts price and approves/denies
4. User sees "Pay" status and pays via app
5. Ad becomes "Running"

**Required Models:**
```python
class AdRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        PRICE_SET = 'price_set', 'Price Set - Awaiting Payment'
        PAID = 'paid', 'Paid'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    media_url = models.CharField(max_length=500)
    target_stations = models.ManyToManyField(Station, blank=True)
    requested_start = models.DateTimeField()
    requested_end = models.DateTimeField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    
    # Admin sets these
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    admin_notes = models.TextField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_ads')
    
    # After payment
    actual_start = models.DateTimeField(null=True)
    actual_end = models.DateTimeField(null=True)

class AdPayment(BaseModel):
    ad_request = models.ForeignKey(AdRequest, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
```

### 12.2 Hardware Display Support

**Business Rule:** Approved ads can be displayed on station screens.

**Required API:**
- `GET /api/internal/stations/{serial_number}/ads` - Returns active ads for station display

---

## 13. User Attribution (❌ NOT IMPLEMENTED)

**Business Rule:** Ability to assign existing users to specific Vendors or Franchises.

**Required Model:**
```python
class UserAttribution(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    franchise = models.ForeignKey(Franchise, on_delete=models.SET_NULL, null=True)
    attributed_at = models.DateTimeField(auto_now_add=True)
    attributed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='attributions_made')
```

---

## Summary: Implementation Priority

### Phase 1 - Quick Wins (Low Effort)
1. ✅ 5-Minute Return Rule - Service logic only
2. ✅ Battery Level Logging - Add fields to existing models
3. ✅ Station Status History - New simple model

### Phase 2 - Medium Effort
1. ⚠️ Station-Specific Coupons - Junction table
2. ⚠️ Package Discounts - New model
3. ⚠️ Swap Rate Limiting - New tracking model
4. ⚠️ Biometric Auth - New endpoint + device token

### Phase 3 - Major Features
1. ❌ Vendor System - New app with models, views, services
2. ❌ Franchise System - New app with models, views, services
3. ❌ Advertisement System - New app with workflow
4. ❌ Payment Distribution - Complex business logic

---

## Appendix: Current Model Count

| Category | Models | Status |
|----------|--------|--------|
| User | 6 | ✅ Complete |
| Station | 7 | ✅ Complete |
| Rental | 5 | ✅ Complete |
| Payment | 8 | ✅ Complete |
| Points | 3 | ✅ Complete |
| Social | 3 | ✅ Complete |
| Promotions | 2 | ⚠️ Needs extension |
| Content | 4 | ✅ Complete |
| System | 4 | ✅ Complete |
| Admin | 3 | ✅ Complete |
| Notifications | 4 | ✅ Complete |
| **Total** | **51** | - |

**New Models Required:** ~15-20 for Vendor/Franchise/Ads

---

*Document maintained by ChargeGhar Development Team*
