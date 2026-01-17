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
| `user` | ForeignKey(User) | User who submitted | NOT NULL, on_delete=CASCADE | --> system
| `full_name` | CharField(255) | full Name | NOT NULL | --> user
| `title` | CharField(255) | Ad title | NOT NULL | --> admin
| `description` | TextField | Ad description | NULL | -- admin
| `contact_number` | TextField | User contact number | NULL | --> user
| `duration_days` | IntegerField | Requested duration | NOT NULL | --> admin
| `status` | CharField(20) | Request status | NOT NULL | --> admin, user, system
| `submitted_at` | DateTimeField | When submitted | NULL | --> system
| `reviewed_by` | ForeignKey(User) | Admin who reviewed | NULL, on_delete=SET_NULL | --> system
| `reviewed_at` | DateTimeField | When reviewed | NULL | --> system
| `admin_price` | DecimalField(12,2) | Price set by admin | NULL | --> admin
| `admin_notes` | TextField | Admin notes | NULL | --> admin
| `rejection_reason` | TextField | If rejected | NULL | --> admin
| `approved_by` | ForeignKey(User) | Admin who approved | NULL, on_delete=SET_NULL | --> system
| `approved_at` | DateTimeField | When approved | NULL | --> system
| `transaction` | ForeignKey(Transaction) | Payment transaction | NULL, on_delete=SET_NULL | --> system
| `paid_at` | DateTimeField | When paid | NULL | --> system
| `start_date` | DateField | When ad starts running | NULL | --> admin for sheduling
| `end_date` | DateField | When ad ends | NULL | --> admin for sheduling
| `completed_at` | DateTimeField | When ad completed | NULL | --> admin

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
| `created_at` | DateTimeField | | auto_now_add | --> system
| `updated_at` | DateTimeField | | auto_now | --> system
| `ad_request` | ForeignKey(AdRequest) | Parent ad request | NOT NULL, on_delete=CASCADE | --> system
| `content_type` | CharField(10) | IMAGE or VIDEO | NOT NULL | --> system
| `media_upload` | ForeignKey(MediaUpload) | Uploaded media | NOT NULL, on_delete=PROTECT | --> user / system
| `duration_seconds` | IntegerField | Play time for images | NOT NULL, default=5 | --> admin
| `display_order` | IntegerField | Order in rotation | NOT NULL, default=0 | --> admin
| `is_active` | BooleanField | Whether to display | NOT NULL, default=True | --> system
| `metadata` | JSONField | Additional data | default={} | --> system

**Content Type Choices**:
```python
CONTENT_TYPE_CHOICES = [
    ('IMAGE', 'Image'),   # jpg, png
    ('VIDEO', 'Video'),   # mp4
]
```
---

### 6.4 AdDistribution

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `ad_content` | ForeignKey(AdContent) | Ad content | NOT NULL, on_delete=CASCADE |
| `station` | ForeignKey(Station) | Station | NOT NULL, on_delete=CASCADE |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |

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