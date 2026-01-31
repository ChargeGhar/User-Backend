# Franchise Endpoint: List Own Stations

> **Endpoint:** `GET /api/partner/franchise/stations/`  
> **Status:** PLANNING  
> **Priority:** HIGH (Phase 2 - Foundation)

---

## 1. Endpoint Specification

### Request
```http
GET /api/partner/franchise/stations/?page=1&page_size=20&status=ACTIVE&search=ST-001
Authorization: Bearer {franchise_access_token}
```

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 20, max: 100) |
| `status` | string | No | Filter by station status: ACTIVE, INACTIVE, MAINTENANCE |
| `search` | string | No | Search by station_name, code, address |
| `has_vendor` | boolean | No | Filter: true=assigned to vendor, false=no vendor |

### Response (200 OK)
```json
{
  "success": true,
  "message": "Stations retrieved successfully",
  "data": {
    "results": [
      {
        "id": "uuid",
        "station_name": "Thamel Station",
        "serial_number": "CG-KTM-001",
        "imei": "123456789012345",
        "latitude": "27.717200000000000",
        "longitude": "85.324000000000000",
        "address": "Thamel, Kathmandu",
        "landmark": "Near Kathmandu Guest House",
        "total_slots": 8,
        "status": "ONLINE",
        "is_maintenance": false,
        "last_heartbeat": "2026-01-31T13:30:00Z",
        "created_at": "2026-01-15T10:00:00Z",
        "updated_at": "2026-01-31T13:30:00Z",
        "amenities": ["WiFi", "Parking", "24/7 Access"],
        "available_slots": 5,
        "occupied_slots": 3,
        "total_powerbanks": 8,
        "available_powerbanks": 5,
        "distribution": {
          "id": "dist-uuid",
          "distribution_type": "CHARGEGHAR_TO_FRANCHISE",
          "effective_date": "2026-01-15",
          "is_active": true
        },
        "vendor": {
          "id": "vendor-uuid",
          "code": "VN-001",
          "business_name": "Thamel Operator",
          "vendor_type": "REVENUE",
          "status": "ACTIVE"
        },
        "revenue_stats": {
          "today_transactions": 12,
          "today_revenue": "1200.00",
          "this_month_transactions": 350,
          "this_month_revenue": "35000.00"
        }
      }
    ],
    "count": 45,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

**Note:** This is for LIST view. For DETAIL view (GET /stations/{id}/), include full `slots` array and `powerbanks` array.

---

## 2. Business Rules Verification

### BR10.2 - Franchise Control Scope
✅ **Rule:** Franchise has control over ONLY their own stations  
**Implementation:** Filter `station_distributions` WHERE `partner_id = franchise.id` AND `distribution_type = CHARGEGHAR_TO_FRANCHISE`

### BR12.2 - Visibility Rules
✅ **Rule:** Franchise views ONLY own station transactions  
**Implementation:** Revenue stats filtered by `franchise_id = franchise.id` in `revenue_distributions`

### BR2.1 - Station Assignment
✅ **Rule:** ChargeGhar assigns stations to Franchise  
**Implementation:** Only show stations with `distribution_type = CHARGEGHAR_TO_FRANCHISE`

### BR2.4 - Single Operator
✅ **Rule:** Station can have only ONE operator at a time  
**Implementation:** Join with `station_distributions` WHERE `is_active = True` to get current vendor (if any)

---

## 3. Database Schema Mapping

### Tables Involved
1. **stations** - Station details
   - Fields: `id`, `station_name`, `serial_number`, `imei`, `latitude`, `longitude`, `address`, `landmark`, `description`, `total_slots`, `status`, `is_maintenance`, `hardware_info`, `last_heartbeat`, `opening_time`, `closing_time`
   - Status choices: `ONLINE`, `OFFLINE`, `MAINTENANCE`
   
2. **station_slots** - Slot information for calculating available/occupied
   - Fields: `station_id`, `slot_number`, `status`, `battery_level`, `current_rental`
   - Status choices: `AVAILABLE`, `OCCUPIED`, `MAINTENANCE`, `ERROR`
   
3. **power_banks** - PowerBank information (linked to slots)
   - Fields: `serial_number`, `model`, `capacity_mah`, `status`, `battery_level`, `current_station`, `current_slot`
   
4. **station_media** - Station images/videos
   - Fields: `station_id`, `media_upload_id`, `media_type`, `title`, `description`, `is_primary`
   - Media types: `IMAGE`, `VIDEO`, `360_VIEW`, `FLOOR_PLAN`
   
5. **media_uploads** - Actual media files
   - Fields: `file_url`, `file_type`, `original_name`, `file_size`, `cloud_provider`, `public_id`
   
6. **station_distributions** - Franchise ownership + Vendor assignment
   - Fields: `station_id`, `partner_id`, `distribution_type`, `effective_date`, `is_active`
   
7. **partners** - Vendor details (if station has vendor)
   - Fields: `id`, `code`, `business_name`, `vendor_type`, `status`
   
8. **revenue_distributions** - Revenue statistics
   - Fields: `station_id`, `franchise_id`, `gross_amount`, `franchise_share`, `created_at`

### Query Logic
```sql
-- Main query: Get franchise's stations with all details
SELECT 
    s.id,
    s.station_name,
    s.serial_number,
    s.imei,
    s.latitude,
    s.longitude,
    s.address,
    s.landmark,
    s.description,
    s.total_slots,
    s.status,
    s.is_maintenance,
    s.last_heartbeat,
    s.opening_time,
    s.closing_time,
    
    -- Franchise distribution info
    sd_franchise.id as franchise_dist_id,
    sd_franchise.distribution_type,
    sd_franchise.effective_date,
    sd_franchise.is_active as dist_is_active,
    
    -- Vendor info (if assigned)
    p_vendor.id as vendor_id,
    p_vendor.code as vendor_code,
    p_vendor.business_name as vendor_business_name,
    p_vendor.vendor_type,
    p_vendor.status as vendor_status,
    
    -- Slot counts (aggregated)
    COUNT(CASE WHEN ss.status = 'AVAILABLE' THEN 1 END) as available_slots,
    COUNT(CASE WHEN ss.status = 'OCCUPIED' THEN 1 END) as occupied_slots
    
FROM stations s
INNER JOIN station_distributions sd_franchise 
    ON s.id = sd_franchise.station_id
    AND sd_franchise.partner_id = {franchise_id}
    AND sd_franchise.distribution_type = 'CHARGEGHAR_TO_FRANCHISE'
    AND sd_franchise.is_active = TRUE

LEFT JOIN station_distributions sd_vendor
    ON s.id = sd_vendor.station_id
    AND sd_vendor.distribution_type = 'FRANCHISE_TO_VENDOR'
    AND sd_vendor.is_active = TRUE

LEFT JOIN partners p_vendor
    ON sd_vendor.partner_id = p_vendor.id

LEFT JOIN station_slots ss
    ON s.id = ss.station_id

WHERE s.is_deleted = FALSE
GROUP BY s.id, sd_franchise.id, p_vendor.id
ORDER BY s.created_at DESC
```

### Media Query (Separate)
```sql
-- Get station media with file URLs
SELECT 
    sm.id,
    sm.station_id,
    sm.media_type,
    sm.title,
    sm.description,
    sm.is_primary,
    mu.file_url,
    mu.file_type,
    mu.original_name
FROM station_media sm
INNER JOIN media_uploads mu ON sm.media_upload_id = mu.id
WHERE sm.station_id IN ({station_ids})
ORDER BY sm.is_primary DESC, sm.created_at ASC
```

### PowerBank Stats Query (Separate)
```sql
-- PowerBank statistics per station
SELECT 
    current_station_id as station_id,
    COUNT(*) as total_powerbanks,
    COUNT(CASE WHEN status = 'AVAILABLE' THEN 1 END) as available_powerbanks,
    COUNT(CASE WHEN status = 'RENTED' THEN 1 END) as rented_powerbanks,
    COUNT(CASE WHEN status = 'MAINTENANCE' THEN 1 END) as maintenance_powerbanks
FROM power_banks
WHERE current_station_id IN ({station_ids})
GROUP BY current_station_id
```
```sql
-- Today's stats
SELECT 
    station_id,
    COUNT(*) as today_transactions,
    SUM(gross_amount) as today_revenue
FROM revenue_distributions
WHERE franchise_id = {franchise_id}
  AND DATE(created_at) = CURRENT_DATE
  AND is_reversal = FALSE
GROUP BY station_id

-- This month's stats
SELECT 
    station_id,
    COUNT(*) as month_transactions,
    SUM(gross_amount) as month_revenue
FROM revenue_distributions
WHERE franchise_id = {franchise_id}
  AND DATE(created_at) >= DATE_TRUNC('month', CURRENT_DATE)
  AND is_reversal = FALSE
GROUP BY station_id
```

---

## 4. Implementation Plan

### Step 1: Repository Method (Use Existing)
**File:** `api/partners/common/repositories/station_distribution_repository.py`

**Method to use:**
```python
StationDistributionRepository.get_franchise_stations(
    franchise_id: str,
    status: Optional[str] = None,
    search: Optional[str] = None,
    has_vendor: Optional[bool] = None
) -> QuerySet
```

**Check if exists:** ✅ Need to verify and potentially add this method

### Step 2: Service Layer
**File:** `api/partners/franchise/services/franchise_service.py`

**Method to add:**
```python
def get_stations_list(
    self,
    franchise: Partner,
    filters: Dict
) -> Dict:
    """
    Get paginated list of franchise's own stations.
    
    Args:
        franchise: Partner object (must be FRANCHISE type)
        filters: Dict with page, page_size, status, search, has_vendor
        
    Returns:
        Dict with results, count, page, page_size, total_pages
        
    Business Rules:
    - BR10.2: Only own stations
    - BR12.2: Only own revenue data
    - BR2.1: CHARGEGHAR_TO_FRANCHISE distribution type
    """
```

**Logic:**
1. Validate franchise type
2. Get stations via repository (with filters)
3. Paginate results
4. For each station:
   - Get slot counts (available/occupied) - from station_slots table
   - Get powerbank stats (total/available/rented/maintenance) - from power_banks table
   - Get revenue stats (today + this month) - from revenue_distributions table
   - Get media files - from station_media + media_uploads tables
5. Return formatted response

### Step 3: Serializer
**File:** `api/partners/franchise/serializers/station_serializers.py` (NEW)

**Serializers to create:**
```python
class VendorBasicSerializer(serializers.Serializer):
    """Vendor basic info for station list"""
    id = serializers.UUIDField()
    code = serializers.CharField()
    business_name = serializers.CharField()
    vendor_type = serializers.CharField()
    status = serializers.CharField()

class StationDistributionSerializer(serializers.Serializer):
    """Distribution info"""
    id = serializers.UUIDField()
    distribution_type = serializers.CharField()
    effective_date = serializers.DateField()
    is_active = serializers.BooleanField()

class StationRevenueStatsSerializer(serializers.Serializer):
    """Revenue statistics"""
    today_transactions = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    this_month_transactions = serializers.IntegerField()
    this_month_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

class FranchiseStationListSerializer(serializers.Serializer):
    """Station list item for franchise - matches AdminStationSerializer format"""
    id = serializers.UUIDField()
    station_name = serializers.CharField()
    serial_number = serializers.CharField()
    imei = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=17, decimal_places=15)
    longitude = serializers.DecimalField(max_digits=18, decimal_places=15)
    address = serializers.CharField()
    landmark = serializers.CharField(allow_null=True)
    total_slots = serializers.IntegerField()
    status = serializers.CharField()
    is_maintenance = serializers.BooleanField()
    last_heartbeat = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
    # Summary data (not full arrays)
    amenities = serializers.ListField(child=serializers.CharField())  # Just names
    available_slots = serializers.IntegerField()
    occupied_slots = serializers.IntegerField()
    total_powerbanks = serializers.IntegerField()
    available_powerbanks = serializers.IntegerField()
    
    # Partner-specific data
    distribution = StationDistributionSerializer()
    vendor = VendorBasicSerializer(allow_null=True)
    revenue_stats = StationRevenueStatsSerializer()
```

**Note:** For station DETAIL endpoint (next), we'll include full `slots`, `powerbanks`, and `media` arrays like AdminStationDetailSerializer.

### Step 4: View
**File:** `api/partners/franchise/views/franchise_station_view.py`

**View to create:**
```python
@franchise_station_router.register(
    r"partner/franchise/stations",
    name="franchise-stations-list"
)
@extend_schema(
    tags=["Partner - Franchise"],
    summary="List Own Stations",
    description="Get paginated list of franchise's own stations with vendor and revenue info",
    parameters=[
        OpenApiParameter('page', type=int, description='Page number'),
        OpenApiParameter('page_size', type=int, description='Items per page'),
        OpenApiParameter('status', type=str, description='Filter by station status'),
        OpenApiParameter('search', type=str, description='Search by name/code/address'),
        OpenApiParameter('has_vendor', type=bool, description='Filter by vendor assignment'),
    ],
    responses={200: BaseResponseSerializer}
)
class FranchiseStationListView(GenericAPIView, BaseAPIView):
    """List franchise's own stations"""
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request) -> Response:
        """Get stations list"""
        def operation():
            franchise = request.user.partner_profile
            filters = {
                'page': request.query_params.get('page', 1),
                'page_size': request.query_params.get('page_size', 20),
                'status': request.query_params.get('status'),
                'search': request.query_params.get('search'),
                'has_vendor': request.query_params.get('has_vendor'),
            }
            service = FranchiseService()
            return service.get_stations_list(franchise, filters)
        
        return self.handle_service_operation(
            operation,
            "Stations retrieved successfully",
            "Failed to retrieve stations"
        )
```

### Step 5: URL Configuration
**File:** `api/partners/franchise/urls.py`

**Add:**
```python
from .views import franchise_station_router

urlpatterns += franchise_station_router.urls
```

---

## 5. Testing Plan

### Test Cases

#### TC1: List All Stations (Happy Path)
```bash
curl -X GET "http://localhost:8010/api/partner/franchise/stations/" \
  -H "Authorization: Bearer {franchise_token}"
```
**Expected:** 200 OK with paginated station list

#### TC2: Filter by Status
```bash
curl -X GET "http://localhost:8010/api/partner/franchise/stations/?status=ACTIVE" \
  -H "Authorization: Bearer {franchise_token}"
```
**Expected:** Only ACTIVE stations

#### TC3: Search by Code
```bash
curl -X GET "http://localhost:8010/api/partner/franchise/stations/?search=ST-001" \
  -H "Authorization: Bearer {franchise_token}"
```
**Expected:** Stations matching search term

#### TC4: Filter by Vendor Assignment
```bash
curl -X GET "http://localhost:8010/api/partner/franchise/stations/?has_vendor=false" \
  -H "Authorization: Bearer {franchise_token}"
```
**Expected:** Only stations without vendor assigned

#### TC5: Pagination
```bash
curl -X GET "http://localhost:8010/api/partner/franchise/stations/?page=2&page_size=10" \
  -H "Authorization: Bearer {franchise_token}"
```
**Expected:** Page 2 with 10 items

#### TC6: Unauthorized Access (Vendor tries to access)
```bash
curl -X GET "http://localhost:8010/api/partner/franchise/stations/" \
  -H "Authorization: Bearer {vendor_token}"
```
**Expected:** 403 Forbidden

#### TC7: No Stations
```bash
# Franchise with no stations assigned
curl -X GET "http://localhost:8010/api/partner/franchise/stations/" \
  -H "Authorization: Bearer {new_franchise_token}"
```
**Expected:** 200 OK with empty results array

---

## 6. Potential Issues & Solutions

### Issue 1: N+1 Query Problem
**Problem:** Loading vendor and revenue stats for each station separately  
**Solution:** Use `select_related()` for vendor and aggregate revenue stats in bulk

### Issue 2: Revenue Stats Performance
**Problem:** Calculating revenue stats for many stations is slow  
**Solution:** 
- Use single aggregation query for all stations
- Cache results for 5 minutes using Redis
- Consider denormalizing stats to `stations` table (future optimization)

### Issue 3: Vendor Assignment Confusion
**Problem:** Multiple distribution records for same station (historical)  
**Solution:** Always filter `is_active = True` to get current assignment only

### Issue 4: Deleted Stations
**Problem:** Soft-deleted stations appearing in list  
**Solution:** Filter `deleted_at IS NULL` in base query

---

## 7. Dependencies

### Existing Code to Verify
- [ ] `StationDistributionRepository.get_franchise_stations()` - Check if exists
- [ ] `RevenueDistributionRepository` - Verify aggregation methods
- [ ] `IsFranchise` permission - Already exists ✅
- [ ] Station model fields - Verify all fields exist

### New Code to Create
- [ ] Repository method (if not exists)
- [ ] Service method: `get_stations_list()`
- [ ] Serializers: 4 serializers (VendorBasic, Distribution, RevenueStats, StationList)
- [ ] View: `FranchiseStationListView`
- [ ] URL registration

**Note:** Media, slots, and powerbanks full arrays will be in DETAIL endpoint (next task)

---

## 8. Acceptance Criteria

- [ ] Franchise can list all their own stations
- [ ] Pagination works correctly
- [ ] Filters (status, search, has_vendor) work correctly
- [ ] Vendor info displayed correctly (if assigned)
- [ ] Revenue stats calculated correctly (today + this month)
- [ ] Non-franchise users cannot access (403)
- [ ] Performance: Response time < 500ms for 100 stations
- [ ] No N+1 queries (verify with Django Debug Toolbar)
- [ ] Proper error handling for edge cases

---

## 9. Next Steps After Implementation

1. Test with real data (create franchise + stations via admin)
2. Verify revenue stats accuracy against database
3. Performance test with 100+ stations
4. Move to next endpoint: `GET /api/partner/franchise/stations/{id}/` (Station Details)

---

**Ready for Review:** YES  
**Estimated Implementation Time:** 2-3 hours  
**Complexity:** MEDIUM
