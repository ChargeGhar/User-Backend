"""
Views package for social app
Maintains backward compatibility by exposing single router
"""
from api.common.routers import CustomViewRouter

from .achievement_views import achievement_router
from .social_views import social_router

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [achievement_router, social_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)