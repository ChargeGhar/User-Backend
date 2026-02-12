# IoT Shared Endpoints - Foundation Plan

> Version: 1.0  
> Created: 2026-02-12  
> Scope: `## 4. IoT Endpoints (Shared)` from `plans/new/Partners/Endpoints.md`

---

## 1. Verified Inputs (No Assumptions)

### 1.1 Planning Docs Reviewed

- `plans/new/Partners/Endpoints.md` (Section 4 IoT endpoints and permission matrix)
- `plans/new/Partners/schema_mapping.md` (Table 6 `partner_iot_history` lifecycle + BR13 notes)
- `plans/new/Partners/Endpoints_status.md` (IoT progress status)
- `plans/new/Partners/Business Rules.md` (BR12 visibility, BR13 control rights)

### 1.2 Existing Code Reviewed

- `libs/chargeghar_client/device.py` (real device operations available)
- `api/user/stations/services/device_api_service.py` (current app wrapper)
- `api/partners/auth/permissions.py` (`CanPerformIotAction`, `IsFranchise`, `HasDashboardAccess`)
- `api/partners/common/views/iot_history_view.py` (existing history endpoint)
- `api/partners/common/services/partner_iot_service.py` (current IoT service)
- `api/partners/common/repositories/partner_iot_history_repository.py`
- `api/partners/common/models/partner_iot_history.py`
- `api/partners/common/urls.py`, `api/web/urls.py` (routing style)

---

## 2. Current State (Verified)

1. Only history endpoint exists now: `GET /api/partner/iot/history`.
2. Spec requires shared IoT path: `/api/internal/iot/*` (7 actions + history).
3. `chargeghar_client` already supports all required hardware calls:
   - check/check_all
   - reboot via `send_command({"cmd":"reboot"})`
   - wifi scan/connect
   - mode set
   - volume set
   - popup specific/random
4. `DeviceAPIService` currently wraps only popup/check/log methods, not reboot/wifi/mode/volume.
5. `PartnerIoTService` has stale/broken logic:
   - imports `Slot` (model is `StationSlot`)
   - calls `get_today_free_ejections_count` (repository method name differs)
   - calls `PowerBankService.eject_powerbank` (method does not exist)

---

## 3. Non-Negotiable Accuracy Rules

1. Station matching for device command must use `Station.imei`, never admin-editable `Station.serial_number`.
2. All IoT actions must write `partner_iot_history` with full audit fields.
3. Object-level station access must be enforced per request, not only by `station_id` presence.
4. Vendor must never be allowed dashboard remote eject (`EJECT`) via IoT action endpoint.
5. WiFi password must not be persisted in plain text in history payload.

---

## 4. Shared Implementation Blueprint

### 4.1 Route Strategy

Implement new endpoints in `api/partners/common` using partner auth and register these routes:

- `internal/iot/history`
- `internal/iot/reboot`
- `internal/iot/check`
- `internal/iot/wifi/scan`
- `internal/iot/wifi/connect`
- `internal/iot/volume`
- `internal/iot/mode`
- `internal/iot/eject`

Keep existing `partner/iot/history` as compatibility alias.

### 4.2 Permission Strategy

1. Action views: `IsAuthenticated + CanPerformIotAction`, with class attribute `iot_action`.
2. Eject view: add `IsFranchise` explicitly.
3. In each action endpoint, resolve station object first and run `self.check_object_permissions(request, station)`.

### 4.3 Service Strategy

Refactor `PartnerIoTService` into action-specific methods:

- `get_iot_history(...)`
- `reboot_station(...)`
- `check_station(...)`
- `wifi_scan(...)`
- `wifi_connect(...)`
- `set_volume(...)`
- `set_mode(...)`
- `eject_powerbank(...)`

Add shared helper methods:

- `_get_station_for_action(partner, station_id)`
- `_log_iot_action(...)`
- `_mask_sensitive_payload(...)`

### 4.4 Device Wrapper Strategy

Extend `api/user/stations/services/device_api_service.py`:

- `reboot_station(station_imei)`
- `wifi_scan(station_imei)`
- `wifi_connect(station_imei, ssid, password)`
- `set_volume(station_imei, volume)`
- `set_mode(station_imei, mode)`

All wrappers must return deterministic tuple pattern:

- `success: bool`
- `data: dict | list | None`
- `message: str`

### 4.5 History Logging Strategy

For all actions:

- `performed_from='DASHBOARD'`
- `partner_id`, `performed_by_id`, `station_id`
- `action_type` mapped to model choices
- `is_successful` from client result
- `error_message` when failed
- `request_payload` (masked)
- `response_data` (normalized)
- `ip_address`, `user_agent`

---

## 5. File-Level Change Map

1. `api/partners/common/views/`  
   add new IoT action views and internal IoT routes.
2. `api/partners/common/serializers/iot_serializers.py`  
   add request/response serializers for reboot/check/wifi/volume/mode/eject.
3. `api/partners/common/services/partner_iot_service.py`  
   replace stale eject logic and implement all actions.
4. `api/partners/common/repositories/partner_iot_history_repository.py`  
   add helper query for franchise-visible history if needed by BR12.
5. `api/partners/common/views/__init__.py` and `api/partners/common/urls.py`  
   include new router exports.
6. `api/user/stations/services/device_api_service.py`  
   add missing wrappers over `chargeghar_client`.

---

## 6. Execution Order

1. Add serializers (contracts first).
2. Add device wrapper methods (integration boundary).
3. Refactor `PartnerIoTService` with shared helper methods.
4. Add/replace endpoint views and route registrations.
5. Keep old history route as alias.
6. Validate permission matrix and action logging completeness.

---

## 7. Conflicts to Resolve During Implementation

1. History visibility wording conflict:
   - `Endpoints.md`: "Own IoT history"
   - `schema_mapping.md` BR12 SQL: franchise can also view child vendor history
2. Route naming conflict:
   - existing implementation path is `/api/partner/iot/history`
   - required path is `/api/internal/iot/history`

Implementation should support both route expectations without breaking existing clients.
