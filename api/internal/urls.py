"""
Internal API URLs for IoT system integration
Separate from main API to allow different authentication/middleware
"""
from __future__ import annotations

from django.urls import path
from api.internal.views import StationDataInternalView, internal_iot_router

urlpatterns = [
    path('internal/stations/data', StationDataInternalView.as_view(), name='internal-station-data'),
    *internal_iot_router.urls,
]
