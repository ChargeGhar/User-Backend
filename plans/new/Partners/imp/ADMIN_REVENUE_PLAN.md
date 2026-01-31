# PLAN: Admin Revenue Endpoint - 100% Auditable

## OBJECTIVE
Create `GET /api/admin/revenue` endpoint for admin to view ALL revenue distributions across the entire platform with complete transaction and rental details for full auditability and accountability.

## CURRENT STATE ANALYSIS

### Existing Models (Verified)
✅ **RevenueDistribution** - Primary revenue tracking table
- Fields: transaction, rental, station, gross_amount, vat_amount, service_charge, net_amount
- Shares: chargeghar_share, franchise_share, vendor_share
- Partners: franchise (FK), vendor (FK)
- Status: is_distributed, distributed_at
- Audit: calculation_details (JSON), is_reversal, reversed_distribution, reversal_reason
- Timestamps: created_at, updated_at

✅ **Transaction** - Payment records
- Fields: user, related_rental, amount, status, payment_method_type, gateway_reference

✅ **Rental** - Rental sessions
- Fields: user, station, powerbank, start_time, end_time, status

✅ **Station** - Station details
- Fields: station_name, serial_number, location, address

✅ **Partner** - Franchise/Vendor details
- Fields: code, business_name, partner_type, contact_person, phone

### Existing Repository
✅ **RevenueDistributionRepository.filter_distributions()**
- Supports: station_id, franchise_id, vendor_id, chargeghar_only, start_date, end_date, is_distributed
- Returns: QuerySet with select_related('station', 'franchise', 'vendor', 'transaction')

### Existing Partner Endpoints (Reference)
✅ Franchise Revenue: `/api/partner/franchise/revenue` - Own stations only
✅ Vendor Revenue: `/api/partner/vendor/revenue` - Own stations only

## REQUIREMENT

**Endpoint:** `GET /api/admin/revenue`

**Purpose:** Admin views ALL revenue distributions across entire platform with complete auditable data

**Business Rules:**
- BR4.1-3: All transactions collected by ChargeGhar
- BR5.1-5: VAT & Service Charge deducted per transaction
- BR6.1-3: ChargeGhar station revenue distribution
- BR7.1-5: Franchise station revenue distribution
- BR11.1-5: Financial calculation rules

## AUDITABLE DATA REQUIREMENTS

### Core Financial Data (MUST HAVE)
1. **Transaction Details**
   - Transaction ID (unique identifier)
   - Transaction amount
   - Transaction status
   - Payment method
   - Gateway reference
   - Transaction date

2. **Revenue Breakdown**
   - Gross amount (total charged)
   - VAT amount (deducted)
   - Service charge (deducted)
   - Net amount (distributable)
   - ChargeGhar share
   - Franchise share (if applicable)
   - Vendor share (if applicable)

3. **Rental Context**
   - Rental ID
   - Rental status
   - Start time
   - End time
   - Duration

4. **User Information**
   - User ID
   - User email
   - User name

5. **Station Information**
   - Station ID
   - Station name
   - Serial number
   - Location

6. **Partner Information**
   - Franchise: code, name, type (if applicable)
   - Vendor: code, name, type (if applicable)

7. **Distribution Status**
   - Is distributed (boolean)
   - Distributed at (timestamp)

8. **Audit Trail**
   - Calculation details (JSON)
   - Is reversal (boolean)
   - Reversal reason (if applicable)
   - Reversed distribution ID (if applicable)
   - Created at
   - Updated at

## IMPLEMENTATION PLAN

### 1. Create Admin Revenue Service
**Location:** `api/admin/services/admin_revenue_service.py` (NEW FILE)

**Method:** `get_all_revenue(filters: Dict) -> Dict`

**Logic:**
```python
from api.common.utils.helpers import paginate_queryset
from api.partners.common.repositories import RevenueDistributionRepository
from django.db.models import Sum, Count

def get_all_revenue(filters: Dict) -> Dict:
    # Use existing repository with all filters
    queryset = RevenueDistributionRepository.filter_distributions(
        station_id=filters.get('station_id'),
        franchise_id=filters.get('franchise_id'),
        vendor_id=filters.get('vendor_id'),
        chargeghar_only=filters.get('chargeghar_only', False),
        start_date=filters.get('start_date'),
        end_date=filters.get('end_date'),
        is_distributed=filters.get('is_distributed')
    ).select_related(
        'transaction__user',  # Get user who paid
        'rental',  # Get rental details
        'station',  # Get station details
        'franchise',  # Get franchise details
        'vendor'  # Get vendor details
    )
    
    # Additional filters
    if filters.get('transaction_status'):
        queryset = queryset.filter(transaction__status=filters['transaction_status'])
    
    if filters.get('is_reversal') is not None:
        queryset = queryset.filter(is_reversal=filters['is_reversal'])
    
    # Calculate summary
    summary = queryset.aggregate(
        total_transactions=Count('id'),
        total_gross=Sum('gross_amount'),
        total_vat=Sum('vat_amount'),
        total_service_charge=Sum('service_charge'),
        total_net=Sum('net_amount'),
        total_chargeghar_share=Sum('chargeghar_share'),
        total_franchise_share=Sum('franchise_share'),
        total_vendor_share=Sum('vendor_share')
    )
    
    # Paginate
    page = int(filters.get('page', 1))
    page_size = int(filters.get('page_size', 20))
    paginated = paginate_queryset(queryset, page, page_size)
    
    # Format results with complete auditable data
    paginated['results'] = [_format_revenue_item(item) for item in paginated['results']]
    paginated['summary'] = summary
    
    return paginated

def _format_revenue_item(rd) -> Dict:
    """Format single revenue distribution with complete audit data"""
    return {
        # Revenue Distribution
        'id': str(rd.id),
        'created_at': rd.created_at.isoformat(),
        'updated_at': rd.updated_at.isoformat(),
        
        # Transaction Details
        'transaction': {
            'id': str(rd.transaction.id),
            'amount': rd.transaction.amount,
            'status': rd.transaction.status,
            'payment_method': rd.transaction.payment_method_type,
            'gateway_reference': rd.transaction.gateway_reference,
            'created_at': rd.transaction.created_at.isoformat(),
        },
        
        # User Details
        'user': {
            'id': rd.transaction.user.id,
            'email': rd.transaction.user.email,
            'username': rd.transaction.user.username,
        },
        
        # Rental Details (if exists)
        'rental': {
            'id': str(rd.rental.id),
            'status': rd.rental.status,
            'start_time': rd.rental.start_time.isoformat(),
            'end_time': rd.rental.end_time.isoformat() if rd.rental.end_time else None,
        } if rd.rental else None,
        
        # Station Details
        'station': {
            'id': str(rd.station.id),
            'station_name': rd.station.station_name,
            'serial_number': rd.station.serial_number,
            'location': rd.station.location,
        },
        
        # Financial Breakdown
        'financial': {
            'gross_amount': rd.gross_amount,
            'vat_amount': rd.vat_amount,
            'service_charge': rd.service_charge,
            'net_amount': rd.net_amount,
            'chargeghar_share': rd.chargeghar_share,
            'franchise_share': rd.franchise_share,
            'vendor_share': rd.vendor_share,
        },
        
        # Partner Details
        'franchise': {
            'id': str(rd.franchise.id),
            'code': rd.franchise.code,
            'business_name': rd.franchise.business_name,
            'partner_type': rd.franchise.partner_type,
        } if rd.franchise else None,
        
        'vendor': {
            'id': str(rd.vendor.id),
            'code': rd.vendor.code,
            'business_name': rd.vendor.business_name,
            'partner_type': rd.vendor.partner_type,
        } if rd.vendor else None,
        
        # Distribution Status
        'distribution': {
            'is_distributed': rd.is_distributed,
            'distributed_at': rd.distributed_at.isoformat() if rd.distributed_at else None,
        },
        
        # Audit Trail
        'audit': {
            'is_reversal': rd.is_reversal,
            'reversal_reason': rd.reversal_reason,
            'reversed_distribution_id': str(rd.reversed_distribution_id) if rd.reversed_distribution_id else None,
            'calculation_details': rd.calculation_details,
        },
    }
```

### 2. Create Admin Revenue Serializers
**Location:** `api/admin/serializers/admin_revenue_serializers.py` (NEW FILE)

**Serializers:**
```python
class AdminRevenueTransactionSerializer(serializers.Serializer):
    """Transaction details"""
    id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField()
    payment_method = serializers.CharField()
    gateway_reference = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()

class AdminRevenueUserSerializer(serializers.Serializer):
    """User who made payment"""
    id = serializers.IntegerField()
    email = serializers.EmailField()
    username = serializers.CharField()

class AdminRevenueRentalSerializer(serializers.Serializer):
    """Rental session details"""
    id = serializers.UUIDField()
    status = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(allow_null=True)

class AdminRevenueStationSerializer(serializers.Serializer):
    """Station details"""
    id = serializers.UUIDField()
    station_name = serializers.CharField()
    serial_number = serializers.CharField()
    location = serializers.CharField()

class AdminRevenueFinancialSerializer(serializers.Serializer):
    """Financial breakdown"""
    gross_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    service_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    chargeghar_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    franchise_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    vendor_share = serializers.DecimalField(max_digits=12, decimal_places=2)

class AdminRevenuePartnerSerializer(serializers.Serializer):
    """Partner details"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    partner_type = serializers.CharField()

class AdminRevenueDistributionSerializer(serializers.Serializer):
    """Distribution status"""
    is_distributed = serializers.BooleanField()
    distributed_at = serializers.DateTimeField(allow_null=True)

class AdminRevenueAuditSerializer(serializers.Serializer):
    """Audit trail"""
    is_reversal = serializers.BooleanField()
    reversal_reason = serializers.CharField(allow_blank=True)
    reversed_distribution_id = serializers.UUIDField(allow_null=True)
    calculation_details = serializers.JSONField()

class AdminRevenueItemSerializer(serializers.Serializer):
    """Complete revenue item with all auditable data"""
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    transaction = AdminRevenueTransactionSerializer()
    user = AdminRevenueUserSerializer()
    rental = AdminRevenueRentalSerializer(allow_null=True)
    station = AdminRevenueStationSerializer()
    financial = AdminRevenueFinancialSerializer()
    franchise = AdminRevenuePartnerSerializer(allow_null=True)
    vendor = AdminRevenuePartnerSerializer(allow_null=True)
    distribution = AdminRevenueDistributionSerializer()
    audit = AdminRevenueAuditSerializer()

class AdminRevenueSummarySerializer(serializers.Serializer):
    """Revenue summary statistics"""
    total_transactions = serializers.IntegerField()
    total_gross = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_vat = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_service_charge = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_net = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_chargeghar_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_franchise_share = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_vendor_share = serializers.DecimalField(max_digits=12, decimal_places=2)
```

### 3. Create Admin Revenue View
**Location:** `api/admin/views/admin_revenue_views.py` (NEW FILE)

**Endpoint:** `GET /api/admin/revenue`

**Query Parameters:**
- `station_id` - Filter by station UUID
- `franchise_id` - Filter by franchise UUID
- `vendor_id` - Filter by vendor UUID
- `chargeghar_only` - Show only ChargeGhar-owned stations (boolean)
- `start_date` - From date (YYYY-MM-DD)
- `end_date` - To date (YYYY-MM-DD)
- `is_distributed` - Filter by distribution status (boolean)
- `transaction_status` - Filter by transaction status
- `is_reversal` - Filter reversals (boolean)
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

**View:**
```python
@admin_revenue_router.register(r"admin/revenue", name="admin-revenue")
@extend_schema(
    tags=["Admin - Partners"],
    summary="Get All Revenue Distributions",
    description="View all revenue distributions across entire platform with complete transaction and rental details for full auditability",
    parameters=[
        OpenApiParameter('station_id', type=str, description='Filter by station UUID'),
        OpenApiParameter('franchise_id', type=str, description='Filter by franchise UUID'),
        OpenApiParameter('vendor_id', type=str, description='Filter by vendor UUID'),
        OpenApiParameter('chargeghar_only', type=bool, description='Show only ChargeGhar-owned stations'),
        OpenApiParameter('start_date', type=str, description='From date (YYYY-MM-DD)'),
        OpenApiParameter('end_date', type=str, description='To date (YYYY-MM-DD)'),
        OpenApiParameter('is_distributed', type=bool, description='Filter by distribution status'),
        OpenApiParameter('transaction_status', type=str, description='Filter by transaction status'),
        OpenApiParameter('is_reversal', type=bool, description='Filter reversals'),
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
    ],
    responses={200: BaseResponseSerializer}
)
class AdminRevenueView(GenericAPIView, BaseAPIView):
    """Admin revenue view"""
    permission_classes = [IsStaffPermission]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get all revenue distributions"""
        def operation():
            filters = {
                'station_id': request.query_params.get('station_id'),
                'franchise_id': request.query_params.get('franchise_id'),
                'vendor_id': request.query_params.get('vendor_id'),
                'chargeghar_only': request.query_params.get('chargeghar_only') == 'true',
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date'),
                'is_distributed': request.query_params.get('is_distributed'),
                'transaction_status': request.query_params.get('transaction_status'),
                'is_reversal': request.query_params.get('is_reversal'),
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
            }
            service = AdminRevenueService()
            return service.get_all_revenue(filters)
        
        return self.handle_service_operation(
            operation,
            "Revenue data retrieved successfully",
            "Failed to retrieve revenue data"
        )
```

### 4. Update __init__.py Files
- `api/admin/services/__init__.py` - Export AdminRevenueService
- `api/admin/serializers/__init__.py` - Export admin revenue serializers
- `api/admin/views/__init__.py` - Import and register admin_revenue_router

## RESPONSE FORMAT

```json
{
  "success": true,
  "message": "Revenue data retrieved successfully",
  "data": {
    "results": [
      {
        "id": "uuid",
        "created_at": "2026-01-31T10:00:00Z",
        "updated_at": "2026-01-31T10:00:00Z",
        "transaction": {
          "id": "uuid",
          "amount": "100.00",
          "status": "COMPLETED",
          "payment_method": "KHALTI",
          "gateway_reference": "KHL123456",
          "created_at": "2026-01-31T10:00:00Z"
        },
        "user": {
          "id": 123,
          "email": "user@example.com",
          "username": "user123"
        },
        "rental": {
          "id": "uuid",
          "status": "COMPLETED",
          "start_time": "2026-01-31T09:00:00Z",
          "end_time": "2026-01-31T10:00:00Z"
        },
        "station": {
          "id": "uuid",
          "station_name": "Chitwan Mall Station",
          "serial_number": "CTW001",
          "location": "Chitwan"
        },
        "financial": {
          "gross_amount": "100.00",
          "vat_amount": "13.00",
          "service_charge": "5.00",
          "net_amount": "82.00",
          "chargeghar_share": "41.00",
          "franchise_share": "24.60",
          "vendor_share": "16.40"
        },
        "franchise": {
          "id": "uuid",
          "code": "FR-001",
          "business_name": "Pro Boy",
          "partner_type": "FRANCHISE"
        },
        "vendor": {
          "id": "uuid",
          "code": "VN-003",
          "business_name": "Vendor ABC",
          "partner_type": "VENDOR"
        },
        "distribution": {
          "is_distributed": true,
          "distributed_at": "2026-01-31T10:05:00Z"
        },
        "audit": {
          "is_reversal": false,
          "reversal_reason": "",
          "reversed_distribution_id": null,
          "calculation_details": {
            "revenue_model": "FRANCHISE_VENDOR",
            "franchise_percentage": 30,
            "vendor_percentage": 20
          }
        }
      }
    ],
    "summary": {
      "total_transactions": 150,
      "total_gross": "15000.00",
      "total_vat": "1950.00",
      "total_service_charge": "750.00",
      "total_net": "12300.00",
      "total_chargeghar_share": "6150.00",
      "total_franchise_share": "3690.00",
      "total_vendor_share": "2460.00"
    },
    "pagination": {
      "current_page": 1,
      "total_pages": 8,
      "total_count": 150,
      "page_size": 20,
      "has_next": true,
      "has_previous": false,
      "next_page": 2,
      "previous_page": null
    }
  }
}
```

## AUDITABILITY FEATURES

### Financial Accountability
✅ Complete money trail: gross → vat → service_charge → net → shares
✅ All partner shares tracked separately
✅ Distribution status (is_distributed, distributed_at)
✅ Calculation details JSON for audit

### Transaction Traceability
✅ Transaction ID, status, payment method, gateway reference
✅ User who made payment (ID, email, username)
✅ Rental session details (ID, status, times)
✅ Station where transaction occurred

### Partner Accountability
✅ Franchise details (if applicable)
✅ Vendor details (if applicable)
✅ ChargeGhar-only filter available

### Reversal Tracking
✅ Is reversal flag
✅ Reversal reason
✅ Link to original distribution (reversed_distribution_id)

### Timestamps
✅ Revenue distribution created_at, updated_at
✅ Transaction created_at
✅ Rental start_time, end_time
✅ Distribution distributed_at

## FILES TO CREATE (3 files)

1. `api/admin/services/admin_revenue_service.py` (~150 lines)
2. `api/admin/serializers/admin_revenue_serializers.py` (~120 lines)
3. `api/admin/views/admin_revenue_views.py` (~70 lines)

## FILES TO UPDATE (3 files)

1. `api/admin/services/__init__.py` - Add export
2. `api/admin/serializers/__init__.py` - Add exports
3. `api/admin/views/__init__.py` - Add router

## REUSE EXISTING CODE

✅ **Repository:** Use `RevenueDistributionRepository.filter_distributions()` - NO NEW CODE
✅ **Pagination:** Use `paginate_queryset` helper - CONSISTENT
✅ **Models:** Use existing RevenueDistribution, Transaction, Rental, Station, Partner - NO CHANGES

## VALIDATION RULES

- All query parameters are optional
- Admin can see ALL revenue across entire platform
- Date filters: start_date and end_date in YYYY-MM-DD format
- Boolean filters: is_distributed, is_reversal, chargeghar_only
- Pagination required (default: page=1, page_size=20)

## TESTING CHECKLIST

1. GET /api/admin/revenue - All revenue
2. GET /api/admin/revenue?franchise_id={uuid} - Specific franchise
3. GET /api/admin/revenue?vendor_id={uuid} - Specific vendor
4. GET /api/admin/revenue?chargeghar_only=true - ChargeGhar stations only
5. GET /api/admin/revenue?is_distributed=false - Undistributed only
6. GET /api/admin/revenue?is_reversal=true - Reversals only
7. GET /api/admin/revenue?transaction_status=COMPLETED - By transaction status
8. Verify: Complete transaction details included
9. Verify: Complete rental details included
10. Verify: Complete user details included
11. Verify: Financial breakdown accurate
12. Verify: Summary calculations correct
13. Verify: Pagination working
14. Verify: All audit fields present

## TOTAL EFFORT

- Lines of code: ~340 lines
- Files: 3 new, 3 updated
- Time estimate: 60 minutes
- Complexity: MEDIUM (complex data structure, multiple relationships)

## CONSISTENCY

✅ Reuses existing repository (no duplication)
✅ Uses paginate_queryset helper (consistent)
✅ Follows admin endpoint patterns
✅ Minimal code (no over-engineering)
✅ 100% accurate (verified from actual models)
✅ Complete audit trail (all required data points)
✅ Accountable (financial breakdown, partner tracking, timestamps)

## READY FOR REVIEW

✅ Plan complete - awaiting approval to implement
✅ All data sources verified from actual models
✅ Complete auditability requirements addressed
✅ Best practices for financial accountability followed
