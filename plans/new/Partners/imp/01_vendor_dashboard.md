# Vendor Dashboard Implementation Plan

> **Endpoint:** `GET /api/partner/vendor/dashboard/`  
> **Phase:** 1 of 4  
> **Created:** 2026-01-31

---

## Endpoint Specification

**Method:** GET  
**Path:** `/api/partner/vendor/dashboard/`  
**Authentication:** JWT (Revenue Vendor only)  
**Permission:** `IsRevenueVendor` + `IsActivePartner`

---

## Response Structure (From Endpoints.md)

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
  "today": {
    "transactions": 10,
    "revenue": 500.00,
    "my_share": 50.00
  },
  "this_week": {
    "transactions": 60,
    "revenue": 3000.00,
    "my_share": 300.00
  },
  "this_month": {
    "transactions": 250,
    "revenue": 12500.00,
    "my_share": 1250.00
  }
}
```

---

## Business Rules to Enforce

| BR# | Rule | Implementation |
|-----|------|----------------|
| BR2.3 | Vendor has ONLY ONE station | Get single station from `station_distributions` |
| BR9.2 | Revenue Vendors have dashboard access | Use `IsRevenueVendor` permission |
| BR9.4 | Non-Revenue Vendors have NO dashboard | Block with 403 if vendor_type != REVENUE |
| BR10.4 | Vendors view ONLY own station | Filter by vendor partner_id |
| BR12.3 | Vendors view ONLY own transactions | Filter revenue by vendor_id |
| BR12.7 | Vendors view only own earnings | Show vendor.balance and total_earnings |

---

## Database Tables Used

### 1. `partners` (Primary)
```python
# Fields needed:
- id (vendor_id)
- balance (Decimal)
- total_earnings (Decimal)
- vendor_type (must be REVENUE)
- status (must be ACTIVE)
```

### 2. `station_distributions`
```python
# Query:
StationDistribution.objects.filter(
    partner_id=vendor_id,
    distribution_type=FRANCHISE_TO_VENDOR or CHARGEGHAR_TO_VENDOR,
    is_active=True
).first()  # BR2.3: Only ONE station

# Fields needed:
- station_id
- distribution_type
```

### 3. `stations`
```python
# Fields needed:
- id
- station_name
- serial_number
```

### 4. `revenue_distributions`
```python
# Query for today:
RevenueDistribution.objects.filter(
    vendor_id=vendor_id,
    transaction_date__date=today
).aggregate(
    total_transactions=Count('id'),
    total_revenue=Sum('net_revenue'),
    vendor_share=Sum('vendor_share')
)

# Fields needed:
- vendor_id
- transaction_date
- net_revenue
- vendor_share
```

### 5. `payout_requests`
```python
# Query for pending:
PayoutRequest.objects.filter(
    partner_id=vendor_id,
    status='PENDING'
).aggregate(
    pending_amount=Sum('amount')
)

# Fields needed:
- partner_id
- status
- amount
```

---

## Service Layer Logic

### VendorDashboardService.get_dashboard_stats(vendor_id)

```python
def get_dashboard_stats(vendor_id: str) -> dict:
    """
    Get vendor dashboard statistics
    
    BR2.3: Vendor has ONLY ONE station
    BR12.3: Filter revenue by vendor_id
    BR12.7: Show only own earnings
    """
    
    # 1. Get vendor
    vendor = PartnerRepository.get_by_id(vendor_id)
    if not vendor.is_revenue_vendor:
        raise PermissionDenied("Non-revenue vendors have no dashboard access")
    
    # 2. Get vendor's single station (BR2.3)
    distribution = StationDistributionRepository.get_by_partner(vendor_id)
    if not distribution:
        station_info = None
    else:
        station = distribution.station
        station_info = {
            "id": str(station.id),
            "name": station.station_name,
            "code": station.serial_number
        }
    
    # 3. Get pending payout
    pending_payout = PayoutRequestRepository.get_pending_amount(vendor_id)
    
    # 4. Get revenue stats
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    today_stats = RevenueDistributionRepository.get_summary_by_vendor(
        vendor_id=vendor_id,
        start_date=today,
        end_date=today
    )
    
    week_stats = RevenueDistributionRepository.get_summary_by_vendor(
        vendor_id=vendor_id,
        start_date=week_start,
        end_date=today
    )
    
    month_stats = RevenueDistributionRepository.get_summary_by_vendor(
        vendor_id=vendor_id,
        start_date=month_start,
        end_date=today
    )
    
    return {
        "balance": vendor.balance,
        "total_earnings": vendor.total_earnings,
        "pending_payout": pending_payout,
        "station": station_info,
        "today": {
            "transactions": today_stats['transaction_count'],
            "revenue": today_stats['total_revenue'],
            "my_share": today_stats['vendor_share']
        },
        "this_week": {
            "transactions": week_stats['transaction_count'],
            "revenue": week_stats['total_revenue'],
            "my_share": week_stats['vendor_share']
        },
        "this_month": {
            "transactions": month_stats['transaction_count'],
            "revenue": month_stats['total_revenue'],
            "my_share": month_stats['vendor_share']
        }
    }
```

---

## Repository Methods Needed

### Existing (Reuse) ✅
- `PartnerRepository.get_by_id(partner_id)` ✅
- `StationDistributionRepository.get_by_partner(partner_id)` ✅
- `PayoutRequestRepository.get_pending_amount(partner_id)` ✅
- `RevenueDistributionRepository.get_summary_by_vendor(vendor_id, start_date, end_date)` ✅

### To Verify
Need to check if `get_summary_by_vendor` exists and returns:
```python
{
    'transaction_count': int,
    'total_revenue': Decimal,
    'vendor_share': Decimal
}
```

---

## Serializer Structure

### VendorDashboardSerializer

```python
class VendorStationInfoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()

class VendorRevenueStatsSerializer(serializers.Serializer):
    transactions = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    my_share = serializers.DecimalField(max_digits=10, decimal_places=2)

class VendorDashboardSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_payout = serializers.DecimalField(max_digits=10, decimal_places=2)
    station = VendorStationInfoSerializer(allow_null=True)
    today = VendorRevenueStatsSerializer()
    this_week = VendorRevenueStatsSerializer()
    this_month = VendorRevenueStatsSerializer()
```

---

## View Structure

### VendorDashboardView

```python
class VendorDashboardView(GenericAPIView, BaseAPIView):
    permission_classes = [IsAuthenticated, IsRevenueVendor, IsActivePartner]
    serializer_class = VendorDashboardSerializer
    
    @extend_schema(
        summary="Vendor Dashboard",
        description="Get vendor dashboard statistics (balance, earnings, station, revenue)",
        responses={200: VendorDashboardSerializer}
    )
    def get(self, request: Request) -> Response:
        @service_call
        def operation():
            vendor_id = request.user.partner_profile.id
            stats = VendorDashboardService.get_dashboard_stats(vendor_id)
            return stats
        
        return operation()
```

---

## Permission Classes

### IsRevenueVendor (To Create)

```python
class IsRevenueVendor(BasePermission):
    """
    Permission: User must be a REVENUE vendor
    BR9.2: Revenue Vendors have dashboard access
    BR9.4: Non-Revenue Vendors have NO dashboard
    """
    
    def has_permission(self, request, view):
        if not hasattr(request.user, 'partner_profile'):
            return False
        
        partner = request.user.partner_profile
        return (
            partner.partner_type == Partner.PartnerType.VENDOR and
            partner.vendor_type == Partner.VendorType.REVENUE
        )
```

---

## Files to Create/Update

### Create:
1. `api/partners/vendor/services/vendor_dashboard_service.py`
2. `api/partners/vendor/serializers/dashboard_serializers.py`
3. `api/partners/vendor/views/dashboard_view.py`
4. `api/partners/common/permissions.py` (add IsRevenueVendor)

### Update:
1. `api/partners/vendor/services/__init__.py` - Export service
2. `api/partners/vendor/serializers/__init__.py` - Export serializers
3. `api/partners/vendor/views/__init__.py` - Export view
4. `api/partners/vendor/urls.py` - Register router

---

## Testing Plan

### Test Data Needed:
- Revenue Vendor (VN-003) with:
  - balance > 0
  - total_earnings > 0
  - 1 assigned station
  - Some revenue transactions
  - Optional: pending payout

### Test Cases:

1. **Revenue Vendor Access** ✅
   - Login as VN-003
   - GET /api/partner/vendor/dashboard/
   - Expect: 200 with dashboard data

2. **Non-Revenue Vendor Blocked** ✅
   - Login as non-revenue vendor
   - GET /api/partner/vendor/dashboard/
   - Expect: 403 Forbidden

3. **Single Station Display** ✅
   - Verify station object has id, name, code
   - Verify only ONE station shown (BR2.3)

4. **Revenue Stats Accuracy** ✅
   - Verify today/week/month calculations
   - Verify vendor_share matches revenue_distributions

5. **Balance Display** ✅
   - Verify balance matches partner.balance
   - Verify total_earnings matches partner.total_earnings

---

## Edge Cases

1. **Vendor with no station:**
   - station: null
   - revenue stats: 0

2. **Vendor with no transactions:**
   - All stats: 0
   - But balance/total_earnings may be > 0

3. **Vendor with no pending payout:**
   - pending_payout: 0.00

---

## Cross-Reference Verification

### vs Franchise Dashboard:
- ✅ Similar structure (balance, earnings, stats)
- ✅ Different: Single station (not list)
- ✅ Different: No vendor management
- ✅ Different: Simpler stats (no vendor breakdown)

### vs Business Rules:
- ✅ BR2.3: Single station enforced
- ✅ BR9.2/9.4: Revenue vendor check
- ✅ BR10.4: Own station only
- ✅ BR12.3: Own transactions only
- ✅ BR12.7: Own earnings only

### vs Endpoints.md:
- ✅ Response structure matches exactly
- ✅ All fields present
- ✅ Correct data types

---

## Implementation Order

1. Create `IsRevenueVendor` permission
2. Create `VendorDashboardService`
3. Create serializers
4. Create view
5. Register URLs
6. Test with VN-003
7. Test edge cases

---

## Success Criteria

- ✅ Revenue vendor can access dashboard
- ✅ Non-revenue vendor gets 403
- ✅ Single station displayed (BR2.3)
- ✅ Revenue stats accurate
- ✅ Balance/earnings correct
- ✅ Pending payout calculated
- ✅ All business rules enforced
