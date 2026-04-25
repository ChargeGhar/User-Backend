# Scope 1 – Response Enrichment: isAssigned + assignedPartner

## Goal
Add `isAssigned` (boolean) and `assignedPartner` (object) to every station returned by the four listed endpoints so the caller knows whether the station is assigned to a partner and, if so, who that partner is.

## Endpoints
| # | Method | Path | View | Serializer / Service Return |
|---|--------|------|------|----------------------------|
| 1 | GET | `/api/admin/stations` | `AdminStationListView` | `AdminStationSerializer` (list) |
| 2 | GET | `/api/admin/stations/<str:station_sn>` | `AdminStationDetailView` | `AdminStationDetailSerializer` |
| 3 | GET | `/api/partner/stations` | `PartnerStationListView` | `PartnerStationService.get_stations_list()` |
| 4 | GET | `/api/partner/stations/<uuid:station_id>` | `PartnerStationDetailView` | `PartnerStationService.get_station_detail()` |

## Field Specification
```json
{
  "isAssigned": true,
  "assignedPartner": {
    "id": "uuid",
    "businessName": "string",
    "partnerType": "FRANCHISE | VENDOR",
    "vendorType": "REVENUE | NON_REVENUE | null",
    "status": "ACTIVE | INACTIVE | SUSPENDED"
  }
}
```
- `isAssigned` – `true` when at least one `StationDistribution` row for this station has `is_active=true`.
- `assignedPartner` – `null` when `isAssigned` is `false`.
- `vendorType` is included only when `partnerType == "VENDOR"`; otherwise `null`.

## Business Rule – Which Partner Is Returned?
A station may have multiple active distributions (e.g. `CHARGEGHAR_TO_FRANCHISE` **and** `FRANCHISE_TO_VENDOR`). To avoid ambiguity, the following priority is used **everywhere**:
1. `FRANCHISE_TO_VENDOR` (the operating vendor)
2. `CHARGEGHAR_TO_FRANCHISE` (the owning franchise)
3. `CHARGEGHAR_TO_VENDOR` (a direct vendor under ChargeGhar)

This means:
- **Admin endpoints** – show the downstream operator (vendor if one exists, else franchise, else direct vendor).
- **Franchise partner endpoints** – show the vendor assigned by this franchise (`FRANCHISE_TO_VENDOR`).
- **Vendor partner endpoints** – show the franchise they work under (`FRANCHISE_TO_VENDOR` from the franchise side, i.e. the vendor’s parent). If the vendor is direct under ChargeGhar (`CHARGEGHAR_TO_VENDOR`), the vendor itself is shown.

## Consistency Rules
- No duplication: the same helper must compute `assignedPartner` for **all four** endpoints.
- No inconsistency: the priority rule above is the single source of truth.
- No assumptions: all partner data is read from the existing `Partner` model via the existing `StationDistribution` model.
