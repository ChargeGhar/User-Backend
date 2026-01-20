# Feature: Partner Models (Franchise & Vendor)

**App**: `api/vendor/`  
**Priority**: Phase 1

---

## Tables

### 2.1 Partner (Base Model)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `partner_type` | CharField(20) | FRANCHISE or VENDOR | NOT NULL |
| `user` | OneToOneField(User) | Linked user account | NOT NULL, UNIQUE, on_delete=PROTECT |
| `code` | CharField(20) | Partner code (FR-001, VN-001) | NOT NULL, UNIQUE |
| `name` | CharField(100) | Business/Partner name | NOT NULL |
| `contact_phone` | CharField(20) | Contact phone | NOT NULL |
| `contact_email` | EmailField | Contact email | NULL |
| `address` | TextField | Address | NULL |
| `status` | CharField(20) | Partner status | NOT NULL, default='ACTIVE' |
| `agreement_doc_url` | URLField | Signed agreement document | NULL |
| `assigned_by` | ForeignKey(User) | Admin who created | NULL, on_delete=SET_NULL |
| `assigned_at` | DateTimeField | When assigned | auto_now_add |
| `notes` | TextField | Admin notes | NULL |

**Partner Type Choices**:
```python
PARTNER_TYPE_CHOICES = [
    ('FRANCHISE', 'Franchise'),
    ('VENDOR', 'Vendor'),
]
```

**Status Choices**:
```python
STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('INACTIVE', 'Inactive'),
    ('SUSPENDED', 'Suspended'),
]
```

---

### 2.2 Franchise

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `partner` | OneToOneField(Partner) | Link to Partner | NOT NULL, UNIQUE, on_delete=CASCADE |
| `upfront_amount` | DecimalField(12,2) | Amount paid upfront | NOT NULL, default=0 |
| `stations_allocated` | IntegerField | Number of stations purchased | NOT NULL, default=0 |
| `revenue_share_percent` | DecimalField(5,2) | % paid to Chargeghar | NOT NULL, CHECK 0-100 |
| `balance` | DecimalField(12,2) | Available balance for payout | NOT NULL, default=0 |
| `total_earnings` | DecimalField(12,2) | Lifetime earnings | NOT NULL, default=0 |
| `total_paid_to_chargeghar` | DecimalField(12,2) | Total paid to CG | NOT NULL, default=0 |
| `payout_threshold` | DecimalField(12,2) | Min balance for payout | NOT NULL, default=0 |
| `agreement_start_date` | DateField | Agreement start | NOT NULL |
| `agreement_end_date` | DateField | Agreement end | NULL (indefinite) |

---

### 2.3 Vendor

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `partner` | OneToOneField(Partner) | Link to Partner | NOT NULL, UNIQUE, on_delete=CASCADE |
| `vendor_type` | CharField(20) | Revenue or Non-Revenue | NOT NULL |
| `franchise` | ForeignKey(Franchise) | Parent franchise (if sub-vendor) | NULL, on_delete=SET_NULL |
| `is_direct_vendor` | BooleanField | True if under Chargeghar directly | NOT NULL, default=False |
| `balance` | DecimalField(12,2) | Available balance | NOT NULL, default=0 |
| `total_earnings` | DecimalField(12,2) | Lifetime earnings | NOT NULL, default=0 |

**Vendor Type Choices**:
```python
VENDOR_TYPE_CHOICES = [
    ('REVENUE', 'Revenue Vendor'),       # Has dashboard, gets payouts
    ('NON_REVENUE', 'Non-Revenue Vendor'), # Physical presence only
]
```

**Logic**:
- `franchise IS NULL AND is_direct_vendor = True` → Direct Vendor (under Chargeghar)
- `franchise IS NOT NULL AND is_direct_vendor = False` → Sub-Vendor (under Franchise)

---

## Business Logic Notes

1. **Partner Creation**:
   - Admin creates Partner first (base record)
   - Then creates Franchise OR Vendor (extends Partner)
   - User account linked via OneToOne

2. **Franchise Conversion**:
   - After agreement ends, Franchise can convert to Vendor
   - Create new Vendor record, deactivate Franchise

3. **Revenue Model**:
   - Stored in `StationRevenueShare` (see 03_station_distribution.md)
   - NOT on Vendor model directly

---

## Indexes

```python
# Partner
class Meta:
    db_table = 'partners'
    indexes = [
        models.Index(fields=['partner_type', 'status']),
        models.Index(fields=['code']),
    ]

# Franchise
class Meta:
    db_table = 'franchises'

# Vendor
class Meta:
    db_table = 'vendors'
    indexes = [
        models.Index(fields=['vendor_type']),
        models.Index(fields=['franchise', 'is_direct_vendor']),
    ]
```

---

## Constraints

```python
# Vendor - must be either direct OR under franchise, not both
class Meta:
    constraints = [
        models.CheckConstraint(
            check=(
                models.Q(franchise__isnull=True, is_direct_vendor=True) |
                models.Q(franchise__isnull=False, is_direct_vendor=False)
            ),
            name='vendor_hierarchy_check'
        )
    ]
```
