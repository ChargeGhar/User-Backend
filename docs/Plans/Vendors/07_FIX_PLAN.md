# Vendor Multi-Station: Fix Plan for Bugs & Gaps

## Plan Date: 2026-04-25
## Based On: `06_BUGS_AND_GAPS.md`

---

## Phase A: P0 — Fix Partner Code Generator (BUG-3)

### Problem
Partner code generator creates `VN-002` which already exists (ghost record). Blocks ALL vendor creation.

### Files to Modify
1. `api/partners/common/repositories/partner_repository.py` — `generate_code()` or `create()` method

### Implementation Steps
1. Locate the code generation logic in `PartnerRepository`
2. Replace naive counter with "find max + 1" approach
3. Handle non-numeric codes gracefully (e.g., `VN-DUMMY-...`, `VNREV-001`)
4. Add retry logic with unique constraint check

### Code Change
```python
def generate_partner_code(self, partner_type: str, vendor_type: str = None) -> str:
    """Generate unique partner code."""
    if partner_type == 'FRANCHISE':
        prefix = 'FR'
    elif partner_type == 'VENDOR' and vendor_type == 'REVENUE':
        prefix = 'VNREV'
    else:
        prefix = 'VN'
    
    existing_codes = Partner.objects.filter(
        code__startswith=prefix
    ).values_list('code', flat=True)
    
    max_num = 0
    for code in existing_codes:
        # Extract numeric suffix: FR-001 → 1, VNREV-001 → 1
        suffix = code.replace(prefix, '').replace('-', '')
        try:
            num = int(suffix)
            max_num = max(max_num, num)
        except ValueError:
            pass  # Skip non-numeric suffixes
    
    return f"{prefix}-{max_num + 1:03d}"
```

### Testing
- [ ] Create REVENUE vendor → should get `VN-004` (skips `VN-002` gap)
- [ ] Create NON_REVENUE vendor → should get `VN-005`
- [ ] Create franchise → should get `FR-002`
- [ ] Create REVENUE franchise vendor → should get `VNREV-002`

---

## Phase B: P1 — Revenue Share Divergence Validation (GAP-1)

### Problem
`vendor_agreement_service.py` reads revenue config from first distribution only. If stations have different configs, agreement is misleading.

### Files to Modify
1. `api/partners/vendor/services/vendor_agreement_service.py` — `get_vendor_agreement()`

### Implementation Steps
1. After fetching all distributions, collect all unique revenue configs
2. If configs differ across stations, log a warning
3. Show per-station revenue in agreement or add a validation flag

### Code Change
```python
# In get_vendor_agreement(), after fetching vendor_distributions:
revenue_configs = set()
for vd in vendor_distributions:
    if hasattr(vd, 'revenue_share'):
        rs = vd.revenue_share
        config_key = f"{rs.revenue_model}:{rs.partner_percent}:{rs.fixed_amount}"
        revenue_configs.add(config_key)

if len(revenue_configs) > 1:
    # Log warning — this vendor has inconsistent revenue configs
    logger.warning(
        f"Vendor {vendor.code} has inconsistent revenue configs across stations: {revenue_configs}"
    )
```

### Testing
- [ ] Vendor with same config on all stations → agreement shows correctly
- [ ] Vendor with different configs → warning logged, agreement shows first config

---

## Phase C: P1 — Verify Admin Service Method (GAP-2)

### Problem
`assign_stations_to_vendor()` was added via fix script. Need to verify it's properly integrated.

### Files to Check
1. `api/admin/services/admin_partner_service.py`

### Verification Steps
1. Confirm `assign_stations_to_vendor` method exists after `create_vendor`
2. Confirm it imports `StationAssignmentService`
3. Confirm it accepts correct parameters: `vendor_id`, `station_ids`, `admin_user`, `notes`
4. Confirm it returns `List[StationDistribution]`
5. Confirm `ServiceException` propagates correctly

### Testing
- [ ] Method exists in class
- [ ] No import errors on Django restart
- [ ] Admin can call `POST /admin/partners/stations/assign`

---

## Phase D: P1 — Investigate VNREV-001 Missing Distributions (GAP-4)

### Problem
Existing franchise vendor VNREV-001 has zero station distributions.

### Investigation Steps
1. Run SQL query to check all distributions for VNREV-001 (including inactive):
```sql
SELECT * FROM partners_stationdistribution 
WHERE partner_id = '03b8920c-dc1d-4bda-a4e4-e91fe544ff27';
```
2. Check if distribution was created with wrong `distribution_type`:
```sql
SELECT * FROM partners_stationdistribution 
WHERE partner_id = '03b8920c-dc1d-4bda-a4e4-e91fe544ff27' 
   OR distribution_type = 'FRANCHISE_TO_VENDOR';
```
3. Check creation history in application logs (if available)

### Possible Fixes
- **If never assigned**: Use admin assign API to assign a station for testing
- **If wrong type**: Data migration to fix `distribution_type`
- **If deleted**: Recreate distribution

### Testing
- [ ] VNREV-001 shows stations in franchise vendor list
- [ ] Franchise vendor detail shows correct station info

---

## Phase E: P1 — Duplicate Station IDs Validation (GAP-5)

### Problem
Serializer allows duplicate `station_ids` which causes duplicate distribution attempts.

### Files to Modify
1. `api/admin/serializers/partner_serializers.py` — `CreateVendorSerializer.validate_station_ids()`
2. `api/partners/franchise/serializers/vendor_serializers.py` — `FranchiseCreateVendorSerializer.validate_station_ids()`

### Implementation Steps
1. In `validate_station_ids()`, deduplicate the list
2. Optionally raise validation error if duplicates detected

### Code Change
```python
def validate_station_ids(self, value):
    if not value:
        raise serializers.ValidationError("At least one station must be selected.")
    
    # Check for duplicates
    if len(value) != len(set(value)):
        raise serializers.ValidationError("Duplicate station IDs are not allowed.")
    
    # Validate each station exists
    for station_id in value:
        try:
            Station.objects.get(id=station_id)
        except Station.DoesNotExist:
            raise serializers.ValidationError(f"Station {station_id} does not exist.")
    
    return value
```

### Testing
- [ ] Duplicate IDs → validation error
- [ ] Unique IDs → passes validation

---

## Phase F: P2 — Update Docstrings (GAP-3)

### Problem
`create_vendor()` docstring may still reference single station.

### Files to Modify
1. `api/admin/services/admin_partner_service.py`

### Changes Needed
- Update Args docstring: `station_id: Station UUID to assign` → `station_ids: List of Station UUIDs to assign`
- Update Flow comment: `4. Assign station` → `4. Assign stations`
- Update Flow comment: `5. Create revenue share (for REVENUE vendors)` → `5. Create revenue share for each station (for REVENUE vendors)`

---

## Execution Order

```
Phase A (P0) → Phase E (P1) → Phase C (P1) → Phase B (P1) → Phase D (P1) → Phase F (P2) → Phase G (P2)
```

Phase A must be done first (blocks all vendor creation).
Phase E should be next (prevents bad data).
Phase C is quick verification.
Phases B, D, F, G can be done in any order after.

---

## Files Modified Summary

| Phase | File | Change Type |
|-------|------|-------------|
| A | `api/partners/common/repositories/partner_repository.py` | Code fix |
| B | `api/partners/vendor/services/vendor_agreement_service.py` | Enhancement |
| C | `api/admin/services/admin_partner_service.py` | Verification |
| D | Data only (SQL) | Investigation + fix |
| E | `api/admin/serializers/partner_serializers.py` | Validation add |
| E | `api/partners/franchise/serializers/vendor_serializers.py` | Validation add |
| F | `api/admin/services/admin_partner_service.py` | Docstring |
| G | `api/config/settings.py` or docker-compose | Infrastructure |
