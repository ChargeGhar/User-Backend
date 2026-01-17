"""
Views package for admin app
Maintains backward compatibility by exposing single router
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .auth_views import auth_router
from .monitoring_views import monitoring_router
from .user_management_views import user_management_router
from .payment_views import payment_router
from .station_views import station_router
from .station_issue_views import station_issue_router
from .powerbank_views import powerbank_router
from .notification_views import notification_router
from .content_admin_views import content_admin_router
from .config_admin_views import config_admin_router
from .media_admin_views import media_admin_router
from .app_admin_views import app_admin_router
from .withdrawal_views import withdrawal_admin_router
from .coupon_views import coupon_router
from .rental_views import rental_router
from .kyc_views import kyc_router
from .amenity_views import amenity_admin_router
from .analytics_views import analytics_router
from .user_analytics_views import user_analytics_router
from .rental_analytics_views import rental_analytics_router
from .payment_analytics_views import payment_analytics_router
from .station_analytics_views import station_analytics_router
from .late_fee_views import late_fee_admin_router
from .points_admin_views import points_admin_router
from .achievement_admin_views import achievement_admin_router
from .referral_admin_views import referral_admin_router
from .ad_views import admin_ads_router

# Merge all sub-routers
# IMPORTANT: Order matters! More specific routes must come before generic ones
router = CustomViewRouter()

for sub_router in [
    auth_router, 
    monitoring_router,
    referral_admin_router,  # MUST come before user_management_router (contains /admin/users/leaderboard)
    user_management_router, 
    payment_router, 
    station_issue_router,  # MUST come before station_router (specific before generic)
    station_router,        # Generic route with <station_sn> parameter
    powerbank_router,
    notification_router, 
    content_admin_router, 
    config_admin_router, 
    media_admin_router, 
    app_admin_router, 
    withdrawal_admin_router, 
    coupon_router, 
    rental_router, 
    kyc_router, 
    amenity_admin_router,
    analytics_router,
    user_analytics_router,
    rental_analytics_router,
    payment_analytics_router,
    station_analytics_router,
    late_fee_admin_router,
    points_admin_router,
    achievement_admin_router,
    admin_ads_router
]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)