# Vendor Multi-Station Assignment — Requirements

## Current State

Admin can assign **only ONE station** to a vendor. This is enforced at multiple layers:

| Layer | Enforcement |
|-------|-------------|
| Model docstring | `BR2.3: Vendor can have ONLY ONE station` |
| `StationAssignmentService.assign_station()` | Raises `vendor_already_has_station` if vendor has any active distribution |
| `StationAssignmentService.assign_station()` | Raises `station_already_assigned` if station has any active operator |
| `StationDistributionRepository.vendor_has_station()` | Returns `True` if vendor has active `CHARGEGHAR_TO_VENDOR` or `FRANCHISE_TO_VENDOR` |
| Admin API `POST /admin/partners/vendor` | Accepts single `station_id` parameter |

## Target State

Admin can assign **MULTIPLE stations** to a single vendor, while preserving:

1. **Vendor/Franchise hierarchy** — ChargeGhar → Franchise → Sub-Vendor chain unchanged
2. **Revenue distribution** — Per-transstation revenue split logic unchanged
3. **Station exclusivity** — Each station can still have only ONE operator at a time
4. **Revenue model consistency** — All stations under a vendor share the SAME revenue model (PERCENTAGE or FIXED)

## Business Rules (Updated)

| Rule ID | Current | Updated |
|---------|---------|---------|
| BR2.3 | Vendor can have ONLY ONE station | Vendor can have MULTIPLE stations |
| BR3.1 | One station = one active distribution | **UNCHANGED** — station still has one operator |
| BR3.3 | Revenue model per station | Revenue model per vendor (same across all stations) |
| BR3.4 | Non-Revenue vendors have no revenue | **UNCHANGED** |
| BR6.2 | CG Vendor gets partner_percent of net | **UNCHANGED** — still per-station calculation |
| BR7.4 | Franchise Vendor gets partner_percent | **UNCHANGED** — still per-station calculation |

## Constraints

- **No assumptions** — Every change must be traceable to a specific file
- **No out-of-boundary changes** — Only `api/admin`, `api/partners`, `api/user/stations` (read-only)
- **No inconsistency** — Revenue model must be identical across all vendor stations
- **No duplication** — Reuse existing `StationDistribution` and `StationRevenueShare` models
- **Hierarchy preservation** — Franchise ownership, vendor subordination, revenue flows unchanged
- **Backward compatibility** — Existing single-station vendors continue to work

## User Stories

1. **Admin assigns multiple stations to vendor**: Admin selects a vendor and assigns 3 stations in one action. All 3 stations get the vendor's existing revenue model.
2. **Admin assigns additional station to existing vendor**: Vendor already has 2 stations. Admin assigns a 3rd. New station gets same revenue model.
3. **Vendor views all their stations**: Vendor dashboard shows list of all assigned stations with per-station metrics.
4. **Vendor revenue aggregates across stations**: Vendor sees total earnings from all stations combined.
5. **Revenue calculation per transaction**: Each rental transaction creates one `RevenueDistribution` per station. Vendor share is calculated using the vendor-wide revenue config.
