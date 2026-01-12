## **1. Partnership Request & Admin-Added Partner**

### **1.1 PartnershipRequest**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `created_at` | DateTime | | DEFAULT NOW() |
| `updated_at` | DateTime | | DEFAULT NOW() |
| `full_name` | VARCHAR(255) | | NOT NULL |
| `contact_number` | VARCHAR(20) | | NOT NULL |
| `subject` | VARCHAR(255) | | NOT NULL |
| `message` | TEXT | | |
| `status` | VARCHAR(20) | PENDING, CONTACTED, APPROVED, REJECTED | NOT NULL, DEFAULT 'PENDING' |
| `contacted_by` | UUID | FK to User (Admin who contacted) | NULLABLE |
| `contacted_at` | DateTime | | NULLABLE |
| `notes` | TEXT | Admin notes | |

### **1.2 Partner (Base Model)**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `created_at` | DateTime | | DEFAULT NOW() |
| `updated_at` | DateTime | | DEFAULT NOW() |
| `partner_type` | VARCHAR(20) | FRANCHISE, VENDOR | NOT NULL |
| `user_id` | UUID | FK to User (Linked account) | NOT NULL, UNIQUE |
| `status` | VARCHAR(20) | ACTIVE, INACTIVE, SUSPENDED | NOT NULL, DEFAULT 'ACTIVE' |
| `agreement_doc_url` | VARCHAR(500) | Link to signed agreement | NULLABLE |
| `assigned_by` | UUID | FK to User (Admin who assigned) | NULLABLE |
| `assigned_at` | DateTime | | DEFAULT NOW() |

### **1.3 Franchise**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `partner_id` | UUID | FK to Partner | NOT NULL, UNIQUE |
| `upfront_amount` | DECIMAL(12,2) | ₹X paid upfront | NOT NULL, DEFAULT 0 |
| `stations_allocated` | INTEGER | Number of stations (Y) | NOT NULL, DEFAULT 0 |
| `revenue_percent` | DECIMAL(5,2) | % paid to Chargeghar | NOT NULL, CHECK (0-100) |
| `balance` | DECIMAL(12,2) | Available balance for payout | NOT NULL, DEFAULT 0 |
| `payout_threshold` | DECIMAL(12,2) | Min balance to request payout | NOT NULL, DEFAULT 0 |

### **1.4 Vendor**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `partner_id` | UUID | FK to Partner | NOT NULL, UNIQUE |
| `vendor_type` | VARCHAR(20) | REVENUE_VENDOR, NON_REVENUE_VENDOR | NOT NULL |
| `balance` | DECIMAL(12,2) | Available balance | NOT NULL, DEFAULT 0 |
| `franchise_id` | UUID | FK to Franchise (if under franchise) | NULLABLE |
| `is_direct_vendor` | BOOLEAN | True if assigned directly by Chargeghar | NOT NULL, DEFAULT FALSE |

**Note**: Revenue model details moved to `StationRevenueShare` table only.

---

## **2. Station Distribution System**

### **2.1 StationDistribution**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `created_at` | DateTime | | DEFAULT NOW() |
| `updated_at` | DateTime | | DEFAULT NOW() |
| `station_id` | UUID | FK to Station | NOT NULL |
| `distributor_id` | UUID | FK to Partner (who distributes) | NOT NULL |
| `distributee_id` | UUID | FK to Partner (who receives) | NOT NULL |
| `distribution_type` | VARCHAR(30) | CHARGE_GHAR_TO_FRANCHISE, CHARGE_GHAR_TO_VENDOR, FRANCHISE_TO_VENDOR | NOT NULL |
| `effective_date` | Date | When assignment starts | NOT NULL, DEFAULT CURRENT_DATE |
| `expiry_date` | Date | NULL = indefinite | NULLABLE |
| `is_active` | BOOLEAN | Current active assignment | NOT NULL, DEFAULT TRUE |
| `notes` | TEXT | Additional details | |

### **2.2 StationRevenueShare**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `distribution_id` | UUID | FK to StationDistribution | NOT NULL, UNIQUE |
| `revenue_model` | VARCHAR(20) | SHARE_PERCENT, FIXED_RENT | NOT NULL |
| `vendor_percent` | DECIMAL(5,2) | Vendor's share percentage | CHECK (0-100) |
| `vendor_fixed_rent` | DECIMAL(12,2) | Fixed rent amount | DEFAULT 0 |
| `chargeghar_share` | DECIMAL(5,2) | Chargeghar's share percentage | CHECK (0-100) |
| `chargeghar_fixed_cut` | DECIMAL(12,2) | Chargeghar's fixed cut | DEFAULT 0 |

**Constraints**: 
- For `SHARE_PERCENT`: `vendor_percent` + `chargeghar_share` = 100
- For `FIXED_RENT`: `vendor_fixed_rent` > 0

### **2.3 StationHierarchy**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `station_id` | UUID | FK to Station | NOT NULL, UNIQUE |
| `chargeghar_owner_id` | UUID | FK to User (always Chargeghar) | NOT NULL |
| `franchise_id` | UUID | FK to Franchise | NULLABLE |
| `vendor_id` | UUID | FK to Vendor | NULLABLE |
| `hierarchy_level` | INTEGER | 0=Chargeghar, 1=Franchise, 2=Vendor | NOT NULL |
| `updated_at` | DateTime | | DEFAULT NOW() |

---

## **3. Payment & Payout System**

### **3.1 PayoutRequest**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `created_at` | DateTime | | DEFAULT NOW() |
| `updated_at` | DateTime | | DEFAULT NOW() |
| `requested_by_id` | UUID | FK to Partner | NOT NULL |
| `amount` | DECIMAL(12,2) | Requested amount | NOT NULL, > 0 |
| `status` | VARCHAR(20) | PENDING, PROCESSED, REJECTED | NOT NULL, DEFAULT 'PENDING' |
| `processed_by` | UUID | FK to User (Admin) | NULLABLE |
| `processed_at` | DateTime | | NULLABLE |
| `vat_deducted` | DECIMAL(12,2) | VAT amount deducted | DEFAULT 0 |
| `service_charge` | DECIMAL(12,2) | Service charge deducted | DEFAULT 0 |
| `net_amount` | DECIMAL(12,2) | Amount after deductions | |
| `payout_type` | VARCHAR(30) | CHARGE_GHAR_TO_FRANCHISE, CHARGE_GHAR_TO_VENDOR, FRANCHISE_TO_VENDOR | NOT NULL |
| `reference_id` | VARCHAR(50) | For tracing | UNIQUE |

### **3.2 RevenueDistribution**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `created_at` | DateTime | | DEFAULT NOW() |
| `transaction_id` | UUID | FK to Transaction | NOT NULL |
| `franchise_id` | UUID | FK to Franchise | NULLABLE |
| `vendor_id` | UUID | FK to Vendor | NULLABLE |
| `chargeghar_share` | DECIMAL(12,2) | | NOT NULL |
| `partner_share` | DECIMAL(12,2) | | NOT NULL |
| `distributed_at` | DateTime | | |
| `distribution_level` | VARCHAR(20) | CHARGE_GHAR, FRANCHISE | NOT NULL |

---

## **4. IoT & Operations Tracking**

### **4.1 PartnerIotHistory**
| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUID | Primary key | PRIMARY KEY |
| `created_at` | DateTime | | DEFAULT NOW() |
| `partner_id` | UUID | FK to Partner | NOT NULL |
| `station_id` | UUID | FK to Station | NOT NULL |
| `action_type` | VARCHAR(20) | EJECT, REBOOT, CHECK, WIFI_SETTINGS | NOT NULL |
| `performed_from` | VARCHAR(20) | MOBILE_APP, DASHBOARD, ADMIN_PANEL | NOT NULL |
| `powerbank_sn` | VARCHAR(100) | Only for EJECT actions | NULLABLE |
| `is_successful` | BOOLEAN | Whether action succeeded | NOT NULL |
| `error_message` | TEXT | If action failed | NULLABLE |
| `metadata` | JSONB | Additional data | DEFAULT '{}' |
| `response_data` | JSONB | Response from IoT device | DEFAULT '{}' |
| `ip_address` | INET | Who performed the action | NULLABLE |
| `user_agent` | TEXT | Device/browser info | NULLABLE |

---

## **2. Payment Hierarchy & Distribution**

### **New Tables Required:**

#### **2.1 PayoutRequest**
| Field              | Type          | Description                                                  |
| ------------------ | ------------- | ------------------------------------------------------------ |
| id                 | UUID          |                                                              |
| created_at         | DateTime      |                                                              |
| updated_at         | DateTime      |                                                              |
| requested_by       | FK to Partner | Franchise or Vendor                                          |
| amount             | DecimalField  | Requested amount                                             |
| status             | CharField     | PENDING, PROCESSED, REJECTED                                 |
| processed_by       | FK to User    | Admin who processed                                          |
| processed_at       | DateTime      |                                                              |
| vat_deducted       | DecimalField  | VAT amount deducted                                          |
| service_charge     | DecimalField  | Service charge deducted                                      |
| net_amount         | DecimalField  | Amount after deductions                                      |
| payout_type        | CharField     | CHARGE_GHAR_TO_FRANCHISE, CHARGE_GHAR_TO_VENDOR, FRANCHISE_TO_SUBVENDOR |
| internal_reference | CharField     | For tracing                                                  |

#### **2.2 RevenueDistribution**
| Field              | Type              | Description                  |
| ------------------ | ----------------- | ---------------------------- |
| id                 | UUID              |                              |
| created_at         | DateTime          |                              |
| updated_at         | DateTime          |                              |
| transaction        | FK to Transaction | Linked rental/ad transaction |
| franchise          | FK to Franchise   | If applicable                |
| vendor             | FK to Vendor      | If applicable                |
| chargeghar_share   | DecimalField      |                              |
| partner_share      | DecimalField      |                              |
| distributed_at     | DateTime          |                              |
| distribution_level | CharField         | CHARGE_GHAR, FRANCHISE       |

---

## **3. Advertisement Workflow**

### **New Tables Required:**

-- Advertisement Request Table
CREATE TABLE adsRequest (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration_days INTEGER NOT NULL,
    budget DECIMAL(15,2) NOT NULL,
    status ENUM('draft', 'submitted', 'under_review', 'approved', 'rejected', 'paid', 'running', 'completed', 'cancelled') DEFAULT 'draft',
    submitted_at TIMESTAMP NULL,
    reviewed_at TIMESTAMP NULL,
    reviewed_by UUID REFERENCES users(id),
    approved_at TIMESTAMP NULL,
    approved_by UUID REFERENCES users(id),
    admin_price DECIMAL(15,2) NULL,
    admin_notes TEXT,
    payment_intent_id UUID REFERENCES payment_intent(id),
    transaction_id UUID REFERENCES transaction(id)
);

-- Advertisement Content Table
CREATE TABLE advertisement_content (
    id UUID PRIMARY KEY,
    ad_request_id UUID NOT NULL REFERENCES advertisement_request(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_type ENUM('image', 'video') NOT NULL,
    MediaUpload_id CHAR NOT NULL,
    duration_seconds INTEGER DEFAULT 5,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON
);

-- Ad Distribution Table (For IoT Devices)
CREATE TABLE ad_distribution (
    id UUID PRIMARY KEY,
    ad_request_id UUID NOT NULL REFERENCES advertisement_request(id),
    station_id UUID NOT NULL REFERENCES station(id),
    device_uuid VARCHAR(100) NOT NULL,
    distributed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ad_content_id UUID NOT NULL REFERENCES advertisement_content(id),
    play_count INTEGER DEFAULT 0,
    last_played_at TIMESTAMP NULL
);

---


## 4. Station Coupons (M2M Junction)

### 4.1 CouponStation Model

**App**: `api/user/promotions/`  
**Table**: `coupon_stations`

```python
class CouponStation(BaseModel):
    """
    Junction table for station-specific coupons
    If coupon has no CouponStation entries → Global coupon (all stations)
    If coupon has CouponStation entries → Only valid at those stations
    """
    coupon = models.ForeignKey('Coupon', on_delete=models.CASCADE, related_name='station_restrictions')
    station = models.ForeignKey('stations.Station', on_delete=models.CASCADE, related_name='coupon_restrictions')
    
    class Meta:
        unique_together = ['coupon', 'station']
        db_table = 'coupon_stations'
```

**Logic**:
- `Coupon.station_restrictions.exists()` → Station-specific
- `not Coupon.station_restrictions.exists()` → Global

Note:
```
ALTER TABLE coupon
ADD COLUMN is_station_specific BOOLEAN DEFAULT FALSE;

ALTER TABLE coupon_usage
ADD COLUMN station_id UUID REFERENCES station(id);
```

### 4.1 StationPackageDiscount Model

**App**: `api/user/rentals/`  
**Table**: `station_package_discounts`

```python
class StationPackageDiscount(BaseModel):
    """
    Station-specific discounts on rental packages
    One station can have different discounts for different packages
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('EXPIRED', 'Expired'),
    ]
    
    station = models.ForeignKey('stations.Station', on_delete=models.CASCADE, related_name='package_discounts')
    package = models.ForeignKey('RentalPackage', on_delete=models.CASCADE, related_name='station_discounts')
    
    # Discount Configuration
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 10.00 = 10%
    
    # Usage Limits
    max_total_uses = models.IntegerField(null=True, blank=True)  # NULL = unlimited
    max_uses_per_user = models.IntegerField(default=1)
    current_usage_count = models.IntegerField(default=0)
    
    # Validity Period
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    class Meta:
        unique_together = ['station', 'package']  # One discount per station-package pair
        db_table = 'station_package_discounts'
```

### 4.2 StationPackageDiscountUsage Model

**Table**: `station_package_discount_usages`

```python
class StationPackageDiscountUsage(BaseModel):
    """
    Track usage of station package discounts per user
    """
    discount = models.ForeignKey('StationPackageDiscount', on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='package_discount_usages')
    rental = models.ForeignKey('Rental', on_delete=models.CASCADE)
    
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'station_package_discount_usages'
```

---

## 5. Biometric Authentication
Note:
```
UserDevice: Add CharField biometric_token (nullable) – For enable/login.
```

## **5. IoT & Internal App Updates**

### **New Tables Required:**

#### **5.1 IotSyncLog**
| Field      | Type          | Description                 |
| ---------- | ------------- | --------------------------- |
| id         | UUID          |                             |
| created_at | DateTime      |                             |
| station    | FK to Station |                             |
| sync_type  | CharField     | STATUS, ADS, DATA |
| payload    | JSONField     |                             |
| response   | JSONField     |                             |
| status     | CharField     | SUCCESS, FAILED             |


## **6. Rental Lifecycle Enhancements**

#### **6.1 Add to Rental Model:**
- `return_battery_level` → IntegerField (0-100)
- `is_under_5_min` → BooleanField (True if returned <5 min)
- `cycle_count` → DecimalField (incremented based on discharge)
- `hardware_issue_reported` → BooleanField

#### **6.2 New Table: BatteryCycleLog**
| Field             | Type            | Description                 |
| ----------------- | --------------- | --------------------------- |
| id                | UUID            |                             |
| created_at        | DateTime        |                             |
| powerbank         | FK to PowerBank |                             |
| rental            | FK to Rental    |                             |
| discharge_percent | DecimalField    | e.g., 100 → 30 = 0.7 cycles |
| cumulative_cycles | DecimalField    | Total cycles for this bank  |
