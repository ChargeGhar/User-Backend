# Swapping Support - Complete Plan

> **Version:** 1.0  
> **Created:** 2026-01-30  
> **Status:** REVIEW REQUIRED

---

## 1. What is Swapping?

### 1.1 Definition

**Swapping** = User exchanges current rented powerbank for a different one at the SAME station within a time window.

**NOT Swapping:**
- Returning to a different station = Normal return
- Cancelling and starting new rental = Two separate transactions
- Extending rental time = Extension (different feature)

### 1.2 Use Cases

1. User gets a powerbank with low battery
2. User gets a defective powerbank
3. User accidentally took wrong cable type
4. Powerbank physical damage noticed after ejection

### 1.3 Business Rules from 10_rental_lifecycle.md

```python
# From 10.4 Swapping Rate Limit:
# User can swap only up to total available powerbank count of that station per day.
```

---

## 2. Swapping vs Cancellation Comparison

| Aspect | Swapping | Cancellation |
|--------|----------|--------------|
| Time Window | `SWAPPING_MAX_TIME` (5 min) | `NO_CHARGE_RENTAL_CANCELLATION_TIME` (5 min) |
| End Result | New powerbank, SAME rental | Rental ended, refund |
| Powerbank Requirement | Must return current PB | Must return current PB |
| Rental Status | Stays ACTIVE | Becomes CANCELLED |
| Transaction | No new transaction | Transaction may be refunded |
| Daily Limit | Station's available PB count | No limit |

---

## 3. Swapping Rules

### 3.1 Time Window

| Config Key | Default Value | Description |
|------------|---------------|-------------|
| `SWAPPING_MAX_TIME` | `5` (minutes) | Max time from rental start to allow swap |

### 3.2 Eligibility Criteria

```
User can swap IF:
1. Rental status is ACTIVE
2. Time since rental.started_at <= SWAPPING_MAX_TIME
3. Current powerbank is returned to station (in slot)
4. Station has at least 1 other available powerbank
5. User has not exceeded daily swap limit for this station
```

### 3.3 Daily Swap Limit

From `10_rental_lifecycle.md`:

```python
def check_swap_limit(user, station):
    """Check if user has exceeded daily swap limit for this station"""
    today = timezone.now().date()
    
    # Count swaps for this user at this station today
    today_swaps = RentalSwap.objects.filter(
        rental__user=user,
        original_station=station,
        created_at__date=today
    ).count()
    
    # Get available slots count
    available_count = station.slots.filter(
        status='AVAILABLE',
        power_bank__isnull=False,
        power_bank__status='AVAILABLE',
        power_bank__battery_level__gte=20
    ).count()
    
    if today_swaps >= available_count:
        raise ServiceException(
            detail=f"Daily swap limit ({available_count}) reached for this station",
            code="swap_limit_exceeded"
        )
```

---

## 4. Swapping Flow

### 4.1 API Endpoint

**New Endpoint:** `POST /api/rentals/{rental_id}/swap`

### 4.2 Request/Response

**Request:**
```json
{
  "reason": "low_battery|defective|wrong_cable|other",
  "description": "Optional additional details"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Powerbank swapped successfully",
  "data": {
    "rental_id": "uuid",
    "rental_code": "RNT-XXXXX",
    "old_powerbank": {
      "serial_number": "PB-OLD-001",
      "battery_level": 15
    },
    "new_powerbank": {
      "serial_number": "PB-NEW-002",
      "battery_level": 85
    },
    "swap_count_today": 1,
    "max_swaps_today": 5
  }
}
```

### 4.3 Flow Diagram

```
POST /api/rentals/{rental_id}/swap
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. VALIDATE RENTAL                                               │
│    ├── Rental exists and belongs to user                         │
│    ├── Rental status == 'ACTIVE'                                 │
│    └── Time since start <= SWAPPING_MAX_TIME                     │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. VALIDATE POWERBANK RETURN                                     │
│    ├── Current powerbank is in a slot at rental.station         │
│    └── Slot status is OCCUPIED with this powerbank              │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. CHECK SWAP LIMITS                                             │
│    ├── Get today's swap count for user at this station           │
│    ├── Get available powerbank count at station                  │
│    └── IF swap_count >= available_count: BLOCK                   │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. GET NEW POWERBANK                                             │
│    ├── Find available powerbank with battery >= 20%              │
│    ├── Exclude current powerbank                                 │
│    └── Lock new powerbank for atomic operation                   │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. TRIGGER DEVICE POPUP                                          │
│    └── Same logic as start_rental() device popup                 │
└──────────────────────────────────────────────────────────────────┘
       │
       ├─── SUCCESS ───┐
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 6. UPDATE RENTAL                                      │
       │   │    ├── rental.power_bank = new_powerbank              │
       │   │    ├── rental.slot = new_slot                         │
       │   │    └── Store swap info in rental_metadata             │
       │   └───────────────────────────────────────────────────────┘
       │               │
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 7. RELEASE OLD POWERBANK                              │
       │   │    ├── old_powerbank.status = 'AVAILABLE'             │
       │   │    └── old_slot.status = 'AVAILABLE'                  │
       │   └───────────────────────────────────────────────────────┘
       │               │
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 8. CREATE SWAP LOG                                    │
       │   │    └── RentalSwap.create(rental, old_pb, new_pb)      │
       │   └───────────────────────────────────────────────────────┘
       │               │
       │               ▼
       │   ┌───────────────────────────────────────────────────────┐
       │   │ 9. SEND NOTIFICATION                                  │
       │   │    └── notify(user, 'rental_swapped', ...)            │
       │   └───────────────────────────────────────────────────────┘
       │
       └─── FAILURE ───┐
                       ▼
           ┌───────────────────────────────────────────────────────┐
           │ Rollback, keep original rental state                  │
           │ Return error to user                                  │
           └───────────────────────────────────────────────────────┘
```

---

## 5. Database Changes

### 5.1 New Model: RentalSwap

```python
# api/user/rentals/models/rental.py

class RentalSwap(BaseModel):
    """
    RentalSwap - Log of powerbank swaps within a rental.
    """
    SWAP_REASON_CHOICES = [
        ('LOW_BATTERY', 'Low Battery'),
        ('DEFECTIVE', 'Defective Powerbank'),
        ('WRONG_CABLE', 'Wrong Cable Type'),
        ('OTHER', 'Other'),
    ]
    
    rental = models.ForeignKey(
        Rental, 
        on_delete=models.CASCADE, 
        related_name='swaps'
    )
    original_station = models.ForeignKey(
        'stations.Station', 
        on_delete=models.CASCADE,
        related_name='rental_swaps'
    )
    
    # Old powerbank
    old_powerbank = models.ForeignKey(
        'stations.PowerBank',
        on_delete=models.SET_NULL,
        null=True,
        related_name='swapped_from'
    )
    old_slot = models.ForeignKey(
        'stations.StationSlot',
        on_delete=models.SET_NULL,
        null=True,
        related_name='swapped_from'
    )
    old_battery_level = models.IntegerField()
    
    # New powerbank
    new_powerbank = models.ForeignKey(
        'stations.PowerBank',
        on_delete=models.SET_NULL,
        null=True,
        related_name='swapped_to'
    )
    new_slot = models.ForeignKey(
        'stations.StationSlot',
        on_delete=models.SET_NULL,
        null=True,
        related_name='swapped_to'
    )
    new_battery_level = models.IntegerField()
    
    # Swap details
    swap_reason = models.CharField(max_length=50, choices=SWAP_REASON_CHOICES)
    description = models.TextField(null=True, blank=True)
    swapped_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rental_swaps'
        verbose_name = 'Rental Swap'
        verbose_name_plural = 'Rental Swaps'
        indexes = [
            models.Index(fields=['rental', 'swapped_at']),
            models.Index(fields=['original_station', 'swapped_at']),
        ]
    
    def __str__(self):
        return f"{self.rental.rental_code} - Swap #{self.pk}"
```

### 5.2 Rental Model Update

Add to `rental_metadata` structure:

```json
{
  "swaps": [
    {
      "swap_id": "uuid",
      "old_powerbank_sn": "PB-001",
      "new_powerbank_sn": "PB-002",
      "reason": "LOW_BATTERY",
      "swapped_at": "2026-01-30T10:05:00Z"
    }
  ],
  "total_swap_count": 1
}
```

---

## 6. Service Implementation

### 6.1 New File: `api/user/rentals/services/rental/swap.py`

```python
"""
Rental Swap Service
===================

Handles powerbank swapping within active rentals.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from api.common.services.base import ServiceException
from api.user.rentals.models import Rental, RentalSwap
from api.user.stations.models import Station, PowerBank


class RentalSwapMixin:
    """Mixin for rental swap operations"""
    
    @transaction.atomic
    def swap_powerbank(
        self, 
        rental_id: str, 
        user, 
        reason: str = 'OTHER',
        description: str = ''
    ) -> Rental:
        """
        Swap current powerbank for a different one at same station.
        
        Rules:
        1. Must be within SWAPPING_MAX_TIME from rental start
        2. Current powerbank must be returned to station
        3. Daily swap limit per station applies
        """
        try:
            rental = Rental.objects.select_for_update().get(id=rental_id, user=user)
            
            # Validate swap eligibility
            self._validate_swap_eligibility(rental)
            self._validate_powerbank_returned_for_swap(rental)
            self._check_swap_limit(user, rental.station)
            
            # Store old powerbank info
            old_powerbank = rental.power_bank
            old_slot = rental.slot
            old_battery = old_powerbank.battery_level
            
            # Get new powerbank
            new_powerbank, new_slot = self._get_swap_powerbank(
                rental.station, 
                exclude_powerbank_id=str(old_powerbank.id)
            )
            
            # Trigger device popup for new powerbank
            popup_success, popup_sn = self._trigger_device_popup(
                rental, rental.station, new_powerbank, None
            )
            
            if not popup_success:
                raise ServiceException(
                    detail="Failed to dispense new powerbank. Please try again.",
                    code="swap_popup_failed"
                )
            
            # Update rental with new powerbank
            rental.power_bank = new_powerbank
            rental.slot = new_slot
            
            # Update metadata
            swap_info = {
                'old_powerbank_sn': old_powerbank.serial_number,
                'new_powerbank_sn': new_powerbank.serial_number,
                'reason': reason,
                'swapped_at': timezone.now().isoformat()
            }
            
            if 'swaps' not in rental.rental_metadata:
                rental.rental_metadata['swaps'] = []
            rental.rental_metadata['swaps'].append(swap_info)
            rental.rental_metadata['total_swap_count'] = len(rental.rental_metadata['swaps'])
            
            rental.save(update_fields=['power_bank', 'slot', 'rental_metadata'])
            
            # Release old powerbank
            old_powerbank.status = 'AVAILABLE'
            old_powerbank.save(update_fields=['status'])
            
            old_slot.status = 'AVAILABLE'
            old_slot.current_rental = None
            old_slot.save(update_fields=['status', 'current_rental'])
            
            # Assign new powerbank
            from api.user.stations.services import PowerBankService
            pb_service = PowerBankService()
            pb_service.assign_power_bank_to_rental(new_powerbank, rental)
            
            # Create swap log
            RentalSwap.objects.create(
                rental=rental,
                original_station=rental.station,
                old_powerbank=old_powerbank,
                old_slot=old_slot,
                old_battery_level=old_battery,
                new_powerbank=new_powerbank,
                new_slot=new_slot,
                new_battery_level=new_powerbank.battery_level,
                swap_reason=reason,
                description=description
            )
            
            # Send notification
            self._send_swap_notification(user, rental, old_powerbank, new_powerbank)
            
            self.log_info(
                f"Powerbank swapped for rental {rental.rental_code}: "
                f"{old_powerbank.serial_number} -> {new_powerbank.serial_number}"
            )
            
            return rental
            
        except Rental.DoesNotExist:
            raise ServiceException(detail="Rental not found", code="rental_not_found")
        except Exception as e:
            self.handle_service_error(e, "Failed to swap powerbank")
    
    def _validate_swap_eligibility(self, rental: Rental) -> None:
        """Check if rental is eligible for swap"""
        if rental.status != 'ACTIVE':
            raise ServiceException(
                detail="Only active rentals can swap powerbanks",
                code="invalid_rental_status"
            )
        
        if not rental.started_at:
            raise ServiceException(
                detail="Rental has not started yet",
                code="rental_not_started"
            )
        
        from api.user.system.models import AppConfig
        
        swap_window_minutes = int(AppConfig.objects.filter(
            key='SWAPPING_MAX_TIME', is_active=True
        ).values_list('value', flat=True).first() or 5)
        
        time_since_start = timezone.now() - rental.started_at
        
        if time_since_start.total_seconds() > (swap_window_minutes * 60):
            raise ServiceException(
                detail=f"Swap window expired. Swapping is only allowed within {swap_window_minutes} minutes of rental start.",
                code="swap_window_expired"
            )
    
    def _validate_powerbank_returned_for_swap(self, rental: Rental) -> None:
        """Verify powerbank is back in station for swap"""
        if not rental.power_bank:
            raise ServiceException(
                detail="No powerbank associated with this rental",
                code="no_powerbank"
            )
        
        # Check powerbank is back at the original station
        if rental.power_bank.current_station_id != rental.station_id:
            raise ServiceException(
                detail="Please return the powerbank to the same station before swapping.",
                code="powerbank_not_at_station"
            )
        
        if rental.power_bank.current_slot is None:
            raise ServiceException(
                detail="Please insert the powerbank into a slot before swapping.",
                code="powerbank_not_in_slot"
            )
    
    def _check_swap_limit(self, user, station: Station) -> None:
        """Check daily swap limit for user at station"""
        today = timezone.now().date()
        
        today_swaps = RentalSwap.objects.filter(
            rental__user=user,
            original_station=station,
            swapped_at__date=today
        ).count()
        
        available_count = PowerBank.objects.filter(
            current_station=station,
            status='AVAILABLE',
            battery_level__gte=20,
            current_slot__isnull=False
        ).count()
        
        if available_count == 0:
            raise ServiceException(
                detail="No available powerbanks at this station for swap",
                code="no_powerbanks_available"
            )
        
        if today_swaps >= available_count:
            raise ServiceException(
                detail=f"Daily swap limit ({available_count}) reached for this station",
                code="swap_limit_exceeded"
            )
    
    def _get_swap_powerbank(
        self, 
        station: Station, 
        exclude_powerbank_id: str
    ) -> tuple:
        """Get an available powerbank for swap, excluding current one"""
        powerbank = PowerBank.objects.select_for_update().filter(
            current_station=station,
            status='AVAILABLE',
            battery_level__gte=20,
            current_slot__isnull=False
        ).exclude(
            id=exclude_powerbank_id
        ).order_by('-battery_level').first()
        
        if not powerbank:
            raise ServiceException(
                detail="No other powerbanks available for swap",
                code="no_swap_powerbank_available"
            )
        
        return powerbank, powerbank.current_slot
    
    def _send_swap_notification(self, user, rental, old_pb, new_pb) -> None:
        """Send swap confirmation notification"""
        from api.user.notifications.services import notify
        notify(
            user,
            'rental_swapped',
            async_send=True,
            rental_code=rental.rental_code,
            old_powerbank=old_pb.serial_number,
            new_powerbank=new_pb.serial_number,
            new_battery_level=new_pb.battery_level
        )
```

### 6.2 Update RentalService

Add mixin to `api/user/rentals/services/rental/__init__.py`:

```python
from .swap import RentalSwapMixin

class RentalService(
    RentalNotificationMixin,
    RentalStartMixin,
    RentalCancelMixin,
    RentalExtendMixin,
    RentalReturnMixin,
    RentalSwapMixin,  # NEW
    RentalQueryMixin,
    CRUDService
):
```

---

## 7. API View

### 7.1 New View

**File:** `api/user/rentals/views/core_views.py` (add to existing)

```python
@extend_schema(
    tags=["Rentals"],
    summary="Swap Powerbank",
    description="Exchange current powerbank for a different one within swap window"
)
class RentalSwapView(GenericAPIView, BaseAPIView):
    serializer_class = RentalSwapSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        request=RentalSwapSerializer,
        responses={200: BaseResponseSerializer}
    )
    @log_api_call()
    def post(self, request: Request, rental_id: str) -> Response:
        """Swap powerbank for rental"""
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service = RentalService()
            rental = service.swap_powerbank(
                rental_id=rental_id,
                user=request.user,
                reason=serializer.validated_data.get('reason', 'OTHER'),
                description=serializer.validated_data.get('description', '')
            )
            
            return {
                'rental_id': str(rental.id),
                'rental_code': rental.rental_code,
                'old_powerbank': rental.rental_metadata.get('swaps', [{}])[-1].get('old_powerbank_sn'),
                'new_powerbank': rental.power_bank.serial_number,
                'new_battery_level': rental.power_bank.battery_level,
                'swap_count_today': len(rental.rental_metadata.get('swaps', []))
            }
        
        return self.handle_service_operation(
            operation,
            success_message="Powerbank swapped successfully",
            error_message="Failed to swap powerbank"
        )
```

### 7.2 Serializer

```python
# api/user/rentals/serializers/action_serializers.py

class RentalSwapSerializer(serializers.Serializer):
    """Serializer for swap request"""
    reason = serializers.ChoiceField(
        choices=['LOW_BATTERY', 'DEFECTIVE', 'WRONG_CABLE', 'OTHER'],
        default='OTHER',
        required=False
    )
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
```

---

## 8. Notification Template

### 8.1 New Template

| Slug | Title | Message |
|------|-------|---------|
| `rental_swapped` | Powerbank Swapped | Your powerbank for rental {{rental_code}} has been swapped. Old: {{old_powerbank}}, New: {{new_powerbank}} ({{new_battery_level}}% battery). |

---

## 9. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `api/user/rentals/models/rental.py` | Add | RentalSwap model |
| `api/user/rentals/services/rental/swap.py` | Create | RentalSwapMixin |
| `api/user/rentals/services/rental/__init__.py` | Modify | Add RentalSwapMixin |
| `api/user/rentals/views/core_views.py` | Modify | Add RentalSwapView |
| `api/user/rentals/serializers/action_serializers.py` | Modify | Add RentalSwapSerializer |
| `api/user/rentals/urls.py` | Modify | Add swap route |
| `api/user/system/fixtures/app_config.json` | Modify | Add SWAPPING_MAX_TIME |
| `api/user/notifications/fixtures/templates.json` | Modify | Add rental_swapped template |

---

## 10. Migration Required

```python
# Migration for RentalSwap model
from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('rentals', 'XXXX_previous'),
        ('stations', 'XXXX_previous'),
    ]

    operations = [
        migrations.CreateModel(
            name='RentalSwap',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('old_battery_level', models.IntegerField()),
                ('new_battery_level', models.IntegerField()),
                ('swap_reason', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True, null=True)),
                ('swapped_at', models.DateTimeField(auto_now_add=True)),
                # Foreign keys...
            ],
            options={
                'db_table': 'rental_swaps',
            },
        ),
    ]
```

---

## Approval Required

Please confirm:
- [ ] Swap window of 5 minutes is correct
- [ ] Daily limit = available powerbanks at station
- [ ] User must return current PB to SAME station before swap
- [ ] Swap reasons list is complete
- [ ] No payment involved in swap (just exchange)

---
