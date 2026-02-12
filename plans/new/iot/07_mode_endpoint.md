# Endpoint Plan: POST `/api/internal/iot/mode`

> Status: Planned  
> Priority: Medium

---

## 1. Goal

Allow authorized partner to switch station network mode (`wifi` or `4g`) with full audit trace.

---

## 2. Device Mapping (Verified)

- `libs/chargeghar_client/device.py` provides `set_network_mode(device_name, mode)`.
- Accepted mode values are exactly `wifi` and `4g`.

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)
- `mode` (string enum: `wifi`, `4g`)

### Success Response

- `station_id`
- `station_imei`
- `action_type='MODE'`
- `mode`
- `message`
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + CanPerformIotAction`.
2. Set `iot_action = 'MODE'`.
3. Enforce station object permission before command.

---

## 5. Service Flow

1. Validate request (`mode` in allowed enum).
2. Resolve authorized station.
3. Call `DeviceAPIService.set_mode(station.imei, mode)`.
4. Log history with `action_type='MODE'`.
5. Return normalized response payload.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py`
2. `api/user/stations/services/device_api_service.py` (mode wrapper)
3. `api/partners/common/services/partner_iot_service.py`
4. `api/partners/common/views/` (new mode view)
5. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Invalid mode string rejected by serializer.
2. Vendor/franchise allowed for assigned station only.
3. History entry includes selected mode and outcome.
