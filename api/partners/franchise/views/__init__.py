# Franchise views
from api.common.routers import CustomViewRouter

# Import routers from view files
from .franchise_dashboard_view import franchise_dashboard_router
from .franchise_vendor_view import franchise_vendor_router
from .franchise_revenue_view import franchise_revenue_router
from .franchise_payout_view import franchise_payout_router
from .franchise_vendor_payout_view import franchise_vendor_payout_router
from .franchise_agreement_view import franchise_agreement_router
from .franchise_user_view import franchise_user_router

# Merge all routers into single router for URL inclusion
router = CustomViewRouter()

router._paths.extend(franchise_dashboard_router._paths)
router._drf_router.registry.extend(franchise_dashboard_router._drf_router.registry)

router._paths.extend(franchise_vendor_router._paths)
router._drf_router.registry.extend(franchise_vendor_router._drf_router.registry)

router._paths.extend(franchise_revenue_router._paths)
router._drf_router.registry.extend(franchise_revenue_router._drf_router.registry)

router._paths.extend(franchise_payout_router._paths)
router._drf_router.registry.extend(franchise_payout_router._drf_router.registry)

router._paths.extend(franchise_vendor_payout_router._paths)
router._drf_router.registry.extend(franchise_vendor_payout_router._drf_router.registry)

router._paths.extend(franchise_agreement_router._paths)
router._drf_router.registry.extend(franchise_agreement_router._drf_router.registry)

router._paths.extend(franchise_user_router._paths)
router._drf_router.registry.extend(franchise_user_router._drf_router.registry)

__all__ = [
    'router',
]
