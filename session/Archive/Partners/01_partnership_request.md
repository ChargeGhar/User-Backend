# Feature: Partnership Request

**App**: `api/vendor/`  
**Priority**: Phase 1

---

## Tables

### 1.1 PartnershipRequest

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `full_name` | CharField(255) | Applicant name | NOT NULL |
| `contact_number` | CharField(20) | Phone number | NOT NULL |
| `subject` | CharField(255) | Request subject | NOT NULL |
| `message` | TextField | Request details | NULL allowed |
| `status` | CharField(20) | Request status | NOT NULL, default='PENDING' |
| `contacted_by` | ForeignKey(User) | Admin who contacted | NULL, on_delete=SET_NULL |
| `contacted_at` | DateTimeField | When contacted | NULL |
| `notes` | TextField | Admin notes | NULL |

**Status Choices**:
```python
STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('CONTACTED', 'Contacted'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
]
```

---

## Business Logic Notes

1. **Mobile App Flow**:
   - User submits request via `POST /api/partnerships/request`
   - Fields: full_name, contact_number, subject, message
   - Status starts as `PENDING`

2. **Admin Panel Flow**:
   - Admin views pending requests
   - Admin contacts user → status = `CONTACTED`
   - Admin decides → status = `APPROVED` or `REJECTED`
   - If approved → Admin creates Partner (Vendor/Franchise) manually

3. **No Auto-Creation**:
   - PartnershipRequest does NOT auto-create Partner
   - Admin manually creates Partner after approval

---

## Indexes

```python
class Meta:
    db_table = 'partnership_requests'
    indexes = [
        models.Index(fields=['status']),
        models.Index(fields=['created_at']),
    ]
```

---

## Related Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/user/partnerships/request` | Submit partnership request |
| GET | `/api/admin/partnerships/requests` | List all requests (Admin) |
| PATCH | `/api/admin/partnerships/requests/{id}` | Update request status (Admin) |
