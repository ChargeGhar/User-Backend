# Endpoint Plan: POST `/api/internal/iot/volume`

> Status: Planned  
> Priority: Medium

---

## 1. Goal

Allow authorized partner to set station speaker volume with strict validation and audit logging.

---

## 2. Device Mapping (Verified)

- `libs/chargeghar_client/device.py` provides `set_volume(device_name, volume)`.
- Valid range enforced client-side: `0..100`.

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)
- `volume` (integer, required, `0 <= volume <= 100`)

### Success Response

- `station_id`
- `station_imei`
- `action_type='VOLUME'`
- `volume`
- `message`
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + CanPerformIotAction`.
2. Set `iot_action = 'VOLUME'`.
3. Enforce object-level station permission.

---

## 5. Service Flow

1. Validate request payload.
2. Resolve authorized station.
3. Call `DeviceAPIService.set_volume(station.imei, volume)`.
4. Log `action_type='VOLUME'` in history with request/response metadata.
5. Return normalized response.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py`
2. `api/user/stations/services/device_api_service.py` (volume wrapper)
3. `api/partners/common/services/partner_iot_service.py`
4. `api/partners/common/views/` (new volume view)
5. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Out-of-range volume is rejected at serializer level.
2. Valid call logs success in `partner_iot_history`.
3. Device/API failure logs error with `is_successful=False`.
