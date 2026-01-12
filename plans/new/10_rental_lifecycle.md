# Feature: Rental Lifecycle Enhancements

**App**: `api/user/rentals/`  
**Priority**: Phase 2

---

## Tables

### 10.1 Rental Model Updates

| Field | Type | Description | Action |
|-------|------|-------------|--------|
| `return_battery_level` | IntegerField | Battery % at return | ADD, NULL |
| `start_battery_level` | IntegerField | Battery % at start | ADD, NULL |
| `is_under_5_min` | BooleanField | Returned within 5 min | ADD, default=False |
| `hardware_issue_reported` | BooleanField | Issue flagged | ADD, default=False |

---

### 10.2 Rental Start API Update

**Endpoint**: `POST /api/rentals/start`

**Current Request**:
```json
{ "station_sn": "...", "package_id": "..." }
```

**Updated Request**:
```json
{ "station_sn": "...", "package_id": "...", "powerbank_sn": "..." }
```

**Logic Updates**:
1. Accept `powerbank_sn` in request (optional - device may auto-select)
2. Check if user is Vendor → apply free ejection rule
3. Check for station package discount → apply if valid
4. Track start_battery_level from device response

---

### 10.2 BatteryCycleLog

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `powerbank` | ForeignKey(PowerBank) | Powerbank | NOT NULL, on_delete=CASCADE |
| `rental` | ForeignKey(Rental) | Rental | NOT NULL, on_delete=CASCADE |
| `start_level` | IntegerField | Battery at start | NOT NULL |
| `end_level` | IntegerField | Battery at return | NOT NULL |
| `discharge_percent` | DecimalField(5,2) | % discharged | NOT NULL |
| `cycle_contribution` | DecimalField(5,4) | Cycle count (0.XX) | NOT NULL |


---

### 10.3 PowerBank Model Updates

| Field | Type | Description | Action |
|-------|------|-------------|--------|
| `total_cycles` | DecimalField(8,4) | Cumulative cycles | ADD, default=0 |
| `total_rentals` | IntegerField | Total rental count | ADD, default=0 |

---

## Business Logic Notes

### 5-Minute Rule

```python
def process_return(rental, return_battery_level):
    rental.ended_at = timezone.now()
    rental.return_battery_level = return_battery_level
    
    # Check 5-minute rule
    duration = rental.ended_at - rental.started_at
    if duration.total_seconds() < 300:  # 5 minutes
        rental.is_under_5_min = True
        rental.hardware_issue_reported = True
        # Trigger notification to admin
        notify_admin_potential_issue(rental)
    
    rental.save()
```

### Battery Cycle Tracking

```python
def log_battery_cycle(rental, powerbank, start_level, end_level):
    """
    1 Cycle = 100% to 0% discharge
    Example: 100% → 30% = 0.70 cycles
    """
    discharge_percent = max(0, start_level - end_level)
    cycle_contribution = Decimal(discharge_percent) / Decimal(100)
    
    BatteryCycleLog.objects.create(
        powerbank=powerbank,
        rental=rental,
        start_level=start_level,
        end_level=end_level,
        discharge_percent=discharge_percent,
        cycle_contribution=cycle_contribution
    )
    
    # Update powerbank cumulative cycles
    powerbank.total_cycles += cycle_contribution
    powerbank.total_rentals += 1
    powerbank.save(update_fields=['total_cycles', 'total_rentals'])
```

---

---

### 10.4 Swapping Rate Limit

**Requirement**: User can swap only up to total available powerbank count of that station per day.

```python
def check_swap_limit(user, station):
    """Check if user has exceeded daily swap limit for this station"""
    from django.utils import timezone
    
    today = timezone.now().date()
    today_swaps = Rental.objects.filter(
        user=user,
        station=station,
        created_at__date=today
    ).count()
    
    # Get available slots count
    available_count = station.slots.filter(
        status='AVAILABLE',
        power_bank__isnull=False
    ).count()
    
    if today_swaps >= available_count:
        raise ValidationError(f"Daily swap limit ({available_count}) reached for this station")
```

---

## Indexes

```python
# BatteryCycleLog
class Meta:
    db_table = 'battery_cycle_logs'
    indexes = [
        models.Index(fields=['powerbank', 'created_at']),
        models.Index(fields=['rental']),
    ]
```
