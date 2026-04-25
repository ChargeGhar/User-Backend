# Vendor Multi-Station Assignment — Testing Plan

## Test Scenarios

### 1. Admin Creates Vendor with Multiple Stations

**Precondition:** 3 unassigned stations exist
**Action:** Admin calls `POST /admin/partners/vendor` with `station_ids: [S1, S2, S3]`
**Expected:**
- 3 `StationDistribution` records created (all active)
- 3 `StationRevenueShare` records created with same config
- Vendor detail shows all 3 stations
- Station exclusivity: each station has only this vendor as operator

### 2. Admin Assigns Additional Station to Existing Vendor

**Precondition:** Vendor V1 has stations S1, S2
**Action:** Admin calls `POST /admin/partners/stations/assign` with `vendor_id: V1, station_ids: [S3]`
**Expected:**
- New `StationDistribution` created for S3
- `StationRevenueShare` for S3 matches V1's existing config
- Vendor now has 3 stations
- S3 cannot be assigned to another vendor

### 3. Vendor Dashboard Shows All Stations

**Precondition:** Vendor has stations S1, S2, S3
**Action:** Vendor calls `GET /partners/vendor/dashboard`
**Expected:**
- Response contains `stations` array with 3 items
- Each station has: name, serial, status, revenue, slot count
- Total revenue = sum of revenue from all 3 stations

### 4. Revenue Calculation Per Station

**Precondition:** Vendor V1 has S1 (10%) and S2 (10%)
**Action:** Rentals occur on S1 (NPR 100) and S2 (NPR 200)
**Expected:**
- 2 `RevenueDistribution` records created
- S1: vendor_share = NPR 10
- S2: vendor_share = NPR 20
- Vendor total = NPR 30

### 5. Station Exclusivity Preserved

**Precondition:** Vendor V1 has station S1
**Action:** Admin tries to assign S1 to Vendor V2
**Expected:**
- Request rejected with `station_already_assigned`
- S1 remains assigned to V1

### 6. Franchise Assigns Vendor to Multiple Stations

**Precondition:** Franchise F1 owns S1, S2, S3
**Action:** Franchise assigns Vendor V1 to S1 and S2
**Expected:**
- 2 `StationDistribution` records with type `FRANCHISE_TO_VENDOR`
- V1 can operate S1 and S2
- F1 still owns all 3 stations

### 7. Revenue Model Consistency Enforced

**Precondition:** Vendor V1 has S1 with PERCENTAGE 10%
**Action:** Admin tries to assign S2 with FIXED NPR 5000
**Expected:**
- S2 gets same PERCENTAGE 10% config
- Warning logged: "Revenue model mismatch — copied vendor's existing config"

### 8. Backward Compatibility — Single Station Vendor

**Precondition:** Existing vendor with 1 station (created before change)
**Action:** Vendor dashboard loaded, rental transaction processed
**Expected:**
- Dashboard shows single station
- Revenue calculation works normally
- No errors

### 9. Deactivate One of Multiple Stations

**Precondition:** Vendor V1 has S1, S2, S3
**Action:** Admin deactivates S2 distribution
**Expected:**
- S2 distribution `is_active = False`
- V1 still has S1 and S3
- S2 becomes available for reassignment

### 10. Vendor IoT Actions with Multiple Stations

**Precondition:** Vendor has S1, S2
**Action:** Vendor calls IoT action with `station_id: S1`
**Expected:**
- Action executes on S1
- Validation passes: S1 belongs to vendor
- Vendor can also execute on S2

## API Contract Tests

### Admin API

```
POST /admin/partners/vendor
Request:  { user_id, vendor_type, business_name, contact_phone, station_ids[], revenue_model?, ... }
Response: { success, data: { partner, stations[], revenue_shares[] } }

POST /admin/partners/stations/assign
Request:  { vendor_id, station_ids[] }
Response: { success, data: { distributions[], revenue_shares[] } }

GET /admin/partners/<partner_id>
Response: { success, data: { ..., stations: [{ id, station_name, serial_number, status }] } }
```

### Vendor Dashboard API

```
GET /partners/vendor/dashboard
Response: { success, data: { stations: [...], revenue_stats: { total, by_station: [...] } } }
```

## Regression Checklist

- [ ] Franchise creation still works with multiple stations
- [ ] ChargeGhar direct vendor creation works
- [ ] Revenue distribution for franchise-owned stations works
- [ ] Payout requests calculate correctly
- [ ] Partner list/filtering works
- [ ] Station analytics unaffected
