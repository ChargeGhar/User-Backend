# Vendor views
from api.common.routers import CustomViewRouter

# Import routers from view files
from .dashboard_view import vendor_dashboard_router
from .revenue_view import vendor_revenue_router
from .payout_view import vendor_payout_router
from .agreement_view import vendor_agreement_router

# Merge all routers into single router for URL inclusion
router = CustomViewRouter()

router._paths.extend(vendor_dashboard_router._paths)
router._drf_router.registry.extend(vendor_dashboard_router._drf_router.registry)

router._paths.extend(vendor_revenue_router._paths)
router._drf_router.registry.extend(vendor_revenue_router._drf_router.registry)

router._paths.extend(vendor_payout_router._paths)
router._drf_router.registry.extend(vendor_payout_router._drf_router.registry)

router._paths.extend(vendor_agreement_router._paths)
router._drf_router.registry.extend(vendor_agreement_router._drf_router.registry)

__all__ = [
    'router',
]
