# Feature: IoT Sync Logging & Station Monitoring

**App**: `api/internal/`  
**Priority**: Phase 2

---

## Tables

### 11.1 IotSyncLog

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `station` | ForeignKey(Station) | Station | NOT NULL, on_delete=CASCADE |
| `device_uuid` | CharField(100) | Device IMEI | NOT NULL |
| `sync_type` | CharField(20) | Type of sync | NOT NULL |
| `direction` | CharField(10) | INBOUND or OUTBOUND | NOT NULL |
| `request_payload` | JSONField | Request data | default={} |
| `response_payload` | JSONField | Response data | default={} |
| `status` | CharField(20) | Sync status | NOT NULL |
| `error_message` | TextField | Error if failed | NULL |
| `duration_ms` | IntegerField | Request duration | NULL |

**Sync Type Choices**:
```python
SYNC_TYPE_CHOICES = [
    ('STATUS', 'Status Update'),
    ('FULL', 'Full Sync'),
    ('RETURNED', 'Return Event'),
    ('ADS', 'Advertisement Sync'),
    ('COMMAND', 'Device Command'),
]
```

**Direction Choices**:
```python
DIRECTION_CHOICES = [
    ('INBOUND', 'Inbound'),   # Device → Django
    ('OUTBOUND', 'Outbound'), # Django → Device
]
```

**Status Choices**:
```python
STATUS_CHOICES = [
    ('SUCCESS', 'Success'),
    ('FAILED', 'Failed'),
    ('TIMEOUT', 'Timeout'),
]
```

---

### 11.2 StationStatusHistory (Station Monitoring)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `station` | ForeignKey(Station) | Station | NOT NULL, on_delete=CASCADE |
| `status` | CharField(20) | ONLINE or OFFLINE | NOT NULL |
| `previous_status` | CharField(20) | Previous status | NULL |
| `changed_at` | DateTimeField | When status changed | NOT NULL |
| `duration_seconds` | IntegerField | Duration in previous status | NULL |
| `triggered_by` | CharField(20) | What triggered change | NOT NULL |

**Status Choices**:
```python
STATUS_CHOICES = [
    ('ONLINE', 'Online'),
    ('OFFLINE', 'Offline'),
]
```

**Triggered By Choices**:
```python
TRIGGERED_BY_CHOICES = [
    ('SYNC', 'IoT Sync'),
    ('HEARTBEAT', 'Heartbeat'),
    ('MANUAL', 'Manual Check'),
    ('TIMEOUT', 'Connection Timeout'),
]
```

---

## Business Logic Notes

### Logging Sync Operations

```python
def log_iot_sync(station, device_uuid, sync_type, direction, request_payload, response_payload, status, error=None, duration_ms=None):
    IotSyncLog.objects.create(
        station=station,
        device_uuid=device_uuid,
        sync_type=sync_type,
        direction=direction,
        request_payload=request_payload,
        response_payload=response_payload,
        status=status,
        error_message=error,
        duration_ms=duration_ms
    )
```

### Station Status Tracking

```python
def update_station_status(station, new_status, triggered_by):
    """Track station online/offline status changes"""
    from django.utils import timezone
    
    now = timezone.now()
    previous_status = station.status  # Assuming Station has status field
    
    if previous_status != new_status:
        # Calculate duration in previous status
        last_change = StationStatusHistory.objects.filter(
            station=station
        ).order_by('-changed_at').first()
        
        duration = None
        if last_change:
            duration = int((now - last_change.changed_at).total_seconds())
        
        StationStatusHistory.objects.create(
            station=station,
            status=new_status,
            previous_status=previous_status,
            changed_at=now,
            duration_seconds=duration,
            triggered_by=triggered_by
        )
        
        # Update station status
        station.status = new_status
        station.save(update_fields=['status'])
```

---

## Indexes

```python
# IotSyncLog
class Meta:
    db_table = 'iot_sync_logs'
    indexes = [
        models.Index(fields=['station', 'sync_type', 'created_at']),
        models.Index(fields=['device_uuid', 'created_at']),
        models.Index(fields=['status', 'created_at']),
    ]

# StationStatusHistory
class Meta:
    db_table = 'station_status_history'
    indexes = [
        models.Index(fields=['station', 'changed_at']),
        models.Index(fields=['status', 'changed_at']),
    ]
```
