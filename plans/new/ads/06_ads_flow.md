# **FINAL ADVERTISEMENT SYSTEM - COMPLETE ENDPOINT FLOW**

## **USER ENDPOINTS (3 Total)**

### **1. POST** `/api/user/ads/request`
**Purpose**: Submit new ad request

**Request**:
```json
{
  "full_name": "John Doe",
  "contact_number": "+977-9841234567",
  "media_upload_id": "uuid"
}
```

**Logic**:
```python
# Create AdRequest
ad_request = AdRequest.objects.create(
    user=request.user,
    full_name=data['full_name'],
    contact_number=data['contact_number'],
    status='SUBMITTED',
    submitted_at=timezone.now()
)

# Create AdContent
AdContent.objects.create(
    ad_request=ad_request,
    media_upload_id=data['media_upload_id'],
    content_type='IMAGE' if is_image else 'VIDEO',
    is_active=True,
    duration_seconds=5,  # default
    display_order=0
)
```

**Response**: AdRequest object with ID

---

### **2. GET** `/api/user/ads/my-ads`
**Purpose**: List user's ad requests

**Query Params**: `?status=RUNNING` (optional)

**Response**:
```json
[
  {
    "id": "uuid",
    "full_name": "John Doe",
    "contact_number": "+977-9841234567",
    "title": "Summer Sale Ad",
    "description": "50% off all items",
    "status": "RUNNING",
    "duration_days": 30,
    "admin_price": "5000.00",
    "submitted_at": "2026-01-10T10:00:00Z",
    "approved_at": "2026-01-11T14:00:00Z",
    "paid_at": "2026-01-12T09:00:00Z",
    "start_date": "2026-01-15",
    "end_date": "2026-02-14",
    "rejection_reason": null,
    "admin_notes": "Approved for all locations",
    "ad_content": {
      "id": "uuid",
      "content_type": "IMAGE",
      "media_upload": {...},
      "duration_seconds": 5
    },
    "stations": [
      {"id": "uuid", "name": "Station A"},
      {"id": "uuid", "name": "Station B"}
    ]
  }
]
```

---

### **3. POST** `/api/user/ads/{id}/pay`
**Purpose**: Pay for approved ad

**Validation**:
- `status` must be `'PENDING_PAYMENT'`
- `admin_price` must exist
- User wallet balance >= admin_price

**Logic**:
```python
# Deduct from wallet
wallet = request.user.wallet
wallet.balance -= ad_request.admin_price
wallet.save()

# Create transaction
transaction = Transaction.objects.create(
    user=request.user,
    transaction_type='ADVERTISEMENT',
    amount=ad_request.admin_price,
    description=f'Payment for ad: {ad_request.title}',
    status='SUCCESS'
)

# Update ad request
ad_request.transaction = transaction
ad_request.paid_at = timezone.now()
ad_request.status = 'PAID'
ad_request.save()
```

**Response**: Updated AdRequest

---

## **ADMIN ENDPOINTS (5 Total - Consolidated)**

### **4. GET** `/api/admin/ads/requests`
**Purpose**: List all ad requests with filters

**Query Params**: 
- `?status=SUBMITTED` (filter by status)
- `?user_id=uuid` (filter by user)
- `?search=keyword` (search title, full_name)

**Response**: Paginated list of AdRequests with related data

---

### **5. GET** `/api/admin/ads/requests/{id}`
**Purpose**: Get single ad request details

**Response**: Full AdRequest with AdContent, stations, transaction details

---

### **6. PATCH** `/api/admin/ads/requests/{id}/review`
**Purpose**: Review and set all ad details (CONSOLIDATED - handles review, pricing, station assignment)

**Valid Statuses**: `'SUBMITTED'`, `'UNDER_REVIEW'`

**Request**:
```json
{
  "title": "Summer Sale Ad",
  "description": "50% off all items",
  "duration_days": 30,
  "admin_price": "5000.00",
  "admin_notes": "Approved for high-traffic stations",
  "station_ids": ["uuid1", "uuid2"],
  "start_date": "2026-01-15",  // optional - can be set later
  
  // AdContent settings
  "duration_seconds": 7,  // for images
  "display_order": 0
}
```

**Logic**:
```python
# Update AdRequest
ad_request.status = 'UNDER_REVIEW'
ad_request.reviewed_by = request.user
ad_request.reviewed_at = timezone.now()
ad_request.title = data['title']
ad_request.description = data['description']
ad_request.duration_days = data['duration_days']
ad_request.admin_price = data['admin_price']
ad_request.admin_notes = data.get('admin_notes', '')
ad_request.start_date = data.get('start_date')
ad_request.save()

# Update AdContent
ad_content = ad_request.adcontent_set.first()
ad_content.duration_seconds = data.get('duration_seconds', 5)
ad_content.display_order = data.get('display_order', 0)
ad_content.save()

# Create AdDistribution records
AdDistribution.objects.filter(ad_content=ad_content).delete()  # Clear existing
for station_id in data['station_ids']:
    AdDistribution.objects.create(
        ad_content=ad_content,
        station_id=station_id
    )
```

**Response**: Updated AdRequest

---

### **7. POST** `/api/admin/ads/requests/{id}/action`
**Purpose**: Approve, Reject, Schedule, Pause, Resume, Cancel, Complete (CONSOLIDATED ACTION ENDPOINT)

**Valid Actions**:

#### **A. APPROVE**
```json
{
  "action": "approve"
}
```
**Logic**:
```python
ad_request.status = 'APPROVED'
ad_request.approved_by = request.user
ad_request.approved_at = timezone.now()
ad_request.save()

# Auto-transition to PENDING_PAYMENT
ad_request.status = 'PENDING_PAYMENT'
ad_request.save()
```

---

#### **B. REJECT**
```json
{
  "action": "reject",
  "rejection_reason": "Content violates policy"
}
```
**Logic**:
```python
ad_request.status = 'REJECTED'
ad_request.rejection_reason = data['rejection_reason']
ad_request.reviewed_by = request.user
ad_request.reviewed_at = timezone.now()
ad_request.save()
```

---

#### **C. SCHEDULE**
```json
{
  "action": "schedule",
  "start_date": "2026-01-20",
  "end_date": "2026-02-19"  // optional - auto-calculated if not provided
}
```
**Valid Status**: `'PAID'`

**Logic**:
```python
ad_request.start_date = data['start_date']
ad_request.end_date = data.get('end_date') or (
    data['start_date'] + timedelta(days=ad_request.duration_days)
)
ad_request.status = 'SCHEDULED'
ad_request.save()
```

---

#### **D. PAUSE**
```json
{
  "action": "pause"
}
```
**Valid Status**: `'RUNNING'`

**Logic**:
```python
ad_request.status = 'PAUSED'
ad_request.save()
```

---

#### **E. RESUME**
```json
{
  "action": "resume"
}
```
**Valid Status**: `'PAUSED'`

**Logic**:
```python
ad_request.status = 'RUNNING'
ad_request.save()
```

---

#### **F. CANCEL**
```json
{
  "action": "cancel",
  "reason": "User requested cancellation"  // optional
}
```
**Valid Statuses**: Any except `'COMPLETED'`

**Logic**:
```python
ad_request.status = 'CANCELLED'
if data.get('reason'):
    ad_request.admin_notes += f"\nCancellation reason: {data['reason']}"
ad_request.save()
```

---

#### **G. COMPLETE**
```json
{
  "action": "complete"
}
```
**Valid Status**: `'RUNNING'`

**Logic**:
```python
ad_request.status = 'COMPLETED'
ad_request.completed_at = timezone.now()
ad_request.save()
```

---

### **8. PATCH** `/api/admin/ads/requests/{id}/update-schedule`
**Purpose**: Update start/end dates for scheduled or running ads

**Request**:
```json
{
  "start_date": "2026-01-25",
  "end_date": "2026-02-24"
}
```

**Valid Statuses**: `'SCHEDULED'`, `'RUNNING'`, `'PAUSED'`

**Logic**:
```python
ad_request.start_date = data.get('start_date', ad_request.start_date)
ad_request.end_date = data.get('end_date', ad_request.end_date)
ad_request.save()
```

---

## **AUTOMATED SYSTEM TASKS (Cron Jobs)**

### **Task 1: Start Scheduled Ads**
**Runs**: Every hour

**Logic**:
```python
from django.utils import timezone

# Get ads that should start today
ads_to_start = AdRequest.objects.filter(
    status='SCHEDULED',
    start_date__lte=timezone.now().date()
)

for ad in ads_to_start:
    ad.status = 'RUNNING'
    ad.save()
```

---

### **Task 2: Complete Finished Ads**
**Runs**: Every hour

**Logic**:
```python
# Get ads that should end today
ads_to_complete = AdRequest.objects.filter(
    status='RUNNING',
    end_date__lt=timezone.now().date()
)

for ad in ads_to_complete:
    ad.status = 'COMPLETED'
    ad.completed_at = timezone.now()
    ad.save()
```

---

## **COMPLETE WORKFLOW DIAGRAM**

```
USER SUBMITS
├─ POST /api/user/ads/request
├─ Creates: AdRequest (SUBMITTED) + AdContent
└─ Fields filled: user, full_name, contact_number, submitted_at, status

        ↓

ADMIN REVIEWS
├─ PATCH /api/admin/ads/requests/{id}/review
├─ Updates: title, description, duration_days, admin_price, admin_notes
├─ Updates: AdContent.duration_seconds, display_order
├─ Creates: AdDistribution (links ad_content + stations)
└─ Fields filled: reviewed_by, reviewed_at, status='UNDER_REVIEW'

        ↓

ADMIN APPROVES
├─ POST /api/admin/ads/requests/{id}/action {"action": "approve"}
├─ Status: APPROVED → PENDING_PAYMENT
└─ Fields filled: approved_by, approved_at

        ↓

USER PAYS
├─ POST /api/user/ads/{id}/pay
├─ Creates: Transaction (DEBIT)
├─ Updates: Wallet.balance
├─ Status: PAID
└─ Fields filled: transaction, paid_at

        ↓

ADMIN SCHEDULES (Optional)
├─ POST /api/admin/ads/requests/{id}/action {"action": "schedule"}
├─ OR PATCH /api/admin/ads/requests/{id}/update-schedule
├─ Status: SCHEDULED
└─ Fields filled: start_date, end_date

        ↓

AUTO START (Cron)
├─ System checks start_date
├─ Status: RUNNING
└─ Fields filled: (none - status change only)

        ↓

MANAGE RUNNING AD
├─ POST /api/admin/ads/requests/{id}/action {"action": "pause"}
├─ POST /api/admin/ads/requests/{id}/action {"action": "resume"}
└─ POST /api/admin/ads/requests/{id}/action {"action": "cancel"}

        ↓

AUTO COMPLETE (Cron)
├─ System checks end_date
├─ Status: COMPLETED
└─ Fields filled: completed_at
```

---

## **FINAL ENDPOINT COUNT**

### **User Endpoints**: 3
1. POST `/api/user/ads/request` - Submit ad
2. GET `/api/user/ads/my-ads` - List my ads
3. POST `/api/user/ads/{id}/pay` - Pay for ad

### **Admin Endpoints**: 5
4. GET `/api/admin/ads/requests` - List all ads
5. GET `/api/admin/ads/requests/{id}` - Get ad details
6. PATCH `/api/admin/ads/requests/{id}/review` - Review + set pricing + assign stations
7. POST `/api/admin/ads/requests/{id}/action` - Approve/Reject/Schedule/Pause/Resume/Cancel/Complete
8. PATCH `/api/admin/ads/requests/{id}/update-schedule` - Update dates

### **Total**: 8 Endpoints (Optimized & Complete)