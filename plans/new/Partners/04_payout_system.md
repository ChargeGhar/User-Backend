# Feature: Payout & Revenue Distribution System

**App**: `api/vendor/`  
**Priority**: Phase 1

---

## AppConfig Keys Required

Add to `api/user/system/fixtures/app_config.json`:

```json
{
  "model": "system.appconfig",
  "fields": {
    "key": "PLATFORM_VAT_PERCENT",
    "value": "13",
    "description": "VAT percentage deducted from Chargeghar-level payouts (to Franchise/Direct Vendor)",
    "is_active": true
  }
},
{
  "model": "system.appconfig",
  "fields": {
    "key": "PLATFORM_SERVICE_CHARGE_PERCENT",
    "value": "2.5",
    "description": "Service charge percentage deducted from Chargeghar-level payouts",
    "is_active": true
  }
}
```

**Usage**: These configs are ONLY applied to Chargeghar-level payouts, NOT Franchise-level payouts.

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
| `vat_percent_applied` | DecimalField(5,2) | VAT % at time of processing | NOT NULL, default=0 |
| `vat_deducted` | DecimalField(12,2) | VAT amount deducted | NOT NULL, default=0 |
| `service_charge_percent_applied` | DecimalField(5,2) | Service charge % at time of processing | NOT NULL, default=0 |
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

**Source**: Requirements.md Section 1 - Payment Hierarchy & Distribution

#### Rule 1: Chargeghar-level Payouts (DEDUCT VAT & Service Charge)
- **Applies to**: `CHARGEGHAR_TO_FRANCHISE`, `CHARGEGHAR_TO_VENDOR`
- **Logic**: System DEDUCTS VAT and Service Charges before manual release
- **Formula**:
  ```
  vat_deducted = amount × (PLATFORM_VAT_PERCENT / 100)
  service_charge = amount × (PLATFORM_SERVICE_CHARGE_PERCENT / 100)
  net_amount = amount - vat_deducted - service_charge
  ```

#### Rule 2: Franchise-level Payouts (NO Deduction)
- **Applies to**: `FRANCHISE_TO_VENDOR`
- **Logic**: System does NOT deduct VAT/Service Charges
- **Reason**: Internal private distributions; already addressed at Chargeghar level
- **Formula**:
  ```
  vat_percent_applied = 0
  vat_deducted = 0
  service_charge_percent_applied = 0
  service_charge = 0
  net_amount = amount
  ```

### Payout Processing Service

```python
from decimal import Decimal
from api.user.system.services import AppConfigService

class PayoutService:
    def __init__(self):
        self.config_service = AppConfigService()
    
    def calculate_payout_deductions(self, amount: Decimal, payout_type: str) -> dict:
        """
        Calculate VAT and Service Charge based on payout type.
        
        Chargeghar-level: DEDUCT VAT & Service Charge
        Franchise-level: NO deductions
        """
        result = {
            'amount': amount,
            'vat_percent_applied': Decimal('0'),
            'vat_deducted': Decimal('0'),
            'service_charge_percent_applied': Decimal('0'),
            'service_charge': Decimal('0'),
            'net_amount': amount,
        }
        
        # Only apply deductions for Chargeghar-level payouts
        if payout_type in ['CHARGEGHAR_TO_FRANCHISE', 'CHARGEGHAR_TO_VENDOR']:
            # Get rates from AppConfig
            vat_percent = Decimal(
                self.config_service.get_config_cached('PLATFORM_VAT_PERCENT', '13')
            )
            service_percent = Decimal(
                self.config_service.get_config_cached('PLATFORM_SERVICE_CHARGE_PERCENT', '2.5')
            )
            
            # Calculate deductions
            vat_deducted = amount * (vat_percent / Decimal('100'))
            service_charge = amount * (service_percent / Decimal('100'))
            net_amount = amount - vat_deducted - service_charge
            
            result.update({
                'vat_percent_applied': vat_percent,
                'vat_deducted': vat_deducted.quantize(Decimal('0.01')),
                'service_charge_percent_applied': service_percent,
                'service_charge': service_charge.quantize(Decimal('0.01')),
                'net_amount': net_amount.quantize(Decimal('0.01')),
            })
        
        # For FRANCHISE_TO_VENDOR: No deductions (result already has zeros)
        
        return result
    
    def process_payout(self, payout_request, admin_user):
        """Process payout with appropriate deductions"""
        deductions = self.calculate_payout_deductions(
            payout_request.amount,
            payout_request.payout_type
        )
        
        # Update payout request with calculated values
        payout_request.vat_percent_applied = deductions['vat_percent_applied']
        payout_request.vat_deducted = deductions['vat_deducted']
        payout_request.service_charge_percent_applied = deductions['service_charge_percent_applied']
        payout_request.service_charge = deductions['service_charge']
        payout_request.net_amount = deductions['net_amount']
        payout_request.processed_by = admin_user
        payout_request.processed_at = timezone.now()
        payout_request.status = 'PROCESSING'
        payout_request.save()
        
        return payout_request
```

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
