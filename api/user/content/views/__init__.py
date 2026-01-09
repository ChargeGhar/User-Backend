"""
Views package for content app
Maintains backward compatibility by exposing single router
"""


from api.common.routers import CustomViewRouter

from .static_pages_views import static_pages_router
from .dynamic_content_views import dynamic_content_router
# admin_views migrated to api/admin/views/content_admin_views.py

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [static_pages_router, dynamic_content_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)
