# Feature: Station-Specific Coupons

**App**: `api/user/promotions/`  
**Priority**: Phase 2

---

## Tables

### 7.1 CouponStation (New Junction Table)

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | UUIDField | Primary key | PK, default=uuid4 |
| `created_at` | DateTimeField | | auto_now_add |
| `coupon` | ForeignKey(Coupon) | Coupon | NOT NULL, on_delete=CASCADE |
| `station` | ForeignKey(Station) | Station | NOT NULL, on_delete=CASCADE |

**Constraint**: `unique_together = ['coupon', 'station']`

---

### 7.2 Coupon Model Updates

| Field | Type | Description | Action |
|-------|------|-------------|--------|
| `is_station_specific` | BooleanField | Whether coupon is station-specific | ADD, default=False |

---

### 7.3 CouponUsage Model Updates

| Field | Type | Description | Action |
|-------|------|-------------|--------|
| `station` | ForeignKey(Station) | Station where used | ADD, NULL, on_delete=SET_NULL |

---

## Business Logic Notes

### Coupon Validation Logic

```python
def validate_coupon(coupon_code, station_sn, user):
    coupon = Coupon.objects.get(code=coupon_code)
    
    # Check if station-specific
    if coupon.is_station_specific:
        station = Station.objects.get(serial_number=station_sn)
        if not CouponStation.objects.filter(coupon=coupon, station=station).exists():
            raise ValidationError("Coupon not valid for this station")
    
    # Check usage limits
    usage_count = CouponUsage.objects.filter(coupon=coupon, user=user).count()
    if usage_count >= coupon.max_uses_per_user:
        raise ValidationError("Coupon usage limit reached")
    
    # Check validity period
    now = timezone.now()
    if now < coupon.valid_from or now > coupon.valid_until:
        raise ValidationError("Coupon expired or not yet valid")
    
    return coupon
```

### API Updates Required

1. **`POST /api/promotions/coupons/apply`**:
   - Add `station_sn` parameter
   - Validate coupon against station

2. **`GET /api/promotions/coupons/active`**:
   - Add `station_sn` query parameter
   - Filter coupons valid for that station

---

## Indexes

```python
class Meta:
    db_table = 'coupon_stations'
    unique_together = ['coupon', 'station']
    indexes = [
        models.Index(fields=['station']),
    ]
```

---

## Migration Notes

```python
# Migration 1: Add is_station_specific to Coupon
operations = [
    migrations.AddField(
        model_name='coupon',
        name='is_station_specific',
        field=models.BooleanField(default=False),
    ),
]

# Migration 2: Create CouponStation
operations = [
    migrations.CreateModel(
        name='CouponStation',
        fields=[...],
    ),
]

# Migration 3: Add station to CouponUsage
operations = [
    migrations.AddField(
        model_name='couponusage',
        name='station',
        field=models.ForeignKey(null=True, blank=True, ...),
    ),
]
```
