# Immediate Fixes Plan

## Overview
Three immediate fixes required from `plans/new/Rough/Remenings.txt`:
1. GET endpoint for station and rental issue types
2. Admin station detail missing media URLs (verification)
3. Latitude/Longitude field precision fix

---

## FIX 1: Issue Types Endpoint

### Requirement
Single GET endpoint returning both station and rental issue type choices for mobile app dropdowns.

### Source Files (Read-Only)
| File | Content |
|------|---------|
| `api/user/stations/models/issue.py` | `StationIssue.ISSUE_TYPE_CHOICES` |
| `api/user/rentals/models/rental.py` | `RentalIssue.ISSUE_TYPE_CHOICES` |

### Issue Type Choices (Current)
```python
# StationIssue.ISSUE_TYPE_CHOICES
OFFLINE, DAMAGED, DIRTY, LOCATION_WRONG, SLOT_ERROR, AMENITY_ISSUE

# RentalIssue.ISSUE_TYPE_CHOICES  
POWER_BANK_DAMAGED, POWER_BANK_LOST, CHARGING_ISSUE, RETURN_ISSUE
```

### Implementation

#### 1. Create View: `api/user/system/views/issue_types_views.py`
```python
"""Issue types endpoint for mobile app"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.permissions import AllowAny

from api.common.routers import CustomViewRouter
from api.common.mixins import BaseAPIView
from api.common.decorators import log_api_call
from api.user.system.serializers import IssueTypesResponseSerializer
from api.user.stations.models import StationIssue
from api.user.rentals.models import RentalIssue

issue_types_router = CustomViewRouter()

@issue_types_router.register(r"app/issue-types", name="issue-types")
@extend_schema(
    tags=["App"],
    summary="Get Issue Types",
    description="Get all issue type choices for stations and rentals",
    responses={200: IssueTypesResponseSerializer}
)
class IssueTypesView(GenericAPIView, BaseAPIView):
    """Get issue type choices for dropdowns"""
    permission_classes = [AllowAny]
    
    @log_api_call()
    def get(self, request: Request):
        def operation():
            return {
                "station_issue_types": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in StationIssue.ISSUE_TYPE_CHOICES
                ],
                "rental_issue_types": [
                    {"value": choice[0], "label": choice[1]}
                    for choice in RentalIssue.ISSUE_TYPE_CHOICES
                ]
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Issue types retrieved",
            error_message="Failed to get issue types"
        )
```

#### 2. Add Serializer: `api/user/system/serializers.py` (append)
```python
class IssueTypeChoiceSerializer(serializers.Serializer):
    """Single issue type choice"""
    value = serializers.CharField()
    label = serializers.CharField()

class IssueTypesResponseSerializer(serializers.Serializer):
    """Response for issue types endpoint"""
    station_issue_types = IssueTypeChoiceSerializer(many=True)
    rental_issue_types = IssueTypeChoiceSerializer(many=True)
```

#### 3. Update: `api/user/system/views/__init__.py`
```python
# Add import
from .issue_types_views import issue_types_router

# Add to router merge loop
for sub_router in [country_router, app_info_router, app_updates_router, issue_types_router]:
```

### Endpoint
```
GET /api/app/issue-types
```

### Response Example
```json
{
  "success": true,
  "message": "Issue types retrieved",
  "data": {
    "station_issue_types": [
      {"value": "OFFLINE", "label": "Offline"},
      {"value": "DAMAGED", "label": "Damaged"}
    ],
    "rental_issue_types": [
      {"value": "POWER_BANK_DAMAGED", "label": "Power Bank Damaged"},
      {"value": "CHARGING_ISSUE", "label": "Charging Issue"}
    ]
  }
}
```

---

## FIX 2: Admin Station Media URLs - ✅ ALREADY DONE

### Verification
Detail endpoint already returns media with `file_url`:
```
GET /api/admin/stations/<sn> → returns media[] with file_url ✅
```

**No changes needed** - `AdminStationDetailSerializer` already has `get_media()` method.

---

## FIX 3: Latitude/Longitude Precision

### Requirement
Extend lat/lng field precision to handle longer coordinate values.

### Current Model
File: `api/user/stations/models/station.py`
```python
latitude = models.DecimalField(max_digits=10, decimal_places=6)
longitude = models.DecimalField(max_digits=10, decimal_places=6)
```

### Problem
- `max_digits=10, decimal_places=6` allows: `±9999.999999`
- Integer part: 4 digits max
- Valid lat range: `-90.000000` to `90.000000` (2-3 integer digits)
- Valid lng range: `-180.000000` to `180.000000` (3-4 integer digits)

Current config is sufficient for valid coordinates. Error likely from:
1. Invalid input data (not actual coordinates)
2. Serializer validation mismatch

### Recommended Fix
Increase precision for safety margin:

#### 1. Update Model: `api/user/stations/models/station.py`
```python
# Change from:
latitude = models.DecimalField(max_digits=10, decimal_places=6)
longitude = models.DecimalField(max_digits=10, decimal_places=6)

# Change to:
latitude = models.DecimalField(max_digits=11, decimal_places=8)
longitude = models.DecimalField(max_digits=12, decimal_places=8)
```

Rationale:
- Latitude: `max_digits=11, decimal_places=8` → `±999.99999999` (handles `-90.12345678`)
- Longitude: `max_digits=12, decimal_places=8` → `±9999.99999999` (handles `-180.12345678`)
- 8 decimal places = ~1.1mm precision (more than enough)

#### 2. Update Serializers: `api/admin/serializers/station_serializers.py`

Update lat/lng in these 4 locations:

| Serializer | Line | Field |
|------------|------|-------|
| `AdminStationSerializer` | 182-184 | read_only |
| `AdminStationDetailSerializer` | 239-241 | read_only |
| `CreateStationSerializer` | 326-328 | input |
| `UpdateStationSerializer` | 495-497 | input |

```python
# Change all from:
latitude = serializers.DecimalField(max_digits=10, decimal_places=6, ...)
longitude = serializers.DecimalField(max_digits=10, decimal_places=6, ...)

# To:
latitude = serializers.DecimalField(max_digits=11, decimal_places=8, ...)
longitude = serializers.DecimalField(max_digits=12, decimal_places=8, ...)
```

#### 3. Update RentalLocation Model: `api/user/rentals/models/rental.py`
```python
# Change:
latitude = models.DecimalField(max_digits=10, decimal_places=6)
longitude = models.DecimalField(max_digits=10, decimal_places=6)

# To:
latitude = models.DecimalField(max_digits=11, decimal_places=8)
longitude = models.DecimalField(max_digits=12, decimal_places=8)
```

#### 4. Create Migration
```bash
python manage.py makemigrations stations rentals --name extend_lat_lng_precision
python manage.py migrate
```

---

## Implementation Checklist

| # | Task | File | Line | Status |
|---|------|------|------|--------|
| 1a | Create issue_types_views.py | `api/user/system/views/issue_types_views.py` | new | TODO |
| 1b | Add serializers | `api/user/system/serializers.py` | append | TODO |
| 1c | Update views __init__ | `api/user/system/views/__init__.py` | 8,14 | TODO |
| 2 | Admin station media URLs | - | - | ✅ DONE |
| 3a | Update Station model lat/lng | `api/user/stations/models/station.py` | 18-19 | ✅ DONE |
| 3b | Update RentalLocation model lat/lng | `api/user/rentals/models/rental.py` | 179-180 | ✅ DONE |
| 3c | Update AdminStationSerializer | `api/admin/serializers/station_serializers.py` | 182-184 | ✅ DONE |
| 3d | Update AdminStationDetailSerializer | `api/admin/serializers/station_serializers.py` | 239-241 | ✅ DONE |
| 3e | Update CreateStationSerializer | `api/admin/serializers/station_serializers.py` | 326-328 | ✅ DONE |
| 3f | Update UpdateStationSerializer | `api/admin/serializers/station_serializers.py` | 495-497 | ✅ DONE |
| 3g | Run migrations | CLI | - | ✅ DONE |

---

## Notes
- Fix 1: New endpoint, no breaking changes
- Fix 2: ✅ Already done - detail endpoint returns media
- Fix 3: Migration required, backward compatible (field expansion)
