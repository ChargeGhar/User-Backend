# Scope 3 – Testing & Verification

## Unit Tests

### 1. Repository Test
**File:** `UserBackend/tests/partners/common/repositories/test_station_distribution_repository.py` (create if missing)

| Scenario | Station Distributions | Expected Partner Returned |
|----------|----------------------|---------------------------|
| Unassigned station | None | `None` |
| Franchise only | `CHARGEGHAR_TO_FRANCHISE` | Franchise partner |
| Franchise + vendor | `CHARGEGHAR_TO_FRANCHISE` + `FRANCHISE_TO_VENDOR` | Vendor partner (priority 1) |
| Direct vendor only | `CHARGEGHAR_TO_VENDOR` | Direct vendor partner |
| All three active | All three | Vendor partner (priority 1) |
| Inactive distribution | One inactive `CHARGEGHAR_TO_FRANCHISE` | `None` |

### 2. Admin List Response Test
**File:** `UserBackend/tests/admin/views/test_station_views.py`

- Call `GET /api/admin/stations`
- Assert every result object contains:
  - `isAssigned` (boolean)
  - `assignedPartner` (object or `null`)
- Assert `assignedPartner` shape matches the spec when `isAssigned == true`.

### 3. Admin Detail Response Test
- Call `GET /api/admin/stations/{station_sn}`
- Assert same fields exist at the top level of `data`.

### 4. Partner List Response Test
**File:** `UserBackend/tests/partners/common/views/test_partner_station_view.py`

- Call `GET /api/partner/stations` as franchise.
- Assert `isAssigned` and `assignedPartner` are present for each station.
- When the franchise has assigned a vendor to a station, assert `assignedPartner.partnerType == "VENDOR"`.

### 5. Partner Detail Response Test
- Call `GET /api/partner/stations/{station_id}` as franchise and as vendor.
- Verify the returned `assignedPartner` matches the priority rule.

## Manual API Verification (Swagger / Postman)

| Endpoint | Check |
|----------|-------|
| `GET /api/admin/stations` | Every item in `data.results` has `isAssigned` + `assignedPartner` |
| `GET /api/admin/stations/{sn}` | `data` has `isAssigned` + `assignedPartner` |
| `GET /api/partner/stations` | Every item in `data.results` has `isAssigned` + `assignedPartner` |
| `GET /api/partner/stations/{id}` | `data` has `isAssigned` + `assignedPartner` |

## Regression Checks
- Confirm no N+1 query increase on admin list (use Django Debug Toolbar or `assertNumQueries`).
- Confirm partner endpoints still enforce `BR10.2` and `BR12.2` (only own stations/data).
- Confirm no 500 errors when a station has no active distributions.

## Rollback Plan
If any field causes issues in production:
1. Revert serializer changes (remove `is_assigned`, `assigned_partner` fields).
2. Revert service enrichment loops.
3. Revert repository helper (safe to keep; unused code is harmless).

All changes are additive (new fields only), so rollback is non-breaking for existing clients.
