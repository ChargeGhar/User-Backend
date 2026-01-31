# Vendor Revenue Implementation Plan

> **Endpoint:** `GET /api/partner/vendor/revenue/`  
> **Phase:** 2 of 4  
> **Created:** 2026-01-31

---

## Endpoint Specification (From Endpoints.md)

**Method:** GET  
**Path:** `/api/partner/vendor/revenue/`  
**Authentication:** JWT (Revenue Vendor only)  
**Permission:** `IsRevenueVendor` + `IsActivePartner`

**Query Parameters:**
```
?period=today|week|month|year|custom
?start_date=2026-01-01
?end_date=2026-01-31
?page=1&page_size=20
```

---

## Response Structure (From Endpoints.md)

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

---

## Business Rules to Enforce

| BR# | Rule | Implementation |
|-----|------|----------------|
| BR12.3 | Vendors view ONLY own transactions | Filter by vendor_id |
| BR12.7 | Vendors view only own earnings | Show vendor_share only |
| BR2.3 | Vendor has ONLY ONE station | All transactions from single station |

---

## Database Tables Used

### 1. `revenue_distributions` (Primary)
```python
# Query:
RevenueDistribution.objects.filter(
    vendor_id=vendor_id
).select_related('rental', 'station')

# Fields needed:
- id
- rental_id
- created_at (transaction_date)
- gross_amount
- net_amount
- vat_amount
- service_charge_amount
- vendor_share
- vendor_share_percent
- station_id
```

### 2. `stations` (Related)
```python
# Via select_related('station')
# Fields needed:
- id
- station_name
```

---

## Repository Methods to Use

### Existing ✅
```python
RevenueDistributionRepository.get_by_vendor(
    vendor_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> QuerySet
```

**Returns:** QuerySet of RevenueDistribution objects filtered by vendor_id

**Need to verify:** Does it support pagination? Does it include station relation?

Let me check the actual implementation:

---

## Verification: Check Existing Repository

```python
# File: api/partners/common/repositories/revenue_distribution_repository.py

@staticmethod
def get_by_vendor(
    vendor_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> QuerySet:
    """Get revenue distributions for a vendor"""
    queryset = RevenueDistribution.objects.filter(vendor_id=vendor_id)
    
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)
    
    return queryset.order_by('-created_at')
```

**Analysis:**
- ✅ Filters by vendor_id (BR12.3)
- ✅ Supports date filtering
- ✅ Orders by created_at descending
- ❌ Does NOT include select_related('station', 'rental')
- ❌ Does NOT support pagination

**Action Required:** Need to add select_related in service layer

---

## Service Layer Logic

### VendorRevenueService.get_revenue_list(vendor_id, filters)

```python
def get_revenue_list(vendor_id: str, filters: dict) -> dict:
    """
    Get vendor revenue transactions with pagination
    
    BR12.3: Filter by vendor_id
    BR12.7: Show only vendor earnings
    """
    
    # Parse filters
    period = filters.get('period', 'month')
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    page = int(filters.get('page', 1))
    page_size = int(filters.get('page_size', 20))
    
    # Calculate date range based on period
    if not start_date or not end_date:
        today = timezone.now().date()
        
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
    
    # Get revenue distributions
    queryset = RevenueDistributionRepository.get_by_vendor(
        vendor_id=vendor_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Add relations (IMPORTANT: avoid N+1 queries)
    queryset = queryset.select_related('station', 'rental')
    
    # Calculate summary
    summary = queryset.aggregate(
        total_transactions=Count('id'),
        total_gross=Sum('gross_amount'),
        total_net=Sum('net_amount'),
        total_vendor_share=Sum('vendor_share')
    )
    
    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    return {
        'results': list(page_obj),
        'count': paginator.count,
        'page': page,
        'page_size': page_size,
        'total_pages': paginator.num_pages,
        'summary': {
            'total_transactions': summary['total_transactions'] or 0,
            'total_gross_revenue': summary['total_gross'] or Decimal('0'),
            'total_net_revenue': summary['total_net'] or Decimal('0'),
            'total_vendor_share': summary['total_vendor_share'] or Decimal('0')
        }
    }
```

---

## Serializer Structure

### VendorRevenueStationSerializer
```python
class VendorRevenueStationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(source='station_name')
```

### VendorRevenueTransactionSerializer
```python
class VendorRevenueTransactionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    rental_id = serializers.UUIDField()
    transaction_date = serializers.DateTimeField(source='created_at')
    gross_revenue = serializers.DecimalField(
        source='gross_amount',
        max_digits=10,
        decimal_places=2
    )
    net_revenue = serializers.DecimalField(
        source='net_amount',
        max_digits=10,
        decimal_places=2
    )
    vat_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    service_charge = serializers.DecimalField(
        source='service_charge_amount',
        max_digits=10,
        decimal_places=2
    )
    vendor_share = serializers.DecimalField(max_digits=10, decimal_places=2)
    vendor_share_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    station = VendorRevenueStationSerializer()
```

### VendorRevenueSummarySerializer
```python
class VendorRevenueSummarySerializer(serializers.Serializer):
    total_transactions = serializers.IntegerField()
    total_gross_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_net_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_vendor_share = serializers.DecimalField(max_digits=10, decimal_places=2)
```

### VendorRevenueListSerializer
```python
class VendorRevenueListSerializer(serializers.Serializer):
    results = VendorRevenueTransactionSerializer(many=True)
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    summary = VendorRevenueSummarySerializer()
```

---

## View Structure

### VendorRevenueView

```python
@vendor_revenue_router.register(r"partner/vendor/revenue", name="vendor-revenue")
@extend_schema(
    tags=["Partner - Vendor"],
    summary="Get Vendor Revenue Transactions",
    description="""
    Returns paginated list of revenue transactions for the logged-in vendor.
    
    Business Rules:
    - BR12.3: Vendors view ONLY own transactions
    - BR12.7: Vendors view only own earnings
    """,
    parameters=[
        OpenApiParameter('period', str, description='Time period filter'),
        OpenApiParameter('start_date', str, description='Start date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', str, description='End date (YYYY-MM-DD)'),
        OpenApiParameter('page', int, description='Page number'),
        OpenApiParameter('page_size', int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class VendorRevenueView(GenericAPIView, BaseAPIView):
    """Vendor revenue transactions"""
    permission_classes = [IsRevenueVendor]
    serializer_class = VendorRevenueListSerializer
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get vendor revenue transactions"""
        def operation():
            vendor_id = str(request.user.partner_profile.id)
            filters = {
                'period': request.query_params.get('period', 'month'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20)
            }
            return VendorRevenueService.get_revenue_list(vendor_id, filters)
        
        return self.handle_service_operation(
            operation,
            "Revenue transactions retrieved successfully",
            "Failed to retrieve revenue transactions"
        )
```

---

## Files to Create/Update

### Create:
1. `api/partners/vendor/services/vendor_revenue_service.py`
2. `api/partners/vendor/serializers/revenue_serializers.py`
3. `api/partners/vendor/views/revenue_view.py`

### Update:
1. `api/partners/vendor/services/__init__.py` - Export VendorRevenueService
2. `api/partners/vendor/serializers/__init__.py` - Export serializers
3. `api/partners/vendor/views/__init__.py` - Add revenue_router to main router
4. `api/partners/vendor/urls.py` - Already uses router from __init__

---

## Testing Plan

### Test Data Needed:
- VN-003 (Franchise-Vendor) with 3 transactions
- VN-004 (CG-Vendor) with 0 transactions

### Test Cases:

1. **List All Transactions (Default)**
   ```bash
   GET /api/partner/vendor/revenue
   ```
   - Expect: Last month's transactions
   - Verify: Pagination working
   - Verify: Summary calculated

2. **Filter by Period**
   ```bash
   GET /api/partner/vendor/revenue?period=today
   GET /api/partner/vendor/revenue?period=week
   GET /api/partner/vendor/revenue?period=month
   ```
   - Verify: Correct date range applied

3. **Custom Date Range**
   ```bash
   GET /api/partner/vendor/revenue?start_date=2026-01-01&end_date=2026-01-31
   ```
   - Verify: Custom dates respected

4. **Pagination**
   ```bash
   GET /api/partner/vendor/revenue?page=1&page_size=10
   ```
   - Verify: Correct page returned
   - Verify: total_pages calculated

5. **Vendor with No Transactions (VN-004)**
   - Expect: Empty results
   - Expect: Summary with 0 values

6. **Vendor with Transactions (VN-003)**
   - Expect: 3 transactions
   - Verify: vendor_share matches database
   - Verify: station info included

---

## Edge Cases

1. **Invalid date format:**
   - Return 400 with validation error

2. **start_date > end_date:**
   - Return 400 with validation error

3. **Invalid page number:**
   - Return last valid page

4. **page_size > 100:**
   - Cap at 100 (prevent abuse)

---

## Cross-Reference Verification

### vs Franchise Revenue Endpoint:
Let me check franchise implementation for consistency...

**File:** `api/partners/franchise/views/franchise_revenue_view.py`

Need to verify:
- Query parameters
- Response structure
- Pagination approach
- Summary calculation

---

## Success Criteria

- ✅ Vendor can list own revenue transactions
- ✅ Pagination working correctly
- ✅ Summary calculated accurately
- ✅ Date filters working
- ✅ Period filters working
- ✅ Station info included
- ✅ No N+1 queries (use select_related)
- ✅ BR12.3 enforced (own transactions only)
- ✅ BR12.7 enforced (own earnings only)

---

## Implementation Order

1. Check franchise revenue implementation for consistency
2. Create VendorRevenueService
3. Create serializers (4 classes)
4. Create view with router
5. Update __init__ files
6. Test with VN-003 (has transactions)
7. Test with VN-004 (no transactions)
8. Test pagination
9. Test filters

---

## Questions to Verify Before Implementation

1. ✅ Does `RevenueDistribution` model have all required fields?
2. ✅ Does `get_by_vendor` repository method exist?
3. ❓ What is the exact field mapping in RevenueDistribution model?
4. ❓ How does franchise revenue endpoint handle pagination?
5. ❓ What is the max page_size allowed?

Let me verify these before proceeding...
