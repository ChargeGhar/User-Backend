# Endpoint Plan: POST `/api/internal/iot/reboot`

> Status: Planned  
> Priority: High

---

## 1. Goal

Allow partner-controlled station reboot with strict access checks and full IoT audit logging.

---

## 2. Device Mapping (Verified)

- `libs/chargeghar_client/device.py` has no direct reboot method.
- Reboot is supported via `send_command(device_name, '{"cmd":"reboot"}')`.

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)

### Success Response

- `station_id`
- `station_imei`
- `action_type='REBOOT'`
- `is_successful`
- `message`
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + CanPerformIotAction`.
2. Set `iot_action = 'REBOOT'` on the view class.
3. Resolve station object and call `check_object_permissions` before device call.

---

## 5. Service Flow

1. Resolve station by `station_id` and partner scope.
2. Use `station.imei` as command target.
3. Call `DeviceAPIService.reboot_station(station.imei)`.
4. Persist history row (`action_type='REBOOT'`, `performed_from='DASHBOARD'`).
5. Return normalized API payload.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py` (request/response serializer)
2. `api/user/stations/services/device_api_service.py` (new reboot wrapper)
3. `api/partners/common/services/partner_iot_service.py`
4. `api/partners/common/views/` (new reboot view + route export)
5. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Franchise reboot success path logs history.
2. Vendor reboot success path logs history.
3. Vendor cannot reboot unassigned station.
4. DB logs failed attempts with `is_successful=False` and `error_message`.
5. Action uses `imei` even when `serial_number` differs.
