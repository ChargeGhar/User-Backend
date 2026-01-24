# api/partners/auth/urls.py
"""
Partner Auth URLs

Authentication endpoints for partners (Franchise & Revenue Vendor).
Base path: /api/partners/auth/
"""
from __future__ import annotations

from api.partners.auth.views import router

urlpatterns = [
    *router.urls,
]
