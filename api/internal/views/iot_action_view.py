"""
Internal IoT action endpoints for partner-controlled station operations.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from api.common.decorators import log_api_call
from api.common.mixins import BaseAPIView
from api.common.routers import CustomViewRouter
from api.common.serializers import BaseResponseSerializer
from api.common.services.base import ServiceException
from api.common.utils.helpers import get_client_ip
from api.internal.serializers import (
    IoTCheckRequestSerializer,
    IoTEjectRequestSerializer,
    IoTModeRequestSerializer,
    IoTStationActionSerializer,
    IoTVolumeRequestSerializer,
    IoTWifiConnectRequestSerializer,
)
from api.internal.services import InternalIoTActionService
from api.partners.auth.permissions import CanPerformIotAction, IsFranchise
from api.user.stations.models import Station


internal_iot_router = CustomViewRouter()


class InternalIoTActionBaseView(GenericAPIView, BaseAPIView):
    """
    Base view for station-level IoT actions.
    Enforces station access via object permissions before command dispatch.
    """

    permission_classes = [IsAuthenticated, CanPerformIotAction]
    iot_action: str = ''

    @staticmethod
    def _get_station(station_id):
        station = Station.objects.filter(id=station_id, is_deleted=False).first()
        if not station:
            raise ServiceException(
                detail="Station not found",
                code='station_not_found',
                status_code=404,
            )
        return station

    def _get_action_context(self, request: Request, station_id):
        partner = request.user.partner_profile
        station = self._get_station(station_id)
        self.check_object_permissions(request, station)
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        return partner, station, ip_address, user_agent


@internal_iot_router.register(r"internal/iot/reboot", name="internal-iot-reboot")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Reboot Station",
    request=IoTStationActionSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTRebootView(InternalIoTActionBaseView):
    """POST /api/internal/iot/reboot"""

    serializer_class = IoTStationActionSerializer
    iot_action = 'REBOOT'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.reboot_station(
                partner=partner,
                performed_by=request.user,
                station=station,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="Reboot command sent successfully",
            error_message="Failed to reboot station",
        )


@internal_iot_router.register(r"internal/iot/check", name="internal-iot-check")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Check Station Status",
    request=IoTCheckRequestSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTCheckView(InternalIoTActionBaseView):
    """POST /api/internal/iot/check"""

    serializer_class = IoTCheckRequestSerializer
    iot_action = 'CHECK'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.check_station(
                partner=partner,
                performed_by=request.user,
                station=station,
                check_all=serializer.validated_data['check_all'],
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="Station check completed successfully",
            error_message="Failed to check station",
        )


@internal_iot_router.register(r"internal/iot/wifi/scan", name="internal-iot-wifi-scan")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Scan Station WiFi",
    request=IoTStationActionSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTWifiScanView(InternalIoTActionBaseView):
    """POST /api/internal/iot/wifi/scan"""

    serializer_class = IoTStationActionSerializer
    iot_action = 'WIFI_SCAN'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.wifi_scan(
                partner=partner,
                performed_by=request.user,
                station=station,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="WiFi scan completed successfully",
            error_message="Failed to scan WiFi",
        )


@internal_iot_router.register(r"internal/iot/wifi/connect", name="internal-iot-wifi-connect")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Connect Station WiFi",
    request=IoTWifiConnectRequestSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTWifiConnectView(InternalIoTActionBaseView):
    """POST /api/internal/iot/wifi/connect"""

    serializer_class = IoTWifiConnectRequestSerializer
    iot_action = 'WIFI_CONNECT'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.wifi_connect(
                partner=partner,
                performed_by=request.user,
                station=station,
                ssid=serializer.validated_data['wifi_ssid'],
                password=serializer.validated_data.get('wifi_password'),
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="WiFi connect command sent successfully",
            error_message="Failed to connect WiFi",
        )


@internal_iot_router.register(r"internal/iot/volume", name="internal-iot-volume")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Set Station Volume",
    request=IoTVolumeRequestSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTVolumeView(InternalIoTActionBaseView):
    """POST /api/internal/iot/volume"""

    serializer_class = IoTVolumeRequestSerializer
    iot_action = 'VOLUME'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.set_volume(
                partner=partner,
                performed_by=request.user,
                station=station,
                volume=serializer.validated_data['volume'],
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="Volume updated successfully",
            error_message="Failed to set volume",
        )


@internal_iot_router.register(r"internal/iot/mode", name="internal-iot-mode")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Set Station Network Mode",
    request=IoTModeRequestSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTModeView(InternalIoTActionBaseView):
    """POST /api/internal/iot/mode"""

    serializer_class = IoTModeRequestSerializer
    iot_action = 'MODE'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.set_mode(
                partner=partner,
                performed_by=request.user,
                station=station,
                mode=serializer.validated_data['mode'],
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="Mode updated successfully",
            error_message="Failed to set mode",
        )


@internal_iot_router.register(r"internal/iot/eject", name="internal-iot-eject")
@extend_schema(
    tags=["Internal - IoT Actions"],
    summary="Eject Powerbank (Franchise Only)",
    request=IoTEjectRequestSerializer,
    responses={200: BaseResponseSerializer},
)
class InternalIoTEjectView(InternalIoTActionBaseView):
    """POST /api/internal/iot/eject"""

    serializer_class = IoTEjectRequestSerializer
    permission_classes = [IsAuthenticated, IsFranchise, CanPerformIotAction]
    iot_action = 'EJECT'

    @log_api_call()
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        def operation():
            partner, station, ip_address, user_agent = self._get_action_context(
                request,
                serializer.validated_data['station_id'],
            )
            service = InternalIoTActionService()
            return service.eject_powerbank(
                partner=partner,
                performed_by=request.user,
                station=station,
                powerbank_sn=serializer.validated_data.get('powerbank_sn'),
                reason=serializer.validated_data.get('reason', ''),
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self.handle_service_operation(
            operation,
            success_message="Powerbank ejected successfully",
            error_message="Failed to eject powerbank",
        )
