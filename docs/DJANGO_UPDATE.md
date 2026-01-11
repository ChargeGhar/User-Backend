# Django Server Update Plan - Device Integration

## Overview

Integrate `chargeghar_client` into rental flow with sync popup + async verification fallback.

---

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| `chargeghar_client` | ✅ Exists | `libs/chargeghar_client/` |
| Rental Service | ✅ Exists | `api/user/rentals/services/` |
| Station Service | ✅ Exists | `api/user/stations/services/` |
| Device popup in rental | ❌ Missing | Not integrated |
| Celery device tasks | ❌ Missing | No device polling |

---

## Changes Required

### 1. Update chargeghar_client - Add popup_sn and logs

**File:** `libs/chargeghar_client/types.py`

Add new types:
```python
@dataclass
class PopupSnResult:
    """Response from popup_sn endpoint"""
    slot: int
    powerbank_sn: str
    status: int
    success: bool
    
    @classmethod
    def from_dict(cls, data: dict) -> "PopupSnResult":
        return cls(
            slot=data.get("slot", 0),
            powerbank_sn=data.get("powerbankSN", ""),
            status=data.get("status", 0),
            success=data.get("success", False)
        )


@dataclass
class TransactionLog:
    """Device transaction log entry"""
    message_id: str
    device_name: str
    cmd: str
    raw: str
    parsed: dict
    timestamp: int
    
    @classmethod
    def from_dict(cls, data: dict) -> "TransactionLog":
        return cls(
            message_id=data.get("messageId", ""),
            device_name=data.get("deviceName", ""),
            cmd=data.get("cmd", ""),
            raw=data.get("raw", ""),
            parsed=data.get("parsed", {}),
            timestamp=data.get("timestamp", 0)
        )
```

---

**File:** `libs/chargeghar_client/device.py`

Add methods:
```python
from .types import PopupSnResult, TransactionLog

# In DeviceClient class:

def popup_sn(self, device_name: str, powerbank_sn: str) -> HttpResult:
    """
    Popup specific powerbank by SN (SYNC - 15s timeout on server)
    
    Args:
        device_name: Station serial number
        powerbank_sn: Powerbank SN to eject
    
    Returns:
        HttpResult with popup result
    """
    return self._get(
        "/popup_sn",
        params={"rentboxSN": device_name, "singleSN": powerbank_sn},
        timeout=20  # 15s server + 5s network buffer
    )

def popup_sn_typed(self, device_name: str, powerbank_sn: str) -> Optional[PopupSnResult]:
    """Popup specific powerbank, returns typed result or None on failure"""
    result = self.popup_sn(device_name, powerbank_sn)
    if result.code == 200 and result.data:
        return PopupSnResult.from_dict(result.data)
    return None

def get_logs(self, device_name: str, limit: int = 20, cmd: str = None) -> HttpResult:
    """Get device transaction logs"""
    params = {"limit": limit}
    if cmd:
        params["cmd"] = cmd
    return self._get(f"/api/device/{device_name}/logs", params=params)

def get_logs_typed(self, device_name: str, limit: int = 20, cmd: str = None) -> List[TransactionLog]:
    """Get device logs as typed list"""
    result = self.get_logs(device_name, limit, cmd)
    if result.code == 200 and result.data:
        return [TransactionLog.from_dict(log) for log in result.data]
    return []

def get_transaction(self, device_name: str, message_id: str) -> HttpResult:
    """Get specific transaction by message ID"""
    return self._get(f"/api/device/{device_name}/logs/{message_id}")

def get_transaction_typed(self, device_name: str, message_id: str) -> Optional[TransactionLog]:
    """Get specific transaction as typed object"""
    result = self.get_transaction(device_name, message_id)
    if result.code == 200 and result.data:
        return TransactionLog.from_dict(result.data)
    return None
```

---

**File:** `libs/chargeghar_client/__init__.py`

Update exports:
```python
from .types import (
    HttpResult,
    LoginResponse,
    AdminUser,
    Powerbank,
    DeviceCreateResult,
    AdminStatistics,
    TokenInfo,
    PopupSnResult,      # NEW
    TransactionLog,     # NEW
)
```

---

### 2. Create DeviceAPIService

**File:** `api/user/stations/services/device_api_service.py` (NEW)

```python
"""
Device API Service - Wrapper for chargeghar_client with business logic
"""
import logging
from typing import Optional, Tuple

from django.conf import settings

from libs.chargeghar_client import get_client, PopupSnResult, TransactionLog

logger = logging.getLogger(__name__)


class DeviceAPIService:
    """
    Service for device communication via Spring API
    """
    
    def __init__(self):
        self.client = get_client()
    
    def popup_random(
        self, 
        station_sn: str, 
        min_power: int = 20
    ) -> Tuple[bool, Optional[str], str]:
        """
        Popup random available powerbank
        
        Returns:
            Tuple[success, powerbank_sn, message]
        """
        try:
            result = self.client.device.popup_random_typed(station_sn, min_power)
            if result:
                logger.info(f"Popup random success: station={station_sn}, powerbank={result}")
                return True, result, "Powerbank ejected successfully"
            else:
                logger.warning(f"Popup random failed: station={station_sn}")
                return False, None, "No available powerbank or device timeout"
        except Exception as e:
            logger.error(f"Popup random error: station={station_sn}, error={e}")
            return False, None, str(e)
    
    def popup_specific(
        self, 
        station_sn: str, 
        powerbank_sn: str
    ) -> Tuple[bool, Optional[PopupSnResult], str]:
        """
        Popup specific powerbank by SN
        
        Returns:
            Tuple[success, result, message]
        """
        try:
            result = self.client.device.popup_sn_typed(station_sn, powerbank_sn)
            if result and result.success:
                logger.info(
                    f"Popup specific success: station={station_sn}, "
                    f"powerbank={powerbank_sn}, slot={result.slot}"
                )
                return True, result, "Powerbank ejected successfully"
            else:
                logger.warning(
                    f"Popup specific failed: station={station_sn}, powerbank={powerbank_sn}"
                )
                return False, result, "Popup failed - device timeout or powerbank not found"
        except Exception as e:
            logger.error(
                f"Popup specific error: station={station_sn}, "
                f"powerbank={powerbank_sn}, error={e}"
            )
            return False, None, str(e)
    
    def check_station(self, station_sn: str) -> Tuple[bool, list, str]:
        """
        Check station slot status
        
        Returns:
            Tuple[success, powerbanks, message]
        """
        try:
            powerbanks = self.client.device.check_typed(station_sn)
            return True, powerbanks, "OK"
        except Exception as e:
            logger.error(f"Check station error: station={station_sn}, error={e}")
            return False, [], str(e)
    
    def verify_transaction(
        self, 
        station_sn: str, 
        message_id: str
    ) -> Optional[TransactionLog]:
        """
        Verify if a transaction completed (for timeout recovery)
        """
        try:
            return self.client.device.get_transaction_typed(station_sn, message_id)
        except Exception as e:
            logger.error(f"Verify transaction error: {e}")
            return None
    
    def get_recent_popups(
        self, 
        station_sn: str, 
        limit: int = 10
    ) -> list:
        """
        Get recent popup transactions for a station
        """
        try:
            return self.client.device.get_logs_typed(station_sn, limit, cmd="0x31")
        except Exception as e:
            logger.error(f"Get recent popups error: {e}")
            return []
```

---

### 3. Create Celery Task for Verification

**File:** `api/user/stations/tasks.py`

Add task:
```python
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    queue="stations"
)
def verify_popup_completion(self, rental_id: int, station_sn: str, expected_powerbank_sn: str):
    """
    Verify popup completed after sync timeout
    
    Called when sync popup times out but rental was created.
    Checks device logs for successful popup within last 2 minutes.
    
    Args:
        rental_id: Rental ID to update
        station_sn: Station serial number
        expected_powerbank_sn: Expected powerbank SN
    """
    from api.user.rentals.models import Rental
    from api.user.stations.services.device_api_service import DeviceAPIService
    
    try:
        rental = Rental.objects.get(id=rental_id)
        
        # Skip if already completed or cancelled
        if rental.status not in ['PENDING', 'PENDING_POPUP']:
            logger.info(f"Rental {rental_id} already processed, status={rental.status}")
            return
        
        device_service = DeviceAPIService()
        recent_popups = device_service.get_recent_popups(station_sn, limit=20)
        
        # Check if our powerbank was popped in last 2 minutes
        cutoff = timezone.now().timestamp() - 120
        
        for popup in recent_popups:
            if popup.timestamp > cutoff:
                parsed = popup.parsed
                if parsed.get("powerbankSN") == expected_powerbank_sn and parsed.get("status") == 1:
                    # Found successful popup!
                    logger.info(
                        f"Verified popup for rental {rental_id}: "
                        f"powerbank={expected_powerbank_sn}"
                    )
                    rental.status = 'ACTIVE'
                    rental.popup_verified_at = timezone.now()
                    rental.save(update_fields=['status', 'popup_verified_at'])
                    return
        
        # Not found - retry or mark failed
        if self.request.retries < self.max_retries:
            logger.warning(f"Popup not verified for rental {rental_id}, retrying...")
            raise self.retry()
        else:
            logger.error(f"Popup verification failed for rental {rental_id}")
            rental.status = 'POPUP_FAILED'
            rental.save(update_fields=['status'])
            # TODO: Trigger refund if prepaid
            
    except Rental.DoesNotExist:
        logger.error(f"Rental {rental_id} not found")
    except Exception as e:
        logger.error(f"Verify popup error: rental={rental_id}, error={e}")
        raise self.retry(exc=e)
```

---

### 4. Update Rental Service

**File:** `api/user/rentals/services/rental_service.py`

Add popup integration:
```python
from api.user.stations.services.device_api_service import DeviceAPIService
from api.user.stations.tasks import verify_popup_completion


class RentalService:
    
    def __init__(self):
        self.device_service = DeviceAPIService()
    
    def start_rental(self, user, station, package, powerbank=None):
        """
        Start rental with device popup
        
        Args:
            user: User starting rental
            station: Station object
            package: RentalPackage
            powerbank: Optional specific powerbank (if user selected from app)
        """
        # ... existing validation code ...
        
        # Create rental in PENDING status
        rental = Rental.objects.create(
            user=user,
            station=station,
            package=package,
            status='PENDING_POPUP',
            # ... other fields ...
        )
        
        try:
            if powerbank:
                # User selected specific powerbank
                success, result, message = self.device_service.popup_specific(
                    station.serial_number,
                    powerbank.serial_number
                )
            else:
                # Random popup
                success, powerbank_sn, message = self.device_service.popup_random(
                    station.serial_number,
                    min_power=package.min_power or 20
                )
                if success:
                    result = type('obj', (object,), {'powerbank_sn': powerbank_sn})()
            
            if success:
                # Popup successful
                rental.status = 'ACTIVE'
                rental.powerbank_sn = result.powerbank_sn if hasattr(result, 'powerbank_sn') else powerbank_sn
                rental.started_at = timezone.now()
                rental.save()
                return rental, None
            else:
                # Popup failed - cancel rental
                rental.status = 'CANCELLED'
                rental.cancelled_reason = message
                rental.save()
                return None, message
                
        except TimeoutError:
            # Sync timed out - schedule verification task
            rental.status = 'PENDING_POPUP'
            rental.save()
            
            verify_popup_completion.apply_async(
                args=[
                    rental.id,
                    station.serial_number,
                    powerbank.serial_number if powerbank else None
                ],
                countdown=10  # Wait 10 seconds then verify
            )
            
            return rental, "Processing - please wait"
```

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    RENTAL FLOW WITH POPUP                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User App                Django                Spring API        │
│     │                      │                      │              │
│     │  Select Station      │                      │              │
│     │─────────────────────>│                      │              │
│     │                      │                      │              │
│     │  [Option A: Random]  │                      │              │
│     │  Start Rental        │                      │              │
│     │─────────────────────>│ popup_random(sn)    │              │
│     │                      │─────────────────────>│              │
│     │                      │     (15s timeout)    │──┐           │
│     │                      │                      │  │ MQTT      │
│     │                      │<─────────────────────│<─┘           │
│     │      Success         │   {powerbank_sn}    │              │
│     │<─────────────────────│                      │              │
│     │                      │                      │              │
│     │  [Option B: Specific]│                      │              │
│     │  Select Powerbank    │                      │              │
│     │─────────────────────>│ popup_sn(sn, pb_sn) │              │
│     │                      │─────────────────────>│              │
│     │                      │     (15s timeout)    │──┐           │
│     │                      │                      │  │ MQTT      │
│     │                      │<─────────────────────│<─┘           │
│     │      Success         │  {slot, status}     │              │
│     │<─────────────────────│                      │              │
│     │                      │                      │              │
│     │  [Timeout Case]      │                      │              │
│     │─────────────────────>│                      │              │
│     │   "Processing..."    │                      │              │
│     │<─────────────────────│                      │              │
│     │                      │                      │              │
│     │                      │  Celery Task (10s)  │              │
│     │                      │  verify_popup()     │              │
│     │                      │─────────────────────>│              │
│     │                      │  get_logs(sn, 0x31) │              │
│     │                      │<─────────────────────│              │
│     │                      │  [Found in logs]    │              │
│     │                      │  Mark ACTIVE        │              │
│     │    Push Notification │                      │              │
│     │<─────────────────────│                      │              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Celery Task Configuration

**File:** `tasks/app.py`

Add to beat schedule:
```python
# No scheduled task needed - verify_popup_completion is triggered on-demand
# But add task routing:

app.conf.task_routes = {
    # ... existing routes ...
    "api.user.stations.tasks.verify_popup_completion": {"queue": "stations"},
}
```

---

## Settings Update

**File:** `api/config/device_api.py` or `.env`

Ensure configured:
```python
DEVICE_API = {
    'BASE_URL': env('DEVICE_API_BASE_URL', default='https://api.chargeghar.com'),
    'CONNECT_TIMEOUT': 10,
    'READ_TIMEOUT': 25,  # 15s server timeout + 10s buffer
    'MAX_RETRIES': 1,    # Don't retry on timeout - let Celery verify
    'AUTH_ENABLED': True,
    'AUTH_USERNAME': env('DEVICE_API_USERNAME'),
    'AUTH_PASSWORD': env('DEVICE_API_PASSWORD'),
}
```

---

## Testing

```python
# Test popup_sn
from libs.chargeghar_client import get_client
client = get_client()

# Random popup
result = client.device.popup_random_typed('864601069946994', min_power=30)
print(result)  # "40818048" or None

# Specific popup
result = client.device.popup_sn_typed('864601069946994', '40818048')
print(result)  # PopupSnResult(slot=1, powerbank_sn='40818048', status=1, success=True)

# Get logs
logs = client.device.get_logs_typed('864601069946994', limit=10, cmd='0x31')
for log in logs:
    print(f"{log.timestamp}: {log.parsed}")
```

---

## Deployment Checklist

1. ✅ Update `libs/chargeghar_client/types.py` - Add new types (PopupSnResult, TransactionLog)
2. ✅ Update `libs/chargeghar_client/device.py` - Add popup_sn and logs methods
3. ✅ Update `libs/chargeghar_client/__init__.py` - Export new types
4. ✅ Create `api/user/stations/services/device_api_service.py`
5. ✅ Update `api/user/stations/tasks.py` - Add verification task
6. ✅ Update rental service with popup integration (`api/user/rentals/services/rental/start.py`)
7. ✅ Add `PENDING_POPUP` status to Rental model
8. ✅ Migration created: `api/user/rentals/migrations/0004_add_pending_popup_status.py`
9. ⏳ Deploy and test
