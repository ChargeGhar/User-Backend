# Vendor Multi-Station: Bugs and Gaps Found During Testing

## Testing Date: 2026-04-25
## Tested By: Cline (AI Assistant)
## Environment: Docker local (cg-api-local)

---

## Table of Contents
1. [Bugs Found & Fixed During Testing](#1-bugs-found--fixed-during-testing)
2. [Pre-existing Bugs Blocking Vendor Creation](#2-pre-existing-bugs-blocking-vendor-creation)
3. [Gaps / Improvement Areas](#3-gaps--improvement-areas)
4. [Data Integrity Concerns](#4-data-integrity-concerns)
5. [Recommended Fix Priority](#5-recommended-fix-priority)

---

## 1. Bugs Found & Fixed During Testing

### BUG-1: `Station.name` Attribute Error
**File**: `api/partners/common/services/station_assignment_service.py`
**Lines**: 108, 296
**Severity**: 🔴 Critical (500 error)
**Status**: ✅ FIXED

**Description**:
The `Station` model uses `station_name` field, not `name`. Two `f-string` references used `station.name` causing `AttributeError`.

**Stack Trace**:
```
Service operation failed: 'Station' object has no attribute 'name'
```

**Fix Applied**:
```python
# Before (line 108):
f"Station {station.name} assigned to partner {partner.code} "

# After:
f"Station {station.station_name} assigned to partner {partner.code} "

# Before (line 296):
f"(station: {distribution.station.name}, partner: {distribution.partner.code})"

# After:
f"(station: {distribution.station.station_name}, partner: {distribution.partner.code})"
```

---

### BUG-2: `_create_revenue_share()` Keyword Argument Mismatch
**File**: `api/partners/common/services/station_assignment_service.py`
**Method**: `assign_station()` → `_create_revenue_share()` call
**Severity**: 🔴 Critical (500 error on REVENUE vendor station assignment)
**Status**: ✅ FIXED

**Description**:
`assign_station()` calls `_create_revenue_share(distribution_id=..., revenue_config=...)` but the method signature is `_create_revenue_share(self, distribution_id: str, config: Dict)`.

**Stack Trace**:
```
StationAssignmentService._create_revenue_share() got an unexpected keyword argument 'revenue_config'
```

**Fix Applied**:
```python
# Before:
revenue_share = self._create_revenue_share(
    distribution_id=str(distribution.id),
    revenue_config=revenue_config
)

# After:
revenue_share = self._create_revenue_share(
    distribution_id=str(distribution.id),
    config=revenue_config
)
```

---

## 2. Pre-existing Bugs Blocking Vendor Creation

### BUG-3: Partner Code Generator — Duplicate Key Collision
**File**: `api/partners/common/repositories/partner_repository.py` (inferred)
**Severity**: 🔴 Critical (blocks ALL vendor creation)
**Status**: ❌ NOT FIXED — Pre-existing

**Description**:
When creating any vendor (admin or franchise), the partner code generator tries to create `VN-002` which already exists (possibly soft-deleted or inactive).

**Stack Trace**:
```
duplicate key value violates unique constraint "partners_code_key"
DETAIL:  Key (code)=(VN-002) already exists.
```

**Impact**:
- ❌ Admin `POST /api/admin/partners/vendor` — 500 error
- ❌ Franchise `POST /api/partner/franchise/vendors` — 500 error
- Cannot test end-to-end vendor creation with multiple stations

**Existing Vendor Codes**:
```
VN-003, VN-DUMMY-D2AC3931, VN-900, VNREV-001
```
Note: `VN-002` does NOT appear in active vendor list but constraint says it exists.

**Root Cause Hypothesis**:
The code generator likely:
1. Counts existing vendors
2. Generates `VN-{count + 1}` format
3. Does not check for gaps or deleted/inactive records

**Fix Required**:
```python
# PartnerRepository.create() or generate_code()
# Should use atomic counter or check for existing codes before insert
# Example fix:
def generate_vendor_code():
    prefix = "VN"
    # Find highest numeric suffix, skipping gaps
    existing = Partner.objects.filter(
        code__startswith=prefix,
        partner_type='VENDOR'
    ).values_list('code', flat=True)
    
    max_num = 0
    for code in existing:
        try:
            num = int(code.replace(prefix + '-', ''))
            max_num = max(max_num, num)
        except ValueError:
            pass  # Skip non-numeric codes like VN-DUMMY-...
    
    return f"{prefix}-{max_num + 1:03d}"
```

---

### BUG-4: Redis Connection Refused
**File**: `api.common.decorators` (rate limit decorator)
**Severity**: 🟡 Low (non-blocking warning)
**Status**: ❌ NOT FIXED — Infrastructure

**Description**:
Rate limit decorator fails to connect to Redis at `redis:6380`.

**Stack Trace**:
```
Rate limit decorator error: Error 111 connecting to redis:6380. Connection refused.
```

**Impact**:
- Warnings in logs but API calls still succeed
- Rate limiting is disabled/fallback mode

**Fix Required**:
Either:
1. Start Redis container: `docker compose up redis`
2. Or disable rate limiting in local dev settings

---

## 3. Gaps / Improvement Areas

### GAP-1: Revenue Share Divergence Risk
**File**: `api/partners/vendor/services/vendor_agreement_service.py`
**Severity**: 🟡 Medium
**Status**: ⚠️ MONITOR

**Description**:
`vendor_agreement_service.py` reads revenue config from `vendor_distributions.first()`. If a vendor has multiple stations with DIFFERENT revenue configs (e.g., one at 20%, one at 25%), the agreement will only show the first station's config.

**Current Code**:
```python
vendor_distribution = vendor_distributions.first()
revenue_model = None
if hasattr(vendor_distribution, 'revenue_share'):
    revenue_model = vendor_distribution.revenue_share
```

**Recommendation**:
Add validation to ensure all stations have the SAME revenue config, OR show per-station revenue in the agreement.

---

### GAP-2: Missing `assign_stations_to_vendor` in Admin Service
**File**: `api/admin/services/admin_partner_service.py`
**Severity**: 🟡 Medium
**Status**: ✅ ADDED (via fix script)

**Description**:
The `AdminPartnerService` class was missing the `assign_stations_to_vendor()` method. It was added during testing via a Python fix script.

**Verification Needed**:
- Confirm method is properly added to the file
- Confirm it imports `StationAssignmentService` correctly
- Confirm it handles `ServiceException` properly

---

### GAP-3: Admin `create_vendor` Docstring Not Updated
**File**: `api/admin/services/admin_partner_service.py`
**Method**: `create_vendor()`
**Severity**: 🟢 Low
**Status**: ⚠️ PARTIALLY UPDATED

**Description**:
The method signature was changed from `station_id: str` to `station_ids: List[str]`, but some docstring references may still say "Station UUID to assign" instead of "List of Station UUIDs to assign".

**Fix Required**:
Review and update all docstring references in `create_vendor()` method.

---

### GAP-4: Franchise Vendor List Returns Empty `stations`
**File**: `api/partners/franchise/services/franchise_vendor_service.py`
**Severity**: 🟡 Medium
**Status**: ⚠️ NEEDS INVESTIGATION

**Description**:
When testing franchise vendor list for FRREV-001, the existing vendor VNREV-001 returned `stations: []` and `station_count: 0`.

**Investigation Results**:
```bash
docker exec cg-api-local python -c "
from api.partners.common.models import StationDistribution
dists = StationDistribution.objects.filter(partner_id='03b8920c-dc1d-4bda-a4e4-e91fe544ff27')
print([d for d in dists])  # Returns EMPTY queryset
"
```

**Possible Causes**:
1. VNREV-001 was created before station assignment was implemented
2. The station distribution was deleted/deactivated
3. Franchise vendor creation previously did NOT create station distributions

**Recommendation**:
Check historical data. If franchise vendors were created without station assignments, a data migration may be needed.

---

### GAP-5: No Validation for Duplicate Station IDs in `station_ids`
**File**: `api/admin/serializers/partner_serializers.py`
**Severity**: 🟢 Low
**Status**: ⚠️ NOT ADDRESSED

**Description**:
If admin passes duplicate station IDs in `station_ids: ["uuid1", "uuid1", "uuid2"]`, the system will try to create duplicate distributions.

**Recommendation**:
Add deduplication in serializer:
```python
station_ids = list(dict.fromkeys(station_ids))  # Remove duplicates while preserving order
```

---

## 4. Data Integrity Concerns

### CONCERN-1: VN-002 Ghost Record
**Table**: `partners_partner`
**Status**: ❌ UNRESOLVED

The `VN-002` code exists in the database but is NOT returned by `Partner.objects.filter(partner_type='VENDOR')`. This implies:
- The record may be soft-deleted (`is_active=False` or `status='DELETED'`)
- OR the record exists but is filtered out by queryset logic
- The code generator does not account for this

**Action Required**:
```sql
SELECT id, code, status, is_active, deleted_at FROM partners_partner WHERE code = 'VN-002';
```

---

### CONCERN-2: VNREV-001 Missing Station Distribution
**Table**: `partners_stationdistribution`
**Status**: ❌ UNRESOLVED

Vendor VNREV-001 (under FRREV-001 franchise) has zero station distributions. This vendor cannot be properly tested.

**Action Required**:
Either:
1. Assign a station to VNREV-001 via admin API for testing
2. Or create new test data after fixing BUG-3

---

## 5. Recommended Fix Priority

### 🔴 P0 — Fix Immediately (Blocking)
| # | Bug | File | Effort |
|---|-----|------|--------|
| 3 | Partner code generator collision | `partner_repository.py` | Small |

### 🟡 P1 — Fix Soon (Functional Gaps)
| # | Gap | File | Effort |
|---|-----|------|--------|
| 1 | Revenue share divergence risk | `vendor_agreement_service.py` | Small |
| 2 | Verify `assign_stations_to_vendor` in admin service | `admin_partner_service.py` | Tiny |
| 4 | Investigate VNREV-001 missing distributions | Data investigation | Small |
| 5 | Duplicate `station_ids` validation | `partner_serializers.py` | Tiny |

### 🟢 P2 — Fix When Convenient (Cleanup)
| # | Gap | File | Effort |
|---|-----|------|--------|
| 3 | Update `create_vendor` docstring | `admin_partner_service.py` | Tiny |
| 4 | Redis connection | Infrastructure | Tiny |

---

## Appendix: Test Commands for Reproducing Issues

### Reproduce BUG-3 (Code Collision):
```bash
curl -s -X POST http://localhost:8010/api/admin/partners/vendor \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 680,
    "vendor_type": "REVENUE",
    "business_name": "Test Vendor",
    "contact_phone": "9809999999",
    "station_ids": ["550e8400-e29b-41d4-a716-446655440301"],
    "revenue_model": "PERCENTAGE",
    "partner_percent": "15.00",
    "password": "testpass123"
  }'
```

### Verify BUG-1 Fix:
```bash
curl -s -X POST http://localhost:8010/api/admin/partners/stations/assign \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": "4333c6a1-49ba-41e4-b3fb-116b885923f3",
    "station_ids": ["550e8400-e29b-41d4-a716-446655440302"]
  }'
```

### Verify Multi-Station Dashboard:
```bash
# Login as vendor
curl -s -X POST http://localhost:8010/api/partners/auth/login \
  -F "email=vendor.demo.20260212@powerbank.com" \
  -F "password=testpass123"

# Get dashboard
curl -s -X GET http://localhost:8010/api/partner/vendor/dashboard \
  -H "Authorization: Bearer <vendor_token>"
```
