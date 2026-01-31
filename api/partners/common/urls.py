"""
Partner Common URLs

Shared partner endpoints (IoT history, Stations).
Base path: /api/partner/
"""

from api.partners.common.views import partner_iot_router, partner_station_router

urlpatterns = [
    *partner_iot_router.urls,
    *partner_station_router.urls,
]
