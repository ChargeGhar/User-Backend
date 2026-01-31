# Endpoint Plan: Franchise Dashboard

> **Endpoint:** `GET /api/partner/franchise/dashboard/`  
> **Version:** 1.0  
> **Created:** 2026-01-31  
> **Status:** Ready for Review

---

## 1. Endpoint Specification

| Attribute | Value |
|-----------|-------|
| Method | GET |
| Path | `/api/partner/franchise/dashboard/` |
| Authentication | JWT (Partner Token) |
| Permission | `IsFranchise` (partner_type = FRANCHISE, status = ACTIVE) |
| Description | Returns aggregated dashboard statistics for the logged-in franchise |

---

## 2. Business Rules Mapping

| BR# | Rule | How This Endpoint Implements |
|-----|------|------------------------------|
| BR3.5 | Franchise revenue_share_percent | Display in response |
| BR7.1 | Franchise receives y% of their stations' net revenue | Aggregate in `franchise_share` |
| BR10.2 | Franchise controls ONLY own vendors/stations | Filter all queries by franchise_id |
| BR12.2 | Franchise views ONLY own station transactions | Filter revenue_distributions by franchise_id |

---

## 3. Schema Mapping

### Tables Queried

| Table | Fields Used | Purpose |
|-------|-------------|---------|
| `partners` | id, balance, total_earnings, revenue_share_percent | Franchise profile data |
| `partners` (child) | COUNT where parent_id = franchise_id | vendors_count |
| `station_distributions` | COUNT where partner_id = franchise_id, is_active = TRUE | stations_count |
| `revenue_distributions` | SUM(franchise_share), COUNT | Transaction aggregates |
| `payout_requests` | SUM(amount) where status = PENDING | pending_payout |

### Query Flow

```
1. Get franchise from request.user.partner_profile
2. Query partners.balance, partners.total_earnings, partners.revenue_share_percent
3. COUNT partners WHERE parent_id = franchise_id AND partner_type = VENDOR
4. COUNT station_distributions WHERE partner_id = franchise_id AND is_active = TRUE
5. SUM payout_requests.amount WHERE partner_id = franchise_id AND status = PENDING
6. Aggregate revenue_distributions for today/week/month:
   - WHERE franchise_id = franchise_id
   - GROUP BY period
   - SUM(gross_amount), COUNT(id), SUM(franchise_share)
```

---

## 4. Response Schema

```json
{
  "success": true,
  "message": "Dashboard retrieved successfully",
  "data": {
    "profile": {
      "id": "uuid",
      "code": "FR-001",
      "business_name": "Kathmandu Franchise",
      "status": "ACTIVE",
      "revenue_share_percent": "20.00"
    },
    "balance": "15000.00",
    "total_earnings": "150000.00",
    "pending_payout": "5000.00",
    "stations_count": 5,
    "vendors_count": 3,
    "today": {
      "transactions": 25,
      "gross_revenue": "2500.00",
      "my_share": "500.00"
    },
    "this_week": {
      "transactions": 150,
      "gross_revenue": "15000.00",
      "my_share": "3000.00"
    },
    "this_month": {
      "transactions": 600,
      "gross_revenue": "60000.00",
      "my_share": "12000.00"
    }
  }
}
```

---

## 5. Implementation Details

### 5.1 File Structure

```
api/partners/franchise/
├── serializers/
│   └── dashboard_serializers.py   # NEW
├── services/
│   └── franchise_service.py       # NEW
├── views/
│   └── dashboard_view.py          # NEW
└── urls.py                        # UPDATE
```

### 5.2 Service Layer

**File:** `api/partners/franchise/services/franchise_service.py`

```python
class FranchiseService(BaseService):
    """Service for Franchise dashboard operations"""
    
    def get_dashboard_stats(self, franchise: Partner) -> dict:
        """
        Get aggregated dashboard statistics for franchise.
        
        Args:
            franchise: The Partner object (must be FRANCHISE type)
            
        Returns:
            dict with dashboard statistics
        """
        # Implementation steps:
        # 1. Validate franchise is actually a FRANCHISE
        # 2. Get base profile data from franchise object
        # 3. Count vendors under this franchise
        # 4. Count active stations assigned to this franchise
        # 5. Sum pending payout requests
        # 6. Aggregate revenue for today/week/month
        pass
```

### 5.3 View Layer

**File:** `api/partners/franchise/views/dashboard_view.py`

```python
@franchise_router.register(r"partner/franchise/dashboard", name="franchise-dashboard")
class FranchiseDashboardView(GenericAPIView, BaseAPIView):
    """Franchise dashboard statistics"""
    permission_classes = [IsFranchise]
    
    @extend_schema(
        tags=["Franchise Dashboard"],
        summary="Get Dashboard Statistics",
        description="Returns aggregated statistics for the logged-in franchise",
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get franchise dashboard stats"""
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseService()
            return service.get_dashboard_stats(franchise)
        
        return self.handle_service_operation(
            operation,
            "Dashboard retrieved successfully",
            "Failed to retrieve dashboard"
        )
```

### 5.4 Serializer

**File:** `api/partners/franchise/serializers/dashboard_serializers.py`

```python
class FranchiseProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    status = serializers.CharField()
    revenue_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2)

class PeriodStatsSerializer(serializers.Serializer):
    transactions = serializers.IntegerField()
    gross_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    my_share = serializers.DecimalField(max_digits=12, decimal_places=2)

class FranchiseDashboardSerializer(serializers.Serializer):
    profile = FranchiseProfileSerializer()
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_payout = serializers.DecimalField(max_digits=12, decimal_places=2)
    stations_count = serializers.IntegerField()
    vendors_count = serializers.IntegerField()
    today = PeriodStatsSerializer()
    this_week = PeriodStatsSerializer()
    this_month = PeriodStatsSerializer()
```

---

## 6. Database Queries (Detailed)

### 6.1 Vendors Count
```python
vendors_count = Partner.objects.filter(
    parent_id=franchise.id,
    partner_type=Partner.PartnerType.VENDOR
).count()
```

### 6.2 Stations Count
```python
stations_count = StationDistribution.objects.filter(
    partner_id=franchise.id,
    distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE,
    is_active=True
).count()
```

### 6.3 Pending Payout
```python
from django.db.models import Sum, Coalesce
from decimal import Decimal

pending_payout = PayoutRequest.objects.filter(
    partner_id=franchise.id,
    status=PayoutRequest.Status.PENDING
).aggregate(
    total=Coalesce(Sum('amount'), Decimal('0'))
)['total']
```

### 6.4 Revenue Aggregation
```python
from django.utils import timezone
from datetime import timedelta

def get_period_stats(franchise_id: str, start_date, end_date) -> dict:
    """Get revenue stats for a date range"""
    from django.db.models import Sum, Count, Coalesce
    from decimal import Decimal
    
    result = RevenueDistribution.objects.filter(
        franchise_id=franchise_id,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        is_reversal=False  # Exclude reversals
    ).aggregate(
        transactions=Count('id'),
        gross_revenue=Coalesce(Sum('gross_amount'), Decimal('0')),
        my_share=Coalesce(Sum('franchise_share'), Decimal('0'))
    )
    
    return {
        'transactions': result['transactions'],
        'gross_revenue': result['gross_revenue'],
        'my_share': result['my_share']
    }

# Usage:
today = timezone.now().date()
week_start = today - timedelta(days=today.weekday())  # Monday
month_start = today.replace(day=1)

today_stats = get_period_stats(franchise.id, today, today)
week_stats = get_period_stats(franchise.id, week_start, today)
month_stats = get_period_stats(franchise.id, month_start, today)
```

---

## 7. Permission Validation

### Pre-checks (In View/Permission Class)
1. User is authenticated (JWT valid)
2. User has `partner_profile` attribute
3. `partner_profile.partner_type == 'FRANCHISE'`
4. `partner_profile.status == 'ACTIVE'`

### Existing Permission Class to Use
```python
# From api/partners/auth/permissions.py
class IsFranchise(IsActivePartner):
    """Partner is a Franchise"""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.partner_profile.partner_type == 'FRANCHISE'
```

---

## 8. Error Scenarios

| Error | Code | Response |
|-------|------|----------|
| Not authenticated | 401 | "Authentication credentials were not provided" |
| Not a partner | 403 | "You do not have permission to perform this action" |
| Not a franchise | 403 | "Only franchises can access this endpoint" |
| Partner suspended | 403 | "Your account is suspended" |

---

## 9. Testing Plan

### 9.1 Test Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 1 | Valid franchise login, get dashboard | 200, returns all stats |
| 2 | Vendor trying to access | 403, permission denied |
| 3 | Suspended franchise | 403, account suspended |
| 4 | No transactions yet | 200, zeros for revenue |
| 5 | Admin user (not partner) | 403, not a partner |

### 9.2 Test Data Requirements
- 1 Franchise partner (ACTIVE)
- 2-3 Vendors under franchise
- 3-5 Stations assigned to franchise
- Some revenue_distributions records
- 1 Pending payout request

### 9.3 API Test (curl)
```bash
# Login as franchise first
curl -X POST 'http://localhost:8010/api/partners/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"email": "janak@powerbank.com", "password": "5060"}'

# Get dashboard with token
curl -X GET 'http://localhost:8010/api/partner/franchise/dashboard/' \
  -H 'Authorization: Bearer <access_token>'
```

---

## 10. Cross-Reference Checklist

- [x] Business Rules.md - BR3.5, BR7.1, BR10.2, BR12.2
- [x] schema.md - partners, station_distributions, revenue_distributions, payout_requests
- [x] schema_mapping.md - Field lifecycle for all tables
- [x] Endpoints.md - Section 2.1 Dashboard specification
- [x] partners_auth.md - IsFranchise permission class

---

## 11. Dependencies

### Existing Code to Import
```python
from api.common.services.base import BaseService
from api.common.mixins import BaseAPIView
from api.partners.auth.permissions import IsFranchise
from api.partners.common.models import (
    Partner,
    StationDistribution,
    RevenueDistribution,
    PayoutRequest
)
from api.partners.common.repositories import (
    PartnerRepository,
    StationDistributionRepository,
    RevenueDistributionRepository,
    PayoutRequestRepository
)
```

---

## 12. Implementation Steps

1. Create `api/partners/franchise/serializers/__init__.py`
2. Create `api/partners/franchise/serializers/dashboard_serializers.py`
3. Create `api/partners/franchise/services/__init__.py`
4. Create `api/partners/franchise/services/franchise_service.py`
5. Update `api/partners/franchise/views/__init__.py`
6. Create `api/partners/franchise/views/dashboard_view.py`
7. Update `api/partners/franchise/urls.py`
8. Register URLs in main app urls
9. Test endpoint manually
10. Write automated tests

---

## 13. Approval Required

**Questions for Review:**

1. Is the response structure correct per frontend requirements?
2. Should `my_share` include both franchise_share AND vendor_share for vendors under this franchise?
3. Do we need to exclude `is_reversal=True` records from revenue aggregation?
4. Should pending_payout include only own payouts or also sub-vendor payouts pending this franchise's approval?

---

## Reviewer Notes

_Space for review comments_

---

**Status:** Awaiting Review

**Next Step After Approval:** Implementation
