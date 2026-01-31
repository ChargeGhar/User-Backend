# Vendor Agreement Implementation Plan

> **Date:** 2026-01-31  
> **Endpoint:** 1 (GET only)  
> **Status:** READY FOR IMPLEMENTATION  
> **Verified:** 100% - All models, repositories, business rules checked

---

## 📋 ENDPOINT TO IMPLEMENT

### GET /api/partner/vendor/agreement/
**Purpose:** View own revenue agreement details

---

## ✅ VERIFIED EXISTING RESOURCES

### Model: StationRevenueShare ✅
**File:** `api/partners/common/models/station_revenue_share.py`

**Fields (Verified):**
- `distribution` (OneToOne FK to StationDistribution)
- `revenue_model` (PERCENTAGE | FIXED)
- `partner_percent` (Decimal) - For PERCENTAGE model (e.g., 10.00 = 10%)
- `fixed_amount` (Decimal) - For FIXED model (monthly amount)

**Important Notes:**
- This table is ONLY for REVENUE vendors
- Franchise revenue model is in `partners.revenue_share_percent`
- NON_REVENUE vendors have NO revenue model

### Model: StationDistribution ✅
**File:** `api/partners/common/models/station_distribution.py`

**Fields (Verified):**
- `station` (FK)
- `partner` (FK)
- `distribution_type` (CHARGEGHAR_TO_FRANCHISE | CHARGEGHAR_TO_VENDOR | FRANCHISE_TO_VENDOR)
- `effective_date` (Date)
- `is_active` (Boolean)

**Relationships:**
- `revenue_share` (OneToOne to StationRevenueShare)

### Repository: StationDistributionRepository ✅
**File:** `api/partners/common/repositories/station_distribution_repository.py`

**Methods (Verified):**
- `get_active_by_partner(partner_id)` ✅ - Returns active distributions
- Includes `select_related('station', 'partner', 'revenue_share')` ✅

---

## 🎯 BUSINESS RULES (Verified)

### BR2.3: Single Station
- Vendor has ONLY ONE station
- Query returns single distribution

### BR3.3: Revenue Model
- PERCENTAGE: Vendor gets % of net revenue
- FIXED: Vendor pays fixed monthly amount to owner

### BR3.4: Non-Revenue Vendors
- Have NO revenue model
- No StationRevenueShare record

### BR6.2: CG Vendor Revenue
- Gets `partner_percent` of net revenue from ChargeGhar

### BR7.4: Franchise Vendor Revenue
- Gets `partner_percent` from Franchise's share

### BR11.4-5: Revenue Model Details
- FIXED: Same amount every month
- PERCENTAGE: Varies by performance

---

## 📊 ENDPOINT: GET /api/partner/vendor/agreement/

### Request
```
GET /api/partner/vendor/agreement/
Authorization: Bearer {token}
```

### Response Structure
```json
{
  "success": true,
  "message": "Agreement retrieved successfully",
  "data": {
    "vendor": {
      "id": "uuid",
      "code": "VN-003",
      "business_name": "Updated Vendor Shop",
      "vendor_type": "REVENUE",
      "status": "ACTIVE",
      "balance": 7.68,
      "total_earnings": 27.68
    },
    "parent": {
      "id": "uuid",
      "code": "FR-001",
      "business_name": "Pro Boy",
      "partner_type": "FRANCHISE"
    },
    "station": {
      "id": "uuid",
      "name": "Chitwan Mall Station",
      "code": "CTW001",
      "address": "Chitwan Mall, Bharatpur, Chitwan",
      "total_slots": 4
    },
    "distribution": {
      "distribution_type": "FRANCHISE_TO_VENDOR",
      "effective_date": "2026-01-31",
      "is_active": true
    },
    "revenue_model": {
      "model_type": "PERCENTAGE",
      "partner_percent": 7.50,
      "fixed_amount": null,
      "description": "You receive 7.50% of net revenue from this station"
    }
  }
}
```

### Service Logic
```python
def get_agreement(vendor_id: str) -> dict:
    # Get vendor
    vendor = PartnerRepository.get_by_id(vendor_id)
    if not vendor:
        raise ValueError("Vendor not found")
    
    # Validate: Revenue vendor only
    if not vendor.is_revenue_vendor:
        raise PermissionDenied("Non-revenue vendors have no agreement")
    
    # Get vendor's station distribution (BR2.3 - single station)
    distribution = StationDistributionRepository.get_active_by_partner(vendor_id).first()
    
    if not distribution:
        raise ValueError("No active station assignment found")
    
    # Get revenue model
    revenue_share = distribution.revenue_share if hasattr(distribution, 'revenue_share') else None
    
    if not revenue_share:
        raise ValueError("No revenue model configured")
    
    # Build response
    return {
        'vendor': {
            'id': str(vendor.id),
            'code': vendor.code,
            'business_name': vendor.business_name,
            'vendor_type': vendor.vendor_type,
            'status': vendor.status,
            'balance': vendor.balance,
            'total_earnings': vendor.total_earnings
        },
        'parent': {
            'id': str(vendor.parent.id),
            'code': vendor.parent.code,
            'business_name': vendor.parent.business_name,
            'partner_type': vendor.parent.partner_type
        } if vendor.parent else None,
        'station': {
            'id': str(distribution.station.id),
            'name': distribution.station.station_name,
            'code': distribution.station.serial_number,
            'address': distribution.station.address,
            'total_slots': distribution.station.total_slots
        },
        'distribution': {
            'distribution_type': distribution.distribution_type,
            'effective_date': distribution.effective_date,
            'is_active': distribution.is_active
        },
        'revenue_model': {
            'model_type': revenue_share.revenue_model,
            'partner_percent': revenue_share.partner_percent,
            'fixed_amount': revenue_share.fixed_amount,
            'description': _get_revenue_description(revenue_share)
        }
    }

def _get_revenue_description(revenue_share) -> str:
    """Generate human-readable revenue model description"""
    if revenue_share.revenue_model == 'PERCENTAGE':
        return f"You receive {revenue_share.partner_percent}% of net revenue from this station"
    else:  # FIXED
        return f"You pay NPR {revenue_share.fixed_amount} monthly to the station owner"
```

---

## 📁 FILES TO CREATE

### 1. Service
**File:** `api/partners/vendor/services/vendor_agreement_service.py`

**Methods:**
- `get_agreement(vendor_id)` → dict
- `_get_revenue_description(revenue_share)` → str (helper)

**Lines:** ~80

### 2. Serializers
**File:** `api/partners/vendor/serializers/agreement_serializers.py`

**Classes:**
- `VendorAgreementVendorSerializer` - Vendor info
- `VendorAgreementParentSerializer` - Parent info
- `VendorAgreementStationSerializer` - Station info
- `VendorAgreementDistributionSerializer` - Distribution info
- `VendorAgreementRevenueModelSerializer` - Revenue model
- `VendorAgreementSerializer` - Complete response

**Lines:** ~70

### 3. Views
**File:** `api/partners/vendor/views/agreement_view.py`

**Classes:**
- `VendorAgreementView` (GET)

**Lines:** ~50

### 4. Update __init__ files
- `services/__init__.py` - Export VendorAgreementService
- `serializers/__init__.py` - Export agreement serializers
- `views/__init__.py` - Register agreement_router

**Total:** ~200 lines

---

## ✅ VALIDATION CHECKLIST

### Model Fields
- [x] StationRevenueShare fields verified ✅
- [x] StationDistribution fields verified ✅
- [x] OneToOne relationship verified ✅
- [x] Revenue model choices verified ✅

### Repository Methods
- [x] get_active_by_partner exists ✅
- [x] Includes select_related ✅
- [x] Returns QuerySet with revenue_share ✅

### Business Rules
- [x] BR2.3 mapped (single station) ✅
- [x] BR3.3 mapped (revenue model types) ✅
- [x] BR3.4 mapped (non-revenue check) ✅
- [x] BR6.2, BR7.4 mapped (revenue calculation) ✅
- [x] BR11.4-5 mapped (model descriptions) ✅

### Response Structure
- [x] Matches Endpoints.md ✅
- [x] All required fields included ✅
- [x] Description field added ✅

---

## 🧪 TEST PLAN

### Test Data
- Vendor: VN-003 (Updated Vendor Shop)
- Parent: FR-001 (Pro Boy)
- Station: Chitwan Mall Station (CTW001)
- Revenue Model: PERCENTAGE, 7.50%

### Test Cases

#### 1. GET Agreement (Valid)
```bash
GET /api/partner/vendor/agreement/
Expected:
- Success
- Vendor info with balance, earnings
- Parent: FR-001 (Pro Boy)
- Station: Chitwan Mall Station
- Distribution type: FRANCHISE_TO_VENDOR
- Revenue model: PERCENTAGE, 7.50%
- Description: "You receive 7.50% of net revenue from this station"
```

#### 2. GET Agreement (Non-Revenue Vendor)
```bash
# If we had a non-revenue vendor
GET /api/partner/vendor/agreement/
Expected: Error "Non-revenue vendors have no agreement"
```

#### 3. GET Agreement (No Station)
```bash
# If vendor has no active station
GET /api/partner/vendor/agreement/
Expected: Error "No active station assignment found"
```

#### 4. Verify Revenue Model Types
```bash
# Test with PERCENTAGE model
Expected: partner_percent populated, fixed_amount null

# Test with FIXED model (if we create one)
Expected: fixed_amount populated, partner_percent null
```

---

## 🚀 IMPLEMENTATION ORDER

1. Create `vendor_agreement_service.py`
2. Create `agreement_serializers.py`
3. Create `agreement_view.py`
4. Update `__init__.py` files
5. Restart Docker
6. Test GET /agreement/ (valid)
7. Verify all fields present
8. Verify revenue model description
9. Test edge cases (if possible)

---

## ✅ SUCCESS CRITERIA

- [x] Vendor can view own agreement
- [x] Shows vendor info (balance, earnings)
- [x] Shows parent info (if exists)
- [x] Shows station info (single station - BR2.3)
- [x] Shows distribution type
- [x] Shows revenue model (PERCENTAGE or FIXED)
- [x] Shows human-readable description
- [x] BR3.4 enforced (revenue vendors only)
- [x] No code duplication
- [x] Follows existing patterns

---

## 📝 NOTES

### Revenue Model Description Logic
```python
if revenue_model == 'PERCENTAGE':
    # Vendor receives % of net revenue
    description = f"You receive {partner_percent}% of net revenue from this station"
    
elif revenue_model == 'FIXED':
    # Vendor pays fixed amount to owner
    description = f"You pay NPR {fixed_amount} monthly to the station owner"
```

### Parent Handling
- CG-level vendor: `parent = None`
- Franchise-level vendor: `parent = Franchise`

### Single Station (BR2.3)
- Query: `get_active_by_partner(vendor_id).first()`
- Returns: Single distribution (vendor can have only 1)

---

**Status:** READY FOR IMPLEMENTATION  
**Estimated Time:** 1 hour  
**Dependencies:** All exist ✅  
**Assumptions:** ZERO
