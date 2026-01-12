# Feature: Partner IoT History

**App**: `api/vendor/`  
**Priority**: Phase 1

---

## Tables

### 5.1 PartnerIotHistory

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `partner` | ForeignKey(Partner) | Partner who performed action | NOT NULL, on_delete=CASCADE |
| `station` | ForeignKey(Station) | Target station | NOT NULL, on_delete=CASCADE |
| `action_type` | CharField(20) | Type of IoT action | NOT NULL |
| `performed_from` | CharField(20) | Where action was performed | NOT NULL |
| `powerbank_sn` | CharField(100) | Powerbank SN (for EJECT) | NULL |
| `rental` | ForeignKey(Rental) | Linked rental (for EJECT) | NULL, on_delete=SET_NULL |
| `is_successful` | BooleanField | Whether action succeeded | NOT NULL |
| `is_free_ejection` | BooleanField | Was this a free daily ejection? | NOT NULL, default=False |
| `error_message` | TextField | Error if failed | NULL |
| `request_payload` | JSONField | Request sent to device | default={} |
| `response_data` | JSONField | Response from device | default={} |
| `ip_address` | GenericIPAddressField | Client IP | NULL |
| `user_agent` | TextField | Client user agent | NULL |

**Action Type Choices**:
```python
ACTION_TYPE_CHOICES = [
    ('EJECT', 'Eject Powerbank'),
    ('REBOOT', 'Reboot Device'),
    ('CHECK', 'Check Status'),
    ('WIFI_SETTINGS', 'WiFi Settings'),
    ('VOLUME', 'Volume Control'),
    ('MODE', 'Network Mode'),
]
```

**Performed From Choices**:
```python
PERFORMED_FROM_CHOICES = [
    ('MOBILE_APP', 'Mobile App'),
    ('DASHBOARD', 'Partner Dashboard'),
    ('ADMIN_PANEL', 'Admin Panel'),
]
```

---

## Business Logic Notes

### Vendor Ejection Rules

1. **Free Ejection Perk**:
   - Every Vendor (Revenue or Non-Revenue) gets 1 free ejection per day
   - Tracked via `is_free_ejection = True`
   - Check: `PartnerIotHistory.objects.filter(partner=vendor.partner, action_type='EJECT', is_free_ejection=True, created_at__date=today).exists()`

2. **Vendor Control Rights**:
   - Can perform: REBOOT, CHECK, WIFI_SETTINGS
   - Cannot perform: EJECT (except 1 free per day via rental flow)

### Franchise Ejection Rules

1. **Unlimited Ejections**:
   - Franchise has unlimited ejections from Dashboard
   - `is_free_ejection = False` (not applicable)

2. **Full Control Rights**:
   - Can perform: EJECT, REBOOT, CHECK, WIFI_SETTINGS, VOLUME, MODE

### Rental Start Integration

```python
# In POST /api/rentals/start
def start_rental(user, station_sn, package_id, powerbank_sn):
    # Check if user is a vendor
    partner = get_user_partner(user)
    
    if partner and partner.partner_type == 'VENDOR':
        vendor = partner.vendor
        today = timezone.now().date()
        
        # Check free ejection quota
        free_ejection_used = PartnerIotHistory.objects.filter(
            partner=partner,
            action_type='EJECT',
            is_free_ejection=True,
            created_at__date=today
        ).exists()
        
        if free_ejection_used:
            raise ServiceException("Daily free ejection already used")
        
        # Proceed with rental, mark as free ejection
        # ... create rental ...
        
        # Log IoT history
        PartnerIotHistory.objects.create(
            partner=partner,
            station=station,
            action_type='EJECT',
            performed_from='MOBILE_APP',
            powerbank_sn=powerbank_sn,
            rental=rental,
            is_successful=True,
            is_free_ejection=True
        )
```

---

## Indexes

```python
class Meta:
    db_table = 'partner_iot_history'
    indexes = [
        models.Index(fields=['partner', 'action_type', 'created_at']),
        models.Index(fields=['station', 'action_type']),
        models.Index(fields=['partner', 'is_free_ejection', 'created_at']),
    ]
```

---

## Related Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/partner/iot/history` | Get partner's IoT action history |
| POST | `/api/partner/iot/reboot` | Reboot station (Vendor/Franchise) |
| POST | `/api/partner/iot/check` | Check station status |
| POST | `/api/partner/iot/wifi` | Update WiFi settings |
| POST | `/api/partner/iot/eject` | Eject powerbank (Franchise only) |
