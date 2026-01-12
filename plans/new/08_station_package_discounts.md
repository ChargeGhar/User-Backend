# Feature: Station Package Discounts

**App**: `api/user/rentals/`  
**Priority**: Phase 2

---

## Tables

### 8.1 StationPackageDiscount

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `updated_at` | DateTimeField | | auto_now |
| `station` | ForeignKey(Station) | Station | NOT NULL, on_delete=CASCADE |
| `package` | ForeignKey(RentalPackage) | Package | NOT NULL, on_delete=CASCADE |
| `discount_percent` | DecimalField(5,2) | Discount % (e.g., 10.00 = 10%) | NOT NULL, CHECK 0-100 |
| `max_total_uses` | IntegerField | Total usage limit | NULL (unlimited) |
| `max_uses_per_user` | IntegerField | Per-user limit | NOT NULL, default=1 |
| `current_usage_count` | IntegerField | Current total uses | NOT NULL, default=0 |
| `valid_from` | DateTimeField | Start validity | NOT NULL |
| `valid_until` | DateTimeField | End validity | NOT NULL |
| `status` | CharField(20) | Status | NOT NULL, default='ACTIVE' |
| `created_by` | ForeignKey(User) | Admin who created | NULL, on_delete=SET_NULL |

**Status Choices**:
```python
STATUS_CHOICES = [
    ('ACTIVE', 'Active'),
    ('INACTIVE', 'Inactive'),
    ('EXPIRED', 'Expired'),
]
```

**Constraint**: `unique_together = ['station', 'package']` (one discount per station-package pair)

---

### 8.2 StationPackageDiscountUsage

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `discount` | ForeignKey(StationPackageDiscount) | Discount used | NOT NULL, on_delete=CASCADE |
| `user` | ForeignKey(User) | User who used | NOT NULL, on_delete=CASCADE |
| `rental` | ForeignKey(Rental) | Rental where used | NOT NULL, on_delete=CASCADE |
| `original_price` | DecimalField(10,2) | Original package price | NOT NULL |
| `discount_amount` | DecimalField(10,2) | Amount discounted | NOT NULL |
| `final_price` | DecimalField(10,2) | Price after discount | NOT NULL |

---

## Business Logic Notes

### Discount Validation

```python
def get_station_package_discount(station_sn, package_id, user):
    """Get applicable discount for station-package combination"""
    now = timezone.now()
    
    try:
        discount = StationPackageDiscount.objects.get(
            station__serial_number=station_sn,
            package_id=package_id,
            status='ACTIVE',
            valid_from__lte=now,
            valid_until__gte=now
        )
    except StationPackageDiscount.DoesNotExist:
        return None
    
    # Check total usage limit
    if discount.max_total_uses and discount.current_usage_count >= discount.max_total_uses:
        return None
    
    # Check per-user limit
    user_usage = StationPackageDiscountUsage.objects.filter(
        discount=discount,
        user=user
    ).count()
    if user_usage >= discount.max_uses_per_user:
        return None
    
    return discount


def apply_discount(discount, package, user, rental):
    """Apply discount and record usage"""
    original_price = package.price
    discount_amount = original_price * (discount.discount_percent / 100)
    final_price = original_price - discount_amount
    
    # Record usage
    StationPackageDiscountUsage.objects.create(
        discount=discount,
        user=user,
        rental=rental,
        original_price=original_price,
        discount_amount=discount_amount,
        final_price=final_price
    )
    
    # Update usage count
    discount.current_usage_count += 1
    discount.save(update_fields=['current_usage_count'])
    
    return final_price
```

### API Updates Required

1. **`GET /api/rentals/packages`**:
   - Add `station_sn` query parameter
   - Return discounted prices if applicable
   - Response includes `original_price`, `discount_percent`, `final_price`

2. **`POST /api/rentals/start`**:
   - Check for station package discount
   - Apply discount to rental amount
   - Record usage

---

## Indexes

```python
# StationPackageDiscount
class Meta:
    db_table = 'station_package_discounts'
    unique_together = ['station', 'package']
    indexes = [
        models.Index(fields=['station', 'status']),
        models.Index(fields=['valid_from', 'valid_until']),
    ]

# StationPackageDiscountUsage
class Meta:
    db_table = 'station_package_discount_usages'
    indexes = [
        models.Index(fields=['discount', 'user']),
        models.Index(fields=['rental']),
    ]
```

---

## Constraints

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(discount_percent__gte=0, discount_percent__lte=100),
            name='discount_percent_range'
        ),
    ]
```
