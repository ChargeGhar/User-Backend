# Endpoint Plan: GET `/api/internal/iot/history`

> Status: Planned  
> Priority: High (shared base path alignment)

---

## 1. Goal

Provide partner IoT action history at the shared path while keeping current behavior stable.

---

## 2. Current State (Verified)

1. Existing route: `GET /api/partner/iot/history` in `api/partners/common/views/iot_history_view.py`.
2. Existing permission: `HasDashboardAccess`.
3. Existing service returns only `partner_id == current_partner.id`.
4. Required shared route in planning docs: `GET /api/internal/iot/history`.

---

## 3. Contract

### Request Query Params

- `action_type` (optional)
- `start_date` (optional, `YYYY-MM-DD`)
- `end_date` (optional, `YYYY-MM-DD`)
- `page` (default `1`)
- `page_size` (default `20`)

### Response

- Paginated list of `PartnerIotHistory` records with existing serializer fields.

---

## 4. Permissions and Visibility

1. Use `IsAuthenticated + IsActivePartner` for shared endpoint.
2. Visibility rule:
   - Vendor: own history only.
   - Franchise: own history and optionally child-vendor history based on BR12 mapping.
3. Keep current `partner/iot/history` route as backward-compatible alias.

---

## 5. Implementation Steps

1. Add route registration for `internal/iot/history` in partner common router.
2. Reuse existing view logic but call an updated service method that applies visibility rules.
3. Update repository with a helper query for "visible history by partner role".
4. Keep response shape unchanged to avoid client breakage.

---

## 6. Files to Change

1. `api/partners/common/views/iot_history_view.py`
2. `api/partners/common/services/partner_iot_service.py`
3. `api/partners/common/repositories/partner_iot_history_repository.py`
4. `api/partners/common/views/__init__.py`
5. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Revenue vendor sees only own records.
2. Franchise sees expected scoped records.
3. Non-partner or inactive partner is rejected.
4. Existing route `/api/partner/iot/history` still works.
5. New route `/api/internal/iot/history` returns same schema and pagination keys.
