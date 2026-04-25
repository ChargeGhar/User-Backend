"""
Internal Ad Distribution View
==============================
Device-facing endpoint for fetching active advertisements per station.

GET /api/internal/ads/distribute?station_serial=<IMEI>
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
from api.internal.serializers import AdDistributionItemSerializer
from api.internal.services import AdDistributionService
from api.user.auth.permissions import IsStaffPermission

internal_ad_router = CustomViewRouter()


@internal_ad_router.register(r"internal/ads/distribute", name="internal-ads-distribute")
@extend_schema(
    tags=["Internal - Advertising"],
    summary="Get Active Ads for Station",
    description="Returns active advertisements assigned to a station for device display.",
    responses={200: BaseResponseSerializer},
)
class AdDistributionInternalView(GenericAPIView, BaseAPIView):
    """
    GET /api/internal/ads/distribute?station_serial=<IMEI>

    Returns active advertisements for a hardware station.
    Called by StationBackend Java service ( ChargeGharConnector.fetchActiveAds() ).
    """
    permission_classes = [IsAuthenticated, IsStaffPermission]
    serializer_class = AdDistributionItemSerializer

    @log_api_call()
    def get(self, request: Request) -> Response:
        station_serial = request.query_params.get("station_serial")
        if not station_serial:
            return self.error_response(
                message="station_serial query parameter is required",
                code="missing_station_serial",
                status_code=400,
            )

        service = AdDistributionService()
        ads = service.get_active_ads_for_station(station_serial)

        return self.success_response(
            data=ads,
            message="Active advertisements retrieved successfully",
        )
