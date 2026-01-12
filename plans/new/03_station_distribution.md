# Feature: Station Distribution & Revenue Share

**App**: `api/vendor/`  
**Priority**: Phase 1

---

## Tables

### 3.1 StationDistribution

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `station` | ForeignKey(Station) | Station being distributed | NOT NULL, on_delete=CASCADE |
| `distributor_type` | CharField(20) | Who distributes | NOT NULL |
| `distributor_partner` | ForeignKey(Partner) | Distributor (NULL = Chargeghar) | NULL, on_delete=CASCADE |
| `distributee_partner` | ForeignKey(Partner) | Who receives | NOT NULL, on_delete=CASCADE |
| `distribution_type` | CharField(30) | Type of distribution | NOT NULL |
| `effective_date` | DateField | When assignment starts | NOT NULL, default=today |
| `expiry_date` | DateField | When assignment ends | NULL (indefinite) |
| `is_active` | BooleanField | Current active assignment | NOT NULL, default=True |
| `assigned_by` | ForeignKey(User) | Admin who assigned | NULL, on_delete=SET_NULL |
| `notes` | TextField | Additional details | NULL |

**Distribution Type Choices**:
```python
DISTRIBUTION_TYPE_CHOICES = [
    ('CHARGEGHAR_TO_FRANCHISE', 'Chargeghar to Franchise'),
    ('CHARGEGHAR_TO_VENDOR', 'Chargeghar to Direct Vendor'),
    ('FRANCHISE_TO_VENDOR', 'Franchise to Sub-Vendor'),
]
```

**Distributor Type Choices**:
```python
DISTRIBUTOR_TYPE_CHOICES = [
    ('CHARGEGHAR', 'Chargeghar'),
    ('FRANCHISE', 'Franchise'),
]
```

---

### 3.2 StationRevenueShare

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `distribution` | OneToOneField(StationDistribution) | Link to distribution | NOT NULL, UNIQUE, on_delete=CASCADE |
| `revenue_model` | CharField(20) | Share % or Fixed Rent | NOT NULL |
| `vendor_percent` | DecimalField(5,2) | Vendor's share % | NULL, CHECK 0-100 |
| `chargeghar_percent` | DecimalField(5,2) | Chargeghar's share % | NULL, CHECK 0-100 |
| `franchise_percent` | DecimalField(5,2) | Franchise's share % (if applicable) | NULL, CHECK 0-100 |
| `fixed_rent_amount` | DecimalField(12,2) | Fixed rent amount | NULL |

**Revenue Model Choices**:
```python
REVENUE_MODEL_CHOICES = [
    ('SHARE_PERCENT', 'Share Percentage'),  # Vendor gets X%
    ('FIXED_RENT', 'Fixed Rent'),           # Fixed amount, rest to owner
]
```

---

### 3.3 StationHierarchy (Denormalized View)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `station` | OneToOneField(Station) | Station | NOT NULL, UNIQUE, on_delete=CASCADE |
| `franchise` | ForeignKey(Franchise) | Assigned franchise | NULL, on_delete=SET_NULL |
| `vendor` | ForeignKey(Vendor) | Assigned vendor | NULL, on_delete=SET_NULL |
| `hierarchy_level` | IntegerField | 0=CG only, 1=Franchise, 2=Vendor | NOT NULL, default=0 |

**Logic**:
- `hierarchy_level = 0`: Station owned by Chargeghar only
- `hierarchy_level = 1`: Station assigned to Franchise
- `hierarchy_level = 2`: Station assigned to Vendor (direct or sub)

---

## Business Logic Notes

1. **Distribution Flow**:
   - Chargeghar → Franchise: Creates StationDistribution + StationRevenueShare
   - Chargeghar → Direct Vendor: Creates StationDistribution + StationRevenueShare
   - Franchise → Sub-Vendor: Creates StationDistribution + StationRevenueShare

2. **Revenue Calculation**:
   - On each rental transaction, calculate shares based on StationRevenueShare
   - Store in RevenueDistribution (see 04_payout_system.md)

3. **StationHierarchy**:
   - Denormalized table for quick lookups
   - Updated via signals when StationDistribution changes

4. **Station Model Update**:
   - NO FK on Station model
   - Use StationHierarchy for lookups

---

## Indexes

```python
# StationDistribution
class Meta:
    db_table = 'station_distributions'
    indexes = [
        models.Index(fields=['station', 'is_active']),
        models.Index(fields=['distributee_partner', 'is_active']),
        models.Index(fields=['distribution_type']),
    ]

# StationHierarchy
class Meta:
    db_table = 'station_hierarchies'
    indexes = [
        models.Index(fields=['franchise']),
        models.Index(fields=['vendor']),
        models.Index(fields=['hierarchy_level']),
    ]
```

---

## Constraints

```python
# StationRevenueShare - percentages must be valid
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(vendor_percent__gte=0, vendor_percent__lte=100) | models.Q(vendor_percent__isnull=True),
            name='vendor_percent_range'
        ),
        models.CheckConstraint(
            check=models.Q(chargeghar_percent__gte=0, chargeghar_percent__lte=100) | models.Q(chargeghar_percent__isnull=True),
            name='chargeghar_percent_range'
        ),

        # Non-Revenue vendors cannot have revenue shares
        if vendor.vendor_type == 'NON_REVENUE':
            revenue_share = None  # No revenue distribution
    ]
```
