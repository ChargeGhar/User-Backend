# Feature: Payout & Revenue Distribution System

**App**: `api/vendor/`  
**Priority**: Phase 1

---

## Tables

### 4.1 PayoutRequest

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `requested_by` | ForeignKey(Partner) | Partner requesting payout | NOT NULL, on_delete=CASCADE |
| `amount` | DecimalField(12,2) | Requested amount | NOT NULL, > 0 |
| `status` | CharField(20) | Request status | NOT NULL, default='PENDING' |
| `payout_type` | CharField(30) | Type of payout | NOT NULL |
| `vat_deducted` | DecimalField(12,2) | VAT amount deducted | NOT NULL, default=0 |
| `service_charge` | DecimalField(12,2) | Service charge deducted | NOT NULL, default=0 |
| `net_amount` | DecimalField(12,2) | Amount after deductions | NOT NULL |
| `processed_by` | ForeignKey(User) | Admin who processed | NULL, on_delete=SET_NULL |
| `processed_at` | DateTimeField | When processed | NULL |
| `reference_id` | CharField(50) | Internal reference for tracing | NOT NULL, UNIQUE |
| `bank_name` | CharField(100) | Bank name | NULL |
| `account_number` | CharField(50) | Account number | NULL |
| `account_holder_name` | CharField(100) | Account holder | NULL |
| `rejection_reason` | TextField | If rejected | NULL |
| `notes` | TextField | Admin notes | NULL |

**Status Choices**:
```python
STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('PROCESSING', 'Processing'),
    ('COMPLETED', 'Completed'),
    ('REJECTED', 'Rejected'),
]
```

**Payout Type Choices**:
```python
PAYOUT_TYPE_CHOICES = [
    ('CHARGEGHAR_TO_FRANCHISE', 'Chargeghar to Franchise'),
    ('CHARGEGHAR_TO_VENDOR', 'Chargeghar to Direct Vendor'),
    ('FRANCHISE_TO_VENDOR', 'Franchise to Sub-Vendor'),
]
```

---

### 4.2 RevenueDistribution

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `transaction` | ForeignKey(Transaction) | Source transaction | NOT NULL, on_delete=CASCADE |
| `station` | ForeignKey(Station) | Station where transaction occurred | NOT NULL, on_delete=CASCADE |
| `distribution_level` | CharField(20) | Level of distribution | NOT NULL |
| `chargeghar_share` | DecimalField(12,2) | Chargeghar's share | NOT NULL, default=0 |
| `franchise` | ForeignKey(Franchise) | Franchise (if applicable) | NULL, on_delete=SET_NULL |
| `franchise_share` | DecimalField(12,2) | Franchise's share | NOT NULL, default=0 |
| `vendor` | ForeignKey(Vendor) | Vendor (if applicable) | NULL, on_delete=SET_NULL |
| `vendor_share` | DecimalField(12,2) | Vendor's share | NOT NULL, default=0 |
| `distributed_at` | DateTimeField | When distributed | NULL |
| `is_distributed` | BooleanField | Whether added to balances | NOT NULL, default=False |

**Distribution Level Choices**:
```python
DISTRIBUTION_LEVEL_CHOICES = [
    ('CHARGEGHAR_ONLY', 'Chargeghar Only'),      # No partners
    ('CHARGEGHAR_FRANCHISE', 'Chargeghar + Franchise'),
    ('CHARGEGHAR_VENDOR', 'Chargeghar + Direct Vendor'),
    ('FRANCHISE_VENDOR', 'Franchise + Sub-Vendor'),
]
```

---

## Business Logic Notes

### VAT & Service Charge Rules

1. **Chargeghar-level payouts** (to Franchise or Direct Vendor):
   - System DEDUCTS VAT and Service Charges
   - `net_amount = amount - vat_deducted - service_charge`

2. **Franchise-level payouts** (to Sub-Vendors):
   - System does NOT deduct VAT/Service Charges
   - `vat_deducted = 0`, `service_charge = 0`
   - `net_amount = amount`

### Revenue Distribution Flow

1. **On Rental Completion**:
   ```python
   # Get station hierarchy
   hierarchy = StationHierarchy.objects.get(station=rental.station)
   revenue_share = StationRevenueShare.objects.get(distribution__station=rental.station, distribution__is_active=True)
   
   # Calculate shares
   total = transaction.amount
   if revenue_share.revenue_model == 'SHARE_PERCENT':
       vendor_share = total * (revenue_share.vendor_percent / 100)
       chargeghar_share = total - vendor_share
   else:  # FIXED_RENT
       vendor_share = revenue_share.fixed_rent_amount
       chargeghar_share = total - vendor_share
   
   # Create RevenueDistribution record
   ```

2. **Balance Updates**:
   - After RevenueDistribution created, update Partner balances
   - Franchise.balance += franchise_share
   - Vendor.balance += vendor_share

---

## Indexes

```python
# PayoutRequest
class Meta:
    db_table = 'payout_requests'
    indexes = [
        models.Index(fields=['requested_by', 'status']),
        models.Index(fields=['payout_type', 'status']),
        models.Index(fields=['created_at']),
    ]

# RevenueDistribution
class Meta:
    db_table = 'revenue_distributions'
    indexes = [
        models.Index(fields=['transaction']),
        models.Index(fields=['station', 'created_at']),
        models.Index(fields=['franchise', 'is_distributed']),
        models.Index(fields=['vendor', 'is_distributed']),
    ]
```
