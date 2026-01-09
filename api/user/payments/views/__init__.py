"""
Views package for payments app
Maintains backward compatibility by exposing single router
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .core_views import core_router
from .wallet_views import wallet_router
from .refund_views import refund_router
from .withdrawal_views import withdrawal_router

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [core_router, wallet_router, refund_router, withdrawal_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)