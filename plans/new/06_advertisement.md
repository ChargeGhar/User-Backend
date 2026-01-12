# Feature: Advertisement System

**App**: `api/user/advertisements/`  
**Priority**: Phase 2

---

## Tables

### 6.1 AdRequest

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `user` | ForeignKey(User) | User who submitted | NOT NULL, on_delete=CASCADE |
| `title` | CharField(255) | Ad title | NOT NULL |
| `description` | TextField | Ad description | NULL |
| `duration_days` | IntegerField | Requested duration | NOT NULL |
| `budget` | DecimalField(12,2) | User's proposed budget | NULL |
| `status` | CharField(20) | Request status | NOT NULL, default='DRAFT' |
| `submitted_at` | DateTimeField | When submitted | NULL |
| `reviewed_by` | ForeignKey(User) | Admin who reviewed | NULL, on_delete=SET_NULL |
| `reviewed_at` | DateTimeField | When reviewed | NULL |
| `admin_price` | DecimalField(12,2) | Price set by admin | NULL |
| `admin_notes` | TextField | Admin notes | NULL |
| `rejection_reason` | TextField | If rejected | NULL |
| `approved_by` | ForeignKey(User) | Admin who approved | NULL, on_delete=SET_NULL |
| `approved_at` | DateTimeField | When approved | NULL |
| `payment_intent` | ForeignKey(PaymentIntent) | Payment intent | NULL, on_delete=SET_NULL |
| `transaction` | ForeignKey(Transaction) | Payment transaction | NULL, on_delete=SET_NULL |
| `paid_at` | DateTimeField | When paid | NULL |
| `start_date` | DateField | When ad starts running | NULL |
| `end_date` | DateField | When ad ends | NULL |
| `completed_at` | DateTimeField | When ad completed | NULL |

**Status Choices**:
```python
STATUS_CHOICES = [
    ('SUBMITTED', 'Submitted'),            # Awaiting admin review
    ('UNDER_REVIEW', 'Under Review'),      # Admin reviewing
    ('APPROVED', 'Approved'),              # Approved, price set
    ('REJECTED', 'Rejected'),              # Admin rejected
    ('PENDING_PAYMENT', 'Pending Payment'), # Awaiting user payment
    ('PAID', 'Paid'),                      # Payment received
    ('SCHEDULED', 'Scheduled'),            # Waiting for start_date
    ('RUNNING', 'Running'),                # Currently active
    ('PAUSED', 'Paused'),                  # Temporarily paused
    ('COMPLETED', 'Completed'),            # Duration ended
    ('CANCELLED', 'Cancelled'),            # User/Admin cancelled
]
```

---

### 6.2 AdContent

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `ad_request` | ForeignKey(AdRequest) | Parent ad request | NOT NULL, on_delete=CASCADE |
| `content_type` | CharField(10) | IMAGE or VIDEO | NOT NULL |
| `media_upload` | ForeignKey(MediaUpload) | Uploaded media | NOT NULL, on_delete=PROTECT |
| `url_small` | URLField | URL for <20 slot devices | NULL |
| `url_large` | URLField | URL for >20 slot devices | NULL |
| `duration_seconds` | IntegerField | Play time for images | NOT NULL, default=5 |
| `display_order` | IntegerField | Order in rotation | NOT NULL, default=0 |
| `is_active` | BooleanField | Whether to display | NOT NULL, default=True |
| `metadata` | JSONField | Additional data | default={} |

**Content Type Choices**:
```python
CONTENT_TYPE_CHOICES = [
    ('IMAGE', 'Image'),   # jpg, png
    ('VIDEO', 'Video'),   # mp4
]
```

---

### 6.3 AdStation

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `ad_request` | ForeignKey(AdRequest) | Ad request | NOT NULL, on_delete=CASCADE |
| `station` | ForeignKey(Station) | Target station | NOT NULL, on_delete=CASCADE |
| `is_active` | BooleanField | Whether active for this station | NOT NULL, default=True |

**Constraint**: `unique_together = ['ad_request', 'station']`

---

### 6.4 AdDistribution (IoT Sync Tracking)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `ad_content` | ForeignKey(AdContent) | Ad content | NOT NULL, on_delete=CASCADE |
| `station` | ForeignKey(Station) | Station | NOT NULL, on_delete=CASCADE |
| `device_uuid` | CharField(100) | Device IMEI | NOT NULL |
| `distributed_at` | DateTimeField | When sent to device | NULL |
| `last_synced_at` | DateTimeField | Last sync time | NULL |
| `play_count` | IntegerField | Times played | NOT NULL, default=0 |
| `last_played_at` | DateTimeField | Last play time | NULL |
| `sync_status` | CharField(20) | Sync status | NOT NULL, default='PENDING' |
| `sync_error` | TextField | Error message | NULL |

**Sync Status Choices**:
```python
SYNC_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('SYNCED', 'Synced'),
    ('FAILED', 'Failed'),
]
```

---

## Business Logic Notes

### Workflow

1. **User Submits** (`POST /api/ads/request`):
   - Creates AdRequest (status=DRAFT)
   - Uploads media → creates AdContent
   - Selects stations → creates AdStation records
   - Submits → status=SUBMITTED

2. **Admin Reviews** (Admin Panel):
   - Reviews content
   - Sets `admin_price`
   - Approves → status=APPROVED → status=PENDING_PAYMENT
   - OR Rejects → status=REJECTED

3. **User Pays** (`POST /api/ads/{id}/pay`):
   - Creates PaymentIntent
   - On success → status=PAID
   - Sets start_date, end_date

4. **Ad Runs**:
   - Scheduler checks start_date → status=RUNNING
   - Creates AdDistribution records
   - Syncs to Java API

5. **Ad Completes**:
   - Scheduler checks end_date → status=COMPLETED

### IoT API Response Format

```python
# GET /api/internal/ads/distribute?uuid={device_imei}&sign={md5_sign}
# Response format matching manufacturer spec:
{
    "code": 200,
    "type": 0,
    "data": [
        {
            "id": ad_content.id,
            "title": ad_request.title,
            "fileType": 0 if IMAGE else 1,
            "url1": ad_content.url_small,  # <20 slots
            "url2": ad_content.url_large,  # >20 slots
            "url3": "",
            "forward": "",
            "playTime": ad_content.duration_seconds,
            "weight": 0,  # Volume (0-100)
            "screenBrightness": 255,  # Brightness (0-255)
            "guuid": None
        }
    ],
    "msg": "OK",
    "time": timestamp_ms
}
```

---

## Indexes

```python
# AdRequest
class Meta:
    db_table = 'ad_requests'
    indexes = [
        models.Index(fields=['user', 'status']),
        models.Index(fields=['status', 'start_date']),
        models.Index(fields=['status', 'end_date']),
    ]

# AdContent
class Meta:
    db_table = 'ad_contents'
    indexes = [
        models.Index(fields=['ad_request', 'is_active']),
    ]

# AdStation
class Meta:
    db_table = 'ad_stations'
    unique_together = ['ad_request', 'station']

# AdDistribution
class Meta:
    db_table = 'ad_distributions'
    indexes = [
        models.Index(fields=['station', 'sync_status']),
        models.Index(fields=['device_uuid']),
    ]
```

---

## Related Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/ads/request` | Create ad request |
| GET | `/api/user/ads/my-ads` | List user's ads |
| POST | `/api/user/ads/{id}/pay` | Pay for approved ad |
| GET | `/api/internal/ads/distribute` | IoT endpoint for devices |
