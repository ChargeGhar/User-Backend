# Franchise Endpoint: Station Details

> **Endpoint:** `GET /api/partner/franchise/stations/{id}/`  
> **Status:** READY FOR IMPLEMENTATION  
> **Priority:** HIGH (Phase 2)

---

## 1. Endpoint Specification

### Request
```http
GET /api/partner/franchise/stations/550e8400-e29b-41d4-a716-446655440301/
Authorization: Bearer {franchise_access_token}
```

### Response (200 OK)
```json
{
  "success": true,
  "message": "Station details retrieved successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440301",
    "station_name": "Chitwan Mall Station",
    "serial_number": "CTW001",
    "imei": "123456789012347",
    "latitude": "27.700769000000000",
    "longitude": "84.429359000000000",
    "address": "Chitwan Mall, Bharatpur, Chitwan",
    "landmark": "Near food court",
    "description": "Station located at main entrance",
    "total_slots": 4,
    "status": "ONLINE",
    "is_maintenance": false,
    "is_deleted": false,
    "hardware_info": {},
    "last_heartbeat": "2024-01-01T12:00:00Z",
    "opening_time": "09:00:00",
    "closing_time": "21:00:00",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
    "amenities": [
      {
        "id": "uuid",
        "name": "WiFi",
        "icon": "wifi",
        "description": "Free WiFi available",
        "is_active": true,
        "is_available": true
      }
    ],
    "media": [
      {
        "id": "uuid",
        "media_upload_id": "uuid",
        "media_type": "IMAGE",
        "title": "Station Front View",
        "description": null,
        "is_primary": true,
        "file_url": "https://cloudinary.com/...",
        "thumbnail_url": "https://cloudinary.com/...",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "slots": [
      {
        "id": "uuid",
        "slot_number": 1,
        "status": "AVAILABLE",
        "battery_level": 100,
        "last_updated": "2024-01-01T12:00:00Z",
        "powerbank": {
          "id": "uuid",
          "serial_number": "PB001",
          "model": "Model X",
          "capacity_mah": 10000,
          "battery_level": 100,
          "status": "AVAILABLE"
        },
        "current_rental_id": null
      }
    ],
    "powerbanks": [
      {
        "id": "uuid",
        "serial_number": "PB001",
        "model": "Model X",
        "capacity_mah": 10000,
        "status": "AVAILABLE",
        "battery_level": 100,
        "slot_number": 1,
        "last_updated": "2024-01-01T12:00:00Z"
      }
    ],
    "distribution": {
      "id": "uuid",
      "distribution_type": "CHARGEGHAR_TO_FRANCHISE",
      "effective_date": "2026-01-24",
      "is_active": true
    },
    "vendor": null
  }
}
```

---

## 2. Business Rules

### BR10.2 - Franchise Control Scope
✅ **Rule:** Franchise can only view their own stations  
**Implementation:** Verify station belongs to franchise via `station_distributions`

### BR12.2 - Visibility Rules
✅ **Rule:** Franchise views only own station data  
**Implementation:** Check `partner_id = franchise.id` in distribution

---

## 3. Implementation

### Service Method
```python
def get_station_detail(self, franchise: Partner, station_id: str) -> Dict:
    """Get detailed station info with slots, powerbanks, media"""
    from api.user.stations.models import Station, PowerBank
    
    # Verify ownership
    station = Station.objects.filter(
        id=station_id,
        partner_distributions__partner_id=franchise.id,
        partner_distributions__distribution_type='CHARGEGHAR_TO_FRANCHISE',
        partner_distributions__is_active=True,
        is_deleted=False
    ).select_related().prefetch_related(
        'slots__current_rental',
        'amenity_mappings__amenity',
        'media__media_upload'
    ).first()
    
    if not station:
        raise ServiceException("Station not found or access denied", "STATION_NOT_FOUND")
    
    # Get distribution
    franchise_dist = StationDistribution.objects.filter(
        station_id=station.id,
        partner_id=franchise.id,
        distribution_type='CHARGEGHAR_TO_FRANCHISE',
        is_active=True
    ).first()
    
    # Get vendor
    vendor_dist = StationDistribution.objects.filter(
        station_id=station.id,
        distribution_type='FRANCHISE_TO_VENDOR',
        is_active=True
    ).select_related('partner').first()
    
    # Get amenities
    amenities = [{
        'id': m.amenity.id,
        'name': m.amenity.name,
        'icon': m.amenity.icon,
        'description': m.amenity.description,
        'is_active': m.amenity.is_active,
        'is_available': m.is_available
    } for m in station.amenity_mappings.filter(amenity__is_active=True)]
    
    # Get media
    media = [{
        'id': sm.id,
        'media_upload_id': sm.media_upload.id,
        'media_type': sm.media_type,
        'title': sm.title,
        'description': sm.description,
        'is_primary': sm.is_primary,
        'file_url': sm.media_upload.file_url,
        'thumbnail_url': sm.media_upload.file_url,
        'created_at': sm.created_at
    } for sm in station.media.select_related('media_upload').order_by('-is_primary', 'created_at')]
    
    # Get slots with powerbanks
    slots = []
    for slot in station.slots.order_by('slot_number'):
        powerbank = PowerBank.objects.filter(current_slot=slot).first()
        slots.append({
            'id': slot.id,
            'slot_number': slot.slot_number,
            'status': slot.status,
            'battery_level': slot.battery_level,
            'last_updated': slot.last_updated,
            'powerbank': {
                'id': powerbank.id,
                'serial_number': powerbank.serial_number,
                'model': powerbank.model,
                'capacity_mah': powerbank.capacity_mah,
                'battery_level': powerbank.battery_level,
                'status': powerbank.status
            } if powerbank else None,
            'current_rental_id': str(slot.current_rental.id) if slot.current_rental else None
        })
    
    # Get all powerbanks at station
    powerbanks = [{
        'id': pb.id,
        'serial_number': pb.serial_number,
        'model': pb.model,
        'capacity_mah': pb.capacity_mah,
        'status': pb.status,
        'battery_level': pb.battery_level,
        'slot_number': pb.current_slot.slot_number if pb.current_slot else None,
        'last_updated': pb.last_updated
    } for pb in PowerBank.objects.filter(current_station=station).select_related('current_slot')]
    
    return {
        'id': station.id,
        'station_name': station.station_name,
        'serial_number': station.serial_number,
        'imei': station.imei,
        'latitude': station.latitude,
        'longitude': station.longitude,
        'address': station.address,
        'landmark': station.landmark,
        'description': station.description,
        'total_slots': station.total_slots,
        'status': station.status,
        'is_maintenance': station.is_maintenance,
        'is_deleted': station.is_deleted,
        'hardware_info': station.hardware_info,
        'last_heartbeat': station.last_heartbeat,
        'opening_time': station.opening_time,
        'closing_time': station.closing_time,
        'created_at': station.created_at,
        'updated_at': station.updated_at,
        'amenities': amenities,
        'media': media,
        'slots': slots,
        'powerbanks': powerbanks,
        'distribution': {
            'id': franchise_dist.id,
            'distribution_type': franchise_dist.distribution_type,
            'effective_date': franchise_dist.effective_date,
            'is_active': franchise_dist.is_active,
        } if franchise_dist else None,
        'vendor': {
            'id': vendor_dist.partner.id,
            'code': vendor_dist.partner.code,
            'business_name': vendor_dist.partner.business_name,
            'vendor_type': vendor_dist.partner.vendor_type,
            'status': vendor_dist.partner.status,
        } if vendor_dist else None
    }
```

### View
```python
@franchise_station_router.register(
    r"partner/franchise/stations/(?P<station_id>[0-9a-f-]+)",
    name="franchise-station-detail"
)
class FranchiseStationDetailView(GenericAPIView, BaseAPIView):
    permission_classes = [IsFranchise]
    
    @log_api_call()
    def get(self, request: Request, station_id: str) -> Response:
        def operation():
            franchise = request.user.partner_profile
            service = FranchiseService()
            return service.get_station_detail(franchise, station_id)
        
        return self.handle_service_operation(
            operation,
            "Station details retrieved successfully",
            "Failed to retrieve station details"
        )
```

---

## 4. Ready to Implement

**Files to modify:**
1. `franchise_service.py` - Add `get_station_detail()` method
2. `franchise_station_view.py` - Add detail view class
3. No new serializers needed (return dict directly)

**Estimated time:** 30 minutes

Ready to implement?
