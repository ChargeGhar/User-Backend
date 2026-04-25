# Vendor Multi-Station Assignment — Affected Files

## Files That Require Changes

### Service Layer

| File | Lines | Change |
|------|-------|--------|
| `api/partners/common/services/station_assignment_service.py` | 66-74 | Remove `vendor_already_has_station` check |
| `api/partners/common/services/station_assignment_service.py` | ~287 | Add `assign_stations_to_vendor()` method |
| `api/partners/common/services/station_assignment_service.py` | ~262 | Update `get_partner_assignment()` to return list |
| `api/partners/common/repositories/station_distribution_repository.py` | ~111-120 | Deprecate `vendor_has_station()`, add `vendor_station_count()` |

### Model Layer

| File | Lines | Change |
|------|-------|--------|
| `api/partners/common/models/station_distribution.py` | 17-18 | Update `BR2.3` docstring |

### Admin API Layer

| File | Lines | Change |
|------|-------|--------|
| `api/admin/serializers/partner_serializers.py` | TBD | `CreateVendorSerializer`: `station_id` → `station_ids` |
| `api/admin/serializers/partner_serializers.py` | TBD | Add `AssignStationsToVendorSerializer` |
| `api/admin/serializers/partner_serializers.py` | TBD | `AdminPartnerDetailSerializer`: `station` → `stations` |
| `api/admin/views/partner_views.py` | TBD | `AdminCreateVendorView`: iterate `station_ids` |
| `api/admin/views/partner_views.py` | TBD | Add `AdminAssignStationsToVendorView` |
| `api/admin/services/admin_partner_service.py` | TBD | Update `create_vendor()` for multi-station |
| `api/admin/services/admin_partner_service.py` | TBD | Add `assign_stations_to_vendor()` |

### Vendor Dashboard API

| File | Lines | Change |
|------|-------|--------|
| `api/partners/vendor/serializers/dashboard_serializers.py` | TBD | `VendorDashboardSerializer`: `station` → `stations` |
| `api/partners/vendor/services/vendor_dashboard_service.py` | TBD | Aggregate stats across all stations |
| `api/partners/vendor/services/vendor_station_service.py` | TBD | Return list of stations |
| `api/partners/vendor/services/vendor_revenue_service.py` | TBD | Aggregate revenue across all stations |

### Franchise Dashboard API

| File | Lines | Change |
|------|-------|--------|
| `api/partners/franchise/serializers/vendor_serializers.py` | TBD | Show station count |
| `api/partners/franchise/services/franchise_vendor_service.py` | TBD | Support multi-station assignment |

### IoT / Common

| File | Lines | Change |
|------|-------|--------|
| `api/partners/common/serializers/iot_serializers.py` | TBD | Validate `station_id` belongs to vendor |
| `api/partners/common/services/partner_iot_service.py` | TBD | Support multiple vendor stations |

## Files That Do NOT Require Changes

| File | Reason |
|------|--------|
| `api/partners/common/models/partner.py` | Partner model unchanged — no schema changes |
| `api/partners/common/models/revenue_distribution.py` | Per-transstation, per-station — already supports multi |
| `api/partners/common/models/station_revenue_share.py` | Per-distribution — each station gets its own record |
| `api/partners/common/services/revenue_distribution_service.py` | Calculates per-station — no changes needed |
| `api/user/stations/models/station.py` | Station model unchanged |
| `api/partners/auth/` | Authentication unchanged |

## Database Migrations

**No new migrations required.** The `StationDistribution` model already uses `ForeignKey` (not `OneToOneField`). The one-to-one constraint was enforced in service layer only.

## Backward Compatibility

| Scenario | Behavior |
|----------|----------|
| Existing single-station vendor | Continues to work — no data migration needed |
| Admin creates vendor with 1 station | Works same as before |
| Admin creates vendor with 3 stations | New behavior — now supported |
| Existing API clients passing `station_id` | **BREAKING** — need to update to `station_ids` array |
