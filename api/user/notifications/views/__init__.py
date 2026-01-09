"""
Views package for notifications app
Maintains backward compatibility by exposing single router
"""


from api.common.routers import CustomViewRouter

from .core_views import core_router
from .detail_views import detail_router
from .action_views import action_router

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [core_router, detail_router, action_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)