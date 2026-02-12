# Endpoint Plan: POST `/api/internal/iot/wifi/connect`

> Status: Planned  
> Priority: Medium-High

---

## 1. Goal

Enable authorized partner to send WiFi credentials to station with safe audit logging.

---

## 2. Device Mapping (Verified)

- `libs/chargeghar_client/device.py` provides:
  - `wifi_connect(device_name, ssid, password)`

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)
- `wifi_ssid` (string, required)
- `wifi_password` (string, optional)

### Success Response

- `station_id`
- `station_imei`
- `action_type='WIFI_CONNECT'`
- `message`
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + CanPerformIotAction`.
2. Set `iot_action = 'WIFI_CONNECT'`.
3. Enforce station object permission before execution.

---

## 5. Service Flow

1. Resolve station by `station_id` and partner scope.
2. Use `station.imei` for command.
3. Call `DeviceAPIService.wifi_connect(station.imei, wifi_ssid, wifi_password)`.
4. Log action with masked payload:
   - store `wifi_ssid`
   - store `wifi_password='***'` (never raw value)
5. Persist response metadata and return normalized response.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py`
2. `api/user/stations/services/device_api_service.py` (wifi connect wrapper)
3. `api/partners/common/services/partner_iot_service.py`
4. `api/partners/common/views/` (new wifi connect view)
5. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. SSID validation rejects blank values.
2. Password is masked in logged `request_payload`.
3. Command uses `imei`, not station serial label.
4. Failed command still writes history row with error details.
