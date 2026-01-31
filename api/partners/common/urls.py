"""
Partner Common URLs

Shared partner endpoints (IoT history).
Base path: /api/partner/
"""

from api.partners.common.views import partner_iot_router

urlpatterns = [
    *partner_iot_router.urls,
]
