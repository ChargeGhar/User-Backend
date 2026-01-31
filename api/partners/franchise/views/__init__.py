# Franchise views
from .franchise_dashboard_view import franchise_dashboard_router
from .franchise_vendor_view import franchise_vendor_router
from .franchise_station_view import franchise_station_router
from .franchise_agreement_view import franchise_agreement_router
from .franchise_revenue_view import franchise_revenue_router
from .franchise_payout_view import franchise_payout_router
from .franchise_vendor_payout_view import franchise_vendor_payout_router

__all__ = [
    'franchise_dashboard_router',
    'franchise_vendor_router',
    'franchise_station_router',
    'franchise_agreement_router',
    'franchise_revenue_router',
    'franchise_payout_router',
    'franchise_vendor_payout_router',
]
