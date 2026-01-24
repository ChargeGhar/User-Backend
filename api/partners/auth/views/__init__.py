# api/partners/auth/views/__init__.py
"""
Views package for partners auth app.
Maintains backward compatibility by exposing single router.
"""
from __future__ import annotations

from api.common.routers import CustomViewRouter

from .login_view import login_router, PartnerLoginView
from .password_views import password_router, PartnerChangePasswordView
from .token_views import token_router, PartnerRefreshTokenView, PartnerLogoutView
from .profile_view import profile_router, PartnerMeView

# Merge all sub-routers
router = CustomViewRouter()

for sub_router in [login_router, password_router, token_router, profile_router]:
    router._paths.extend(sub_router._paths)
    router._drf_router.registry.extend(sub_router._drf_router.registry)

__all__ = [
    'router',
    'PartnerLoginView',
    'PartnerChangePasswordView',
    'PartnerRefreshTokenView',
    'PartnerLogoutView',
    'PartnerMeView',
]
