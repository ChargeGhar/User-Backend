"""
Internal IoT action service for partner-triggered station commands.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from api.common.services.base import BaseService, ServiceException
from api.partners.common.models import PartnerIotHistory
from api.partners.common.repositories import PartnerIotHistoryRepository
from api.user.stations.models import PowerBank, Station
from api.user.stations.services import get_device_api_service


class InternalIoTActionService(BaseService):
    """Service layer for shared IoT endpoints under /api/internal/iot/*"""

    def __init__(self):
        super().__init__()
        self.device_service = get_device_api_service()

    def reboot_station(
        self,
        partner,
        performed_by,
        station: Station,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Send reboot command and log history."""
        action_type = PartnerIotHistory.ActionType.REBOOT
        request_payload: Dict[str, Any] = {}

        success, response_data, message = self.device_service.reboot_station(station.imei)
        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_data,
            is_successful=success,
            error_message=None if success else message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(detail=message, code='reboot_failed')

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'action_type': action_type,
            'is_successful': True,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def check_station(
        self,
        partner,
        performed_by,
        station: Station,
        check_all: bool,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Check station status and log history."""
        action_type = PartnerIotHistory.ActionType.CHECK
        request_payload = {'check_all': check_all}

        if check_all:
            success, powerbanks, message = self.device_service.check_station_all(station.imei)
        else:
            success, powerbanks, message = self.device_service.check_station(station.imei)

        slots_data = self._serialize_value(powerbanks)
        response_payload = {'slots': slots_data, 'message': message}

        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_payload,
            is_successful=success,
            error_message=None if success else message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(detail=message, code='check_failed')

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'action_type': action_type,
            'slots': slots_data,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def wifi_scan(
        self,
        partner,
        performed_by,
        station: Station,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Scan WiFi networks and log history."""
        action_type = PartnerIotHistory.ActionType.WIFI_SCAN
        request_payload: Dict[str, Any] = {}

        success, networks, message = self.device_service.wifi_scan(station.imei)
        response_payload = {'networks': networks, 'message': message}

        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_payload,
            is_successful=success,
            error_message=None if success else message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(detail=message, code='wifi_scan_failed')

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'action_type': action_type,
            'networks': networks,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def wifi_connect(
        self,
        partner,
        performed_by,
        station: Station,
        ssid: str,
        password: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Send WiFi connect command and log history."""
        action_type = PartnerIotHistory.ActionType.WIFI_CONNECT
        request_payload = self._mask_sensitive_payload(
            {'wifi_ssid': ssid, 'wifi_password': password}
        )

        success, response_data, message = self.device_service.wifi_connect(
            station.imei,
            ssid,
            password,
        )
        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_data,
            is_successful=success,
            error_message=None if success else message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(detail=message, code='wifi_connect_failed')

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'action_type': action_type,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def set_volume(
        self,
        partner,
        performed_by,
        station: Station,
        volume: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Set station volume and log history."""
        action_type = PartnerIotHistory.ActionType.VOLUME
        request_payload = {'volume': volume}

        success, response_data, message = self.device_service.set_volume(station.imei, volume)
        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_data,
            is_successful=success,
            error_message=None if success else message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(detail=message, code='set_volume_failed')

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'action_type': action_type,
            'volume': volume,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def set_mode(
        self,
        partner,
        performed_by,
        station: Station,
        mode: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Set station network mode and log history."""
        action_type = PartnerIotHistory.ActionType.MODE
        request_payload = {'mode': mode}

        success, response_data, message = self.device_service.set_mode(station.imei, mode)
        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_data,
            is_successful=success,
            error_message=None if success else message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(detail=message, code='set_mode_failed')

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'action_type': action_type,
            'mode': mode,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def eject_powerbank(
        self,
        partner,
        performed_by,
        station: Station,
        powerbank_sn: Optional[str],
        reason: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> Dict[str, Any]:
        """Eject a powerbank (specific by SN or random) and log history."""
        action_type = PartnerIotHistory.ActionType.EJECT
        requested_powerbank_sn = (powerbank_sn or '').strip() or None
        use_random_popup = not bool(requested_powerbank_sn)

        request_payload = {
            'powerbank_sn': requested_powerbank_sn,
            'random_popup': use_random_popup,
            'reason': reason or '',
        }

        # Slot in response/history should come from actual eject result or DB mapping only.
        resolved_slot_number = None
        resolved_powerbank_sn = requested_powerbank_sn

        if use_random_popup:
            success, random_powerbank_sn, message = self.device_service.popup_random(station.imei)
            response_payload = {'powerbank_sn': random_powerbank_sn}
            resolved_powerbank_sn = random_powerbank_sn

            if random_powerbank_sn:
                matched_powerbank = PowerBank.objects.select_related('current_slot').filter(
                    serial_number=str(random_powerbank_sn)
                ).first()
                if (
                    matched_powerbank
                    and matched_powerbank.current_slot
                    and matched_powerbank.current_slot.station_id == station.id
                ):
                    resolved_slot_number = matched_powerbank.current_slot.slot_number
        else:
            success, popup_result, message = self.device_service.popup_specific(
                station.imei,
                requested_powerbank_sn,
            )
            response_payload = self._serialize_value(popup_result)

            popup_slot = getattr(popup_result, 'slot', None) if popup_result else None
            popup_powerbank_sn = (
                getattr(popup_result, 'powerbank_sn', None) if popup_result else None
            )
            if popup_slot:
                resolved_slot_number = popup_slot
            if popup_powerbank_sn:
                resolved_powerbank_sn = popup_powerbank_sn

        history = self._log_action(
            partner=partner,
            performed_by=performed_by,
            station=station,
            action_type=action_type,
            request_payload=request_payload,
            response_data=response_payload,
            is_successful=success,
            error_message=None if success else message,
            powerbank_sn=resolved_powerbank_sn,
            slot_number=resolved_slot_number,
            is_free_ejection=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if not success:
            raise ServiceException(
                detail=message,
                code='eject_failed',
                context={'iot_history_id': str(history.id)},
            )

        return {
            'station_id': str(station.id),
            'station_imei': station.imei,
            'slot_number': resolved_slot_number,
            'powerbank_serial': resolved_powerbank_sn,
            'random_popup': use_random_popup,
            'action_type': action_type,
            'is_successful': True,
            'message': message,
            'iot_history_id': str(history.id),
        }

    def _log_action(
        self,
        partner,
        performed_by,
        station: Station,
        action_type: str,
        request_payload: Dict[str, Any],
        response_data: Optional[Dict[str, Any]],
        is_successful: bool,
        error_message: Optional[str],
        powerbank_sn: Optional[str] = None,
        slot_number: Optional[int] = None,
        is_free_ejection: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> PartnerIotHistory:
        """Create partner IoT history row for any action."""
        return PartnerIotHistoryRepository.create(
            partner_id=str(partner.id),
            performed_by_id=performed_by.id,
            station_id=str(station.id),
            action_type=action_type,
            performed_from=PartnerIotHistory.PerformedFrom.DASHBOARD,
            powerbank_sn=powerbank_sn,
            slot_number=slot_number,
            rental_id=None,
            is_free_ejection=is_free_ejection,
            is_successful=is_successful,
            error_message=error_message,
            request_payload=request_payload or {},
            response_data=response_data or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def _mask_sensitive_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive values before storing request payload."""
        masked = dict(payload or {})
        if 'wifi_password' in masked and masked['wifi_password'] is not None:
            masked['wifi_password'] = '***'
        return masked

    def _serialize_value(self, value: Any) -> Any:
        """Convert dataclasses and custom objects into JSON-serializable values."""
        if value is None:
            return None
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._serialize_value(item) for key, item in value.items()}
        if hasattr(value, '__dict__'):
            return {
                key: self._serialize_value(item)
                for key, item in value.__dict__.items()
                if not key.startswith('_')
            }
        return value
