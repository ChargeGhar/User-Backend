# Endpoint Plan: POST `/api/internal/iot/wifi/scan`

> Status: Planned  
> Priority: Medium-High

---

## 1. Goal

Allow authorized partners to request WiFi network scan on their station and track action logs.

---

## 2. Device Mapping (Verified)

- `libs/chargeghar_client/device.py` provides `wifi_scan(device_name)`.
- Typed helper returns list of SSIDs.

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)

### Success Response

- `station_id`
- `station_imei`
- `action_type='WIFI_SCAN'`
- `networks` (list of SSID strings)
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + CanPerformIotAction`.
2. Set `iot_action = 'WIFI_SCAN'`.
3. Enforce station object permission before execution.

---

## 5. Service Flow

1. Resolve station with partner visibility checks.
2. Call `DeviceAPIService.wifi_scan(station.imei)`.
3. Normalize result list.
4. Log to `partner_iot_history` with `action_type='WIFI_SCAN'`.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py`
2. `api/user/stations/services/device_api_service.py` (wifi scan wrapper)
3. `api/partners/common/services/partner_iot_service.py`
4. `api/partners/common/views/` (new wifi scan view)
5. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Partner can scan on assigned station.
2. Scan fails cleanly when station/device offline.
3. History persists both success and failure results.
