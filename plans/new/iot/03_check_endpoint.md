# Endpoint Plan: POST `/api/internal/iot/check`

> Status: Planned  
> Priority: High

---

## 1. Goal

Expose station hardware/slot health check for authorized partners and log every invocation.

---

## 2. Device Mapping (Verified)

- `libs/chargeghar_client/device.py` supports:
  - `check` (occupied slots)
  - `check_all` (all slots including empty)

Plan default: use `check_all` for complete operational visibility.

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)
- `include_empty` (bool, optional, default `true`)

### Success Response

- `station_id`
- `station_imei`
- `action_type='CHECK'`
- `slots` (normalized list)
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + CanPerformIotAction`.
2. Set `iot_action = 'CHECK'`.
3. Enforce object-level station permission before command execution.

---

## 5. Service Flow

1. Resolve station and validate partner station access.
2. Use `station.imei` for device call.
3. Call:
   - `check_station_all()` if `include_empty=true`
   - `check_station()` if `include_empty=false`
4. Map typed `Powerbank` results to API schema.
5. Log to `partner_iot_history` with `action_type='CHECK'`.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py`
2. `api/partners/common/services/partner_iot_service.py`
3. `api/partners/common/views/` (new check view)
4. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Authorized partner can retrieve slot status.
2. Unauthorized station access is blocked.
3. Empty-slot behavior follows `include_empty` flag.
4. Success and failure both write history rows.
