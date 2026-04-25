# Vendor Multi-Station Assignment — Architecture

## Data Model Analysis

### Current Schema (One-to-One Vendor-Station)

```
Partner (1) ──── (*) StationDistribution (*) ──── (1) Station
                      │
                      └── (1) StationRevenueShare
```

- `Partner` → `StationDistribution`: One partner can have multiple distributions (but vendor is limited to 1 by service logic)
- `StationDistribution` → `StationRevenueShare`: One-to-one — each distribution has its own revenue config

### Target Schema (Multi-Station Vendor)

```
Partner (1) ──── (*) StationDistribution (*) ──── (1) Station
                      │
                      └── (1) StationRevenueShare
```

**No schema changes needed.** The `StationDistribution` model already uses `ForeignKey` (not `OneToOneField`). The constraint is purely in service-layer logic.

### Revenue Model Consistency

Since revenue model is **same across all stations for a vendor**, when assigning a new station to an existing vendor:
1. Copy the vendor's existing `StationRevenueShare` config to the new `StationDistribution`
2. All vendor stations share identical `partner_percent` or `fixed_amount`

## Service Layer Changes

### `StationAssignmentService`

| Method | Current | Change |
|--------|---------|--------|
| `assign_station()` | Rejects if vendor already has station | **Remove vendor limit check** — keep station exclusivity check |
| `assign_station()` | Creates one distribution | **Keep** — called once per station |
| `assign_station()` | Creates revenue share per distribution | **Keep** — copy vendor's existing config |
| `get_partner_assignment()` | Returns single distribution | **Update** — return list of all vendor distributions |
| `get_station_assignment()` | Returns single distribution | **Keep** — station still has one operator |

### `StationDistributionRepository`

| Method | Current | Change |
|--------|---------|--------|
| `vendor_has_station()` | Returns `True` if vendor has ≥1 | **Deprecate** or rename to `vendor_station_count()` |
| `station_has_operator()` | Returns `True` if station has operator | **Keep unchanged** |
| `get_active_by_partner()` | Returns QuerySet of distributions | **Keep unchanged** — already supports multiple |
| `get_station_operator()` | Returns first vendor operator | **Keep unchanged** — station has one operator |
| `get_franchise_unassigned_stations()` | Excludes assigned stations | **Keep unchanged** |

## Admin API Changes

### New Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /admin/partners/stations/assign` | POST | Assign one or more stations to an **existing** vendor |

### Modified Endpoints

| Endpoint | Current | Change |
|----------|---------|--------|
| `POST /admin/partners/vendor` | `station_id: str` (single) | `station_ids: list[str]` (multiple) |
| `GET /admin/partners/<partner_id>` | Shows single station | Shows **list of stations** |

### Unchanged Endpoints

| Endpoint | Reason |
|----------|--------|
| `POST /admin/partners/franchise` | Franchises already support multiple stations |
| `GET /admin/partners/stations` | Already lists all distributions |
| `DELETE /admin/partners/stations/<id>` | Deactivates single distribution |
| `GET /admin/partners/stations/available` | Lists unassigned stations |

## Partner Dashboard Changes

### Vendor Dashboard (`api/partners/vendor/`)

| Component | Current | Change |
|-----------|---------|--------|
| Station info | Single station object | **List of station objects** |
| Revenue stats | Single station revenue | **Aggregated across all stations** |
| IoT actions | Single station selector | **Station selector dropdown** |
| Payout requests | Single station earnings | **All stations combined** |

### Franchise Dashboard (`api/partners/franchise/`)

| Component | Current | Change |
|-----------|---------|--------|
| Vendor list | Shows vendor + station | **Shows vendor + station count** |
| Assign vendor | Single station dropdown | **Multi-select stations** |

## Revenue Distribution Changes

### `RevenueDistribution` Model

**No changes.** The model already supports per-transstation, per-station revenue calculation. Each transaction on a vendor-operated station creates one `RevenueDistribution` record with:
- `station` = the specific station
- `vendor` = the vendor partner
- `vendor_share` = calculated from `StationRevenueShare` for that station

### Revenue Calculation Service

**No changes.** The existing `calculate_shares()` logic:
1. Finds `StationDistribution` for the transaction's station
2. Finds `StationRevenueShare` for that distribution
3. Calculates vendor share using `partner_percent` or `fixed_amount`

This works identically whether the vendor has 1 station or 10 stations — each transaction is independent.
