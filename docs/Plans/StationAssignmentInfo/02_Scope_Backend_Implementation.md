# Scope 2 – Backend Implementation

## Step 1 – Create `StationDistributionRepository.get_assigned_partner()`
**File:** `UserBackend/api/partners/common/repositories/station_distribution_repository.py`

Add a **single** class-method that returns the `Partner` instance according to the priority defined in `01_Scope_Response_Enrichment.md`.

```python
@staticmethod
def get_assigned_partner(station_id: str) -> Optional[Partner]:
    """
    Return the partner that should be shown as 'assignedPartner' for a station.
    Priority: FRANCHISE_TO_VENDOR > CHARGEGHAR_TO_FRANCHISE > CHARGEGHAR_TO_VENDOR
    """
    distributions = StationDistribution.objects.filter(
        station_id=station_id,
        is_active=True
    ).select_related('partner').order_by(
        # Force priority via a simple conditional annotation or manual sort.
        # Django cannot order by raw string values directly without Case/When.
        models.Case(
            models.When(distribution_type=StationDistribution.DistributionType.FRANCHISE_TO_VENDOR, then=models.Value(0)),
            models.When(distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_FRANCHISE, then=models.Value(1)),
            models.When(distribution_type=StationDistribution.DistributionType.CHARGEGHAR_TO_VENDOR, then=models.Value(2)),
            default=models.Value(3),
            output_field=models.IntegerField(),
        )
    )
    first = distributions.first()
    return first.partner if first else None
```

> **Why here?** The repository already owns `get_station_operator()` and `get_station_franchise()` (per model comment). Adding the unified lookup here keeps the rule in one place.

## Step 2 – Add `assignedPartner` helper for services/serializers
**File:** `UserBackend/api/partners/common/services/partner_station_service.py`

Add a **module-level** private helper that both admin and partner code can call:

```python
def _get_assigned_partner_info(station_id: str) -> Dict[str, Any]:
    partner = StationDistributionRepository.get_assigned_partner(station_id)
    if not partner:
        return {"isAssigned": False, "assignedPartner": None}
    return {
        "isAssigned": True,
        "assignedPartner": {
            "id": str(partner.id),
            "businessName": partner.business_name,
            "partnerType": partner.partner_type,
            "vendorType": partner.vendor_type if partner.is_vendor else None,
            "status": partner.status,
        },
    }
```

## Step 3 – Admin List (`GET /api/admin/stations`)
**Files:**
- `UserBackend/api/admin/serializers/station_serializers.py` – add fields to `AdminStationSerializer`
- `UserBackend/api/admin/services/admin_station_service.py` – bulk-fetch partners for the page

### 3a – Serializer changes
Add to `AdminStationSerializer`:
```python
is_assigned = serializers.SerializerMethodField()
assigned_partner = serializers.SerializerMethodField()

def get_is_assigned(self, obj):
    # Will be populated by service via annotation or bulk lookup
    return getattr(obj, '_is_assigned', False)

def get_assigned_partner(self, obj):
    return getattr(obj, '_assigned_partner', None)
```

### 3b – Service changes
In `AdminStationService.get_stations_list()`, **after** pagination, iterate `result['results']` and attach the partner info in bulk:

```python
station_ids = [s.id for s in result['results']]
partner_map = self._get_assigned_partner_map(station_ids)
for station in result['results']:
    info = partner_map.get(str(station.id), {"isAssigned": False, "assignedPartner": None})
    station._is_assigned = info["isAssigned"]
    station._assigned_partner = info["assignedPartner"]
```

Add a private helper `_get_assigned_partner_map(station_ids)` that uses the repository method from Step 1 in a loop or a single optimized query.

> **Constraint:** Do **not** change the pagination SQL to avoid N+1. Perform the enrichment after the page is sliced.

## Step 4 – Admin Detail (`GET /api/admin/stations/<station_sn>`)
**File:** `UserBackend/api/admin/serializers/station_serializers.py`

Add the same two fields to `AdminStationDetailSerializer`.

Use `SerializerMethodField` and read the partner via the repository helper directly (single station, no bulk concern).

## Step 5 – Partner List (`GET /api/partner/stations`)
**File:** `UserBackend/api/partners/common/services/partner_station_service.py`

In `get_stations_list()`, the service already loops over `stations` to build `station_data` dicts. At the point where each dict is assembled, merge in `_get_assigned_partner_info(station.id)`.

Example insertion point (after the existing dict build, before appending to `results`):
```python
station_info = _get_assigned_partner_info(station.id)
station_data.update(station_info)
```

## Step 6 – Partner Detail (`GET /api/partner/stations/<station_id>`)
**File:** `UserBackend/api/partners/common/services/partner_station_service.py`

In `get_station_detail()`, merge `_get_assigned_partner_info(station.id)` into the returned dict at the top level.

Insertion point: just before the final `return {…}` block.

## Step 7 – Update OpenAPI / DRF Spectacular
Add the new fields to any response serializer used by `@extend_schema` if the schema is generated from a serializer rather than `BaseResponseSerializer`. Otherwise the fields will still appear because they are returned in the nested `data` payload.

No separate schema file changes are required if the API uses `BaseResponseSerializer(data=…)` pattern.

## Exact Files to Touch (No More, No Less)
1. `UserBackend/api/partners/common/repositories/station_distribution_repository.py`
2. `UserBackend/api/partners/common/services/partner_station_service.py`
3. `UserBackend/api/admin/serializers/station_serializers.py`
4. `UserBackend/api/admin/services/admin_station_service.py`
