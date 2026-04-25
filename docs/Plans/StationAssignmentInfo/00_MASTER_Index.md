# Master Plan: Station Assignment Info Enrichment

## Context
Super Admin needs visibility into which partner (franchise/vendor) is assigned to each station across the entire system. Currently, admin and partner endpoints return station data without assignment metadata. This plan adds `isAssigned` and `assignedPartner` fields to the four primary station read endpoints.

## Plan Files
| # | File | Purpose |
|---|------|---------|
| 1 | [`01_Scope_Response_Enrichment.md`](01_Scope_Response_Enrichment.md) | Field spec, endpoint mapping, business rules |
| 2 | [`02_Scope_Backend_Implementation.md`](02_Scope_Backend_Implementation.md) | Exact code changes per file, step-by-step |
| 3 | [`03_Scope_Testing_Verification.md`](03_Scope_Testing_Verification.md) | Unit tests, manual checks, regression guards |
| 4 | [`04_Scope_Execution_Order.md`](04_Scope_Execution_Order.md) | Phase-by-phase execution order with validation gates |

## Principles
- **No assumptions** – every change is grounded in existing models (`Partner`, `StationDistribution`).
- **No out-of-boundary** – only the four listed GET endpoints are modified.
- **No inconsistency** – one repository method drives `assignedPartner` resolution everywhere.
- **No duplication** – a single module-level helper (`_get_assigned_partner_info`) is reused by admin and partner services.

## Quick Reference
| Endpoint | Who Calls | What Gets Added |
|----------|-----------|-----------------|
| `GET /api/admin/stations` | Super Admin / Admin | `isAssigned` + `assignedPartner` per result item |
| `GET /api/admin/stations/{sn}` | Super Admin / Admin | `isAssigned` + `assignedPartner` at top level |
| `GET /api/partner/stations` | Franchise / Vendor | `isAssigned` + `assignedPartner` per result item |
| `GET /api/partner/stations/{id}` | Franchise / Vendor | `isAssigned` + `assignedPartner` at top level |

## Status
- [ ] Scope 1 approved
- [ ] Scope 2 implemented
- [ ] Scope 3 verified
