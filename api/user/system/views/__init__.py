"""
Views package for system app
Maintains backward compatibility by exposing single router
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .country_views import country_router
from .app_info_views import app_info_router
from .app_updates_views import app_updates_router

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [country_router, app_info_router, app_updates_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)