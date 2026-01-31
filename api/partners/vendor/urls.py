"""
Vendor Dashboard URLs

Base path: /api/partner/vendor/
"""

from api.partners.vendor.views import router

urlpatterns = [
    *router.urls,
]
