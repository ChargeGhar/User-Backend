"""
Views package for rentals app
Maintains backward compatibility by exposing single router
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .core_views import core_router
from .history_views import history_router
from .support_views import support_router
from .package_views import package_router

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [core_router, history_router, support_router, package_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)