# Endpoint Plan: POST `/api/internal/iot/eject`

> Status: Planned  
> Priority: High  
> Constraint: Franchise-only dashboard action (BR13)

---

## 1. Goal

Implement franchise-controlled remote ejection with strict permission boundaries and accurate slot-powerbank targeting.

---

## 2. Current Gap (Verified)

`api/partners/common/services/partner_iot_service.py` eject flow is stale and not runnable as-is:

1. imports non-existent `Slot` model (actual is `StationSlot`)
2. calls missing `PowerBankService.eject_powerbank`
3. uses repository method name that does not exist

This endpoint requires a clean replacement flow.

---

## 3. Request/Response Contract

### Request Body

- `station_id` (UUID, required)
- `slot_number` (integer, required, `>=1`)
- `reason` (string, optional)

### Success Response

- `station_id`
- `station_imei`
- `slot_number`
- `powerbank_serial`
- `action_type='EJECT'`
- `is_successful`
- `message`
- `iot_history_id`

---

## 4. Permission and Access

1. View uses `IsAuthenticated + IsFranchise + CanPerformIotAction`.
2. Set `iot_action = 'EJECT'`.
3. Enforce object-level station permission before ejection.
4. Vendors must always receive permission denial for this endpoint.

---

## 5. Service Flow

1. Resolve station by `station_id` under franchise visibility rules.
2. Resolve slot with `StationSlot.objects.get(station=station, slot_number=...)`.
3. Resolve powerbank from slot (`PowerBank.current_slot == slot`).
4. Call `DeviceAPIService.popup_specific(station.imei, powerbank.serial_number)`.
5. Log action in `partner_iot_history`:
   - `action_type='EJECT'`
   - `powerbank_sn`, `slot_number`
   - `is_free_ejection=False` (dashboard eject is not vendor free ejection flow)
6. Return normalized response.

No direct slot/powerbank state mutation in this endpoint; rely on inbound IoT sync to update physical state.

---

## 6. Files to Change

1. `api/partners/common/serializers/iot_serializers.py`
2. `api/partners/common/services/partner_iot_service.py` (replace stale eject logic)
3. `api/partners/common/views/` (new eject view)
4. `api/partners/common/urls.py`

---

## 7. Validation Checklist

1. Franchise can eject from authorized station and slot.
2. Vendor gets forbidden response.
3. Missing slot returns controlled `slot_not_found`.
4. Empty slot returns controlled `no_powerbank_in_slot`.
5. Command uses `station.imei` consistently.
6. Failed ejection still writes history with error details.
