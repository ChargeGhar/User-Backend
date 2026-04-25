# Vendor Multi-Station Assignment — Implementation Plan

## Phase 1: Core Service Layer (Foundation)

### Step 1.1: Relax Vendor Station Limit
**File:** `api/partners/common/services/station_assignment_service.py`
- Remove `vendor_already_has_station` check in `assign_station()` (lines 66-74)
- Keep `station_already_assigned` check (station exclusivity preserved)
- Update docstring: remove `BR2.3: Vendor has only ONE station`

### Step 1.2: Add Multi-Station Assignment Method
**File:** `api/partners/common/services/station_assignment_service.py`
- Add `assign_stations_to_vendor(vendor_id, station_ids, assigned_by_id)` method
- Iterate over `station_ids`, call `assign_station()` for each
- Copy existing vendor's `StationRevenueShare` config to each new distribution
- Return list of created distributions

### Step 1.3: Update Repository Queries
**File:** `api/partners/common/repositories/station_distribution_repository.py`
- Deprecate `vendor_has_station()` — add `@DeprecationWarning`
- Add `vendor_station_count(partner_id) -> int` — returns count of active vendor distributions
- `get_active_by_partner()` already supports multiple — no change needed

### Step 1.4: Update Model Docstring
**File:** `api/partners/common/models/station_distribution.py`
- Update `BR2.3` docstring: `Vendor can have MULTIPLE stations`
- Remove `BR2.4` reference if it implies single station

## Phase 2: Admin API Layer

### Step 2.1: Update Create Vendor Endpoint
**File:** `api/admin/views/partner_views.py`
**Serializer:** `api/admin/serializers/partner_serializers.py`
- Change `CreateVendorSerializer`: `station_id` → `station_ids` (list)
- `AdminCreateVendorView`: Iterate `station_ids`, create distributions for each
- Return vendor detail with all assigned stations

### Step 2.2: Add Assign Stations to Existing Vendor Endpoint
**File:** `api/admin/views/partner_views.py`
- New view: `AdminAssignStationsToVendorView`
- Route: `POST /admin/partners/stations/assign`
- Serializer: `AssignStationsToVendorSerializer` with `vendor_id`, `station_ids`
- Calls `StationAssignmentService.assign_stations_to_vendor()`

### Step 2.3: Update Partner Detail Response
**File:** `api/admin/serializers/partner_serializers.py`
- `AdminPartnerDetailSerializer`: `station` field → `stations` list
- Include all active `StationDistribution` records for the partner

## Phase 3: Partner Dashboard (Vendor)

### Step 3.1: Update Vendor Dashboard Serializer
**File:** `api/partners/vendor/serializers/dashboard_serializers.py`
- `VendorDashboardSerializer`: `station` → `stations` (list)
- `VendorRevenueStatsSerializer`: aggregate revenue across all vendor stations

### Step 3.2: Update Vendor Dashboard Service
**File:** `api/partners/vendor/services/vendor_dashboard_service.py`
- `get_dashboard()`: Query all vendor stations, aggregate stats
- Revenue calculation: sum `vendor_revenue_distributions` across all stations

### Step 3.3: Update Vendor Station List
**File:** `api/partners/vendor/views/` (station-related views)
- Return list of stations instead of single station
- Include per-station metrics (revenue, utilization, status)

### Step 3.4: Update Vendor IoT Actions
**File:** `api/partners/common/serializers/iot_serializers.py`
- `IoTStationActionSerializer`: `station_id` field — validate station belongs to vendor
- Add `get_vendor_stations()` helper for dropdown population

## Phase 4: Partner Dashboard (Franchise)

### Step 4.1: Update Franchise Vendor Assignment
**File:** `api/partners/franchise/views/franchise_vendor_payout_view.py` or similar
- Franchise assigning vendor to station: support multi-select
- Validate vendor belongs to franchise

### Step 4.2: Update Franchise Vendor List
**File:** `api/partners/franchise/serializers/vendor_serializers.py`
- Show station count per vendor instead of single station

## Phase 5: Revenue Distribution (Validation Only)

### Step 5.1: Verify Revenue Calculation
**File:** `api/partners/common/services/revenue_distribution_service.py`
- Confirm `calculate_shares()` works per-station with same vendor
- Each transaction creates independent `RevenueDistribution` — no changes needed

### Step 5.2: Add Revenue Consistency Check
**File:** `api/partners/common/services/station_assignment_service.py`
- When assigning new station to existing vendor, copy existing `StationRevenueShare`
- Log warning if attempting to set different revenue config for same vendor

## Phase 6: Testing

### Step 6.1: Unit Tests
- `StationAssignmentService`: vendor with 0, 1, 3 stations
- `StationDistributionRepository`: multiple distributions per vendor
- Revenue calculation: same vendor, different stations

### Step 6.2: Integration Tests
- Admin creates vendor with 3 stations
- Admin assigns additional station to existing vendor
- Vendor dashboard shows all stations
- Revenue aggregates correctly
- Franchise assigns vendor to multiple stations

### Step 6.3: Regression Tests
- Single-station vendor still works (backward compatibility)
- Franchise with multiple stations unchanged
- Station exclusivity preserved (one operator per station)
