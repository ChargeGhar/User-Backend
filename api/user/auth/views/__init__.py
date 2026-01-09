"""
Views package for users app
Maintains backward compatibility by exposing single router
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .auth_views import auth_router
from .social_auth_views import social_router
from .profile_views import profile_router

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [auth_router, social_router, profile_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)