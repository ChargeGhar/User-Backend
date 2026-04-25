# Scope 4 – Execution Order & Validation Gates

## Phase 1: Repository Foundation
**Goal:** Create the single source of truth for partner assignment lookup.

**File:** `UserBackend/api/partners/common/repositories/station_distribution_repository.py`

**Action:**
1. Add `get_assigned_partner(station_id)` static method.
2. Run existing repository tests to ensure no regression.

**Validation Gate:**
- [ ] `get_assigned_partner('nonexistent-id')` returns `None`
- [ ] `get_assigned_partner('station-with-franchise-only')` returns franchise `Partner`
- [ ] `get_assigned_partner('station-with-franchise-and-vendor')` returns vendor `Partner`

---

## Phase 2: Partner Service Integration
**Goal:** Enrich partner endpoints with assignment info.

**File:** `UserBackend/api/partners/common/services/partner_station_service.py`

**Actions:**
1. Add `_get_assigned_partner_info(station_id)` module-level helper.
2. In `get_stations_list()`, merge `station_info` into each `station_data` dict.
3. In `get_station_detail()`, merge `station_info` into the return dict.

**Validation Gate:**
- [ ] `GET /api/partner/stations` returns `isAssigned` + `assignedPartner` in every result
- [ ] `GET /api/partner/stations/{id}` returns `isAssigned` + `assignedPartner` at top level
- [ ] Existing partner access rules (`BR10.2`, `BR12.2`) still pass

---

## Phase 3: Admin Serializer Updates
**Goal:** Add fields to admin serializers.

**File:** `UserBackend/api/admin/serializers/station_serializers.py`

**Actions:**
1. Add `is_assigned` + `assigned_partner` to `AdminStationSerializer`.
2. Add `is_assigned` + `assigned_partner` to `AdminStationDetailSerializer`.

**Validation Gate:**
- [ ] `AdminStationSerializer(station).data` contains `isAssigned` and `assignedPartner` keys
- [ ] `AdminStationDetailSerializer(station).data` contains the same keys

---

## Phase 4: Admin Service Enrichment
**Goal:** Populate the new serializer fields without N+1 queries.

**File:** `UserBackend/api/admin/services/admin_station_service.py`

**Actions:**
1. Add `_get_assigned_partner_map(station_ids)` private helper.
2. In `get_stations_list()`, enrich paginated results with partner map.
3. In `get_station_detail()`, enrich single station result.

**Validation Gate:**
- [ ] `GET /api/admin/stations` returns `isAssigned` + `assignedPartner` per item
- [ ] `GET /api/admin/stations/{sn}` returns `isAssigned` + `assignedPartner` at top level
- [ ] Query count does not increase by more than 1 per page vs baseline

---

## Phase 5: Integration Testing
**Goal:** Verify all four endpoints together.

**Tests to Run:**
1. Admin list + detail with unassigned station → `isAssigned: false`, `assignedPartner: null`
2. Admin list + detail with franchise-only station → `isAssigned: true`, `partnerType: FRANCHISE`
3. Admin list + detail with franchise+vendor station → `isAssigned: true`, `partnerType: VENDOR`
4. Partner list + detail as franchise → same shape, context-aware partner
5. Partner list + detail as vendor → same shape, context-aware partner

**Validation Gate:**
- [ ] All 5 test scenarios pass
- [ ] No 500 errors on edge cases (deleted stations, inactive distributions)

---

## Phase 6: Swagger / Schema Verification
**Goal:** Ensure API documentation reflects new fields.

**Action:**
1. Start local server.
2. Open `/api/schema/swagger-ui/` or `/api/schema/redoc/`.
3. Inspect the four endpoint response schemas.

**Validation Gate:**
- [ ] Swagger shows `isAssigned` (boolean) and `assignedPartner` (object) in response examples

---

## Rollback Order (if needed)
Execute in reverse:
1. Revert `AdminStationService` enrichment.
2. Revert `AdminStationSerializer` / `AdminStationDetailSerializer` field additions.
3. Revert `PartnerStationService` enrichment.
4. Revert `StationDistributionRepository.get_assigned_partner()` (optional – harmless to keep).

## Completion Criteria
- [ ] All 4 plan scopes are implemented and verified
- [ ] No regressions in existing station endpoints
- [ ] New fields present in all 4 target endpoints
